#!/usr/bin/env python3
"""Emit a compact, factual inspection packet for one corpus XML source."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TEXT_TAGS = {
    "TITLE",
    "AUTHOR",
    "EDITOR",
    "EDITION",
    "PUBPLACE",
    "PUBLISHER",
    "DATE",
    "SOURCEDESC",
    "AVAILABILITY",
    "EDITORIALDECL",
    "LANGUAGE",
    "CLASSCODE",
}
COUNT_TAGS = {
    "DIV1",
    "DIV2",
    "DIV3",
    "HEAD",
    "P",
    "LG",
    "L",
    "PB",
    "MILESTONE",
    "NOTE",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].upper()


def _compact_text(node: ET.Element, limit: int = 700) -> str:
    text = " ".join(" ".join(node.itertext()).split())
    if len(text) > limit:
        return text[: limit - 1] + "…"
    return text


def _git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def _source_path(root: Path, work_id: str) -> Path:
    matches = sorted((root / "CME" / "source").rglob(f"{work_id}.xml"))
    if len(matches) != 1:
        raise ValueError(f"expected one source for {work_id!r}, found {matches!r}")
    return matches[0]


def inspect(root: Path, work_id: str) -> dict[str, Any]:
    path = _source_path(root, work_id)
    tree = ET.parse(path)
    root_node = tree.getroot()
    elements = list(root_node.iter())
    tag_counts = Counter(_local_name(node.tag) for node in elements)

    identifiers: list[dict[str, str]] = []
    header_fields: dict[str, list[str]] = {}
    languages: list[dict[str, Any]] = []
    for node in elements:
        tag = _local_name(node.tag)
        if tag == "IDG" and node.get("ID"):
            identifiers.append({"kind": "IDG/@ID", "value": node.get("ID", "").strip()})
        elif tag in {"BIBNO", "VID", "IDNO"}:
            value = _compact_text(node, 240)
            if value:
                identifiers.append({"kind": tag, "value": value})
        if tag in TEXT_TAGS:
            value = _compact_text(node)
            if value and len(header_fields.setdefault(tag, [])) < 8:
                header_fields[tag].append(value)
        if tag == "LANGUAGE":
            languages.append(
                {
                    "text": _compact_text(node, 300),
                    "attributes": dict(sorted(node.attrib.items())),
                }
            )

    raw = path.read_bytes()
    relative_path = path.relative_to(root)
    return {
        "work_id": work_id,
        "source_path": str(relative_path),
        "root_element": _local_name(root_node.tag),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob": _git("hash-object", "--no-filters", str(path), cwd=root),
        "cme_commit": _git("rev-parse", "HEAD", cwd=root / "CME"),
        "identifiers": identifiers,
        "header_fields": header_fields,
        "languages": languages,
        "structure_counts": {
            tag: tag_counts[tag] for tag in sorted(COUNT_TAGS) if tag_counts[tag]
        },
        "umich_url": f"https://name.umdl.umich.edu/{work_id}",
        "notes": [
            "Header fields are compact diagnostic excerpts, not independent authority records.",
            "Structure counts describe this XML representation and may not equal canonical work units.",
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_id")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    print(json.dumps(inspect(args.root.resolve(), args.work_id), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
