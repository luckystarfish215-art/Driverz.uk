#!/usr/bin/env python3

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


MANIFEST_FILE = Path(
    "data/content/drafts/draft-manifest.json"
)

OUTPUT_FILE = Path(
    "data/content/draft-reviews.json"
)

VALID_REVIEW_STATUSES = {
    "pending_review",
    "approved",
    "rejected",
    "changes_requested",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_value(value):
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def build_review_fingerprint(item):
    return sha256_value({
        "normalized_topic":
            item["normalized_topic"],
        "draft_file":
            item["draft_file"],
        "draft_fingerprint":
            item["draft_fingerprint"],
    })


def load_existing_reviews():
    if not OUTPUT_FILE.exists():
        return {}

    data = load_json(OUTPUT_FILE)

    return {
        item["normalized_topic"]: item
        for item in data.get("reviews", [])
    }


def build_review_item(result, existing):
    topic = result["normalized_topic"]

    draft_file = Path(result["draft_file"])

    if not draft_file.exists():
        raise ValueError(
            "Missing draft file for " + topic
        )

    draft = load_json(draft_file)

    if (
        draft["draft_fingerprint"]
        != result["draft_fingerprint"]
    ):
        raise ValueError(
            "Manifest/draft fingerprint mismatch for "
            + topic
        )

    source_identity = draft["source_identity"]

    if (
        source_identity["source_queue_priority"]
        != result["queue_priority"]
    ):
        raise ValueError(
            "Manifest/draft queue priority mismatch for "
            + topic
        )

    if (
        source_identity["brief_fingerprint"]
        != result["brief_fingerprint"]
    ):
        raise ValueError(
            "Manifest/draft brief fingerprint mismatch for "
            + topic
        )

    source = {
        "normalized_topic": topic,
        "draft_file": result["draft_file"],
        "draft_fingerprint":
            draft["draft_fingerprint"],
    }

    review_fingerprint = build_review_fingerprint(
        source
    )

    previous = existing.get(topic)

    review_status = "pending_review"
    review_reason = None
    reviewed_at = None

    if previous:
        same_source = (
            previous.get("draft_fingerprint")
            == result["draft_fingerprint"]
        )

        if same_source:
            previous_status = previous.get(
                "review_status"
            )

            if previous_status in VALID_REVIEW_STATUSES:
                review_status = previous_status
                review_reason = previous.get(
                    "review_reason"
                )
                reviewed_at = previous.get(
                    "reviewed_at"
                )

    return {
        "review_priority":
            result["queue_priority"],
        "source_queue_priority":
            result["queue_priority"],
        "source_brief_priority":
            source_identity["source_brief_priority"],
        "topic":
            result["topic"],
        "normalized_topic":
            topic,
        "production_action":
            result["production_action"],
        "content_type":
            result["content_type"],
        "routing_target":
            draft["routing_target"],
        "brief_fingerprint":
            source_identity["brief_fingerprint"],
        "draft_file":
            result["draft_file"],
        "draft_fingerprint":
            result["draft_fingerprint"],
        "review_fingerprint":
            review_fingerprint,
        "review_status":
            review_status,
        "review_reason":
            review_reason,
        "reviewed_at":
            reviewed_at,
        "publish_status":
            "not_published",
    }


def main():
    manifest = load_json(MANIFEST_FILE)

    results = manifest["drafts"]

    actionable = [
        item
        for item in results
        if item["result"] in {
            "created",
            "unchanged",
        }
    ]

    existing = load_existing_reviews()

    reviews = [
        build_review_item(item, existing)
        for item in actionable
    ]

    reviews.sort(
        key=lambda item:
            item["source_queue_priority"]
    )

    for index, item in enumerate(reviews, 1):
        item["review_priority"] = index

    status_counts = Counter(
        item["review_status"]
        for item in reviews
    )

    output = {
        "source":
            "driverz_draft_review_queue",
        "review_queue_version": 1,
        "generated_at": utc_now(),
        "source_generator_version":
            manifest["generator_version"],
        "source_draft_queue_version":
            manifest["source_draft_queue_version"],
        "input_draft_count":
            len(results),
        "actionable_draft_count":
            len(actionable),
        "review_count":
            len(reviews),
        "review_status_counts":
            dict(status_counts),
        "review_policy": {
            "requires_human_review": True,
            "approval_bound_to_draft_fingerprint":
                True,
            "source_change_resets_review":
                True,
            "automatic_approval_enabled": False,
            "automatic_publishing_enabled": False,
        },
        "reviews":
            reviews,
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
        "===== Driverz Draft Review Queue v1 ====="
    )
    print("Input drafts:", len(results))
    print("Actionable drafts:", len(actionable))
    print("Reviews:", len(reviews))
    print(
        "Review status counts:",
        dict(status_counts),
    )
    print("Saved:", OUTPUT_FILE)

    print("\n===== REVIEW QUEUE =====")

    for item in reviews:
        print(
            item["review_priority"],
            "| status=",
            item["review_status"],
            "| action=",
            item["production_action"],
            "| type=",
            item["content_type"],
            "|",
            item["topic"],
        )


if __name__ == "__main__":
    main()
