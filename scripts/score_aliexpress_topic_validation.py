#!/usr/bin/env python3

import json
from datetime import datetime, timezone
from pathlib import Path

from score_aliexpress_products import (
    MIN_RATING,
    MIN_RELEVANCE,
    estimated_commission_value,
    keyword_relevance_score,
    parse_int,
    parse_percent,
    sales_score,
)


INPUT_FILE = Path(
    "data/affiliate/validation/raw/"
    "aliexpress_validation_products.json"
)

OUTPUT_FILE = Path(
    "data/affiliate/validation/scored/"
    "aliexpress_topic_validation_scores.json"
)


MIN_VALIDATED_SCORE = 65.0
MIN_WATCH_SCORE = 45.0


def clamp(value, minimum=0.0, maximum=100.0):
    return max(minimum, min(value, maximum))


def mean(values):
    if not values:
        return 0.0

    return sum(values) / len(values)


def main():
    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    products = data["products"]
    collection_stats = data["collection_stats"]

    results = []

    for stat in collection_stats:
        topic = stat["topic"]

        topic_products = [
            product
            for product in products
            if topic
            in product.get(
                "matched_validation_topics",
                [],
            )
        ]

        raw_count = stat["raw_count"]
        unique_count = len(topic_products)

        relevant_products = []
        quality_products = []

        for product in topic_products:
            relevance = keyword_relevance_score(
                product.get("product_title", ""),
                topic,
            )

            if relevance >= MIN_RELEVANCE:
                relevant_products.append(product)

                rating = parse_percent(
                    product.get("evaluate_rate")
                )

                if (
                    rating >= MIN_RATING
                    and product.get("promotion_link")
                ):
                    quality_products.append(product)

        relevant_count = len(relevant_products)
        quality_count = len(quality_products)

        relevant_product_rate = (
            relevant_count / unique_count * 100.0
            if unique_count
            else 0.0
        )

        quality_product_rate = (
            quality_count / relevant_count * 100.0
            if relevant_count
            else 0.0
        )

        promotion_link_coverage = (
            sum(
                bool(product.get("promotion_link"))
                for product in relevant_products
            )
            / relevant_count
            * 100.0
            if relevant_count
            else 0.0
        )

        average_sales_score = mean([
            sales_score(product.get("sales_volume"))
            for product in relevant_products
        ])

        average_commission_rate = mean([
            parse_percent(product.get("commission_rate"))
            for product in relevant_products
        ])

        commission_potential = clamp(
            average_commission_rate / 10.0 * 100.0
        )

        average_estimated_commission = mean([
            estimated_commission_value(product)
            for product in relevant_products
        ])

        multi_topic_count = sum(
            len(
                product.get(
                    "matched_validation_topics",
                    [],
                )
            ) > 1
            for product in topic_products
        )

        overlap_rate = (
            multi_topic_count / unique_count * 100.0
            if unique_count
            else 0.0
        )

        # Availability is intentionally capped.
        # 50 API results should not dominate scoring.
        availability_score = clamp(
            raw_count / 30.0 * 100.0
        )

        product_validation_score = (
            relevant_product_rate * 0.30
            + quality_product_rate * 0.20
            + average_sales_score * 0.20
            + commission_potential * 0.15
            + promotion_link_coverage * 0.10
            + availability_score * 0.05
        )

        product_validation_score = round(
            product_validation_score,
            2,
        )

        if product_validation_score >= MIN_VALIDATED_SCORE:
            validation_status = "validated"
        elif product_validation_score >= MIN_WATCH_SCORE:
            validation_status = "watch"
        else:
            validation_status = "rejected"

        results.append({
            "topic": topic,
            "normalized_topic": str(
                stat["topic"]
            ).strip().lower(),
            "batch_priority": stat["batch_priority"],
            "pre_validation_score": stat[
                "pre_validation_score"
            ],
            "raw_product_count": raw_count,
            "unique_product_count": unique_count,
            "relevant_product_count": relevant_count,
            "quality_product_count": quality_count,
            "relevant_product_rate": round(
                relevant_product_rate,
                2,
            ),
            "quality_product_rate": round(
                quality_product_rate,
                2,
            ),
            "average_sales_score": round(
                average_sales_score,
                2,
            ),
            "average_commission_rate": round(
                average_commission_rate,
                2,
            ),
            "commission_potential": round(
                commission_potential,
                2,
            ),
            "average_estimated_commission": round(
                average_estimated_commission,
                4,
            ),
            "promotion_link_coverage": round(
                promotion_link_coverage,
                2,
            ),
            "multi_topic_product_count":
                multi_topic_count,
            "overlap_rate": round(
                overlap_rate,
                2,
            ),
            "availability_score": round(
                availability_score,
                2,
            ),
            "product_validation_score":
                product_validation_score,
            "validation_status": validation_status,
        })

    results.sort(
        key=lambda item: (
            item["product_validation_score"],
            item["pre_validation_score"],
        ),
        reverse=True,
    )

    for index, item in enumerate(results, 1):
        item["product_validation_rank"] = index

    status_counts = {
        "validated": sum(
            item["validation_status"] == "validated"
            for item in results
        ),
        "watch": sum(
            item["validation_status"] == "watch"
            for item in results
        ),
        "rejected": sum(
            item["validation_status"] == "rejected"
            for item in results
        ),
    }

    output = {
        "source":
            "driverz_aliexpress_topic_validation_scoring",
        "scorer_version": 1,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_generated_at": data["generated_at"],
        "source_validator_version":
            data["validator_version"],
        "production_scorer_compatibility": {
            "min_rating": MIN_RATING,
            "min_relevance": MIN_RELEVANCE,
            "relevance_function":
                "keyword_relevance_score",
            "sales_function": "sales_score",
            "estimated_commission_function":
                "estimated_commission_value",
        },
        "scoring_policy": {
            "relevant_product_rate_weight": 0.30,
            "quality_product_rate_weight": 0.20,
            "sales_strength_weight": 0.20,
            "commission_potential_weight": 0.15,
            "promotion_link_coverage_weight": 0.10,
            "availability_weight": 0.05,
            "validated_score_threshold":
                MIN_VALIDATED_SCORE,
            "watch_score_threshold":
                MIN_WATCH_SCORE,
        },
        "topic_count": len(results),
        "status_counts": status_counts,
        "topics": results,
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

    print(
        "===== Driverz AliExpress Topic "
        "Validation Scorer v1 ====="
    )
    print("Topics scored:", len(results))
    print("Validated:", status_counts["validated"])
    print("Watch:", status_counts["watch"])
    print("Rejected:", status_counts["rejected"])
    print("Saved:", OUTPUT_FILE)

    print("\n===== TOPIC VALIDATION RESULTS =====")

    for item in results:
        print(
            item["product_validation_rank"],
            "| score=",
            item["product_validation_score"],
            "| relevant=",
            str(item["relevant_product_count"])
            + "/"
            + str(item["unique_product_count"]),
            "| quality=",
            item["quality_product_count"],
            "| sales=",
            item["average_sales_score"],
            "| commission=",
            str(item["average_commission_rate"]) + "%",
            "| overlap=",
            str(item["overlap_rate"]) + "%",
            "| status=",
            item["validation_status"],
            "|",
            item["topic"],
        )


if __name__ == "__main__":
    main()
