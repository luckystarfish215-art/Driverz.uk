#!/usr/bin/env python3

import json
import re
from datetime import datetime, timezone
from pathlib import Path


SEED_FILE = Path("config/trends/product_seed_topics.json")
AFFILIATE_KEYWORDS_FILE = Path("config/aliexpress_keywords.json")
OUTPUT_FILE = Path("data/trends/product-topic-candidates.json")


EXPANSIONS = {
    "car phone accessories": [
        "car phone holder",
        "magsafe car mount",
        "wireless car charger",
        "car phone charging cable",
        "car tablet holder",
    ],
    "car organisation": [
        "car boot organiser",
        "car seat organiser",
        "car storage organiser",
        "car seat gap filler",
        "car rubbish bin",
    ],
    "car cleaning": [
        "car cleaning brush",
        "car detailing brush",
        "car interior cleaning tools",
        "car windscreen cleaning tool",
        "car cleaning gel",
    ],
    "car comfort": [
        "car sun shade",
        "car seat cushion",
        "car neck pillow",
        "car armrest cushion",
        "car window shade",
    ],
    "winter car accessories": [
        "car windscreen cover",
        "car ice scraper",
        "car snow brush",
        "heated car seat cushion",
        "car demister pad",
    ],
    "summer car accessories": [
        "car sun shade",
        "car cooling seat cushion",
        "car window sun shade",
        "car dashboard sun cover",
        "car fan",
    ],
    "car travel accessories": [
        "car travel organiser",
        "car food tray",
        "car cup holder expander",
        "car headrest hook",
        "car travel pillow",
    ],
    "EV accessories": [
        "EV charging cable bag",
        "EV cable organiser",
        "EV charging port cover",
        "electric car screen protector",
        "EV tyre inflator",
    ],
}


SEASONALITY = {
    "winter car accessories": "winter",
    "summer car accessories": "summer",
}


def normalize_topic(value):
    return re.sub(
        r"\s+",
        " ",
        str(value).strip().lower(),
    )


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def main():
    seed_data = load_json(SEED_FILE)
    affiliate_data = load_json(AFFILIATE_KEYWORDS_FILE)

    existing_affiliate_keywords = {
        normalize_topic(item["keyword"])
        for item in affiliate_data.get("keywords", [])
        if item.get("enabled") is True
    }

    candidates = {}
    enabled_seed_count = 0

    for seed in seed_data.get("seed_topics", []):
        if seed.get("enabled") is not True:
            continue

        enabled_seed_count += 1

        seed_topic = seed["topic"]
        category = seed["category"]

        expanded_topics = EXPANSIONS.get(seed_topic, [])

        for topic in expanded_topics:
            normalized = normalize_topic(topic)

            if not normalized:
                continue

            if normalized not in candidates:
                candidates[normalized] = {
                    "topic": topic,
                    "normalized_topic": normalized,
                    "categories": [],
                    "source_seeds": [],
                    "seasonality": [],
                    "already_in_affiliate_keywords":
                        normalized in existing_affiliate_keywords,
                }

            candidate = candidates[normalized]

            if category not in candidate["categories"]:
                candidate["categories"].append(category)

            if seed_topic not in candidate["source_seeds"]:
                candidate["source_seeds"].append(seed_topic)

            season = SEASONALITY.get(seed_topic)

            if season and season not in candidate["seasonality"]:
                candidate["seasonality"].append(season)

    candidate_list = list(candidates.values())

    candidate_list.sort(
        key=lambda item: (
            item["already_in_affiliate_keywords"],
            item["normalized_topic"],
        )
    )

    new_topics = [
        item
        for item in candidate_list
        if not item["already_in_affiliate_keywords"]
    ]

    existing_topics = [
        item
        for item in candidate_list
        if item["already_in_affiliate_keywords"]
    ]

    output = {
        "source": "driverz_controlled_topic_expansion",
        "generator_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "market": seed_data["market"],
        "language": seed_data["language"],
        "topic_scope": seed_data["topic_scope"],
        "enabled_seed_count": enabled_seed_count,
        "candidate_count": len(candidate_list),
        "new_topic_count": len(new_topics),
        "existing_affiliate_keyword_count": len(existing_topics),
        "candidates": candidate_list,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

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

    print("===== Driverz Topic Candidate Generator v1 =====")
    print("Enabled seeds:", enabled_seed_count)
    print("Unique candidates:", len(candidate_list))
    print("New topics:", len(new_topics))
    print(
        "Already in affiliate keywords:",
        len(existing_topics),
    )
    print("Saved:", OUTPUT_FILE)

    print("\n===== NEW TOPIC CANDIDATES =====")

    for index, item in enumerate(new_topics, 1):
        seasons = (
            ",".join(item["seasonality"])
            if item["seasonality"]
            else "-"
        )

        print(
            index,
            "|",
            item["topic"],
            "| category=" + ",".join(item["categories"]),
            "| season=" + seasons,
        )

    print("\n===== EXISTING AFFILIATE KEYWORDS =====")

    for item in existing_topics:
        print("-", item["topic"])


if __name__ == "__main__":
    main()
