#!/usr/bin/env python3
"""Check rights/access layering and explicit access-local-copy boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def duplicate_ids(records: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for record in records:
        record_id = record.get("id")
        if not isinstance(record_id, str):
            continue
        if record_id in seen:
            duplicates.add(record_id)
        seen.add(record_id)
    return sorted(duplicates)


def check_manifest(path: Path) -> list[str]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot read valid JSON: {error}"]

    errors: list[str] = []
    entities = document.get("entities", [])
    access = document.get("access", [])
    rights = document.get("rights", [])

    for label, records in (
        ("entity", entities),
        ("access", access),
        ("rights", rights),
    ):
        duplicates = duplicate_ids(records)
        if duplicates:
            errors.append(f"duplicate {label} IDs: {', '.join(duplicates)}")

    entity_ids = {
        record.get("id") for record in entities if isinstance(record.get("id"), str)
    }
    access_by_id = {
        record.get("id"): record
        for record in access
        if isinstance(record.get("id"), str)
    }
    covered_entities: set[str] = set()

    for access_record in access:
        access_id = access_record.get("id", "access without ID")
        access_urls = {
            value
            for value in [
                access_record.get("url"),
                *access_record.get("alternate_urls", []),
            ]
            if isinstance(value, str)
        }
        for index, local_copy in enumerate(access_record.get("local_copies", [])):
            label = local_copy.get("label", f"local_copies[{index}]")
            presence = local_copy.get("target_work_presence")
            work_portion = local_copy.get("work_portion")
            if presence not in {"present", "absent"}:
                errors.append(
                    f"{access_id} / {label}: target_work_presence must be "
                    "explicitly 'present' or 'absent'"
                )
            elif presence == "present" and not isinstance(work_portion, dict):
                errors.append(
                    f"{access_id} / {label}: present target lacks work_portion"
                )
            elif presence == "absent" and work_portion is not None:
                errors.append(
                    f"{access_id} / {label}: absent target must omit work_portion"
                )

            source_url = local_copy.get("source_url")
            if isinstance(source_url, str) and source_url not in access_urls:
                errors.append(
                    f"{access_id} / {label}: source_url is not the access URL "
                    "or an alternate URL"
                )

    for index, record in enumerate(rights):
        rights_id = record.get("id", f"rights[{index}]")
        entity_id = record.get("entity")
        if entity_id not in entity_ids:
            errors.append(f"{rights_id}: unresolved entity {entity_id!r}")
            continue
        covered_entities.add(entity_id)

        access_id = record.get("access_id")
        if access_id is None:
            continue
        access_record = access_by_id.get(access_id)
        if access_record is None:
            errors.append(f"{rights_id}: unresolved access_id {access_id!r}")
            continue
        access_entity = access_record.get("entity")
        if access_entity != entity_id:
            errors.append(
                f"{rights_id}: entity {entity_id!r} does not match "
                f"{access_id} entity {access_entity!r}"
            )

    for entity_id in sorted(entity_ids - covered_entities):
        errors.append(f"{entity_id}: no rights record")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", type=Path)
    arguments = parser.parse_args()

    failed = False
    for path in arguments.manifests:
        errors = check_manifest(path)
        if errors:
            failed = True
            for error in errors:
                print(f"ERROR: {path}: {error}", file=sys.stderr)
        else:
            print(f"Rights/access entity audit passed: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
