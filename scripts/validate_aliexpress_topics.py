#!/usr/bin/env python3

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(SCRIPT_DIR))

from fetch_aliexpress_products import (
    API_METHOD,
    ENV_FILE,
    call_api,
    extract_products,
    load_env_file,
    normalize_product,
)


BATCH_FILE = PROJECT_ROOT / (
    "data/trends/current-validation-batch.json"
)

AFFILIATE_CONFIG_FILE = PROJECT_ROOT / (
    "config/aliexpress_keywords.json"
)

OUTPUT_FILE = PROJECT_ROOT / (
    "data/affiliate/validation/raw/"
    "aliexpress_validation_products.json"
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def merge_validation_product(
    product_pool,
    normalized_product,
    topic,
    categories,
):
    product_id = normalized_product["product_id"]

    if not product_id:
        return False

    if product_id not in product_pool:
        normalized_product[
            "matched_validation_topics"
        ] = [topic]

        normalized_product[
            "matched_validation_categories"
        ] = list(categories)

        product_pool[product_id] = normalized_product

        return True

    existing = product_pool[product_id]

    if topic not in existing["matched_validation_topics"]:
        existing["matched_validation_topics"].append(topic)

    for category in categories:
        if (
            category
            not in existing["matched_validation_categories"]
        ):
            existing[
                "matched_validation_categories"
            ].append(category)

    return False


def main():
    load_env_file(ENV_FILE)

    app_key = os.environ.get("ALIEXPRESS_APP_KEY")
    app_secret = os.environ.get("ALIEXPRESS_APP_SECRET")

    if not app_key:
        raise RuntimeError("ALIEXPRESS_APP_KEY is missing")

    if not app_secret:
        raise RuntimeError("ALIEXPRESS_APP_SECRET is missing")

    batch_data = load_json(BATCH_FILE)
    config = load_json(AFFILIATE_CONFIG_FILE)

    topics = batch_data["topics"]

    if not topics:
        raise RuntimeError("Validation batch contains no topics")

    market = config["market"]
    collection = config["collection"]

    page_size = int(collection["page_size"])
    sort = collection["sort"]
    delay_seconds = float(
        collection.get("delay_seconds", 0)
    )

    product_pool = {}
    collection_stats = []

    total_raw_results = 0
    successful_topics = 0
    failed_topics = 0

    print(
        "===== Driverz AliExpress Topic Validator v1 ====="
    )
    print("Validation topics:", len(topics))
    print("Page size:", page_size)
    print()

    for index, item in enumerate(topics, 1):
        topic = item["topic"]
        categories = item["categories"]

        print(
            f"[{index}/{len(topics)}] "
            f"Validating: {topic}"
        )

        try:
            response = call_api(
                app_key=app_key,
                app_secret=app_secret,
                keyword=topic,
                page_size=page_size,
                sort=sort,
                ship_to_country=market["ship_to_country"],
                target_currency=market["target_currency"],
                target_language=market["target_language"],
            )

            products = extract_products(response)

        except Exception as exc:
            failed_topics += 1

            collection_stats.append({
                "topic": topic,
                "categories": categories,
                "opportunity_priority":
                    item["validation_priority"],
                "batch_priority":
                    item["batch_priority"],
                "pre_validation_score":
                    item["pre_validation_score"],
                "status": "failed",
                "error_type":
                    type(exc).__name__,
                "error_message": str(exc),
                "raw_count": 0,
                "new_unique_products": 0,
                "duplicates_seen": 0,
                "product_pool_size":
                    len(product_pool),
            })

            print(
                "  ERROR:",
                type(exc).__name__,
                str(exc),
            )
            print()

            continue

        successful_topics += 1

        raw_count = len(products)
        total_raw_results += raw_count

        new_products = 0

        for product in products:
            normalized = normalize_product(product)

            if merge_validation_product(
                product_pool,
                normalized,
                topic,
                categories,
            ):
                new_products += 1

        duplicate_count = raw_count - new_products

        collection_stats.append({
            "topic": topic,
            "categories": categories,
            "opportunity_priority":
                item["validation_priority"],
            "batch_priority":
                item["batch_priority"],
            "pre_validation_score":
                item["pre_validation_score"],
            "status": "success",
            "error_type": None,
            "error_message": None,
            "raw_count": raw_count,
            "new_unique_products": new_products,
            "duplicates_seen": duplicate_count,
            "product_pool_size":
                len(product_pool),
        })

        print(f"  Raw products: {raw_count}")
        print(f"  New unique products: {new_products}")
        print(f"  Duplicates seen: {duplicate_count}")
        print(f"  Product pool size: {len(product_pool)}")
        print()

        if (
            index < len(topics)
            and delay_seconds > 0
        ):
            print(f"  Sleeping {delay_seconds:g}s...")
            time.sleep(delay_seconds)
            print()

    products = list(product_pool.values())

    multi_topic_products = sum(
        1
        for product in products
        if len(
            product["matched_validation_topics"]
        ) > 1
    )

    output = {
        "source":
            "aliexpress_affiliate_api_topic_validation",
        "api_method": API_METHOD,
        "validator_version": 1,
        "generated_at": utc_now(),
        "source_batch_generated_at":
            batch_data["generated_at"],
        "source_selector_version":
            batch_data["selector_version"],
        "market": market,
        "validation": {
            "requested_topic_count": len(topics),
            "successful_topic_count": successful_topics,
            "failed_topic_count": failed_topics,
            "page_size": page_size,
            "sort": sort,
            "delay_seconds": delay_seconds,
            "total_raw_results": total_raw_results,
            "unique_product_count": len(products),
            "multi_topic_product_count":
                multi_topic_products,
        },
        "collection_stats": collection_stats,
        "products": products,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = OUTPUT_FILE.with_suffix(".json.tmp")

    temp_file.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    temp_file.replace(OUTPUT_FILE)

    print("===== VALIDATION COLLECTION COMPLETE =====")
    print("Successful topics:", successful_topics)
    print("Failed topics:", failed_topics)
    print("Total raw results:", total_raw_results)
    print("Unique products:", len(products))
    print(
        "Products matched by multiple topics:",
        multi_topic_products,
    )
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
