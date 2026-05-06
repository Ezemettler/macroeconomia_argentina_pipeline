"""
Incremental load script — intended to run once a week.

Extracts the last LOOKBACK_DAYS days of data from the BCRA API for all
variables, appends only new records to BigQuery, then triggers dbt run
to refresh all downstream models.

Required environment variables:
  GCP_PROJECT_ID    — GCP project that owns the BigQuery dataset
  BQ_DATASET        — BigQuery dataset name (e.g. 'raw')
  DBT_PROFILES_DIR  — directory containing profiles.yml (default: ~/.dbt)

Usage:
  export GCP_PROJECT_ID=my-gcp-project
  export BQ_DATASET=raw
  export DBT_PROFILES_DIR=~/.dbt
  python scripts/load_incremental.py
"""

import logging
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from extraction.bcra.extractor import BCRAExtractor, BCRAAPIError, VARIABLES
from extraction.bigquery.loader import BigQueryLoader, BigQueryLoaderError

# Days to look back on each run — wide enough to cover any API publication lag
LOOKBACK_DAYS = 30

# Path to the dbt project relative to the repo root
DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt" / "macroeconomia_argentina_pipeline"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def read_env_vars() -> tuple[str, str, str]:
    """Read and validate required environment variables. Exit on missing values."""
    project_id   = os.environ.get("GCP_PROJECT_ID")
    dataset_id   = os.environ.get("BQ_DATASET")
    profiles_dir = os.environ.get("DBT_PROFILES_DIR", str(Path.home() / ".dbt"))

    missing = [name for name, val in [("GCP_PROJECT_ID", project_id), ("BQ_DATASET", dataset_id)] if not val]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)

    return project_id, dataset_id, profiles_dir


def extract_all_variables(extractor: BCRAExtractor, date_from: str, date_to: str) -> list[dict]:
    """Extract each variable individually to report per-variable progress."""
    all_records: list[dict] = []

    for variable_id, variable_name in VARIABLES.items():
        logger.info(
            "Extracting variable %d (%s) from %s to %s ...",
            variable_id, variable_name, date_from, date_to,
        )
        try:
            records = extractor.extract_variable(variable_id, date_from, date_to)
            all_records.extend(records)
            logger.info("  -> %d records extracted.", len(records))
        except BCRAAPIError as e:
            logger.error("  -> Failed to extract variable %d: %s", variable_id, e)

    return all_records


def run_dbt(profiles_dir: str) -> None:
    """Trigger dbt run for all models. Exits with error if dbt fails."""
    logger.info("Step 3/3: Running dbt models ...")
    logger.info("  dbt project : %s", DBT_PROJECT_DIR)
    logger.info("  profiles dir: %s", profiles_dir)

    result = subprocess.run(
        [
            "dbt", "run",
            "--project-dir", str(DBT_PROJECT_DIR),
            "--profiles-dir", profiles_dir,
        ],
        capture_output=False,  # stream dbt output directly to console
    )

    if result.returncode != 0:
        logger.error("dbt run failed with exit code %d.", result.returncode)
        sys.exit(result.returncode)

    logger.info("dbt run completed successfully.")


def main() -> None:
    """Orchestrate the incremental extraction, BigQuery load, and dbt refresh."""
    project_id, dataset_id, profiles_dir = read_env_vars()
    date_to   = date.today()
    date_from = date_to - timedelta(days=LOOKBACK_DAYS)

    logger.info("=" * 60)
    logger.info("Incremental load — BCRA monetary variables")
    logger.info("Project  : %s", project_id)
    logger.info("Dataset  : %s", dataset_id)
    logger.info("Period   : %s  →  %s", date_from.isoformat(), date_to.isoformat())
    logger.info("Variables: %d", len(VARIABLES))
    logger.info("=" * 60)

    # --- Step 1: Extraction -------------------------------------------------
    logger.info("Step 1/3: Extracting data from BCRA API ...")
    extractor = BCRAExtractor()
    records = extract_all_variables(extractor, date_from.isoformat(), date_to.isoformat())

    if not records:
        logger.warning("No records extracted from the API. Nothing to load.")
        sys.exit(0)

    logger.info("Extraction complete. Total records: %d", len(records))

    # --- Step 2: Load -------------------------------------------------------
    logger.info("Step 2/3: Running incremental load into BigQuery (%s) ...", dataset_id)
    loader = BigQueryLoader(project_id=project_id, dataset_id=dataset_id)

    try:
        rows_written = loader.load_incremental(records)
    except BigQueryLoaderError as e:
        logger.error("Load failed: %s", e)
        sys.exit(1)

    logger.info("Incremental load complete. New rows written: %d", rows_written)

    # --- Step 3: dbt run ----------------------------------------------------
    run_dbt(profiles_dir)

    logger.info("=" * 60)
    logger.info("Pipeline complete.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
