\
from __future__ import annotations

import hashlib
import time
from datetime import datetime

import numpy as np
from elasticsearch import helpers

from app.services.rag import chunk_text, embed_hash, split_pages
from app.services.store import get_conn
from app.services.es_store import es_client, ES_INDEX
from app.services.redis_store import redis_client, REDIS_PREFIX


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def create_document(*, filename: str, content: str) -> str:
    doc_id = hashlib.sha1(f"{filename}-{time.time()}".encode("utf-8")).hexdigest()[:16]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO documents(doc_id, filename, content, created_at) VALUES (?, ?, ?, ?)",
            (doc_id, filename, content, _now_iso()),
        )
    return doc_id


def list_documents() -> list[dict]:
    with get_conn() as conn:
        docs = conn.execute("SELECT doc_id, filename, created_at FROM documents ORDER BY created_at DESC").fetchall()
        out = []
        for doc_id, filename, created_at in docs:
            chunk_count = conn.execute("SELECT COUNT(1) FROM chunks WHERE doc_id = ?", (doc_id,)).fetchone()[0]
            out.append(
                {
                    "doc_id": doc_id,
                    "filename": filename,
                    "created_at": created_at,
                    "ingested": chunk_count > 0,
                    "chunk_count": int(chunk_count),
                }
            )
        return out


def ingest_document(doc_id: str) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT filename, content FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        if not row:
            raise KeyError("document not found")
        filename, content = row
        conn.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))

    # chunk within each page so every chunk maps to exactly one page
    chunks = [(page, text) for page, page_text in split_pages(content) for text in chunk_text(page_text)]
    es = es_client()
    r = redis_client()

    # best-effort cleanup
    try:
        es.delete_by_query(index=ES_INDEX, query={"term": {"doc_id": doc_id}}, refresh=True)
    except Exception:
        pass
    try:
        stale = list(r.scan_iter(match=f"{REDIS_PREFIX}{doc_id}:*"))
        if stale:
            r.delete(*stale)
    except Exception:
        pass

    actions = []
    pipe = r.pipeline()

    with get_conn() as conn:
        for i, (page, text) in enumerate(chunks):
            chunk_id = hashlib.sha1(f"{doc_id}:{i}".encode("utf-8")).hexdigest()[:20]
            emb = embed_hash(text).astype(np.float32)
            conn.execute(
                "INSERT INTO chunks(chunk_id, doc_id, ord, page, text, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                (chunk_id, doc_id, i, page, text, emb.tobytes()),
            )

            actions.append(
                {
                    "_index": ES_INDEX,
                    "_id": chunk_id,
                    "_source": {
                        "doc_id": doc_id,
                        "chunk_id": chunk_id,
                        "filename": filename,
                        "ord": i,
                        "page": page,
                        "text": text,
                    },
                }
            )

            key = f"{REDIS_PREFIX}{doc_id}:{chunk_id}"
            pipe.hset(
                key,
                mapping={
                    "doc_id": doc_id,
                    "chunk_id": chunk_id,
                    "filename": filename,
                    "page": page,
                    "text": text,
                    "embedding": emb.tobytes(),
                },
            )

    if actions:
        helpers.bulk(es, actions, refresh=True)
    pipe.execute()

    return len(chunks)
