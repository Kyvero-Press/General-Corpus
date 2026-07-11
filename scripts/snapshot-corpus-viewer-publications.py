#!/usr/bin/env python3
"""Snapshot the canonical PDF set used by the default corpus viewer release."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = REPO_ROOT / "scripts" / "build-corpus-viewer-catalog.py"


def _load_generator() -> Any:
    spec = importlib.util.spec_from_file_location(
        "snapshot_corpus_viewer_generator", GENERATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load catalog generator from {GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def snapshot(pdf_root: Path, output: Path, snapshot_date: str) -> int:
    try:
        date.fromisoformat(snapshot_date)
    except ValueError as exc:
        raise RuntimeError(
            f"snapshot date must be ISO YYYY-MM-DD: {snapshot_date!r}"
        ) from exc
    generator = _load_generator()
    publications, _ = generator._load_publications(
        pdf_root.resolve(), None, require_pdfinfo=True
    )
    if not publications:
        raise RuntimeError(f"no canonical PDFs found under {pdf_root.resolve()}")
    items = [
        {
            "work_id": work_id,
            "filename": publication["filename"],
            "sha256": publication["sha256"],
            "bytes": publication["bytes"],
            "pages": publication["pages"],
        }
        for work_id, publication in sorted(
            publications.items(), key=lambda item: item[0].casefold()
        )
    ]
    payload = {
        "$schema": "schemas/publication-set.schema.json",
        "schema_version": "1.0.0",
        "snapshot_date": snapshot_date,
        "description": (
            "Approved canonical PDF snapshot for the default corpus viewer "
            "deployment. Replace only after a fail-closed publication refresh."
        ),
        "item_count": len(items),
        "items": items,
    }

    allowed_root = (REPO_ROOT / "manifests" / "publication-set").resolve()
    resolved_output = output.resolve()
    try:
        resolved_output.relative_to(allowed_root)
    except ValueError as exc:
        raise RuntimeError(
            f"inventory output must be inside {allowed_root}"
        ) from exc
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=resolved_output.parent,
        prefix=f".{resolved_output.name}.",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    os.replace(temporary, resolved_output)
    return len(items)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-root", type=Path, default=REPO_ROOT / "dist")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "manifests" / "publication-set" / "viewer-default.json",
    )
    parser.add_argument("--snapshot-date", default=date.today().isoformat())
    args = parser.parse_args(argv)
    try:
        count = snapshot(args.pdf_root, args.output, args.snapshot_date)
    except (RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {count} publication records to {args.output.resolve()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
