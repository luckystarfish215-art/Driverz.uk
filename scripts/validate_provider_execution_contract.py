#!/usr/bin/env python3

import hashlib
import json
from collections import Counter
from pathlib import Path


CONTRACT_VERSION = 1

BOUNDARY_FILE = Path(
    "data/content/provider-execution-boundary.json"
)

VALID_PROVIDER_STATUSES = {
    "not_called",
}

VALID_ATTEMPT_STATUSES = {
    "not_started",
}

VALID_RESPONSE_STATUSES = {
    "not_received",
}

VALID_FAILURE_STATUSES = {
    "none",
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


def execution_fingerprint_payload(item):
    return {
        key: value
        for key, value in item.items()
        if key not in {
            "execution_fingerprint",
        }
    }


def expected_execution_id(item):
    return sha256_value({
        "normalized_topic":
            item["normalized_topic"],
        "generation_request_fingerprint":
            item[
                "generation_request_fingerprint"
            ],
        "provider_payload_fingerprint":
            item[
                "provider_payload_fingerprint"
            ],
    })


def expected_idempotency_key(item):
    return sha256_value({
        "execution_id":
            item["execution_id"],
        "attempt_number":
            item["attempt_number"],
    })


def validate_execution(item):
    required_fields = {
        "execution_priority",
        "normalized_topic",
        "generation_request_fingerprint",
        "provider_payload_fingerprint",
        "execution_id",
        "idempotency_key",
        "attempt_number",
        "provider_status",
        "attempt_status",
        "response_status",
        "failure_status",
        "response_envelope",
        "failure_record",
        "execution_fingerprint",
    }

    if set(item) != required_fields:
        raise ValueError(
            "Invalid execution schema"
        )

    if (
        not isinstance(
            item["execution_priority"],
            int,
        )
        or item["execution_priority"] < 1
    ):
        raise ValueError(
            "Invalid execution priority"
        )

    for field in {
        "generation_request_fingerprint",
        "provider_payload_fingerprint",
        "execution_id",
        "idempotency_key",
        "execution_fingerprint",
    }:
        value = item[field]

        if (
            not isinstance(value, str)
            or len(value) != 64
        ):
            raise ValueError(
                "Invalid SHA256 field: " + field
            )

    if item["attempt_number"] != 0:
        raise ValueError(
            "Initial attempt number must be zero"
        )

    if (
        item["provider_status"]
        not in VALID_PROVIDER_STATUSES
    ):
        raise ValueError(
            "Invalid provider status"
        )

    if (
        item["attempt_status"]
        not in VALID_ATTEMPT_STATUSES
    ):
        raise ValueError(
            "Invalid attempt status"
        )

    if (
        item["response_status"]
        not in VALID_RESPONSE_STATUSES
    ):
        raise ValueError(
            "Invalid response status"
        )

    if (
        item["failure_status"]
        not in VALID_FAILURE_STATUSES
    ):
        raise ValueError(
            "Invalid failure status"
        )

    if item["response_envelope"] is not None:
        raise ValueError(
            "Response envelope must be null"
        )

    if item["failure_record"] is not None:
        raise ValueError(
            "Failure record must be null"
        )

    if (
        item["execution_id"]
        != expected_execution_id(item)
    ):
        raise ValueError(
            "Execution ID mismatch"
        )

    if (
        item["idempotency_key"]
        != expected_idempotency_key(item)
    ):
        raise ValueError(
            "Idempotency key mismatch"
        )

    expected_fingerprint = sha256_value(
        execution_fingerprint_payload(item)
    )

    if (
        item["execution_fingerprint"]
        != expected_fingerprint
    ):
        raise ValueError(
            "Execution fingerprint mismatch"
        )

    return True


def validate_document(document):
    if (
        document["provider_execution_contract_version"]
        != CONTRACT_VERSION
    ):
        raise ValueError(
            "Invalid provider execution contract version"
        )

    required_policy = {
        "source_dry_run_only": True,
        "provider_neutral": True,
        "allow_empty_executions": True,
        "automatic_api_call_enabled": False,
        "automatic_content_generation_enabled": False,
        "automatic_rendering_enabled": False,
        "automatic_publishing_enabled": False,
        "idempotency_enabled": True,
        "response_validation_required": True,
        "failure_record_required_on_failure": True,
        "fingerprint_algorithm": "sha256",
    }

    if (
        document.get("execution_policy")
        != required_policy
    ):
        raise ValueError(
            "Invalid or unsafe execution policy"
        )

    executions = document["executions"]

    if (
        document["execution_count"]
        != len(executions)
    ):
        raise ValueError(
            "Execution count mismatch"
        )

    priorities = [
        item["execution_priority"]
        for item in executions
    ]

    if priorities != list(
        range(1, len(executions) + 1)
    ):
        raise ValueError(
            "Execution priorities invalid"
        )

    topics = [
        item["normalized_topic"]
        for item in executions
    ]

    if len(topics) != len(set(topics)):
        raise ValueError(
            "Duplicate execution topics"
        )

    execution_ids = [
        item["execution_id"]
        for item in executions
    ]

    if (
        len(execution_ids)
        != len(set(execution_ids))
    ):
        raise ValueError(
            "Duplicate execution IDs"
        )

    idempotency_keys = [
        item["idempotency_key"]
        for item in executions
    ]

    if (
        len(idempotency_keys)
        != len(set(idempotency_keys))
    ):
        raise ValueError(
            "Duplicate idempotency keys"
        )

    for item in executions:
        validate_execution(item)

    expected_status_counts = dict(
        Counter(
            item["attempt_status"]
            for item in executions
        )
    )

    if (
        document["attempt_status_counts"]
        != expected_status_counts
    ):
        raise ValueError(
            "Attempt status counts mismatch"
        )

    if (
        document["input_adapter_execution_count"]
        != len(executions)
    ):
        raise ValueError(
            "Input adapter execution count mismatch"
        )

    return True


def main():
    print(
        "Provider Execution Contract Validator v1"
    )
    print(
        "Contract version:",
        CONTRACT_VERSION,
    )

    if BOUNDARY_FILE.exists():
        document = json.loads(
            BOUNDARY_FILE.read_text(
                encoding="utf-8"
            )
        )

        validate_document(document)


if __name__ == "__main__":
    main()
