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
STOREFINDER_BUTTON_SELECTOR = "a.js-layer-storefinder"
ADDRESS_INPUT_SELECTOR = 'input[type="text"][name="post_code"]'
ADDRESS_DROPDOWN_SELECTOR = "div.js-autocomplete-dropdown span"
GO_TO_OFFERS_BUTTON_SELECTOR = (
    "a.btn-primary"
    ".store-finder__inner__box__button"
    ".store-offers-btn"
    )

PARTITION_TEMPLATE = (
    "{root}/retailer={retailer}/store_external_id={external_id}/"
    "year={year}/month={month}/day={day}/"
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


class StoreOfferFiles:
    def __init__(
        self,
        conf: StoreConfig,
        date: date = date.today(), 
        root_dir: Path = Path("./data")
        ) -> None:
        self.conf = conf
        self.date = date
        self.root_dir = root_dir
        self.partition_template = PARTITION_TEMPLATE
    
    @property
    def partition_dir(self) -> Path:
        path_str = self.partition_template.format(
            root=self.root_dir,
            retailer=self.conf.retailer,
            external_id=self.conf.external_id,
            year=self.date.year,
            month=self.date.strftime("%m"),
            day=self.date.strftime(r"%d"),
        )
        return Path(path_str)      
    
    def partition_exists(self) -> bool:
        return self.partition_dir.exists()  
    
    def get_file_path(self, name: str, page: int) -> Path:
        page_name_str = "page={}/{}.html".format(page, name)  
        return self.partition_dir / page_name_str
    
    def save(self, html: str, name: str, page: int) -> None:
        file_path = self.get_file_path(name=name, page=page)
        logger.info("Saving to {}", file_path)
        if not (parent_dir := file_path.parent).exists():
            logger.info("Creating folder {}", parent_dir)
            parent_dir.mkdir(parents=True, exist_ok=True)
        with file_path.open("wt") as f:
            f.write(html) 


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
) -> None:
    store_configs = STORE_CONFIGS
    if store_configs_path is not None:
        store_configs = get_store_configs(store_configs_path)

    if output_data_dir is None:
        output_data_dir = Path("./data")

    for conf in store_configs:
        files = StoreOfferFiles(
            conf=conf, 
            date=date.today(), 
            root_dir=output_data_dir.absolute(),
            )
        
        if files.partition_exists():
            logger.info("{} already exists. Skipping ...", files.partition_dir)
            continue

        with seleniumbase_browser_context() as ctx:             
            page = ctx.new_page()
            try:
                pages_html = scrape_store(address=conf.address, page=page)
            except Exception as e:
                logger.error("Failed to scrape store with id {}. Moving to next store.", conf.external_id)
                logger.error("{}", e)
                continue

        for page_number, html in enumerate(pages_html, start=1):
            files.save(html=html, name="main", page=page_number)


def scrape_store(address: str, page: Page) -> list[str]:
    page.goto(STORE_FINDER_URL)
    deny_cookiebot_banner(page)
    
    logger.info("Clicking storefinder button ...")
    page.locator(STOREFINDER_BUTTON_SELECTOR).first.click()
    
    page.wait_for_selector(ADDRESS_INPUT_SELECTOR)
    logger.info("Typing address into input field ...")
    page.locator(ADDRESS_INPUT_SELECTOR).type(address)
    
    page.wait_for_selector(ADDRESS_DROPDOWN_SELECTOR)
    logger.info("Clicking first address in autocomplete dropdown ...")
    page.locator(ADDRESS_DROPDOWN_SELECTOR).first.click()
    
    logger.info('Clicking "Go to offers" button ...')
    page.locator(GO_TO_OFFERS_BUTTON_SELECTOR).first.click()
    page.wait_for_timeout(1000)

    number_of_pages = get_number_of_pages(page)
    logger.info("Found {} offer page(s)", number_of_pages)

    pages_html: list[str] = []
    for page_number in range(1, number_of_pages + 1):
        footer = page.wait_for_selector("footer")
        if footer is not None:
            footer.scroll_into_view_if_needed()
        scroll_to_top(page)  # prime all content before scrapping

        main_locator = page.get_by_role("main").first
        main_soup = BeautifulSoup(main_locator.inner_html(), "html.parser")
        articles = main_soup.select("div.product-list__item")
        logger.info("Page {}: found {} items", page_number, len(articles))

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
            logger.debug("Scrolling... counter={}", counter)
            time.sleep(0.5)


def get_store_configs(path: Path) -> list[StoreConfig]:
    with path.open("rt") as f:
        store_dicts = json.load(f)

    for d in store_dicts:
        d.setdefault("retailer", "netto")

    return [StoreConfig.from_dict(d) for d in store_dicts]


if __name__ == "__main__":
    # example:
    # 
    # main(
    #    store_configs_path=Path(__file__).parent / "netto_store_configs.json",
    #    output_data_dir=Path("../data/")
    #    )
    main()
