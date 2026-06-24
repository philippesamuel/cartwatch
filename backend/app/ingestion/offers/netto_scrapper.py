import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal, Optional, Self

from bs4 import BeautifulSoup
from loguru import logger
from playwright.sync_api import Page

from ingestion.browser import deny_consent_banner, scroll_to_top, seleniumbase_browser_context

STORE_FINDER_URL = "https://www.netto-online.de/filialangebote"
DENY_BUTTON_CSS_LOCATOR = "#CybotCookiebotDialogBodyButtonDecline"

_SHOW_ALL_PRODUCTS_JS = (
    'document.querySelectorAll("ul.product-list").forEach(el => el.style.display = "")'
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
    
    def get_file_path(self, name: str) -> Path:
        name_str = f"{name}.html"
        return self.partition_dir / name_str
    
    def save(self, html: str, name: str) -> None:
        file_path = self.get_file_path(name=name)
        logger.info(f"Saving to {file_path}")
        if not (parent_dir := file_path.parent).exists():
            logger.info(f"Creating folder {parent_dir}")
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
            logger.info(f"{files.partition_dir} already exists. Skipping ...")
            continue

        with seleniumbase_browser_context() as ctx:
            page = ctx.new_page()
            try:
                html_content = scrape_store(conf=conf, page=page)
            except Exception as e:
                logger.error(f"Failed to scrape store {conf.external_id}. Moving to next store.")
                logger.error(f"{e}")
                continue

        files.save(html=html_content["main"], name="main")
        files.save(html=html_content["articles"], name="articles")


def scrape_store(conf: StoreConfig, page: Page) -> dict[Literal["main", "articles"], str]:
    cookies = [{
        "name": "netto_user_stores_id",
        "value": conf.external_id,        
        "domain": ".netto-online.de",     # leading dot = also valid on subdomains
        "path": "/",
        # optional but often expected by the site:
        "secure": True,
        "sameSite": "Lax",
    }] 
    page.context.add_cookies(cookies)  # type: ignore
    page.goto(STORE_FINDER_URL)
    deny_consent_banner(page, DENY_BUTTON_CSS_LOCATOR, timeout=1000)

    footer = page.wait_for_selector("footer")
    if footer is not None:
        footer.scroll_into_view_if_needed()
    scroll_to_top(page)

    page.evaluate(_SHOW_ALL_PRODUCTS_JS)

    main_locator = page.get_by_role("main").first
    main_soup = BeautifulSoup(main_locator.inner_html(), "html.parser")
    articles = main_soup.select("div.product-list__item")
    logger.info(f"Found {len(articles)} items")
    return {
        "main": main_soup.prettify(),
        "articles": "".join([a.prettify() for a in articles]),
    }


def get_store_configs(path: Path) -> list[StoreConfig]:
    path = Path(path)
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
