import os
import sys
from datetime import datetime, timedelta

from airflow.providers.standard.operators.python import PythonOperator
from airflow.sdk import DAG, BaseHook

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "scripts"))

from extract import extract  # noqa: E402
from load import load  # noqa: E402
from transform import transform  # noqa: E402
from validate import validate  # noqa: E402

ES_CONNECTION_ID = "elasticsearch_default"


def run_extract():
    return extract()


def run_transform():
    return transform()


def run_validate():
    return validate()


def run_load(ti):
    counts = ti.xcom_pull(task_ids="validate")
    connection = BaseHook.get_connection(ES_CONNECTION_ID)
    es_url = f"http://{connection.host}:{connection.port}"
    loaded = load(es_url=es_url)
    return {"validated": counts, "loaded": loaded}


default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="etl_ecommerce",
    description="Extraction, transformation, validation et chargement des données e-commerce",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["ecommerce", "etl"],
) as dag:
    extract_task = PythonOperator(task_id="extract", python_callable=run_extract)
    transform_task = PythonOperator(task_id="transform", python_callable=run_transform)
    validate_task = PythonOperator(task_id="validate", python_callable=run_validate)
    load_task = PythonOperator(task_id="load", python_callable=run_load)

    extract_task >> transform_task >> validate_task >> load_task
