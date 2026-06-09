#!/usr/bin/env python3
"""Inventory the XML format iterations present in the CME corpus."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from lxml import etree

# Allow importing the sibling converter helpers when the script is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cme_xml_to_html import detect_format, local_name, parse_xml, primary_text_nodes, tagu  # noqa: E402


@dataclass
class FileRecord:
    path: str
    fmt: str
    strict_xml: bool
    root_signature: str
    doctype: str
    primary_text_paths: str
    errors: str = ""


@dataclass
class FormatSummary:
    count: int = 0
    strict_failures: list[str] = field(default_factory=list)
    roots: Counter[str] = field(default_factory=Counter)
    doctypes: Counter[str] = field(default_factory=Counter)
    directories: Counter[str] = field(default_factory=Counter)
    tags: Counter[str] = field(default_factory=Counter)
    samples: list[str] = field(default_factory=list)
    text_paths: Counter[str] = field(default_factory=Counter)


def direct_signature(root: etree._Element) -> str:
    children = [tagu(child) for child in root if isinstance(child.tag, str)]
    return "/".join([tagu(root), *children[:4]])


def doctype_for(path: Path) -> str:
    head = path.read_text("utf-8", errors="replace")[:4096]
    match = re.search(r"<!DOCTYPE\s+([^\s>]+)", head, flags=re.IGNORECASE)
    return match.group(1) if match else ""


def element_path(el: etree._Element) -> str:
    parts: list[str] = []
    cur: etree._Element | None = el
    while cur is not None and isinstance(cur.tag, str):
        parts.append(tagu(cur))
        cur = cur.getparent()
    return "/".join(reversed(parts))


def inventory(root_dir: Path) -> tuple[list[FileRecord], dict[str, FormatSummary]]:
    records: list[FileRecord] = []
    summaries: dict[str, FormatSummary] = defaultdict(FormatSummary)

    for path in sorted(root_dir.rglob("*.xml")):
        parsed = parse_xml(path)
        fmt = detect_format(parsed.root)
        signature = direct_signature(parsed.root)
        text_paths = ";".join(element_path(node) for node in primary_text_nodes(parsed.root, fmt))
        rel = str(path)
        errors = " | ".join(parsed.errors[:2])
        record = FileRecord(
            path=rel,
            fmt=fmt,
            strict_xml=not parsed.recovered,
            root_signature=signature,
            doctype=doctype_for(path),
            primary_text_paths=text_paths,
            errors=errors,
        )
        records.append(record)

        summary = summaries[fmt]
        summary.count += 1
        summary.roots[signature] += 1
        summary.doctypes[record.doctype or "(none)"] += 1
        # Three components normally gives CME/source/<bucket>.
        parts = path.parts
        summary.directories["/".join(parts[:3]) if len(parts) >= 3 else str(path.parent)] += 1
        summary.text_paths.update(text_paths.split(";") if text_paths else [])
        if parsed.recovered:
            summary.strict_failures.append(rel)
        if len(summary.samples) < 8:
            summary.samples.append(rel)
        for el in parsed.root.iter():
            if isinstance(el.tag, str):
                summary.tags[local_name(el).upper()] += 1

    return records, dict(sorted(summaries.items()))


def write_manifest(records: list[FileRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            delimiter="\t",
            fieldnames=[
                "path",
                "format",
                "strict_xml",
                "root_signature",
                "doctype",
                "primary_text_paths",
                "errors",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "path": record.path,
                    "format": record.fmt,
                    "strict_xml": "yes" if record.strict_xml else "no",
                    "root_signature": record.root_signature,
                    "doctype": record.doctype,
                    "primary_text_paths": record.primary_text_paths,
                    "errors": record.errors,
                }
            )


def markdown_report(root_dir: Path, records: list[FileRecord], summaries: dict[str, FormatSummary]) -> str:
    total = len(records)
    lines: list[str] = [
        "# XML format inventory",
        "",
        f"Scanned `{root_dir}` and found **{total} XML files**.",
        "",
        "| Format | Files | Strict XML failures | Main root/signature | Primary text payload |",
        "|---|---:|---:|---|---|",
    ]
    for fmt, summary in summaries.items():
        root_sig = summary.roots.most_common(1)[0][0] if summary.roots else ""
        text_path = summary.text_paths.most_common(1)[0][0] if summary.text_paths else ""
        lines.append(
            f"| `{fmt}` | {summary.count} | {len(summary.strict_failures)} | `{root_sig}` | `{text_path}` |"
        )

    descriptions = {
        "dlpstextclass": "Older DLPS/HTI TEI-like files. Header lives in `HEADER`; text lives in `TEXT` with `FRONT`, `BODY`, `BACK`, `DIV1`...`DIV7`, `P`, `LG`, `L`, `NOTE1`, `HI1`, `PB`, and `MILESTONE`.",
        "ets-temphead-eebo": "Phase-3 EEBO/TCP-derived files with root `ETS`, a temporary revision header in `TEMPHEAD`, and payload under `EEBO/TEXT` or `EEBO/GROUP/TEXT`.",
        "ets-header-eebo": "Newer repaired/addition ETS files where the bibliographic `HEADER` has replaced `TEMPHEAD`; payload is still under `EEBO/TEXT`.",
        "tei2": "Single legacy `TEI.2` file with a standard-ish `TEIHEADER` and `TEXT/BODY`.",
        "headwords": "Lexical headword list, not a running text. It is converted as flowing paragraph records rather than prose/verse so large PDFs avoid oversized LaTeX tables or labels.",
    }

    lines.extend(["", "## Format categories", ""])
    for fmt, summary in summaries.items():
        lines.append(f"### `{fmt}`")
        lines.append("")
        if fmt in descriptions:
            lines.append(descriptions[fmt])
            lines.append("")
        lines.append("Directories:")
        for directory, count in summary.directories.most_common():
            lines.append(f"- `{directory}`: {count}")
        lines.append("")
        lines.append("Most common elements:")
        lines.append(
            "- " + ", ".join(f"`{tag}` ({count})" for tag, count in summary.tags.most_common(12))
        )
        lines.append("")
        lines.append("Sample files:")
        for sample in summary.samples:
            lines.append(f"- `{sample}`")
        if summary.strict_failures:
            lines.append("")
            lines.append("Strict XML failures recovered by the converter:")
            for sample in summary.strict_failures[:20]:
                lines.append(f"- `{sample}`")
            if len(summary.strict_failures) > 20:
                lines.append(f"- ...and {len(summary.strict_failures) - 20} more")
        lines.append("")

    lines.extend(
        [
            "## Conversion scripts",
            "",
            "The scripts in `scripts/` normalize the source XML to HTML and then call Pandoc.",
            "Use the format-specific wrappers when you already know the category, or `pandoc-cme-xml` to auto-detect.",
            "",
            "```bash",
            "scripts/pandoc-dlpstextclass INPUT.xml OUTPUT.html [PANDOC_OPTIONS...]",
            "scripts/pandoc-ets INPUT.xml OUTPUT.epub [PANDOC_OPTIONS...]",
            "scripts/pandoc-tei2 INPUT.xml OUTPUT.pdf --pdf-engine=xelatex",
            "scripts/pandoc-headwords INPUT.xml OUTPUT.html",
            "scripts/pandoc-cme-xml INPUT.xml OUTPUT.docx",
            "scripts/pandoc-all CME/source build/pandoc html",
            "```",
            "",
            "Useful XML-side options accepted before `INPUT.xml`: `--drop-notes`, `--preserve-milestones`, and `--strict`.",
            "All remaining arguments after `OUTPUT` are passed directly to Pandoc.",
            "For `.tex`, `.latex`, and `.pdf` output, `pandoc-cme-xml` automatically adds the project LaTeX pagination header and Lua filter in `scripts/pandoc-latex-pagebreaks.*` to reduce orphaned/widowed prose and verse fragments.",
            "",
            "A complete per-file TSV manifest is generated by:",
            "",
            "```bash",
            "scripts/categorize-xml-formats.py CME/source --manifest docs/xml-format-manifest.tsv --output docs/xml-formats.md",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("CME/source"))
    parser.add_argument("--manifest", type=Path, help="write per-file TSV manifest")
    parser.add_argument("--output", type=Path, help="write Markdown report instead of stdout")
    parser.add_argument("--json", action="store_true", help="emit JSON summary instead of Markdown")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="succeed when ROOT contains no XML files",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.root.is_dir():
        raise SystemExit(f"XML root directory not found: {args.root}")

    records, summaries = inventory(args.root)
    if not records and not args.allow_empty:
        raise SystemExit(f"No XML files found under: {args.root}")

    if args.manifest:
        write_manifest(records, args.manifest)

    if args.json:
        payload = {
            "root": str(args.root),
            "total": len(records),
            "formats": {
                fmt: {
                    "count": summary.count,
                    "strictFailures": summary.strict_failures,
                    "rootSignatures": dict(summary.roots),
                    "doctypes": dict(summary.doctypes),
                    "directories": dict(summary.directories),
                    "primaryTextPaths": dict(summary.text_paths),
                    "topElements": dict(summary.tags.most_common(30)),
                    "samples": summary.samples,
                }
                for fmt, summary in summaries.items()
            },
        }
        output = json.dumps(payload, indent=2, ensure_ascii=False)
    else:
        output = markdown_report(args.root, records, summaries)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
