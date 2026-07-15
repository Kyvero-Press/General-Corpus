#!/usr/bin/env python3
"""Reject duplicate object keys in one or more JSON documents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


class DuplicateKeyError(ValueError):
    """Raised when a JSON object repeats a key."""


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse JSON without silently accepting duplicate object keys."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    failed = False
    for path in args.paths:
        try:
            with path.open(encoding="utf-8") as handle:
                json.load(handle, object_pairs_hook=reject_duplicate_keys)
        except (OSError, json.JSONDecodeError, DuplicateKeyError) as error:
            print(f"ERROR: {path}: {error}", file=sys.stderr)
            failed = True
        else:
            print(f"No duplicate JSON object keys: {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
