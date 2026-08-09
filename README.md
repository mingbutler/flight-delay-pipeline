# Flight Delay Pipeline

Airflow-orchestrated pipeline: ingest BTS historical + AeroDataBox live flight data to GCS, transform with dbt on BigQuery.

## Architecture

- **Ingestion** (Python): `ingestion/download_bts_data.py`, `ingestion/fetch_live_flights.py`
- **Orchestration** (Airflow): `airflow/dags/`
- **Transform** (dbt + BigQuery): `dbt_project/`

## Prerequisites

1. Docker Desktop (or Docker Engine + Compose v2)
2. GCP project with BigQuery dataset and GCS bucket
3. Service account JSON with GCS write + BigQuery permissions
4. BigQuery external tables — see `infra/bigquery_external_tables.sql`
5. AeroDataBox API key (for live flights DAG)

## Local setup

```bash
# 1. Secrets and config (not committed)
mkdir -p secrets docker/dbt
cp /path/to/service-account.json secrets/gcp-service-account.json
cp docker/dbt/profiles.yml.example docker/dbt/profiles.yml
# Edit docker/dbt/profiles.yml with your GCP project + dataset

cp .env.example .env
# Set AIRFLOW__CORE__FERNET_KEY and AIRFLOW_UID (run: id -u)

# 2. Initialize and start Airflow
docker compose up airflow-init
docker compose up -d

# 3. Set API key for live flights DAG
docker compose exec airflow-webserver \
  airflow variables set AERODATABOX_API_KEY "your-key"

# 4. Open UI
open http://localhost:8080   # login: airflow / airflow (from .env)

