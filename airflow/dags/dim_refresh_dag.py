from airflow.sdk import dag, task, Asset

# manual trigger only
@dag(
    schedule=None,  
    catchup=False,
    tags=["dims", "reference-data"]
)
def dim_refresh_dag():
    @task.bash
    def dbt_seed():
        return "cd /opt/dbt_project && dbt seed --target prod"

    @task.bash
    def dbt_run_dims():
        return "cd /opt/dbt_project && dbt run --select dim_date dim_carrier dim_airports --target prod"

    @task.bash
    def dbt_test_dims():
        return "cd /opt/dbt_project && dbt test --select dim_date dim_carrier dim_airports"

    dbt_seed() >> dbt_run_dims() >> dbt_test_dims()  # pyright: ignore [reportUnusedExpression]

dim_refresh_dag()