import logging
from datetime import date
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger(__name__)

# Destination table coordinates
DATASET_ID = "raw"
TABLE_ID = "raw_bcra_variables"

# Schema mirrors the record format produced by BCRAExtractor
TABLE_SCHEMA = [
    bigquery.SchemaField("fecha",           "DATE",    mode="REQUIRED"),
    bigquery.SchemaField("id_variable",     "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("nombre_variable", "STRING",  mode="REQUIRED"),
    bigquery.SchemaField("valor",           "FLOAT",   mode="REQUIRED"),
]


class BigQueryLoader:
    """Loads BCRA variable records into BigQuery table {dataset}.raw_bcra_variables."""

    def __init__(self, project_id: str, dataset_id: str = DATASET_ID):
        # Initialize the BigQuery client; dataset_id defaults to module-level constant
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = bigquery.Client(project=project_id)
        self.table_ref = f"{project_id}.{dataset_id}.{TABLE_ID}"

    # -------------------------------------------------------------------------
    # Public methods
    # -------------------------------------------------------------------------

    def load_initial(self, records: list[dict]) -> int:
        """Truncate the destination table and load all records from scratch.

        Use this for the first historical load or a full refresh.
        Returns the number of rows written.
        """
        if not records:
            logger.warning("load_initial called with empty records list — skipping.")
            return 0

        self._ensure_table_exists()

        job_config = bigquery.LoadJobConfig(
            schema=TABLE_SCHEMA,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        rows_written = self._run_load_job(records, job_config)
        logger.info("Initial load complete: %d rows written to %s", rows_written, self.table_ref)
        return rows_written

    def load_incremental(self, records: list[dict]) -> int:
        """Append only records whose (fecha, id_variable) pair is not yet in the table.

        Safe to call repeatedly; already-loaded records are filtered out before insert.
        Returns the number of new rows written.
        """
        if not records:
            logger.info("load_incremental called with empty records list — nothing to do.")
            return 0

        self._ensure_table_exists()

        existing_keys = self._fetch_existing_keys(records)
        new_records = [
            r for r in records
            if (r["fecha"], r["id_variable"]) not in existing_keys
        ]

        if not new_records:
            logger.info("No new records to insert — all %d records already exist.", len(records))
            return 0

        job_config = bigquery.LoadJobConfig(
            schema=TABLE_SCHEMA,
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        rows_written = self._run_load_job(new_records, job_config)
        logger.info(
            "Incremental load complete: %d new rows written (%d duplicates skipped).",
            rows_written,
            len(records) - len(new_records),
        )
        return rows_written

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _ensure_table_exists(self) -> None:
        """Create the destination table if it does not already exist."""
        dataset_ref = self.client.dataset(self.dataset_id)

        # Create dataset if missing (no-op if it already exists)
        try:
            self.client.get_dataset(dataset_ref)
        except GoogleAPIError:
            self.client.create_dataset(bigquery.Dataset(dataset_ref))
            logger.info("Created dataset %s.%s", self.project_id, self.dataset_id)

        table = bigquery.Table(self.table_ref, schema=TABLE_SCHEMA)
        try:
            self.client.get_table(table)
        except GoogleAPIError:
            self.client.create_table(table)
            logger.info("Created table %s", self.table_ref)

    def _fetch_existing_keys(self, records: list[dict]) -> set[tuple]:
        """Query BQ for (fecha, id_variable) pairs that already exist in the table.

        Restricts the query to the date range present in the incoming records
        to avoid scanning the full table unnecessarily.
        """
        dates = [r["fecha"] for r in records]
        date_from = min(dates)
        date_to = max(dates)

        query = f"""
            SELECT DISTINCT fecha, id_variable
            FROM `{self.table_ref}`
            WHERE fecha BETWEEN @date_from AND @date_to
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("date_from", "DATE", str(date_from)),
                bigquery.ScalarQueryParameter("date_to",   "DATE", str(date_to)),
            ]
        )

        try:
            result = self.client.query(query, job_config=job_config).result()
            return {(str(row.fecha), row.id_variable) for row in result}
        except GoogleAPIError as e:
            logger.error("Failed to fetch existing keys: %s", e)
            raise BigQueryLoaderError("Could not query existing records.") from e

    def _run_load_job(self, records: list[dict], job_config: bigquery.LoadJobConfig) -> int:
        """Submit a load job and block until completion. Returns rows written."""
        normalized = [_normalize_record(r) for r in records]

        try:
            job = self.client.load_table_from_json(
                normalized, self.table_ref, job_config=job_config
            )
            job.result()  # Block until the job finishes
        except GoogleAPIError as e:
            logger.error("BigQuery load job failed: %s", e)
            raise BigQueryLoaderError("Load job failed.") from e

        return job.output_rows


def _normalize_record(record: dict) -> dict:
    """Coerce record field types to match the BigQuery schema.

    Converts fecha to ISO string if it's a date object; ensures valor is float.
    """
    return {
        "fecha":           record["fecha"].isoformat() if isinstance(record["fecha"], date) else str(record["fecha"]),
        "id_variable":     int(record["id_variable"]),
        "nombre_variable": str(record["nombre_variable"]),
        "valor":           float(record["valor"]),
    }


class BigQueryLoaderError(Exception):
    """Raised when a BigQuery operation fails unrecoverably."""
