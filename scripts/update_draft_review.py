#!/usr/bin/env python3

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REVIEWS_FILE = Path(
    "data/content/draft-reviews.json"
)

VALID_ACTIONS = {
    "approve",
    "reject",
    "request-changes",
    "reset",
}

ACTION_TO_STATUS = {
    "approve": "approved",
    "reject": "rejected",
    "request-changes": "changes_requested",
    "reset": "pending_review",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


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


def expected_review_fingerprint(review):
    return sha256_value({
        "normalized_topic":
            review["normalized_topic"],
        "draft_file":
            review["draft_file"],
        "draft_fingerprint":
            review["draft_fingerprint"],
    })


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "action",
        choices=sorted(VALID_ACTIONS),
    )

    parser.add_argument(
        "topic",
    )

    parser.add_argument(
        "--reason",
        default=None,
    )

    return parser.parse_args()


def validate_reason(action, reason):
    if action == "reset":
        return

    if not reason or not reason.strip():
        raise ValueError(
            "--reason is required for " + action
        )


def validate_review_source(review):
    draft_file = Path(review["draft_file"])

    if not draft_file.exists():
        raise ValueError(
            "Draft file does not exist: "
            + str(draft_file)
        )

    draft = load_json(draft_file)

    if (
        draft["normalized_topic"]
        != review["normalized_topic"]
    ):
        raise ValueError(
            "Review/draft topic mismatch"
        )

    if (
        draft["draft_fingerprint"]
        != review["draft_fingerprint"]
    ):
        raise ValueError(
            "Review is stale: draft fingerprint changed"
        )

    expected = expected_review_fingerprint(
        review
    )

    if (
        review["review_fingerprint"]
        != expected
    ):
        raise ValueError(
            "Invalid review fingerprint"
        )

    return draft


def main():
    args = parse_args()

    validate_reason(
        args.action,
        args.reason,
    )

    data = load_json(REVIEWS_FILE)

    topic_key = args.topic.strip().lower()

    matches = [
        item
        for item in data["reviews"]
        if item["normalized_topic"] == topic_key
    ]

    if not matches:
        raise ValueError(
            "Unknown review topic: " + args.topic
        )

    if len(matches) != 1:
        raise ValueError(
            "Duplicate review topic: " + topic_key
        )

    review = matches[0]

    validate_review_source(review)

    new_status = ACTION_TO_STATUS[
        args.action
    ]

    review["review_status"] = new_status

    if args.action == "reset":
        review["review_reason"] = None
        review["reviewed_at"] = None
    else:
        review["review_reason"] = (
            args.reason.strip()
        )
        review["reviewed_at"] = utc_now()

    data["review_status_counts"] = dict(
        Counter(
            item["review_status"]
            for item in data["reviews"]
        )
    )

    data["generated_at"] = utc_now()

    temp_file = REVIEWS_FILE.with_suffix(
        ".json.tmp"
    )

    temp_file.write_text(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    temp_file.replace(REVIEWS_FILE)

    print("===== Driverz Draft Review Update v1 =====")
    print("Topic:", review["topic"])
    print("Action:", args.action)
    print("Review status:", new_status)
    print(
        "Draft fingerprint:",
        review["draft_fingerprint"],
    )
    print(
        "Review status counts:",
        data["review_status_counts"],
    )
    print("Saved:", REVIEWS_FILE)


if __name__ == "__main__":
    main()
