# macroeconomia_argentina_pipeline

An end-to-end ELT pipeline that extracts monetary and macroeconomic data from Argentina's Central Bank (BCRA) public API, loads it into BigQuery, transforms it with dbt, and visualizes it in Looker Studio.

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-GCP-blue?logo=google-cloud&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.11-orange?logo=dbt&logoColor=white)
![Looker Studio](https://img.shields.io/badge/Looker_Studio-Dashboard-green?logo=google&logoColor=white)
![GCP](https://img.shields.io/badge/GCP-Cloud_Run-blue?logo=google-cloud&logoColor=white)

---

## What this project does

This pipeline automates the collection and analysis of Argentina's key macroeconomic indicators:

1. **Extract** — A Python script queries the BCRA's public REST API and retrieves daily observations for 9 monetary variables, handling pagination and retries automatically.
2. **Load** — Records are loaded into a raw BigQuery table. An incremental loader ensures each daily run only appends new data.
3. **Transform** — dbt models clean the raw data, compute monthly closing values, pivot variables into a wide analytical table, and enrich it with political context (government periods, key economic events).
4. **Visualize** — The final mart is connected to a Looker Studio dashboard for time series analysis and exploration.

---

## Architecture

```
BCRA Public API
      │
      │  HTTP (Python / requests)
      ▼
extraction/bcra/extractor.py
      │
      │  google-cloud-bigquery
      ▼
BigQuery: raw.raw_bcra_variables      ← daily historical load
      │
      │  dbt
      ▼
BigQuery: staging.stg_bcra_variables  ← cleaned, typed, nulls removed
      │
      │  dbt
      ▼
BigQuery: analytics.mart_variables_mensual   ← monthly closing values
      │
      │  dbt
      ▼
BigQuery: analytics.mart_variables_pivot     ← wide table, enriched with
      │                                         government periods & events
      │
      ▼
Looker Studio Dashboard
```

---

## Variables analyzed

| Variable | Description |
|---|---|
| `reservas_internacionales` | Argentina's international reserves held by the BCRA (millions USD) |
| `tipo_cambio_minorista` | Retail USD/ARS exchange rate (average sell price) |
| `tasa_prestamos_personales` | Interest rate on personal loans (%) |
| `base_monetaria` | Total monetary base in circulation (millions ARS) |
| `variacion_m2_privado` | Year-on-year change of the 30-day moving average of private M2 (%) |
| `prestamos_sector_privado` | Total loans granted to the private sector (millions ARS) |
| `inflacion_mensual` | Monthly CPI variation reported by INDEC (%) |
| `inflacion_interanual` | Year-on-year CPI variation (%) |
| `uva` | UVA index — inflation-adjustment unit used for mortgages (base 31-03-2016 = 14.05) |

---

## Tech stack

| Layer | Technology |
|---|---|
| Extraction & loading | Python 3.10, `requests`, `google-cloud-bigquery` |
| Data warehouse | Google BigQuery |
| Transformation | dbt 1.11 (dbt-bigquery) |
| Orchestration | Cloud Run + Cloud Scheduler |
| Visualization | Looker Studio |
| CI/CD | GitHub Actions *(coming soon)* |
| Auth | Google Application Default Credentials (OAuth) |

---

## Running the project locally

### 1. Clone and install dependencies

```bash
git clone git@github.com:Ezemettler/macroeconomia_argentina_pipeline.git
cd macroeconomia_argentina_pipeline
pip install requests google-cloud-bigquery
pip install dbt-bigquery
```

### 2. Configure GCP credentials

```bash
gcloud auth application-default login
gcloud config set project YOUR_GCP_PROJECT_ID
gcloud auth application-default set-quota-project YOUR_GCP_PROJECT_ID
```

### 3. Set environment variables

```bash
export GCP_PROJECT_ID=your-gcp-project-id
export BQ_DATASET=raw
```

### 4. Run the historical load

Extracts all 9 variables from 2003-01-01 to today and loads them into BigQuery.

```bash
python scripts/load_historical.py
```

### 5. Run dbt transformations

```bash
cd dbt/macroeconomia_argentina_pipeline
dbt seed        # load political events reference table
dbt run         # build all models
dbt test        # run data quality tests
```

---

## Dashboard

[View the Looker Studio dashboard](#) *(link coming soon)*

---

## Author

**Ezequiel Mettler**
[github.com/Ezemettler](https://github.com/Ezemettler)
