# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RUNBOOKRAG_INDEX=/app/build/index.json \
    RUNBOOKRAG_DB=/app/data/runbookrag.db

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY runbookrag ./runbookrag
COPY api ./api
COPY frontend ./frontend
COPY corpus ./corpus
COPY eval ./eval
COPY scripts ./scripts

# Build the index and evaluation report at image build time so start-up is instant.
RUN python -m runbookrag build --corpus corpus --out build/index.json \
 && python scripts/evaluate.py > /dev/null \
 && useradd --create-home --uid 10001 app && mkdir -p /app/data && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
