"""Generate netto_store_configs.json from data/stores/netto_raw_stores_list.json.

The raw list is Netto's full store directory export. This script filters out
closed stores and reshapes each entry into what `netto_scrapper.StoreConfig`
expects — notably an `address` field ("{street} {zipCode}") used to drive the
store-finder search on netto-online.de.

Usage:
    python backend/scripts/generate_netto_store_configs.py
"""

import json
from pathlib import Path

RAW_STORES_PATH = Path(__file__).parent / "../../data/stores/netto_raw_stores_list.json"
OUTPUT_PATH = Path(__file__).parent / "../app/ingestion/offers/netto_store_configs.json"


def main() -> None:
    with RAW_STORES_PATH.open("rt") as f:
        raw_stores = json.load(f)

    configs = [build_store_config(s) for s in raw_stores if not s.get("is_closed")]

    with OUTPUT_PATH.open("wt") as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(configs)} store configs to {OUTPUT_PATH.resolve()}")


def build_store_config(store: dict) -> dict:
    street = store["street"].strip()
    zip_code = store["post_code"].strip()
    return {
        "retailer": "netto",
        "external_id": store["store_id"],
        "name": store["store_name"],
        "street": street,
        "zipCode": zip_code,
        "city": store["city"],
        "location": {
            "latitude": float(store["coord_latitude"]),
            "longitude": float(store["coord_longitude"]),
        },
        # used by netto_scrapper.scrape_store() to search the store-finder
        "address": f"{street} {zip_code}",
    }


if __name__ == "__main__":
    main()
