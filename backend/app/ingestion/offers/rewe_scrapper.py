from dataclasses import dataclass
from datetime import date
import functools
from pathlib import Path
import time
from typing import Optional, Protocol

from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import sync_playwright, Playwright


@dataclass(frozen=True, slots=True)
class StoreConfig:
    retailer: str
    external_id: str
    name: str
    url: str


STORE_CONFIGS: list[StoreConfig] = [
    StoreConfig(
        retailer="rewe",
        external_id="1765982",
        name="REWE Müllerstr. 141 Berlin",
        url="https://www.rewe.de/angebote/berlin-wedding/1765982/rewe-markt-muellerstr-141/",
    ),
]


DENY_BUTTON_CSS_LOCATOR = 'button[data-testid="uc-deny-all-button"]'
DATE = date.today()
ISODATE = DATE.isoformat()
HTML_FILE_TEMPLATE = (
    './data/retailer={retailer}/store_external_id={external_id}/'
    'year={year}/month={month}/day={day}/'
    'page={page}/{name}.html'
    )


def run(playwright: Playwright):
    for conf in STORE_CONFIGS:
        file_path_fn = functools.partial(
            get_file_path_with_retailer_store_date_partitions, 
            conf=conf,
            )
        scrape_store(
            url=conf.url, 
            file_path_fn=file_path_fn,
            playwright=playwright,
            )


class FilePathFn(Protocol):
    def __call__(self, name: str) -> Path: ...


def get_file_path_with_retailer_store_date_partitions(
    name: str, 
    conf: StoreConfig,
    ) -> Path:
    path_str = HTML_FILE_TEMPLATE.format(
        name=name,
        retailer=conf.retailer, 
        external_id=conf.external_id, 
        year=DATE.year, 
        month=DATE.strftime("%m"), 
        day=DATE.strftime(r"%d"), 
        page=1,
        )
    return Path(path_str)


def scrape_store(
    url: str,
    playwright: Playwright,
    file_path_fn: FilePathFn
    ) -> None:
    
    main_html_file = file_path_fn(name="main")
    articles_html_file = file_path_fn(name="articles")
    
    chromium = playwright.chromium # or "firefox" or "webkit".
    browser = chromium.launch(headless=False)
    page = browser.new_page()
    page.goto(url)
    deny_usercentrics_banner(page)
    
    page.wait_for_timeout(2000)
    
    page.wait_for_selector("footer").scroll_into_view_if_needed()
    scroll_to_top(page)  # prime all content before scrapping
        
    main_locator = page.get_by_role("main")
    main_soup = BeautifulSoup(main_locator.inner_html(), "html.parser")
    articles = main_soup.find_all("article") 
    
    logger.info(f"Found {len(articles)} items")
    
    logger.info(f"Saving <main> element to {main_html_file}")
    if not (parent_dir := main_html_file.parent).exists():
        logger.info("Creating folder {}", parent_dir)
        parent_dir.mkdir(parents=True, exist_ok=True) 
    with main_html_file.open("wt") as f:
        f.write(main_soup.prettify())
    
    logger.info(f"Saving <article> elements to {articles_html_file}")
    
    articles_html_file.unlink(missing_ok=True) 
    with articles_html_file.open("at") as f:
        for article in articles:
            f.write(article.prettify())
    
    browser.close()
    
    
def deny_usercentrics_banner(page) -> None:
    try:
        # 1. Locate the button directly. Playwright pierces the Shadow DOM automatically.
        deny_button = page.locator(DENY_BUTTON_CSS_LOCATOR)
        
        # 2. Wait up to 10 seconds for the button to be attached to the DOM and visible.
        # This handles the asynchronous loading of the Usercentrics script.
        logger.info("Waiting for Usercentrics banner...")
        deny_button.wait_for(state="visible", timeout=10000)
        
        # 3. Click it once it appears
        deny_button.click()
        logger.success("Successfully clicked the 'Deny All' button.")
        
    except TimeoutError:
        # If 10 seconds pass and the button never shows up, it fails gracefully.
        logger.error("Timeout: Banner did not appear within 10 seconds. It may be disabled or already accepted.")


def scroll_to_top(page):
    # Get the initial height of the page
    page.evaluate(
        """
        var intervalID = setInterval(function () {
            window.scrollBy(0, -window.innerHeight);
        }, 300);
        """
    )
    counter = 0
    while True:
        if page.evaluate('window.scrollY <= window.innerHeight'):
            logger.success("I reached the top")
            page.evaluate('clearInterval(intervalID)')
            break
        else:
            counter += 1
            logger.info(f"Scrolling... {counter=}")
            time.sleep(1)


with sync_playwright() as playwright:
    run(playwright) 