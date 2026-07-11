#!/usr/bin/env python3

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


TOPIC_FILE = Path("data/trends/product-topic-candidates.json")
OUTPUT_FILE = Path("data/trends/uk-trend-signals.json")

RSS_URL = "https://trends.google.com/trending/rss?geo=GB"
AUTOCOMPLETE_URL = "https://suggestqueries.google.com/complete/search"

REQUEST_DELAY_SECONDS = 1.5
TIMEOUT_SECONDS = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    return " ".join(str(value).strip().lower().split())


def fetch_bytes(url):
    request = urllib.request.Request(url, headers=HEADERS)

    with urllib.request.urlopen(
        request,
        timeout=TIMEOUT_SECONDS,
    ) as response:
        return response.read()


def collect_rss():
    body = fetch_bytes(RSS_URL)
    root = ET.fromstring(body)

    signals = []

    for item in root.findall("./channel/item"):
        title = item.findtext("title", default="").strip()

        if not title:
            continue

        traffic = ""

        for child in item:
            if child.tag.endswith("approx_traffic"):
                traffic = (child.text or "").strip()

        signals.append({
            "query": title,
            "normalized_query": normalize(title),
            "source": "google_trends_uk_rss",
            "parent_topic": None,
            "suggestion_rank": None,
            "approx_traffic": traffic,
        })

    return signals


def collect_autocomplete(parent_topic):
    params = urllib.parse.urlencode({
        "client": "firefox",
        "q": parent_topic,
        "hl": "en",
        "gl": "uk",
    })

    body = fetch_bytes(
        AUTOCOMPLETE_URL + "?" + params
    )

    data = json.loads(body.decode("utf-8"))

    suggestions = data[1] if len(data) > 1 else []

    signals = []

    for rank, suggestion in enumerate(suggestions, 1):
        suggestion = str(suggestion).strip()

        if not suggestion:
            continue

        signals.append({
            "query": suggestion,
            "normalized_query": normalize(suggestion),
            "source": "google_autocomplete_uk",
            "parent_topic": parent_topic,
            "suggestion_rank": rank,
            "approx_traffic": None,
        })

    return signals


def main():
    topic_data = json.loads(
        TOPIC_FILE.read_text(encoding="utf-8")
    )

    parent_topics = [
        item["topic"]
        for item in topic_data["candidates"]
        if not item["already_in_affiliate_keywords"]
    ]

    print("===== Driverz Trend Signal Collector v1 =====")
    print("Autocomplete parent topics:", len(parent_topics))

    raw_signals = []

    print("\nCollecting Google Trends UK RSS...")
    rss_signals = collect_rss()
    raw_signals.extend(rss_signals)
    print("RSS signals:", len(rss_signals))

    autocomplete_stats = []

    for index, parent_topic in enumerate(parent_topics, 1):
        print(
            f"[{index}/{len(parent_topics)}] "
            f"Autocomplete: {parent_topic}"
        )

        try:
            signals = collect_autocomplete(parent_topic)

            raw_signals.extend(signals)

            autocomplete_stats.append({
                "parent_topic": parent_topic,
                "signal_count": len(signals),
                "status": "success",
            })

            print("  Signals:", len(signals))

        except Exception as exc:
            autocomplete_stats.append({
                "parent_topic": parent_topic,
                "signal_count": 0,
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

            print(
                "  ERROR:",
                type(exc).__name__,
                str(exc),
            )

        if index < len(parent_topics):
            time.sleep(REQUEST_DELAY_SECONDS)

    signal_pool = {}

    for signal in raw_signals:
        key = signal["normalized_query"]

        if not key:
            continue

        if key not in signal_pool:
            merged = dict(signal)
            merged["sources"] = [signal["source"]]
            merged["parent_topics"] = []

            if signal["parent_topic"]:
                merged["parent_topics"].append(
                    signal["parent_topic"]
                )

            signal_pool[key] = merged

        else:
            existing = signal_pool[key]

            if signal["source"] not in existing["sources"]:
                existing["sources"].append(signal["source"])

            if (
                signal["parent_topic"]
                and signal["parent_topic"]
                not in existing["parent_topics"]
            ):
                existing["parent_topics"].append(
                    signal["parent_topic"]
                )

            # Keep the best autocomplete rank seen.
            new_rank = signal["suggestion_rank"]
            old_rank = existing["suggestion_rank"]

            if (
                new_rank is not None
                and (
                    old_rank is None
                    or new_rank < old_rank
                )
            ):
                existing["suggestion_rank"] = new_rank

            # Preserve RSS traffic if available.
            if (
                not existing.get("approx_traffic")
                and signal.get("approx_traffic")
            ):
                existing["approx_traffic"] = (
                    signal["approx_traffic"]
                )

    signals = list(signal_pool.values())

    signals.sort(
        key=lambda item: (
            item["source"],
            item["normalized_query"],
        )
    )

    successful_autocomplete = sum(
        stat["status"] == "success"
        for stat in autocomplete_stats
    )

    failed_autocomplete = (
        len(autocomplete_stats)
        - successful_autocomplete
    )

    output = {
        "source": "driverz_trend_signal_collection",
        "collector_version": 1,
        "generated_at": utc_now(),
        "market": "UK",
        "raw_signal_count": len(raw_signals),
        "unique_signal_count": len(signals),
        "rss_signal_count": len(rss_signals),
        "autocomplete_parent_topic_count":
            len(parent_topics),
        "autocomplete_success_count":
            successful_autocomplete,
        "autocomplete_failure_count":
            failed_autocomplete,
        "autocomplete_stats": autocomplete_stats,
        "signals": signals,
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

    print("\n===== COLLECTION COMPLETE =====")
    print("Raw signals:", len(raw_signals))
    print("Unique signals:", len(signals))
    print("RSS signals:", len(rss_signals))
    print(
        "Autocomplete success:",
        successful_autocomplete,
    )
    print(
        "Autocomplete failures:",
        failed_autocomplete,
    )
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
