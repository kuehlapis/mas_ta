\
from __future__ import annotations

import os
from elasticsearch import Elasticsearch

ES_URL = os.getenv("DOCQA_ES_URL", "http://localhost:9200")
ES_INDEX = os.getenv("DOCQA_ES_INDEX", "docqa_chunks")


def es_client() -> Elasticsearch:
    return Elasticsearch(ES_URL)


def ensure_es_index() -> None:
    es = es_client()
    if es.indices.exists(index=ES_INDEX):
        return
    es.indices.create(
        index=ES_INDEX,
        mappings={
            "properties": {
                "doc_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "ord": {"type": "integer"},
                "text": {"type": "text"},
            }
        },
    )
