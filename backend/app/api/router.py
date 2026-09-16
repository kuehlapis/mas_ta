\
from __future__ import annotations

from fastapi import APIRouter

from app.api.documents import router as documents_router
from app.api.search import router as search_router

router = APIRouter()
router.include_router(documents_router, tags=["documents"])
router.include_router(search_router, tags=["retrieval"])
