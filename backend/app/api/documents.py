\
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, HTTPException
from pydantic import BaseModel, Field

from app.schemas import DocumentCreateResponse, DocumentListResponse, IngestResponse
from app.services.ingest import create_document, ingest_document, list_documents

router = APIRouter(prefix="/documents")


class TextDocumentRequest(BaseModel):
    filename: str = Field(default="pasted.txt", min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2_000_000)


@router.post("", response_model=DocumentCreateResponse)
async def upload_document(file: UploadFile | None = File(default=None), body: TextDocumentRequest | None = None):
    if file is None and body is None:
        raise HTTPException(status_code=400, detail="Provide either a file upload or a JSON body.")
    if file is not None and body is not None:
        raise HTTPException(status_code=400, detail="Provide either file OR body, not both.")

    if file is not None:
        data = await file.read()
        if len(data) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 5MB).")
        content = data.decode("utf-8", errors="replace")
        doc_id = create_document(filename=file.filename or "upload.txt", content=content)
        return {"doc_id": doc_id}

    doc_id = create_document(filename=body.filename, content=body.content)
    return {"doc_id": doc_id}


@router.get("", response_model=DocumentListResponse)
def get_documents():
    return {"documents": list_documents()}


@router.post("/{doc_id}/ingest", response_model=IngestResponse)
def ingest(doc_id: str):
    try:
        n = ingest_document(doc_id)
        return {"doc_id": doc_id, "chunks_indexed": n}
    except KeyError:
        raise HTTPException(status_code=404, detail="Document not found.")
