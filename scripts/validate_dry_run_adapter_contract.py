#!/usr/bin/env python3

import hashlib
import json


CONTRACT_VERSION = 1

VALID_ADAPTER_STATUSES = {
    "dry_run_ready",
}

REQUIRED_PAYLOAD_FIELDS = {
    "payload_priority",
    "normalized_topic",
    "production_action",
    "content_type",
    "routing_target",
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
    "adapter_controls",
    "provider_payload_fingerprint",
}

REQUIRED_EXECUTION_FIELDS = {
    "execution_priority",
    "normalized_topic",
    "generation_request_fingerprint",
    "provider_payload_fingerprint",
    "adapter_status",
    "api_call_status",
    "generation_status",
    "render_status",
    "publish_status",
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


def payload_fingerprint_payload(payload):
    return {
        key: value
        for key, value in payload.items()
        if key != "provider_payload_fingerprint"
    }


def validate_payload(payload):
    missing = (
        REQUIRED_PAYLOAD_FIELDS
        - set(payload.keys())
    )

    if missing:
        raise ValueError(
            "Missing provider payload fields: "
            + ", ".join(sorted(missing))
        )

    if payload["payload_priority"] < 1:
        raise ValueError(
            "Invalid payload_priority"
        )

    if not payload["normalized_topic"]:
        raise ValueError(
            "Missing normalized_topic"
        )

    source = payload["source_identity"]

    required_source_fields = {
        "generation_request_fingerprint",
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
            "Missing payload source identity fields"
        )

    sections = payload["section_requirements"]

    if not sections:
        raise ValueError(
            "section_requirements cannot be empty"
        )

    if [
        section["section_order"]
        for section in sections
    ] != list(range(1, len(sections) + 1)):
        raise ValueError(
            "Invalid payload section order"
        )

    products = payload["products"]

    if len(products) != 5:
        raise ValueError(
            "Exactly 5 products required"
        )

    if [
        product["slot"]
        for product in products
    ] != [1, 2, 3, 4, 5]:
        raise ValueError(
            "Invalid payload product slots"
        )

    product_ids = [
        product["product_id"]
        for product in products
    ]

    if len(product_ids) != len(set(product_ids)):
        raise ValueError(
            "Duplicate payload product IDs"
        )

    if any(
        not product.get("promotion_link")
        for product in products
    ):
        raise ValueError(
            "Missing payload promotion link"
        )

    controls = payload["adapter_controls"]

    required_controls = {
        "dry_run": True,
        "provider_neutral": True,
        "api_call_enabled": False,
        "content_generation_enabled": False,
        "rendering_enabled": False,
        "publishing_enabled": False,
    }

    for field, expected in required_controls.items():
        if controls.get(field) is not expected:
            raise ValueError(
                "Unsafe adapter control: " + field
            )

    expected_fingerprint = sha256_value(
        payload_fingerprint_payload(payload)
    )

    if (
        payload["provider_payload_fingerprint"]
        != expected_fingerprint
    ):
        raise ValueError(
            "Provider payload fingerprint mismatch"
        )

    return True


def validate_execution_item(item):
    missing = (
        REQUIRED_EXECUTION_FIELDS
        - set(item.keys())
    )

    if missing:
        raise ValueError(
            "Missing execution manifest fields: "
            + ", ".join(sorted(missing))
        )

    if item["execution_priority"] < 1:
        raise ValueError(
            "Invalid execution_priority"
        )

    if (
        item["adapter_status"]
        not in VALID_ADAPTER_STATUSES
    ):
        raise ValueError(
            "Invalid adapter_status"
        )

    expected_states = {
        "api_call_status": "not_called",
        "generation_status": "not_started",
        "render_status": "not_rendered",
        "publish_status": "not_published",
    }

    for field, expected in expected_states.items():
        if item[field] != expected:
            raise ValueError(
                "Unsafe execution state: " + field
            )

    return True


def validate_document(document):
    if (
        document["dry_run_adapter_version"]
        != CONTRACT_VERSION
    ):
        raise ValueError(
            "Invalid dry-run adapter version"
        )

    payloads = document["provider_payloads"]
    executions = document["executions"]

    if (
        document["provider_payload_count"]
        != len(payloads)
    ):
        raise ValueError(
            "Provider payload count mismatch"
        )

    if (
        document["execution_count"]
        != len(executions)
    ):
        raise ValueError(
            "Execution count mismatch"
        )

    if len(payloads) != len(executions):
        raise ValueError(
            "Payload/execution count mismatch"
        )

    payload_priorities = [
        payload["payload_priority"]
        for payload in payloads
    ]

    if payload_priorities != list(
        range(1, len(payloads) + 1)
    ):
        raise ValueError(
            "Payload priorities invalid"
        )

    execution_priorities = [
        item["execution_priority"]
        for item in executions
    ]

    if execution_priorities != list(
        range(1, len(executions) + 1)
    ):
        raise ValueError(
            "Execution priorities invalid"
        )

    payload_topics = [
        payload["normalized_topic"]
        for payload in payloads
    ]

    execution_topics = [
        item["normalized_topic"]
        for item in executions
    ]

    if len(payload_topics) != len(set(payload_topics)):
        raise ValueError(
            "Duplicate provider payload topics"
        )

    if payload_topics != execution_topics:
        raise ValueError(
            "Payload/execution topic mismatch"
        )

    if (
        document["input_generation_request_count"]
        != len(payloads)
    ):
        raise ValueError(
            "Input generation request count mismatch"
        )

    if (
        document["input_generation_request_count"]
        != len(executions)
    ):
        raise ValueError(
            "Input generation request/execution count mismatch"
        )

    payload_fingerprints = [
        payload["provider_payload_fingerprint"]
        for payload in payloads
    ]

    if (
        len(payload_fingerprints)
        != len(set(payload_fingerprints))
    ):
        raise ValueError(
            "Duplicate provider payload fingerprints"
        )

    for payload in payloads:
        validate_payload(payload)

    for item in executions:
        validate_execution_item(item)

    for payload, item in zip(payloads, executions):
        if (
            payload["source_identity"][
                "generation_request_fingerprint"
            ]
            != item[
                "generation_request_fingerprint"
            ]
        ):
            raise ValueError(
                "Execution/request fingerprint mismatch"
            )

        if (
            payload["provider_payload_fingerprint"]
            != item["provider_payload_fingerprint"]
        ):
            raise ValueError(
                "Execution/payload fingerprint mismatch"
            )

    policy = document["adapter_policy"]

    required_policy = {
        "validate_generation_requests_before_adaptation":
            True,
        "provider_neutral":
            True,
        "dry_run_only":
            True,
        "allow_empty_payloads":
            True,
        "automatic_api_call_enabled":
            False,
        "automatic_content_generation_enabled":
            False,
        "automatic_rendering_enabled":
            False,
        "automatic_publishing_enabled":
            False,
        "fingerprint_algorithm":
            "sha256",
    }

    for field, expected in required_policy.items():
        if policy.get(field) != expected:
            raise ValueError(
                "Unsafe adapter policy: " + field
            )

    return True


def main():
    print(
        "Dry-run Adapter Contract Validator v1"
    )
    print("Contract version:", CONTRACT_VERSION)


if __name__ == "__main__":
    main()
