import json
import logging
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

log = logging.getLogger(__name__)


def load_json(name: str) -> list[dict]:
    return json.loads((RAW_DIR / f"{name}.json").read_text(encoding="utf-8"))


def deduplicate(records: list[dict], key: str) -> list[dict]:
    seen, unique = set(), []
    for record in records:
        if record[key] not in seen:
            seen.add(record[key])
            unique.append(record)
    log.info("Déduplication sur %s : %d -> %d", key, len(records), len(unique))
    return unique


def normalize_date(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()


def transform_products(raw: list[dict]) -> list[dict]:
    products = []
    for item in deduplicate(raw, "id"):
        reviews = item.get("reviews", [])
        ratings = [r["rating"] for r in reviews]
        final_price = round(item["price"] * (1 - item["discountPercentage"] / 100), 2)
        products.append({
            "product_id": item["id"],
            "title": item["title"].strip(),
            "category": item["category"],
            "brand": item.get("brand") or "Inconnue",
            "sku": item["sku"],
            "price": round(item["price"], 2),
            "discount_percentage": round(item["discountPercentage"], 2),
            "final_price": final_price,
            "stock": item["stock"],
            "stock_value": round(final_price * item["stock"], 2),
            "rating": round(item["rating"], 2),
            "review_count": len(reviews),
            "average_review_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "reviews": [
                {
                    "rating": r["rating"],
                    "comment": r["comment"],
                    "date": normalize_date(r["date"]),
                    "reviewer": r["reviewerName"],
                }
                for r in reviews
            ],
        })
    return products


def transform_sales(carts: list[dict], catalog: dict[int, dict]) -> list[dict]:
    sales = []
    for cart in deduplicate(carts, "id"):
        for line in cart["products"]:
            product = catalog[line["id"]]
            sales.append({
                "cart_id": cart["id"],
                "user_id": cart["userId"],
                "product_id": line["id"],
                "title": product["title"],
                "category": product["category"],
                "brand": product["brand"],
                "quantity": line["quantity"],
                "unit_price": product["final_price"],
                "line_total": round(product["final_price"] * line["quantity"], 2),
            })
    return sales


def transform() -> dict[str, str]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    products = transform_products(load_json("products"))
    catalog = {p["product_id"]: p for p in products}
    sales = transform_sales(load_json("carts"), catalog)

    paths = {}
    for name, rows in {"products": products, "sales": sales}.items():
        path = PROCESSED_DIR / f"{name}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("%s transformés : %d lignes -> %s", name, len(rows), path)
        paths[name] = str(path)
    return paths


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(transform())
