\
from __future__ import annotations

import os
from dataclasses import replace
from functools import lru_cache

from flashrank import Ranker, RerankRequest

from app.services.answer import to_plain
from app.services.rag import ScoredChunk, split_section

RERANK_ENABLED = os.getenv("DOCQA_RERANK", "true").lower() in ("1", "true", "yes")
RERANK_CANDIDATES = int(os.getenv("DOCQA_RERANK_CANDIDATES", "20"))
RERANK_MODEL = os.getenv("DOCQA_RERANK_MODEL", "ms-marco-TinyBERT-L-2-v2")
RERANK_CACHE_DIR = os.getenv("DOCQA_RERANK_CACHE_DIR", "/opt/flashrank")


@lru_cache(maxsize=1)
def _ranker() -> Ranker:
    # the Dockerfile downloads the model into RERANK_CACHE_DIR at build time
    return Ranker(model_name=RERANK_MODEL, cache_dir=RERANK_CACHE_DIR, max_length=512)


def _passage(chunk: ScoredChunk) -> str:
    section, body = split_section(chunk.text)
    return f"{section}\n{to_plain(body)}" if section else to_plain(body)


def rerank(query: str, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
    """Return chunks sorted by cross-encoder relevance; score becomes the reranker score."""
    if not chunks:
        return chunks
    by_id = {c.chunk_id: c for c in chunks}
    results = _ranker().rerank(
        RerankRequest(query=query, passages=[{"id": c.chunk_id, "text": _passage(c)} for c in chunks])
    )
    return [
        replace(by_id[r["id"]], score=float(r["score"]), rerank_rank=rank)
        for rank, r in enumerate(results, start=1)
    ]
