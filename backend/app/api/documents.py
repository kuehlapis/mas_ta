\
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field, ValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.schemas import DocumentCreateResponse, DocumentListResponse, IngestResponse
from app.services.rag import pdf_to_text
from app.services.ingest import create_document, ingest_document, list_documents

router = APIRouter(prefix="/documents")


class TextDocumentRequest(BaseModel):
    filename: str = Field(default="pasted.txt", min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=2_000_000)


MAX_UPLOAD_BYTES = 5 * 1024 * 1024

# FastAPI can't bind a multipart file and a JSON body in one signature (a File param
# forces the whole body to be form data), so the content type is dispatched by hand
# and both shapes are declared for the OpenAPI docs.
_UPLOAD_OPENAPI = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {"file": {"type": "string", "format": "binary"}},
                    "required": ["file"],
                }
            },
            "application/json": {"schema": TextDocumentRequest.model_json_schema()},
        },
    }
}


@router.post("", response_model=DocumentCreateResponse, openapi_extra=_UPLOAD_OPENAPI)
async def upload_document(request: Request):
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        file = form.get("file")
        if not isinstance(file, StarletteUploadFile):
            raise HTTPException(status_code=400, detail="Multipart upload needs a 'file' field.")
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 5MB).")
        if data.startswith(b"%PDF"):
            try:
                content = await run_in_threadpool(pdf_to_text, data)  # ~15s for a 27-page PDF
            except Exception:
                raise HTTPException(status_code=400, detail="Could not read PDF.")
        else:
            content = data.decode("utf-8", errors="replace")
        filename = file.filename or "upload.txt"

    elif content_type.startswith("application/json"):
        try:
            body = TextDocumentRequest.model_validate_json(await request.body())
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=jsonable_encoder(e.errors(include_url=False)))
        filename, content = body.filename, body.content

    else:
        raise HTTPException(
            status_code=415, detail="Send multipart/form-data with a 'file' field, or a JSON body {filename, content}."
        )

    if not content.strip():
        raise HTTPException(status_code=400, detail="Document has no extractable text.")
    return {"doc_id": create_document(filename=filename, content=content)}


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
