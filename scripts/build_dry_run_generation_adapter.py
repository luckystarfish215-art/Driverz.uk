#!/usr/bin/env python3

import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from validate_generation_request_contract import (
    validate_document as validate_generation_requests,
)

from validate_dry_run_adapter_contract import (
    sha256_value,
    validate_document as validate_adapter_document,
)


ADAPTER_VERSION = 1

INPUT_FILE = Path(
    "data/content/generation-requests.json"
)

OUTPUT_FILE = Path(
    "data/content/dry-run-generation-adapter.json"
)


def utc_now():
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )


def atomic_write_json(path, document):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                document,
                handle,
                indent=2,
                ensure_ascii=False,
            )

            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary_path,
            path,
        )

    except Exception:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass

        raise


def build_source_identity(request):
    source = request["source_identity"]

    return {
        "generation_request_fingerprint":
            request[
                "generation_request_fingerprint"
            ],
        "approved_queue_priority":
            source["approved_queue_priority"],
        "source_queue_priority":
            source["source_queue_priority"],
        "source_brief_priority":
            source["source_brief_priority"],
        "brief_fingerprint":
            source["brief_fingerprint"],
        "draft_fingerprint":
            source["draft_fingerprint"],
        "review_fingerprint":
            source["review_fingerprint"],
        "approval_fingerprint":
            source["approval_fingerprint"],
    }


def build_payload(request, priority):
    payload = {
        "payload_priority":
            priority,
        "normalized_topic":
            request["normalized_topic"],
        "production_action":
            request["production_action"],
        "content_type":
            request["content_type"],
        "routing_target":
            request["routing_target"],
        "source_identity":
            build_source_identity(request),
        "content_specification":
            request["content_specification"],
        "seo_requirements":
            request["seo_requirements"],
        "section_requirements":
            request["section_requirements"],
        "product_fact_constraints":
            request["product_fact_constraints"],
        "affiliate_requirements":
            request["affiliate_requirements"],
        "internal_linking_requirements":
            request[
                "internal_linking_requirements"
            ],
        "generation_instructions":
            request["generation_instructions"],
        "output_contract":
            request["output_contract"],
        "products":
            request["products"],
        "adapter_controls": {
            "dry_run":
                True,
            "provider_neutral":
                True,
            "api_call_enabled":
                False,
            "content_generation_enabled":
                False,
            "rendering_enabled":
                False,
            "publishing_enabled":
                False,
        },
    }

    payload[
        "provider_payload_fingerprint"
    ] = sha256_value(payload)

    return payload


def build_execution(
    request,
    payload,
    priority,
):
    return {
        "execution_priority":
            priority,
        "normalized_topic":
            request["normalized_topic"],
        "generation_request_fingerprint":
            request[
                "generation_request_fingerprint"
            ],
        "provider_payload_fingerprint":
            payload[
                "provider_payload_fingerprint"
            ],
        "adapter_status":
            "dry_run_ready",
        "api_call_status":
            "not_called",
        "generation_status":
            "not_started",
        "render_status":
            "not_rendered",
        "publish_status":
            "not_published",
    }


def main():
    request_data = json.loads(
        INPUT_FILE.read_text(
            encoding="utf-8"
        )
    )

    validate_generation_requests(
        request_data
    )

    requests = request_data["requests"]

    payloads = [
        build_payload(request, index)
        for index, request in enumerate(
            requests,
            start=1,
        )
    ]

    executions = [
        build_execution(
            request,
            payload,
            index,
        )
        for index, (request, payload)
        in enumerate(
            zip(requests, payloads),
            start=1,
        )
    ]

    action_counts = dict(
        Counter(
            request["production_action"]
            for request in requests
        )
    )

    content_type_counts = dict(
        Counter(
            request["content_type"]
            for request in requests
        )
    )

    adapter_status_counts = dict(
        Counter(
            item["adapter_status"]
            for item in executions
        )
    )

    document = {
        "source":
            "driverz_dry_run_generation_adapter",
        "dry_run_adapter_version":
            ADAPTER_VERSION,
        "generated_at":
            utc_now(),
        "source_generation_request_version":
            request_data[
                "generation_request_version"
            ],
        "source_builder_version":
            request_data["builder_version"],
        "input_generation_request_count":
            len(requests),
        "provider_payload_count":
            len(payloads),
        "execution_count":
            len(executions),
        "action_counts":
            action_counts,
        "content_type_counts":
            content_type_counts,
        "adapter_status_counts":
            adapter_status_counts,
        "adapter_policy": {
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
        },
        "provider_payloads":
            payloads,
        "executions":
            executions,
    }

    validate_adapter_document(
        document
    )

    atomic_write_json(
        OUTPUT_FILE,
        document,
    )

    print(
        "===== Driverz Dry-run Generation Adapter v1 ====="
    )
    print(
        "Input generation requests:",
        len(requests),
    )
    print(
        "Provider payloads:",
        len(payloads),
    )
    print(
        "Executions:",
        len(executions),
    )
    print(
        "Action counts:",
        action_counts,
    )
    print(
        "Content type counts:",
        content_type_counts,
    )
    print(
        "Adapter status counts:",
        adapter_status_counts,
    )
    print(
        "Saved:",
        OUTPUT_FILE,
    )

    print(
        "\n===== DRY-RUN EXECUTIONS ====="
    )

    for item in executions:
        print(
            item["execution_priority"],
            "| status=",
            item["adapter_status"],
            "| api=",
            item["api_call_status"],
            "| generation=",
            item["generation_status"],
            "|",
            item["normalized_topic"],
        )


if __name__ == "__main__":
    main()
