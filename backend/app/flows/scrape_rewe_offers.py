import asyncio
import math
from itertools import batched
from pathlib import Path
from typing import Literal

from prefect import flow, get_run_logger, task
from prefect.deployments import arun_deployment

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
def extract_html_with_playwright(
    conf: StoreConfig,
) -> dict[Literal["main", "articles"], str]:
    logger = get_run_logger()
    logger.info(f"Starting scrape for {conf.retailer} - {conf.external_id}")

    with browser_context(headless=True) as ctx:
        page = ctx.new_page()
        return scrape_store(url=conf.url, page=page)


@flow(name="scrape-rewe-daily-offers")
@forward_logs
async def scrape_offers_flow(batch_size: int = 8):
    logger = get_run_logger()
    store_ids = [conf.external_id for conf in STORE_CONFIGS]
    n_batches = math.ceil(len(store_ids) / batch_size)
    logger.info(
        f"Dispatching {len(store_ids)} stores, {n_batches} batch(es) of {batch_size}"
    )
    futures = []
    for i, batch in enumerate(batched(store_ids, batch_size), start=1):
        logger.info(f"Dispatching batch {i}/{n_batches}: {list(batch)}")
        future = arun_deployment(
            name="scrape-rewe-store-batch/scrape-rewe-store-batch_ecs",
            parameters={"store_ids": list(batch)},
            as_subflow=False,
        )
        futures.append(future)
    await asyncio.gather(*futures)
    logger.info(f"All {n_batches} batch(es) dispatched.")


@flow(name="scrape-rewe-store-batch")
@forward_logs
def scrape_store_flow(store_ids: list[str]) -> None:
    logger = get_run_logger()
    logger.info(f"Batch started: {len(store_ids)} store(s) — {store_ids}")
    for i, id_ in enumerate(store_ids, start=1):
        logger.info(f"[{i}/{len(store_ids)}] Scraping store {id_}")
        try:
            scrape_single_store(id_)
        except Exception as e:
            logger.error(f"Scrape failed for rewe {id_}: {e}")
    logger.info(f"Batch complete: {len(store_ids)} store(s) processed.")


@task
@forward_logs
def scrape_single_store(store_id: str) -> None:
    logger = get_run_logger()
    conf = next(c for c in STORE_CONFIGS if c.external_id == store_id)
    scraped_data = extract_html_with_playwright(conf)
    upload_html_to_datalake(conf, scraped_data["main"], "main")  # type: ignore[no-matching-overload]
    upload_html_to_datalake(conf, scraped_data["articles"], "articles")  # type: ignore[no-matching-overload]
    logger.info(f"Store {store_id} uploaded successfully.")
