import functools
import json
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Self

from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import Page, TimeoutError

from ingestion.browser import seleniumbase_browser_context

STORE_FINDER_URL = "https://www.netto-online.de/filialangebote"
DENY_BUTTON_CSS_LOCATOR = "#CybotCookiebotDialogBodyButtonDecline"

DATE = date.today()
ISODATE = DATE.isoformat()
HTML_FILE_TEMPLATE = (
    "{root}/retailer={retailer}/store_external_id={external_id}/"
    "year={year}/month={month}/day={day}/"
    "page={page}/{name}.html"
)


@dataclass(frozen=True, slots=True)
class StoreConfig:
    retailer: str
    external_id: str
    address: str

    @classmethod
    def from_dict(cls, dict_) -> Self:
        return cls(
            retailer=dict_["retailer"],
            external_id=dict_["external_id"],
            address=dict_["address"],
        )


STORE_CONFIGS: list[StoreConfig] = [
    StoreConfig(
        retailer="netto",
        external_id="7625",
        address="Oudenarder Str. 14 13347",
    ),
]


def main(
    store_configs_path: Optional[Path] = None,
    output_data_dir: Optional[Path] = None,
    headless: bool = True,
) -> None:
    store_configs = STORE_CONFIGS
    if store_configs_path is not None:
        store_configs = get_store_configs(store_configs_path)

    if output_data_dir is None:
        output_data_dir = Path("./data")

    for conf in store_configs:
        file_path_fn = functools.partial(
            get_file_path_with_retailer_store_date_partitions,
            conf=conf,
            root_dir=str(output_data_dir.absolute()),
        )

        with seleniumbase_browser_context() as ctx:             
            page = ctx.new_page()
            try:
                pages_html = scrape_store(address=conf.address, page=page)
            except Exception as e:
                logger.error("Failed to scrape store with id {}. Moving to next store.", conf.external_id)
                logger.error(e)
                continue

        for page_number, html in enumerate(pages_html, start=1):
            save_scraped_html(html=html, file_path=file_path_fn(name="main", page=page_number))


def get_file_path_with_retailer_store_date_partitions(
    name: str, conf: StoreConfig, page: int, root_dir: str = "./data"
) -> Path:
    path_str = HTML_FILE_TEMPLATE.format(
        root=root_dir,
        name=name,
        retailer=conf.retailer,
        external_id=conf.external_id,
        year=DATE.year,
        month=DATE.strftime("%m"),
        day=DATE.strftime(r"%d"),
        page=page,
    )
    return Path(path_str)


def scrape_store(address: str, page: Page) -> list[str]:
    page.goto(STORE_FINDER_URL)

    storefinder_butto_selector = "a.js-layer-storefinder"
    address_input_selector = 'input[type="text"][name="post_code"]'
    address_dropdown_selector = "div.js-autocomplete-dropdown span"
    go_to_offers_button_selector = (
        "a.btn-primary"
        ".store-finder__inner__box__button"
        ".store-offers-btn"
        )
    
    deny_cookiebot_banner(page)
    
    logger.info("Clicking storefinder button ...")
    page.locator(storefinder_butto_selector).click()
    
    page.wait_for_selector(address_input_selector)
    logger.info("Typing address into input field ...")
    page.locator(address_input_selector).type(address)
    
    page.wait_for_selector(address_dropdown_selector)
    logger.info("Clicking first address in autocomplete dropdown ...")
    page.locator(address_dropdown_selector).first.click()
    
    logger.info('Clicking "Go to offers" button ...')
    page.locator(go_to_offers_button_selector).first.click()
    page.wait_for_timeout(1000)

    number_of_pages = get_number_of_pages(page)
    logger.info(f"Found {number_of_pages} offer page(s)")

    pages_html: list[str] = []
    for page_number in range(1, number_of_pages + 1):
        footer = page.wait_for_selector("footer")
        if footer is not None:
            footer.scroll_into_view_if_needed()
        scroll_to_top(page)  # prime all content before scrapping

        main_locator = page.get_by_role("main")
        main_soup = BeautifulSoup(main_locator.inner_html(), "html.parser")
        articles = main_soup.select("div.product-list__item")
        logger.info(f"Page {page_number}: found {len(articles)} items")

        pages_html.append(main_soup.prettify())

        if page_number < number_of_pages:
            next_page_el = page.query_selector("ul.pagination li:last-child")
            if next_page_el is not None:
                next_page_el.click()
                page.wait_for_timeout(1000)

    return pages_html


def get_number_of_pages(page: Page) -> int:
    # second-to-last pagination item is the highest page number (e.g.: < 1 2 3 4 >, last is ">")
    last_page_el = page.query_selector("ul.pagination li:nth-last-child(2)")
    if last_page_el is None:
        return 1
    return int(last_page_el.inner_text())


def save_scraped_html(html: str, file_path: Path) -> None:
    logger.info(f"Saving to {file_path}")
    if not (parent_dir := file_path.parent).exists():
        logger.info("Creating folder {}", parent_dir)
        parent_dir.mkdir(parents=True, exist_ok=True)
    with file_path.open("wt") as f:
        f.write(html)


def deny_cookiebot_banner(page: Page) -> None:
    try:
        # wait up to 1 second for the button to be attached to the DOM and visible.
        deny_button = page.locator(DENY_BUTTON_CSS_LOCATOR)

        # This handles the asynchronous loading of the Cookiebot script.
        logger.info("Waiting for Cookiebot banner...")
        deny_button.wait_for(state="visible", timeout=1000)
        deny_button.click()
        logger.success("Successfully clicked the 'Deny All' button.")

    except TimeoutError:
        # If 10 seconds pass and the button never shows up, it fails gracefully.
        logger.warning(
            "Timeout: Banner did not appear within 1 second. "
            "It may be disabled or already accepted."
        )


def scroll_to_top(page: Page) -> None:
    page.evaluate(
        """
        var intervalID = setInterval(function () {
            window.scrollBy(0, -window.innerHeight);
        }, 200);
        """
    )
    counter = 0
    while True:
        if page.evaluate("window.scrollY <= window.innerHeight"):
            logger.success("I reached the top")
            page.evaluate("clearInterval(intervalID)")
            break
        else:
            counter += 1
            logger.debug(f"Scrolling... {counter=}")
            time.sleep(0.5)


def get_store_configs(path: Path) -> list[StoreConfig]:
    with path.open("rt") as f:
        store_dicts = json.load(f)

    for d in store_dicts:
        d.setdefault("retailer", "netto")

    return [StoreConfig.from_dict(d) for d in store_dicts]


if __name__ == "__main__":
    main(
        store_configs_path=Path(__file__).parent / "netto_store_configs.json",
        output_data_dir=Path("../data/")
        )
