#!/usr/bin/env python3
"""Audit CME XML for high-risk PDF typography/frontmatter structures.

This checker is intentionally report-only.  It does not decide whether source
markup is editorially wrong; it identifies source structures that are likely to
need generated-LaTeX/PDF inspection because they can affect drop caps, running
heads, generated contents, or frontmatter presentation.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# Allow importing sibling converter/audit helpers when the script is loaded by
# path from tests or run directly.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cme_contents_audit import (  # noqa: E402
    collect_title_pages,
    detect_format,
    direct_head_text,
    element_path,
    parse_xml,
)
from cme_xml_to_html import attr, child_elements, primary_text_nodes, tagu  # noqa: E402


ISSUE_FIELDS = ["source", "format", "severity", "code", "message", "context"]


@dataclass(frozen=True)
class TypographyIssue:
    source: str
    format: str
    severity: str
    code: str
    message: str
    context: str


def normalize_field(value: str) -> str:
    return " ".join((value or "").split())


def short_text(value: str, limit: int = 180) -> str:
    value = normalize_field(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def normalize_marker(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def marker_is_titlepage_like(marker: str) -> bool:
    return "titlepage" in marker


def marker_is_contents_like(marker: str) -> bool:
    return marker in {"toc", "content"} or "contents" in marker


def heading_marker_is_contents_like(marker: str) -> bool:
    return marker in {"toc", "content", "contents"} or marker.startswith(
        ("contents", "tableofcontents", "tablesofcontents", "listofcontents")
    )


def section_scope(el: object) -> str:
    current = el
    while current is not None and getattr(current, "tag", None) is not None:
        tag = tagu(current)
        if tag in {"FRONT", "BODY", "BACK"}:
            return tag.lower()
        current = current.getparent()
    return "unknown"


def element_context(el: object) -> str:
    parts = [
        f"scope={section_scope(el)}",
        f"line={getattr(el, 'sourceline', None) or 'unknown'}",
        f"path={element_path(el)}",
        f"tag={tagu(el)}",
    ]
    type_value = attr(el, "TYPE") or ""
    if type_value:
        parts.append(f"type={type_value}")
    text = short_text(" ".join(el.itertext()) if hasattr(el, "itertext") else "")
    if text:
        parts.append(f"text={text}")
    return "; ".join(parts)


def add_issue(issues: list[TypographyIssue], source: Path, fmt: str, severity: str, code: str, message: str, context: str) -> None:
    issue = TypographyIssue(str(source), fmt, severity, code, message, normalize_field(context))
    if issue not in issues:
        issues.append(issue)


def titlepage_elements(root: object, fmt: str) -> list[object]:
    wanted_paths = {candidate.path for candidate in collect_title_pages(root, fmt)}
    elements: list[object] = []
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if element_path(el) in wanted_paths:
            elements.append(el)
    return elements


def typography_text_sections(root: object, fmt: str) -> tuple[object, ...]:
    sections: list[object] = []
    for text_node in primary_text_nodes(root, fmt):
        for name in ("FRONT", "BODY", "BACK"):
            sections.extend(child_elements(text_node, name))
    return tuple(sections)


def is_typography_contents_container(el: object) -> bool:
    if tagu(el) in {"CONTENTS", "TOC"}:
        return True

    type_marker = normalize_marker(attr(el, "TYPE") or "")
    if "omitted" in type_marker:
        return False
    if marker_is_contents_like(type_marker):
        return True

    heading_marker = normalize_marker(direct_head_text(el))
    return heading_marker_is_contents_like(heading_marker)


def typography_contents_containers(root: object, fmt: str) -> list[object]:
    elements: list[object] = []
    seen: set[str] = set()

    def add_once(el: object) -> None:
        key = el.getroottree().getpath(el)
        if key not in seen:
            seen.add(key)
            elements.append(el)

    def walk(el: object) -> None:
        for child in child_elements(el):
            if is_typography_contents_container(child):
                add_once(child)
            else:
                walk(child)

    for section in typography_text_sections(root, fmt):
        if is_typography_contents_container(section):
            add_once(section)
        else:
            walk(section)
    return elements


def audit_file(path: Path) -> list[TypographyIssue]:
    parsed = parse_xml(path)
    fmt = detect_format(parsed.root)
    if fmt == "headwords":
        return []

    issues: list[TypographyIssue] = []

    titlepages = titlepage_elements(parsed.root, fmt)
    if len(titlepages) > 1:
        add_issue(
            issues,
            path,
            fmt,
            "needs_visual_sample",
            "multiple_title_pages",
            "Multiple title-page-like structures may affect frontmatter/dropcap presentation.",
            f"count={len(titlepages)}; " + "; ".join(element_context(el) for el in titlepages[:8]),
        )
    for el in titlepages:
        scope = section_scope(el)
        if scope in {"body", "back"}:
            add_issue(
                issues,
                path,
                fmt,
                "blocker_candidate",
                "source_titlepage_in_body_or_back",
                "Title-page-like structure appears outside FRONT and needs generated PDF inspection.",
                element_context(el),
            )

    contents = typography_contents_containers(parsed.root, fmt)
    if len(contents) > 1:
        add_issue(
            issues,
            path,
            fmt,
            "needs_visual_sample",
            "multiple_contents_sections",
            "Multiple source contents/table-of-contents sections may affect generated TOC/dropcap presentation.",
            f"count={len(contents)}; " + "; ".join(element_context(el) for el in contents[:8]),
        )
    for el in contents:
        scope = section_scope(el)
        if scope in {"body", "back"}:
            add_issue(
                issues,
                path,
                fmt,
                "blocker_candidate",
                "body_encoded_contents_section",
                "Contents/table-of-contents section appears outside FRONT and needs generated PDF inspection.",
                element_context(el),
            )

    return issues


def iter_sources(root: Path) -> tuple[Path, ...]:
    if root.is_file():
        return (root,)
    if root.is_dir():
        return tuple(sorted(root.rglob("*.xml")))
    raise SystemExit(f"Path not found: {root}")


def audit_sources(root: Path) -> list[TypographyIssue]:
    issues: list[TypographyIssue] = []
    for source in iter_sources(root):
        issues.extend(audit_file(source))
    return issues


def write_report(issues: Sequence[TypographyIssue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=ISSUE_FIELDS)
        writer.writeheader()
        for issue in issues:
            writer.writerow({field: getattr(issue, field) for field in ISSUE_FIELDS})


def write_high_risk_list(issues: Sequence[TypographyIssue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sources = sorted({issue.source for issue in issues if issue.severity in {"blocker_candidate", "needs_visual_sample"}})
    path.write_text("".join(f"{source}\n" for source in sources), encoding="utf-8")


def write_summary(issues: Sequence[TypographyIssue], path: Path) -> None:
    from collections import Counter, defaultdict

    path.parent.mkdir(parents=True, exist_ok=True)
    by_severity = Counter(issue.severity for issue in issues)
    by_code = Counter(issue.code for issue in issues)
    examples: dict[str, list[TypographyIssue]] = defaultdict(list)
    for issue in issues:
        examples[issue.code].append(issue)

    lines = ["# CME PDF typography risk audit", "", f"Total issues: {len(issues)}", "", "## Counts by severity", ""]
    for severity, count in by_severity.most_common():
        lines.append(f"- {severity}: {count}")
    lines.extend(["", "## Counts by code", ""])
    for code, count in by_code.most_common():
        lines.append(f"- {code}: {count}")
    lines.extend(["", "## Examples", ""])
    for code in sorted(examples):
        lines.extend([f"### {code}", ""])
        for issue in examples[code][:8]:
            lines.append(f"- `{issue.source}` ({issue.severity}): {short_text(issue.context, 320)}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="XML file or directory to audit")
    parser.add_argument("--report", type=Path, required=True, help="TSV report path")
    parser.add_argument("--summary", type=Path, help="optional Markdown summary path")
    parser.add_argument("--high-risk-list", type=Path, help="optional newline-delimited high-risk source list")
    parser.add_argument("--allow-issues", action="store_true", help="exit 0 even when risk rows are found")
    parser.add_argument("--allow-empty", action="store_true", help="succeed when no XML files are found")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    sources = iter_sources(args.root)
    if not sources and not args.allow_empty:
        raise SystemExit(f"No XML files found under {args.root}")
    issues = audit_sources(args.root)
    write_report(issues, args.report)
    if args.summary:
        write_summary(issues, args.summary)
    if args.high_risk_list:
        write_high_risk_list(issues, args.high_risk_list)
    return 1 if issues and not args.allow_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
