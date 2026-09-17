\
from __future__ import annotations

import os
from elasticsearch import Elasticsearch

ES_URL = os.getenv("DOCQA_ES_URL", "http://localhost:9200")
ES_INDEX = os.getenv("DOCQA_ES_INDEX", "docqa_chunks")


def es_client() -> Elasticsearch:
    return Elasticsearch(ES_URL)


ES_PROPERTIES = {
    "doc_id": {"type": "keyword"},
    "chunk_id": {"type": "keyword"},
    "filename": {"type": "keyword"},
    "ord": {"type": "integer"},
    "page": {"type": "integer"},
    "text": {"type": "text"},
}


def ensure_es_index() -> None:
    es = es_client()
    if es.indices.exists(index=ES_INDEX):
        # adding new fields to an existing mapping is allowed
        es.indices.put_mapping(index=ES_INDEX, properties=ES_PROPERTIES)
        return
    es.indices.create(index=ES_INDEX, mappings={"properties": ES_PROPERTIES})
