#!/usr/bin/env python3

import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from validate_dry_run_adapter_contract import (
    validate_document as validate_adapter_document,
)

from validate_provider_execution_contract import (
    sha256_value,
    validate_document as validate_execution_document,
)


BOUNDARY_VERSION = 1

INPUT_FILE = Path(
    "data/content/dry-run-generation-adapter.json"
)

OUTPUT_FILE = Path(
    "data/content/provider-execution-boundary.json"
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


def build_execution(adapter_execution, priority):
    item = {
        "execution_priority":
            priority,
        "normalized_topic":
            adapter_execution["normalized_topic"],
        "generation_request_fingerprint":
            adapter_execution[
                "generation_request_fingerprint"
            ],
        "provider_payload_fingerprint":
            adapter_execution[
                "provider_payload_fingerprint"
            ],
        "attempt_number":
            0,
        "provider_status":
            "not_called",
        "attempt_status":
            "not_started",
        "response_status":
            "not_received",
        "failure_status":
            "none",
        "response_envelope":
            None,
        "failure_record":
            None,
    }

    item["execution_id"] = sha256_value({
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

    item["idempotency_key"] = sha256_value({
        "execution_id":
            item["execution_id"],
        "attempt_number":
            item["attempt_number"],
    })

    item["execution_fingerprint"] = sha256_value(
        item
    )

    return item


def main():
    adapter_data = json.loads(
        INPUT_FILE.read_text(
            encoding="utf-8"
        )
    )

    validate_adapter_document(
        adapter_data
    )

    adapter_executions = adapter_data[
        "executions"
    ]

    executions = [
        build_execution(item, index)
        for index, item in enumerate(
            adapter_executions,
            start=1,
        )
    ]

    attempt_status_counts = dict(
        Counter(
            item["attempt_status"]
            for item in executions
        )
    )

    document = {
        "source":
            "driverz_provider_execution_boundary",
        "provider_execution_contract_version":
            BOUNDARY_VERSION,
        "generated_at":
            utc_now(),
        "source_dry_run_adapter_version":
            adapter_data[
                "dry_run_adapter_version"
            ],
        "source_generation_request_version":
            adapter_data[
                "source_generation_request_version"
            ],
        "input_adapter_execution_count":
            len(adapter_executions),
        "execution_count":
            len(executions),
        "attempt_status_counts":
            attempt_status_counts,
        "execution_policy": {
            "source_dry_run_only":
                True,
            "provider_neutral":
                True,
            "allow_empty_executions":
                True,
            "automatic_api_call_enabled":
                False,
            "automatic_content_generation_enabled":
                False,
            "automatic_rendering_enabled":
                False,
            "automatic_publishing_enabled":
                False,
            "idempotency_enabled":
                True,
            "response_validation_required":
                True,
            "failure_record_required_on_failure":
                True,
            "fingerprint_algorithm":
                "sha256",
        },
        "executions":
            executions,
    }

    validate_execution_document(
        document
    )

    atomic_write_json(
        OUTPUT_FILE,
        document,
    )

    print(
        "===== Driverz Provider Execution Boundary v1 ====="
    )
    print(
        "Input adapter executions:",
        len(adapter_executions),
    )
    print(
        "Executions:",
        len(executions),
    )
    print(
        "Attempt status counts:",
        attempt_status_counts,
    )
    print(
        "Saved:",
        OUTPUT_FILE,
    )

    print(
        "\n===== PROVIDER EXECUTIONS ====="
    )

    for item in executions:
        print(
            item["execution_priority"],
            "| attempt=",
            item["attempt_number"],
            "| provider=",
            item["provider_status"],
            "| status=",
            item["attempt_status"],
            "| response=",
            item["response_status"],
            "| failure=",
            item["failure_status"],
            "|",
            item["normalized_topic"],
        )


if __name__ == "__main__":
    main()
