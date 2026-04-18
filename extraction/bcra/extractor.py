import time
import logging
import requests

logger = logging.getLogger(__name__)

# Base URL for BCRA monetary statistics API
BASE_URL = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"

# Variables to extract: maps idVariable → descriptive name
VARIABLES = {
    1:  "reservas_internacionales",
    4:  "tipo_cambio_minorista",
    14: "tasa_prestamos_personales",
    15: "base_monetaria",
    25: "variacion_m2_privado",
    26: "prestamos_sector_privado",
    27: "inflacion_mensual",
    28: "inflacion_interanual",
    31: "uva",
}

# API pagination limit per request
PAGE_SIZE = 1000

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT = 15


class BCRAExtractor:
    """Extracts monetary statistics from the BCRA public API."""

    def __init__(self, variables: dict[int, str] = VARIABLES):
        # Allow injecting a custom variable map for flexibility and testing
        self.variables = variables

    def extract_variable(
        self, variable_id: int, date_from: str, date_to: str
    ) -> list[dict]:
        """Fetch all records for a single variable between two dates (YYYY-MM-DD).

        Handles pagination automatically if total results exceed PAGE_SIZE.
        Returns a flat list of dicts with fecha, id_variable, nombre_variable, valor.
        """
        variable_name = self.variables.get(variable_id, f"variable_{variable_id}")
        all_records: list[dict] = []
        offset = 0

        while True:
            page = self._fetch_page(variable_id, date_from, date_to, offset)
            records = self._parse_page(page, variable_id, variable_name)
            all_records.extend(records)

            # Stop when we've retrieved all available records
            total_count = page["metadata"]["resultset"]["count"]
            offset += PAGE_SIZE
            if offset >= total_count:
                break

        logger.info(
            "Extracted %d records for variable %d (%s)",
            len(all_records),
            variable_id,
            variable_name,
        )
        return all_records

    def extract_all(self, date_from: str, date_to: str) -> list[dict]:
        """Fetch records for all configured variables between two dates (YYYY-MM-DD).

        Returns a single flat list combining results from every variable.
        """
        combined_records: list[dict] = []

        for variable_id in self.variables:
            try:
                records = self.extract_variable(variable_id, date_from, date_to)
                combined_records.extend(records)
            except BCRAAPIError as e:
                # Log the failure but continue extracting remaining variables
                logger.error(
                    "Failed to extract variable %d after retries: %s", variable_id, e
                )

        logger.info(
            "Total records extracted across all variables: %d", len(combined_records)
        )
        return combined_records

    def _fetch_page(
        self, variable_id: int, date_from: str, date_to: str, offset: int
    ) -> dict:
        """Request a single page from the API with retry logic on transient errors."""
        url = f"{BASE_URL}/{variable_id}"
        params = {
            "desde": date_from,
            "hasta": date_to,
            "offset": offset,
            "limit": PAGE_SIZE,
        }

        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.json()

            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(
                    "Timeout on attempt %d/%d for variable %d",
                    attempt, MAX_RETRIES, variable_id,
                )

            except requests.exceptions.HTTPError as e:
                # 4xx errors are client-side and won't be fixed by retrying
                if response.status_code < 500:
                    raise BCRAAPIError(
                        f"HTTP {response.status_code} for variable {variable_id}: {e}"
                    ) from e
                last_error = e
                logger.warning(
                    "Server error %d on attempt %d/%d for variable %d",
                    response.status_code, attempt, MAX_RETRIES, variable_id,
                )

            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(
                    "Connection error on attempt %d/%d for variable %d: %s",
                    attempt, MAX_RETRIES, variable_id, e,
                )

            # Exponential backoff before next retry
            if attempt < MAX_RETRIES:
                sleep_seconds = RETRY_BACKOFF_SECONDS ** attempt
                logger.info("Retrying in %ds...", sleep_seconds)
                time.sleep(sleep_seconds)

        raise BCRAAPIError(
            f"All {MAX_RETRIES} attempts failed for variable {variable_id}"
        ) from last_error

    def _parse_page(
        self, page: dict, variable_id: int, variable_name: str
    ) -> list[dict]:
        """Convert raw API response into a flat list of normalized record dicts."""
        records = []

        # API wraps results in a list with one element per idVariable
        for result in page.get("results", []):
            for entry in result.get("detalle", []):
                records.append(
                    {
                        "fecha": entry["fecha"],
                        "id_variable": variable_id,
                        "nombre_variable": variable_name,
                        "valor": entry["valor"],
                    }
                )

        return records


class BCRAAPIError(Exception):
    """Raised when the BCRA API fails after exhausting all retry attempts."""
