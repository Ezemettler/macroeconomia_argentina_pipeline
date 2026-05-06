FROM python:3.11-slim

WORKDIR /app

# Install dependencies before copying source code to leverage Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy runtime code
COPY extraction/                            ./extraction/
COPY scripts/load_incremental.py           ./scripts/load_incremental.py
COPY dbt/macroeconomia_argentina_pipeline/ ./dbt/macroeconomia_argentina_pipeline/

# Copy dbt connection profile — dbt/profiles.yml is git-ignored and never committed
COPY dbt/profiles.yml                      /root/.dbt/profiles.yml

# Required env vars (injected at runtime via --env or Cloud Run config):
#   GCP_PROJECT_ID — GCP project for BigQuery
#   BQ_DATASET     — target BigQuery dataset
ENV PYTHONPATH=/app

CMD ["python", "scripts/load_incremental.py"]
