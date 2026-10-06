import json
import logging
from pathlib import Path

import requests

BASE_URL = "https://dummyjson.com"
PAGE_SIZE = 100
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

log = logging.getLogger(__name__)


def fetch_all(endpoint: str, key: str) -> list[dict]:
    items, skip = [], 0
    while True:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params={"limit": PAGE_SIZE, "skip": skip},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        items.extend(payload[key])
        log.info("%s : %d éléments récupérés sur %d", endpoint, len(items), payload["total"])
        skip += PAGE_SIZE
        if skip >= payload["total"]:
            return items


def extract() -> dict[str, str]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    sources = {"products": "products", "carts": "carts"}
    paths = {}
    for endpoint, key in sources.items():
        records = fetch_all(endpoint, key)
        path = RAW_DIR / f"{endpoint}.json"
        path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("Données brutes sauvegardées : %s (%d lignes)", path, len(records))
        paths[endpoint] = str(path)
    return paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(extract())
