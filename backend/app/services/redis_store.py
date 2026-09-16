\
from __future__ import annotations

import os
import redis
from redis.commands.search.field import TextField, TagField, VectorField
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
        r.ft(REDIS_INDEX).info()
        return
    except Exception:
        pass

    schema = (
        TagField("doc_id"),
        TagField("chunk_id"),
        TextField("text"),
        VectorField(
            "embedding",
            "FLAT",
            {"TYPE": "FLOAT32", "DIM": EMBED_DIM, "DISTANCE_METRIC": "COSINE"},
        ),
    )
    definition = IndexDefinition(prefix=[REDIS_PREFIX], index_type=IndexType.HASH)
    r.ft(REDIS_INDEX).create_index(schema, definition=definition)
