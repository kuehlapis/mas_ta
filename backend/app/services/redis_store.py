\
from __future__ import annotations

import os
import redis
from redis.commands.search.field import NumericField, TextField, TagField, VectorField
try:
    from redis.commands.search.index_definition import IndexDefinition, IndexType
except ImportError:
    from redis.commands.search.indexDefinition import IndexDefinition, IndexType

REDIS_URL = os.getenv("DOCQA_REDIS_URL", "redis://localhost:6379/0")
REDIS_INDEX = os.getenv("DOCQA_REDIS_INDEX", "idx:docqa_chunks")
REDIS_PREFIX = os.getenv("DOCQA_REDIS_PREFIX", "docqa:chunk:")
EMBED_DIM = 384


def redis_client() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=False)


def ensure_redis_index() -> None:
    r = redis_client()
    try:
        info = r.ft(REDIS_INDEX).info()
    except Exception:
        info = None

    if info is not None:
        # migrate indexes created before page tracking
        existing = {str(a[1], "utf-8") if isinstance(a[1], bytes) else str(a[1]) for a in info["attributes"]}
        for field in (NumericField("page"), TagField("filename")):
            if field.name not in existing:
                r.ft(REDIS_INDEX).alter_schema_add(field)
        return

    schema = (
        TagField("doc_id"),
        TagField("chunk_id"),
        TagField("filename"),
        NumericField("page"),
        TextField("text"),
        VectorField(
            "embedding",
            "FLAT",
            {"TYPE": "FLOAT32", "DIM": EMBED_DIM, "DISTANCE_METRIC": "COSINE"},
        ),
    )
    definition = IndexDefinition(prefix=[REDIS_PREFIX], index_type=IndexType.HASH)
    r.ft(REDIS_INDEX).create_index(schema, definition=definition)
