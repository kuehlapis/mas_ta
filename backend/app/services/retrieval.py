\
from __future__ import annotations

from typing import Literal

from redis.commands.search.query import Query

from app.services.rag import ScoredChunk, embed_hash, rrf
from app.services.es_store import es_client, ES_INDEX
from app.services.redis_store import redis_client, REDIS_INDEX

Mode = Literal["keyword", "semantic", "hybrid"]


def keyword_search(query: str, *, top_k: int) -> list[ScoredChunk]:
    es = es_client()
    resp = es.search(index=ES_INDEX, size=top_k, query={"match": {"text": {"query": query}}})
    out: list[ScoredChunk] = []
    for hit in resp.get("hits", {}).get("hits", []):
        src = hit["_source"]
        out.append(ScoredChunk(doc_id=src["doc_id"], chunk_id=src["chunk_id"], text=src["text"], score=float(hit.get("_score") or 0.0)))
    return out


def semantic_search(query: str, *, top_k: int) -> list[ScoredChunk]:
    r = redis_client()
    qv = embed_hash(query).astype("float32").tobytes()

    q = (
        Query(f"*=>[KNN {top_k} @embedding $vec AS score]")
        .return_fields("doc_id", "chunk_id", "text", "score")
        .sort_by("score")
        .dialect(2)
    )
    res = r.ft(REDIS_INDEX).search(q, query_params={"vec": qv})

    out: list[ScoredChunk] = []
    for doc in res.docs:
        dist = float(doc.score)
        sim = 1.0 - dist
        doc_id = doc.doc_id.decode() if isinstance(doc.doc_id, (bytes, bytearray)) else doc.doc_id
        chunk_id = doc.chunk_id.decode() if isinstance(doc.chunk_id, (bytes, bytearray)) else doc.chunk_id
        text = doc.text.decode() if isinstance(doc.text, (bytes, bytearray)) else doc.text
        out.append(ScoredChunk(doc_id=doc_id, chunk_id=chunk_id, text=text, score=sim))
    out.sort(key=lambda x: x.score, reverse=True)
    return out


def search(query: str, *, mode: Mode, top_k: int) -> list[ScoredChunk]:
    if mode == "keyword":
        return keyword_search(query, top_k=top_k)
    if mode == "semantic":
        return semantic_search(query, top_k=top_k)

    kw = keyword_search(query, top_k=max(top_k * 3, 30))
    sem = semantic_search(query, top_k=max(top_k * 3, 30))

    fused: dict[str, ScoredChunk] = {}
    for i, x in enumerate(kw):
        fused[x.chunk_id] = ScoredChunk(x.doc_id, x.chunk_id, x.text, rrf(i))
    for i, x in enumerate(sem):
        add = rrf(i)
        prev = fused.get(x.chunk_id)
        if prev:
            fused[x.chunk_id] = ScoredChunk(prev.doc_id, prev.chunk_id, prev.text, prev.score + add)
        else:
            fused[x.chunk_id] = ScoredChunk(x.doc_id, x.chunk_id, x.text, add)

    out = list(fused.values())
    out.sort(key=lambda x: x.score, reverse=True)
    return out[:top_k]
