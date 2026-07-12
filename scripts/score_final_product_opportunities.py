#!/usr/bin/env python3

import json
from datetime import datetime, timezone
from pathlib import Path


OPPORTUNITY_FILE = Path(
    "data/trends/product-validation-queue.json"
)

VALIDATION_FILE = Path(
    "data/affiliate/validation/scored/"
    "aliexpress_topic_validation_scores.json"
)

OUTPUT_FILE = Path(
    "data/trends/final-product-opportunities.json"
)


DEMAND_WEIGHT = 0.40
VALIDATION_WEIGHT = 0.60

PROMOTE_THRESHOLD = 75.0
APPROVED_THRESHOLD = 65.0


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize_topic(value):
    return str(value).strip().lower()


def make_decision(validation_status, final_score):
    if validation_status == "rejected":
        return {
            "final_status": "rejected",
            "production_eligible": False,
            "decision_reason": "failed_product_validation",
        }

    if validation_status == "watch":
        return {
            "final_status": "watch",
            "production_eligible": False,
            "decision_reason": "insufficient_supply_quality",
        }

    if validation_status != "validated":
        return {
            "final_status": "watch",
            "production_eligible": False,
            "decision_reason": "unknown_validation_status",
        }

    if final_score >= PROMOTE_THRESHOLD:
        return {
            "final_status": "promote",
            "production_eligible": True,
            "decision_reason":
                "strong_demand_and_validated_supply",
        }

    if final_score >= APPROVED_THRESHOLD:
        return {
            "final_status": "approved",
            "production_eligible": True,
            "decision_reason":
                "validated_commercial_opportunity",
        }

    return {
        "final_status": "watch",
        "production_eligible": False,
        "decision_reason":
            "combined_opportunity_score_below_threshold",
    }


def main():
    opportunity_data = json.loads(
        OPPORTUNITY_FILE.read_text(encoding="utf-8")
    )

    validation_data = json.loads(
        VALIDATION_FILE.read_text(encoding="utf-8")
    )

    opportunities = {
        item["normalized_topic"]: item
        for item in opportunity_data["opportunities"]
    }

    validation_results = validation_data["topics"]

    results = []
    missing_opportunities = []

    for validation in validation_results:
        topic = validation["topic"]
        normalized_topic = normalize_topic(topic)

        opportunity = opportunities.get(normalized_topic)

        if opportunity is None:
            missing_opportunities.append(topic)
            continue

        demand_score = float(
            opportunity["pre_validation_score"]
        )

        product_validation_score = float(
            validation["product_validation_score"]
        )

        final_score = round(
            demand_score * DEMAND_WEIGHT
            + product_validation_score * VALIDATION_WEIGHT,
            2,
        )

        decision = make_decision(
            validation["validation_status"],
            final_score,
        )

        result = {
            "topic": topic,
            "normalized_topic": normalized_topic,
            "categories": opportunity["categories"],
            "seasonality": opportunity["seasonality"],
            "validation_priority":
                opportunity["validation_priority"],
            "pre_validation_score": demand_score,
            "product_validation_score":
                product_validation_score,
            "final_opportunity_score": final_score,
            "validation_status":
                validation["validation_status"],
            "final_status": decision["final_status"],
            "production_eligible":
                decision["production_eligible"],
            "decision_reason":
                decision["decision_reason"],
            "accepted_signal_count":
                opportunity["accepted_signal_count"],
            "commercial_signal_count":
                opportunity["commercial_signal_count"],
            "validation_metrics": {
                "raw_product_count":
                    validation["raw_product_count"],
                "unique_product_count":
                    validation["unique_product_count"],
                "relevant_product_count":
                    validation["relevant_product_count"],
                "quality_product_count":
                    validation["quality_product_count"],
                "relevant_product_rate":
                    validation["relevant_product_rate"],
                "quality_product_rate":
                    validation["quality_product_rate"],
                "average_sales_score":
                    validation["average_sales_score"],
                "average_commission_rate":
                    validation["average_commission_rate"],
                "average_estimated_commission":
                    validation["average_estimated_commission"],
                "promotion_link_coverage":
                    validation["promotion_link_coverage"],
                "overlap_rate":
                    validation["overlap_rate"],
                "availability_score":
                    validation["availability_score"],
            },
        }

        results.append(result)

    results.sort(
        key=lambda item: (
            item["production_eligible"],
            item["final_opportunity_score"],
            -item["validation_priority"],
        ),
        reverse=True,
    )

    for index, item in enumerate(results, 1):
        item["final_priority"] = index

    status_counts = {}

    for item in results:
        status = item["final_status"]

        status_counts[status] = (
            status_counts.get(status, 0) + 1
        )

    production_eligible_count = sum(
        item["production_eligible"]
        for item in results
    )

    output = {
        "source": "driverz_final_product_opportunity_scoring",
        "scorer_version": 1,
        "generated_at": utc_now(),
        "source_opportunity_scorer_version":
            opportunity_data["scorer_version"],
        "source_validation_scorer_version":
            validation_data["scorer_version"],
        "scoring_policy": {
            "demand_weight": DEMAND_WEIGHT,
            "product_validation_weight": VALIDATION_WEIGHT,
            "promote_threshold": PROMOTE_THRESHOLD,
            "approved_threshold": APPROVED_THRESHOLD,
            "validation_hard_gate": True,
        },
        "input_validation_topic_count":
            len(validation_results),
        "scored_topic_count": len(results),
        "missing_opportunity_count":
            len(missing_opportunities),
        "missing_opportunities":
            missing_opportunities,
        "production_eligible_count":
            production_eligible_count,
        "status_counts": status_counts,
        "opportunities": results,
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
        "===== Driverz Final Product Opportunity Scorer v1 ====="
    )
    print(
        "Validation topics:",
        len(validation_results),
    )
    print("Topics scored:", len(results))
    print(
        "Missing opportunities:",
        len(missing_opportunities),
    )
    print(
        "Production eligible:",
        production_eligible_count,
    )
    print("Saved:", OUTPUT_FILE)

    print("\n===== FINAL OPPORTUNITY RESULTS =====")

    for item in results:
        print(
            item["final_priority"],
            "| final=",
            item["final_opportunity_score"],
            "| demand=",
            item["pre_validation_score"],
            "| validation=",
            item["product_validation_score"],
            "| status=",
            item["final_status"],
            "| eligible=",
            item["production_eligible"],
            "|",
            item["topic"],
        )


if __name__ == "__main__":
    main()
