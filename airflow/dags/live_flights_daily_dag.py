from airflow.sdk import dag, task, Asset
from datetime import datetime, timedelta

from ingestion.fetch_live_flights import run

live_raw_asset = Asset("gcs://flight-delay-raw/raw/live/")

@dag(
    schedule="0 6 * * *", # 6 AM UTC daily
    start_date=datetime(2026, 8, 13),
    catchup=False,
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["live", "aerodatabox"]
)
def live_flights_daily_dag():
    @task(outlets=[live_raw_asset])
    def fetch_flights(ds=None):
        run(date_str=ds, airports=['ATL'])
        
    @task.bash
    def dbt_run_live():
        return "cd /opt/dbt_project && dbt deps && dbt run --select stg_live_flights --target prod"
    
    @task.bash
    def dbt_test_live():
        return "cd /opt/dbt_project && dbt test --select stg_live_flights"
    
    fetch_flights() >> dbt_run_live() >> dbt_test_live() # pyright: ignore [reportUnusedExpression]
    
live_flights_daily_dag()