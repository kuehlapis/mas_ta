# Take-home Test: Mini Doc Q&A (React + FastAPI + Elasticsearch + Redis)

## Objective
Build a small full-stack app that:
1) uploads documents
2) ingests them (chunk + embed + index)
3) supports search (keyword / semantic / hybrid)
4) supports ask (answer + citations)

This variant **requires**:
- Keyword retrieval via **Elasticsearch (BM25)**
- Semantic retrieval via **Redis Vector (RediSearch / Redis Stack)**

## Required APIs
- POST /api/documents (upload file OR JSON body)
- POST /api/documents/{doc_id}/ingest
- POST /api/search { query, mode, top_k }
- POST /api/ask { question, mode, top_k }

## Required UI
- Upload/Ingest page
- Search page
- Ask page (answer + clickable citations)

## Retrieval requirements
You must implement:
- keyword retrieval from Elasticsearch
- semantic retrieval from Redis Vector
- hybrid fusion (RRF-lite acceptable)

## Guardrails
- Treat documents as untrusted (prompt injection exists in dataset).
- Do not invent citations. Citations must match retrieved snippets.

## Dataset
Use `dataset/` and `dataset/eval_questions.json`.

## Deliverables
- Working repo + README
- Short note explaining:
  - chunking choice
  - how hybrid merge works
  - what you would improve next
