#!/usr/bin/env python3
"""Audit CME XML contents/frontmatter references against BODY divisions.

The report is intentionally conservative: it looks for explicit part/chapter
signals in title pages, contents sections, and BODY division metadata, then
flags cases where the BODY structure does not represent those references.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence

from lxml import etree

# Allow importing the sibling converter helpers when this module or its wrapper
# is loaded directly by path.
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cme_xml_to_html import (  # noqa: E402
    attr,
    child_elements,
    detect_format,
    parse_xml,
    primary_text_nodes,
    tagu,
    title_text,
)


ISSUE_FIELDS = ["source", "format", "code", "message", "context"]
SUPPORTED_DIVISION_KINDS = {"part", "chapter"}
MAX_PART_ORDINAL = 100
MAX_CHAPTER_ORDINAL = 999
MAX_SEQUENCE_GAP_SIZE = 200
MAX_DISPLAY_NUMBERS = 40
DIV_TAG_RE = re.compile(r"^DIV\d*$", re.IGNORECASE)
NOTE_TAG_RE = re.compile(r"^NOTE\d*$", re.IGNORECASE)


ENGLISH_ORDINALS: dict[str, int] = {
    "first": 1,
    "firste": 1,
    "fyrst": 1,
    "fyrste": 1,
    "seconde": 2,
    "second": 2,
    "secound": 2,
    "secounde": 2,
    "secunde": 2,
    "third": 3,
    "thirde": 3,
    "thrid": 3,
    "thridde": 3,
    "thride": 3,
    "þridde": 3,
    "fourth": 4,
    "fourthe": 4,
    "fourte": 4,
    "fourt": 4,
    "fyfthe": 5,
    "fifte": 5,
    "fifth": 5,
    "fifthe": 5,
    "sixth": 6,
    "sixte": 6,
    "sixteenthe": 16,
    "seventh": 7,
    "seventhe": 7,
    "seuenth": 7,
    "seuenthe": 7,
    "eighth": 8,
    "eighthe": 8,
    "ninth": 9,
    "ninthe": 9,
    "tenth": 10,
    "tenthe": 10,
    "eleventh": 11,
    "eleventhe": 11,
    "twelfth": 12,
    "twelfthe": 12,
    "thirteenth": 13,
    "thirteenthe": 13,
    "fourteenth": 14,
    "fourteenthe": 14,
    "fifteenth": 15,
    "fifteenthe": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "seventeenthe": 17,
    "eighteenth": 18,
    "eighteenthe": 18,
    "nineteenth": 19,
    "nineteenthe": 19,
    "twentieth": 20,
    "twentithe": 20,
    "prima": 1,
    "primus": 1,
    "secunda": 2,
    "secundus": 2,
    "tercia": 3,
    "tertia": 3,
    "tercius": 3,
    "tertius": 3,
    "quarta": 4,
    "quartus": 4,
    "quinta": 5,
    "quintus": 5,
    "sexta": 6,
    "sextus": 6,
    "septima": 7,
    "septimus": 7,
    "octava": 8,
    "octavus": 8,
    "nona": 9,
    "nonus": 9,
    "decima": 10,
    "decimus": 10,
    "vndecimum": 11,
    "undecimum": 11,
    "duodecimum": 12,
}

WORD_ORDINAL_RE = re.compile(
    r"\b(" + "|".join(sorted(map(re.escape, ENGLISH_ORDINALS), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
ARABIC_ORDINAL_RE = re.compile(r"(?<![\w])([\[(]?\d[\d,]*(?:st|nd|rd|th|m)?[\])]?(?![\w]))", re.IGNORECASE)
ROMAN_ORDINAL_RE = re.compile(r"(?<![A-Za-z0-9])([mdclxvij]+)(?![A-Za-z0-9])", re.IGNORECASE)
ROMAN_ATOM = r"(?<![A-Za-z0-9])[mdclxvij]+(?![A-Za-z0-9])"
ARABIC_ATOM = r"(?<![\w])[\[(]?\d[\d,]*(?:st|nd|rd|th|m)?[\])]?(?![\w])"
WORD_ATOM = r"\b(?:" + "|".join(sorted(map(re.escape, ENGLISH_ORDINALS), key=len, reverse=True)) + r")\b"
ORDINAL_ATOM = rf"(?:{ARABIC_ATOM}|{ROMAN_ATOM}|{WORD_ATOM})"
ORDINAL_PHRASE_RE = re.compile(
    rf"(?P<phrase>{ORDINAL_ATOM}(?:\s*(?:[-–—]|,|\band\b|\bto\b|\bthrough\b|\bthru\b)\s*{ORDINAL_ATOM})*)",
    re.IGNORECASE,
)
RANGE_SEPARATOR_RE = re.compile(r"^\s*(?:[-–—]|to|through|thru)\s*$", re.IGNORECASE)
PART_LABEL_RE = r"(?:partie|party|part|pt\.?|pars)"
CHAPTER_LABEL_RE = (
    r"(?:chapter|chap\.?|capitulum|capitulu\.?|capitulo|cap(?:i|y)?\s*m\.?|capl\s*m\.?|caplm\.?|cam\.?|ca\s*m\.?|cap(?![a-zl])\.?)"
)
LINE_RANGE_RE = re.compile(r"\blines?\s+(\d[\d,]*)\s*[-–—]\s*(\d[\d,]*)", re.IGNORECASE)


@dataclass(frozen=True)
class Issue:
    source: str
    format: str
    code: str
    message: str
    context: str


@dataclass(frozen=True)
class OrdinalToken:
    start: int
    end: int
    value: int


@dataclass(frozen=True)
class FrontPartExpectation:
    ordinal: int
    label: str
    context: str
    line_ranges: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class TocRef:
    kind: str
    ordinal: int
    label: str
    context: str
    part_ordinal: int | None = None


@dataclass(frozen=True)
class BodyIndex:
    parts: frozenset[int]
    chapters: frozenset[int]
    chapters_by_part: Mapping[int, frozenset[int]]
    has_part_divisions: bool = False


@dataclass(frozen=True)
class BodyDivision:
    element: etree._Element
    kind: str
    ordinals: tuple[int, ...]


@dataclass(frozen=True)
class TitlePageCandidate:
    line: int | None
    path: str
    tag: str
    type_value: str
    text: str


@dataclass(frozen=True)
class AuditState:
    source: Path
    fmt: str
    issues: list[Issue]

    def add(self, code: str, message: str, context: str) -> None:
        issue = Issue(str(self.source), self.fmt, code, message, normalize_field(context))
        if issue not in self.issues:
            self.issues.append(issue)


def normalize_field(value: str) -> str:
    return " ".join((value or "").split())


def normalize_ordinal_text(value: str) -> str:
    return (value or "").replace("ſ", "s").replace("ȝ", "y").replace("ƚ", "l")


def short_text(value: str, limit: int = 160) -> str:
    value = normalize_field(value)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def roman_to_int(value: str, *, allow_single_high: bool = False) -> int | None:
    text = value.strip().lower().replace("j", "i")
    stripped_marker_suffix = False
    if len(text) > 1 and text.endswith("m") and "m" not in text[:-1]:
        # Some CME chapter references use a trailing abbreviation marker, e.g.
        # "Capm. ijm." for chapter 2, "Cam.xm." for chapter 10, and
        # "Capm. lm." for chapter 50.  Treat that final m as a marker rather
        # than as Roman 1000.
        text = text[:-1]
        stripped_marker_suffix = True
    if not text or not re.fullmatch(r"[mdclxvi]+", text):
        return None
    # A lone high Roman letter is more often an abbreviation in CME headings
    # (for example "Cap m. xix.") than an intended part/chapter ordinal, unless
    # it came from a known trailing-m chapter marker such as "lm.".
    if not stripped_marker_suffix and not allow_single_high and len(text) == 1 and text in {"l", "c", "d", "m"}:
        return None
    values = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    total = 0
    for index, char in enumerate(text):
        current = values[char]
        next_value = values[text[index + 1]] if index + 1 < len(text) else 0
        if current < next_value:
            total -= current
        else:
            total += current
    if total <= 0 or total > 10000:
        return None
    return total


def arabic_to_int(value: str) -> int | None:
    text = value.strip().lower()
    text = text.strip("[]()")
    text = re.sub(r"(?:st|nd|rd|th|m)$", "", text)
    text = text.replace(",", "")
    if not text.isdigit():
        return None
    number = int(text)
    if number <= 0:
        return None
    return number


def ordinal_tokens(text: str, *, allow_single_high: bool = False) -> tuple[OrdinalToken, ...]:
    text = normalize_ordinal_text(text)
    tokens: list[OrdinalToken] = []

    for match in ARABIC_ORDINAL_RE.finditer(text):
        value = arabic_to_int(match.group(1))
        if value is not None:
            tokens.append(OrdinalToken(match.start(), match.end(), value))

    for match in ROMAN_ORDINAL_RE.finditer(text):
        value = roman_to_int(match.group(1), allow_single_high=allow_single_high)
        if value is not None:
            tokens.append(OrdinalToken(match.start(), match.end(), value))

    for match in WORD_ORDINAL_RE.finditer(text):
        value = ENGLISH_ORDINALS[match.group(1).casefold()]
        tokens.append(OrdinalToken(match.start(), match.end(), value))

    tokens.sort(key=lambda token: (token.start, token.end))
    filtered: list[OrdinalToken] = []
    last_end = -1
    for token in tokens:
        if token.start < last_end:
            continue
        filtered.append(token)
        last_end = token.end
    return tuple(filtered)


def parse_ordinals(text: str | None, *, allow_single_high: bool = False) -> tuple[int, ...]:
    """Parse conservative ordinal references from a short label.

    Supports Arabic ordinals, Roman numerals, medieval final-j Roman forms, and
    the Middle/Modern English ordinal words needed by the CME structural tests.
    Ranges using dash/to/through are expanded; comma/"and" lists are preserved.
    """

    if not text:
        return ()
    tokens = ordinal_tokens(text, allow_single_high=allow_single_high)
    if not tokens:
        return ()

    values: list[int] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if index + 1 < len(tokens):
            next_token = tokens[index + 1]
            separator = text[token.end : next_token.start]
            if RANGE_SEPARATOR_RE.match(separator) and token.value < next_token.value:
                values.extend(range(token.value, next_token.value + 1))
                index += 2
                continue
        values.append(token.value)
        index += 1

    result: list[int] = []
    seen: set[int] = set()
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return tuple(result)


def ordinal_phrase_at_start(text: str) -> str:
    text = normalize_ordinal_text(text)
    match = ORDINAL_PHRASE_RE.match(text.strip())
    return match.group("phrase") if match else ""


def labeled_ordinals(text: str | None, kind: str, *, anchored: bool = False) -> tuple[int, ...]:
    if not text:
        return ()
    text = normalize_ordinal_text(text)
    label = PART_LABEL_RE if kind == "part" else CHAPTER_LABEL_RE
    prefix = r"^\s*" if anchored else r"\b"
    forward = re.compile(
        prefix + rf"(?:the\s+)?(?:{label})s?\s*[.:]?\s*(?P<rest>.{{1,120}})",
        re.IGNORECASE,
    )
    for match in forward.finditer(text):
        rest = match.group("rest")
        candidates = [rest, re.sub(r"^\s*(?:[a-z]\.)+\s*", "", rest, flags=re.IGNORECASE)]
        for candidate in candidates:
            phrase = ordinal_phrase_at_start(candidate)
            ordinals = plausible_division_ordinals(parse_ordinals(phrase, allow_single_high=True), kind)
            if ordinals:
                return ordinals

    reverse = re.compile(
        prefix
        + rf"(?:the\s+)?(?P<phrase>{ORDINAL_ATOM}(?:\s*(?:[-–—]|,|\band\b|\bto\b|\bthrough\b|\bthru\b)\s*{ORDINAL_ATOM})*)\s+(?:{label})s?\b",
        re.IGNORECASE,
    )
    for match in reverse.finditer(text):
        ordinals = plausible_division_ordinals(parse_ordinals(match.group("phrase"), allow_single_high=True), kind)
        if ordinals:
            return ordinals
    return ()


def line_ranges_from_text(text: str | None) -> tuple[tuple[int, int], ...]:
    if not text:
        return ()
    ranges: list[tuple[int, int]] = []
    for match in LINE_RANGE_RE.finditer(text):
        start = arabic_to_int(match.group(1))
        end = arabic_to_int(match.group(2))
        if start is not None and end is not None and start <= end:
            ranges.append((start, end))
    return tuple(ranges)


def format_numbers(values: Iterable[int]) -> str:
    numbers = list(values)
    if not numbers:
        return "none"
    shown = numbers[:MAX_DISPLAY_NUMBERS]
    suffix = f",…(+{len(numbers) - len(shown)} more)" if len(shown) < len(numbers) else ""
    return ",".join(str(value) for value in shown) + suffix


def plausible_division_ordinals(ordinals: Iterable[int], kind: str) -> tuple[int, ...]:
    maximum = MAX_PART_ORDINAL if kind == "part" else MAX_CHAPTER_ORDINAL
    return tuple(ordinal for ordinal in ordinals if ordinal <= maximum)


def is_div(el: etree._Element) -> bool:
    tag = tagu(el)
    return tag == "DIV" or bool(DIV_TAG_RE.match(tag))


def normalized_type(el: etree._Element) -> str:
    return re.sub(r"[^a-z0-9]+", "", (attr(el, "TYPE") or "").casefold())


def division_kind(el: etree._Element) -> str | None:
    if not is_div(el):
        return None
    typ = normalized_type(el)
    if typ in {"part", "pt"}:
        return "part"
    if typ in {"chapter", "chap", "cap", "capitulum"}:
        return "chapter"
    return None


def is_title_page_candidate(el: etree._Element) -> bool:
    if tagu(el) == "TITLEPAGE":
        return True
    if not is_div(el):
        return False
    typ = normalized_type(el)
    if "verso" in typ or "omitted" in typ:
        return False
    return typ.startswith("titlepage") or typ.startswith("volumetitlepage")


def direct_head_text(el: etree._Element) -> str:
    for child in child_elements(el):
        if tagu(child) == "HEAD":
            return title_text(child)
    return ""


def element_path(el: etree._Element) -> str:
    parts: list[str] = []
    current: etree._Element | None = el
    while current is not None and isinstance(current.tag, str):
        label = tagu(current)
        typ = attr(current, "TYPE")
        n_value = attr(current, "N")
        qualifiers: list[str] = []
        if typ:
            qualifiers.append(f"TYPE={typ}")
        if n_value:
            qualifiers.append(f"N={n_value}")
        if qualifiers:
            label += "[" + ",".join(qualifiers) + "]"
        parts.append(label)
        current = current.getparent()
    return "/".join(reversed(parts))


def division_label(el: etree._Element) -> str:
    label = attr(el, "N") or direct_head_text(el) or title_text(el)
    return short_text(label or element_path(el), 120)


def part_day_ordinals(text: str) -> tuple[int, ...]:
    normalized = normalize_ordinal_text(text).casefold()
    day_map = {
        "die lune": 1,
        "lunae": 1,
        "martis": 2,
        "mercurij": 3,
        "mercurii": 3,
        "jovis": 4,
        "jouis": 4,
        "veneris": 5,
        "sabbato": 6,
        "dominica": 7,
    }
    for marker, ordinal in day_map.items():
        if marker in normalized:
            return (ordinal,)
    return ()


def division_ordinals(el: etree._Element, kind: str) -> tuple[int, ...]:
    n_value = attr(el, "N")
    ordinals = plausible_division_ordinals(parse_ordinals(n_value, allow_single_high=True), kind)
    if ordinals:
        return ordinals

    head = direct_head_text(el)
    ordinals = plausible_division_ordinals(labeled_ordinals(head, kind), kind)
    if ordinals:
        return ordinals

    if kind == "part":
        ordinals = plausible_division_ordinals(part_day_ordinals(head), kind)
        if ordinals:
            return ordinals

    # Some CME chapter headings are encoded as a combined ordinal heading rather
    # than with an N attribute, e.g. "fyfthe, vj, and vij".
    phrase = ordinal_phrase_at_start(head)
    if phrase:
        ordinals = plausible_division_ordinals(parse_ordinals(phrase), kind)
        if ordinals:
            return ordinals
    return ()


def body_nodes(root: etree._Element, fmt: str) -> Iterator[etree._Element]:
    for text_node in primary_text_nodes(root, fmt):
        bodies = child_elements(text_node, "BODY")
        if bodies:
            yield from bodies
        elif tagu(text_node) == "BODY":
            yield text_node


def front_nodes(root: etree._Element, fmt: str) -> Iterator[etree._Element]:
    for text_node in primary_text_nodes(root, fmt):
        yield from child_elements(text_node, "FRONT")


def nearest_part_ordinals(el: etree._Element) -> tuple[int, ...]:
    current = el.getparent()
    while current is not None and isinstance(current.tag, str):
        if division_kind(current) == "part":
            ordinals = division_ordinals(current, "part")
            if ordinals:
                return ordinals
        current = current.getparent()
    return ()


def iter_body_divisions(root: etree._Element, fmt: str) -> Iterator[BodyDivision]:
    def walk(el: etree._Element, in_contents: bool = False) -> Iterator[BodyDivision]:
        if not isinstance(el.tag, str):
            return
        current_is_contents = in_contents or is_contents_container(el)
        if not current_is_contents:
            kind = division_kind(el)
            if kind is not None:
                ordinals = division_ordinals(el, kind)
                if kind == "part" or ordinals:
                    yield BodyDivision(el, kind, ordinals)
        for child in child_elements(el):
            yield from walk(child, current_is_contents)

    for body in body_nodes(root, fmt):
        yield from walk(body)


def build_body_index(root: etree._Element, fmt: str) -> BodyIndex:
    parts: set[int] = set()
    chapters: set[int] = set()
    chapters_by_part: dict[int, set[int]] = defaultdict(set)
    has_part_divisions = False

    for division in iter_body_divisions(root, fmt):
        if division.kind == "part":
            has_part_divisions = True
            parts.update(division.ordinals)
        elif division.kind == "chapter":
            chapters.update(division.ordinals)
            part_ordinals = nearest_part_ordinals(division.element)
            for part in part_ordinals:
                chapters_by_part[part].update(division.ordinals)

    return BodyIndex(
        frozenset(parts),
        frozenset(chapters),
        {part: frozenset(values) for part, values in chapters_by_part.items()},
        has_part_divisions,
    )


def titlepart_is_part(el: etree._Element) -> bool:
    raw_type = (attr(el, "TYPE") or "").casefold()
    if "series" in raw_type:
        return False
    typ = normalized_type(el)
    text = title_text(el)
    return typ == "part" or bool(labeled_ordinals(text, "part", anchored=True))


def collect_front_part_expectations(root: etree._Element, fmt: str) -> tuple[FrontPartExpectation, ...]:
    expectations: list[FrontPartExpectation] = []
    for front in front_nodes(root, fmt):
        for el in front.iter():
            if not isinstance(el.tag, str) or tagu(el) != "TITLEPART":
                continue
            if not titlepart_is_part(el):
                continue
            label = title_text(el)
            ordinals = parse_ordinals(attr(el, "N"), allow_single_high=True) or labeled_ordinals(label, "part", anchored=True)
            for ordinal in ordinals:
                expectations.append(
                    FrontPartExpectation(
                        ordinal=ordinal,
                        label=label,
                        context=element_path(el),
                        line_ranges=line_ranges_from_text(label),
                    )
                )
    return tuple(expectations)


def collect_title_pages(root: etree._Element, fmt: str) -> tuple[TitlePageCandidate, ...]:
    candidates: list[TitlePageCandidate] = []
    seen: set[str] = set()
    for text_node in primary_text_nodes(root, fmt):
        for el in text_node.iter():
            if not isinstance(el.tag, str):
                continue
            key = el.getroottree().getpath(el)
            if key in seen:
                continue
            seen.add(key)
            if not is_title_page_candidate(el):
                continue
            candidates.append(
                TitlePageCandidate(
                    line=el.sourceline,
                    path=element_path(el),
                    tag=tagu(el),
                    type_value=attr(el, "TYPE") or "",
                    text=short_text(title_text(el), 90),
                )
            )
    return tuple(candidates)


def title_page_context(candidates: Sequence[TitlePageCandidate]) -> str:
    parts = [f"count={len(candidates)}"]
    shown = candidates[:8]
    for index, candidate in enumerate(shown, start=1):
        fields = [
            f"#{index}",
            f"line={candidate.line if candidate.line is not None else 'unknown'}",
            f"path={candidate.path}",
            f"tag={candidate.tag}",
        ]
        if candidate.type_value:
            fields.append(f"type={candidate.type_value}")
        if candidate.text:
            fields.append(f"text={candidate.text}")
        parts.append(" ".join(fields))
    if len(shown) < len(candidates):
        parts.append(f"(+{len(candidates) - len(shown)} more)")
    return "; ".join(parts)


def contents_indicator_text(el: etree._Element) -> str:
    return " ".join(part for part in [attr(el, "TYPE") or "", direct_head_text(el)] if part)


def is_contents_container(el: etree._Element) -> bool:
    tag = tagu(el)
    if tag in {"CONTENTS", "TOC"}:
        return True
    typ = normalized_type(el)
    if typ in {"contents", "content", "tableofcontents", "toc"}:
        return True
    if typ in {"part", "pt", "chapter", "chap", "cap", "capitulum"}:
        return False

    heading = normalize_field(direct_head_text(el)).casefold()
    return bool(
        re.fullmatch(
            r"(?:the\s+)?(?:table\s+of\s+contents|contents|list\s+of\s+contents|editor'?s\s+summary\s+of\s+contents)",
            heading,
            re.IGNORECASE,
        )
    )


def contents_containers(root: etree._Element, fmt: str) -> Iterator[etree._Element]:
    def walk(el: etree._Element) -> Iterator[etree._Element]:
        for child in child_elements(el):
            if is_contents_container(child):
                yield child
            else:
                yield from walk(child)

    for section in (*front_nodes(root, fmt), *body_nodes(root, fmt)):
        if is_contents_container(section):
            yield section
        else:
            yield from walk(section)


def collect_structured_toc_refs(container: etree._Element) -> tuple[TocRef, ...]:
    refs: list[TocRef] = []

    def walk(el: etree._Element, current_part: int | None) -> None:
        for child in child_elements(el):
            kind = division_kind(child)
            if kind == "part":
                ordinals = division_ordinals(child, "part")
                for ordinal in ordinals:
                    refs.append(
                        TocRef(
                            kind="part",
                            ordinal=ordinal,
                            label=division_label(child),
                            context=element_path(child),
                        )
                    )
                next_part = ordinals[0] if ordinals else current_part
                walk(child, next_part)
                continue
            if kind == "chapter":
                ordinals = division_ordinals(child, "chapter")
                for ordinal in ordinals:
                    refs.append(
                        TocRef(
                            kind="chapter",
                            ordinal=ordinal,
                            label=division_label(child),
                            context=element_path(child),
                            part_ordinal=current_part,
                        )
                    )
            walk(child, current_part)

    walk(container, None)
    return tuple(refs)


def inside_structured_toc_division(el: etree._Element, container: etree._Element) -> bool:
    current = el.getparent()
    while current is not None and current is not container and isinstance(current.tag, str):
        if division_kind(current) in SUPPORTED_DIVISION_KINDS:
            return True
        current = current.getparent()
    return False


def iter_unstructured_toc_items(container: etree._Element) -> Iterator[etree._Element]:
    for el in container.iter():
        if el is container or not isinstance(el.tag, str):
            continue
        if division_kind(el) in SUPPORTED_DIVISION_KINDS or inside_structured_toc_division(el, container):
            # Structured DIVs are handled separately; their prose children should
            # not be treated as independent contents rows.
            continue
        if tagu(el) in {"P", "ITEM", "ROW"}:
            yield el


def collect_unstructured_toc_refs(container: etree._Element) -> tuple[TocRef, ...]:
    refs: list[TocRef] = []
    current_part: int | None = None
    for item in iter_unstructured_toc_items(container):
        text = title_text(item)
        if not text:
            continue
        part_ordinals = labeled_ordinals(text, "part", anchored=False)
        if part_ordinals:
            current_part = part_ordinals[0]
            for ordinal in part_ordinals:
                refs.append(
                    TocRef(
                        kind="part",
                        ordinal=ordinal,
                        label=short_text(text),
                        context=element_path(item),
                    )
                )
            continue

        chapter_ordinals = labeled_ordinals(text, "chapter", anchored=False)
        if chapter_ordinals:
            for ordinal in chapter_ordinals:
                refs.append(
                    TocRef(
                        kind="chapter",
                        ordinal=ordinal,
                        label=short_text(text),
                        context=element_path(item),
                        part_ordinal=current_part,
                    )
                )
    return tuple(refs)


def collect_toc_refs(root: etree._Element, fmt: str) -> tuple[TocRef, ...]:
    refs: list[TocRef] = []
    seen: set[tuple[str, int, int | None, str]] = set()
    for container in contents_containers(root, fmt):
        for ref in (*collect_structured_toc_refs(container), *collect_unstructured_toc_refs(container)):
            key = (ref.kind, ref.ordinal, ref.part_ordinal, ref.context)
            if key not in seen:
                refs.append(ref)
                seen.add(key)
    return tuple(refs)


def audit_multiple_title_pages(state: AuditState, root: etree._Element) -> None:
    candidates = collect_title_pages(root, state.fmt)
    if len(candidates) <= 1:
        return
    state.add(
        "multiple_title_pages",
        "Multiple title-page-like elements were found in the source XML.",
        title_page_context(candidates),
    )


def audit_front_part_expectations(state: AuditState, root: etree._Element, body: BodyIndex) -> None:
    expectations = collect_front_part_expectations(root, state.fmt)
    expected = sorted({expectation.ordinal for expectation in expectations})
    if not expected:
        return

    # Be conservative for single-volume title pages: a lone "Part I" title page
    # often simply identifies the physical source part. Multi-part title pages,
    # or any mismatch when BODY already has part divisions, are structural cues.
    if len(expected) < 2 and not body.parts:
        return

    missing = [ordinal for ordinal in expected if ordinal not in body.parts]
    if not missing:
        return

    ranges = [f"{start}-{end}" for expectation in expectations for start, end in expectation.line_ranges]
    context_parts = [
        f"front_parts={format_numbers(expected)}",
        f"body_parts={format_numbers(sorted(body.parts))}",
        f"missing={format_numbers(missing)}",
    ]
    if ranges:
        context_parts.append(f"referenced_line_ranges={','.join(ranges)}")
    state.add(
        "front_parts_not_represented_in_body",
        "Front/titlepage part expectations are not represented by BODY part divisions.",
        "; ".join(context_parts),
    )


def audit_toc_refs(state: AuditState, root: etree._Element, body: BodyIndex) -> None:
    seen_missing: set[tuple[str, int, int | None]] = set()
    for ref in collect_toc_refs(root, state.fmt):
        if ref.kind == "part":
            if ref.ordinal in body.parts or (not body.parts and body.has_part_divisions):
                continue
            key = (ref.kind, ref.ordinal, None)
            if key in seen_missing:
                continue
            seen_missing.add(key)
            state.add(
                "toc_part_missing_from_body",
                f"Contents references part {ref.ordinal}, but no matching BODY part division was found.",
                f"toc={ref.context}; label={ref.label}; body_parts={format_numbers(sorted(body.parts))}",
            )
            continue

        if ref.kind == "chapter":
            scoped_body_chapters = None
            if ref.part_ordinal is not None and body.parts:
                scoped_body_chapters = body.chapters_by_part.get(ref.part_ordinal, frozenset())
            candidates = scoped_body_chapters if scoped_body_chapters is not None else body.chapters
            if ref.ordinal in candidates:
                continue
            key = (ref.kind, ref.ordinal, ref.part_ordinal if scoped_body_chapters is not None else None)
            if key in seen_missing:
                continue
            seen_missing.add(key)
            scope = f"part={ref.part_ordinal}; " if scoped_body_chapters is not None else ""
            state.add(
                "toc_chapter_missing_from_body",
                f"Contents references chapter {ref.ordinal}, but no matching BODY chapter division was found.",
                f"{scope}toc={ref.context}; label={ref.label}; body_chapters={format_numbers(sorted(candidates))}",
            )


def audit_body_sequence_gaps(state: AuditState, root: etree._Element) -> None:
    def check_parent(parent: etree._Element) -> None:
        if is_contents_container(parent):
            return
        div_children = [child for child in child_elements(parent) if is_div(child) and not is_contents_container(child)]
        for kind in ("part", "chapter"):
            previous_max: int | None = None
            previous_label = ""
            for child in div_children:
                if division_kind(child) != kind:
                    continue
                ordinals = sorted(set(division_ordinals(child, kind)))
                if not ordinals:
                    continue
                current_min = ordinals[0]
                current_max = ordinals[-1]
                if previous_max is not None and current_min > previous_max + 1:
                    missing = tuple(range(previous_max + 1, current_min))
                    if len(missing) <= MAX_SEQUENCE_GAP_SIZE:
                        state.add(
                            f"body_{kind}_sequence_gap",
                            f"BODY {kind} sequence jumps from {previous_max} to {current_min} among sibling divisions.",
                            (
                                f"parent={element_path(parent)}; previous={previous_label}; "
                                f"current={division_label(child)}; missing={format_numbers(missing)}"
                            ),
                        )
                previous_max = current_max if previous_max is None else max(previous_max, current_max)
                previous_label = division_label(child)

        for child in div_children:
            check_parent(child)

    for body in body_nodes(root, state.fmt):
        check_parent(body)


def audit_file(path: Path) -> list[Issue]:
    parsed = parse_xml(path)
    fmt = detect_format(parsed.root)
    if fmt == "headwords":
        return []

    state = AuditState(path, fmt, [])
    body = build_body_index(parsed.root, fmt)
    audit_multiple_title_pages(state, parsed.root)
    audit_front_part_expectations(state, parsed.root, body)
    audit_toc_refs(state, parsed.root, body)
    audit_body_sequence_gaps(state, parsed.root)
    return state.issues


def iter_sources(root: Path) -> tuple[Path, ...]:
    if root.is_file():
        return (root,)
    if root.is_dir():
        return tuple(sorted(root.rglob("*.xml")))
    raise SystemExit(f"Path not found: {root}")


def audit_sources(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path in iter_sources(root):
        issues.extend(audit_file(path))
    return issues


def write_report(issues: Sequence[Issue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=ISSUE_FIELDS)
        writer.writeheader()
        for issue in issues:
            writer.writerow(
                {
                    "source": issue.source,
                    "format": issue.format,
                    "code": issue.code,
                    "message": issue.message,
                    "context": issue.context,
                }
            )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("CME/source"), help="CME XML file or directory")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("build/cme-contents-audit/contents.tsv"),
        help="write TSV report to this path",
    )
    parser.add_argument("--allow-issues", action="store_true", help="exit 0 even when audit issues are found")
    parser.add_argument("--allow-empty", action="store_true", help="succeed when the input directory contains no XML files")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    sources = iter_sources(args.root)
    if not sources and not args.allow_empty:
        raise SystemExit(f"No XML files found under: {args.root}")

    issues: list[Issue] = []
    for source in sources:
        issues.extend(audit_file(source))

    write_report(issues, args.report)
    if issues and not args.allow_issues:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
