from datetime import date
from pathlib import Path
import playwright
from prefect import flow, task, get_run_logger
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

from core.supabase import get_supabase
from ingestion.offers.rewe_scrapper import get_store_configs, StoreConfig, deny_usercentrics_banner, scroll_to_top, scrape_store


STORE_CONFIGS_PATH = Path(__file__).parent / "../../../data/stores/rewe_store_configs.json"
STORE_CONFIGS = get_store_configs(STORE_CONFIGS_PATH)

DATALAKE_PATH_TEMPLATE = (
    "retailer={retailer}/"
    "store_external_id={store_external_id}/"
    "year={year}/"
    "month={month}/"
    "day={day}/"
    "page=1/"
    "{page_name}.html"
)


@task(retries=2, retry_delay_seconds=30)
def extract_html_with_playwright(conf: StoreConfig) -> dict[str, str]:
    logger = get_run_logger()
    logger.info("Starting scrape for %s - %s", conf.retailer, conf.name)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            return scrape_store(url=conf.url, page=page)
        finally:
            browser.close()


@task
def upload_html_to_datalake(
    conf: StoreConfig, html_content: str, page_name: str
    ) -> str:
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
    
    logger.info("Uploading %s to Supabase path: %s", page_name, path)
    
    # Assuming you create a bucket named 'raw_offers'
    supabase.storage.from_("raw_offers").upload(
        path,
        html_content.encode("utf-8"),
        file_options={"content-type": "text/html", "upsert": "true"} # Upsert prevents 409 errors on retries
    )
    return path

# 3. The Orchestrating Flow
@flow(name="scrape-daily-offers")
def scrape_offers_flow():
    logger = get_run_logger()
    
    for conf in STORE_CONFIGS[:3]:
        try:
            # Execute the resilient scrape task
            scraped_data = extract_html_with_playwright(conf)
            
            # Upload the results
            upload_html_to_datalake(conf, scraped_data["main"], "main")
            upload_html_to_datalake(conf, scraped_data["articles"], "articles")
            
        except Exception as e:
            logger.error(f"Failed to process {conf.retailer}: {e}")
            # Flow continues to the next store even if one fails
            