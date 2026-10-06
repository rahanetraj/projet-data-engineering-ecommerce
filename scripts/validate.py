import json
import logging
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"

log = logging.getLogger(__name__)


class DataQualityError(Exception):
    pass


def check(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        log.info("OK : %s", message)
    else:
        log.error("ÉCHEC : %s", message)
        failures.append(message)


def validate_products(products: list[dict], failures: list[str]) -> None:
    required = ["product_id", "title", "category", "brand", "price", "final_price", "stock"]
    check(len(products) > 0, "le catalogue contient des produits", failures)
    check(
        all(p.get(k) not in (None, "") for p in products for k in required),
        "les champs obligatoires des produits sont renseignés",
        failures,
    )
    ids = [p["product_id"] for p in products]
    check(len(ids) == len(set(ids)), "product_id est unique", failures)
    check(all(p["price"] >= 0 for p in products), "les prix sont positifs", failures)
    check(all(p["stock"] >= 0 for p in products), "les stocks sont positifs", failures)
    check(
        all(0 <= p["discount_percentage"] <= 100 for p in products),
        "les remises sont comprises entre 0 et 100 %",
        failures,
    )
    check(
        all(date.fromisoformat(r["date"]) <= date.today() for p in products for r in p["reviews"]),
        "les dates d'avis ne sont pas dans le futur",
        failures,
    )


def validate_sales(sales: list[dict], products: list[dict], failures: list[str]) -> None:
    product_ids = {p["product_id"] for p in products}
    check(len(sales) > 0, "les ventes contiennent des lignes", failures)
    check(
        all(s["product_id"] in product_ids for s in sales),
        "chaque vente correspond à un produit du catalogue",
        failures,
    )
    check(all(s["quantity"] > 0 for s in sales), "les quantités sont strictement positives", failures)
    check(
        all(abs(s["line_total"] - s["unit_price"] * s["quantity"]) < 0.01 for s in sales),
        "le total de chaque ligne = prix unitaire x quantité",
        failures,
    )


def validate() -> dict:
    products = json.loads((PROCESSED_DIR / "products.json").read_text(encoding="utf-8"))
    sales = json.loads((PROCESSED_DIR / "sales.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    validate_products(products, failures)
    validate_sales(sales, products, failures)
    if failures:
        raise DataQualityError(f"{len(failures)} contrôle(s) en échec : {failures}")
    log.info("Tous les contrôles qualité sont passés")
    return {"products": len(products), "sales": len(sales)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(validate())
