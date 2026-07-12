#!/usr/bin/env python3

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


INPUT_FILE = Path(
    "data/content/content-draft-queue.json"
)

DRAFT_DIR = Path(
    "data/content/drafts"
)

MANIFEST_FILE = DRAFT_DIR / "draft-manifest.json"


GENERATOR_VERSION = 1

VALID_ACTIONS = {
    "new_guide",
    "guide_cluster",
    "product_block",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_value(value):
    return hashlib.sha256(
        canonical_json(value).encode("utf-8")
    ).hexdigest()


def load_json(path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def write_json_atomic(path, value):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_file = path.with_suffix(
        path.suffix + ".tmp"
    )

    temp_file.write_text(
        json.dumps(
            value,
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )

    temp_file.replace(path)


def validate_queue_data(data):
    required_top_level = {
        "draft_queue_version",
        "input_brief_count",
        "queue_item_count",
        "queue_policy",
        "items",
    }

    missing = required_top_level - set(data)

    if missing:
        raise ValueError(
            "Missing queue fields: "
            + ", ".join(sorted(missing))
        )

    items = data["items"]

    if data["queue_item_count"] != len(items):
        raise ValueError(
            "queue_item_count does not match items"
        )

    seen_topics = set()
    seen_priorities = set()

    for item in items:
        required_item_fields = {
            "queue_priority",
            "source_brief_priority",
            "topic",
            "normalized_topic",
            "brief_fingerprint",
            "final_opportunity_score",
            "production_action",
            "content_type",
            "routing_target",
            "brief_title",
            "primary_keyword",
            "secondary_keywords",
            "target_audience",
            "content_objective",
            "required_sections",
            "internal_linking",
            "selected_product_count",
            "products",
            "draft_status",
            "generation_status",
            "approval_status",
            "publish_status",
        }

        missing_item_fields = (
            required_item_fields - set(item)
        )

        if missing_item_fields:
            raise ValueError(
                "Missing fields for "
                + item.get("topic", "<unknown>")
                + ": "
                + ", ".join(
                    sorted(missing_item_fields)
                )
            )

        topic_key = item["normalized_topic"]
        priority = item["queue_priority"]
        action = item["production_action"]

        if topic_key in seen_topics:
            raise ValueError(
                "Duplicate topic: " + topic_key
            )

        if priority in seen_priorities:
            raise ValueError(
                "Duplicate queue priority: "
                + str(priority)
            )

        if action not in VALID_ACTIONS:
            raise ValueError(
                "Unsupported production action: "
                + str(action)
            )

        if len(item["brief_fingerprint"]) != 64:
            raise ValueError(
                "Invalid brief fingerprint: "
                + topic_key
            )

        if (
            item["selected_product_count"]
            != len(item["products"])
        ):
            raise ValueError(
                "Product count mismatch: "
                + topic_key
            )

        if len(item["products"]) != 5:
            raise ValueError(
                "Expected 5 products: "
                + topic_key
            )

        seen_topics.add(topic_key)
        seen_priorities.add(priority)

    expected_priorities = set(
        range(1, len(items) + 1)
    )

    if seen_priorities != expected_priorities:
        raise ValueError(
            "Queue priorities are not sequential"
        )


def build_draft_filename(item):
    return (
        item["normalized_topic"]
        .replace(" ", "-")
        + ".json"
    )


def build_source_identity(item):
    return {
        "source_queue_priority":
            item["queue_priority"],
        "source_brief_priority":
            item["source_brief_priority"],
        "brief_fingerprint":
            item["brief_fingerprint"],
    }


def build_section_skeleton(item):
    sections = []

    for index, section in enumerate(
        item["required_sections"],
        1,
    ):
        if isinstance(section, str):
            section_data = {
                "section_order": index,
                "section_title": section,
                "generation_status": "not_generated",
                "content": None,
            }

        elif isinstance(section, dict):
            section_data = dict(section)

            section_data["section_order"] = index

            section_data.setdefault(
                "generation_status",
                "not_generated",
            )

            section_data.setdefault(
                "content",
                None,
            )

        else:
            raise ValueError(
                "Unsupported section type for "
                + item["normalized_topic"]
            )

        sections.append(section_data)

    return sections


def build_product_slots(item):
    products = []

    for expected_slot, product in enumerate(
        item["products"],
        1,
    ):
        if product["slot"] != expected_slot:
            raise ValueError(
                "Invalid product slot order for "
                + item["normalized_topic"]
            )

        if not product.get("promotion_link"):
            raise ValueError(
                "Missing promotion link for product "
                + str(product["product_id"])
            )

        if not isinstance(
            product.get("product_score"),
            (int, float),
        ):
            raise ValueError(
                "Missing product score for product "
                + str(product["product_id"])
            )

        products.append(dict(product))

    return products


def build_action_schema(item):
    action = item["production_action"]

    if action == "new_guide":
        if item["routing_target"] is not None:
            raise ValueError(
                "new_guide must not have routing target: "
                + item["normalized_topic"]
            )

        return {
            "draft_kind": "standalone_guide",
            "page_creation_required": True,
            "parent_content_target": None,
            "insertion_target": None,
        }

    if action == "guide_cluster":
        if not item["routing_target"]:
            raise ValueError(
                "guide_cluster missing routing target: "
                + item["normalized_topic"]
            )

        return {
            "draft_kind": "supporting_guide",
            "page_creation_required": True,
            "parent_content_target":
                item["routing_target"],
            "insertion_target": None,
        }

    if action == "product_block":
        if not item["routing_target"]:
            raise ValueError(
                "product_block missing routing target: "
                + item["normalized_topic"]
            )

        return {
            "draft_kind": "product_recommendation_block",
            "page_creation_required": False,
            "parent_content_target": None,
            "insertion_target":
                item["routing_target"],
        }

    raise ValueError(
        "Unsupported production action: "
        + str(action)
    )


def build_generation_payload(item):
    return {
        "brief_title":
            item["brief_title"],
        "primary_keyword":
            item["primary_keyword"],
        "secondary_keywords":
            item["secondary_keywords"],
        "target_audience":
            item["target_audience"],
        "content_objective":
            item["content_objective"],
        "required_sections":
            item["required_sections"],
        "internal_linking":
            item["internal_linking"],
        "products":
            item["products"],
    }


def build_generation_fingerprint(item):
    return sha256_value(
        {
            "brief_fingerprint":
                item["brief_fingerprint"],
            "production_action":
                item["production_action"],
            "content_type":
                item["content_type"],
            "routing_target":
                item["routing_target"],
            "generation_payload":
                build_generation_payload(item),
        }
    )


def build_draft(item):
    action_schema = build_action_schema(item)

    products = build_product_slots(item)

    sections = build_section_skeleton(item)

    generation_fingerprint = (
        build_generation_fingerprint(item)
    )

    draft = {
        "source":
            "driverz_content_draft_generation",
        "generator_version":
            GENERATOR_VERSION,
        "generated_at":
            utc_now(),
        "topic":
            item["topic"],
        "normalized_topic":
            item["normalized_topic"],
        "final_opportunity_score":
            item["final_opportunity_score"],
        "production_action":
            item["production_action"],
        "content_type":
            item["content_type"],
        "routing_target":
            item["routing_target"],
        "source_identity":
            build_source_identity(item),
        "generation_fingerprint":
            generation_fingerprint,
        "brief_title":
            item["brief_title"],
        "primary_keyword":
            item["primary_keyword"],
        "secondary_keywords":
            item["secondary_keywords"],
        "target_audience":
            item["target_audience"],
        "content_objective":
            item["content_objective"],
        "internal_linking":
            item["internal_linking"],
        "draft_schema":
            action_schema,
        "sections":
            sections,
        "selected_product_count":
            item["selected_product_count"],
        "products":
            products,
        "generation_status":
            "skeleton_generated",
        "draft_status":
            "generated",
        "approval_status":
            "pending_review",
        "publish_status":
            "not_published",
        "workflow": {
            "requires_human_review": True,
            "automatic_generation_enabled": False,
            "automatic_publishing_enabled": False,
        },
    }

    draft["draft_fingerprint"] = sha256_value(
        {
            key: value
            for key, value in draft.items()
            if key not in {
                "generated_at",
                "draft_fingerprint",
            }
        }
    )

    return draft


def inspect_existing_draft(path, new_draft):
    if not path.exists():
        return {
            "result": "created",
            "existing_draft": None,
        }

    try:
        existing = load_json(path)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Existing draft is invalid JSON: "
            + str(path)
        ) from exc

    existing_topic = existing.get(
        "normalized_topic"
    )

    expected_topic = new_draft[
        "normalized_topic"
    ]

    if existing_topic != expected_topic:
        raise ValueError(
            "Existing draft topic mismatch: "
            + str(path)
        )

    existing_generation_fingerprint = (
        existing.get(
            "generation_fingerprint"
        )
    )

    new_generation_fingerprint = (
        new_draft[
            "generation_fingerprint"
        ]
    )

    if (
        existing_generation_fingerprint
        == new_generation_fingerprint
    ):
        return {
            "result": "unchanged",
            "existing_draft": existing,
        }

    return {
        "result": "stale",
        "existing_draft": existing,
    }


def process_queue_item(item):
    if item["draft_status"] != "pending":
        return {
            "result": "skipped_status",
            "topic": item["topic"],
            "normalized_topic":
                item["normalized_topic"],
            "queue_priority":
                item["queue_priority"],
            "draft_file":
                item.get("draft_file"),
        }

    draft = build_draft(item)

    filename = build_draft_filename(item)

    draft_path = DRAFT_DIR / filename

    inspection = inspect_existing_draft(
        draft_path,
        draft,
    )

    result = inspection["result"]

    if result == "created":
        write_json_atomic(
            draft_path,
            draft,
        )

        manifest_draft = draft

    elif result == "unchanged":
        manifest_draft = inspection[
            "existing_draft"
        ]

    elif result == "stale":
        manifest_draft = inspection[
            "existing_draft"
        ]

    else:
        raise ValueError(
            "Unexpected processing result: "
            + str(result)
        )

    return {
        "result": result,
        "topic": item["topic"],
        "normalized_topic":
            item["normalized_topic"],
        "queue_priority":
            item["queue_priority"],
        "draft_file":
            str(draft_path),
        "brief_fingerprint":
            item["brief_fingerprint"],
        "generation_fingerprint":
            draft["generation_fingerprint"],
        "existing_generation_fingerprint":
            (
                manifest_draft.get(
                    "generation_fingerprint"
                )
                if manifest_draft
                else None
            ),
        "draft_fingerprint":
            (
                manifest_draft.get(
                    "draft_fingerprint"
                )
                if manifest_draft
                else None
            ),
        "production_action":
            item["production_action"],
        "content_type":
            item["content_type"],
        "selected_product_count":
            item["selected_product_count"],
        "approval_status":
            (
                manifest_draft.get(
                    "approval_status"
                )
                if manifest_draft
                else None
            ),
        "publish_status":
            (
                manifest_draft.get(
                    "publish_status"
                )
                if manifest_draft
                else None
            ),
    }


def build_manifest(queue_data, results):
    result_counts = Counter(
        result["result"]
        for result in results
    )

    actionable_results = [
        result
        for result in results
        if result["result"] in {
            "created",
            "unchanged",
            "stale",
        }
    ]

    stale_topics = [
        result["normalized_topic"]
        for result in results
        if result["result"] == "stale"
    ]

    return {
        "source":
            "driverz_content_draft_manifest",
        "manifest_version":
            1,
        "generator_version":
            GENERATOR_VERSION,
        "generated_at":
            utc_now(),
        "source_draft_queue_version":
            queue_data["draft_queue_version"],
        "input_queue_item_count":
            len(queue_data["items"]),
        "processed_result_count":
            len(results),
        "actionable_draft_count":
            len(actionable_results),
        "result_counts":
            dict(result_counts),
        "stale_draft_count":
            len(stale_topics),
        "stale_topics":
            stale_topics,
        "generation_policy": {
            "process_pending_only": True,
            "overwrite_unchanged_drafts":
                False,
            "overwrite_stale_drafts":
                False,
            "requires_human_review":
                True,
            "automatic_generation_enabled":
                False,
            "automatic_publishing_enabled":
                False,
        },
        "drafts":
            results,
    }


def main():
    queue_data = load_json(INPUT_FILE)

    validate_queue_data(queue_data)

    DRAFT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    items = sorted(
        queue_data["items"],
        key=lambda item: item["queue_priority"],
    )

    results = [
        process_queue_item(item)
        for item in items
    ]

    manifest = build_manifest(
        queue_data,
        results,
    )

    write_json_atomic(
        MANIFEST_FILE,
        manifest,
    )

    result_counts = Counter(
        result["result"]
        for result in results
    )

    print(
        "===== Driverz Content Draft Generator v1 ====="
    )
    print(
        "Input queue items:",
        len(items),
    )
    print(
        "Processed results:",
        len(results),
    )
    print(
        "Result counts:",
        dict(result_counts),
    )
    print(
        "Stale drafts:",
        manifest["stale_draft_count"],
    )
    print(
        "Manifest:",
        MANIFEST_FILE,
    )

    print("\n===== DRAFT GENERATION RESULTS =====")

    for result in results:
        print(
            result["queue_priority"],
            "| result=",
            result["result"],
            "| action=",
            result.get("production_action", "-"),
            "| type=",
            result.get("content_type", "-"),
            "| products=",
            result.get(
                "selected_product_count",
                "-",
            ),
            "|",
            result["topic"],
        )


if __name__ == "__main__":
    main()
