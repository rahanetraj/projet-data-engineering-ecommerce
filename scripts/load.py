import json
import logging
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
MAPPING_PATH = ROOT / "elasticsearch" / "mapping.json"
DEFAULT_ES_URL = "http://localhost:9200"

log = logging.getLogger(__name__)


def create_indices(es_url: str, mapping: dict) -> None:
    for index, body in mapping.items():
        exists = requests.head(f"{es_url}/{index}", timeout=10).status_code == 200
        if exists:
            log.info("Index %s déjà présent, mapping conservé", index)
            continue
        response = requests.put(f"{es_url}/{index}", json=body, timeout=30)
        response.raise_for_status()
        log.info("Index %s créé avec son mapping", index)


def bulk_index(es_url: str, index: str, documents: list[tuple[str, dict]]) -> int:
    lines = []
    for doc_id, doc in documents:
        lines.append(json.dumps({"index": {"_index": index, "_id": doc_id}}))
        lines.append(json.dumps(doc, ensure_ascii=False))
    payload = "\n".join(lines) + "\n"
    response = requests.post(
        f"{es_url}/_bulk",
        data=payload.encode("utf-8"),
        headers={"Content-Type": "application/x-ndjson"},
        timeout=60,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("errors"):
        failed = [item for item in result["items"] if "error" in item["index"]]
        raise RuntimeError(f"{len(failed)} document(s) rejeté(s) par Elasticsearch : {failed[:3]}")
    return len(documents)


def load(es_url: str = DEFAULT_ES_URL) -> dict[str, int]:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    products = json.loads((PROCESSED_DIR / "products.json").read_text(encoding="utf-8"))
    sales = json.loads((PROCESSED_DIR / "sales.json").read_text(encoding="utf-8"))

    create_indices(es_url, mapping)

    product_docs = [(str(p["product_id"]), p) for p in products]
    sale_docs = [(f"{s['cart_id']}-{s['product_id']}", s) for s in sales]

    loaded = {
        "products": bulk_index(es_url, "products", product_docs),
        "sales": bulk_index(es_url, "sales", sale_docs),
    }
    log.info("Chargement terminé : %s", loaded)
    return loaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(load())
