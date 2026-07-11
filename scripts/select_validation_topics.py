#!/usr/bin/env python3

import json
from datetime import datetime, timezone
from pathlib import Path


INPUT_FILE = Path(
    "data/trends/product-validation-queue.json"
)

OUTPUT_FILE = Path(
    "data/trends/current-validation-batch.json"
)

BATCH_SIZE = 10
MAX_SEASONAL_TOPICS = 3
MAX_EV_DIVERSITY_SLOTS = 2
MIN_EV_DIVERSITY_SCORE = 45.0


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def main():
    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    opportunities = [
        item
        for item in data["opportunities"]
        if item["accepted_signal_count"] > 0
        and item["validation_status"] == "pending"
    ]

    selected = []
    selected_topics = set()

    def add_item(item, reason):
        topic_key = item["normalized_topic"]

        if topic_key in selected_topics:
            return False

        record = dict(item)
        record["selection_reason"] = reason

        selected.append(record)
        selected_topics.add(topic_key)

        return True

    # Phase 1:
    # Add up to 2 reasonably strong EV topics
    # for category diversity.
    ev_candidates = [
        item
        for item in opportunities
        if "ev" in item["categories"]
        and item["pre_validation_score"]
        >= MIN_EV_DIVERSITY_SCORE
    ]

    for item in ev_candidates[:MAX_EV_DIVERSITY_SLOTS]:
        add_item(item, "ev_diversity")

    # Phase 2:
    # Fill remaining slots by score while limiting
    # seasonal-topic concentration.
    seasonal_count = sum(
        bool(item["seasonality"])
        for item in selected
    )

    for item in opportunities:
        if len(selected) >= BATCH_SIZE:
            break

        if item["normalized_topic"] in selected_topics:
            continue

        is_seasonal = bool(item["seasonality"])

        if (
            is_seasonal
            and seasonal_count >= MAX_SEASONAL_TOPICS
        ):
            continue

        if add_item(item, "score_priority"):
            if is_seasonal:
                seasonal_count += 1

    # Phase 3:
    # Safety fallback. Fill any remaining slots
    # without seasonal limit.
    for item in opportunities:
        if len(selected) >= BATCH_SIZE:
            break

        if add_item(item, "fallback_score_priority"):
            pass

    # Final batch order should follow opportunity score,
    # not phase insertion order.
    selected.sort(
        key=lambda item: (
            -item["pre_validation_score"],
            item["validation_priority"],
        )
    )

    for index, item in enumerate(selected, 1):
        item["batch_priority"] = index

    output = {
        "source": "driverz_validation_batch_selection",
        "selector_version": 1,
        "generated_at": utc_now(),
        "source_scorer_version": data["scorer_version"],
        "batch_size_requested": BATCH_SIZE,
        "selected_topic_count": len(selected),
        "selection_policy": {
            "max_seasonal_topics":
                MAX_SEASONAL_TOPICS,
            "max_ev_diversity_slots":
                MAX_EV_DIVERSITY_SLOTS,
            "min_ev_diversity_score":
                MIN_EV_DIVERSITY_SCORE,
            "exclude_zero_signal_topics": True,
            "exclude_non_pending_topics": True,
        },
        "topics": selected,
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
        "===== Driverz Validation Batch Selector v1 ====="
    )
    print("Eligible topics:", len(opportunities))
    print("Selected topics:", len(selected))
    print("Saved:", OUTPUT_FILE)

    print("\n===== CURRENT VALIDATION BATCH =====")

    for item in selected:
        print(
            item["batch_priority"],
            "| opportunity_priority=",
            item["validation_priority"],
            "| score=",
            item["pre_validation_score"],
            "| category=",
            ",".join(item["categories"]),
            "| season=",
            ",".join(item["seasonality"]) or "-",
            "| reason=",
            item["selection_reason"],
            "|",
            item["topic"],
        )


if __name__ == "__main__":
    main()
