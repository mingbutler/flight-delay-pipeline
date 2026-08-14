from airflow.sdk import dag, task, Asset
from datetime import datetime

from ingestion.download_bts_data import run

bts_raw_asset = Asset("gcs://flight-delay-raw/raw/bts/")

@dag(
    schedule="0 8 1 * *", # 8 am UTC on the 1st day of every month 
    start_date=datetime(2026, 8, 1), 
    catchup=False,
    tags=["bts", "monthly"]
)
def bts_monthly_dag():
    @task(outlets=[bts_raw_asset])
    def download_bts():
        run()
    
    @task.bash
    def dbt_run_bts():
        return "cd /opt/dbt_project && dbt run --select stg_bts_ontime --target prod"
    
    @task.bash
    def dbt_test_bts():
        return "cd /opt/dbt_project && dbt test --select stg_bts_ontime"

    download_bts() >> dbt_run_bts() >> dbt_test_bts() # pyright: ignore [reportUnusedExpression]

bts_monthly_dag()
