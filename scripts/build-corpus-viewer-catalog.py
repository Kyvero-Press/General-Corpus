#!/usr/bin/env python3
"""Build the static data contract and PDF staging area for the corpus viewer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, urlsplit, urlunsplit


METADATA_INDEX = Path("manifests/work-metadata/index.json")
METADATA_ROOT = Path("manifests/work-metadata")
LINEAGE_INDEX = Path("manifests/lineage/index.json")
LINEAGE_ROOT = Path("manifests/lineage")
DEFAULT_PDF_ROOT = Path("dist")
DEFAULT_OUTPUT_ROOT = Path("build/corpus-viewer/public")
# Work identifiers are also used as one filename component. The corpus has a
# canonical ``Vices+V1`` identifier, so ``+`` must remain valid; path
# separators, whitespace, percent escapes, and shell metacharacters remain
# excluded. ``safe_child`` separately enforces containment for manifest paths.
SAFE_WORK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
PDF_HEADER = b"%PDF-"


class CatalogError(RuntimeError):
    """Raised when catalog inputs are unsafe, inconsistent, or invalid."""


def quote_path_segment(value: str) -> str:
    """Quote a validated filename/ID while retaining literal + for static hosts."""
    return quote(value, safe="+")


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise CatalogError(f"cannot load Python module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


def validate_manifests(
    repo_root: Path,
    *,
    allow_missing_source_cache: bool = False,
) -> None:
    scripts = repo_root / "scripts"
    lineage = _load_module(
        scripts / "validate-lineage-manifests.py",
        "_viewer_lineage_validation",
    )
    metadata = _load_module(
        scripts / "validate-work-metadata-manifests.py",
        "_viewer_metadata_validation",
    )
    errors = [
        *lineage.validate_repository(
            repo_root,
            allow_missing_source_cache=allow_missing_source_cache,
        ),
        *metadata.validate_repository(
            repo_root,
            allow_missing_source_cache=allow_missing_source_cache,
        ),
    ]
    if errors:
        rendered = "\n".join(f"- {item}" for item in errors)
        raise CatalogError(f"manifest validation failed:\n{rendered}")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CatalogError(f"required JSON file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogError(f"invalid JSON in {path}:{exc.lineno}:{exc.colno}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise CatalogError(f"expected a JSON object in {path}")
    return data


def safe_child(root: Path, relative: str, *, must_exist: bool = True) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute():
        raise CatalogError(f"path must be relative: {relative!r}")
    resolved_root = root.resolve()
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise CatalogError(f"path escapes its root: {relative!r}") from exc
    if must_exist and not resolved.is_file():
        raise CatalogError(f"file does not exist: {relative!r}")
    return resolved


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_pdfinfo(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def humanize_stem(stem: str) -> str:
    value = re.sub(r"[_-]+", " ", stem)
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])", " ", value)
    return " ".join(value.split()) or stem


def format_bytes(value: int) -> str:
    units = ("bytes", "KiB", "MiB", "GiB")
    amount = float(value)
    for unit in units:
        if unit == "bytes" or amount >= 1024:
            if unit != units[-1] and amount >= 1024:
                amount /= 1024
                continue
        if unit == "bytes":
            return f"{value} bytes"
        precision = 0 if amount >= 100 else 1
        return f"{amount:.{precision}f} {unit}"
    return f"{value} bytes"


def validate_external_pdf_base_url(value: str) -> str:
    if value != value.strip() or any(character.isspace() for character in value):
        raise CatalogError("external PDF base URL must not contain whitespace")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise CatalogError(f"invalid external PDF base URL: {exc}") from exc
    if parsed.scheme != "https":
        raise CatalogError("external PDF base URL must use https")
    if not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise CatalogError(
            "external PDF base URL must have a host and must not contain credentials"
        )
    if parsed.query or parsed.fragment:
        raise CatalogError("external PDF base URL must not contain a query or fragment")
    if re.search(r"%(?![0-9A-Fa-f]{2})", parsed.path):
        raise CatalogError("external PDF base URL contains malformed percent encoding")
    netloc = parsed.hostname
    if ":" in netloc and not netloc.startswith("["):
        netloc = f"[{netloc}]"
    if port is not None:
        netloc = f"{netloc}:{port}"
    return urlunsplit(("https", netloc, parsed.path.rstrip("/"), "", ""))


def inspect_pdf(path: Path, *, require_pdfinfo: bool = False) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            header = stream.read(len(PDF_HEADER))
    except OSError as exc:
        raise CatalogError(f"cannot read PDF {path}: {exc}") from exc
    if header != PDF_HEADER:
        raise CatalogError(f"invalid PDF header: {path}")
    initial_digest = sha256(path) if require_pdfinfo else None

    try:
        process = subprocess.run(
            ["pdfinfo", str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
    except FileNotFoundError:
        process = None
    if process is None and require_pdfinfo:
        raise CatalogError(
            "pdfinfo is required when staging or externally publishing PDFs"
        )
    if process is not None and process.returncode != 0:
        message = process.stderr.strip() or "pdfinfo returned a non-zero status"
        raise CatalogError(f"invalid or unreadable PDF {path}: {message}")

    info = parse_pdfinfo(process.stdout) if process is not None else {}
    pages_text = info.get("Pages", "")
    pages = int(pages_text) if pages_text.isdigit() else None
    page_size = info.get("Page size") or None
    if require_pdfinfo and (pages is None or pages <= 0 or page_size is None):
        raise CatalogError(
            f"pdfinfo did not report a positive page count and page size for {path}"
        )
    title = info.get("Title", "").strip() or humanize_stem(path.stem)
    author = info.get("Author", "").strip() or "Authorship metadata pending"
    size = path.stat().st_size
    digest = sha256(path)
    if initial_digest is not None and initial_digest != digest:
        raise CatalogError(f"PDF changed while it was being inspected: {path}")
    return {
        "status": "available",
        "filename": path.name,
        # A local URL is advertised only when build_catalog actually stages
        # the file. Otherwise the generated catalog would contain a broken
        # download link whenever --copy-pdfs is omitted.
        "path": None,
        "externalUrl": None,
        "bytes": size,
        "sizeLabel": format_bytes(size),
        "pages": pages,
        "pageSize": page_size,
        "embeddedTitle": title,
        "embeddedAuthor": author,
        "sha256": digest,
    }


def unavailable_publication(work_id: str) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "filename": f"{work_id}.pdf",
        "path": None,
        "externalUrl": None,
        "bytes": None,
        "sizeLabel": None,
        "pages": None,
        "pageSize": None,
        "embeddedTitle": None,
        "embeddedAuthor": None,
        "sha256": None,
    }


def externalize_publication(publication: dict[str, Any], base_url: str | None) -> None:
    if not base_url or publication.get("status") != "available":
        return
    filename = publication["filename"]
    publication["externalUrl"] = (
        f"{base_url.rstrip('/')}/{quote_path_segment(filename)}"
    )
    publication["path"] = None


def _whole_english_translation(metadata: dict[str, Any]) -> str | None:
    for title in metadata.get("titles", []):
        if not isinstance(title, dict):
            continue
        if (
            title.get("type") == "translated"
            and title.get("language") == "eng"
            and title.get("scope", {}).get("kind") == "whole"
        ):
            value = title.get("value")
            return value if isinstance(value, str) else None
    return None


def _abstract(metadata: dict[str, Any]) -> str | None:
    for summary in metadata.get("summaries", []):
        if not isinstance(summary, dict):
            continue
        if summary.get("type") == "abstract" and summary.get("scope", {}).get("kind") == "whole":
            value = summary.get("value")
            return value if isinstance(value, str) else None
    return None


def _resolved_places(metadata: dict[str, Any]) -> list[dict[str, str]]:
    places = {
        item.get("id"): item
        for item in metadata.get("places", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    result: list[dict[str, str]] = []
    for statement in metadata.get("place_statements", []):
        if not isinstance(statement, dict):
            continue
        place = places.get(statement.get("place_id"), {})
        label = place.get("label")
        relation = statement.get("type")
        if isinstance(label, str) and isinstance(relation, str):
            result.append({"label": label, "relation": relation})
    return result


def _source_periods(metadata: dict[str, Any]) -> list[str]:
    labels: set[str] = set()
    for statement in metadata.get("date_statements", []):
        if not isinstance(statement, dict) or statement.get("type") != "first_known_attestation":
            continue
        normalized = statement.get("normalized")
        if not isinstance(normalized, dict):
            continue
        start = normalized.get("not_before")
        end = normalized.get("not_after")
        if not isinstance(start, int) and not isinstance(end, int):
            continue
        first = start if isinstance(start, int) else end
        last = end if isinstance(end, int) else start
        assert isinstance(first, int) and isinstance(last, int)
        start_century = (first - 1) // 100 + 1
        end_century = (last - 1) // 100 + 1
        for century in range(start_century, end_century + 1):
            suffix = "th"
            if century % 100 not in {11, 12, 13}:
                suffix = {1: "st", 2: "nd", 3: "rd"}.get(century % 10, "th")
            labels.add(f"{century}{suffix} century")
    return sorted(labels, key=lambda item: int(re.match(r"\d+", item).group(0)))


def _publication_year(metadata: dict[str, Any]) -> int | None:
    for statement in metadata.get("date_statements", []):
        if not isinstance(statement, dict) or statement.get("type") != "first_publication":
            continue
        normalized = statement.get("normalized")
        if not isinstance(normalized, dict):
            continue
        value = normalized.get("not_after", normalized.get("not_before"))
        if isinstance(value, int):
            return value
    return None


def _normalized_languages(metadata: dict[str, Any]) -> list[dict[str, str]]:
    values: dict[str, str] = {}
    for statement in metadata.get("language_statements", []):
        if not isinstance(statement, dict):
            continue
        code = statement.get("code")
        label = statement.get("label")
        if isinstance(code, str) and isinstance(label, str):
            values.setdefault(code, label)
    return [{"code": code, "label": values[code]} for code in sorted(values)]


def _normalized_terms(records: Iterable[Any]) -> list[dict[str, str]]:
    values: dict[str, str] = {}
    for item in records:
        if not isinstance(item, dict):
            continue
        term = item.get("term")
        label = item.get("label")
        if isinstance(term, str) and isinstance(label, str):
            existing = values.get(term)
            if existing is not None and existing != label:
                raise CatalogError(
                    f"conflicting labels for controlled term {term!r}: "
                    f"{existing!r} and {label!r}"
                )
            values[term] = label
    return [{"term": term, "label": label} for term, label in values.items()]


def _empty_card(work_id: str, publication: dict[str, Any]) -> dict[str, Any]:
    title = publication.get("embeddedTitle") or humanize_stem(work_id)
    author = publication.get("embeddedAuthor") or "Authorship metadata pending"
    return {
        "workId": work_id,
        "displayTitle": title,
        "preferredTitle": title,
        "translatedTitle": None,
        "author": author,
        "editor": None,
        "dateDisplay": "Descriptive metadata pending",
        "regionDisplay": "Region metadata pending",
        "form": "unknown",
        "languages": [],
        "genres": [],
        "subjects": [],
        "tags": [],
        "regions": [],
        "sourcePeriods": [],
        "publicationYear": None,
        "summary": "A generated General Corpus publication awaiting a descriptive metadata manifest.",
        "metadataStatus": "pending",
        "metadataRecordStatus": None,
        "lineageStatus": "missing",
        "lastReviewed": None,
        "publication": publication,
        "detailPath": f"catalog/works/{quote_path_segment(work_id)}.json",
    }


def _metadata_card(
    work_id: str,
    metadata: dict[str, Any],
    lineage: dict[str, Any],
    publication: dict[str, Any],
) -> dict[str, Any]:
    summary = metadata["catalog_summary"]
    preferred = summary["title"]
    translated = _whole_english_translation(metadata)
    return {
        "workId": work_id,
        "displayTitle": translated or preferred,
        "preferredTitle": preferred,
        "translatedTitle": translated,
        "author": summary["author"],
        "editor": summary.get("editor"),
        "dateDisplay": summary["date"],
        "regionDisplay": summary["region"],
        "form": summary["form"],
        "languages": _normalized_languages(metadata),
        "genres": _normalized_terms(metadata.get("genre_statements", [])),
        "subjects": _normalized_terms(metadata.get("subject_statements", [])),
        "tags": list(metadata.get("tags", [])),
        "regions": _resolved_places(metadata),
        "sourcePeriods": _source_periods(metadata),
        "publicationYear": _publication_year(metadata),
        "summary": _abstract(metadata) or "Descriptive summary not yet supplied.",
        "metadataStatus": "cataloged",
        "metadataRecordStatus": metadata.get("record_status"),
        "lineageStatus": "available" if lineage else "missing",
        "lastReviewed": metadata.get("last_reviewed"),
        "publication": publication,
        "detailPath": f"catalog/works/{quote_path_segment(work_id)}.json",
    }


def _agent_names(lineage: dict[str, Any]) -> dict[str, str]:
    return {
        item["id"]: item["name"]
        for item in lineage.get("agents", [])
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("name"), str)
    }


def _normalized_local_copy(
    repo_root: Path,
    work_id: str,
    local_copy: Any,
) -> dict[str, Any] | None:
    if not isinstance(local_copy, dict):
        return None
    raw_path = local_copy.get("path")
    if not isinstance(raw_path, str):
        raise CatalogError(f"lineage {work_id} local_copy has no path")
    candidate = Path(raw_path)
    expected_parent = Path("source-cache") / work_id
    if candidate.is_absolute() or candidate.parent != expected_parent:
        raise CatalogError(
            f"lineage {work_id} local_copy must be one file under "
            f"{expected_parent.as_posix()}"
        )
    resolved = safe_child(repo_root, raw_path, must_exist=False)
    available = resolved.is_file()
    if resolved.exists() and not available:
        raise CatalogError(f"lineage {work_id} local_copy is not a file: {raw_path}")
    if available:
        expected_bytes = local_copy.get("bytes")
        if resolved.stat().st_size != expected_bytes:
            raise CatalogError(f"lineage {work_id} local_copy byte count mismatch: {raw_path}")
        expected_sha = local_copy.get("sha256")
        if sha256(resolved) != expected_sha:
            raise CatalogError(f"lineage {work_id} local_copy checksum mismatch: {raw_path}")
    byte_count = local_copy.get("bytes")
    raw_work_portion = local_copy.get("work_portion")
    work_portion = None
    if isinstance(raw_work_portion, dict):
        work_portion = {
            "label": raw_work_portion.get("label"),
            "locators": raw_work_portion.get("locators", []),
            "startUrl": raw_work_portion.get("start_url"),
            "endUrl": raw_work_portion.get("end_url"),
            "notes": raw_work_portion.get("notes", []),
        }
    return {
        "label": local_copy.get("label"),
        "path": raw_path,
        "sourceUrl": local_copy.get("source_url"),
        "sha256": local_copy.get("sha256"),
        "bytes": byte_count,
        "sizeLabel": format_bytes(byte_count) if isinstance(byte_count, int) else None,
        "mediaType": local_copy.get("media_type"),
        "downloadedOn": local_copy.get("downloaded_on"),
        "coverage": local_copy.get("coverage"),
        "retrievalMethod": local_copy.get("retrieval_method", "direct_download"),
        "sourceFileCount": local_copy.get("source_file_count"),
        "bundleSourceKind": local_copy.get("bundle_source_kind"),
        "workPortion": work_portion,
        "notes": local_copy.get("notes", []),
        "available": available,
    }


def _normalized_lineage(
    lineage: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any] | None:
    if not lineage:
        return None
    entities = {
        item["id"]: item
        for item in lineage.get("entities", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    work_id = lineage.get("work_id")
    if not isinstance(work_id, str):
        raise CatalogError("lineage manifest has no work_id")
    agents = _agent_names(lineage)
    access_by_entity: dict[str, list[dict[str, Any]]] = {}
    rights_by_entity: dict[str, list[dict[str, Any]]] = {}
    rights_by_access: dict[str, list[dict[str, Any]]] = {}
    for right in lineage.get("rights", []):
        if not isinstance(right, dict):
            continue
        entity_id = right.get("entity")
        access_id = right.get("access_id")
        if isinstance(entity_id, str):
            rights_by_entity.setdefault(entity_id, []).append(right)
        if isinstance(access_id, str):
            rights_by_access.setdefault(access_id, []).append(right)

    source_links: list[dict[str, Any]] = []
    for access in lineage.get("access", []):
        if not isinstance(access, dict):
            continue
        entity_id = access.get("entity")
        if not isinstance(entity_id, str):
            continue
        entity = entities.get(entity_id, {})
        access_id = access.get("id")
        raw_local_copies = access.get("local_copies", [])
        if not isinstance(raw_local_copies, list):
            raise CatalogError(f"lineage {work_id} access {access_id} has invalid local_copies")
        normalized = {
            "id": access_id,
            "entityId": entity_id,
            "entityLabel": entity.get("label", entity_id),
            "entityType": entity.get("type", "unknown"),
            "provider": agents.get(access.get("provider_id"), access.get("provider_id")),
            "resourceKind": access.get("resource_kind"),
            "status": access.get("status"),
            "accessMethod": access.get("access_method"),
            "url": access.get("url"),
            "alternateUrls": access.get("alternate_urls", []),
            "contact": access.get("contact"),
            "cost": access.get("cost"),
            "format": access.get("format"),
            "lastChecked": access.get("last_checked"),
            "notes": access.get("notes", []),
            "localCopies": [
                normalized_copy
                for item in raw_local_copies
                if (normalized_copy := _normalized_local_copy(repo_root, work_id, item))
                is not None
            ],
            "rights": rights_by_access.get(access_id, []),
        }
        source_links.append(normalized)
        access_by_entity.setdefault(entity_id, []).append(normalized)

    normalized_entities: list[dict[str, Any]] = []
    for entity_id, entity in entities.items():
        normalized_entities.append(
            {
                "id": entity_id,
                "type": entity.get("type"),
                "label": entity.get("label"),
                "description": entity.get("description"),
                "identifiers": entity.get("identifiers", []),
                "bibliographic": entity.get("bibliographic"),
                "holding": entity.get("holding"),
                "physicalDescription": entity.get("physical_description"),
                "dateStatements": entity.get("date_statements", []),
                "survivalStatus": entity.get("survival_status"),
                "notes": entity.get("notes", []),
                "access": access_by_entity.get(entity_id, []),
                "rights": rights_by_entity.get(entity_id, []),
            }
        )

    relations: list[dict[str, Any]] = []
    for relation in lineage.get("relations", []):
        if not isinstance(relation, dict):
            continue
        subject_id = relation.get("subject")
        object_id = relation.get("object")
        relations.append(
            {
                "id": relation.get("id"),
                "type": relation.get("type"),
                "subjectId": subject_id,
                "subjectLabel": entities.get(subject_id, {}).get("label", subject_id),
                "objectId": object_id,
                "objectLabel": entities.get(object_id, {}).get("label", object_id),
                "scope": relation.get("scope"),
                "assertion": relation.get("assertion"),
            }
        )

    relation_classification = None
    raw_primary_paths = lineage.get("primary_transmission_paths")
    raw_supporting_groups = lineage.get("supporting_relationships")
    if isinstance(raw_primary_paths, list) and isinstance(raw_supporting_groups, list):
        relation_classification = {
            "primaryTransmissionPaths": [
                {
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "relationIds": item.get("relation_ids", []),
                    "entitySequence": item.get("entity_sequence", []),
                    "description": item.get("description"),
                }
                for item in raw_primary_paths
                if isinstance(item, dict)
            ],
            "supportingRelationships": [
                {
                    "id": item.get("id"),
                    "label": item.get("label"),
                    "relationIds": item.get("relation_ids", []),
                    "description": item.get("description"),
                }
                for item in raw_supporting_groups
                if isinstance(item, dict)
            ],
        }

    return {
        "manifestId": lineage.get("id"),
        "primarySubjectId": lineage.get("primary_subject"),
        "recordStatus": lineage.get("record_status"),
        "lastReviewed": lineage.get("last_reviewed"),
        "summary": lineage.get("summary"),
        "entities": normalized_entities,
        "relations": relations,
        "relationClassification": relation_classification,
        "sourceLinks": source_links,
        "openQuestions": lineage.get("open_questions", []),
        "reviewNotes": lineage.get("review_notes", []),
    }


def _normalized_metadata(metadata: dict[str, Any]) -> dict[str, Any] | None:
    if not metadata:
        return None
    agents = {
        item["id"]: item["name"]
        for item in metadata.get("agents", [])
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("name"), str)
    }
    places = {
        item["id"]: item["label"]
        for item in metadata.get("places", [])
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and isinstance(item.get("label"), str)
    }
    responsibilities: list[dict[str, Any]] = []
    for item in metadata.get("responsibilities", []):
        if not isinstance(item, dict):
            continue
        copy = dict(item)
        copy["agentName"] = agents.get(item.get("agent_id"), item.get("display_name"))
        responsibilities.append(copy)
    place_statements: list[dict[str, Any]] = []
    for item in metadata.get("place_statements", []):
        if not isinstance(item, dict):
            continue
        copy = dict(item)
        copy["placeLabel"] = places.get(item.get("place_id"), item.get("place_id"))
        place_statements.append(copy)
    return {
        "manifestId": metadata.get("id"),
        "recordStatus": metadata.get("record_status"),
        "lastReviewed": metadata.get("last_reviewed"),
        "catalogingSubject": metadata.get("cataloging_subject"),
        "catalogSummary": metadata.get("catalog_summary"),
        "titles": metadata.get("titles", []),
        "responsibilities": responsibilities,
        "dateStatements": metadata.get("date_statements", []),
        "placeStatements": place_statements,
        "languageStatements": metadata.get("language_statements", []),
        "formStatements": metadata.get("form_statements", []),
        "genres": metadata.get("genre_statements", []),
        "subjects": metadata.get("subject_statements", []),
        "tags": metadata.get("tags", []),
        "summaries": metadata.get("summaries", []),
        "extent": metadata.get("extent"),
        "contentStructureStatus": metadata.get("content_structure_status"),
        "contentParts": metadata.get("content_parts", []),
        "openQuestions": metadata.get("open_questions", []),
        "notes": metadata.get("notes", []),
    }


def _facet_counts(cards: list[dict[str, Any]]) -> dict[str, Any]:
    def count_values(values: Iterable[str]) -> list[dict[str, Any]]:
        counter = Counter(values)
        return [
            {"value": value, "count": counter[value]}
            for value in sorted(counter, key=str.casefold)
        ]

    language_labels: dict[str, str] = {}
    genre_labels: dict[str, str] = {}
    subject_labels: dict[str, str] = {}
    for card in cards:
        for language in card["languages"]:
            code = language["code"]
            label = language["label"]
            if code in language_labels and language_labels[code] != label:
                raise CatalogError(f"conflicting language labels for {code!r}")
            language_labels[code] = label
        for genre in card["genres"]:
            term = genre["term"]
            label = genre["label"]
            if term in genre_labels and genre_labels[term] != label:
                raise CatalogError(f"conflicting genre labels for {term!r}")
            genre_labels[term] = label
        for subject in card["subjects"]:
            term = subject["term"]
            label = subject["label"]
            if term in subject_labels and subject_labels[term] != label:
                raise CatalogError(f"conflicting subject labels for {term!r}")
            subject_labels[term] = label

    def labeled_counts(values: Iterable[str], labels: dict[str, str]) -> list[dict[str, Any]]:
        counter = Counter(values)
        return [
            {"value": value, "label": labels.get(value, value), "count": counter[value]}
            for value in sorted(counter, key=lambda item: labels.get(item, item).casefold())
        ]

    return {
        "metadataStatuses": count_values(card["metadataStatus"] for card in cards),
        "pdfStatuses": count_values(card["publication"]["status"] for card in cards),
        "recordStatuses": count_values(
            card["metadataRecordStatus"]
            for card in cards
            if isinstance(card.get("metadataRecordStatus"), str)
        ),
        "forms": count_values(card["form"] for card in cards if card["form"] != "unknown"),
        "languages": labeled_counts(
            (
                code
                for card in cards
                for code in {language["code"] for language in card["languages"]}
            ),
            language_labels,
        ),
        "genres": labeled_counts(
            (
                term
                for card in cards
                for term in {genre["term"] for genre in card["genres"]}
            ),
            genre_labels,
        ),
        "subjects": labeled_counts(
            (
                term
                for card in cards
                for term in {subject["term"] for subject in card["subjects"]}
            ),
            subject_labels,
        ),
        "tags": count_values(tag for card in cards for tag in set(card["tags"])),
        "regions": count_values(
            label
            for card in cards
            for label in {region["label"] for region in card["regions"]}
        ),
        "sourcePeriods": count_values(
            period for card in cards for period in set(card["sourcePeriods"])
        ),
    }


def _deterministic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _replace_generated_trees(stage_root: Path, output_root: Path) -> None:
    """Replace the catalog/PDF subtrees together, rolling back ordinary failures."""
    names = ("publication-pdfs", "catalog")
    backup_root = stage_root / ".previous"
    backup_root.mkdir()
    installed: list[str] = []
    backed_up: list[str] = []
    try:
        for name in names:
            target = output_root / name
            staged = stage_root / name
            backup = backup_root / name
            if target.exists():
                os.replace(target, backup)
                backed_up.append(name)
            if staged.exists():
                os.replace(staged, target)
                installed.append(name)
    except OSError as exc:
        for name in reversed(installed):
            target = output_root / name
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        for name in reversed(backed_up):
            backup = backup_root / name
            if backup.exists():
                os.replace(backup, output_root / name)
        raise CatalogError(f"could not install generated viewer data: {exc}") from exc
    shutil.rmtree(backup_root)


def _load_lineage_records(repo_root: Path) -> dict[str, tuple[dict[str, Any], Path]]:
    index = load_json(repo_root / LINEAGE_INDEX)
    result: dict[str, tuple[dict[str, Any], Path]] = {}
    for entry in index.get("items", []):
        if not isinstance(entry, dict):
            continue
        work_id = entry.get("work_id")
        relative = entry.get("manifest")
        if not isinstance(work_id, str) or not SAFE_WORK_ID.fullmatch(work_id):
            raise CatalogError(f"unsafe or invalid lineage work_id: {work_id!r}")
        if work_id in result:
            raise CatalogError(f"duplicate lineage work_id: {work_id}")
        if not isinstance(relative, str):
            raise CatalogError(f"lineage index entry {work_id} has no manifest path")
        lineage_path = safe_child(repo_root / LINEAGE_ROOT, relative)
        lineage = load_json(lineage_path)
        if lineage.get("work_id") != work_id:
            raise CatalogError(f"lineage work_id mismatch for {work_id}")
        result[work_id] = (lineage, lineage_path)
    return result


def _load_metadata_records(
    repo_root: Path,
    lineage_records: dict[str, tuple[dict[str, Any], Path]],
) -> dict[str, tuple[dict[str, Any], dict[str, Any], Path, Path]]:
    index = load_json(repo_root / METADATA_INDEX)
    result: dict[str, tuple[dict[str, Any], dict[str, Any], Path, Path]] = {}
    for entry in index.get("items", []):
        if not isinstance(entry, dict):
            continue
        work_id = entry.get("work_id")
        relative = entry.get("manifest")
        if not isinstance(work_id, str) or not SAFE_WORK_ID.fullmatch(work_id):
            raise CatalogError(f"unsafe or invalid metadata work_id: {work_id!r}")
        if work_id in result:
            raise CatalogError(f"duplicate metadata work_id: {work_id}")
        if not isinstance(relative, str):
            raise CatalogError(f"metadata index entry {work_id} has no manifest path")
        metadata_path = safe_child(repo_root / METADATA_ROOT, relative)
        metadata = load_json(metadata_path)
        lineage_rel = metadata.get("lineage", {}).get("manifest_path")
        if not isinstance(lineage_rel, str):
            raise CatalogError(f"metadata manifest {work_id} has no lineage path")
        lineage_path = safe_child(repo_root, lineage_rel)
        lineage = load_json(lineage_path)
        if metadata.get("work_id") != work_id or lineage.get("work_id") != work_id:
            raise CatalogError(f"metadata/lineage work_id mismatch for {work_id}")
        indexed_lineage = lineage_records.get(work_id)
        if indexed_lineage is None:
            raise CatalogError(
                f"metadata manifest {work_id} links lineage absent from the lineage index"
            )
        if indexed_lineage[1].resolve() != lineage_path.resolve():
            raise CatalogError(
                f"metadata manifest {work_id} and lineage index resolve different lineage files"
            )
        result[work_id] = (metadata, lineage, metadata_path, lineage_path)
    return result


def _load_publications(
    pdf_root: Path,
    external_base_url: str | None,
    *,
    require_pdfinfo: bool = False,
) -> tuple[dict[str, dict[str, Any]], dict[str, Path]]:
    publications: dict[str, dict[str, Any]] = {}
    paths: dict[str, Path] = {}
    casefolded_ids: dict[str, str] = {}
    if not pdf_root.exists():
        return publications, paths
    if not pdf_root.is_dir():
        raise CatalogError(f"PDF root is not a directory: {pdf_root}")
    resolved_root = pdf_root.resolve()
    for path in sorted(pdf_root.glob("*.pdf"), key=lambda item: item.name.casefold()):
        resolved = path.resolve()
        try:
            resolved.relative_to(resolved_root)
        except ValueError as exc:
            raise CatalogError(f"PDF path escapes its root: {path}") from exc
        work_id = path.stem
        if not SAFE_WORK_ID.fullmatch(work_id):
            raise CatalogError(f"unsafe PDF work_id/stem: {work_id!r}")
        if work_id in publications:
            raise CatalogError(f"duplicate PDF work_id: {work_id}")
        folded = work_id.casefold()
        existing = casefolded_ids.get(folded)
        if existing is not None and existing != work_id:
            raise CatalogError(
                f"case-insensitive PDF work_id collision: {existing!r} and {work_id!r}"
            )
        casefolded_ids[folded] = work_id
        publication = inspect_pdf(resolved, require_pdfinfo=require_pdfinfo)
        externalize_publication(publication, external_base_url)
        publications[work_id] = publication
        paths[work_id] = resolved
    return publications, paths


def _reject_cross_source_case_collisions(
    *sources: tuple[str, Iterable[str]],
) -> None:
    seen: dict[str, tuple[str, str]] = {}
    for source_name, work_ids in sources:
        for work_id in work_ids:
            folded = work_id.casefold()
            previous = seen.get(folded)
            if previous is not None and previous[0] != work_id:
                raise CatalogError(
                    "case-insensitive work_id collision across catalog sources: "
                    f"{previous[0]!r} ({previous[1]}) and {work_id!r} ({source_name})"
                )
            seen[folded] = (work_id, source_name)


def _load_publication_inventory(path: Path) -> dict[str, dict[str, Any]]:
    inventory = load_json(path)
    if inventory.get("$schema") != "schemas/publication-set.schema.json":
        raise CatalogError(f"unexpected publication inventory schema path in {path}")
    if inventory.get("schema_version") != "1.0.0":
        raise CatalogError(
            f"unsupported publication inventory schema version in {path}"
        )
    items = inventory.get("items")
    if not isinstance(items, list):
        raise CatalogError(f"publication inventory has no items array: {path}")
    if inventory.get("item_count") != len(items):
        raise CatalogError(
            f"publication inventory item_count does not equal {len(items)} in {path}"
        )
    result: dict[str, dict[str, Any]] = {}
    casefolded: dict[str, str] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise CatalogError(f"publication inventory item {index} is not an object")
        work_id = item.get("work_id")
        filename = item.get("filename")
        digest = item.get("sha256")
        byte_count = item.get("bytes")
        pages = item.get("pages")
        if not isinstance(work_id, str) or not SAFE_WORK_ID.fullmatch(work_id):
            raise CatalogError(
                f"publication inventory item {index} has unsafe work_id {work_id!r}"
            )
        if filename != f"{work_id}.pdf":
            raise CatalogError(
                f"publication inventory item {work_id} filename must be {work_id}.pdf"
            )
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise CatalogError(
                f"publication inventory item {work_id} has invalid sha256"
            )
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
            raise CatalogError(
                f"publication inventory item {work_id} has invalid byte count"
            )
        if not isinstance(pages, int) or isinstance(pages, bool) or pages <= 0:
            raise CatalogError(
                f"publication inventory item {work_id} has invalid page count"
            )
        if work_id in result:
            raise CatalogError(f"duplicate publication inventory work_id: {work_id}")
        folded = work_id.casefold()
        existing = casefolded.get(folded)
        if existing is not None and existing != work_id:
            raise CatalogError(
                f"case-insensitive publication inventory collision: {existing!r} and {work_id!r}"
            )
        casefolded[folded] = work_id
        result[work_id] = item
    return result


def _validate_publications_against_inventory(
    publications: dict[str, dict[str, Any]],
    inventory: dict[str, dict[str, Any]],
) -> None:
    missing = sorted(set(inventory) - set(publications), key=str.casefold)
    extra = sorted(set(publications) - set(inventory), key=str.casefold)
    errors: list[str] = []
    if missing:
        errors.append(f"missing expected PDFs: {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected PDFs: {', '.join(extra)}")
    for work_id in sorted(set(inventory) & set(publications), key=str.casefold):
        expected = inventory[work_id]
        actual = publications[work_id]
        for key in ("filename", "sha256", "bytes", "pages"):
            if actual.get(key) != expected.get(key):
                errors.append(
                    f"{work_id} {key} differs: expected {expected.get(key)!r}, "
                    f"found {actual.get(key)!r}"
                )
    if errors:
        raise CatalogError(
            "publication set does not match its approved inventory:\n- "
            + "\n- ".join(errors)
        )


def build_catalog(
    repo_root: Path,
    *,
    pdf_root: Path,
    output_root: Path,
    include_pdf_only: bool = True,
    copy_pdfs: bool = False,
    require_pdfs: bool = False,
    external_pdf_base_url: str | None = None,
    publication_inventory: Path | None = None,
    validate: bool = True,
    allow_missing_source_cache: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    if validate:
        validate_manifests(
            repo_root,
            allow_missing_source_cache=allow_missing_source_cache,
        )
    if external_pdf_base_url is not None:
        external_pdf_base_url = validate_external_pdf_base_url(external_pdf_base_url)
    lineage_records = _load_lineage_records(repo_root)
    metadata_records = _load_metadata_records(repo_root, lineage_records)
    publications, publication_paths = _load_publications(
        pdf_root,
        external_pdf_base_url,
        require_pdfinfo=(
            copy_pdfs
            or require_pdfs
            or external_pdf_base_url is not None
            or publication_inventory is not None
        ),
    )
    _reject_cross_source_case_collisions(
        ("metadata", metadata_records),
        ("lineage", lineage_records),
        ("PDFs", publications),
    )
    inventory_source_path: Path | None = None
    inventory_summary: dict[str, Any] | None = None
    if publication_inventory is not None:
        inventory_path = publication_inventory
        if not inventory_path.is_absolute():
            inventory_path = repo_root / inventory_path
        try:
            inventory_path.resolve().relative_to(repo_root)
        except ValueError as exc:
            raise CatalogError(
                "publication inventory must be inside the repository"
            ) from exc
        inventory = _load_publication_inventory(inventory_path)
        _validate_publications_against_inventory(publications, inventory)
        inventory_source_path = inventory_path
        inventory_data = load_json(inventory_path)
        inventory_summary = {
            "snapshotDate": inventory_data.get("snapshot_date"),
            "itemCount": len(inventory),
            "manifestPath": "catalog/manifests/publication-set/viewer-default.json",
        }
    if copy_pdfs and external_pdf_base_url is None:
        for publication in publications.values():
            publication["path"] = (
                f"publication-pdfs/{quote_path_segment(publication['filename'])}"
            )
    described_work_ids = set(metadata_records) | set(lineage_records)
    missing = sorted(described_work_ids - set(publications))
    if require_pdfs and missing:
        raise CatalogError(f"cataloged works missing canonical PDFs: {', '.join(missing)}")

    work_ids = set(described_work_ids)
    if include_pdf_only:
        work_ids.update(publications)
    cards: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}
    for work_id in sorted(work_ids, key=str.casefold):
        publication = publications.get(work_id, unavailable_publication(work_id))
        record = metadata_records.get(work_id)
        if record is None:
            card = _empty_card(work_id, publication)
            lineage_record = lineage_records.get(work_id)
            lineage = lineage_record[0] if lineage_record is not None else None
            if lineage is not None:
                card["lineageStatus"] = "available"
            detail = {
                "schemaVersion": "1.0.0",
                "work": card,
                "metadata": None,
                "lineage": (
                    _normalized_lineage(lineage, repo_root)
                    if lineage is not None
                    else None
                ),
                "metadataManifestPath": None,
                "lineageManifestPath": (
                    f"catalog/manifests/lineage/{quote_path_segment(work_id)}.json"
                    if lineage is not None
                    else None
                ),
            }
        else:
            metadata, lineage, _, _ = record
            card = _metadata_card(work_id, metadata, lineage, publication)
            detail = {
                "schemaVersion": "1.0.0",
                "work": card,
                "metadata": _normalized_metadata(metadata),
                "lineage": _normalized_lineage(lineage, repo_root),
                "metadataManifestPath": (
                    "catalog/manifests/work-metadata/"
                    f"{quote_path_segment(work_id)}.json"
                ),
                "lineageManifestPath": (
                    f"catalog/manifests/lineage/{quote_path_segment(work_id)}.json"
                ),
            }
        cards.append(card)
        details[work_id] = detail

    cards.sort(
        key=lambda item: (
            item["metadataStatus"] != "cataloged",
            item["lineageStatus"] != "available",
            item["displayTitle"].casefold(),
            item["workId"].casefold(),
        )
    )
    metadata_reviewed_dates = [
        entry[0].get("last_reviewed")
        for entry in metadata_records.values()
        if isinstance(entry[0].get("last_reviewed"), str)
    ]
    lineage_reviewed_dates = [
        entry[0].get("last_reviewed")
        for entry in lineage_records.values()
        if isinstance(entry[0].get("last_reviewed"), str)
    ]
    all_reviewed_dates = metadata_reviewed_dates + lineage_reviewed_dates
    catalog = {
        "schemaVersion": "1.0.0",
        "catalogReviewedThrough": max(all_reviewed_dates) if all_reviewed_dates else None,
        "metadataReviewedThrough": (
            max(metadata_reviewed_dates) if metadata_reviewed_dates else None
        ),
        "lineageReviewedThrough": (
            max(lineage_reviewed_dates) if lineage_reviewed_dates else None
        ),
        "coverageNote": load_json(repo_root / METADATA_INDEX).get("coverage", {}).get("notes"),
        "lineageCoverageNote": load_json(repo_root / LINEAGE_INDEX)
        .get("coverage", {})
        .get("notes"),
        "publicationInventory": inventory_summary,
        "counts": {
            "works": len(cards),
            "catalogedMetadata": sum(card["metadataStatus"] == "cataloged" for card in cards),
            "lineageRecords": sum(card["lineageStatus"] == "available" for card in cards),
            "metadataPending": sum(card["metadataStatus"] == "pending" for card in cards),
            "pdfsAvailable": sum(card["publication"]["status"] == "available" for card in cards),
            "pdfsUnavailable": sum(card["publication"]["status"] == "unavailable" for card in cards),
            "publicationBytes": sum(
                card["publication"]["bytes"] or 0 for card in cards
            ),
        },
        "facets": _facet_counts(cards),
        "works": cards,
    }

    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="corpus-viewer-catalog-", dir=output_root.parent
    ) as temp:
        temp_root = Path(temp)
        catalog_root = temp_root / "catalog"
        _deterministic_json(catalog_root / "index.json", catalog)
        for work_id, detail in details.items():
            _deterministic_json(catalog_root / "works" / f"{work_id}.json", detail)
        for work_id, (_, _, metadata_path, _) in metadata_records.items():
            destination = catalog_root / "manifests"
            (destination / "work-metadata").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(metadata_path, destination / "work-metadata" / f"{work_id}.json")
        for work_id, (_, lineage_path) in lineage_records.items():
            destination = catalog_root / "manifests"
            (destination / "lineage").mkdir(parents=True, exist_ok=True)
            shutil.copyfile(lineage_path, destination / "lineage" / f"{work_id}.json")
        if inventory_source_path is not None:
            destination = catalog_root / "manifests" / "publication-set"
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(inventory_source_path, destination / "viewer-default.json")
        if copy_pdfs and external_pdf_base_url is None:
            pdf_destination = temp_root / "publication-pdfs"
            pdf_destination.mkdir()
            for work_id in sorted(work_ids, key=str.casefold):
                source = publication_paths.get(work_id)
                if source is None:
                    continue
                destination = pdf_destination / source.name
                try:
                    shutil.copyfile(source, destination)
                except OSError as exc:
                    raise CatalogError(f"could not stage publication PDF {source}: {exc}") from exc
                expected = publications[work_id]["sha256"]
                actual = sha256(destination)
                if actual != expected:
                    raise CatalogError(
                        f"publication PDF changed while it was being staged: {source}"
                    )
        _replace_generated_trees(temp_root, output_root)

    return catalog


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root",
    )
    parser.add_argument(
        "--pdf-root",
        type=Path,
        default=DEFAULT_PDF_ROOT,
        help="canonical publication PDF directory, relative to the repository root by default",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="generated static-site root, relative to the repository root by default",
    )
    parser.add_argument(
        "--include-pdf-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="include canonical PDFs absent from both manifest indexes",
    )
    parser.add_argument(
        "--copy-pdfs",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="copy canonical PDFs into OUTPUT_ROOT/publication-pdfs",
    )
    parser.add_argument(
        "--require-pdfs",
        action="store_true",
        help="fail if a work indexed by either manifest system lacks a readable canonical PDF",
    )
    parser.add_argument(
        "--external-pdf-base-url",
        help="link available PDFs to this URL prefix instead of a staged local path",
    )
    parser.add_argument(
        "--publication-inventory",
        type=Path,
        help=(
            "require exact filename, hash, byte, and page-count equality with "
            "this tracked publication-set snapshot"
        ),
    )
    parser.add_argument(
        "--skip-manifest-validation",
        action="store_true",
        help="skip manifest validators (intended only for focused unit tests)",
    )
    parser.add_argument(
        "--allow-missing-source-cache",
        action="store_true",
        help=(
            "retain manifest validation but allow absent repository_path files "
            "inside the gitignored source-cache directory"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.root.resolve()
    pdf_root = args.pdf_root if args.pdf_root.is_absolute() else repo_root / args.pdf_root
    output_root = args.output_root if args.output_root.is_absolute() else repo_root / args.output_root
    try:
        relative_output = output_root.resolve().relative_to((repo_root / "build").resolve())
    except ValueError:
        print("ERROR: output root must be inside the repository build/ directory", file=sys.stderr)
        return 2
    if not relative_output.parts:
        print("ERROR: output root must be a child of build/, not build/ itself", file=sys.stderr)
        return 2
    try:
        catalog = build_catalog(
            repo_root,
            pdf_root=pdf_root,
            output_root=output_root,
            include_pdf_only=args.include_pdf_only,
            copy_pdfs=args.copy_pdfs,
            require_pdfs=args.require_pdfs,
            external_pdf_base_url=args.external_pdf_base_url,
            publication_inventory=args.publication_inventory,
            validate=not args.skip_manifest_validation,
            allow_missing_source_cache=args.allow_missing_source_cache,
        )
    except CatalogError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    counts = catalog["counts"]
    print(
        f"Built viewer catalog with {counts['works']} works, "
        f"{counts['catalogedMetadata']} cataloged metadata records, and "
        f"{counts['pdfsAvailable']} available PDFs at {output_root}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
