#!/usr/bin/env python3

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


INPUT_FILE = Path(
    "data/trends/final-product-opportunities.json"
)

STRATEGY_FILE = Path(
    "config/content/product_topic_strategy.json"
)

OUTPUT_FILE = Path(
    "data/content/production-topic-queue.json"
)


VALID_ACTIONS = {
    "new_guide",
    "guide_cluster",
    "product_block",
    "hold",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    return str(value).strip().lower()


def main():
    opportunity_data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    strategy_data = json.loads(
        STRATEGY_FILE.read_text(encoding="utf-8")
    )

    default_action = strategy_data["default_action"]

    if default_action not in VALID_ACTIONS:
        raise ValueError(
            "Invalid default_action: "
            + str(default_action)
        )

    rules = {}

    for rule in strategy_data["rules"]:
        topic_key = normalize(rule["topic"])

        if topic_key in rules:
            raise ValueError(
                "Duplicate strategy rule: "
                + topic_key
            )

        if rule["action"] not in VALID_ACTIONS:
            raise ValueError(
                "Invalid action for "
                + topic_key
            )

        rules[topic_key] = rule

    eligible = [
        item
        for item in opportunity_data["opportunities"]
        if item["production_eligible"]
    ]

    queue = []

    for item in eligible:
        topic_key = normalize(item["topic"])

        rule = rules.get(topic_key, {})

        action = rule.get(
            "action",
            default_action,
        )

        record = {
            "topic": item["topic"],
            "normalized_topic": topic_key,
            "source_final_priority":
                item["final_priority"],
            "final_opportunity_score":
                item["final_opportunity_score"],
            "source_final_status":
                item["final_status"],
            "categories":
                item["categories"],
            "seasonality":
                item["seasonality"],
            "production_action":
                action,
            "strategy_source":
                (
                    "explicit_rule"
                    if topic_key in rules
                    else "default_rule"
                ),
            "production_status":
                (
                    "hold"
                    if action == "hold"
                    else "pending"
                ),
        }

        if action == "guide_cluster":
            cluster = rule.get("cluster")

            if not cluster:
                raise ValueError(
                    "Missing cluster for "
                    + item["topic"]
                )

            record["cluster"] = cluster

        if action == "product_block":
            target = rule.get("target")

            if not target:
                raise ValueError(
                    "Missing target for "
                    + item["topic"]
                )

            record["target"] = target

        queue.append(record)

    queue.sort(
        key=lambda item: (
            -item["final_opportunity_score"],
            item["source_final_priority"],
        )
    )

    for index, item in enumerate(queue, 1):
        item["production_priority"] = index

    action_counts = Counter(
        item["production_action"]
        for item in queue
    )

    status_counts = Counter(
        item["production_status"]
        for item in queue
    )

    output = {
        "source":
            "driverz_production_topic_queue",
        "queue_version": 1,
        "generated_at": utc_now(),
        "source_final_scorer_version":
            opportunity_data["scorer_version"],
        "strategy_version":
            strategy_data["version"],
        "input_eligible_topic_count":
            len(eligible),
        "queue_topic_count":
            len(queue),
        "action_counts":
            dict(action_counts),
        "status_counts":
            dict(status_counts),
        "topics": queue,
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
        "===== Driverz Production Topic Queue v1 ====="
    )
    print(
        "Eligible topics:",
        len(eligible),
    )
    print(
        "Queue topics:",
        len(queue),
    )
    print(
        "Action counts:",
        dict(action_counts),
    )
    print(
        "Saved:",
        OUTPUT_FILE,
    )

    print("\n===== PRODUCTION QUEUE =====")

    for item in queue:
        extra = "-"

        if item["production_action"] == "guide_cluster":
            extra = item["cluster"]

        elif item["production_action"] == "product_block":
            extra = item["target"]

        print(
            item["production_priority"],
            "| score=",
            item["final_opportunity_score"],
            "| action=",
            item["production_action"],
            "| strategy=",
            item["strategy_source"],
            "| target=",
            extra,
            "|",
            item["topic"],
        )


if __name__ == "__main__":
    main()
