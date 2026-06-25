from datetime import date
from typing import Protocol

from prefect import get_run_logger, task

from core.supabase import get_supabase
from logger import forward_logs


DATALAKE_PATH_TEMPLATE = (
    "retailer={retailer}/"
    "store_external_id={store_external_id}/"
    "year={year}/"
    "month={month}/"
    "day={day}/"
    "{page_name}.html"
)


class StoreConf(Protocol):
    retailer: str
    external_id: str


@task
@forward_logs
def upload_html_to_datalake(conf: StoreConf, html_content: str, page_name: str) -> str:
    logger = get_run_logger()
    supabase = get_supabase()

    today = date.today()
    path = DATALAKE_PATH_TEMPLATE.format(
        retailer=conf.retailer,
        store_external_id=conf.external_id,
        year=today.year,
        month=today.strftime("%m"),
        day=today.strftime("%d"),
        page_name=page_name,
    )

    logger.info(f"Uploading {page_name} to Supabase path: {path}")

    supabase.storage.from_("raw_offers").upload(
        path,
        html_content.encode("utf-8"),
        file_options={
            "content-type": "text/html",
            "upsert": "true",
        },
    )
    return path
