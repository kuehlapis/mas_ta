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
    score: float
    snippet: str
    mode: Mode


class SearchResponse(BaseModel):
    query: str
    mode: Mode
    results: list[SearchResult]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    mode: Mode = "hybrid"
    top_k: int = Field(default=6, ge=1, le=20)


class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    snippet: str


class AskResponse(BaseModel):
    question: str
    mode: Mode
    answer: str
    citations: list[Citation]
