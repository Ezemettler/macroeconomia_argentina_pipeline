# macroeconomia_argentina_pipeline

Pipeline ELT end-to-end que extrae datos monetarios y macroeconómicos de la API pública del Banco Central de la República Argentina (BCRA), los carga en BigQuery, los transforma con dbt y los visualiza en Looker Studio.

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-GCP-blue?logo=google-cloud&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.11-orange?logo=dbt&logoColor=white)
![Looker Studio](https://img.shields.io/badge/Looker_Studio-Dashboard-green?logo=google&logoColor=white)
![GCP](https://img.shields.io/badge/GCP-Cloud_Run-blue?logo=google-cloud&logoColor=white)

---

## Qué hace este proyecto

Este pipeline automatiza la recolección y el análisis de los principales indicadores macroeconómicos de Argentina:

1. **Extracción** — Un script Python consulta la API REST pública del BCRA y obtiene observaciones diarias para 9 variables monetarias, con manejo automático de paginación y reintentos.
2. **Carga** — Los registros se cargan en una tabla raw de BigQuery. Un loader incremental garantiza que cada ejecución diaria solo agregue datos nuevos.
3. **Transformación** — Los modelos dbt limpian los datos crudos, calculan valores de cierre mensual, pivotean las variables en una tabla analítica y la enriquecen con contexto político (períodos de gobierno y eventos económicos clave).
4. **Visualización** — El mart final se conecta a un dashboard de Looker Studio para análisis de series de tiempo y exploración interactiva.

---

## Arquitectura

```
API Pública del BCRA
        │
        │  HTTP (Python / requests)
        ▼
extraction/bcra/extractor.py
        │
        │  google-cloud-bigquery
        ▼
BigQuery: raw.raw_bcra_variables         ← carga histórica diaria
        │
        │  dbt
        ▼
BigQuery: staging.stg_bcra_variables     ← datos limpios, tipados, sin nulos
        │
        │  dbt
        ▼
BigQuery: analytics.mart_variables_mensual   ← valor de cierre mensual por variable
        │
        │  dbt
        ▼
BigQuery: analytics.mart_variables_pivot     ← tabla wide, enriquecida con
        │                                       gobiernos y eventos políticos
        │
        ▼
Dashboard en Looker Studio
```

---

## Variables analizadas

| Variable | Descripción |
|---|---|
| `reservas_internacionales` | Reservas internacionales del BCRA (millones de USD) |
| `tipo_cambio_minorista` | Tipo de cambio minorista (promedio vendedor, ARS/USD) |
| `tasa_prestamos_personales` | Tasa de interés de préstamos personales (%) |
| `base_monetaria` | Base monetaria total en circulación (millones de ARS) |
| `variacion_m2_privado` | Variación interanual del promedio móvil de 30 días del M2 privado (%) |
| `prestamos_sector_privado` | Préstamos totales otorgados al sector privado (millones de ARS) |
| `inflacion_mensual` | Variación mensual del IPC informada por INDEC (%) |
| `inflacion_interanual` | Variación interanual del IPC (%) |
| `uva` | Índice UVA — unidad de ajuste por inflación para créditos hipotecarios (base 31-03-2016 = 14,05) |

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Extracción y carga | Python 3.10, `requests`, `google-cloud-bigquery` |
| Data warehouse | Google BigQuery |
| Transformación | dbt 1.11 (dbt-bigquery) |
| Orquestación | Cloud Run + Cloud Scheduler |
| Visualización | Looker Studio |
| CI/CD | GitHub Actions *(próximamente)* |
| Autenticación | Google Application Default Credentials (OAuth) |

---

## Cómo correr el proyecto localmente

### 1. Clonar e instalar dependencias

```bash
git clone git@github.com:Ezemettler/macroeconomia_argentina_pipeline.git
cd macroeconomia_argentina_pipeline
pip install requests google-cloud-bigquery
pip install dbt-bigquery
```

### 2. Configurar credenciales de GCP

```bash
gcloud auth application-default login
gcloud config set project TU_GCP_PROJECT_ID
gcloud auth application-default set-quota-project TU_GCP_PROJECT_ID
```

### 3. Configurar variables de entorno

```bash
export GCP_PROJECT_ID=tu-proyecto-gcp
export BQ_DATASET=raw
```

### 4. Correr la carga histórica

Extrae las 9 variables desde 2003-01-01 hasta hoy y las carga en BigQuery.

```bash
python scripts/load_historical.py
```

### 5. Correr las transformaciones dbt

```bash
cd dbt/macroeconomia_argentina_pipeline
dbt seed        # carga la tabla de referencia de eventos políticos
dbt run         # construye todos los modelos
dbt test        # ejecuta los tests de calidad de datos
```

---

## Dashboard

[Ver el dashboard en Looker Studio](#) *(link próximamente)*

---

## Autor

**Ezequiel Mettler**
[github.com/Ezemettler](https://github.com/Ezemettler)
