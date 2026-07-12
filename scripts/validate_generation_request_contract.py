#!/usr/bin/env python3

import hashlib
import json


CONTRACT_VERSION = 1

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

REQUIRED_PRODUCT_FIELDS = {
    "slot",
    "product_id",
    "product_title",
    "product_main_image_url",
    "promotion_link",
    "target_sale_price",
    "currency",
    "sales_volume",
    "evaluate_rate",
    "commission_rate",
    "estimated_commission_value",
    "product_score",
    "selection_reason",
}

REQUIRED_TOP_LEVEL_FIELDS = {
    "request_priority",
    "topic",
    "normalized_topic",
    "production_action",
    "content_type",
    "routing_target",
    "request_identity",
    "source_identity",
    "content_specification",
    "seo_requirements",
    "section_requirements",
    "product_fact_constraints",
    "affiliate_requirements",
    "internal_linking_requirements",
    "generation_instructions",
    "output_contract",
    "products",
    "workflow",
    "generation_status",
    "generation_request_fingerprint",
}


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


def fingerprint_payload(request):
    return {
        key: value
        for key, value in request.items()
        if key != "generation_request_fingerprint"
    }


def validate_request(request):
    missing = (
        REQUIRED_TOP_LEVEL_FIELDS
        - set(request.keys())
    )

    if missing:
        raise ValueError(
            "Missing generation request fields: "
            + ", ".join(sorted(missing))
        )

    if request["production_action"] not in VALID_ACTIONS:
        raise ValueError(
            "Invalid production_action"
        )

    if request["content_type"] not in VALID_CONTENT_TYPES:
        raise ValueError(
            "Invalid content_type"
        )

    if request["request_priority"] < 1:
        raise ValueError(
            "Invalid request_priority"
        )

    if request["generation_status"] != "pending":
        raise ValueError(
            "generation_status must be pending"
        )

    request_identity = request["request_identity"]

    if request_identity["contract_version"] != CONTRACT_VERSION:
        raise ValueError(
            "Invalid contract_version"
        )

    if (
        request_identity["normalized_topic"]
        != request["normalized_topic"]
    ):
        raise ValueError(
            "request_identity topic mismatch"
        )

    source = request["source_identity"]

    required_source_fields = {
        "approved_queue_priority",
        "source_queue_priority",
        "source_brief_priority",
        "brief_fingerprint",
        "draft_fingerprint",
        "review_fingerprint",
        "approval_fingerprint",
    }

    if not required_source_fields.issubset(source):
        raise ValueError(
            "Missing source identity fields"
        )

    content = request["content_specification"]

    required_content_fields = {
        "brief_title",
        "target_audience",
        "content_objective",
        "final_opportunity_score",
    }

    if not required_content_fields.issubset(content):
        raise ValueError(
            "Missing content specification fields"
        )

    seo = request["seo_requirements"]

    if not isinstance(seo["primary_keyword"], str):
        raise ValueError(
            "primary_keyword must be string"
        )

    if not isinstance(seo["secondary_keywords"], list):
        raise ValueError(
            "secondary_keywords must be list"
        )

    sections = request["section_requirements"]

    if not sections:
        raise ValueError(
            "section_requirements cannot be empty"
        )

    if [
        section["section_order"]
        for section in sections
    ] != list(range(1, len(sections) + 1)):
        raise ValueError(
            "Invalid section order"
        )

    if any(
        not isinstance(
            section["section_title"],
            str,
        )
        or not section["section_title"]
        for section in sections
    ):
        raise ValueError(
            "Invalid section title"
        )

    products = request["products"]

    if len(products) != 5:
        raise ValueError(
            "Exactly 5 products required"
        )

    if [
        product["slot"]
        for product in products
    ] != [1, 2, 3, 4, 5]:
        raise ValueError(
            "Invalid product slots"
        )

    product_ids = [
        product["product_id"]
        for product in products
    ]

    if len(product_ids) != len(set(product_ids)):
        raise ValueError(
            "Duplicate product IDs"
        )

    for product in products:
        missing_product_fields = (
            REQUIRED_PRODUCT_FIELDS
            - set(product.keys())
        )

        if missing_product_fields:
            raise ValueError(
                "Missing product fields"
            )

        if not product["promotion_link"]:
            raise ValueError(
                "Missing promotion link"
            )

    linking = request[
        "internal_linking_requirements"
    ]

    action = request["production_action"]
    routing_target = request["routing_target"]

    if action == "new_guide":
        if routing_target is not None:
            raise ValueError(
                "new_guide routing_target must be null"
            )

    elif action == "guide_cluster":
        if not routing_target:
            raise ValueError(
                "guide_cluster requires routing_target"
            )

        if (
            linking.get("parent_cluster")
            != routing_target
        ):
            raise ValueError(
                "parent_cluster routing mismatch"
            )

    elif action == "product_block":
        if not routing_target:
            raise ValueError(
                "product_block requires routing_target"
            )

        if (
            linking.get("insertion_target")
            != routing_target
        ):
            raise ValueError(
                "insertion_target routing mismatch"
            )

    fact_policy = request[
        "product_fact_constraints"
    ]

    required_fact_flags = {
        "use_only_provided_product_facts",
        "do_not_invent_prices",
        "do_not_invent_ratings",
        "do_not_invent_sales",
        "do_not_invent_product_features",
        "do_not_claim_first_hand_testing",
    }

    if not all(
        fact_policy.get(flag) is True
        for flag in required_fact_flags
    ):
        raise ValueError(
            "Unsafe product fact constraints"
        )

    affiliate = request[
        "affiliate_requirements"
    ]

    if (
        affiliate[
            "preserve_promotion_links_exactly"
        ] is not True
        or affiliate[
            "affiliate_disclosure_required"
        ] is not True
    ):
        raise ValueError(
            "Unsafe affiliate requirements"
        )

    workflow = request["workflow"]

    required_workflow = {
        "requires_human_review": True,
        "automatic_api_call_enabled": False,
        "automatic_rendering_enabled": False,
        "automatic_publishing_enabled": False,
    }

    for field, expected in required_workflow.items():
        if workflow.get(field) is not expected:
            raise ValueError(
                "Unsafe workflow field: " + field
            )

    output_contract = request["output_contract"]

    if (
        output_contract["format"]
        != "structured_json"
    ):
        raise ValueError(
            "Output format must be structured_json"
        )

    if (
        output_contract[
            "preserve_section_order"
        ] is not True
    ):
        raise ValueError(
            "Section order preservation required"
        )

    expected_fingerprint = sha256_value(
        fingerprint_payload(request)
    )

    if (
        request["generation_request_fingerprint"]
        != expected_fingerprint
    ):
        raise ValueError(
            "Generation request fingerprint mismatch"
        )

    return True


def validate_document(document):
    if (
        document["generation_request_version"]
        != CONTRACT_VERSION
    ):
        raise ValueError(
            "Invalid generation request version"
        )

    required_request_policy = {
        "approved_items_only": True,
        "provider_neutral": True,
        "structured_contract": True,
        "validate_before_write": True,
        "allow_empty_requests": True,
        "automatic_api_call_enabled": False,
        "automatic_rendering_enabled": False,
        "automatic_publishing_enabled": False,
        "fingerprint_algorithm": "sha256",
    }

    if (
        document.get("request_policy")
        != required_request_policy
    ):
        raise ValueError(
            "Invalid or unsafe request policy"
        )

    requests = document["requests"]

    if (
        document["request_count"]
        != len(requests)
    ):
        raise ValueError(
            "Request count mismatch"
        )

    priorities = [
        request["request_priority"]
        for request in requests
    ]

    if priorities != list(
        range(1, len(requests) + 1)
    ):
        raise ValueError(
            "Request priorities invalid"
        )

    topics = [
        request["normalized_topic"]
        for request in requests
    ]

    if len(topics) != len(set(topics)):
        raise ValueError(
            "Duplicate request topics"
        )

    fingerprints = [
        request["generation_request_fingerprint"]
        for request in requests
    ]

    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError(
            "Duplicate generation request fingerprints"
        )

    for request in requests:
        validate_request(request)

    return True


def main():
    print(
        "Generation Request Contract Validator v1"
    )
    print("Contract version:", CONTRACT_VERSION)


if __name__ == "__main__":
    main()
