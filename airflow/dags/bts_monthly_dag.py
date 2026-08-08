from airflow.decorators import dag, task
from datetime import datetime

from ingestion.download_bts_data import run

@dag(
    schedule="0 8 5 * *",
    start_date=datetime(2026, 8, 3),
    catchup=False,
    tags=["bts", "monthly"]
)
def bts_monthly_dag():
    @task
    def download_bts():
        run()
    
    @task.bash
    def dbt_run_bts():
        return "cd /opt/dbt_project && dbt run --select stg_bts_ontime+ --target prod"
    
    @task.bash
    def dbt_test_bts():
        return "cd /opt/dbt_project && dbt test --select stg_bts_ontime+"

    download_bts() >> dbt_run_bts() >> dbt_test_bts()

bts_monthly_dag()
