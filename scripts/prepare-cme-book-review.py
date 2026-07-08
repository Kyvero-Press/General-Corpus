#!/usr/bin/env python3
"""Prepare a bounded CME generated-book review manifest and chunk plan.

This helper is report-only.  It joins the XML format manifest, existing PDF
outputs, and source-structure audits so corpus review can proceed book by book
without loading the whole corpus into one context.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


MANIFEST_FIELDS = [
    "stem",
    "source",
    "format",
    "strict_xml",
    "primary_text_paths",
    "dist_pdf",
    "dist_pages",
    "duplicate_stem_group",
    "risk_codes",
    "contents_codes",
    "priority_bucket",
    "notes",
]

CHUNK_FIELDS = ["chunk", "order", "source", "stem", "format", "pages", "priority_bucket", "notes"]


@dataclass(frozen=True)
class ReviewRow:
    stem: str
    source: str
    format: str
    strict_xml: str
    primary_text_paths: str
    dist_pdf: str
    dist_pages: int | None
    duplicate_stem_group: str
    risk_codes: str
    contents_codes: str
    priority_bucket: str
    notes: str

    def as_dict(self) -> dict[str, str]:
        return {
            "stem": self.stem,
            "source": self.source,
            "format": self.format,
            "strict_xml": self.strict_xml,
            "primary_text_paths": self.primary_text_paths,
            "dist_pdf": self.dist_pdf,
            "dist_pages": "" if self.dist_pages is None else str(self.dist_pages),
            "duplicate_stem_group": self.duplicate_stem_group,
            "risk_codes": self.risk_codes,
            "contents_codes": self.contents_codes,
            "priority_bucket": self.priority_bucket,
            "notes": self.notes,
        }


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_pdf_pages(text: str) -> int | None:
    for line in text.splitlines():
        if line.lower().startswith("pages:"):
            value = line.split(":", 1)[1].strip()
            return int(value) if value.isdigit() else None
    return None


def pdf_page_count(path: Path) -> int | None:
    try:
        proc = subprocess.run(["pdfinfo", str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    return parse_pdf_pages(proc.stdout)


def grouped_codes(rows: Iterable[dict[str, str]], code_field: str = "code") -> dict[str, str]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        source = row.get("source", "")
        code = row.get(code_field, "")
        if source and code:
            grouped[source].add(code)
    return {source: ",".join(sorted(codes)) for source, codes in grouped.items()}


def pdfs_by_stem(dist_dir: Path) -> dict[str, Path]:
    if not dist_dir.exists():
        return {}
    return {pdf.stem: pdf for pdf in sorted(dist_dir.glob("*.pdf"))}


def priority_bucket(risk_codes: str, contents_codes: str) -> str:
    if risk_codes:
        return "1-risk"
    if contents_codes:
        return "2-contents"
    return "3-remaining"


def build_rows(
    manifest_rows: Sequence[dict[str, str]],
    *,
    dist_dir: Path,
    risk_rows: Sequence[dict[str, str]] = (),
    contents_rows: Sequence[dict[str, str]] = (),
) -> list[ReviewRow]:
    dist = pdfs_by_stem(dist_dir)
    risk_by_source = grouped_codes(risk_rows)
    contents_by_source = grouped_codes(contents_rows)
    sources_by_stem: dict[str, list[str]] = defaultdict(list)
    for row in manifest_rows:
        source = row.get("path", "")
        if source:
            sources_by_stem[Path(source).stem].append(source)

    page_cache: dict[Path, int | None] = {}
    output: list[ReviewRow] = []
    for row in manifest_rows:
        source = row.get("path", "")
        if not source:
            continue
        stem = Path(source).stem
        dist_pdf = dist.get(stem)
        if dist_pdf and dist_pdf not in page_cache:
            page_cache[dist_pdf] = pdf_page_count(dist_pdf)
        duplicate_sources = sources_by_stem.get(stem, [])
        risk_codes = risk_by_source.get(source, "")
        contents_codes = contents_by_source.get(source, "")
        notes: list[str] = []
        if len(duplicate_sources) > 1:
            notes.append("duplicate_stem_requires_canonical_decision")
        if not dist_pdf:
            notes.append("missing_dist_pdf")
        if row.get("strict_xml") == "no":
            notes.append("recovery_xml")
        output.append(
            ReviewRow(
                stem=stem,
                source=source,
                format=row.get("format", ""),
                strict_xml=row.get("strict_xml", ""),
                primary_text_paths=row.get("primary_text_paths", ""),
                dist_pdf="" if dist_pdf is None else str(dist_pdf),
                dist_pages=None if dist_pdf is None else page_cache.get(dist_pdf),
                duplicate_stem_group=";".join(duplicate_sources) if len(duplicate_sources) > 1 else "",
                risk_codes=risk_codes,
                contents_codes=contents_codes,
                priority_bucket=priority_bucket(risk_codes, contents_codes),
                notes=",".join(notes),
            )
        )
    return sorted(output, key=lambda r: (r.priority_bucket, r.format, r.stem, r.source))


def chunk_rows(rows: Sequence[ReviewRow], page_budget: int) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    chunk_id = 1
    used_pages = 0
    order = 0
    for row in rows:
        pages = row.dist_pages or 0
        if chunks and used_pages > 0 and used_pages + pages > page_budget:
            chunk_id += 1
            used_pages = 0
        order += 1
        chunks.append(
            {
                "chunk": str(chunk_id),
                "order": str(order),
                "source": row.source,
                "stem": row.stem,
                "format": row.format,
                "pages": "" if row.dist_pages is None else str(row.dist_pages),
                "priority_bucket": row.priority_bucket,
                "notes": row.notes,
            }
        )
        used_pages += pages
        if pages > page_budget:
            chunk_id += 1
            used_pages = 0
    return chunks


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xml-manifest", type=Path, default=Path("docs/xml-format-manifest.tsv"))
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--risk-report", type=Path, default=Path("build/corpus-book-review/audits/risk.tsv"))
    parser.add_argument("--contents-report", type=Path, default=Path("build/corpus-book-review/audits/contents.tsv"))
    parser.add_argument("--output", type=Path, default=Path("build/corpus-book-review/manifest.tsv"))
    parser.add_argument("--chunks", type=Path, default=Path("build/corpus-book-review/chunks/chunks.tsv"))
    parser.add_argument("--priority-sources", type=Path, default=Path("build/corpus-book-review/priority-sources.txt"))
    parser.add_argument("--page-budget", type=int, default=900)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = read_tsv(args.xml_manifest)
    if not manifest:
        raise SystemExit(f"No rows found in XML manifest: {args.xml_manifest}")
    rows = build_rows(
        manifest,
        dist_dir=args.dist_dir,
        risk_rows=read_tsv(args.risk_report),
        contents_rows=read_tsv(args.contents_report),
    )
    write_tsv(args.output, MANIFEST_FIELDS, (row.as_dict() for row in rows))
    write_tsv(args.chunks, CHUNK_FIELDS, chunk_rows(rows, args.page_budget))
    args.priority_sources.parent.mkdir(parents=True, exist_ok=True)
    args.priority_sources.write_text("".join(f"{row.source}\n" for row in rows), encoding="utf-8")
    print(f"wrote {len(rows)} manifest rows to {args.output}")
    print(f"wrote chunks to {args.chunks}")
    print(f"wrote priority sources to {args.priority_sources}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
