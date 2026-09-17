\
from __future__ import annotations

import os
from dataclasses import replace
from typing import Literal

from redis.commands.search.query import Query

from app.services.rag import ScoredChunk, embed_hash, rrf
from app.services.es_store import es_client, ES_INDEX
from app.services.redis_store import redis_client, REDIS_INDEX
from app.services.reranker import RERANK_CANDIDATES, RERANK_ENABLED, rerank

Mode = Literal["keyword", "semantic", "hybrid"]

RRF_K = int(os.getenv("DOCQA_RRF_K", "60"))
RRF_KEYWORD_WEIGHT = float(os.getenv("DOCQA_RRF_KEYWORD_WEIGHT", "1.0"))
RRF_SEMANTIC_WEIGHT = float(os.getenv("DOCQA_RRF_SEMANTIC_WEIGHT", "1.0"))
RERANK_PER_RETRIEVER = int(os.getenv("DOCQA_RERANK_PER_RETRIEVER", "5"))


def _str(v) -> str:
    return v.decode() if isinstance(v, (bytes, bytearray)) else str(v)


def keyword_search(query: str, *, top_k: int) -> list[ScoredChunk]:
    es = es_client()
    resp = es.search(
        index=ES_INDEX,
        size=top_k,
        query={"multi_match": {"query": query, "fields": ["text", "text.en"], "type": "most_fields"}},
    )
    out: list[ScoredChunk] = []
    for rank, hit in enumerate(resp.get("hits", {}).get("hits", []), start=1):
        src = hit["_source"]
        out.append(
            ScoredChunk(
                doc_id=src["doc_id"],
                chunk_id=src["chunk_id"],
                text=src["text"],
                score=float(hit.get("_score") or 0.0),
                page=int(src.get("page", 1)),
                filename=src.get("filename", ""),
                keyword_rank=rank,
            )
        )
    return out


def semantic_search(query: str, *, top_k: int) -> list[ScoredChunk]:
    r = redis_client()
    qv = embed_hash(query).astype("float32").tobytes()

    q = (
        Query(f"*=>[KNN {top_k} @embedding $vec AS score]")
        .return_fields("doc_id", "chunk_id", "filename", "page", "text", "score")
        .sort_by("score")
        .paging(0, top_k)  
        .dialect(2)
    )
    res = r.ft(REDIS_INDEX).search(q, query_params={"vec": qv})

    out: list[ScoredChunk] = []
    for rank, doc in enumerate(res.docs, start=1):
        out.append(
            ScoredChunk(
                doc_id=_str(doc.doc_id),
                chunk_id=_str(doc.chunk_id),
                text=_str(doc.text),
                score=1.0 - float(doc.score),  
                page=int(_str(getattr(doc, "page", 1))),
                filename=_str(getattr(doc, "filename", "")),
                semantic_rank=rank,
            )
        )
    return out


def search(query: str, *, mode: Mode, top_k: int) -> list[ScoredChunk]:
    if mode == "keyword":
        return keyword_search(query, top_k=top_k)
    if mode == "semantic":
        return semantic_search(query, top_k=top_k)


    depth = max(top_k * 3, 30)
    kw = keyword_search(query, top_k=depth)
    sem = semantic_search(query, top_k=depth)

    fused: dict[str, ScoredChunk] = {}
    for i, x in enumerate(kw):
        fused[x.chunk_id] = replace(x, score=RRF_KEYWORD_WEIGHT * rrf(i, k=RRF_K))
    for i, x in enumerate(sem):
        add = RRF_SEMANTIC_WEIGHT * rrf(i, k=RRF_K)
        prev = fused.get(x.chunk_id)
        if prev:
            fused[x.chunk_id] = replace(prev, score=prev.score + add, semantic_rank=x.semantic_rank)
        else:
            fused[x.chunk_id] = replace(x, score=add)
    out = sorted(fused.values(), key=lambda x: x.score, reverse=True)

    if RERANK_ENABLED:
        pool = {c.chunk_id: c for c in out[: max(RERANK_CANDIDATES, top_k)]}
        for x in kw[:RERANK_PER_RETRIEVER] + sem[:RERANK_PER_RETRIEVER]:
            pool.setdefault(x.chunk_id, fused[x.chunk_id])
        out = rerank(query, list(pool.values()))
    return out[:top_k]
