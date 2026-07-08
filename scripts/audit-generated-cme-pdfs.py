#!/usr/bin/env python3
"""Audit generated CME PDFs for publication/frontmatter anomalies.

This checker is report-only.  It reads PDF metadata, fonts, and extracted text
and flags likely publication problems such as duplicated generated frontmatter,
visible source metadata, page-size mismatches, unembedded fonts, and blank or
suspicious boundary pages.  It does not decide editorial source structure.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ISSUE_FIELDS = ["pdf", "source", "severity", "code", "message", "context"]
EXPECTED_WIDTH_PT = 360.0
EXPECTED_HEIGHT_PT = 576.0
SIZE_TOLERANCE_PT = 1.0


@dataclass(frozen=True)
class PdfIssue:
    pdf: str
    source: str
    severity: str
    code: str
    message: str
    context: str


def normalize_space(value: str) -> str:
    return " ".join((value or "").split())


def short(value: str, limit: int = 240) -> str:
    value = normalize_space(value)
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def run_text(cmd: Sequence[str]) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except FileNotFoundError as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def parse_pdfinfo(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip().casefold()] = value.strip()
    return data


def parse_page_size(value: str) -> tuple[float, float] | None:
    match = re.search(r"([0-9.]+)\s+x\s+([0-9.]+)\s+pts", value or "", re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def page_size_is_expected(size: tuple[float, float] | None) -> bool:
    if size is None:
        return False
    width, height = size
    direct = abs(width - EXPECTED_WIDTH_PT) <= SIZE_TOLERANCE_PT and abs(height - EXPECTED_HEIGHT_PT) <= SIZE_TOLERANCE_PT
    rotated = abs(width - EXPECTED_HEIGHT_PT) <= SIZE_TOLERANCE_PT and abs(height - EXPECTED_WIDTH_PT) <= SIZE_TOLERANCE_PT
    return direct or rotated


def unembedded_fonts(pdffonts_text: str) -> list[str]:
    fonts: list[str] = []
    for line in pdffonts_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("name") or stripped.startswith("----"):
            continue
        parts = stripped.split()
        if len(parts) < 4:
            continue
        # Poppler columns end with emb/sub/uni/object ID.  From the right,
        # ``emb`` is five tokens back; ``sub`` is four tokens back.
        emb = parts[-5] if len(parts) >= 5 else ""
        if emb.lower() == "no":
            fonts.append(parts[0])
    return fonts


def split_pages(pdftotext_output: str) -> list[str]:
    pages = pdftotext_output.split("\f")
    if pages and pages[-1] == "":
        pages.pop()
    return pages or [pdftotext_output]


def count_phrase(text: str, phrase: str) -> int:
    return len(re.findall(re.escape(phrase), text, flags=re.IGNORECASE))


def leading_lines(page: str, limit: int = 12) -> list[str]:
    return [line.strip() for line in page.splitlines() if line.strip()][:limit]


def count_pages_with_leading_pattern(pages: Sequence[str], pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for page in pages if any(regex.search(line) for line in leading_lines(page)))


def blank_pages(pages: Sequence[str], *, max_words: int = 3) -> list[int]:
    blanks: list[int] = []
    for index, page in enumerate(pages, start=1):
        if len(re.findall(r"\w+", page)) <= max_words:
            blanks.append(index)
    return blanks


def source_for_pdf(pdf: Path, manifest_by_stem: dict[str, str]) -> str:
    return manifest_by_stem.get(pdf.stem, "")


def add_issue(issues: list[PdfIssue], pdf: Path, source: str, severity: str, code: str, message: str, context: str) -> None:
    issue = PdfIssue(str(pdf), source, severity, code, message, short(context, 500))
    if issue not in issues:
        issues.append(issue)


def audit_pdf(pdf: Path, manifest_by_stem: dict[str, str] | None = None) -> list[PdfIssue]:
    manifest_by_stem = manifest_by_stem or {}
    source = source_for_pdf(pdf, manifest_by_stem)
    issues: list[PdfIssue] = []

    info_code, info_out, info_err = run_text(["pdfinfo", str(pdf)])
    if info_code != 0:
        add_issue(issues, pdf, source, "error", "pdfinfo_failed", "pdfinfo failed for generated PDF.", info_err or info_out)
        return issues
    info = parse_pdfinfo(info_out)
    page_count = info.get("pages", "")
    size = parse_page_size(info.get("page size", ""))
    if not page_size_is_expected(size):
        add_issue(
            issues,
            pdf,
            source,
            "warning",
            "unexpected_page_size",
            "Generated PDF page size is not the expected 5 x 8 inch review size.",
            f"page_size={info.get('page size', '')}; pages={page_count}",
        )

    fonts_code, fonts_out, fonts_err = run_text(["pdffonts", str(pdf)])
    if fonts_code != 0:
        add_issue(issues, pdf, source, "warning", "pdffonts_failed", "pdffonts failed for generated PDF.", fonts_err or fonts_out)
    else:
        bad_fonts = unembedded_fonts(fonts_out)
        if bad_fonts:
            add_issue(
                issues,
                pdf,
                source,
                "warning",
                "unembedded_fonts",
                "One or more PDF fonts are not embedded.",
                "fonts=" + ",".join(bad_fonts[:20]),
            )

    text_code, text_out, text_err = run_text(["pdftotext", "-layout", str(pdf), "-"])
    if text_code != 0:
        add_issue(issues, pdf, source, "warning", "pdftotext_failed", "pdftotext failed for generated PDF.", text_err or text_out)
        return issues
    pages = split_pages(text_out)
    full_text = "\n".join(pages)
    phrase_counts = {
        "generated_title_pages": count_pages_with_leading_pattern(pages, r"^general corpus edition$"),
        "colophon_pages": count_pages_with_leading_pattern(pages, r"^colophon$"),
        "source_metadata": count_phrase(full_text, "Source metadata"),
        "contents_pages": count_pages_with_leading_pattern(pages, r"^(contents|table of contents)$"),
    }
    if phrase_counts["generated_title_pages"] > 1:
        add_issue(issues, pdf, source, "warning", "duplicate_generated_title_signal", "Generated title-page signal appears more than once.", str(phrase_counts))
    if phrase_counts["colophon_pages"] > 1:
        add_issue(issues, pdf, source, "warning", "duplicate_colophon_signal", "Generated colophon signal appears more than once.", str(phrase_counts))
    if phrase_counts["contents_pages"] > 1:
        add_issue(issues, pdf, source, "info", "many_contents_signals", "Contents/Table of Contents text appears repeatedly; inspect for duplicate source/generated TOCs.", str(phrase_counts))
    if phrase_counts["source_metadata"]:
        add_issue(issues, pdf, source, "warning", "visible_source_metadata", "Source metadata block appears visible in generated PDF text.", str(phrase_counts))

    blanks = blank_pages(pages)
    if blanks:
        add_issue(issues, pdf, source, "info", "near_blank_pages", "PDF contains near-blank pages; inspect if unexpected.", "pages=" + ",".join(map(str, blanks[:30])))
    if pages and len(re.findall(r"\w+", pages[0])) < 5:
        add_issue(issues, pdf, source, "info", "suspicious_first_page", "First page has very little extracted text.", short(pages[0]))
    if pages and len(re.findall(r"\w+", pages[-1])) < 5:
        add_issue(issues, pdf, source, "info", "suspicious_last_page", "Last page has very little extracted text.", short(pages[-1]))
    return issues


def read_manifest_sources(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle, delimiter="\t")
        return {Path(row.get("dist_pdf", "")).stem: row.get("source", "") for row in rows if row.get("dist_pdf")}


def iter_pdfs(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if root.is_dir():
        return sorted(root.rglob("*.pdf"))
    raise SystemExit(f"PDF path not found: {root}")


def write_report(issues: Sequence[PdfIssue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=ISSUE_FIELDS, lineterminator="\n")
        writer.writeheader()
        for issue in issues:
            writer.writerow({field: getattr(issue, field) for field in ISSUE_FIELDS})


def write_summary(issues: Sequence[PdfIssue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_code = Counter(issue.code for issue in issues)
    by_severity = Counter(issue.severity for issue in issues)
    examples: dict[str, list[PdfIssue]] = defaultdict(list)
    for issue in issues:
        examples[issue.code].append(issue)
    lines = ["# Generated CME PDF audit", "", f"Total issues: {len(issues)}", "", "## Counts by severity", ""]
    for severity, count in by_severity.most_common():
        lines.append(f"- {severity}: {count}")
    lines.extend(["", "## Counts by code", ""])
    for code, count in by_code.most_common():
        lines.append(f"- {code}: {count}")
    lines.extend(["", "## Examples", ""])
    for code in sorted(examples):
        lines.extend([f"### {code}", ""])
        for issue in examples[code][:10]:
            source = f" source={issue.source}" if issue.source else ""
            lines.append(f"- `{issue.pdf}`{source} ({issue.severity}): {issue.context}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_root", type=Path, help="PDF file or directory to audit")
    parser.add_argument("--manifest", type=Path, help="optional review manifest TSV")
    parser.add_argument("--report", type=Path, required=True, help="TSV report path")
    parser.add_argument("--summary", type=Path, help="optional Markdown summary path")
    parser.add_argument("--allow-issues", action="store_true", help="exit 0 even when issues are found")
    parser.add_argument("--allow-empty", action="store_true", help="succeed when no PDFs are found")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    pdfs = iter_pdfs(args.pdf_root)
    if not pdfs and not args.allow_empty:
        raise SystemExit(f"No PDFs found under {args.pdf_root}")
    manifest_by_stem = read_manifest_sources(args.manifest)
    issues: list[PdfIssue] = []
    for pdf in pdfs:
        issues.extend(audit_pdf(pdf, manifest_by_stem))
    write_report(issues, args.report)
    if args.summary:
        write_summary(issues, args.summary)
    print(f"audited {len(pdfs)} PDFs")
    print(f"issues {len(issues)}")
    return 1 if issues and not args.allow_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
