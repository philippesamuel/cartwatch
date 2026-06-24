import functools
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Optional, Self

from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import Page

from ingestion.browser import browser_context, deny_consent_banner, scroll_to_top


@dataclass(frozen=True, slots=True)
class StoreConfig:
    retailer: str
    external_id: str
    url: str

    @classmethod
    def from_dict(cls, dict_) -> Self:
        return cls(
            retailer=dict_["retailer"],
            external_id=dict_["external_id"],
            url=dict_["url"],
        )


STORE_CONFIGS: list[StoreConfig] = [
    StoreConfig(
        retailer="rewe",
        external_id="1765982",
        url="https://www.rewe.de/angebote/berlin-wedding/1765982/rewe-markt-muellerstr-141/",
    ),
]


DENY_BUTTON_CSS_LOCATOR = 'button[data-testid="uc-deny-all-button"]'
DATE = date.today()
HTML_FILE_TEMPLATE = (
    "{root}/"
    "retailer={retailer}/"
    "store_external_id={external_id}/"
    "year={year}/"
    "month={month}/"
    "day={day}/"
    "{name}.html"
)


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
        main_file = file_path_fn(name="main")
        articles_file = file_path_fn(name="articles")

        if main_file.exists() and articles_file.exists():
            logger.info(f"{main_file} and {articles_file} already exist. Skipping ...")
            continue
        with browser_context(headless=headless) as ctx:
            page = ctx.new_page()
            html_content = scrape_store(url=conf.url, page=page)

        save_scraped_html(html=html_content["main"], file_path=file_path_fn(name="main"))
        save_scraped_html(html=html_content["articles"], file_path=file_path_fn(name="articles"))


def get_file_path_with_retailer_store_date_partitions(
    name: str, conf: StoreConfig, root_dir: str = "./data"
) -> Path:
    path_str = HTML_FILE_TEMPLATE.format(
        root=root_dir,
        name=name,
        retailer=conf.retailer,
        external_id=conf.external_id,
        year=DATE.year,
        month=DATE.strftime("%m"),
        day=DATE.strftime("%d"),
    )
    return Path(path_str)


def scrape_store(
    url: str,
    page: Page,
) -> dict[Literal["main", "articles"], str]:
    page.goto(url)
    deny_consent_banner(page, DENY_BUTTON_CSS_LOCATOR)

    page.wait_for_timeout(1000)

    page.wait_for_selector("footer").scroll_into_view_if_needed()
    scroll_to_top(page)

    main_locator = page.get_by_role("main").first
    main_soup = BeautifulSoup(main_locator.inner_html(), "html.parser")
    articles = main_soup.find_all("article")

    logger.info(f"Found {len(articles)} items")
    return {
        "main": main_soup.prettify(),
        "articles": "".join([a.prettify() for a in articles]),
    }


def save_scraped_html(html: str, file_path: Path) -> None:
    logger.info(f"Saving to {file_path}")
    if not (parent_dir := file_path.parent).exists():
        logger.info(f"Creating folder {parent_dir}")
        parent_dir.mkdir(parents=True, exist_ok=True)
    with file_path.open("wt") as f:
        f.write(html)


def get_store_configs(path: Path) -> list[StoreConfig]:
    path = Path(path)
    with path.open("rt") as f:
        store_dicts = json.load(f)

    for d in store_dicts:
        d.setdefault("retailer", "rewe")

    return [StoreConfig.from_dict(d) for d in store_dicts]


if __name__ == "__main__":
    main()
