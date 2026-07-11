#!/usr/bin/env python3
"""Rebuild descriptive and lineage discovery indexes from work manifests."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
METADATA_DIR = Path("manifests/work-metadata")
LINEAGE_DIR = Path("manifests/lineage")
GENERATED_DATE = "2026-07-11"


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _work_manifests(root: Path, directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    records = [(path, _load(path)) for path in (root / directory / "works").glob("*.json")]
    return sorted(records, key=lambda item: str(item[1].get("work_id", "")).casefold())


def build_metadata_index(root: Path) -> dict[str, Any]:
    records = _work_manifests(root, METADATA_DIR)
    items: list[dict[str, Any]] = []
    for path, manifest in records:
        summary = manifest.get("catalog_summary", {})
        subject = manifest.get("cataloging_subject", {})
        lineage = manifest.get("lineage", {})
        raw_lineage_path = lineage.get("manifest_path")
        lineage_manifest = None
        if isinstance(raw_lineage_path, str):
            lineage_manifest = os.path.relpath(
                root / raw_lineage_path,
                root / METADATA_DIR,
            )
        genres = manifest.get("genre_statements", [])
        items.append(
            {
                "id": manifest.get("id"),
                "work_id": manifest.get("work_id"),
                "preferred_title": summary.get("title"),
                "author_display": summary.get("author"),
                "editor_display": summary.get("editor"),
                "date_display": summary.get("date"),
                "region_display": summary.get("region"),
                "manifest": f"works/{path.name}",
                "unit_type": subject.get("unit_type"),
                "primary_form": summary.get("form"),
                "language_codes": summary.get("language_codes"),
                "genre_terms": [
                    record.get("term") for record in genres if isinstance(record, dict)
                ],
                "tags": manifest.get("tags"),
                "lineage_manifest": lineage_manifest,
                "record_status": manifest.get("record_status"),
                "last_reviewed": manifest.get("last_reviewed"),
            }
        )

    return {
        "$schema": "schemas/work-metadata-index.schema.json",
        "schema_version": "1.0.0",
        "generated": GENERATED_DATE,
        "coverage": {
            "strategy": "incremental",
            "manifest_count": len(items),
            "notes": (
                "Descriptive work metadata is added only after source-specific cataloging. "
                "A repository work absent from this index has not yet been cataloged in this "
                "system; absence is not a claim that metadata is unknowable."
            ),
        },
        "items": items,
    }


def _umich_identifier(manifest: dict[str, Any]) -> dict[str, str]:
    work_id = str(manifest.get("work_id", ""))
    entities = [item for item in manifest.get("entities", []) if isinstance(item, dict)]
    primary_id = manifest.get("primary_subject")
    ordered_entities = [item for item in entities if item.get("id") == primary_id]
    ordered_entities.extend(item for item in entities if item.get("id") != primary_id)
    for entity in ordered_entities:
        for identifier in entity.get("identifiers", []):
            if not isinstance(identifier, dict):
                continue
            uri = identifier.get("uri")
            value = identifier.get("value")
            if (
                isinstance(uri, str)
                and "name.umdl.umich.edu/" in uri
                and isinstance(value, str)
            ):
                return {"scheme": "CME", "value": value, "uri": uri}
    return {
        "scheme": "CME",
        "value": work_id,
        "uri": f"https://name.umdl.umich.edu/{work_id}",
    }


def build_lineage_index(root: Path) -> dict[str, Any]:
    records = _work_manifests(root, LINEAGE_DIR)
    items: list[dict[str, Any]] = []
    for path, manifest in records:
        primary_id = manifest.get("primary_subject")
        primary = next(
            (
                entity
                for entity in manifest.get("entities", [])
                if isinstance(entity, dict) and entity.get("id") == primary_id
            ),
            None,
        )
        if not isinstance(primary, dict):
            raise ValueError(f"{path}: unresolved primary_subject {primary_id!r}")
        repository_file = primary.get("repository_file")
        if not isinstance(repository_file, dict) or not isinstance(
            repository_file.get("path"), str
        ):
            raise ValueError(f"{path}: primary subject lacks repository_file.path")
        items.append(
            {
                "id": manifest.get("id"),
                "work_id": manifest.get("work_id"),
                "title": manifest.get("title"),
                "manifest": f"works/{path.name}",
                "repository_paths": [repository_file["path"]],
                "external_identifiers": [_umich_identifier(manifest)],
                "record_status": manifest.get("record_status"),
                "last_reviewed": manifest.get("last_reviewed"),
            }
        )

    return {
        "$schema": "schemas/lineage-index.schema.json",
        "schema_version": "1.0.0",
        "generated": GENERATED_DATE,
        "coverage": {
            "strategy": "incremental",
            "manifest_count": len(items),
            "notes": (
                "Lineage records are added only after source-specific research. This index "
                "does not imply that the remaining repository works lack provenance; they "
                "have not yet been represented in this manifest system."
            ),
        },
        "items": items,
    }


def _render(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def _update(path: Path, value: dict[str, Any], check: bool) -> bool:
    rendered = _render(value)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current == rendered:
        return False
    if check:
        print(f"STALE: {path}")
    else:
        path.write_text(rendered, encoding="utf-8")
        print(f"Updated {path}")
    return True


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale indexes without writing them.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    changed = False
    changed |= _update(
        root / METADATA_DIR / "index.json",
        build_metadata_index(root),
        args.check,
    )
    changed |= _update(
        root / LINEAGE_DIR / "index.json",
        build_lineage_index(root),
        args.check,
    )
    if args.check and changed:
        return 1
    if not changed:
        print("Manifest indexes are current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
