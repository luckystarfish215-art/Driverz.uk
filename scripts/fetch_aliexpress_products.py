#!/usr/bin/env python3

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


API_BASE_URL = "https://api-sg.aliexpress.com"
API_PATH = "/sync"
API_METHOD = "aliexpress.affiliate.product.query"

ENV_FILE = Path(
    "/var/services/homes/Mark/driverz-automation/driverz.env"
)

CONFIG_FILE = Path("config/aliexpress_keywords.json")

OUTPUT_FILE = Path(
    "data/affiliate/raw/aliexpress_products.json"
)


def load_env_file(path):
    if not path.exists():
        raise FileNotFoundError(f"Environment file not found: {path}")

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()

        if name and name not in os.environ:
            os.environ[name] = value


def load_config(path):
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    config = json.loads(path.read_text(encoding="utf-8"))

    enabled_keywords = [
        item
        for item in config.get("keywords", [])
        if item.get("enabled") is True
    ]

    if not enabled_keywords:
        raise RuntimeError("No enabled AliExpress keywords found")

    return config, enabled_keywords


def generate_sign(params, app_secret):
    sign_content = "".join(
        f"{key}{params[key]}"
        for key in sorted(params)
        if params[key] is not None
    )

    return hmac.new(
        app_secret.encode("utf-8"),
        sign_content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()


def call_api(
    app_key,
    app_secret,
    keyword,
    page_size,
    sort,
    ship_to_country,
    target_currency,
    target_language,
):
    timestamp = int(time.time() * 1000)

    params = {
        "app_key": app_key,
        "method": API_METHOD,
        "sign_method": "sha256",
        "timestamp": str(timestamp),
        "v": "2.0",
        "format": "json",
        "simplify": "true",
        "keywords": keyword,
        "page_no": "1",
        "page_size": str(page_size),
        "platform_product_type": "ALL",
        "sort": sort,
        "target_currency": target_currency,
        "target_language": target_language,
        "ship_to_country": ship_to_country,
    }

    params["sign"] = generate_sign(params, app_secret)

    request_url = (
        f"{API_BASE_URL}{API_PATH}?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        request_url,
        headers={
            "User-Agent": "Driverz-Affiliate-Collector/2.0",
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(
            response.read().decode("utf-8", errors="replace")
        )


def extract_products(response):
    if "error_response" in response:
        error = response["error_response"]

        raise RuntimeError(
            "AliExpress API error: "
            f"{error.get('code')} "
            f"{error.get('msg')} "
            f"{error.get('sub_code', '')}"
        )

    try:
        if "resp_result" in response:
            resp_result = response["resp_result"]
        else:
            root = response[
                "aliexpress_affiliate_product_query_response"
            ]
            resp_result = root["resp_result"]

        if int(resp_result["resp_code"]) != 200:
            raise RuntimeError(
                "AliExpress API error: "
                f"{resp_result.get('resp_code')} "
                f"{resp_result.get('resp_msg')}"
            )

        products_node = resp_result["result"].get("products", [])

        if isinstance(products_node, list):
            products = products_node

        elif isinstance(products_node, dict):
            products = products_node.get("product", [])

        else:
            raise TypeError(
                "Unexpected products type: "
                f"{type(products_node).__name__}"
            )

        if isinstance(products, dict):
            products = [products]

        return products

    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(
            "Unexpected AliExpress response structure:\n"
            + json.dumps(response, indent=2, ensure_ascii=False)
        ) from exc


def normalize_product(product):
    return {
        "product_id": str(product.get("product_id", "")),
        "product_title": product.get("product_title", ""),
        "product_main_image_url": product.get(
            "product_main_image_url", ""
        ),
        "product_small_image_urls": product.get(
            "product_small_image_urls", []
        ),
        "product_video_url": product.get(
            "product_video_url", ""
        ),
        "product_detail_url": product.get(
            "product_detail_url", ""
        ),
        "promotion_link": product.get("promotion_link", ""),
        "target_sale_price": product.get(
            "target_sale_price", ""
        ),
        "target_original_price": product.get(
            "target_original_price", ""
        ),
        "currency": product.get(
            "target_sale_price_currency", ""
        ),
        "discount": product.get("discount", ""),
        "sales_volume": product.get("lastest_volume", 0),
        "evaluate_rate": product.get("evaluate_rate", ""),
        "commission_rate": product.get(
            "commission_rate", ""
        ),
        "hot_product_commission_rate": product.get(
            "hot_product_commission_rate", ""
        ),
        "first_level_category_id": product.get(
            "first_level_category_id"
        ),
        "first_level_category_name": product.get(
            "first_level_category_name", ""
        ),
        "second_level_category_id": product.get(
            "second_level_category_id"
        ),
        "second_level_category_name": product.get(
            "second_level_category_name", ""
        ),
        "shop_id": product.get("shop_id"),
        "shop_name": product.get("shop_name", ""),
    }


def merge_product(
    product_pool,
    normalized_product,
    keyword,
    category,
):
    product_id = normalized_product["product_id"]

    if not product_id:
        return False

    if product_id not in product_pool:
        normalized_product["matched_keywords"] = [keyword]
        normalized_product["matched_categories"] = [category]

        product_pool[product_id] = normalized_product

        return True

    existing = product_pool[product_id]

    if keyword not in existing["matched_keywords"]:
        existing["matched_keywords"].append(keyword)

    if category not in existing["matched_categories"]:
        existing["matched_categories"].append(category)

    return False


def main():
    load_env_file(ENV_FILE)

    app_key = os.environ.get("ALIEXPRESS_APP_KEY")
    app_secret = os.environ.get("ALIEXPRESS_APP_SECRET")

    if not app_key:
        raise RuntimeError("ALIEXPRESS_APP_KEY is missing")

    if not app_secret:
        raise RuntimeError("ALIEXPRESS_APP_SECRET is missing")

    config, enabled_keywords = load_config(CONFIG_FILE)

    market = config["market"]
    collection = config["collection"]

    page_size = int(collection["page_size"])
    sort = collection["sort"]
    delay_seconds = float(collection.get("delay_seconds", 0))

    product_pool = {}
    collection_stats = []

    total_raw_results = 0

    print("===== Driverz AliExpress Collector v2 =====")
    print(f"Enabled keywords: {len(enabled_keywords)}")
    print(f"Page size: {page_size}")
    print()

    for index, item in enumerate(enabled_keywords, 1):
        keyword = item["keyword"]
        category = item["category"]

        print(
            f"[{index}/{len(enabled_keywords)}] "
            f"Collecting: {keyword}"
        )

        response = call_api(
            app_key=app_key,
            app_secret=app_secret,
            keyword=keyword,
            page_size=page_size,
            sort=sort,
            ship_to_country=market["ship_to_country"],
            target_currency=market["target_currency"],
            target_language=market["target_language"],
        )

        products = extract_products(response)

        raw_count = len(products)
        total_raw_results += raw_count

        new_products = 0

        for product in products:
            normalized = normalize_product(product)

            if merge_product(
                product_pool,
                normalized,
                keyword,
                category,
            ):
                new_products += 1

        duplicate_count = raw_count - new_products

        collection_stats.append(
            {
                "keyword": keyword,
                "category": category,
                "raw_count": raw_count,
                "new_unique_products": new_products,
                "duplicates_seen": duplicate_count,
            }
        )

        print(f"  Raw products: {raw_count}")
        print(f"  New unique products: {new_products}")
        print(f"  Duplicates seen: {duplicate_count}")
        print(f"  Product pool size: {len(product_pool)}")

        if index < len(enabled_keywords) and delay_seconds > 0:
            print(f"  Sleeping {delay_seconds:g}s...")
            time.sleep(delay_seconds)

        print()

    products = list(product_pool.values())

    multi_keyword_products = sum(
        1
        for product in products
        if len(product["matched_keywords"]) > 1
    )

    output = {
        "source": "aliexpress_affiliate_api",
        "api_method": API_METHOD,
        "collector_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": market,
        "collection": {
            "page_size": page_size,
            "sort": sort,
            "enabled_keyword_count": len(enabled_keywords),
            "total_raw_results": total_raw_results,
            "unique_product_count": len(products),
            "multi_keyword_product_count": multi_keyword_products,
        },
        "collection_stats": collection_stats,
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_file = OUTPUT_FILE.with_suffix(".json.tmp")

    temp_file.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    temp_file.replace(OUTPUT_FILE)

    print("===== COLLECTION COMPLETE =====")
    print(f"Total raw results: {total_raw_results}")
    print(f"Unique products: {len(products)}")
    print(
        "Products matched by multiple keywords: "
        f"{multi_keyword_products}"
    )
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
