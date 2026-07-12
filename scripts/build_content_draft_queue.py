#!/usr/bin/env python3

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


INPUT_FILE = Path(
    "data/content/content-briefs.json"
)

OUTPUT_FILE = Path(
    "data/content/content-draft-queue.json"
)


QUEUE_VERSION = 1


VALID_ACTIONS = {
    "new_guide",
    "guide_cluster",
    "product_block",
}


VALID_CONTENT_TYPES = {
    "guide",
    "supporting_guide",
    "product_block",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    return str(value).strip().lower()


def build_brief_fingerprint(brief):
    payload = {
        "normalized_topic":
            brief["normalized_topic"],
        "production_action":
            brief["production_action"],
        "content_type":
            brief["content_type"],
        "routing_target":
            brief["routing_target"],
        "brief_title":
            brief["brief_title"],
        "primary_keyword":
            brief["primary_keyword"],
        "secondary_keywords":
            brief["secondary_keywords"],
        "target_audience":
            brief["target_audience"],
        "content_objective":
            brief["content_objective"],
        "required_sections":
            brief["required_sections"],
        "internal_linking":
            brief["internal_linking"],
        "products":
            brief["products"],
        "workflow":
            brief["workflow"],
    }

    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def validate_brief(brief):
    action = brief["production_action"]
    content_type = brief["content_type"]

    if action not in VALID_ACTIONS:
        raise ValueError(
            "Invalid production action: "
            + str(action)
        )

    if content_type not in VALID_CONTENT_TYPES:
        raise ValueError(
            "Invalid content type: "
            + str(content_type)
        )

    products = brief["products"]

    if len(products) != 5:
        raise ValueError(
            "Expected 5 products for "
            + brief["topic"]
        )

    product_slots = [
        product["slot"]
        for product in products
    ]

    if product_slots != [1, 2, 3, 4, 5]:
        raise ValueError(
            "Invalid product slots for "
            + brief["topic"]
        )

    if not all(
        product.get("promotion_link")
        for product in products
    ):
        raise ValueError(
            "Missing promotion link for "
            + brief["topic"]
        )

    workflow = brief["workflow"]

    if not workflow["requires_human_review"]:
        raise ValueError(
            "Human review must be required for "
            + brief["topic"]
        )

    if workflow["automatic_generation_enabled"]:
        raise ValueError(
            "Automatic generation must be disabled for "
            + brief["topic"]
        )

    if workflow["automatic_publishing_enabled"]:
        raise ValueError(
            "Automatic publishing must be disabled for "
            + brief["topic"]
        )


def build_queue_item(brief):
    validate_brief(brief)

    fingerprint = build_brief_fingerprint(brief)

    return {
        "queue_priority":
            brief["brief_priority"],
        "source_brief_priority":
            brief["brief_priority"],
        "topic":
            brief["topic"],
        "normalized_topic":
            brief["normalized_topic"],
        "final_opportunity_score":
            brief["final_opportunity_score"],
        "production_action":
            brief["production_action"],
        "content_type":
            brief["content_type"],
        "routing_target":
            brief["routing_target"],
        "brief_title":
            brief["brief_title"],
        "primary_keyword":
            brief["primary_keyword"],
        "secondary_keywords":
            brief["secondary_keywords"],
        "target_audience":
            brief["target_audience"],
        "content_objective":
            brief["content_objective"],
        "required_sections":
            brief["required_sections"],
        "internal_linking":
            brief["internal_linking"],
        "selected_product_count":
            len(brief["products"]),
        "products":
            brief["products"],
        "brief_fingerprint":
            fingerprint,
        "draft_status":
            "pending",
        "generation_status":
            "not_started",
        "approval_status":
            "pending_review",
        "publish_status":
            "not_published",
        "draft_file":
            (
                "data/content/drafts/"
                + normalize(
                    brief["normalized_topic"]
                ).replace(" ", "-")
                + ".json"
            ),
    }


def main():
    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    briefs = data["briefs"]

    queue = [
        build_queue_item(brief)
        for brief in briefs
    ]

    queue.sort(
        key=lambda item: (
            item["source_brief_priority"],
            item["normalized_topic"],
        )
    )

    for index, item in enumerate(queue, 1):
        item["queue_priority"] = index

    normalized_topics = [
        item["normalized_topic"]
        for item in queue
    ]

    if len(normalized_topics) != len(
        set(normalized_topics)
    ):
        raise ValueError(
            "Duplicate topics in draft queue"
        )

    action_counts = Counter(
        item["production_action"]
        for item in queue
    )

    content_type_counts = Counter(
        item["content_type"]
        for item in queue
    )

    draft_status_counts = Counter(
        item["draft_status"]
        for item in queue
    )

    output = {
        "source":
            "driverz_content_draft_queue",
        "draft_queue_version":
            QUEUE_VERSION,
        "generated_at":
            utc_now(),
        "source_brief_builder_version":
            data["brief_builder_version"],
        "source_generated_at":
            data["generated_at"],
        "input_brief_count":
            len(briefs),
        "queue_item_count":
            len(queue),
        "action_counts":
            dict(action_counts),
        "content_type_counts":
            dict(content_type_counts),
        "draft_status_counts":
            dict(draft_status_counts),
        "queue_policy": {
            "requires_human_review": True,
            "automatic_generation_enabled": False,
            "automatic_publishing_enabled": False,
            "fingerprint_algorithm": "sha256",
            "fingerprint_scope":
                "generation_relevant_brief_fields",
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
        "===== Driverz Content Draft Queue v1 ====="
    )
    print(
        "Input briefs:",
        len(briefs),
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
        "Draft status counts:",
        dict(draft_status_counts),
    )
    print(
        "Saved:",
        OUTPUT_FILE,
    )

    print("\n===== DRAFT QUEUE =====")

    for item in queue:
        print(
            item["queue_priority"],
            "| score=",
            item["final_opportunity_score"],
            "| action=",
            item["production_action"],
            "| type=",
            item["content_type"],
            "| products=",
            item["selected_product_count"],
            "| status=",
            item["draft_status"],
            "| target=",
            item["routing_target"] or "-",
            "|",
            item["topic"],
        )


if __name__ == "__main__":
    main()
