#!/usr/bin/env python3

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


INPUT_FILE = Path("data/trends/uk-trend-signals.json")
OUTPUT_FILE = Path("data/trends/filtered-trend-signals.json")


NOISE_PHRASES = {
    "near me",
    "nearby",
    "amazon",
    "ebay",
    "temu",
    "aliexpress",
    "kmart",
    "walmart",
    "hsn code",
    "meaning",
    "definition",
    "diy",
    "reddit",
    "3d print",
    "how to make",
    "homemade",
}


NON_UK_MARKET_TERMS = {
    "nz",
    "australia",
    "canada",
    "india",
    "usa",
    "us",
}


DRIVING_TERMS = {
    "car",
    "cars",
    "vehicle",
    "vehicles",
    "driving",
    "driver",
    "drivers",
    "automotive",
    "windscreen",
    "dashboard",
    "seat",
    "seats",
    "boot",
    "tyre",
    "tyres",
    "ev",
    "electric car",
    "electric vehicle",
    "magsafe car",
}


PRODUCT_INTENT_TERMS = {
    "holder",
    "mount",
    "charger",
    "cable",
    "organiser",
    "organizer",
    "brush",
    "cleaner",
    "cleaning",
    "gel",
    "shade",
    "cover",
    "cushion",
    "pillow",
    "scraper",
    "inflator",
    "tray",
    "hook",
    "bin",
    "fan",
    "protector",
    "accessory",
    "accessories",
    "storage",
    "tool",
    "tools",
    "pad",
    "filler",
    "shield",
    "visor",
    "kit",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    return " ".join(str(value).strip().lower().split())


def contains_phrase(text, phrase):
    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(phrase)
        + r"(?![a-z0-9])"
    )
    return re.search(pattern, text) is not None


def singularize_word(word):
    irregular = {
        "accessories": "accessory",
        "brushes": "brush",
        "hooks": "hook",
        "tools": "tool",
        "holders": "holder",
        "chargers": "charger",
        "cables": "cable",
        "organisers": "organiser",
        "organizers": "organizer",
        "shades": "shade",
        "covers": "cover",
        "cushions": "cushion",
        "pillows": "pillow",
        "scrapers": "scraper",
        "inflators": "inflator",
        "trays": "tray",
        "bins": "bin",
        "fans": "fan",
        "protectors": "protector",
        "seats": "seat",
        "cars": "car",
        "vehicles": "vehicle",
        "drivers": "driver",
        "tyres": "tyre",
    }

    return irregular.get(word, word)


def normalized_words(text):
    return " ".join(
        singularize_word(word)
        for word in text.split()
    )


def matching_terms(text, terms):
    normalized_text = normalized_words(text)

    return sorted(
        term
        for term in terms
        if (
            contains_phrase(text, term)
            or contains_phrase(normalized_text, term)
        )
    )


def classify_autocomplete(signal):
    query = normalize(signal["query"])

    noise_matches = matching_terms(query, NOISE_PHRASES)

    if noise_matches:
        return False, "noise_phrase", noise_matches

    market_matches = matching_terms(
        query,
        NON_UK_MARKET_TERMS,
    )

    if market_matches:
        return False, "non_uk_market", market_matches

    driving_matches = matching_terms(query, DRIVING_TERMS)

    if not driving_matches:
        return False, "no_driving_relevance", []

    product_matches = matching_terms(
        query,
        PRODUCT_INTENT_TERMS,
    )

    if not product_matches:
        return False, "no_product_intent", []

    return True, "accepted", sorted(
        set(driving_matches + product_matches)
    )


def classify_rss(signal):
    query = normalize(signal["query"])

    driving_matches = matching_terms(query, DRIVING_TERMS)

    if not driving_matches:
        return False, "no_driving_relevance", []

    return True, "accepted", driving_matches


def main():
    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    accepted_autocomplete = []
    rejected_autocomplete = []
    relevant_rss = []
    rejected_rss = []

    rejection_reasons = Counter()

    for signal in data["signals"]:
        sources = signal.get("sources", [])

        if "google_autocomplete_uk" in sources:
            accepted, reason, matches = (
                classify_autocomplete(signal)
            )

            record = dict(signal)
            record["filter_reason"] = reason
            record["matched_filter_terms"] = matches

            if accepted:
                accepted_autocomplete.append(record)
            else:
                rejected_autocomplete.append(record)
                rejection_reasons[
                    "autocomplete:" + reason
                ] += 1

        if "google_trends_uk_rss" in sources:
            accepted, reason, matches = classify_rss(signal)

            record = dict(signal)
            record["filter_reason"] = reason
            record["matched_filter_terms"] = matches

            if accepted:
                relevant_rss.append(record)
            else:
                rejected_rss.append(record)
                rejection_reasons[
                    "rss:" + reason
                ] += 1

    accepted_autocomplete.sort(
        key=lambda item: (
            item["suggestion_rank"]
            if item["suggestion_rank"] is not None
            else 999,
            item["normalized_query"],
        )
    )

    relevant_rss.sort(
        key=lambda item: item["normalized_query"]
    )

    output = {
        "source": "driverz_trend_signal_filter",
        "filter_version": 1,
        "generated_at": utc_now(),
        "input_unique_signal_count":
            data["unique_signal_count"],
        "accepted_autocomplete_count":
            len(accepted_autocomplete),
        "rejected_autocomplete_count":
            len(rejected_autocomplete),
        "relevant_rss_count":
            len(relevant_rss),
        "rejected_rss_count":
            len(rejected_rss),
        "rejection_reasons": dict(rejection_reasons),
        "accepted_autocomplete":
            accepted_autocomplete,
        "rejected_autocomplete":
            rejected_autocomplete,
        "relevant_rss":
            relevant_rss,
        "rejected_rss":
            rejected_rss,
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

    print("===== Driverz Trend Relevance Filter v1 =====")
    print(
        "Accepted autocomplete:",
        len(accepted_autocomplete),
    )
    print(
        "Rejected autocomplete:",
        len(rejected_autocomplete),
    )
    print("Relevant RSS:", len(relevant_rss))
    print("Rejected RSS:", len(rejected_rss))

    print("\n===== REJECTION REASONS =====")

    for reason, count in rejection_reasons.most_common():
        print(reason, ":", count)

    print("\n===== TOP ACCEPTED AUTOCOMPLETE =====")

    for index, item in enumerate(
        accepted_autocomplete[:30],
        1,
    ):
        print(
            index,
            "| rank=" + str(item["suggestion_rank"]),
            "|",
            item["query"],
            "| parents=",
            item["parent_topics"],
        )

    print("\n===== RELEVANT RSS =====")

    if relevant_rss:
        for item in relevant_rss:
            print(
                "-",
                item["query"],
                "| traffic=",
                item["approx_traffic"],
            )
    else:
        print("None")


if __name__ == "__main__":
    main()
