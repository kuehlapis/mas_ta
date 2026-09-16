\
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.services.store import init_db
from app.services.es_store import ensure_es_index
from app.services.redis_store import ensure_redis_index
from app.api.router import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Mini Doc Q&A (ES+Redis)", version="0.2.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_db()
    ensure_es_index()
    ensure_redis_index()

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
