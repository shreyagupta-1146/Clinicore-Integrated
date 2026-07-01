# apps/clinicore/backend/Dockerfile
# Build context is the repo root (see docker-compose.yml: context: .)
# so this image can COPY in substrate/ and ai_services/ alongside the app.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY apps/clinicore/backend/requirements.txt /app/apps/clinicore/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/clinicore/backend/requirements.txt \
    && python -m spacy download en_core_web_lg

COPY substrate /app/substrate
COPY ai_services /app/ai_services
COPY apps/clinicore/backend /app/apps/clinicore/backend

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/healthz || exit 1

CMD ["uvicorn", "apps.clinicore.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
