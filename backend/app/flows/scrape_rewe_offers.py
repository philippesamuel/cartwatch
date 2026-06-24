from itertools import batched
from pathlib import Path
from typing import Literal

from prefect import flow, get_run_logger, task

from core.config import get_prefect_settings
from flows.common import upload_html_to_datalake
from ingestion.browser import browser_context
from ingestion.offers.rewe_scrapper import (
    StoreConfig,
    get_store_configs,
    scrape_store,
)
from logger import forward_logs

settings = get_prefect_settings()

# TODO: migrate store configs to a Supabase table so they can be managed without a redeploy
# Alternative (Option B): mount a host volume at /data/stores/ in docker-compose.prod.yml
#   and point this path there — useful if the list grows large or needs frequent updates
STORE_CONFIGS_PATH = Path(__file__).parent / "../ingestion/offers/rewe_store_configs.json"
STORE_CONFIGS = get_store_configs(STORE_CONFIGS_PATH)


@task(retries=2, retry_delay_seconds=30)
@forward_logs
def extract_html_with_playwright(  # type: ignore[no-matching-overload]
    conf: StoreConfig,
) -> dict[Literal["main", "articles"], str]:
    logger = get_run_logger()
    logger.info(f"Starting scrape for {conf.retailer} - {conf.external_id}")

    with browser_context(headless=True) as ctx:
        page = ctx.new_page()
        return scrape_store(url=conf.url, page=page)


@flow(name="scrape-rewe-daily-offers")
@forward_logs
def scrape_offers_flow(batch_size: int = settings.scrapper_batch_size):
    logger = get_run_logger()

    for batch in batched(STORE_CONFIGS, batch_size):
        scrape_futures = extract_html_with_playwright.map(list(batch))  # type: ignore[no-matching-overload]

        for conf, future in zip(batch, scrape_futures):
            try:
                scraped_data = future.result()
            except Exception as e:
                logger.error(f"Scrape failed for {conf.retailer} {conf.external_id}: {e}")
                continue
            upload_html_to_datalake(conf, scraped_data["main"], "main")  # type: ignore[no-matching-overload]
            upload_html_to_datalake(conf, scraped_data["articles"], "articles")  # type: ignore[no-matching-overload]
