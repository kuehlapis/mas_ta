# Junior Take-home (Variant): Mini Doc Q&A with Elasticsearch + Redis Vector

This variant **requires**:
- Elasticsearch for keyword (BM25) retrieval
- Redis Stack (RediSearch) for vector (semantic) retrieval

The starter uses deterministic embeddings (no API keys required) so candidates can focus on integration and ranking.

## Run everything
```bash
docker compose up --build
```

Then open:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000/docs

## Seed dataset
With services running:
```bash
python tools/seed_dataset.py
```

## Services
- Elasticsearch: http://localhost:9200
- Redis Stack: http://localhost:6379 (RedisInsight: http://localhost:8001)

## Environment
See `.env.example`.
