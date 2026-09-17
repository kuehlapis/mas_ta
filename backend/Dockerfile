FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir -e .

# Bake the reranker model (~3 MB) into the image so the first search doesn't download it
ARG RERANK_MODEL=ms-marco-TinyBERT-L-2-v2
ENV DOCQA_RERANK_CACHE_DIR=/opt/flashrank
RUN python -c "from flashrank import Ranker; Ranker(model_name='${RERANK_MODEL}', cache_dir='/opt/flashrank')"

COPY app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
