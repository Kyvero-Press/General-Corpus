#!/usr/bin/env python3
"""Validate General Corpus descriptive work metadata manifests offline."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any


METADATA_DIR = Path("manifests/work-metadata")
INDEX_PATH = METADATA_DIR / "index.json"
INDEX_SCHEMA_PATH = METADATA_DIR / "schemas/work-metadata-index.schema.json"
MANIFEST_SCHEMA_PATH = METADATA_DIR / "schemas/work-metadata-manifest.schema.json"
WORKS_DIR = METADATA_DIR / "works"


def _load_schema_support() -> Any:
    """Reuse the repository's dependency-free JSON Schema subset validator."""

    support_path = Path(__file__).resolve().with_name("validate-lineage-manifests.py")
    spec = importlib.util.spec_from_file_location("_manifest_schema_validation_support", support_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load schema validation support from {support_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


_SCHEMA_SUPPORT = _load_schema_support()


def _record_ids(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    collections = (
        "titles",
        "agents",
        "responsibilities",
        "date_statements",
        "places",
        "place_statements",
        "language_statements",
        "form_statements",
        "genre_statements",
        "subject_statements",
        "summaries",
        "content_parts",
        "related_works",
        "evidence",
        "open_questions",
    )
    records: dict[str, dict[str, Any]] = {}
    locations: dict[str, str] = {}
    cataloging_subject = manifest.get("cataloging_subject")
    if isinstance(cataloging_subject, dict) and isinstance(cataloging_subject.get("id"), str):
        records[cataloging_subject["id"]] = cataloging_subject
        locations[cataloging_subject["id"]] = "cataloging_subject"
    for collection_name in collections:
        collection = manifest.get(collection_name, [])
        if not isinstance(collection, list):
            continue
        for index, record in enumerate(collection):
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                record_id = record["id"]
                if record_id not in records:
                    records[record_id] = record
                    locations[record_id] = f"{collection_name}[{index}]"
    return records, locations


def _check_evidence_refs(
    refs: Any,
    evidence_ids: set[str],
    location: str,
    errors: list[str],
) -> None:
    if not isinstance(refs, list):
        return
    for ref in refs:
        if ref not in evidence_ids:
            errors.append(f"{location}: unresolved evidence reference {ref!r}")


def _check_scope(
    scope: Any,
    part_ids: set[str],
    location: str,
    errors: list[str],
) -> None:
    if not isinstance(scope, dict):
        return
    kind = scope.get("kind")
    refs = scope.get("part_ids", [])
    if kind == "whole" and refs:
        errors.append(f"{location}: whole scope must not contain part_ids")
    if kind in {"part", "selected_passages"} and not refs:
        errors.append(f"{location}: {kind} scope requires at least one part_id")
    if isinstance(refs, list):
        for index, ref in enumerate(refs):
            if ref not in part_ids:
                errors.append(f"{location}.part_ids[{index}]: unresolved content part {ref!r}")


def _check_assertion(
    record: dict[str, Any],
    evidence_ids: set[str],
    part_ids: set[str],
    location: str,
    errors: list[str],
) -> None:
    _check_scope(record.get("scope"), part_ids, f"{location}.scope", errors)
    assertion = record.get("assertion")
    if isinstance(assertion, dict):
        _check_evidence_refs(
            assertion.get("evidence_ids"),
            evidence_ids,
            f"{location}.assertion.evidence_ids",
            errors,
        )


def _lineage_data(
    repo_root: Path,
    manifest: dict[str, Any],
    location: str,
    errors: list[str],
) -> tuple[dict[str, Any] | None, Path | None]:
    lineage = manifest.get("lineage")
    if not isinstance(lineage, dict):
        return None, None
    raw_path = lineage.get("manifest_path")
    lineage_path = _SCHEMA_SUPPORT._safe_repo_file(
        repo_root,
        raw_path,
        f"{location}.lineage.manifest_path",
        errors,
    )
    if lineage_path is None:
        return None, None
    lineage_data = _SCHEMA_SUPPORT._load_json(lineage_path, errors)
    if not isinstance(lineage_data, dict):
        return None, lineage_path
    if lineage_data.get("id") != lineage.get("manifest_id"):
        errors.append(
            f"{location}.lineage.manifest_id: {lineage.get('manifest_id')!r} does not match "
            f"linked manifest id {lineage_data.get('id')!r}"
        )
    if lineage_data.get("work_id") != manifest.get("work_id"):
        errors.append(
            f"{location}.lineage: linked work_id {lineage_data.get('work_id')!r} does not match "
            f"metadata work_id {manifest.get('work_id')!r}"
        )
    return lineage_data, lineage_path


def _xml_identifier_aliases_for_repository_path(
    lineage_data: dict[str, Any] | None,
    repository_path: Any,
) -> list[str]:
    """Return explicit XML aliases declared by linked lineage repository files."""

    if not isinstance(lineage_data, dict) or not isinstance(repository_path, str):
        return []
    aliases: list[str] = []
    for entity in lineage_data.get("entities", []):
        if not isinstance(entity, dict):
            continue
        repository_file = entity.get("repository_file")
        if (
            not isinstance(repository_file, dict)
            or repository_file.get("path") != repository_path
        ):
            continue
        for alias in repository_file.get("xml_identifier_aliases", []):
            if isinstance(alias, str) and alias and alias not in aliases:
                aliases.append(alias)
    return aliases


def _check_part_graph(parts: list[Any], location: str, errors: list[str]) -> None:
    by_id = {
        part.get("id"): part
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("id"), str)
    }
    sibling_sequences: set[tuple[str | None, int]] = set()
    for index, part in enumerate(parts):
        if not isinstance(part, dict):
            continue
        item_location = f"{location}.content_parts[{index}]"
        parent_id = part.get("parent_id")
        if parent_id is not None and parent_id not in by_id:
            errors.append(f"{item_location}.parent_id: unresolved parent {parent_id!r}")
        sequence = part.get("sequence")
        if isinstance(sequence, int):
            key = (parent_id, sequence)
            if key in sibling_sequences:
                errors.append(
                    f"{item_location}.sequence: duplicate sibling sequence {sequence} "
                    f"under parent {parent_id!r}"
                )
            sibling_sequences.add(key)

    for part_id in by_id:
        seen: set[str] = set()
        current: str | None = part_id
        while current is not None:
            if current in seen:
                errors.append(f"{location}.content_parts: parent cycle includes {current!r}")
                break
            seen.add(current)
            parent = by_id.get(current, {}).get("parent_id")
            current = parent if isinstance(parent, str) else None


def _check_extent_totals(manifest: dict[str, Any], location: str, errors: list[str]) -> None:
    extent = manifest.get("extent")
    parts = manifest.get("content_parts")
    if not isinstance(extent, dict) or not isinstance(parts, list):
        return
    counted_parts = [
        item for item in parts if isinstance(item, dict) and isinstance(item.get("item_count"), int)
    ]
    if counted_parts and isinstance(extent.get("numbered_items"), int):
        total_items = sum(item["item_count"] for item in counted_parts)
        if total_items != extent["numbered_items"]:
            errors.append(
                f"{location}.extent.numbered_items: part total is {total_items}, "
                f"recorded extent is {extent['numbered_items']}"
            )
    metric_keys = (
        "prose_only_items",
        "verse_only_items",
        "mixed_items",
        "verse_groups",
        "verse_lines",
    )
    metric_parts = [item for item in counted_parts if isinstance(item.get("metrics"), dict)]
    if metric_parts and len(metric_parts) == len(counted_parts):
        for key in metric_keys:
            values = [item["metrics"].get(key) for item in metric_parts]
            if all(isinstance(value, int) for value in values) and isinstance(extent.get(key), int):
                total = sum(values)
                if total != extent[key]:
                    errors.append(
                        f"{location}.extent.{key}: part total is {total}, recorded extent is "
                        f"{extent[key]}"
                    )


def _semantic_manifest_errors(
    repo_root: Path,
    path: Path,
    manifest: dict[str, Any],
    *,
    allow_missing_source_cache: bool = False,
) -> list[str]:
    errors: list[str] = []
    location = str(path.relative_to(repo_root))
    work_id = manifest.get("work_id")
    if isinstance(work_id, str):
        if path.stem != work_id:
            errors.append(f"{location}: filename must equal work_id ({work_id}.json)")
        if manifest.get("id") != f"metadata:{work_id}":
            errors.append(f"{location}.id: expected metadata:{work_id}")

    records, first_locations = _record_ids(manifest)
    all_seen: dict[str, str] = {}
    cataloging_subject = manifest.get("cataloging_subject")
    if isinstance(cataloging_subject, dict) and isinstance(cataloging_subject.get("id"), str):
        all_seen[cataloging_subject["id"]] = "cataloging_subject"
    for collection_name in (
        "titles",
        "agents",
        "responsibilities",
        "date_statements",
        "places",
        "place_statements",
        "language_statements",
        "form_statements",
        "genre_statements",
        "subject_statements",
        "summaries",
        "content_parts",
        "related_works",
        "evidence",
        "open_questions",
    ):
        for index, record in enumerate(manifest.get(collection_name, [])):
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                continue
            record_id = record["id"]
            item_location = f"{collection_name}[{index}]"
            if record_id in all_seen:
                errors.append(
                    f"{location}.{item_location}: duplicate record id {record_id!r}; "
                    f"first used at {all_seen[record_id]}"
                )
            else:
                all_seen[record_id] = item_location

    evidence_ids = {
        item.get("id") for item in manifest.get("evidence", []) if isinstance(item, dict)
    }
    part_ids = {
        item.get("id") for item in manifest.get("content_parts", []) if isinstance(item, dict)
    }
    agent_ids = {
        item.get("id") for item in manifest.get("agents", []) if isinstance(item, dict)
    }
    place_ids = {
        item.get("id") for item in manifest.get("places", []) if isinstance(item, dict)
    }
    evidence_ids.discard(None)
    part_ids.discard(None)
    agent_ids.discard(None)
    place_ids.discard(None)

    titles = manifest.get("titles", [])
    preferred = [
        item
        for item in titles
        if isinstance(item, dict)
        and item.get("type") == "preferred"
        and item.get("scope", {}).get("kind") == "whole"
    ]
    if len(preferred) != 1:
        errors.append(f"{location}.titles: expected exactly one whole-scope preferred title")
    summary = manifest.get("catalog_summary")
    if isinstance(summary, dict) and preferred and summary.get("title") != preferred[0].get("value"):
        errors.append(f"{location}.catalog_summary.title: does not match preferred title")

    whole_forms = [
        item
        for item in manifest.get("form_statements", [])
        if isinstance(item, dict) and item.get("scope", {}).get("kind") == "whole"
    ]
    if len(whole_forms) != 1:
        errors.append(f"{location}.form_statements: expected exactly one whole-scope form")
    if isinstance(summary, dict) and whole_forms and summary.get("form") != whole_forms[0].get("value"):
        errors.append(f"{location}.catalog_summary.form: does not match whole-scope form")

    for collection_name in (
        "titles",
        "responsibilities",
        "date_statements",
        "place_statements",
        "language_statements",
        "form_statements",
        "genre_statements",
        "subject_statements",
    ):
        for index, record in enumerate(manifest.get(collection_name, [])):
            if isinstance(record, dict):
                _check_assertion(
                    record,
                    evidence_ids,
                    part_ids,
                    f"{location}.{collection_name}[{index}]",
                    errors,
                )

    for index, responsibility in enumerate(manifest.get("responsibilities", [])):
        if not isinstance(responsibility, dict):
            continue
        item_location = f"{location}.responsibilities[{index}]"
        agent_id = responsibility.get("agent_id")
        status = responsibility.get("attribution_status")
        if isinstance(agent_id, str) and agent_id not in agent_ids:
            errors.append(f"{item_location}.agent_id: unresolved agent {agent_id!r}")
        if status in {"known", "attributed", "disputed"} and not isinstance(agent_id, str):
            errors.append(f"{item_location}: attribution status {status!r} requires agent_id")
        if status in {"anonymous", "unknown"} and not (
            isinstance(agent_id, str) or isinstance(responsibility.get("display_name"), str)
        ):
            errors.append(f"{item_location}: anonymous/unknown responsibility requires display_name")

    if isinstance(summary, dict):
        author_names = [
            item.get("display_name")
            for item in manifest.get("responsibilities", [])
            if isinstance(item, dict)
            and item.get("role") in {"author", "coauthor", "attributed_author"}
            and isinstance(item.get("display_name"), str)
        ]
        if author_names and summary.get("author") not in author_names:
            errors.append(f"{location}.catalog_summary.author: does not match an author display_name")
        agent_by_id = {
            item.get("id"): item for item in manifest.get("agents", []) if isinstance(item, dict)
        }
        editor_names = [
            agent_by_id.get(item.get("agent_id"), {}).get("name")
            for item in manifest.get("responsibilities", [])
            if isinstance(item, dict) and item.get("role") == "editor"
        ]
        editor_names = [name for name in editor_names if isinstance(name, str)]
        editor_display = summary.get("editor")
        names_a_single_editor = editor_display in editor_names
        names_every_editor = isinstance(editor_display, str) and all(
            name in editor_display for name in editor_names
        )
        if editor_names and not (names_a_single_editor or names_every_editor):
            errors.append(
                f"{location}.catalog_summary.editor: must name one editor agent or include "
                "every editor agent in a composite display"
            )

        language_codes = {
            item.get("code")
            for item in manifest.get("language_statements", [])
            if isinstance(item, dict)
        }
        language_codes.discard(None)
        if set(summary.get("language_codes", [])) != language_codes:
            errors.append(
                f"{location}.catalog_summary.language_codes: does not match language statements"
            )
        genre_labels = [
            item.get("label")
            for item in manifest.get("genre_statements", [])
            if isinstance(item, dict)
        ]
        if summary.get("genres") != genre_labels:
            errors.append(f"{location}.catalog_summary.genres: does not match genre labels")
        if summary.get("tags") != manifest.get("tags"):
            errors.append(f"{location}.catalog_summary.tags: does not match top-level tags")

    for index, statement in enumerate(manifest.get("date_statements", [])):
        if not isinstance(statement, dict):
            continue
        normalized = statement.get("normalized")
        if isinstance(normalized, dict):
            start = normalized.get("not_before")
            end = normalized.get("not_after")
            if isinstance(start, int) and isinstance(end, int) and start > end:
                errors.append(
                    f"{location}.date_statements[{index}].normalized: not_before exceeds not_after"
                )

    for index, place in enumerate(manifest.get("places", [])):
        if not isinstance(place, dict):
            continue
        for ref_index, ref in enumerate(place.get("broader_place_ids", [])):
            if ref not in place_ids:
                errors.append(
                    f"{location}.places[{index}].broader_place_ids[{ref_index}]: "
                    f"unresolved place {ref!r}"
                )
    for index, statement in enumerate(manifest.get("place_statements", [])):
        if isinstance(statement, dict) and statement.get("place_id") not in place_ids:
            errors.append(
                f"{location}.place_statements[{index}].place_id: unresolved place "
                f"{statement.get('place_id')!r}"
            )

    for collection_name in ("summaries", "content_parts", "related_works", "open_questions"):
        for index, record in enumerate(manifest.get(collection_name, [])):
            if not isinstance(record, dict):
                continue
            _check_evidence_refs(
                record.get("evidence_ids"),
                evidence_ids,
                f"{location}.{collection_name}[{index}].evidence_ids",
                errors,
            )
            if "scope" in record:
                _check_scope(
                    record.get("scope"),
                    part_ids,
                    f"{location}.{collection_name}[{index}].scope",
                    errors,
                )
    extent = manifest.get("extent")
    if isinstance(extent, dict):
        _check_evidence_refs(
            extent.get("evidence_ids"), evidence_ids, f"{location}.extent.evidence_ids", errors
        )

    _check_part_graph(manifest.get("content_parts", []), location, errors)
    _check_extent_totals(manifest, location, errors)

    lineage_data, lineage_path = _lineage_data(repo_root, manifest, location, errors)
    lineage_entity_ids: set[str] = set()
    lineage_evidence_ids: set[str] = set()
    if isinstance(lineage_data, dict):
        lineage_entity_ids = {
            item.get("id") for item in lineage_data.get("entities", []) if isinstance(item, dict)
        }
        lineage_evidence_ids = {
            item.get("id") for item in lineage_data.get("evidence", []) if isinstance(item, dict)
        }
        lineage_entity_ids.discard(None)
        lineage_evidence_ids.discard(None)

    metadata_targets = part_ids | {
        manifest.get("cataloging_subject", {}).get("id")
        if isinstance(manifest.get("cataloging_subject"), dict)
        else None
    }
    metadata_targets.discard(None)
    for index, binding in enumerate(manifest.get("lineage", {}).get("bindings", [])):
        if not isinstance(binding, dict):
            continue
        target = binding.get("metadata_target")
        entity_id = binding.get("lineage_entity_id")
        if target not in metadata_targets:
            errors.append(
                f"{location}.lineage.bindings[{index}].metadata_target: unresolved target {target!r}"
            )
        if lineage_data is not None and entity_id not in lineage_entity_ids:
            errors.append(
                f"{location}.lineage.bindings[{index}].lineage_entity_id: unresolved lineage "
                f"entity {entity_id!r}"
            )

    lineage_ref_fields: list[tuple[str, Any]] = []
    for collection_name in ("date_statements", "place_statements"):
        for index, record in enumerate(manifest.get(collection_name, [])):
            if isinstance(record, dict) and "source_lineage_entity_id" in record:
                lineage_ref_fields.append(
                    (
                        f"{location}.{collection_name}[{index}].source_lineage_entity_id",
                        record.get("source_lineage_entity_id"),
                    )
                )
    for part_index, part in enumerate(manifest.get("content_parts", [])):
        if not isinstance(part, dict):
            continue
        for locator_index, locator in enumerate(part.get("locators", [])):
            if isinstance(locator, dict) and "lineage_entity_id" in locator:
                lineage_ref_fields.append(
                    (
                        f"{location}.content_parts[{part_index}].locators[{locator_index}]"
                        ".lineage_entity_id",
                        locator.get("lineage_entity_id"),
                    )
                )
    if lineage_data is not None:
        for ref_location, ref in lineage_ref_fields:
            if ref not in lineage_entity_ids:
                errors.append(f"{ref_location}: unresolved lineage entity {ref!r}")

    for index, evidence in enumerate(manifest.get("evidence", [])):
        if not isinstance(evidence, dict):
            continue
        item_location = f"{location}.evidence[{index}]"
        if "repository_path" in evidence:
            evidence_path = _SCHEMA_SUPPORT._safe_repo_file(
                repo_root,
                evidence.get("repository_path"),
                f"{item_location}.repository_path",
                errors,
                allow_missing_source_cache=allow_missing_source_cache,
            )
            if evidence_path is not None:
                expected_sha = evidence.get("sha256")
                if isinstance(expected_sha, str) and _SCHEMA_SUPPORT._sha256(evidence_path) != expected_sha:
                    errors.append(f"{item_location}.sha256: checksum mismatch")
                if evidence_path.suffix.lower() == ".xml" and isinstance(work_id, str):
                    _SCHEMA_SUPPORT._validate_xml_work_id(
                        evidence_path,
                        work_id,
                        item_location,
                        errors,
                        _xml_identifier_aliases_for_repository_path(
                            lineage_data,
                            evidence.get("repository_path"),
                        ),
                    )
        source_evidence_id = evidence.get("source_evidence_id")
        if isinstance(source_evidence_id, str) and lineage_data is not None:
            if source_evidence_id not in lineage_evidence_ids:
                errors.append(
                    f"{item_location}.source_evidence_id: unresolved lineage evidence "
                    f"{source_evidence_id!r}"
                )
            raw_path = evidence.get("repository_path")
            if lineage_path is not None and isinstance(raw_path, str):
                if (repo_root / raw_path).resolve() != lineage_path.resolve():
                    errors.append(
                        f"{item_location}: source_evidence_id must point at the linked lineage manifest"
                    )

    return errors


def validate_repository(
    repo_root: Path,
    *,
    allow_missing_source_cache: bool = False,
) -> list[str]:
    repo_root = repo_root.resolve()
    errors: list[str] = []
    index_schema = _SCHEMA_SUPPORT._load_json(repo_root / INDEX_SCHEMA_PATH, errors)
    manifest_schema = _SCHEMA_SUPPORT._load_json(repo_root / MANIFEST_SCHEMA_PATH, errors)
    index = _SCHEMA_SUPPORT._load_json(repo_root / INDEX_PATH, errors)
    if not all(isinstance(item, dict) for item in (index_schema, manifest_schema, index)):
        return errors

    errors.extend(
        _SCHEMA_SUPPORT._schema_errors(index, index_schema, index_schema, str(INDEX_PATH))
    )
    discovered_paths = sorted((repo_root / WORKS_DIR).glob("*.json"))
    discovered_relative = {
        str(path.relative_to(repo_root / METADATA_DIR)) for path in discovered_paths
    }
    indexed_items = index.get("items", []) if isinstance(index.get("items"), list) else []
    indexed_relative = {
        item.get("manifest") for item in indexed_items if isinstance(item, dict)
    }
    indexed_relative.discard(None)
    if discovered_relative != indexed_relative:
        missing = sorted(discovered_relative - indexed_relative)
        stale = sorted(indexed_relative - discovered_relative)
        if missing:
            errors.append(f"{INDEX_PATH}: manifests missing from index: {missing!r}")
        if stale:
            errors.append(f"{INDEX_PATH}: indexed manifests do not exist: {stale!r}")

    manifest_count = index.get("coverage", {}).get("manifest_count")
    if manifest_count != len(discovered_paths):
        errors.append(
            f"{INDEX_PATH}.coverage.manifest_count: expected {len(discovered_paths)}, "
            f"found {manifest_count!r}"
        )

    seen_ids: set[str] = set()
    seen_work_ids: set[str] = set()
    for index_number, item in enumerate(indexed_items):
        if not isinstance(item, dict):
            continue
        item_location = f"{INDEX_PATH}.items[{index_number}]"
        for key, seen in (("id", seen_ids), ("work_id", seen_work_ids)):
            value = item.get(key)
            if isinstance(value, str):
                if value in seen:
                    errors.append(f"{item_location}.{key}: duplicate value {value!r}")
                seen.add(value)

        relative_manifest = item.get("manifest")
        if not isinstance(relative_manifest, str):
            continue
        manifest_path = repo_root / METADATA_DIR / relative_manifest
        manifest = _SCHEMA_SUPPORT._load_json(manifest_path, errors)
        if not isinstance(manifest, dict):
            continue
        manifest_location = str(manifest_path.relative_to(repo_root))
        errors.extend(
            _SCHEMA_SUPPORT._schema_errors(
                manifest, manifest_schema, manifest_schema, manifest_location
            )
        )
        errors.extend(
            _semantic_manifest_errors(
                repo_root,
                manifest_path,
                manifest,
                allow_missing_source_cache=allow_missing_source_cache,
            )
        )

        summary = manifest.get("catalog_summary", {})
        subject = manifest.get("cataloging_subject", {})
        genres = manifest.get("genre_statements", [])
        lineage = manifest.get("lineage", {})
        raw_lineage_path = lineage.get("manifest_path")
        expected_lineage_index_path = None
        if isinstance(raw_lineage_path, str):
            expected_lineage_index_path = os.path.relpath(
                repo_root / raw_lineage_path,
                repo_root / METADATA_DIR,
            )
        expected = {
            "id": manifest.get("id"),
            "work_id": manifest.get("work_id"),
            "preferred_title": summary.get("title"),
            "author_display": summary.get("author"),
            "editor_display": summary.get("editor"),
            "date_display": summary.get("date"),
            "region_display": summary.get("region"),
            "unit_type": subject.get("unit_type"),
            "primary_form": summary.get("form"),
            "language_codes": summary.get("language_codes"),
            "genre_terms": [record.get("term") for record in genres if isinstance(record, dict)],
            "tags": manifest.get("tags"),
            "lineage_manifest": expected_lineage_index_path,
            "record_status": manifest.get("record_status"),
            "last_reviewed": manifest.get("last_reviewed"),
        }
        for key, value in expected.items():
            if item.get(key) != value:
                errors.append(
                    f"{item_location}.{key}: index value {item.get(key)!r} does not match "
                    f"manifest-derived value {value!r}"
                )
        if item.get("work_id") and Path(relative_manifest).stem != item["work_id"]:
            errors.append(f"{item_location}.manifest: filename does not match work_id")

    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root (defaults to the parent of scripts/)",
    )
    parser.add_argument(
        "--allow-missing-source-cache",
        action="store_true",
        help=(
            "allow absent evidence files only when they resolve inside the "
            "gitignored source-cache directory"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors = validate_repository(
        args.root,
        allow_missing_source_cache=args.allow_missing_source_cache,
    )
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        print(f"Work metadata validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    index = json.loads((args.root / INDEX_PATH).read_text(encoding="utf-8"))
    count = len(index["items"])
    noun = "manifest" if count == 1 else "manifests"
    print(
        f"Validated {count} work metadata {noun}; index, assertions, source IDs, "
        "lineage bindings, and checksums are consistent."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
