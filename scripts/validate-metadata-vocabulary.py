#!/usr/bin/env python3
"""Check corpus-wide labels for normalized metadata vocabulary terms."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKS_DIR = Path("manifests/work-metadata/works")
VOCABULARIES = (
    ("language_statements", "code"),
    ("genre_statements", "term"),
    ("subject_statements", "term"),
)


def _load_manifest(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path}: cannot load JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path}: expected a JSON object")
        return None
    return value


def validate_vocabulary(repo_root: Path) -> list[str]:
    errors: list[str] = []
    labels: dict[tuple[str, str], dict[str, dict[str, set[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set))
    )
    for path in sorted((repo_root / WORKS_DIR).glob("*.json")):
        manifest = _load_manifest(path, errors)
        if manifest is None:
            continue
        for collection_name, key_name in VOCABULARIES:
            collection = manifest.get(collection_name, [])
            if not isinstance(collection, list):
                continue
            for record in collection:
                if not isinstance(record, dict):
                    continue
                key = record.get(key_name)
                label = record.get("label")
                if isinstance(key, str) and isinstance(label, str):
                    labels[(collection_name, key_name)][key][label].add(path.name)

    for (collection_name, key_name), terms in sorted(labels.items()):
        for term, term_labels in sorted(terms.items()):
            if len(term_labels) < 2:
                continue
            rendered = "; ".join(
                f"{label!r} in {', '.join(sorted(paths))}"
                for label, paths in sorted(term_labels.items())
            )
            errors.append(
                f"{collection_name}.{key_name} {term!r} has conflicting labels: {rendered}"
            )
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors = validate_vocabulary(args.root.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(
            f"Metadata vocabulary validation failed with {len(errors)} error(s).",
            file=sys.stderr,
        )
        return 1
    count = len(list((args.root.resolve() / WORKS_DIR).glob("*.json")))
    print(f"Validated normalized metadata labels across {count} manifests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
