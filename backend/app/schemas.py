\
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal

Mode = Literal["keyword", "semantic", "hybrid"]


class DocumentCreateResponse(BaseModel):
    doc_id: str


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    created_at: str
    ingested: bool
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]


class IngestResponse(BaseModel):
    doc_id: str
    chunks_indexed: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    mode: Mode = "hybrid"
    top_k: int = Field(default=10, ge=1, le=50)


class SearchResult(BaseModel):
    doc_id: str
    chunk_id: str
    filename: str
    page: int
    section: str = Field(description="Page title > section heading the chunk belongs to")
    score: float = Field(description="BM25 (keyword), cosine similarity (semantic), reranker relevance or RRF sum (hybrid)")
    snippet: str
    mode: Mode
    keyword_rank: int | None = Field(default=None, description="1-based rank in Elasticsearch results, if present")
    semantic_rank: int | None = Field(default=None, description="1-based rank in Redis vector results, if present")
    rerank_rank: int | None = Field(default=None, description="1-based rank after cross-encoder reranking (hybrid)")


class SearchResponse(BaseModel):
    query: str
    mode: Mode
    results: list[SearchResult]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    mode: Mode = "hybrid"
    top_k: int = Field(default=6, ge=1, le=20)


class Citation(BaseModel):
    n: int = Field(description="Number used by the [n] markers in the answer")
    doc_id: str
    chunk_id: str
    filename: str
    page: int
    section: str
    snippet: str = Field(description="Window of the retrieved chunk containing every quoted sentence")
    quotes: list[str] = Field(description="Sentences of the answer copied verbatim from this chunk")
    text: str = Field(description="Full retrieved chunk as plain text")


class AskResponse(BaseModel):
    question: str
    mode: Mode
    answer: str
    citations: list[Citation]
    blocked_sentences: int = Field(
        default=0, description="Retrieved sentences dropped because they looked like prompt injection"
    )
