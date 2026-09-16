\
from __future__ import annotations

from fastapi import APIRouter

from app.schemas import AskRequest, AskResponse, SearchRequest, SearchResponse
from app.services.retrieval import search as do_search

router = APIRouter()


def _sanitize_context(text: str) -> str:
    lines = text.splitlines()
    cleaned = []
    for ln in lines:
        if "IGNORE ALL PREVIOUS INSTRUCTIONS" in ln.upper():
            continue
        cleaned.append(ln)
    return "\n".join(cleaned)


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    chunks = do_search(req.query, mode=req.mode, top_k=req.top_k)
    return {
        "query": req.query,
        "mode": req.mode,
        "results": [
            {
                "doc_id": c.doc_id,
                "chunk_id": c.chunk_id,
                "score": float(c.score),
                "snippet": c.text[:240] + ("…" if len(c.text) > 240 else ""),
                "mode": req.mode,
            }
            for c in chunks
        ],
    }


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    chunks = do_search(req.question, mode=req.mode, top_k=req.top_k)
    if not chunks:
        return {"question": req.question, "mode": req.mode, "answer": "I don't know based on the provided documents.", "citations": []}

    answer = (
        "Based on the documents I found, here is the best answer I can support:\\n\\n"
        f"{_summarize_heuristic(req.question, chunks)}\\n\\n"
        "Citations are listed below."
    )

    return {
        "question": req.question,
        "mode": req.mode,
        "answer": answer,
        "citations": [{"doc_id": c.doc_id, "chunk_id": c.chunk_id, "snippet": c.text[:240]} for c in chunks],
    }


def _summarize_heuristic(question: str, chunks):
    q = question.lower()
    for c in chunks:
        t = c.text
        if any(w in t.lower() for w in q.split()[:3]):
            return _sanitize_context(t)[:450] + ("…" if len(t) > 450 else "")
    t = _sanitize_context(chunks[0].text)
    return t[:450] + ("…" if len(t) > 450 else "")
