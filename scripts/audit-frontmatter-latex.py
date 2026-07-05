#!/usr/bin/env python3
"""Generate LaTeX for CME XML files and audit PDF front-matter metadata.

The audit checks that the generated Pandoc LaTeX contains the title-page and
colophon data derived from the source XML: title, subtitles/title supplements,
author (or Anonymous), original date, source path, format, editor, source date,
identifier when present, and the General Corpus repository/download notice.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import cme_xml_to_html as cme  # noqa: E402


REPOSITORY_URL = "https://github.com/Kyvero-Press/General-Corpus"
COLLECTION_NOTICE_MARKERS = (
    "source for this book",
    "other general corpus books and texts",
    "available for download",
)
DOCUMENT_BEGIN_MARKER = "\\begin{document}"
FRONTMATTER_ORDER_MARKERS = (
    "\\maketitle",
    "\\cmeColophon",
    "\\tableofcontents",
    "\\mainmatter",
)


def label_for(path: Path, root: Path) -> Path:
    rel = path.relative_to(root)
    return rel.with_suffix(".tex")


def contains_tex_value(tex: str, value: str, *, break_paths: bool = False) -> bool:
    if not value:
        return True
    expected = cme.latex_text(value, break_paths=break_paths)
    if expected in tex:
        return True
    # Pandoc may wrap metadata values in macro arguments.  Fall back to a
    # whitespace-insensitive search for non-path values.
    if break_paths:
        return False
    compact_expected = re.sub(r"\s+", " ", expected).strip()
    compact_tex = re.sub(r"\s+", " ", tex)
    return compact_expected in compact_tex


def frontmatter_order_is_valid(tex: str) -> bool:
    body_start = tex.find(DOCUMENT_BEGIN_MARKER)
    if body_start < 0:
        return False
    body = tex[body_start + len(DOCUMENT_BEGIN_MARKER) :]
    positions = [body.find(marker) for marker in FRONTMATTER_ORDER_MARKERS]
    return not any(position < 0 for position in positions) and positions == sorted(positions)


def audit_one(source: Path, root: Path, output_root: Path) -> dict[str, str]:
    parsed = cme.parse_xml(source)
    fmt = cme.detect_format(parsed.root)
    cme.require_format("auto", fmt, source)
    meta = cme.metadata(parsed.root, fmt, source, parsed)

    tex_path = output_root / label_for(source, root)
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(SCRIPT_DIR / "pandoc-cme-xml"),
        "--xml-format",
        fmt,
        str(source),
        str(tex_path),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    omissions: list[str] = []
    if proc.returncode != 0:
        return {
            "source": str(source),
            "format": fmt,
            "tex": str(tex_path),
            "status": "FAIL",
            "omissions": "pandoc-cme-xml failed: " + (proc.stderr.strip() or proc.stdout.strip())[:500],
            "title": meta.get("title", ""),
            "subtitle": meta.get("subtitle", ""),
            "author": meta.get("author", "Anonymous"),
            "original_date": meta.get("original_date", ""),
        }

    tex = tex_path.read_text(errors="replace")
    if REPOSITORY_URL not in tex:
        omissions.append("repository_url")
    normalized_tex = re.sub(r"\s+", " ", tex).lower()
    if any(marker not in normalized_tex for marker in COLLECTION_NOTICE_MARKERS):
        omissions.append("collection_notice")

    checks = [
        ("title", meta.get("title", ""), False),
        ("subtitle", meta.get("subtitle", ""), False),
        ("author", meta.get("author") or "Anonymous", False),
        ("original_date", meta.get("original_date", ""), False),
        ("source", meta.get("source", ""), True),
        ("format", meta.get("format", ""), False),
        ("editor", meta.get("editor", ""), False),
        ("source_date", meta.get("date", ""), False),
        ("identifier", meta.get("id", ""), False),
    ]
    for name, value, break_paths in checks:
        if value and not contains_tex_value(tex, value, break_paths=break_paths):
            omissions.append(name)

    if not frontmatter_order_is_valid(tex):
        omissions.append("frontmatter_order")
    if "\\section{Source metadata}" in tex:
        omissions.append("source_metadata_left_in_body")

    # Cross-check explicit source title parts/supplements are represented in
    # the derived title/subtitle values, not merely in body text.
    display_values = " — ".join(
        part for part in (meta.get("title", ""), meta.get("subtitle", "")) if part
    )
    source_title_parts = cme.titlepage_title_parts(parsed.root, fmt)
    for part in source_title_parts:
        if part and cme.title_key(part) not in cme.title_key(display_values):
            omissions.append("source_titlepart:" + part[:80])
    if not source_title_parts:
        for part in cme.body_title_supplements(parsed.root, fmt, meta.get("title", "")):
            if part and cme.title_key(part) not in cme.title_key(display_values):
                omissions.append("source_titlesupplement:" + part[:80])

    return {
        "source": str(source),
        "format": fmt,
        "tex": str(tex_path),
        "status": "PASS" if not omissions else "FAIL",
        "omissions": "; ".join(omissions),
        "title": meta.get("title", ""),
        "subtitle": meta.get("subtitle", ""),
        "author": meta.get("author", "Anonymous"),
        "original_date": meta.get("original_date", ""),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path, nargs="?", default=Path("CME/source"))
    parser.add_argument("--output-root", type=Path, default=Path("build/frontmatter-audit/tex"))
    parser.add_argument("--report", type=Path, default=Path("build/frontmatter-audit/frontmatter-audit.tsv"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    sources = sorted(args.source_root.rglob("*.xml"))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output_root.mkdir(parents=True, exist_ok=True)
    rows = [audit_one(source, args.source_root, args.output_root) for source in sources]
    with args.report.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source", "format", "tex", "status", "omissions", "title", "subtitle", "author", "original_date"],
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    failures = [row for row in rows if row["status"] != "PASS"]
    print(f"audited {len(rows)} source XML files")
    print(f"report {args.report}")
    print(f"failures {len(failures)}")
    for row in failures[:20]:
        print(f"FAIL {row['source']}: {row['omissions']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
