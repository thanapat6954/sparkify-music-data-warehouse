"""Optional Airflow 3 DAG. Mount this repo at /opt/sparkify in a prepared worker.

The worker needs requirements.txt installed, PostgreSQL reachability, PGPASSWORD,
PGHOST/PGPORT/PGUSER/PGDATABASE environment variables and the input archives.
This file does not provision or change an existing Airflow deployment.
"""
import pendulum
from airflow.sdk import dag
from airflow.providers.standard.operators.bash import BashOperator


@dag(dag_id='sparkify_dw', start_date=pendulum.datetime(2026, 1, 1, tz='UTC'),
     schedule=None, catchup=False, max_active_runs=1,
     default_args={'retries': 1}, tags=['sparkify', 'dbt', 'data-warehouse'])
def sparkify_dw():
    BashOperator(task_id='load_build_test_export',
        bash_command='python /opt/sparkify/scripts/pipeline.py --target postgres',
        append_env=True)


sparkify_dw()
