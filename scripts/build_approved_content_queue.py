#!/usr/bin/env python3

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


REVIEWS_FILE = Path(
    "data/content/draft-reviews.json"
)

OUTPUT_FILE = Path(
    "data/content/approved-content-queue.json"
)

QUEUE_VERSION = 1


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


def validate_approved_review(review):
    topic = review["normalized_topic"]

    if review["review_status"] != "approved":
        raise ValueError(
            "Review is not approved: " + topic
        )

    if not review["review_reason"]:
        raise ValueError(
            "Approved review has no reason: "
            + topic
        )

    if not review["reviewed_at"]:
        raise ValueError(
            "Approved review has no reviewed_at: "
            + topic
        )

    expected = expected_review_fingerprint(
        review
    )

    if (
        review["review_fingerprint"]
        != expected
    ):
        raise ValueError(
            "Invalid review fingerprint: "
            + topic
        )

    draft_file = Path(review["draft_file"])

    if not draft_file.exists():
        raise ValueError(
            "Draft file does not exist: "
            + str(draft_file)
        )

    draft = load_json(draft_file)

    if (
        draft["normalized_topic"]
        != topic
    ):
        raise ValueError(
            "Review/draft topic mismatch: "
            + topic
        )

    if (
        draft["draft_fingerprint"]
        != review["draft_fingerprint"]
    ):
        raise ValueError(
            "Approved review is stale: "
            + topic
        )

    if (
        draft["source_identity"][
            "source_queue_priority"
        ]
        != review["source_queue_priority"]
    ):
        raise ValueError(
            "Queue priority mismatch: "
            + topic
        )

    if (
        draft["source_identity"][
            "source_brief_priority"
        ]
        != review["source_brief_priority"]
    ):
        raise ValueError(
            "Brief priority mismatch: "
            + topic
        )

    if (
        draft["source_identity"][
            "brief_fingerprint"
        ]
        != review["brief_fingerprint"]
    ):
        raise ValueError(
            "Brief fingerprint mismatch: "
            + topic
        )

    if (
        draft["approval_status"]
        != "pending_review"
    ):
        raise ValueError(
            "Unexpected draft approval status: "
            + topic
        )

    if (
        draft["publish_status"]
        != "not_published"
    ):
        raise ValueError(
            "Draft already published: "
            + topic
        )

    return draft


def build_approval_fingerprint(
    review,
    draft,
):
    return sha256_value({
        "normalized_topic":
            review["normalized_topic"],
        "review_fingerprint":
            review["review_fingerprint"],
        "draft_fingerprint":
            draft["draft_fingerprint"],
        "review_status":
            review["review_status"],
        "review_reason":
            review["review_reason"],
        "reviewed_at":
            review["reviewed_at"],
    })


def build_queue_item(review):
    draft = validate_approved_review(review)

    return {
        "source_review_priority":
            review["review_priority"],
        "source_queue_priority":
            review["source_queue_priority"],
        "source_brief_priority":
            review["source_brief_priority"],
        "topic":
            review["topic"],
        "normalized_topic":
            review["normalized_topic"],
        "final_opportunity_score":
            draft["final_opportunity_score"],
        "production_action":
            draft["production_action"],
        "content_type":
            draft["content_type"],
        "routing_target":
            draft["routing_target"],
        "brief_title":
            draft["brief_title"],
        "primary_keyword":
            draft["primary_keyword"],
        "secondary_keywords":
            draft["secondary_keywords"],
        "target_audience":
            draft["target_audience"],
        "content_objective":
            draft["content_objective"],
        "internal_linking":
            draft["internal_linking"],
        "selected_product_count":
            draft["selected_product_count"],
        "products":
            draft["products"],
        "draft_file":
            review["draft_file"],
        "brief_fingerprint":
            review["brief_fingerprint"],
        "draft_fingerprint":
            review["draft_fingerprint"],
        "review_fingerprint":
            review["review_fingerprint"],
        "review_reason":
            review["review_reason"],
        "reviewed_at":
            review["reviewed_at"],
        "approval_fingerprint":
            build_approval_fingerprint(
                review,
                draft,
            ),
        "generation_status":
            "not_started",
        "render_status":
            "not_rendered",
        "publish_status":
            "not_published",
    }


def main():
    review_data = load_json(
        REVIEWS_FILE
    )

    reviews = review_data["reviews"]

    approved_reviews = [
        review
        for review in reviews
        if review["review_status"] == "approved"
    ]

    approved_reviews.sort(
        key=lambda item: (
            item["review_priority"],
            item["source_queue_priority"],
            item["normalized_topic"],
        )
    )

    queue = [
        build_queue_item(review)
        for review in approved_reviews
    ]

    for index, item in enumerate(queue, 1):
        item["approved_queue_priority"] = index

    action_counts = Counter(
        item["production_action"]
        for item in queue
    )

    content_type_counts = Counter(
        item["content_type"]
        for item in queue
    )

    output = {
        "source":
            "driverz_approved_content_queue",
        "approved_queue_version":
            QUEUE_VERSION,
        "generated_at":
            utc_now(),
        "source_review_queue_version":
            review_data["review_queue_version"],
        "input_review_count":
            len(reviews),
        "approved_review_count":
            len(approved_reviews),
        "queue_item_count":
            len(queue),
        "action_counts":
            dict(action_counts),
        "content_type_counts":
            dict(content_type_counts),
        "queue_policy": {
            "approved_reviews_only":
                True,
            "validate_review_fingerprint":
                True,
            "validate_draft_fingerprint":
                True,
            "validate_source_identity":
                True,
            "allow_empty_queue":
                True,
            "automatic_generation_enabled":
                False,
            "automatic_rendering_enabled":
                False,
            "automatic_publishing_enabled":
                False,
            "fingerprint_algorithm":
                "sha256",
        },
        "items":
            queue,
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
        "===== Driverz Approved Content Queue v1 ====="
    )
    print(
        "Input reviews:",
        len(reviews),
    )
    print(
        "Approved reviews:",
        len(approved_reviews),
    )
    print(
        "Queue items:",
        len(queue),
    )
    print(
        "Action counts:",
        dict(action_counts),
    )
    print(
        "Content type counts:",
        dict(content_type_counts),
    )
    print(
        "Saved:",
        OUTPUT_FILE,
    )

    print("\n===== APPROVED QUEUE =====")

    for item in queue:
        print(
            item["approved_queue_priority"],
            "| score=",
            item["final_opportunity_score"],
            "| action=",
            item["production_action"],
            "| type=",
            item["content_type"],
            "| products=",
            item["selected_product_count"],
            "| target=",
            item["routing_target"] or "-",
            "|",
            item["topic"],
        )


if __name__ == "__main__":
    main()
