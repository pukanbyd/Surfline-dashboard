from __future__ import annotations

import sys
from datetime import datetime, timedelta

sys.path.insert(0, "/opt/airflow/scripts")

from airflow import DAG
from airflow.operators.python import PythonOperator

from fetch_surfline import main as fetch_main
from upload_to_s3 import upload_latest_csv
from load_latest_s3_to_postgres import main as load_main


def run_fetch() -> None:
    fetch_main()


def run_upload() -> None:
    upload_latest_csv()


def run_load() -> None:
    load_main()


with DAG(
    dag_id="surfline_pipeline",
    default_args={
        "owner": "airflow",
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    description="Fetch Surfline wave forecast, upload CSV, and load the latest data into warehouse",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["surfline", "etl"],
) as dag:
    fetch_task = PythonOperator(
        task_id="fetch_surfline_data",
        python_callable=run_fetch,
    )

    upload_task = PythonOperator(
        task_id="upload_to_s3",
        python_callable=run_upload,
    )

    load_task = PythonOperator(
        task_id="load_to_postgres",
        python_callable=run_load,
    )

    fetch_task >> upload_task >> load_task
