FROM python:3.11-slim

WORKDIR /app

# Install system deps for Presidio/spaCy and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/relaymed/backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model (needed by Presidio de-identifier in substrate)
RUN python -m spacy download en_core_web_lg

# Copy substrate and AI services that RelayMed depends on
COPY substrate /app/substrate
COPY ai_services /app/ai_services

# Copy RelayMed app
COPY apps/relaymed/backend /app/apps/relaymed/backend

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "apps.relaymed.backend.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
