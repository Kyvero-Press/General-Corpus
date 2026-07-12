#!/usr/bin/env python3
"""Validate one manifest pair's focused projection into the corpus viewer."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILDER_PATH = Path(__file__).resolve().with_name("build-corpus-viewer-catalog.py")


def _load_builder() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_focused_viewer_builder",
        BUILDER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load viewer catalog builder: {BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_projection(repo_root: Path, work_id: str) -> dict[str, Any]:
    """Build and JSON-serialize one work detail using the production normalizers."""
    builder = _load_builder()
    if builder.SAFE_WORK_ID.fullmatch(work_id) is None:
        raise builder.CatalogError(f"unsafe work ID: {work_id!r}")

    metadata_path = (
        repo_root / "manifests" / "work-metadata" / "works" / f"{work_id}.json"
    )
    lineage_path = repo_root / "manifests" / "lineage" / "works" / f"{work_id}.json"
    metadata = builder.load_json(metadata_path)
    lineage = builder.load_json(lineage_path)
    for kind, manifest in (("metadata", metadata), ("lineage", lineage)):
        if manifest.get("work_id") != work_id:
            raise builder.CatalogError(
                f"{kind} manifest work_id does not match {work_id}: "
                f"{manifest.get('work_id')!r}"
            )

    inventory_path = (
        repo_root / "manifests" / "publication-set" / "viewer-default.json"
    )
    inventory = builder._load_publication_inventory(inventory_path)
    expected_publication = inventory.get(work_id)
    if expected_publication is None:
        raise builder.CatalogError(
            f"publication inventory has no entry for changed work {work_id}"
        )
    pdf_path = repo_root / "dist" / f"{work_id}.pdf"
    publication = builder.inspect_pdf(pdf_path, require_pdfinfo=True)
    builder._validate_publications_against_inventory(
        {work_id: publication},
        {work_id: expected_publication},
    )

    identifier_sources = (
        (
            "metadata manifests",
            (
                path.stem
                for path in (
                    repo_root / "manifests/work-metadata/works"
                ).glob("*.json")
            ),
        ),
        (
            "lineage manifests",
            (
                path.stem
                for path in (repo_root / "manifests/lineage/works").glob("*.json")
            ),
        ),
        ("PDFs", (path.stem for path in (repo_root / "dist").glob("*.pdf"))),
        ("publication inventory", inventory),
    )
    checked_sources: list[tuple[str, list[str]]] = []
    for source_name, identifiers in identifier_sources:
        values = list(identifiers)
        for identifier in values:
            if builder.SAFE_WORK_ID.fullmatch(identifier) is None:
                raise builder.CatalogError(
                    f"unsafe work ID in {source_name}: {identifier!r}"
                )
        checked_sources.append((source_name, values))
    builder._reject_cross_source_case_collisions(*checked_sources)

    card = builder._metadata_card(work_id, metadata, lineage, publication)
    detail = {
        "schemaVersion": "1.0.0",
        "work": card,
        "metadata": builder._normalized_metadata(metadata),
        "lineage": builder._normalized_lineage(lineage, repo_root),
        "metadataManifestPath": (
            "catalog/manifests/work-metadata/"
            f"{builder.quote_path_segment(work_id)}.json"
        ),
        "lineageManifestPath": (
            f"catalog/manifests/lineage/{builder.quote_path_segment(work_id)}.json"
        ),
    }
    json.dumps(detail, ensure_ascii=False, allow_nan=False)
    return detail


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_id")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        validate_projection(root, args.work_id)
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Validated viewer projection for {args.work_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
