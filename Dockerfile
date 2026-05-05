FROM python:3.11-slim

WORKDIR /app

# Install dependencies before copying source code to leverage Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the packages needed at runtime
COPY extraction/ ./extraction/
COPY scripts/load_incremental.py ./scripts/load_incremental.py

# GCP_PROJECT_ID and BQ_DATASET must be injected at runtime via --env or Cloud Run config
ENV PYTHONPATH=/app

CMD ["python", "scripts/load_incremental.py"]
