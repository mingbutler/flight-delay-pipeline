from airflow.sdk import dag, task, Asset

live_raw_asset = Asset("gcs://flight-delay-raw/raw/live/")

@dag(
    schedule=[live_raw_asset], # triggers when new live data lands in GCS
    catchup=False,
    tags=["mart", "asset-triggered", "live"]
)
def mart_flights_triggered_by_live():
    @task.bash
    def dbt_run_mart():
        return "cd /opt/dbt_project && dbt deps && dbt run --select stg_bts_ontime+ stg_live_flights+ --target prod"
    
    @task.bash
    def dbt_test_mart():
        return "cd /opt/dbt_project && dbt test --select stg_bts_ontime+ stg_live_flights+"
    
    dbt_run_mart() >> dbt_test_mart() # pyright: ignore [reportUnusedExpression]
    
mart_flights_triggered_by_live()