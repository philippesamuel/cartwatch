from datetime import date
from itertools import batched
from pathlib import Path

from prefect import flow, get_run_logger, task

from core.config import get_prefect_settings
from core.supabase import get_supabase
from ingestion.browser import seleniumbase_browser_context
from ingestion.offers.netto_scrapper import (
    StoreConfig,
    get_store_configs,
    scrape_store,
)

settings = get_prefect_settings()

# TODO: migrate store configs to a Supabase table so they can be managed without a redeploy
# Alternative (Option B): mount a host volume at /data/stores/ in docker-compose.prod.yml
#   and point this path there — useful if the list grows large or needs frequent updates
STORE_CONFIGS_PATH = Path(__file__).parent / "../ingestion/offers/netto_store_configs.json"
STORE_CONFIGS = get_store_configs(STORE_CONFIGS_PATH)

DATALAKE_PATH_TEMPLATE = (
    "retailer={retailer}/"
    "store_external_id={store_external_id}/"
    "year={year}/"
    "month={month}/"
    "day={day}/"
    "page={page}/"
    "main.html"
)


@task(retries=2, retry_delay_seconds=30)
def extract_html_with_seleniumbase(conf: StoreConfig) -> list[str]:
    logger = get_run_logger()
    logger.info("Starting scrape for %s - %s", conf.retailer, conf.external_id)

    with seleniumbase_browser_context() as ctx:
        page = ctx.new_page()
        return scrape_store(address=conf.address, page=page)


@task
def upload_html_to_datalake(conf: StoreConfig, html_content: str, page_number: int) -> str:
    logger = get_run_logger()
    supabase = get_supabase()

    today = date.today()
    path = DATALAKE_PATH_TEMPLATE.format(
        retailer=conf.retailer,
        store_external_id=conf.external_id,
        year=today.year,
        month=today.strftime("%m"),
        day=today.strftime("%d"),
        page=page_number,
    )

    logger.info("Uploading page %d to Supabase path: %s", page_number, path)

    supabase.storage.from_("raw_offers").upload(
        path,
        html_content.encode("utf-8"),
        file_options={
            "content-type": "text/html",
            "upsert": "true",
        },
    )
    return path


@flow(name="scrape-netto-daily-offers")
def scrape_offers_flow(batch_size: int = settings.scrapper_batch_size):
    logger = get_run_logger()

    for batch in batched(STORE_CONFIGS, batch_size):
        scrape_futures = extract_html_with_seleniumbase.map(list(batch))  # type: ignore[no-matching-overload]

        for conf, future in zip(batch, scrape_futures):
            try:
                pages_html = future.result()
            except Exception as e:
                logger.error(
                    "Scrape failed for %s %s: %s", 
                    conf.retailer, conf.external_id, e
                    )
                continue

            for page_number, html in enumerate(pages_html, start=1):
                upload_html_to_datalake(conf, html, page_number)  # type: ignore[no-matching-overload]
