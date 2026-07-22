#!/usr/bin/env python3
"""Validate General Corpus lineage manifests without network access or dependencies."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


LINEAGE_DIR = Path("manifests/lineage")
INDEX_PATH = LINEAGE_DIR / "index.json"
INDEX_SCHEMA_PATH = LINEAGE_DIR / "schemas/lineage-index.schema.json"
MANIFEST_SCHEMA_PATH = LINEAGE_DIR / "schemas/lineage-manifest.schema.json"
WORKS_DIR = LINEAGE_DIR / "works"
SOURCE_CACHE_DIR = Path("source-cache")


def _load_json(path: Path, errors: list[str]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"{path}: file does not exist")
    except json.JSONDecodeError as exc:
        errors.append(f"{path}:{exc.lineno}:{exc.colno}: invalid JSON: {exc.msg}")
    except OSError as exc:
        errors.append(f"{path}: cannot read file: {exc}")
    return None


def _json_type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _resolve_local_ref(root_schema: dict[str, Any], ref: str) -> Any:
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported non-local schema reference {ref!r}")
    value: Any = root_schema
    for raw_part in ref[2:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        value = value[part]
    return value


def _validate_format(value: str, format_name: str) -> bool:
    if format_name == "date":
        try:
            return date.fromisoformat(value).isoformat() == value
        except ValueError:
            return False
    if format_name == "uri":
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    return True


def _schema_errors(
    value: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any],
    location: str,
) -> list[str]:
    """Validate the JSON Schema features used by this repository's schemas."""

    if "$ref" in schema:
        try:
            target = _resolve_local_ref(root_schema, schema["$ref"])
        except (KeyError, TypeError, ValueError) as exc:
            return [f"{location}: invalid schema reference: {exc}"]
        return _schema_errors(value, target, root_schema, location)

    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type is not None:
        allowed_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_json_type_matches(value, item) for item in allowed_types):
            errors.append(
                f"{location}: expected JSON type {' or '.join(allowed_types)}, "
                f"got {type(value).__name__}"
            )
            return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: value {value!r} is not in {schema['enum']!r}")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{location}: value {value!r} does not equal {schema['const']!r}")

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{location}: string is shorter than {min_length}")
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            errors.append(f"{location}: value {value!r} does not match {pattern!r}")
        format_name = schema.get("format")
        if format_name is not None and not _validate_format(value, format_name):
            errors.append(f"{location}: value {value!r} is not a valid {format_name}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        if minimum is not None and value < minimum:
            errors.append(f"{location}: value {value!r} is less than {minimum}")

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{location}: array has fewer than {min_items} items")
        if schema.get("uniqueItems"):
            serialized = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in value]
            if len(set(serialized)) != len(serialized):
                errors.append(f"{location}: array items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_schema_errors(item, item_schema, root_schema, f"{location}[{index}]"))

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{location}: missing required property {key!r}")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                errors.extend(
                    _schema_errors(item, properties[key], root_schema, f"{location}.{key}")
                )
            elif schema.get("additionalProperties") is False:
                errors.append(f"{location}: unexpected property {key!r}")

    if "anyOf" in schema:
        alternatives = [
            _schema_errors(value, alternative, root_schema, location)
            for alternative in schema["anyOf"]
        ]
        if all(alternative_errors for alternative_errors in alternatives):
            errors.append(f"{location}: value does not satisfy any anyOf alternative")

    if "not" in schema:
        prohibited_errors = _schema_errors(value, schema["not"], root_schema, location)
        if not prohibited_errors:
            errors.append(f"{location}: value satisfies a prohibited schema")

    for requirement in schema.get("allOf", []):
        errors.extend(_schema_errors(value, requirement, root_schema, location))

    if "if" in schema:
        condition_errors = _schema_errors(value, schema["if"], root_schema, location)
        branch_name = "then" if not condition_errors else "else"
        branch = schema.get(branch_name)
        if isinstance(branch, dict):
            errors.extend(_schema_errors(value, branch, root_schema, location))

    return errors


def _safe_repo_file(
    repo_root: Path,
    raw_path: Any,
    location: str,
    errors: list[str],
    *,
    allow_missing_source_cache: bool = False,
) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path:
        errors.append(f"{location}: repository path must be a non-empty string")
        return None
    path = Path(raw_path)
    if path.is_absolute():
        errors.append(f"{location}: repository path must be relative: {raw_path!r}")
        return None
    resolved_root = repo_root.resolve()
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError:
        errors.append(f"{location}: repository path escapes the repository: {raw_path!r}")
        return None
    if resolved.is_file():
        return resolved
    if (
        allow_missing_source_cache
        and not resolved.exists()
        and path.parts
        and path.parts[0] == SOURCE_CACHE_DIR.name
    ):
        resolved_cache = (repo_root / SOURCE_CACHE_DIR).resolve()
        try:
            cache_relative = resolved.relative_to(resolved_cache)
        except ValueError:
            pass
        else:
            if cache_relative.parts:
                return None
    if not resolved.is_file():
        errors.append(f"{location}: repository file does not exist: {raw_path!r}")
        return None
    return resolved


def _safe_local_copy(
    repo_root: Path,
    raw_path: Any,
    work_id: Any,
    location: str,
    errors: list[str],
) -> Path | None:
    """Validate a gitignored cache path and return it only when present."""

    if not isinstance(raw_path, str) or not raw_path:
        errors.append(f"{location}: local copy path must be a non-empty string")
        return None
    if not isinstance(work_id, str) or not work_id:
        errors.append(f"{location}: cannot validate local copy without a work_id")
        return None
    path = Path(raw_path)
    expected_parent = SOURCE_CACHE_DIR / work_id
    if path.is_absolute() or path.parent != expected_parent or path.name in {"", ".", ".."}:
        errors.append(
            f"{location}: local copy must be one file under "
            f"{expected_parent.as_posix()!r}: {raw_path!r}"
        )
        return None
    resolved_root = repo_root.resolve()
    resolved_cache = (repo_root / expected_parent).resolve()
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(resolved_root)
        resolved.relative_to(resolved_cache)
    except ValueError:
        errors.append(f"{location}: local copy path escapes its work cache: {raw_path!r}")
        return None
    if resolved.exists() and not resolved.is_file():
        errors.append(f"{location}: local copy path is not a file: {raw_path!r}")
        return None
    return resolved if resolved.is_file() else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_iiif_bundle(
    path: Path,
    local_copy: dict[str, Any],
    location: str,
    errors: list[str],
) -> None:
    source_kind = local_copy.get("bundle_source_kind")
    expected_source_member = (
        "source-list.json" if source_kind == "image_url_inventory" else "manifest.json"
    )
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            for required_name in (expected_source_member, "inventory.json"):
                if required_name not in names:
                    errors.append(f"{location}: IIIF bundle is missing {required_name}")
            if "inventory.json" not in names:
                return
            try:
                inventory = json.loads(archive.read("inventory.json"))
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                errors.append(f"{location}: IIIF bundle inventory is invalid JSON: {exc}")
                return
    except (OSError, zipfile.BadZipFile) as exc:
        errors.append(f"{location}: IIIF bundle is not a readable ZIP: {exc}")
        return

    if not isinstance(inventory, dict):
        errors.append(f"{location}: IIIF bundle inventory root must be an object")
        return
    if inventory.get("source_kind") != source_kind:
        errors.append(f"{location}: IIIF bundle source kind does not match its inventory")
    if inventory.get("source_url") != local_copy.get("source_url"):
        errors.append(f"{location}: IIIF bundle source URL does not match its inventory")
    expected_count = local_copy.get("source_file_count")
    items = inventory.get("items")
    if inventory.get("source_file_count") != expected_count:
        errors.append(f"{location}: IIIF bundle source file count does not match its inventory")
    if not isinstance(items, list) or len(items) != expected_count:
        errors.append(f"{location}: IIIF bundle inventory item count is inconsistent")
        return
    member_paths = [
        item.get("member_path")
        for item in items
        if isinstance(item, dict) and isinstance(item.get("member_path"), str)
    ]
    if len(member_paths) != len(items) or len(set(member_paths)) != len(member_paths):
        errors.append(f"{location}: IIIF bundle inventory member paths are missing or duplicated")
        return
    missing_members = [member_path for member_path in member_paths if member_path not in names]
    if missing_members:
        errors.append(
            f"{location}: IIIF bundle is missing {len(missing_members)} inventoried image member(s)"
        )


def _git_blob_hash(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


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


def _check_entity_ref(ref: Any, entity_ids: set[str], location: str, errors: list[str]) -> None:
    if isinstance(ref, str) and ref not in entity_ids:
        errors.append(f"{location}: unresolved entity reference {ref!r}")


def _check_agent_ref(ref: Any, agent_ids: set[str], location: str, errors: list[str]) -> None:
    if isinstance(ref, str) and ref not in agent_ids:
        errors.append(f"{location}: unresolved agent reference {ref!r}")


def _validate_xml_work_id(
    path: Path,
    work_id: str,
    location: str,
    errors: list[str],
    xml_identifier_aliases: Any = None,
) -> None:
    try:
        tree = ET.parse(path)
    except (ET.ParseError, OSError) as exc:
        errors.append(f"{location}: cannot parse XML for identifier validation: {exc}")
        return

    def values_for(tag: str, attribute: str | None = None) -> list[str]:
        values: list[str] = []
        for node in tree.getroot().findall(f".//{tag}"):
            raw_value = node.get(attribute, "") if attribute else node.text or ""
            value = raw_value.strip()
            if value:
                values.append(value)
        return values

    def matches(value: str, candidate: str) -> bool:
        """Accept exact IDs or case-insensitive, structurally delimited variants."""

        normalized_value = value.casefold()
        normalized_candidate = candidate.casefold()
        return normalized_value == normalized_candidate or any(
            normalized_value.startswith(f"{normalized_candidate}{delimiter}")
            or normalized_candidate.startswith(f"{normalized_value}{delimiter}")
            for delimiter in (".", ":")
        )

    identifiers = (
        ("IDG/@ID", values_for("IDG", "ID")),
        ("BIBNO", values_for("BIBNO")),
        ("VID", values_for("VID")),
        ("IDNO", values_for("IDNO")),
    )
    present_identifiers = [(label, values) for label, values in identifiers if values]
    if any(
        matches(value, work_id)
        for _label, values in present_identifiers
        for value in values
    ):
        return

    aliases = (
        [value for value in xml_identifier_aliases if isinstance(value, str) and value]
        if isinstance(xml_identifier_aliases, list)
        else []
    )
    if any(
        value.casefold() == alias.casefold()
        for _label, values in present_identifiers
        for value in values
        for alias in aliases
    ):
        return

    errors.append(
        f"{location}: XML has no matching IDG/@ID, BIBNO, VID, or IDNO identifier "
        f"for manifest work_id {work_id!r} or its explicit aliases {aliases!r}; "
        f"found {present_identifiers!r}"
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
    if isinstance(work_id, str) and path.stem != work_id:
        errors.append(f"{location}: filename must equal work_id ({work_id}.json)")

    collection_names = (
        "entities",
        "agents",
        "relations",
        "access",
        "rights",
        "editorial_practices",
        "evidence",
        "open_questions",
    )
    records: dict[str, dict[str, Any]] = {}
    record_locations: dict[str, str] = {}
    for collection_name in collection_names:
        collection = manifest.get(collection_name, [])
        if not isinstance(collection, list):
            continue
        for index, record in enumerate(collection):
            if not isinstance(record, dict) or not isinstance(record.get("id"), str):
                continue
            record_id = record["id"]
            item_location = f"{location}.{collection_name}[{index}]"
            if record_id in records:
                errors.append(
                    f"{item_location}: duplicate record id {record_id!r}; first used at "
                    f"{record_locations[record_id]}"
                )
            else:
                records[record_id] = record
                record_locations[record_id] = item_location

    entity_ids = {
        item.get("id") for item in manifest.get("entities", []) if isinstance(item, dict)
    }
    entities_by_id = {
        item["id"]: item
        for item in manifest.get("entities", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    agent_ids = {
        item.get("id") for item in manifest.get("agents", []) if isinstance(item, dict)
    }
    evidence_ids = {
        item.get("id") for item in manifest.get("evidence", []) if isinstance(item, dict)
    }
    access_ids = {
        item.get("id") for item in manifest.get("access", []) if isinstance(item, dict)
    }
    entity_ids.discard(None)
    agent_ids.discard(None)
    evidence_ids.discard(None)
    access_ids.discard(None)

    manuscript_witness_ids = {
        entity_id
        for entity_id, entity in entities_by_id.items()
        if entity.get("type") == "manuscript_witness"
    }
    manuscript_facsimile_ids = {
        relation.get("subject")
        for relation in manifest.get("relations", [])
        if isinstance(relation, dict)
        and relation.get("type") == "facsimile_of"
        and relation.get("object") in manuscript_witness_ids
        and entities_by_id.get(relation.get("subject"), {}).get("type") == "facsimile"
    }
    manuscript_facsimile_ids.discard(None)

    _check_entity_ref(manifest.get("primary_subject"), entity_ids, f"{location}.primary_subject", errors)

    for index, entity in enumerate(manifest.get("entities", [])):
        if not isinstance(entity, dict):
            continue
        item_location = f"{location}.entities[{index}]"
        _check_evidence_refs(entity.get("evidence_ids"), evidence_ids, f"{item_location}.evidence_ids", errors)
        for ref_index, creator_id in enumerate(entity.get("creator_ids", [])):
            _check_agent_ref(creator_id, agent_ids, f"{item_location}.creator_ids[{ref_index}]", errors)
        holding = entity.get("holding")
        if isinstance(holding, dict):
            _check_agent_ref(
                holding.get("institution_id"),
                agent_ids,
                f"{item_location}.holding.institution_id",
                errors,
            )
        for date_index, statement in enumerate(entity.get("date_statements", [])):
            if isinstance(statement, dict):
                _check_evidence_refs(
                    statement.get("evidence_ids"),
                    evidence_ids,
                    f"{item_location}.date_statements[{date_index}].evidence_ids",
                    errors,
                )
        repository_file = entity.get("repository_file")
        if isinstance(repository_file, dict):
            file_path = _safe_repo_file(
                repo_root,
                repository_file.get("path"),
                f"{item_location}.repository_file.path",
                errors,
                allow_missing_source_cache=allow_missing_source_cache,
            )
            if file_path is not None:
                expected_sha = repository_file.get("sha256")
                if isinstance(expected_sha, str) and _sha256(file_path) != expected_sha:
                    errors.append(f"{item_location}.repository_file.sha256: checksum mismatch")
                expected_blob = repository_file.get("git_blob")
                if isinstance(expected_blob, str) and _git_blob_hash(file_path) != expected_blob:
                    errors.append(f"{item_location}.repository_file.git_blob: git blob mismatch")
                if file_path.suffix.lower() == ".xml" and isinstance(work_id, str):
                    _validate_xml_work_id(
                        file_path,
                        work_id,
                        item_location,
                        errors,
                        repository_file.get("xml_identifier_aliases"),
                    )

    for index, agent in enumerate(manifest.get("agents", [])):
        if isinstance(agent, dict) and "evidence_ids" in agent:
            _check_evidence_refs(
                agent.get("evidence_ids"),
                evidence_ids,
                f"{location}.agents[{index}].evidence_ids",
                errors,
            )

    for index, relation in enumerate(manifest.get("relations", [])):
        if not isinstance(relation, dict):
            continue
        item_location = f"{location}.relations[{index}]"
        _check_entity_ref(relation.get("subject"), entity_ids, f"{item_location}.subject", errors)
        _check_entity_ref(relation.get("object"), entity_ids, f"{item_location}.object", errors)
        assertion = relation.get("assertion")
        if isinstance(assertion, dict):
            _check_evidence_refs(
                assertion.get("evidence_ids"),
                evidence_ids,
                f"{item_location}.assertion.evidence_ids",
                errors,
            )

    has_primary_paths = "primary_transmission_paths" in manifest
    has_supporting_groups = "supporting_relationships" in manifest
    if has_primary_paths != has_supporting_groups:
        errors.append(
            f"{location}: primary_transmission_paths and supporting_relationships "
            "must be supplied together"
        )
    elif has_primary_paths:
        relations_by_id = {
            item["id"]: item
            for item in manifest.get("relations", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        classification_ids: dict[str, str] = {}
        classified_relations: dict[str, str] = {}

        def classify_relation_ids(raw_ids: Any, item_location: str) -> None:
            if not isinstance(raw_ids, list):
                return
            for relation_index, relation_id in enumerate(raw_ids):
                ref_location = f"{item_location}.relation_ids[{relation_index}]"
                if not isinstance(relation_id, str):
                    continue
                if relation_id not in relations_by_id:
                    errors.append(
                        f"{ref_location}: unresolved relation reference {relation_id!r}"
                    )
                    continue
                prior_location = classified_relations.get(relation_id)
                if prior_location is not None:
                    errors.append(
                        f"{ref_location}: relation {relation_id!r} is already classified at "
                        f"{prior_location}"
                    )
                    continue
                classified_relations[relation_id] = ref_location

        for index, path_record in enumerate(manifest.get("primary_transmission_paths", [])):
            if not isinstance(path_record, dict):
                continue
            item_location = f"{location}.primary_transmission_paths[{index}]"
            path_id = path_record.get("id")
            if isinstance(path_id, str):
                prior_location = classification_ids.get(path_id)
                if prior_location is not None:
                    errors.append(
                        f"{item_location}.id: duplicate classification id {path_id!r}; "
                        f"first used at {prior_location}"
                    )
                else:
                    classification_ids[path_id] = f"{item_location}.id"

            relation_ids = path_record.get("relation_ids")
            entity_sequence = path_record.get("entity_sequence")
            classify_relation_ids(relation_ids, item_location)
            if not isinstance(relation_ids, list) or not isinstance(entity_sequence, list):
                continue
            if len(entity_sequence) != len(relation_ids) + 1:
                errors.append(
                    f"{item_location}.entity_sequence: expected exactly one more entity "
                    "than relation_ids"
                )
            for entity_index, entity_id in enumerate(entity_sequence):
                _check_entity_ref(
                    entity_id,
                    entity_ids,
                    f"{item_location}.entity_sequence[{entity_index}]",
                    errors,
                )
            for relation_index, relation_id in enumerate(relation_ids):
                if (
                    not isinstance(relation_id, str)
                    or relation_id not in relations_by_id
                    or relation_index + 1 >= len(entity_sequence)
                ):
                    continue
                subject_id = entity_sequence[relation_index]
                object_id = entity_sequence[relation_index + 1]
                relation = relations_by_id[relation_id]
                if relation.get("subject") != subject_id or relation.get("object") != object_id:
                    errors.append(
                        f"{item_location}.relation_ids[{relation_index}]: relation "
                        f"{relation_id!r} endpoints {relation.get('subject')!r} -> "
                        f"{relation.get('object')!r} do not match adjacent entity_sequence "
                        f"endpoints {subject_id!r} -> {object_id!r}"
                    )

        for index, group in enumerate(manifest.get("supporting_relationships", [])):
            if not isinstance(group, dict):
                continue
            item_location = f"{location}.supporting_relationships[{index}]"
            group_id = group.get("id")
            if isinstance(group_id, str):
                prior_location = classification_ids.get(group_id)
                if prior_location is not None:
                    errors.append(
                        f"{item_location}.id: duplicate classification id {group_id!r}; "
                        f"first used at {prior_location}"
                    )
                else:
                    classification_ids[group_id] = f"{item_location}.id"
            classify_relation_ids(group.get("relation_ids"), item_location)

        for relation_id in relations_by_id:
            if relation_id not in classified_relations:
                errors.append(
                    f"{location}.relations: relation {relation_id!r} is not classified by "
                    "primary_transmission_paths or supporting_relationships"
                )

    for index, access in enumerate(manifest.get("access", [])):
        if not isinstance(access, dict):
            continue
        item_location = f"{location}.access[{index}]"
        is_manuscript_facsimile = access.get("entity") in manuscript_facsimile_ids
        _check_entity_ref(access.get("entity"), entity_ids, f"{item_location}.entity", errors)
        if "provider_id" in access:
            _check_agent_ref(access.get("provider_id"), agent_ids, f"{item_location}.provider_id", errors)
        _check_evidence_refs(access.get("evidence_ids"), evidence_ids, f"{item_location}.evidence_ids", errors)
        if "repository_path" in access:
            _safe_repo_file(
                repo_root,
                access.get("repository_path"),
                f"{item_location}.repository_path",
                errors,
                allow_missing_source_cache=allow_missing_source_cache,
            )
        local_copies = access.get("local_copies", [])
        if isinstance(local_copies, list):
            alternate_urls = access.get("alternate_urls", [])
            access_urls = [access.get("url")]
            if isinstance(alternate_urls, list):
                access_urls.extend(alternate_urls)
            seen_cache_paths: set[str] = set()
            for copy_index, local_copy in enumerate(local_copies):
                if not isinstance(local_copy, dict):
                    continue
                copy_location = f"{item_location}.local_copies[{copy_index}]"
                raw_cache_path = local_copy.get("path")
                if isinstance(raw_cache_path, str):
                    if raw_cache_path in seen_cache_paths:
                        errors.append(f"{copy_location}.path: duplicate local copy path")
                    seen_cache_paths.add(raw_cache_path)
                cache_path = _safe_local_copy(
                    repo_root,
                    raw_cache_path,
                    work_id,
                    f"{copy_location}.path",
                    errors,
                )
                source_url = local_copy.get("source_url")
                if source_url not in access_urls:
                    errors.append(
                        f"{copy_location}.source_url: exact source URL must also "
                        "appear as access.url or in alternate_urls"
                    )
                if local_copy.get("retrieval_method") == "iiif_bundle":
                    if not isinstance(raw_cache_path, str) or not raw_cache_path.endswith(".zip"):
                        errors.append(f"{copy_location}.path: IIIF bundle must be a .zip file")
                    if local_copy.get("media_type") != "application/zip":
                        errors.append(
                            f"{copy_location}.media_type: IIIF bundle must use application/zip"
                        )
                if (
                    is_manuscript_facsimile
                    and local_copy.get("coverage") == "complete"
                    and local_copy.get("target_work_presence") != "absent"
                    and not isinstance(local_copy.get("work_portion"), dict)
                ):
                    errors.append(
                        f"{copy_location}.work_portion: complete manuscript facsimile "
                        "requires the corpus work's physical or digital locators"
                    )
                if cache_path is not None:
                    expected_bytes = local_copy.get("bytes")
                    if isinstance(expected_bytes, int) and cache_path.stat().st_size != expected_bytes:
                        errors.append(f"{copy_location}.bytes: byte count mismatch")
                    expected_sha = local_copy.get("sha256")
                    if isinstance(expected_sha, str) and _sha256(cache_path) != expected_sha:
                        errors.append(f"{copy_location}.sha256: checksum mismatch")
                    if local_copy.get("retrieval_method") == "iiif_bundle":
                        _check_iiif_bundle(cache_path, local_copy, copy_location, errors)
        if access.get("status") == "no_public_copy_found" and not access.get("last_checked"):
            errors.append(f"{item_location}: negative access claim requires last_checked")

    for index, rights in enumerate(manifest.get("rights", [])):
        if not isinstance(rights, dict):
            continue
        item_location = f"{location}.rights[{index}]"
        _check_entity_ref(rights.get("entity"), entity_ids, f"{item_location}.entity", errors)
        access_id = rights.get("access_id")
        if isinstance(access_id, str) and access_id not in access_ids:
            errors.append(f"{item_location}.access_id: unresolved access reference {access_id!r}")
        if "asserted_by_id" in rights:
            _check_agent_ref(
                rights.get("asserted_by_id"), agent_ids, f"{item_location}.asserted_by_id", errors
            )
        _check_evidence_refs(rights.get("evidence_ids"), evidence_ids, f"{item_location}.evidence_ids", errors)

    for index, practice in enumerate(manifest.get("editorial_practices", [])):
        if not isinstance(practice, dict):
            continue
        item_location = f"{location}.editorial_practices[{index}]"
        _check_entity_ref(practice.get("entity"), entity_ids, f"{item_location}.entity", errors)
        _check_evidence_refs(practice.get("evidence_ids"), evidence_ids, f"{item_location}.evidence_ids", errors)

    for index, question in enumerate(manifest.get("open_questions", [])):
        if isinstance(question, dict):
            _check_evidence_refs(
                question.get("evidence_ids"),
                evidence_ids,
                f"{location}.open_questions[{index}].evidence_ids",
                errors,
            )

    all_ids = set(records)
    manifest_id = manifest.get("id")
    if isinstance(manifest_id, str):
        all_ids.add(manifest_id)
    for index, evidence in enumerate(manifest.get("evidence", [])):
        if not isinstance(evidence, dict):
            continue
        item_location = f"{location}.evidence[{index}]"
        if "repository_path" in evidence:
            file_path = _safe_repo_file(
                repo_root,
                evidence.get("repository_path"),
                f"{item_location}.repository_path",
                errors,
                allow_missing_source_cache=allow_missing_source_cache,
            )
            if file_path is not None and isinstance(evidence.get("sha256"), str):
                if _sha256(file_path) != evidence["sha256"]:
                    errors.append(f"{item_location}.sha256: checksum mismatch")
        for support_index, supported_id in enumerate(evidence.get("supports", [])):
            if supported_id not in all_ids:
                errors.append(
                    f"{item_location}.supports[{support_index}]: unresolved record reference "
                    f"{supported_id!r}"
                )

    return errors


def validate_repository(
    repo_root: Path,
    *,
    allow_missing_source_cache: bool = False,
) -> list[str]:
    repo_root = repo_root.resolve()
    errors: list[str] = []
    index_schema = _load_json(repo_root / INDEX_SCHEMA_PATH, errors)
    manifest_schema = _load_json(repo_root / MANIFEST_SCHEMA_PATH, errors)
    index = _load_json(repo_root / INDEX_PATH, errors)
    if not all(isinstance(item, dict) for item in (index_schema, manifest_schema, index)):
        return errors

    errors.extend(_schema_errors(index, index_schema, index_schema, str(INDEX_PATH)))

    discovered_paths = sorted((repo_root / WORKS_DIR).glob("*.json"))
    discovered_relative = {
        str(path.relative_to(repo_root / LINEAGE_DIR)) for path in discovered_paths
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

    seen_index_ids: set[str] = set()
    seen_work_ids: set[str] = set()
    for index_number, item in enumerate(indexed_items):
        if not isinstance(item, dict):
            continue
        item_location = f"{INDEX_PATH}.items[{index_number}]"
        for key, seen in (("id", seen_index_ids), ("work_id", seen_work_ids)):
            value = item.get(key)
            if isinstance(value, str):
                if value in seen:
                    errors.append(f"{item_location}.{key}: duplicate value {value!r}")
                seen.add(value)

        relative_manifest = item.get("manifest")
        if not isinstance(relative_manifest, str):
            continue
        manifest_path = repo_root / LINEAGE_DIR / relative_manifest
        manifest = _load_json(manifest_path, errors)
        if not isinstance(manifest, dict):
            continue
        manifest_location = str(manifest_path.relative_to(repo_root))
        errors.extend(_schema_errors(manifest, manifest_schema, manifest_schema, manifest_location))
        errors.extend(
            _semantic_manifest_errors(
                repo_root,
                manifest_path,
                manifest,
                allow_missing_source_cache=allow_missing_source_cache,
            )
        )

        for key in ("id", "work_id", "title", "record_status", "last_reviewed"):
            if item.get(key) != manifest.get(key):
                errors.append(
                    f"{item_location}.{key}: index value {item.get(key)!r} does not match "
                    f"manifest value {manifest.get(key)!r}"
                )
        if item.get("work_id") and Path(relative_manifest).stem != item["work_id"]:
            errors.append(f"{item_location}.manifest: filename does not match work_id")

        repository_paths = set(item.get("repository_paths", []))
        entity_paths = {
            entity.get("repository_file", {}).get("path")
            for entity in manifest.get("entities", [])
            if isinstance(entity, dict) and isinstance(entity.get("repository_file"), dict)
        }
        entity_paths.discard(None)
        for repository_path in repository_paths:
            _safe_repo_file(
                repo_root,
                repository_path,
                f"{item_location}.repository_paths",
                errors,
                allow_missing_source_cache=allow_missing_source_cache,
            )
            if repository_path not in entity_paths:
                errors.append(
                    f"{item_location}.repository_paths: {repository_path!r} is not represented "
                    "by a manifest entity"
                )

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
            "allow absent repository_path files only when they resolve inside the "
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
        print(f"Lineage validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    index = json.loads((args.root / INDEX_PATH).read_text(encoding="utf-8"))
    count = len(index["items"])
    noun = "manifest" if count == 1 else "manifests"
    print(f"Validated {count} lineage {noun}; index, references, source IDs, and checksums are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
