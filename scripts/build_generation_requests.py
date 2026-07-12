#!/usr/bin/env python3

import copy
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from validate_generation_request_contract import (
    CONTRACT_VERSION,
    sha256_value,
    validate_document,
)


INPUT_FILE = Path(
    "data/content/approved-content-queue.json"
)

OUTPUT_FILE = Path(
    "data/content/generation-requests.json"
)

BUILDER_VERSION = 1


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_source_draft(item):
    draft_file = Path(item["draft_file"])

    if not draft_file.exists():
        raise ValueError(
            "Approved source draft does not exist: "
            + str(draft_file)
        )

    draft = json.loads(
        draft_file.read_text(encoding="utf-8")
    )

    if (
        draft["normalized_topic"]
        != item["normalized_topic"]
    ):
        raise ValueError(
            "Approved item/source draft topic mismatch"
        )

    if (
        draft["draft_fingerprint"]
        != item["draft_fingerprint"]
    ):
        raise ValueError(
            "Approved item/source draft fingerprint mismatch"
        )

    source_identity = draft["source_identity"]

    if (
        source_identity["source_queue_priority"]
        != item["source_queue_priority"]
    ):
        raise ValueError(
            "Approved item/source queue priority mismatch"
        )

    if (
        source_identity["source_brief_priority"]
        != item["source_brief_priority"]
    ):
        raise ValueError(
            "Approved item/source brief priority mismatch"
        )

    if (
        source_identity["brief_fingerprint"]
        != item["brief_fingerprint"]
    ):
        raise ValueError(
            "Approved item/source brief fingerprint mismatch"
        )

    return draft


def build_section_requirements(draft):
    return [
        {
            "section_order":
                section["section_order"],
            "section_title":
                section["section_title"],
        }
        for section in draft["sections"]
    ]


def build_request(item, request_priority):
    draft = load_source_draft(item)

    products = copy.deepcopy(
        item["products"]
    )

    request = {
        "request_priority":
            request_priority,

        "topic":
            item["topic"],

        "normalized_topic":
            item["normalized_topic"],

        "production_action":
            item["production_action"],

        "content_type":
            item["content_type"],

        "routing_target":
            item["routing_target"],

        "request_identity": {
            "contract_version":
                CONTRACT_VERSION,
            "normalized_topic":
                item["normalized_topic"],
        },

        "source_identity": {
            "approved_queue_priority":
                item["approved_queue_priority"],
            "source_queue_priority":
                item["source_queue_priority"],
            "source_brief_priority":
                item["source_brief_priority"],
            "brief_fingerprint":
                item["brief_fingerprint"],
            "draft_fingerprint":
                item["draft_fingerprint"],
            "review_fingerprint":
                item["review_fingerprint"],
            "approval_fingerprint":
                item["approval_fingerprint"],
        },

        "content_specification": {
            "brief_title":
                item["brief_title"],
            "target_audience":
                copy.deepcopy(
                    item["target_audience"]
                ),
            "content_objective":
                item["content_objective"],
            "final_opportunity_score":
                item["final_opportunity_score"],
        },

        "seo_requirements": {
            "primary_keyword":
                item["primary_keyword"],
            "secondary_keywords":
                copy.deepcopy(
                    item["secondary_keywords"]
                ),
        },

        "section_requirements":
            build_section_requirements(draft),

        "product_fact_constraints": {
            "use_only_provided_product_facts":
                True,
            "do_not_invent_prices":
                True,
            "do_not_invent_ratings":
                True,
            "do_not_invent_sales":
                True,
            "do_not_invent_product_features":
                True,
            "do_not_claim_first_hand_testing":
                True,
        },

        "affiliate_requirements": {
            "preserve_promotion_links_exactly":
                True,
            "affiliate_disclosure_required":
                True,
        },

        "internal_linking_requirements":
            copy.deepcopy(
                item["internal_linking"]
            ),

        "generation_instructions": {
            "language":
                "en-GB",
            "market":
                "United Kingdom",
            "write_for_target_audience":
                True,
            "follow_content_objective":
                True,
            "use_primary_keyword_naturally":
                True,
            "use_secondary_keywords_naturally":
                True,
            "follow_section_requirements":
                True,
            "avoid_keyword_stuffing":
                True,
            "avoid_unsupported_superlatives":
                True,
            "avoid_false_urgency":
                True,
            "avoid_fabricated_experience":
                True,
        },

        "output_contract": {
            "format":
                "structured_json",
            "preserve_section_order":
                True,
            "one_output_section_per_requirement":
                True,
            "include_product_ids":
                True,
            "preserve_promotion_links_exactly":
                True,
            "include_affiliate_disclosure":
                True,
        },

        "products":
            products,

        "workflow": {
            "requires_human_review":
                True,
            "automatic_api_call_enabled":
                False,
            "automatic_rendering_enabled":
                False,
            "automatic_publishing_enabled":
                False,
        },

        "generation_status":
            "pending",
    }

    request[
        "generation_request_fingerprint"
    ] = sha256_value(request)

    return request


def main():
    approved_data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    items = approved_data["items"]

    requests = [
        build_request(item, index)
        for index, item in enumerate(items, 1)
    ]

    action_counts = Counter(
        request["production_action"]
        for request in requests
    )

    content_type_counts = Counter(
        request["content_type"]
        for request in requests
    )

    status_counts = Counter(
        request["generation_status"]
        for request in requests
    )

    output = {
        "source":
            "driverz_generation_request_builder",
        "generation_request_version":
            CONTRACT_VERSION,
        "builder_version":
            BUILDER_VERSION,
        "generated_at":
            utc_now(),
        "source_approved_queue_version":
            approved_data[
                "approved_queue_version"
            ],
        "input_approved_item_count":
            len(items),
        "request_count":
            len(requests),
        "action_counts":
            dict(action_counts),
        "content_type_counts":
            dict(content_type_counts),
        "generation_status_counts":
            dict(status_counts),
        "request_policy": {
            "approved_items_only":
                True,
            "provider_neutral":
                True,
            "structured_contract":
                True,
            "validate_before_write":
                True,
            "allow_empty_requests":
                True,
            "automatic_api_call_enabled":
                False,
            "automatic_rendering_enabled":
                False,
            "automatic_publishing_enabled":
                False,
            "fingerprint_algorithm":
                "sha256",
        },
        "requests":
            requests,
    }

    validate_document(output)

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
        "===== Driverz Generation Request Builder v1 ====="
    )
    print(
        "Input approved items:",
        len(items),
    )
    print(
        "Generation requests:",
        len(requests),
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
        "Generation status counts:",
        dict(status_counts),
    )
    print(
        "Saved:",
        OUTPUT_FILE,
    )

    print("\n===== GENERATION REQUESTS =====")

    for request in requests:
        print(
            request["request_priority"],
            "| status=",
            request["generation_status"],
            "| action=",
            request["production_action"],
            "| type=",
            request["content_type"],
            "| products=",
            len(request["products"]),
            "| target=",
            request["routing_target"] or "-",
            "|",
            request["topic"],
        )


if __name__ == "__main__":
    main()
