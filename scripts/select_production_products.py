#!/usr/bin/env python3

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))

import score_aliexpress_products as scorer


QUEUE_FILE = Path(
    "data/content/production-topic-queue.json"
)

PRODUCT_FILE = Path(
    "data/affiliate/validation/raw/"
    "aliexpress_validation_products.json"
)

OUTPUT_FILE = Path(
    "data/content/production-products.json"
)


MIN_RATING = 90.0
MIN_RELEVANCE = 70.0

CANDIDATE_POOL_SIZE = 10
TARGET_PRODUCTS_PER_TOPIC = 5
MIN_PRODUCTS_PER_TOPIC = 3


PRODUCTION_NEGATIVE_TERMS = {
    "car travel pillow": [
        "tablet mount",
        "tablet holder",
        "ipad mount",
        "ipad holder",
        "phone holder",
        "headrest hook",
    ],
    "car armrest cushion": [
        "knee cushion",
        "knee pad",
        "door armrest pad",
    ],
    "car food tray": [
        "toy",
        "miniature",
        "replacement part",
    ],
    "wireless car charger": [
        "charging cable only",
        "replacement cable",
        "adapter only",
    ],
    "car windscreen cover": [
        "sticker",
        "decal",
        "replacement part",
    ],
    "car window sun shade": [
        "sticker",
        "decal",
        "replacement part",
    ],
    "ev charging cable bag": [
        "cable only",
        "charging cable only",
        "adapter only",
    ],
}


def has_production_negative_term(title, topic):
    title_lower = str(title).lower()

    return any(
        term in title_lower
        for term in PRODUCTION_NEGATIVE_TERMS.get(
            normalize(topic),
            [],
        )
    )


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    return str(value).strip().lower()


def main():
    queue_data = json.loads(
        QUEUE_FILE.read_text(encoding="utf-8")
    )

    product_data = json.loads(
        PRODUCT_FILE.read_text(encoding="utf-8")
    )

    queue_topics = [
        item
        for item in queue_data["topics"]
        if item["production_status"] == "pending"
    ]

    products = product_data["products"]

    candidate_pools = {}
    rejected_counts = {}

    for topic_item in queue_topics:
        topic = topic_item["topic"]
        topic_key = normalize(topic)

        ranked = []

        rejected_low_rating = 0
        rejected_missing_promotion_link = 0
        rejected_low_relevance = 0
        rejected_negative_term = 0

        for product in products:
            matched_topics = {
                normalize(value)
                for value in product.get(
                    "matched_validation_topics",
                    [],
                )
            }

            if topic_key not in matched_topics:
                continue

            rating = scorer.parse_percent(
                product.get("evaluate_rate")
            )

            if rating < MIN_RATING:
                rejected_low_rating += 1
                continue

            if not product.get("promotion_link"):
                rejected_missing_promotion_link += 1
                continue

            if has_production_negative_term(
                product.get("product_title", ""),
                topic,
            ):
                rejected_negative_term += 1
                continue

            breakdown = scorer.score_product_for_keyword(
                product,
                topic,
            )

            if breakdown["relevance"] < MIN_RELEVANCE:
                rejected_low_relevance += 1
                continue

            candidate = dict(product)

            candidate["selection_topic"] = topic
            candidate["selection_score"] = breakdown["score"]
            candidate["score_breakdown"] = breakdown

            candidate["estimated_commission_value"] = round(
                scorer.estimated_commission_value(product),
                4,
            )

            ranked.append(candidate)

        ranked.sort(
            key=lambda product: (
                product["selection_score"],
                product["estimated_commission_value"],
                scorer.parse_int(
                    product.get("sales_volume")
                ),
            ),
            reverse=True,
        )

        candidate_pools[topic_key] = ranked[
            :CANDIDATE_POOL_SIZE
        ]

        rejected_counts[topic_key] = {
            "rejected_low_rating":
                rejected_low_rating,
            "rejected_missing_promotion_link":
                rejected_missing_promotion_link,
            "rejected_low_relevance":
                rejected_low_relevance,
            "rejected_negative_term":
                rejected_negative_term,
            "eligible_before_pool_limit":
                len(ranked),
            "candidate_pool_count":
                min(len(ranked), CANDIDATE_POOL_SIZE),
        }

    used_product_ids = set()
    selections_by_topic = {}

    # Phase 1:
    # Allocate globally unique products according to
    # production priority.
    for topic_item in queue_topics:
        topic = topic_item["topic"]
        topic_key = normalize(topic)

        selected = []

        for product in candidate_pools[topic_key]:
            if len(selected) >= TARGET_PRODUCTS_PER_TOPIC:
                break

            product_id = str(product["product_id"])

            if product_id in used_product_ids:
                continue

            record = dict(product)
            record["selection_reason"] = "unique_priority"
            record["shared_product"] = False

            selected.append(record)
            used_product_ids.add(product_id)

        selections_by_topic[topic_key] = selected

    # Phase 2:
    # Guarantee minimum product coverage.
    # Reuse products only when deduplication leaves
    # a topic below MIN_PRODUCTS_PER_TOPIC.
    for topic_item in queue_topics:
        topic = topic_item["topic"]
        topic_key = normalize(topic)

        selected = selections_by_topic[topic_key]

        if len(selected) >= MIN_PRODUCTS_PER_TOPIC:
            continue

        selected_ids = {
            str(product["product_id"])
            for product in selected
        }

        for product in candidate_pools[topic_key]:
            if len(selected) >= MIN_PRODUCTS_PER_TOPIC:
                break

            product_id = str(product["product_id"])

            if product_id in selected_ids:
                continue

            record = dict(product)
            record["selection_reason"] = "shared_fallback"
            record["shared_product"] = True

            selected.append(record)
            selected_ids.add(product_id)

    # Final per-topic ranking and compact output.
    output_topics = []

    for topic_item in queue_topics:
        topic = topic_item["topic"]
        topic_key = normalize(topic)

        selected = selections_by_topic[topic_key]

        selected.sort(
            key=lambda product: (
                product["selection_score"],
                product["estimated_commission_value"],
                scorer.parse_int(
                    product.get("sales_volume")
                ),
            ),
            reverse=True,
        )

        compact_products = []

        for index, product in enumerate(selected, 1):
            compact_products.append({
                "product_rank": index,
                "product_id":
                    product["product_id"],
                "product_title":
                    product["product_title"],
                "product_main_image_url":
                    product["product_main_image_url"],
                "product_detail_url":
                    product["product_detail_url"],
                "promotion_link":
                    product["promotion_link"],
                "target_sale_price":
                    product["target_sale_price"],
                "currency":
                    product["currency"],
                "sales_volume":
                    product["sales_volume"],
                "evaluate_rate":
                    product["evaluate_rate"],
                "commission_rate":
                    product["commission_rate"],
                "estimated_commission_value":
                    product[
                        "estimated_commission_value"
                    ],
                "shop_id":
                    product["shop_id"],
                "shop_name":
                    product["shop_name"],
                "matched_validation_topics":
                    product[
                        "matched_validation_topics"
                    ],
                "selection_score":
                    product["selection_score"],
                "score_breakdown":
                    product["score_breakdown"],
                "selection_reason":
                    product["selection_reason"],
                "shared_product":
                    product["shared_product"],
            })

        output_topics.append({
            "production_priority":
                topic_item["production_priority"],
            "topic": topic,
            "normalized_topic": topic_key,
            "production_action":
                topic_item["production_action"],
            "final_opportunity_score":
                topic_item["final_opportunity_score"],
            "candidate_stats":
                rejected_counts[topic_key],
            "selected_product_count":
                len(compact_products),
            "products":
                compact_products,
        })

    selected_occurrences = [
        product
        for topic in output_topics
        for product in topic["products"]
    ]

    product_occurrence_counts = Counter(
        str(product["product_id"])
        for product in selected_occurrences
    )

    unique_selected_product_count = len(
        product_occurrence_counts
    )

    shared_product_ids = sorted(
        product_id
        for product_id, count
        in product_occurrence_counts.items()
        if count > 1
    )

    topics_below_minimum = [
        topic["topic"]
        for topic in output_topics
        if topic["selected_product_count"]
        < MIN_PRODUCTS_PER_TOPIC
    ]

    output = {
        "source":
            "driverz_production_product_selection",
        "selector_version": 1,
        "generated_at": utc_now(),
        "source_queue_version":
            queue_data["queue_version"],
        "source_validator_version":
            product_data["validator_version"],
        "selection_policy": {
            "min_rating": MIN_RATING,
            "min_relevance": MIN_RELEVANCE,
            "candidate_pool_size":
                CANDIDATE_POOL_SIZE,
            "target_products_per_topic":
                TARGET_PRODUCTS_PER_TOPIC,
            "min_products_per_topic":
                MIN_PRODUCTS_PER_TOPIC,
            "global_cross_topic_deduplication":
                True,
            "shared_fallback_below_minimum":
                True,
        },
        "input_queue_topic_count":
            len(queue_topics),
        "output_topic_count":
            len(output_topics),
        "selected_product_occurrence_count":
            len(selected_occurrences),
        "unique_selected_product_count":
            unique_selected_product_count,
        "shared_product_count":
            len(shared_product_ids),
        "shared_product_ids":
            shared_product_ids,
        "topics_below_minimum_count":
            len(topics_below_minimum),
        "topics_below_minimum":
            topics_below_minimum,
        "topics":
            output_topics,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = OUTPUT_FILE.with_suffix(
        ".json.tmp"
    )

    temp_file.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    temp_file.replace(OUTPUT_FILE)

    print(
        "===== Driverz Production Product Selector v1 ====="
    )
    print("Queue topics:", len(queue_topics))
    print(
        "Selected product occurrences:",
        len(selected_occurrences),
    )
    print(
        "Unique selected products:",
        unique_selected_product_count,
    )
    print(
        "Shared products:",
        len(shared_product_ids),
    )
    print(
        "Topics below minimum:",
        len(topics_below_minimum),
    )
    print("Saved:", OUTPUT_FILE)

    print("\n===== PRODUCT SELECTION RESULTS =====")

    for topic in output_topics:
        stats = topic["candidate_stats"]

        print(
            topic["production_priority"],
            "| selected=",
            topic["selected_product_count"],
            "| pool=",
            stats["candidate_pool_count"],
            "| eligible=",
            stats["eligible_before_pool_limit"],
            "| low_rating=",
            stats["rejected_low_rating"],
            "| low_relevance=",
            stats["rejected_low_relevance"],
            "| negative=",
            stats["rejected_negative_term"],
            "|",
            topic["topic"],
        )

        for product in topic["products"]:
            print(
                "   ",
                product["product_rank"],
                "| score=",
                product["selection_score"],
                "| sales=",
                product["sales_volume"],
                "| rating=",
                product["evaluate_rate"],
                "| commission=",
                product["commission_rate"],
                "| reason=",
                product["selection_reason"],
                "|",
                product["product_title"][:70],
            )


if __name__ == "__main__":
    main()
