#!/usr/bin/env python3
"""Validate one work's lineage and metadata manifests without index integration."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate_pair(root: Path, work_id: str) -> list[str]:
    scripts = root / "scripts"
    lineage_support = _load_module(
        "_pair_lineage_validation",
        scripts / "validate-lineage-manifests.py",
    )
    metadata_support = _load_module(
        "_pair_metadata_validation",
        scripts / "validate-work-metadata-manifests.py",
    )

    lineage_path = root / "manifests/lineage/works" / f"{work_id}.json"
    metadata_path = root / "manifests/work-metadata/works" / f"{work_id}.json"
    lineage_schema = _load_json(
        root / "manifests/lineage/schemas/lineage-manifest.schema.json"
    )
    metadata_schema = _load_json(
        root / "manifests/work-metadata/schemas/work-metadata-manifest.schema.json"
    )
    lineage = _load_json(lineage_path)
    metadata = _load_json(metadata_path)

    lineage_location = str(lineage_path.relative_to(root))
    metadata_location = str(metadata_path.relative_to(root))
    errors = lineage_support._schema_errors(
        lineage,
        lineage_schema,
        lineage_schema,
        lineage_location,
    )
    errors.extend(
        lineage_support._semantic_manifest_errors(root, lineage_path, lineage)
    )
    errors.extend(
        metadata_support._SCHEMA_SUPPORT._schema_errors(
            metadata,
            metadata_schema,
            metadata_schema,
            metadata_location,
        )
    )
    errors.extend(
        metadata_support._semantic_manifest_errors(root, metadata_path, metadata)
    )
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_id")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors = validate_pair(args.root.resolve(), args.work_id)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"Pair validation failed with {len(errors)} error(s).")
        return 1
    print(f"Validated lineage and work metadata manifests for {args.work_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
