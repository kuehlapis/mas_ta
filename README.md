# Mini Doc Q&A with Elasticsearch + Redis Vector

Upload documents, ingest them (chunk + embed + index), then search (keyword / semantic / hybrid) or ask questions with cited answers.

- Keyword retrieval: **Elasticsearch (BM25)**
- Semantic retrieval: **Redis Stack (RediSearch vectors)**
- Embeddings are the starter's deterministic hash embeddings (no API keys required)

## Run everything

```bash
docker compose up --build
```

- Frontend: http://localhost:5173 (Upload & Ingest, Search, Ask)
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

See `.env.example`. Besides connection settings it holds the ranking settings (`DOCQA_RRF_*`, `DOCQA_RERANK_*`).

---

## Notes

### Chunking choice

1. **PDF → Markdown per page** with PyMuPDF4LLM. It keeps reading order, headings and tables, and each chunk remembers its page number for citations.
2. **Split at headings** with `MarkdownHeaderTextSplitter`, so each chunk covers one section.
3. **Merge tiny sections** (< 200 chars, usually a lone heading) into the next section.
4. **Cap size** at 1,500 chars with 150 chars overlap using `RecursiveCharacterTextSplitter`. Only long sections are split.
5. **Prefix each chunk with `[page title > section]`**, so a piece from the middle of a section still carries its topic.

**Why both splitters:** each fixes the other's weakness.

|                            | Header splitter only | Recursive splitter only | Both |
| -------------------------- | -------------------- | ----------------------- | ---- |
| Cuts at section boundaries | ✅                   | ❌ can cut mid-section  | ✅   |
| Chunk knows its heading    | ✅                   | ❌                      | ✅   |
| Size limit                 | ❌ up to 3,308 chars | ✅                      | ✅   |

The report is organised by page and section (one case study per page), so section-based chunks keep a fact together with its context. The 27-page PDF becomes 62 chunks.

### How the hybrid merge works

1. **Retrieve** the top 30 chunks from Elasticsearch (BM25 on the original text plus an English-stemmed copy) and the top 30 from Redis (vector KNN).
2. **Fuse with Reciprocal Rank Fusion (RRF):** each chunk gets `1 / (60 + rank)` from each list it appears in, and the scores are summed. Ranks are used instead of raw scores because BM25 scores and cosine similarity are on different scales.
3. **Rerank** the top 20 fused chunks, plus each retriever's own top 5, with a cross-encoder (FlashRank `ms-marco-TinyBERT-L-2-v2`, local, no API key). It reads the question and chunk together and returns the final order. Adding each retriever's top 5 ensures a chunk ranked 1st by only one retriever isn't lost during fusion.

**Ask** takes the top 6 chunks and returns the passage (1–3 consecutive sentences) that best covers the question's terms, quoted verbatim. The citation is the chunk that passage came from, and the API checks that every `[n]` exists and every quote appears in its snippet. Sentences that look like prompt injection are dropped and redacted. If nothing matches well enough, it answers "I don't know".

### What I would improve next

- **Real embeddings** (e.g. `bge-small-en-v1.5`). The hash embeddings only match shared words, so semantic search finds the right page 8/12 times.
- **Contextual chunks with a local LLM**, following Anthropic's [Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval). At ingest, a local model (e.g. via Ollama) reads the whole document and writes a short summary of where each chunk fits ("This chunk is from the SAFS case on AML/CFT breaches; it describes the penalty imposed"). That summary is prepended to the chunk before BM25 indexing and embedding. The current `[page title > section]` prefix is a lightweight version of this; LLM context would also resolve references like "He was sentenced…" to the person they refer to.
- **Generated answers with grounding checks.** Verbatim extraction is safe but can read awkwardly, and it misses answers worded differently from the question ("fined" vs "composition penalty"). An LLM could write the answer, with every cited fact verified against the snippet.
- **Drop label-only chunks** at ingest. Infographic pages (e.g. page 4: "Vision / Mission / Enforcement Approach") produce tiny chunks that outrank the real content in Search.
- **Local vision model for charts.** Page 9's chart comes out scrambled (`35 34 12 2 13 months…`) because its numbers and labels are separate text objects. PyMuPDF4LLM's layout model already marks chart regions (`page_boxes`); crop those regions and have a local vision model (e.g. via Ollama) describe them ("Criminal Prosecutions: 35 months; Civil Penalties: 34 months…"), then add the description to the page text before chunking.

* **Background ingestion** for large PDFs: return `doc_id` immediately and process in a background job with a status field. Today the server stays responsive, but the upload request waits for conversion (~15 s for 27 pages).
* **Cache `/search` and `/ask` responses in Redis**, keyed by the normalised question, mode, `top_k` and an index version that every ingest bumps (so documents changing never serve stale answers). Add semantic caching (reuse answers for near-identical questions via vector similarity) once real embeddings are in place. Most useful if LLM-generated answers are added.
* **Stream large PDFs** with generators (`yield`): convert page by page, yield chunks instead of building lists, and index in batches (`helpers.bulk` accepts generators; flush the Redis pipeline every few hundred writes). This keeps memory flat for documents with thousands of pages.
