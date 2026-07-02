import json
import re
from pathlib import Path

from loguru import logger
from pydantic import BaseModel, computed_field, ValidationError


URL_TEMPLATE = "https://www.rewe.de/angebote/{city}/{ww_ident}/{street}/"


class Location(BaseModel):
    latitude: float
    longitude: float


class ReweRawStoreInfo(BaseModel):
    wwIdent: str
    name: str
    companyName: str
    street: str
    zipCode: str
    city: str
    location: Location
    openingInfo: list[dict]

    @computed_field
    @property
    def url(self) -> str:
        return URL_TEMPLATE.format(
            city=slugify(self.city),
            ww_ident=self.wwIdent,
            street=slugify(self.street),
        )


def slugify(s: str) -> str:
    return re.sub(r"\W+", "-", s.lower().strip())


DATA = Path("data") / "stores"
INPUT = DATA / "rewe_raw_stores_list.json"
OUTPUT = DATA / "rewe_url_stores_list.json"

_OUTPUT_FIELDS = {"wwIdent", "name", "companyName", "street", "zipCode", "city", "location", "openingInfo", "url"}


def main() -> None:
    raw = json.loads(INPUT.read_text())
    logger.info("Loaded {} markets from {}", len(raw), INPUT)

    results = []
    for entry in raw:
        try:
            store = ReweRawStoreInfo.model_validate(entry)
            results.append(store.model_dump(include=_OUTPUT_FIELDS))
        except ValidationError as e:
            logger.warning("Skipping wwIdent={}: {}", entry.get("wwIdent"), e)

    OUTPUT.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    logger.success("Wrote {} records to {}", len(results), OUTPUT)


if __name__ == "__main__":
    main()
