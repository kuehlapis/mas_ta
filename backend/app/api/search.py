\
from __future__ import annotations

import re

from fastapi import APIRouter

from app.schemas import AskRequest, AskResponse, SearchRequest, SearchResponse
from app.services.answer import NO_ANSWER, answer_question, to_plain
from app.services.rag import split_section
from app.services.retrieval import search as do_search

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    chunks = do_search(req.query, mode=req.mode, top_k=req.top_k)
    results = []
    for c in chunks:
        section, body = split_section(c.text)
        body = to_plain(body)
        results.append(
            {
                "doc_id": c.doc_id,
                "chunk_id": c.chunk_id,
                "filename": c.filename,
                "page": c.page,
                "section": section,
                "score": float(c.score),
                "snippet": body[:240] + ("…" if len(body) > 240 else ""),
                "mode": req.mode,
                "keyword_rank": c.keyword_rank,
                "semantic_rank": c.semantic_rank,
                "rerank_rank": c.rerank_rank,
            }
        )
    return {"query": req.query, "mode": req.mode, "results": results}


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    chunks = do_search(req.question, mode=req.mode, top_k=req.top_k)
    result = answer_question(req.question, chunks)

    citations = [
        {
            "n": c.n,
            "doc_id": c.chunk.doc_id,
            "chunk_id": c.chunk.chunk_id,
            "filename": c.chunk.filename,
            "page": c.chunk.page,
            "section": c.section,
            "snippet": c.snippet(),
            "quotes": c.quotes,
            "text": c.plain,
        }
        for c in result.citations
    ]

    markers = {int(m) for m in re.findall(r"\[(\d+)\]", result.text)}
    valid = {c["n"] for c in citations}
    if markers - valid or any(q not in c["snippet"].replace("…", "") for c in citations for q in c["quotes"]):
        return {"question": req.question, "mode": req.mode, "answer": NO_ANSWER, "citations": [], "blocked_sentences": 0}

    return {
        "question": req.question,
        "mode": req.mode,
        "answer": result.text,
        "citations": citations,
        "blocked_sentences": result.blocked_sentences,
    }
