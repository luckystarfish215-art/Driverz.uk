#!/usr/bin/env python3

import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


TOPIC_FILE = Path(
    "data/trends/product-topic-candidates.json"
)

FILTERED_SIGNAL_FILE = Path(
    "data/trends/filtered-trend-signals.json"
)

OUTPUT_FILE = Path(
    "data/trends/product-validation-queue.json"
)


COMMERCIAL_TERMS = {
    "best",
    "price",
    "cost",
    "cheap",
    "kit",
    "with",
    "for",
    "wireless",
    "magnetic",
    "memory foam",
    "foldable",
    "universal",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    return " ".join(
        str(value).strip().lower().split()
    )


def contains_phrase(text, phrase):
    text = normalize(text)
    phrase = normalize(phrase)

    return (
        text == phrase
        or text.startswith(phrase + " ")
        or text.endswith(" " + phrase)
        or (" " + phrase + " ") in text
    )


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def main():
    topic_data = json.loads(
        TOPIC_FILE.read_text(encoding="utf-8")
    )

    signal_data = json.loads(
        FILTERED_SIGNAL_FILE.read_text(
            encoding="utf-8"
        )
    )

    topic_lookup = {
        normalize(item["topic"]): item
        for item in topic_data["candidates"]
        if not item["already_in_affiliate_keywords"]
    }

    signals_by_parent = defaultdict(list)

    for signal in signal_data["accepted_autocomplete"]:
        for parent in signal["parent_topics"]:
            key = normalize(parent)

            if key in topic_lookup:
                signals_by_parent[key].append(signal)

    opportunities = []

    for topic_key, topic in topic_lookup.items():
        signals = signals_by_parent.get(topic_key, [])

        unique_signals = {
            signal["normalized_query"]: signal
            for signal in signals
        }

        signals = list(unique_signals.values())

        signal_count = len(signals)

        # 10 suggestions is the expected maximum
        # from the current autocomplete collector.
        coverage_score = clamp(
            signal_count / 10.0 * 100.0
        )

        ranks = [
            signal["suggestion_rank"]
            for signal in signals
            if signal["suggestion_rank"] is not None
        ]

        if ranks:
            average_rank = sum(ranks) / len(ranks)

            # Rank 1 => 100, rank 10 => 10.
            rank_score = clamp(
                110.0 - average_rank * 10.0
            )
        else:
            average_rank = None
            rank_score = 0.0

        commercial_signal_count = 0
        matched_commercial_terms = set()

        for signal in signals:
            query = signal["normalized_query"]

            matches = {
                term
                for term in COMMERCIAL_TERMS
                if contains_phrase(query, term)
            }

            if matches:
                commercial_signal_count += 1
                matched_commercial_terms.update(matches)

        if signal_count:
            commercial_score = clamp(
                commercial_signal_count
                / signal_count
                * 100.0
            )
        else:
            commercial_score = 0.0

        seasons = topic.get("seasonality", [])

        # Seasonal topics receive a modest bonus,
        # not a dominant score.
        seasonality_score = (
            100.0 if seasons else 0.0
        )

        multi_parent_count = sum(
            1
            for signal in signals
            if len(signal["parent_topics"]) > 1
        )

        if signal_count:
            multi_parent_score = clamp(
                multi_parent_count
                / signal_count
                * 100.0
            )
        else:
            multi_parent_score = 0.0

        pre_validation_score = (
            coverage_score * 0.40
            + rank_score * 0.30
            + commercial_score * 0.15
            + seasonality_score * 0.10
            + multi_parent_score * 0.05
        )

        opportunities.append({
            "topic": topic["topic"],
            "normalized_topic":
                topic["normalized_topic"],
            "categories": topic["categories"],
            "source_seeds": topic["source_seeds"],
            "seasonality": seasons,
            "accepted_signal_count": signal_count,
            "average_suggestion_rank": (
                round(average_rank, 2)
                if average_rank is not None
                else None
            ),
            "commercial_signal_count":
                commercial_signal_count,
            "matched_commercial_terms":
                sorted(matched_commercial_terms),
            "multi_parent_signal_count":
                multi_parent_count,
            "score_breakdown": {
                "autocomplete_coverage":
                    round(coverage_score, 2),
                "autocomplete_rank":
                    round(rank_score, 2),
                "commercial_modifier":
                    round(commercial_score, 2),
                "seasonality":
                    round(seasonality_score, 2),
                "multi_parent_signal":
                    round(multi_parent_score, 2),
            },
            "pre_validation_score":
                round(pre_validation_score, 2),
            "validation_status": "pending",
        })

    opportunities.sort(
        key=lambda item: (
            -item["pre_validation_score"],
            -item["accepted_signal_count"],
            item["normalized_topic"],
        )
    )

    for index, item in enumerate(opportunities, 1):
        item["validation_priority"] = index

    output = {
        "source": "driverz_topic_opportunity_scoring",
        "scorer_version": 1,
        "generated_at": utc_now(),
        "market": "UK",
        "opportunity_count": len(opportunities),
        "score_type": "pre_product_validation",
        "score_weights": {
            "autocomplete_coverage": 0.40,
            "autocomplete_rank": 0.30,
            "commercial_modifier": 0.15,
            "seasonality": 0.10,
            "multi_parent_signal": 0.05,
        },
        "opportunities": opportunities,
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
        "===== Driverz Topic Opportunity Scorer v1 ====="
    )
    print("Topics scored:", len(opportunities))
    print("Saved:", OUTPUT_FILE)

    print("\n===== TOP 20 VALIDATION QUEUE =====")

    for item in opportunities[:20]:
        print(
            item["validation_priority"],
            "| score=",
            item["pre_validation_score"],
            "| signals=",
            item["accepted_signal_count"],
            "| avg_rank=",
            item["average_suggestion_rank"],
            "| commercial=",
            item["commercial_signal_count"],
            "| season=",
            ",".join(item["seasonality"]) or "-",
            "|",
            item["topic"],
        )


if __name__ == "__main__":
    main()
