#!/usr/bin/env python3
"""Convert the CME TEI-inspired XML variants to HTML for Pandoc.

This is intentionally conservative: it keeps the readable text, major
structure, headings, verse lines, lists, tables, notes, and simple inline
formatting, while ignoring transport/page-break markup by default.  The shell
wrappers in this directory pipe this HTML into pandoc for the desired output
format.
"""

from __future__ import annotations

import argparse
import copy
import re
import sys
import unicodedata
from dataclasses import dataclass
from html import escape, unescape
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from lxml import etree


RECOVERING_PARSER = etree.XMLParser(
    recover=True,
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    huge_tree=True,
)
STRICT_PARSER = etree.XMLParser(
    recover=False,
    resolve_entities=False,
    no_network=True,
    load_dtd=False,
    huge_tree=True,
)

FORMATS = {
    "auto",
    "dlpstextclass",
    "ets",
    "ets-temphead-eebo",
    "ets-header-eebo",
    "tei2",
    "headwords",
}

MILESTONE_TAGS = {"PB", "EPB", "MILESTONE", "FW"}
NOTE_TAG_RE = re.compile(r"^NOTE\d*$")
DIV_TAG_RE = re.compile(r"^DIV\d*$")
HTML_TAG_RE = re.compile(r"<[^>]+>")
NUMERIC_LINE_NUMBER_RE = re.compile(r"^\d+$")
NUMERIC_OR_ROMAN_TITLE_RE = re.compile(r"^(?:\d+|[ivxlcdm]+)\.?$", re.IGNORECASE)
STANZA_HEAD_MARKER_PREFIX_RE = re.compile(
    r"""
    ^\s*
    [\[({]?\s*\*?\s*
    (?:\d+[a-z]?|[ivxlcdm]+)
    (?=\s*(?:[\])}.,;:—–-]|\(|$))
    \s*[\])}.]?
    (?:\s*\(\s*(?:\d+[a-z]?|[ivxlcdm]+)\s*\)\s*[\])}.]?)?
    """,
    re.IGNORECASE | re.VERBOSE,
)
GENERATED_FALLBACK_HEADING_CLASSES = [
    "structural-fallback-heading",
    "nonrunning",
    "unlisted",
    "unnumbered",
]
STANZA_HEADING_CLASSES = [
    "stanza-head",
    "nonrunning",
    "unlisted",
    "unnumbered",
]


@dataclass(frozen=True)
class Options:
    include_notes: bool = True
    preserve_milestones: bool = False
    include_source_metadata: bool = True
    include_verse_line_metadata: bool = False


@dataclass(frozen=True)
class ParsedXml:
    root: etree._Element
    recovered: bool
    errors: tuple[str, ...]


def local_name(node_or_name: etree._Element | str) -> str:
    name = node_or_name.tag if hasattr(node_or_name, "tag") else str(node_or_name)
    if not isinstance(name, str):
        return ""
    try:
        return etree.QName(name).localname
    except ValueError:
        return name.split("}", 1)[-1]


def tagu(el: etree._Element) -> str:
    return local_name(el).upper()


def attr(el: etree._Element, *names: str) -> str | None:
    wanted = {name.upper() for name in names}
    for key, value in el.attrib.items():
        if local_name(key).upper() in wanted:
            return value
    return None


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.split())


def text_content(el: etree._Element | None) -> str:
    if el is None:
        return ""
    return clean_text("".join(el.itertext()))


def text_content_excluding_notes(el: etree._Element | None) -> str:
    if el is None:
        return ""
    parts: list[str] = []

    def walk(node: etree._Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in child_elements(node):
            if not NOTE_TAG_RE.match(tagu(child)):
                walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(el)
    return clean_text("".join(parts))


def spaced_text_content(el: etree._Element | None) -> str:
    """Extract text while inserting spaces between adjacent XML elements.

    Some compact lexical records encode alternatives as adjacent inline tags
    with no tail text.  Joining itertext verbatim creates very long unbreakable
    strings in LaTeX; inserting separators produces readable, wrappable text.
    """
    if el is None:
        return ""
    parts: list[str] = []

    def append(value: str | None) -> None:
        if value:
            parts.append(value)

    def need_space() -> bool:
        if not parts:
            return False
        return not parts[-1].endswith((" ", "\n", "\t", "(", "[", "{", "/", "-"))

    def walk(node: etree._Element) -> None:
        append(node.text)
        for child in child_elements(node):
            if need_space():
                parts.append(" ")
            walk(child)
            if child.tail:
                append(child.tail)
            elif need_space():
                parts.append(" ")

    walk(el)
    value = clean_text("".join(parts))
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"([([{])\s+", r"\1", value)
    return value


def html_text(text: str | None) -> str:
    # Pilcrows are source paragraph markers, not output glyphs.  Block renderers
    # split on them before escaping; this fallback prevents any unhandled marker
    # from leaking into visible text.
    return escape((text or "").replace("¶", " "), quote=False)


def has_visible_html(fragment: str) -> bool:
    """Return true when rendered inline HTML contains visible text.

    Suppressed milestones/page breaks can leave a verse line with only
    whitespace or empty markup.  Those lines should not create blank output
    lines when milestone display is disabled.
    """
    text = unescape(HTML_TAG_RE.sub("", fragment)).replace("\xa0", " ")
    return bool(text.strip())


def html_attr(value: str | None) -> str:
    return escape(value or "", quote=True)


def safe_numeric_line_number(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not NUMERIC_LINE_NUMBER_RE.match(stripped):
        return None
    number = int(stripped)
    if number <= 0:
        return None
    return str(number)


def milestone_unit_indicates_page_marker(el: etree._Element) -> bool:
    unit = (attr(el, "UNIT") or "").strip().lower()
    if not unit:
        return False
    normalized = re.sub(r"[^a-z0-9]+", "", unit)
    if any(marker in normalized for marker in ("page", "folio", "leaf", "column")):
        return True
    return normalized in {
        "pb",
        "epb",
        "fol",
        "f",
        "col",
        "cols",
        "sig",
        "signature",
        "quire",
        "sheet",
    }


def child_elements(el: etree._Element, name: str | None = None) -> list[etree._Element]:
    children = [child for child in el if isinstance(child.tag, str)]
    if name is None:
        return children
    name_u = name.upper()
    return [child for child in children if tagu(child) == name_u]


def first_child(el: etree._Element, name: str) -> etree._Element | None:
    matches = child_elements(el, name)
    return matches[0] if matches else None


def first_path(root: etree._Element, path: Sequence[str]) -> etree._Element | None:
    current = root
    for part in path:
        current = first_child(current, part)
        if current is None:
            return None
    return current


def first_descendant(root: etree._Element, *names: str) -> etree._Element | None:
    wanted = {name.upper() for name in names}
    for el in root.iter():
        if isinstance(el.tag, str) and tagu(el) in wanted:
            return el
    return None


def parse_xml(path: Path) -> ParsedXml:
    data = path.read_bytes()
    try:
        return ParsedXml(etree.fromstring(data, STRICT_PARSER), False, ())
    except etree.XMLSyntaxError as exc:
        errors = tuple(str(entry) for entry in exc.error_log[:8])
        return ParsedXml(etree.fromstring(data, RECOVERING_PARSER), True, errors)


def detect_format(root: etree._Element) -> str:
    root_tag = tagu(root)
    if root_tag == "DLPSTEXTCLASS":
        return "dlpstextclass"
    if root_tag == "TEI.2":
        return "tei2"
    if root_tag == "HEADWORDS":
        return "headwords"
    if root_tag == "ETS":
        direct = [tagu(child) for child in child_elements(root)]
        if direct[:2] == ["TEMPHEAD", "EEBO"]:
            return "ets-temphead-eebo"
        if direct[:2] == ["HEADER", "EEBO"]:
            return "ets-header-eebo"
        return "ets"
    return "unknown"


def require_format(requested: str, detected: str, path: Path) -> None:
    if requested == "auto":
        if detected == "unknown":
            raise SystemExit(f"{path}: unrecognized XML root; not a supported CME format")
        return
    if requested == "ets" and detected.startswith("ets"):
        return
    if requested != detected:
        raise SystemExit(
            f"{path}: expected format {requested!r}, but detected {detected!r}"
        )


def primary_text_nodes(root: etree._Element, fmt: str) -> list[etree._Element]:
    """Return top-level textual payload nodes without falling back to metadata.

    Malformed or reduced fixtures occasionally omit the format's expected
    ``TEXT``/``EEBO`` wrapper.  In those shapes, rendering no body is safer than
    treating the document root (and therefore headers or revision metadata) as
    primary text.  A direct ``BODY`` remains a narrow, unambiguous fallback.
    """
    if fmt == "dlpstextclass" or fmt == "tei2":
        text = first_child(root, "TEXT")
        if text is not None:
            return [text]
        body = first_child(root, "BODY")
        return [body] if body is not None else []

    if fmt.startswith("ets"):
        eebo = first_child(root, "EEBO")
        if eebo is None:
            text = first_child(root, "TEXT")
            if text is not None:
                return [text]
            body = first_child(root, "BODY")
            return [body] if body is not None else []
        nodes: list[etree._Element] = []
        for child in child_elements(eebo):
            child_tag = tagu(child)
            if child_tag == "TEXT":
                nodes.append(child)
            elif child_tag == "GROUP":
                nodes.extend(child_elements(child, "TEXT"))
        if nodes:
            return nodes
        body = first_child(eebo, "BODY")
        return [body] if body is not None else []

    return [root]


def title_text(el: etree._Element | None) -> str:
    if el is None:
        return ""
    value = spaced_text_content(el)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    return value.strip()


def heading_title_text(el: etree._Element | None) -> str:
    if el is None:
        return ""
    value = text_content_excluding_notes(el)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    return value.strip()


def clean_title(value: str | None) -> str:
    value = clean_text((value or "").replace("¶", " — "))
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    return re.sub(r"\s*[:/]\s*$", "", value).strip()


def title_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_title(value).casefold())


def same_title(left: str | None, right: str | None) -> bool:
    return bool(title_key(left)) and title_key(left) == title_key(right)


def title_is_numeric_only(value: str | None) -> bool:
    cleaned = clean_title(value)
    cleaned = re.sub(r"^[\[({]+|[\])}.]+$", "", cleaned).strip()
    return bool(cleaned and NUMERIC_OR_ROMAN_TITLE_RE.fullmatch(cleaned))


def title_candidate_is_meaningful(value: str | None) -> bool:
    return bool(title_key(value)) and not title_is_numeric_only(value)


def remove_author_from_title(title: str, author: str | None) -> str:
    if not author:
        return title
    pattern = re.compile(r"\s*/\s*" + re.escape(clean_text(author)) + r"\s*$", re.IGNORECASE)
    return clean_title(pattern.sub("", title))


def unique_title_parts(parts: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for part in parts:
        cleaned = clean_title(part)
        key = title_key(cleaned)
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result


def normalized_marker(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").casefold())


def marker_is_titlepage_like(marker: str) -> bool:
    return "titlepage" in marker


def source_titlepage_title_parts(el: etree._Element) -> list[str]:
    doctitle = first_descendant(el, "DOCTITLE")
    if doctitle is not None:
        parts = [title_text(part) for part in child_elements(doctitle, "TITLEPART")]
        parts = unique_title_parts(parts)
        if parts:
            return parts
        doctitle_text = title_text(doctitle)
        if doctitle_text:
            return [doctitle_text]

    heading_parts = unique_title_parts(
        title_text(child) for child in child_elements(el) if tagu(child) == "HEAD"
    )
    if heading_parts:
        return heading_parts

    for child in child_elements(el):
        if tagu(child) in {"P", "L"}:
            paragraph_text = title_text(child)
            if paragraph_text:
                return [paragraph_text]
    return []


def titlepage_title_parts(root: etree._Element, fmt: str) -> list[str]:
    for text_node in primary_text_nodes(root, fmt):
        containers: list[etree._Element] = []
        for name in ("FRONT", "BODY"):
            container = first_child(text_node, name)
            if container is not None:
                containers.append(container)
        if not containers:
            containers.append(text_node)

        for container in containers:
            for child in child_elements(container):
                child_tag = tagu(child)
                if child_tag in MILESTONE_TAGS:
                    continue
                marker = normalized_marker(attr(child, "TYPE"))
                if child_tag == "TITLEPAGE" or marker_is_titlepage_like(marker):
                    parts = source_titlepage_title_parts(child)
                    if parts:
                        return parts
                break
    return []


def looks_like_incipit(value: str) -> bool:
    lowered = value.strip().casefold()
    return lowered.startswith(("here begynneth", "here beginneth", "here begins", "here bygynneth"))


def initial_body_heading_parts(root: etree._Element, fmt: str) -> list[str]:
    for text_node in primary_text_nodes(root, fmt):
        body = first_child(text_node, "BODY")
        container = body if body is not None else text_node
        current = container
        for _ in range(8):
            children = [child for child in child_elements(current) if tagu(child) not in MILESTONE_TAGS]
            if not children:
                break

            heading_parts: list[str] = []
            for child in children:
                if tagu(child) != "HEAD":
                    break
                candidate = heading_title_text(child)
                if title_candidate_is_meaningful(candidate):
                    heading_parts.append(candidate)
            if heading_parts:
                return unique_title_parts(heading_parts)

            first = children[0]
            if DIV_TAG_RE.match(tagu(first)) or tagu(first) == "DIV":
                current = first
                continue
            break
    return []


def body_title_supplements(root: etree._Element, fmt: str, title: str) -> list[str]:
    supplements: list[str] = []
    initial_headings = initial_body_heading_parts(root, fmt)
    if initial_headings and same_title(initial_headings[0], title):
        supplements.extend(initial_headings[1:])

    for text_node in primary_text_nodes(root, fmt):
        container = first_child(text_node, "BODY")
        if container is None:
            container = text_node
        children = [child for child in child_elements(container) if tagu(child) not in MILESTONE_TAGS]
        index = 0
        while index < len(children) and tagu(children[index]) == "HEAD":
            head_text = heading_title_text(children[index])
            if title_candidate_is_meaningful(head_text) and not same_title(head_text, title):
                supplements.append(head_text)
            index += 1
        if index >= len(children):
            break

        first = children[index]
        if not (DIV_TAG_RE.match(tagu(first)) or tagu(first) == "DIV"):
            break

        div_children = [child for child in child_elements(first) if tagu(child) not in MILESTONE_TAGS]
        if not div_children or tagu(div_children[0]) != "HEAD":
            break

        div_title = heading_title_text(div_children[0])
        if not same_title(div_title, title):
            break

        for child in div_children[1:]:
            child_tag = tagu(child)
            if child_tag == "HEAD" and (attr(child, "TYPE") or "").lower() in {"sub", "subtitle", "subsubtitle", "sub-subtitle"}:
                subtitle = heading_title_text(child)
                if title_candidate_is_meaningful(subtitle):
                    supplements.append(subtitle)
            elif child_tag == "OPENER":
                opener_text = title_text(child)
                if looks_like_incipit(opener_text):
                    supplements.append(opener_text)
                break
            else:
                break
        break
    return unique_title_parts(supplements)


def apply_display_title_metadata(root: etree._Element, fmt: str, data: dict[str, str]) -> None:
    title_parts = titlepage_title_parts(root, fmt)
    if title_parts:
        data["title"] = title_parts[0]
        subtitles = title_parts[1:]
    else:
        data["title"] = remove_author_from_title(clean_title(data.get("title")), data.get("author"))
        subtitles = body_title_supplements(root, fmt, data["title"])

    if subtitles:
        data["subtitle"] = " — ".join(subtitles)
        data["full_title"] = f"{data['title']} — {data['subtitle']}"
    else:
        data.pop("subtitle", None)
        data["full_title"] = data["title"]


def metadata(root: etree._Element, fmt: str, source: Path, parsed: ParsedXml) -> dict[str, str]:
    data: dict[str, str] = {
        "source": str(source),
        "format": fmt,
    }
    if parsed.recovered:
        data["xml_recovered"] = "true"

    candidates: dict[str, list[Sequence[str]]] = {
        "title": [
            ("HEADER", "FILEDESC", "TITLESTMT", "TITLE"),
            ("TEIHEADER", "FILEDESC", "TITLESTMT", "TITLE"),
            ("HEADER", "FILEDESC", "SOURCEDESC", "BIBLFULL", "TITLESTMT", "TITLE"),
        ],
        "author": [
            ("HEADER", "FILEDESC", "TITLESTMT", "AUTHOR"),
            ("TEIHEADER", "FILEDESC", "TITLESTMT", "AUTHOR"),
            ("HEADER", "FILEDESC", "SOURCEDESC", "BIBLFULL", "TITLESTMT", "AUTHOR"),
        ],
        "original_date": [
            ("HEADER", "PROFILEDESC", "CREATION", "DATE"),
            ("TEIHEADER", "PROFILEDESC", "CREATION", "DATE"),
        ],
        "editor": [
            ("HEADER", "FILEDESC", "TITLESTMT", "EDITOR"),
            ("TEIHEADER", "FILEDESC", "TITLESTMT", "EDITOR"),
            ("HEADER", "FILEDESC", "SOURCEDESC", "BIBLFULL", "TITLESTMT", "EDITOR"),
        ],
        "date": [
            ("HEADER", "FILEDESC", "PUBLICATIONSTMT", "DATE"),
            ("TEIHEADER", "FILEDESC", "PUBLICATIONSTMT", "DATE"),
        ],
        "id": [
            ("HEADER", "FILEDESC", "PUBLICATIONSTMT", "IDNO"),
            ("TEIHEADER", "FILEDESC", "PUBLICATIONSTMT", "IDNO"),
            ("EEBO", "IDG", "BIBNO"),
            ("EEBO", "IDG", "VID"),
        ],
    }

    for key, paths in candidates.items():
        for path in paths:
            value = text_content(first_path(root, path))
            if value:
                data[key] = value
                break

    if "title" not in data:
        for text_node in primary_text_nodes(root, fmt):
            for tag in ("DOCTITLE", "TITLEPART", "HEAD", "P"):
                tag_name = tag.upper()
                saw_candidates_for_tag = False
                for element in text_node.iter():
                    if not isinstance(element.tag, str) or tagu(element) != tag_name:
                        continue
                    if element_is_inside_note(element):
                        continue
                    saw_candidates_for_tag = True
                    candidate = text_content_excluding_notes(element) or text_content(element)
                    if title_candidate_is_meaningful(candidate):
                        data["title"] = candidate
                        break
                if "title" in data:
                    break
                if tag == "HEAD" and saw_candidates_for_tag:
                    break
            if "title" in data:
                break

    if "id" not in data:
        vid = first_descendant(root, "VID", "BIBNO", "IDNO")
        value = text_content(vid)
        if value:
            data["id"] = value

    data.setdefault("title", source.stem)
    apply_display_title_metadata(root, fmt, data)
    return data


def element_is_inside_note(el: etree._Element) -> bool:
    current = el.getparent()
    while current is not None and isinstance(current.tag, str):
        if NOTE_TAG_RE.match(tagu(current)):
            return True
        current = current.getparent()
    return False


def element_is_in_front_matter(el: etree._Element) -> bool:
    current: etree._Element | None = el
    while current is not None and isinstance(current.tag, str):
        name = tagu(current)
        if name == "FRONT":
            return True
        if name == "BODY":
            return False
        current = current.getparent()
    return False


def element_is_in_front_or_back_matter(el: etree._Element) -> bool:
    current: etree._Element | None = el
    while current is not None and isinstance(current.tag, str):
        name = tagu(current)
        if name in {"FRONT", "BACK"}:
            return True
        if name == "BODY":
            return False
        current = current.getparent()
    return False


def marker_is_contents_like(marker: str) -> bool:
    return marker in {"toc", "content"} or "contents" in marker


def marker_is_omitted_apparatus(marker: str) -> bool:
    return "omitted" in marker


def source_apparatus_classes(el: etree._Element) -> list[str]:
    titlepage_like = False
    contents_like = False
    omitted_apparatus = False
    current: etree._Element | None = el
    while current is not None and isinstance(current.tag, str):
        marker = normalized_marker(attr(current, "TYPE"))
        in_front_matter = element_is_in_front_matter(current)
        front_title_like = marker == "title" and in_front_matter
        front_half_title_like = marker in {"halftitle", "halftitles"} and in_front_matter
        titlepage_like = (
            titlepage_like
            or tagu(current) == "TITLEPAGE"
            or marker_is_titlepage_like(marker)
            or front_title_like
            or front_half_title_like
        )
        contents_like = contents_like or marker_is_contents_like(marker)
        omitted_apparatus = omitted_apparatus or (
            marker_is_omitted_apparatus(marker) and element_is_in_front_or_back_matter(current)
        )
        if titlepage_like or contents_like or omitted_apparatus:
            break
        current = current.getparent()
    if not (titlepage_like or contents_like or omitted_apparatus):
        return []
    classes = ["source-apparatus", "nonrunning", "unlisted", "unnumbered"]
    if titlepage_like:
        classes.append("source-titlepage")
    if contents_like:
        classes.append("source-contents")
    if omitted_apparatus:
        classes.append("source-omitted-apparatus")
    return classes


def element_is_direct_child_of(el: etree._Element, parent_tag: str) -> bool:
    parent = el.getparent()
    return (
        parent is not None
        and isinstance(parent.tag, str)
        and tagu(parent) == parent_tag.upper()
    )


def heading_text_has_stanza_marker_prefix(value: str | None) -> bool:
    cleaned = clean_title(value)
    if not cleaned:
        return False
    match = STANZA_HEAD_MARKER_PREFIX_RE.match(cleaned)
    if not match:
        return False
    # Inside an ``LG``, a heading with an initial numeric/roman stanza marker is
    # local source apparatus even when it carries a longer editorial gloss.
    return True


def stanza_heading_classes(el: etree._Element, heading_text: str | None = None) -> list[str]:
    if tagu(el) != "HEAD" or not element_is_direct_child_of(el, "LG"):
        return []
    text = heading_text if heading_text is not None else heading_title_text(el)
    if not heading_text_has_stanza_marker_prefix(text):
        return []
    return list(STANZA_HEADING_CLASSES)


def join_classes(*groups: str | Sequence[str] | None) -> str | None:
    classes: list[str] = []
    for group in groups:
        if not group:
            continue
        if isinstance(group, str):
            candidates = group.split()
        else:
            candidates = list(group)
        for candidate in candidates:
            if candidate and candidate not in classes:
                classes.append(candidate)
    return " ".join(classes) if classes else None


def render_heading_attrs(
    el: etree._Element,
    classes: Sequence[str],
    *,
    preserve_attrs: bool = True,
) -> str:
    class_value = join_classes(classes)
    if preserve_attrs:
        return render_attrs(el, class_value)
    pairs: list[tuple[str, str]] = []
    if class_value:
        pairs.append(("class", class_value))
    type_value = attr(el, "TYPE")
    if type_value:
        pairs.append(("data-type", type_value))
    return "".join(f' {name}="{html_attr(value)}"' for name, value in pairs)


def render_attrs(
    el: etree._Element,
    css_class: str | None = None,
    *,
    skip_xml_names: set[str] | None = None,
) -> str:
    pairs: list[tuple[str, str]] = []
    skipped = skip_xml_names or set()
    if css_class:
        pairs.append(("class", css_class))
    for xml_name, html_name in (
        ("ID", "id"),
        ("TYPE", "data-type"),
        ("N", "data-n"),
        ("NODE", "data-node"),
        ("LANG", "lang"),
        ("REND", "data-rend"),
    ):
        if xml_name in skipped:
            continue
        value = attr(el, xml_name)
        if value:
            if html_name == "id" and not re.match(r"^[A-Za-z][-A-Za-z0-9_:.]*$", value):
                html_name = "data-id"
            pairs.append((html_name, value))
    return "".join(f' {name}="{html_attr(value)}"' for name, value in pairs)


def source_line_number_for_verse_line(el: etree._Element) -> str | None:
    line_number = safe_numeric_line_number(attr(el, "N"))
    if line_number:
        return line_number
    for child in child_elements(el, "MILESTONE"):
        if milestone_unit_indicates_page_marker(child):
            continue
        line_number = safe_numeric_line_number(attr(child, "N"))
        if line_number:
            return line_number
    return None


def render_verse_line_attrs(
    el: etree._Element,
    opts: Options,
    css_class: str | None = None,
) -> str:
    rendered = render_attrs(el, css_class, skip_xml_names={"N"})
    if opts.include_verse_line_metadata:
        line_number = source_line_number_for_verse_line(el)
        if line_number:
            rendered += f' data-line-number="{html_attr(line_number)}"'
    return rendered


def render_verse_line_span(segment: str, line_number: str | None, opts: Options) -> str:
    if not opts.include_verse_line_metadata:
        return segment.strip()
    attrs = ' class="verse-line"'
    if line_number:
        attrs += f' data-line-number="{html_attr(line_number)}"'
    return f"<span{attrs}>{segment.strip()}</span>"


@dataclass(frozen=True)
class VerseLineFragment:
    segment: str
    line_number: str | None


@dataclass(frozen=True)
class RawVerseFragment:
    segment: str


VerseFragment = VerseLineFragment | RawVerseFragment


def is_wrapped_l_continuation(el: etree._Element) -> bool:
    """Return true for source-wrapped verse continuation lines.

    In Gawain and similar line groups, exact-four-space unnumbered ``<L>``
    entries are source-text wraps of the previous intended line, while two-space
    wheel lines, six-space motto/display lines, and explicitly numbered lines
    are intentional separate lines.
    """
    if tagu(el) != "L":
        return False
    if source_line_number_for_verse_line(el) is not None:
        return False
    return bool(re.match(r"^ {4}(?! )", el.text or ""))


def strip_wrapped_continuation_indent(segment: str) -> str:
    return re.sub(r"^[ \t\r\n]+", "", segment)


def join_inline_continuation(base: str, continuation: str) -> str:
    base = base.rstrip()
    continuation = strip_wrapped_continuation_indent(continuation)
    if not base:
        return continuation
    if not continuation:
        return base
    no_space_after = "([{«“‘"
    no_space_before = ",.;:!?)]}»”’"
    separator = "" if base[-1] in no_space_after or continuation[0] in no_space_before else " "
    return f"{base}{separator}{continuation}"


def render_verse_fragment(fragment: VerseFragment, opts: Options) -> str:
    if isinstance(fragment, VerseLineFragment):
        return render_verse_line_span(fragment.segment, fragment.line_number, opts)
    return fragment.segment


def render_children(
    el: etree._Element,
    opts: Options,
    *,
    skip_first_head: bool = False,
) -> str:
    parts: list[str] = []
    skipped_head = False
    if el.text:
        parts.append(html_text(el.text))
    for child in child_elements(el):
        if skip_first_head and not skipped_head and tagu(child) == "HEAD":
            skipped_head = True
            if child.tail:
                parts.append(html_text(child.tail))
            continue
        parts.append(render_node(child, opts))
        if child.tail:
            parts.append(html_text(child.tail))
    return "".join(parts)


BLOCK_TAGS = {
    "TEXT",
    "BODY",
    "FRONT",
    "BACK",
    "GROUP",
    "DIV",
    "P",
    "AB",
    "HEAD",
    "DOCTITLE",
    "TITLEPAGE",
    "TITLEPART",
    "BYLINE",
    "DOCIMPRINT",
    "OPENER",
    "CLOSER",
    "SIGNED",
    "SALUTE",
    "TRAILER",
    "DATELINE",
    "HEADNOTE",
    "ARGUMENT",
    "EPIGRAPH",
    "LG",
    "L",
    "LIST",
    "CASTLIST",
    "ITEM",
    "CASTITEM",
    "TABLE",
    "ROW",
    "CELL",
    "SP",
    "SPEAKER",
    "STAGE",
    "DIRECTION",
    "FIGURE",
}
QUOTE_TAGS = {"Q", "Q1", "QUOTE", "SAID"}


def is_block_tag_name(tag: str) -> bool:
    return bool(DIV_TAG_RE.match(tag)) or tag in BLOCK_TAGS


def is_block_element(el: etree._Element) -> bool:
    tag = tagu(el)
    return is_block_tag_name(tag) or (tag in QUOTE_TAGS and has_block_child(el))


def has_block_child(el: etree._Element) -> bool:
    return any(is_block_element(child) for child in child_elements(el))


PAYLOAD_HAS_WORD_BREAK_VERBAR = etree.XPath(
    "boolean(.//text()[contains(., '∣')])"
)


def payload_has_word_break_verbar(nodes: Iterable[etree._Element]) -> bool:
    """Return whether selected rendered payload text contains U+2223."""
    return any(PAYLOAD_HAS_WORD_BREAK_VERBAR(node) for node in nodes)


def normalize_word_break_verbars(
    nodes: Iterable[etree._Element],
    opts: Options,
    fmt: str,
) -> set[etree._Element]:
    """Remove transcriptional U+2223 word-break markers from rendered flows.

    A marker is removed only when its immediately adjacent visible characters
    are both Unicode alphabetic characters.  Ordinary inline elements do not
    interrupt adjacency.  Blocks, explicit line breaks, lexical ENTRY/FORM
    units, notes, gaps, and milestones do: the latter wrappers either render a
    bracketed label or are deliberately suppressed, so their source text must
    never provide adjacency for the surrounding flow.  Included note content
    is normalized independently.
    """

    changed_nodes: set[etree._Element] = set()
    for node in nodes:
        flow: list[tuple[etree._Element, str]] = []

        def flush() -> None:
            if not flow:
                return
            if not any("∣" in (getattr(owner, field) or "") for owner, field in flow):
                flow.clear()
                return
            values = [getattr(owner, field) or "" for owner, field in flow]
            combined = "".join(values)

            def alphabetic_before(index: int) -> bool:
                index -= 1
                while index >= 0 and unicodedata.category(combined[index]).startswith("M"):
                    index -= 1
                return index >= 0 and combined[index].isalpha()

            remove_at = {
                index
                for index, char in enumerate(combined)
                if char == "∣"
                and alphabetic_before(index)
                and index + 1 < len(combined)
                and combined[index + 1].isalpha()
            }
            if remove_at:
                offset = 0
                for (owner, field), value in zip(flow, values):
                    normalized = "".join(
                        char
                        for local_index, char in enumerate(value)
                        if offset + local_index not in remove_at
                    )
                    if normalized != value:
                        setattr(owner, field, normalized)
                        changed_nodes.add(owner)
                    offset += len(value)
            flow.clear()

        def append(owner: etree._Element, field: str) -> None:
            if getattr(owner, field):
                flow.append((owner, field))

        def walk(container: etree._Element) -> None:
            append(container, "text")
            for child in container:
                if not isinstance(child.tag, str):
                    continue
                child_tag = local_name(child.tag).upper()
                is_special_boundary = (
                    child_tag == "GAP"
                    or child_tag in MILESTONE_TAGS
                    or bool(NOTE_TAG_RE.match(child_tag))
                )
                is_headword_boundary = fmt == "headwords" and child_tag in {
                    "ENTRY",
                    "FORM",
                }
                if (
                    child_tag == "LB"
                    or is_block_tag_name(child_tag)
                    or has_block_child(child)
                    or is_special_boundary
                    or is_headword_boundary
                ):
                    flush()
                    if not is_special_boundary or (
                        NOTE_TAG_RE.match(child_tag) and opts.include_notes
                    ):
                        walk(child)
                    flush()
                else:
                    walk(child)
                append(child, "tail")

        walk(node)
        flush()

    return changed_nodes


def append_inline_segments(parts: list[str], segments: list[str]) -> None:
    if not segments:
        return
    parts[-1] += segments[0]
    parts.extend(segments[1:])


def html_text_segments(text: str | None) -> list[str]:
    if text is None:
        return [""]
    return [html_text(part) for part in text.split("¶")]


def wrap_inline_segments(open_tag: str, close_tag: str, segments: list[str]) -> list[str]:
    return [f"{open_tag}{segment}{close_tag}" for segment in segments]


def render_inline_children_segments(
    el: etree._Element,
    opts: Options,
    *,
    exclude_notes: bool = False,
) -> list[str]:
    parts: list[str] = [""]
    if el.text:
        append_inline_segments(parts, html_text_segments(el.text))
    for child in child_elements(el):
        append_inline_segments(parts, render_inline_node_segments(child, opts, exclude_notes=exclude_notes))
        if child.tail:
            tail = child.tail
            if exclude_notes and NOTE_TAG_RE.match(tagu(child)) and parts[-1].endswith((" ", "\n", "\t")):
                tail = re.sub(r"^\s+", "", tail)
            append_inline_segments(parts, html_text_segments(tail))
    return parts


def render_inline_children(
    el: etree._Element,
    opts: Options,
    *,
    exclude_notes: bool = False,
) -> str:
    return "".join(render_inline_children_segments(el, opts, exclude_notes=exclude_notes))


def render_hi_segments(
    el: etree._Element,
    opts: Options,
    *,
    exclude_notes: bool = False,
) -> list[str]:
    rend = (attr(el, "REND") or "").strip().lower()
    body = render_inline_children_segments(el, opts, exclude_notes=exclude_notes)
    if rend in {"i", "italic", "ital", "itialic"}:
        return wrap_inline_segments("<em>", "</em>", body)
    if rend in {"b", "bold"}:
        return wrap_inline_segments("<strong>", "</strong>", body)
    if rend in {"sup", "super", "superscript", "aup"}:
        return wrap_inline_segments("<sup>", "</sup>", body)
    if rend in {"sub", "subscript"}:
        return wrap_inline_segments("<sub>", "</sub>", body)
    if rend in {"u", "und", "underline"}:
        return wrap_inline_segments("<u>", "</u>", body)
    if "small" in rend or rend == "sc":
        return wrap_inline_segments('<span class="smallcaps">', "</span>", body)
    return wrap_inline_segments(f"<span{render_attrs(el, 'hi')}>", "</span>", body)


def render_inline_node_segments(
    el: etree._Element,
    opts: Options,
    *,
    exclude_notes: bool = False,
) -> list[str]:
    tag = tagu(el)
    if tag == "LB":
        return ["<br />"]
    if tag in MILESTONE_TAGS:
        return [render_milestone(el, opts)]
    if NOTE_TAG_RE.match(tag):
        return [""] if exclude_notes else [render_note(el, opts)]
    if tag in {"HI", "HI1"}:
        return render_hi_segments(el, opts, exclude_notes=exclude_notes)
    if tag == "FOREIGN":
        lang = attr(el, "LANG") or attr(el, "XML:LANG")
        lang_attr = f' lang="{html_attr(lang)}"' if lang else ""
        return wrap_inline_segments(f"<em{lang_attr}>", "</em>", render_inline_children_segments(el, opts, exclude_notes=exclude_notes))
    if tag in QUOTE_TAGS:
        return wrap_inline_segments(f"<q{render_attrs(el)}>", "</q>", render_inline_children_segments(el, opts, exclude_notes=exclude_notes))
    if tag in {"REF", "PTR", "XPTR"}:
        target = attr(el, "TARGET", "HREF", "URL")
        body = render_inline_children_segments(el, opts, exclude_notes=exclude_notes)
        if target:
            return wrap_inline_segments(f'<a href="{html_attr(target)}">', "</a>", body)
        return wrap_inline_segments(f"<span{render_attrs(el, 'ref')}>", "</span>", body)
    if tag in {"DEL"}:
        return wrap_inline_segments(f"<del{render_attrs(el)}>", "</del>", render_inline_children_segments(el, opts, exclude_notes=exclude_notes))
    if tag in {"ADD", "INS"}:
        return wrap_inline_segments(f"<ins{render_attrs(el)}>", "</ins>", render_inline_children_segments(el, opts, exclude_notes=exclude_notes))
    if tag == "SUP":
        return wrap_inline_segments("<sup>", "</sup>", render_inline_children_segments(el, opts, exclude_notes=exclude_notes))
    if tag == "SUB":
        return wrap_inline_segments("<sub>", "</sub>", render_inline_children_segments(el, opts, exclude_notes=exclude_notes))
    if tag == "GAP":
        return [render_gap(el)]
    if tag in {
        "CORR",
        "REG",
        "ORIG",
        "ABBR",
        "EXPAN",
        "TERM",
        "NAME",
        "DATE",
        "NUM",
        "UNCLEAR",
        "SUPPLIED",
        "TITLEPART",
        "TITLE",
        "DOCAUTHOR",
        "AUTHOR",
        "EDITOR",
        "PUBLISHER",
        "PUBPLACE",
        "IDNO",
        "LABEL",
    }:
        return wrap_inline_segments(f"<span{render_attrs(el, tag.lower())}>", "</span>", render_inline_children_segments(el, opts, exclude_notes=exclude_notes))
    if is_block_tag_name(tag):
        return render_inline_children_segments(el, opts, exclude_notes=exclude_notes)
    return wrap_inline_segments(f"<span{render_attrs(el, tag.lower())}>", "</span>", render_inline_children_segments(el, opts, exclude_notes=exclude_notes))


def render_inline_node(
    el: etree._Element,
    opts: Options,
    *,
    exclude_notes: bool = False,
) -> str:
    return "".join(render_inline_node_segments(el, opts, exclude_notes=exclude_notes))


def heading_note_descendants(el: etree._Element) -> Iterator[etree._Element]:
    for child in child_elements(el):
        if NOTE_TAG_RE.match(tagu(child)):
            yield child
        else:
            yield from heading_note_descendants(child)


def render_heading_note_blocks(el: etree._Element, opts: Options) -> str:
    parts: list[str] = []
    for note in heading_note_descendants(el):
        rendered = render_note(note, opts)
        if rendered:
            parts.append(f'<p class="heading-note">{rendered}</p>\n')
    return "".join(parts)


def render_standalone_head(el: etree._Element, opts: Options) -> str:
    title_text_for_classification = heading_title_text(el)
    heading_classes = join_classes(
        source_apparatus_classes(el),
        stanza_heading_classes(el, title_text_for_classification),
    )
    body = render_inline_children(el, opts, exclude_notes=True).strip()
    heading = ""
    if has_visible_html(body):
        attrs = render_heading_attrs(el, heading_classes.split() if heading_classes else [])
        heading = f"<h3{attrs}>{body}</h3>\n"
    return heading + render_heading_note_blocks(el, opts)


def heading_level_for_div(el: etree._Element) -> int:
    match = re.match(r"^DIV(\d+)$", tagu(el))
    if not match:
        return 2
    # Reserve h1 for the document title.
    return max(2, min(6, int(match.group(1)) + 1))


def render_div(el: etree._Element, opts: Options) -> str:
    head = first_child(el, "HEAD")
    level = heading_level_for_div(el)
    title = render_inline_children(head, opts, exclude_notes=True).strip() if head is not None else ""
    heading_notes = render_heading_note_blocks(head, opts) if head is not None else ""
    is_generated_fallback = not clean_text(heading_title_text(head))
    if is_generated_fallback:
        fallback_bits = [attr(el, "TYPE"), attr(el, "N")]
        title = html_text(" ".join(bit for bit in fallback_bits if bit)[:120])
    apparatus_classes = source_apparatus_classes(el)
    heading_classes = apparatus_classes
    if is_generated_fallback and title and not apparatus_classes:
        heading_classes = GENERATED_FALLBACK_HEADING_CLASSES
    heading = f"<h{level}{render_heading_attrs(el, heading_classes, preserve_attrs=False)}>{title}</h{level}>\n" if title else ""
    body = render_children(el, opts, skip_first_head=head is not None)
    return f"<section{render_attrs(el, join_classes('div', apparatus_classes))}>\n{heading}{heading_notes}{body}\n</section>\n"


def render_hi(el: etree._Element, opts: Options) -> str:
    rend = (attr(el, "REND") or "").strip().lower()
    body = render_inline_children(el, opts)
    if rend in {"i", "italic", "ital", "itialic"}:
        return f"<em>{body}</em>"
    if rend in {"b", "bold"}:
        return f"<strong>{body}</strong>"
    if rend in {"sup", "super", "superscript", "aup"}:
        return f"<sup>{body}</sup>"
    if rend in {"sub", "subscript"}:
        return f"<sub>{body}</sub>"
    if rend in {"u", "und", "underline"}:
        return f"<u>{body}</u>"
    if "small" in rend or rend == "sc":
        return f'<span class="smallcaps">{body}</span>'
    return f"<span{render_attrs(el, 'hi')}>{body}</span>"


def render_milestone(el: etree._Element, opts: Options) -> str:
    if not opts.preserve_milestones:
        return ""
    label_bits = [tagu(el).lower()]
    for name in ("N", "REF", "UNIT"):
        value = attr(el, name)
        if value:
            label_bits.append(value)
    label = " ".join(label_bits)
    return f'<span{render_attrs(el, "milestone")}>[{html_text(label)}]</span>'


def render_note(el: etree._Element, opts: Options) -> str:
    if not opts.include_notes:
        return ""
    body = render_inline_children(el, opts).strip()
    if not has_visible_html(body):
        return ""
    return f'<span{render_attrs(el, "note")}>[{body}]</span>'


def table_column_count(el: etree._Element) -> int:
    declared = attr(el, "COLS")
    if declared and declared.isdigit():
        return max(1, int(declared))

    count = 0
    for row in child_elements(el, "ROW"):
        row_count = 0
        for cell in child_elements(row, "CELL"):
            colspan = attr(cell, "COLS")
            row_count += int(colspan) if colspan and colspan.isdigit() else 1
        count = max(count, row_count)
    return max(1, count)


def table_column_widths(column_count: int) -> list[float]:
    if column_count == 1:
        return [1.0]
    if column_count == 2:
        return [0.5, 0.5]
    if column_count == 3:
        return [0.15, 0.70, 0.15]
    if column_count == 4:
        return [0.10, 0.15, 0.65, 0.10]
    return [1.0 / column_count] * column_count


def render_colgroup(el: etree._Element) -> str:
    widths = table_column_widths(table_column_count(el))
    cols = "".join(f'<col style="width: {width:.0%}" />' for width in widths)
    return f"<colgroup>{cols}</colgroup>\n"


def render_table(el: etree._Element, opts: Options) -> str:
    rows: list[str] = []
    surrounding: list[str] = []
    for child in child_elements(el):
        if tagu(child) == "ROW":
            rows.append(render_row(child, opts))
        elif tagu(child) in MILESTONE_TAGS and not opts.preserve_milestones:
            pass
        else:
            surrounding.append(render_node(child, opts))
        if child.tail and child.tail.strip():
            surrounding.append(html_text(child.tail))
    table = f"<table{render_attrs(el)}>\n{render_colgroup(el)}{''.join(rows)}\n</table>\n"
    if surrounding:
        return f"<div{render_attrs(el, 'table-block')}>\n{''.join(surrounding)}{table}</div>\n"
    return table


def render_nested_table(el: etree._Element, opts: Options) -> str:
    """Render a table nested inside a table cell as line-level prose.

    HTML permits nested tables, but Pandoc's LaTeX writer turns both levels into
    longtable environments.  A longtable inside a longtable cell is not legal
    LaTeX and causes XeLaTeX failures for a small number of corpus sources.
    Flatten the inner table while preserving row/cell reading order and any
    non-row readable children, such as nested table headings.
    """
    segments: list[str] = []
    if el.text and el.text.strip():
        segments.append(f'<div class="nested-table-text">{html_text(el.text)}</div>')

    for child in child_elements(el):
        tag = tagu(child)
        if tag == "ROW":
            cell_segments: list[str] = []
            for cell in child_elements(child, "CELL"):
                body = render_table_cell_children(cell, opts).strip()
                if has_visible_html(body):
                    cell_segments.append(body)
            if cell_segments:
                segments.append(
                    f'<div class="nested-table-row">{" — ".join(cell_segments)}</div>'
                )
        elif tag in MILESTONE_TAGS and not opts.preserve_milestones:
            pass
        elif tag == "HEAD":
            body = render_inline_children(child, opts).strip()
            if has_visible_html(body):
                segments.append(f'<div class="nested-table-head">{body}</div>')
        else:
            body = render_node(child, opts).strip()
            if has_visible_html(body):
                segments.append(body)
        if child.tail and child.tail.strip():
            segments.append(f'<div class="nested-table-text">{html_text(child.tail)}</div>')

    if segments:
        return f'<div class="nested-table">{"".join(segments)}</div>'
    return ""


def render_table_cell_children(el: etree._Element, opts: Options) -> str:
    parts: list[str] = []
    if el.text:
        parts.append(html_text(el.text))
    for child in el:
        if isinstance(child.tag, str) and tagu(child) == "TABLE":
            parts.append(render_nested_table(child, opts))
        else:
            parts.append(render_node(child, opts))
        if child.tail:
            parts.append(html_text(child.tail))
    return "".join(parts)


def render_row(el: etree._Element, opts: Options) -> str:
    return f"<tr>{render_children(el, opts)}</tr>\n"


def render_cell(el: etree._Element, opts: Options) -> str:
    extra = []
    rows = attr(el, "ROWS")
    cols = attr(el, "COLS")
    if rows and rows.isdigit():
        extra.append(f' rowspan="{html_attr(rows)}"')
    if cols and cols.isdigit():
        extra.append(f' colspan="{html_attr(cols)}"')
    return f"<td{''.join(extra)}>{render_table_cell_children(el, opts)}</td>"


def render_gap(el: etree._Element) -> str:
    reason = attr(el, "REASON", "DESC", "EXTENT")
    return f'<span{render_attrs(el, "gap")}>[{html_text("gap: " + reason if reason else "gap")}]</span>'


def render_ref(el: etree._Element, opts: Options) -> str:
    body = render_children(el, opts) if has_block_child(el) else render_inline_children(el, opts)
    target = attr(el, "TARGET", "HREF", "URL")
    if target:
        return f'<a href="{html_attr(target)}">{body}</a>'
    wrapper = "div" if has_block_child(el) else "span"
    return f"<{wrapper}{render_attrs(el, 'ref')}>{body}</{wrapper}>"


def wrap_visible_blocks(tag: str, attrs: str, segments: Iterable[str]) -> str:
    return "".join(
        f"<{tag}{attrs}>{segment.strip()}</{tag}>\n"
        for segment in segments
        if has_visible_html(segment)
    )


def render_paragraphish(
    el: etree._Element,
    opts: Options,
    *,
    css_class: str | None = None,
) -> str:
    if has_block_child(el):
        return f"<div{render_attrs(el, css_class or 'p')}>{render_children(el, opts)}</div>\n"
    return wrap_visible_blocks("p", render_attrs(el, css_class), render_inline_children_segments(el, opts))


def render_doctitle(el: etree._Element, opts: Options) -> str:
    apparatus_classes = source_apparatus_classes(el)
    children = child_elements(el)
    if not children:
        body = html_text(el.text or "")
    else:
        parts: list[str] = []
        if el.text:
            parts.append(html_text(el.text))
        for index, child in enumerate(children):
            if tagu(child) == "TITLEPART":
                parts.append(
                    f"<span{render_attrs(child, join_classes('titlepart', apparatus_classes))}>{render_inline_children(child, opts)}</span>"
                )
                if index != len(children) - 1:
                    parts.append("<br />")
            else:
                parts.append(render_inline_node(child, opts))
            if child.tail:
                parts.append(html_text(child.tail))
        body = "".join(parts)
    return f"<h1{render_heading_attrs(el, join_classes('doctitle', apparatus_classes).split())}>{body}</h1>\n"


def render_list_item(el: etree._Element, opts: Options) -> str:
    attrs = render_attrs(el)
    if has_block_child(el):
        body = render_children(el, opts)
    else:
        segments = [segment.strip() for segment in render_inline_children_segments(el, opts) if has_visible_html(segment)]
        if not segments:
            return ""
        if len(segments) == 1:
            body = segments[0]
        else:
            body = "".join(f"<p>{segment}</p>" for segment in segments)
    return f"<li{attrs}>{body}</li>\n"


def render_list(el: etree._Element, opts: Options) -> str:
    children = child_elements(el)
    simple = all(
        tagu(child) in {"ITEM", "CASTITEM"}
        or (tagu(child) in MILESTONE_TAGS and not opts.preserve_milestones)
        for child in children
    )
    if simple:
        return f"<ul{render_attrs(el)}>\n{render_children(el, opts)}</ul>\n"

    parts: list[str] = []
    if el.text and el.text.strip():
        parts.append(f"<p>{html_text(el.text)}</p>\n")
    for child in children:
        child_tag = tagu(child)
        if child_tag in {"ITEM", "CASTITEM"}:
            if has_block_child(child):
                parts.append(f"<div{render_attrs(child, 'item')}>{render_children(child, opts)}</div>\n")
            else:
                item_body = wrap_visible_blocks("p", "", render_inline_children_segments(child, opts))
                if item_body:
                    parts.append(f"<div{render_attrs(child, 'item')}>{item_body}</div>\n")
        elif child_tag == "LABEL":
            parts.append(f"<div{render_attrs(child, 'label')}>{render_inline_children(child, opts)}</div>\n")
        elif child_tag in MILESTONE_TAGS and not opts.preserve_milestones:
            pass
        else:
            parts.append(render_node(child, opts))
        if child.tail and child.tail.strip():
            parts.append(f"<p>{html_text(child.tail)}</p>\n")
    return f"<div{render_attrs(el, 'list')}>\n{''.join(parts)}</div>\n"


def render_lg_fallback(el: etree._Element, opts: Options) -> str:
    return f"<div{render_attrs(el, 'lg')}>\n{render_children(el, opts)}</div>\n"


def is_simple_trailing_lg_closer(el: etree._Element) -> bool:
    return tagu(el) == "CLOSER" and not has_block_child(el)


def render_lg(el: etree._Element, opts: Options) -> str:
    """Render a verse line group as paragraphs with explicit line breaks.

    Pandoc turns consecutive block ``div`` lines into separate LaTeX paragraphs,
    which makes widow/orphan controls ineffective for poetry: a page break can
    strand the final one or two lines of a stanza.  Grouping verse lines into
    paragraphs with ``<br />`` maps to LaTeX line breaks inside paragraphs, so
    page-break penalties can keep stanza fragments together.  Source pilcrows
    split those verse paragraphs without rendering the pilcrow glyph.
    """
    if el.text and el.text.strip():
        return render_lg_fallback(el, opts)

    children = child_elements(el)
    trailing_closer = ""
    if children and is_simple_trailing_lg_closer(children[-1]):
        closer = children[-1]
        if closer.tail and closer.tail.strip():
            return render_lg_fallback(el, opts)
        trailing_closer = render_node(closer, opts)
        children = children[:-1]

    groups: list[list[VerseFragment]] = [[]]
    for child in children:
        child_tag = tagu(child)
        if child_tag == "L":
            line_number = source_line_number_for_verse_line(child)
            line_segments = render_inline_children_segments(child, opts)
            is_continuation = is_wrapped_l_continuation(child)
            for index, segment in enumerate(line_segments):
                if index > 0 and groups[-1]:
                    groups.append([])
                if not has_visible_html(segment):
                    continue
                if (
                    is_continuation
                    and index == 0
                    and groups[-1]
                    and isinstance(groups[-1][-1], VerseLineFragment)
                ):
                    previous = groups[-1][-1]
                    groups[-1][-1] = VerseLineFragment(
                        join_inline_continuation(previous.segment, segment),
                        previous.line_number,
                    )
                else:
                    groups[-1].append(VerseLineFragment(segment, line_number))
        elif child_tag in MILESTONE_TAGS:
            marker = render_milestone(child, opts)
            if marker:
                groups[-1].append(RawVerseFragment(marker))
        else:
            return render_lg_fallback(el, opts)

        if child.tail and child.tail.strip():
            return render_lg_fallback(el, opts)

    groups = [group for group in groups if any(has_visible_html(fragment.segment) for fragment in group)]
    if not groups:
        return render_lg_fallback(el, opts)

    paragraphs = "".join(
        f"<p class=\"verse-lines\">\n{'<br />\n'.join(render_verse_fragment(fragment, opts) for fragment in group)}\n</p>\n"
        for group in groups
    )
    return f"<div{render_attrs(el, 'lg')}>\n{paragraphs}{trailing_closer}</div>\n"


def render_node(el: etree._Element, opts: Options) -> str:
    tag = tagu(el)

    if DIV_TAG_RE.match(tag) or tag == "DIV":
        return render_div(el, opts)
    if tag in {"TEXT", "BODY", "FRONT", "BACK", "GROUP"}:
        return render_children(el, opts)
    if tag in {"P", "AB"}:
        return render_paragraphish(el, opts)
    if tag == "HEAD":
        return render_standalone_head(el, opts)
    if tag in {"DOCTITLE"}:
        return render_doctitle(el, opts)
    if tag in {"TITLEPART", "BYLINE", "DOCIMPRINT", "OPENER", "CLOSER", "SIGNED", "SALUTE", "TRAILER", "DATELINE"}:
        return render_paragraphish(el, opts, css_class=tag.lower())
    if tag in {"TITLEPAGE"}:
        return f"<section{render_attrs(el, join_classes(tag.lower(), source_apparatus_classes(el)))}>\n{render_children(el, opts)}</section>\n"
    if tag in {"HEADNOTE", "ARGUMENT"}:
        return f"<div{render_attrs(el, tag.lower())}>{render_children(el, opts)}</div>\n"
    if tag == "EPIGRAPH":
        return f"<blockquote{render_attrs(el, 'epigraph')}>{render_children(el, opts)}</blockquote>\n"
    if tag == "LG":
        return render_lg(el, opts)
    if tag == "L":
        if has_block_child(el):
            body = render_children(el, opts)
            if not has_visible_html(body):
                return ""
            return f"<div{render_verse_line_attrs(el, opts, 'l')}>{body}</div>\n"
        return wrap_visible_blocks("div", render_verse_line_attrs(el, opts, "l"), render_inline_children_segments(el, opts))
    if tag == "LB":
        return "<br />"
    if tag in MILESTONE_TAGS:
        return render_milestone(el, opts)
    if NOTE_TAG_RE.match(tag):
        return render_note(el, opts)
    if tag in {"LIST", "CASTLIST"}:
        return render_list(el, opts)
    if tag in {"ITEM", "CASTITEM"}:
        return render_list_item(el, opts)
    if tag == "LABEL":
        return f"<strong{render_attrs(el, 'label')}>{render_children(el, opts)}</strong>"
    if tag == "TABLE":
        return render_table(el, opts)
    if tag == "ROW":
        return render_row(el, opts)
    if tag == "CELL":
        return render_cell(el, opts)
    if tag == "SP":
        return f"<div{render_attrs(el, 'speech')}>\n{render_children(el, opts)}</div>\n"
    if tag == "SPEAKER":
        return f"<p{render_attrs(el, 'speaker')}><strong>{render_inline_children(el, opts)}</strong></p>\n"
    if tag in {"STAGE", "DIRECTION"}:
        return f"<p{render_attrs(el, 'stage')}><em>{render_inline_children(el, opts)}</em></p>\n"
    if tag in {"HI", "HI1"}:
        return render_hi(el, opts)
    if tag == "FOREIGN":
        lang = attr(el, "LANG") or attr(el, "XML:LANG")
        lang_attr = f' lang="{html_attr(lang)}"' if lang else ""
        return f"<em{lang_attr}>{render_inline_children(el, opts)}</em>"
    if tag in {"Q", "Q1", "QUOTE", "SAID"}:
        if has_block_child(el):
            return f"<blockquote{render_attrs(el)}>{render_children(el, opts)}</blockquote>\n"
        return f"<q{render_attrs(el)}>{render_inline_children(el, opts)}</q>"
    if tag in {"REF", "PTR", "XPTR"}:
        return render_ref(el, opts)
    if tag in {"CORR", "REG", "ORIG", "ABBR", "EXPAN", "TERM", "NAME", "DATE", "NUM", "UNCLEAR", "SUPPLIED"}:
        return f"<span{render_attrs(el, tag.lower())}>{render_inline_children(el, opts)}</span>"
    if tag == "DEL":
        return f"<del{render_attrs(el)}>{render_inline_children(el, opts)}</del>"
    if tag in {"ADD", "INS"}:
        return f"<ins{render_attrs(el)}>{render_inline_children(el, opts)}</ins>"
    if tag == "SUP":
        return f"<sup>{render_inline_children(el, opts)}</sup>"
    if tag == "SUB":
        return f"<sub>{render_inline_children(el, opts)}</sub>"
    if tag == "GAP":
        return render_gap(el)
    if tag == "FIGURE":
        caption = text_content(el)
        return f'<figure{render_attrs(el)}><figcaption>{html_text(caption or "[figure]")}</figcaption></figure>\n'
    if tag in {"TITLE", "DOCAUTHOR", "AUTHOR", "EDITOR", "PUBLISHER", "PUBPLACE", "IDNO"}:
        return f"<span{render_attrs(el, tag.lower())}>{render_inline_children(el, opts)}</span>"

    # Conservative fallback: preserve textual content and descendants.  If the
    # element contains block-ish children, use a div; otherwise use a span.
    if has_block_child(el):
        return f"<div{render_attrs(el, tag.lower())}>{render_children(el, opts)}</div>"
    return f"<span{render_attrs(el, tag.lower())}>{render_inline_children(el, opts)}</span>"


def render_headwords(
    root: etree._Element,
    opts: Options,
    normalized_nodes: set[etree._Element] | None = None,
) -> str:
    """Render lexical entries, preserving the compact legacy path by default.

    Only an entry whose content had a word-break marker removed needs the
    structure-preserving inline renderer.  Unaffected entries retain the
    compact plain-text output used before word-break normalization.
    """
    normalized_nodes = normalized_nodes or set()
    items: list[str] = []
    for entry in child_elements(root, "ENTRY"):
        entry_id = attr(entry, "ID") or ""
        seq = attr(entry, "SEQ") or ""
        forms = child_elements(entry, "FORM")
        targets = forms or [entry]
        normalized_targets = (
            {
                target
                for target in targets
                if any(node in normalized_nodes for node in target.iter())
            }
            if normalized_nodes
            else set()
        )
        if normalized_targets:
            bodies = [
                render_inline_children(target, opts).strip()
                if target in normalized_targets
                else html_text(spaced_text_content(target))
                for target in targets
            ]
            body = " ".join(body for body in bodies if has_visible_html(body))
        else:
            form = first_child(entry, "FORM")
            body = html_text(spaced_text_content(form if form is not None else entry))
        label = " ".join(html_text(bit) for bit in (seq, entry_id) if bit)
        prefix = f"<strong>{label}</strong> " if label else ""
        items.append(f"<p class=\"headword-entry\">{prefix}{body}</p>\n")
    return "<div class=\"headwords\">\n" + "".join(items) + "</div>\n"


def metadata_value_html(key: str, value: str) -> str:
    if key == "source":
        # Make long paths breakable in LaTeX/PDF output.
        return html_text(value.replace("/", "/ "))
    return html_text(value)


LATEX_REPLACEMENTS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_text(value: str | None, *, break_paths: bool = False) -> str:
    escaped = "".join(LATEX_REPLACEMENTS.get(char, char) for char in (value or ""))
    if break_paths:
        escaped = escaped.replace("/", r"/\allowbreak{}")
    return escaped


COLOPHON_SEPARATOR_PUNCTUATION = {",", ":", ";"}
COLOPHON_TERMINAL_PUNCTUATION = {".", "?", "!"}
COLOPHON_TRAILING_CLOSERS = set("'\"”’»)]}")


def colophon_title_final_punctuation(value: str | None) -> str:
    text = clean_text(value)
    while text and text[-1] in COLOPHON_TRAILING_CLOSERS:
        text = text[:-1].rstrip()
    return text[-1] if text else ""


def colophon_macro_for_title(title: str) -> str:
    punctuation = colophon_title_final_punctuation(title)
    if punctuation in COLOPHON_SEPARATOR_PUNCTUATION:
        return "cmeColophonPunctuatedTitle"
    if punctuation in COLOPHON_TERMINAL_PUNCTUATION:
        return "cmeColophonTerminalTitle"
    return "cmeColophon"


def render_colophon_tex(path: Path, parsed: ParsedXml, fmt: str) -> str:
    meta = metadata(parsed.root, fmt, path, parsed)
    title = meta.get("title", path.stem)
    author = meta.get("author") or "Anonymous"
    values = [
        latex_text(title),
        latex_text(meta.get("subtitle")),
        latex_text(author),
        latex_text(meta.get("original_date")),
        latex_text(meta.get("source"), break_paths=True),
        latex_text(meta.get("format")),
        latex_text(meta.get("editor")),
        latex_text(meta.get("date")),
        latex_text(meta.get("id")),
    ]
    macro = colophon_macro_for_title(title)
    return f"\\{macro}{{" + "}{".join(values) + "}\n"


def render_document(path: Path, parsed: ParsedXml, fmt: str, opts: Options) -> str:
    root = parsed.root
    meta = metadata(root, fmt, path, parsed)
    title = meta.get("title", path.stem)
    display_title = meta.get("full_title") or title
    author = meta.get("author") or "Anonymous"
    # Pandoc's LaTeX template uses the HTML <title> for PDF metadata and the
    # title page.  Fold CME subtitle/head supplements into that title string;
    # the separately generated colophon still records title/subtitle fields.
    subtitle_meta = ""
    original_date_meta = (
        f'<meta name="date" content="{html_attr(meta["original_date"])}" />\n'
        if meta.get("original_date")
        else ""
    )

    meta_rows = "\n".join(
        f"<dt>{html_text(key.replace('_', ' ').title())}</dt><dd>{metadata_value_html(key, value)}</dd>"
        for key, value in meta.items()
        if key != "title" and value
    )
    warning = ""
    if parsed.recovered:
        warning = (
            '<p class="xml-warning"><strong>Warning:</strong> XML was parsed in recovery mode. '
            "The source has well-formedness errors; check conversion around the reported locations.</p>\n"
        )
    source_metadata = ""
    if opts.include_source_metadata:
        source_metadata = f"""<div class="source-metadata">
<h2>Source metadata</h2>
{warning}<dl>
{meta_rows}
</dl>
</div>
"""

    source_payload_nodes = primary_text_nodes(root, fmt)
    normalized_nodes: set[etree._Element] = set()
    if payload_has_word_break_verbar(source_payload_nodes):
        render_root = copy.deepcopy(root)
        rendered_payload_nodes = primary_text_nodes(render_root, fmt)
        normalized_nodes = normalize_word_break_verbars(rendered_payload_nodes, opts, fmt)
    else:
        render_root = root
        rendered_payload_nodes = source_payload_nodes
    if fmt == "headwords":
        body = render_headwords(render_root, opts, normalized_nodes)
    else:
        body = "\n".join(render_node(node, opts) for node in rendered_payload_nodes)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{html_text(display_title)}</title>
<meta name="author" content="{html_attr(author)}" />
{subtitle_meta}{original_date_meta}<style>
body {{ line-height: 1.35; }}
.source-metadata {{ border-bottom: 1px solid #ccc; margin-bottom: 2rem; }}
.source-metadata dl {{ display: grid; grid-template-columns: max-content 1fr; gap: .25rem 1rem; }}
.source-metadata dt {{ font-weight: bold; }}
.lg {{ margin: 1rem 0 1rem 2rem; }}
.l {{ margin: 0; }}
.note {{ font-size: 0.9em; color: #555; }}
.stage {{ font-style: italic; }}
.speaker {{ font-variant: small-caps; }}
.milestone {{ color: #777; font-size: 0.85em; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #ccc; padding: .2rem .4rem; vertical-align: top; }}
</style>
</head>
<body>
<main>
{source_metadata}{body}
</main>
</body>
</html>
"""


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="CME XML file to convert to HTML")
    parser.add_argument(
        "--format",
        default="auto",
        choices=sorted(FORMATS),
        help="Expected source format; auto-detected by default",
    )
    parser.add_argument(
        "--drop-notes",
        action="store_true",
        help="omit NOTE/NOTE1/etc. content from the readable output",
    )
    parser.add_argument(
        "--preserve-milestones",
        action="store_true",
        help="render PB/EPB/MILESTONE/FW markers visibly instead of dropping them",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail instead of recovering when the source XML is not well formed",
    )
    parser.add_argument(
        "--omit-source-metadata",
        action="store_true",
        help="omit the visible source metadata block from the rendered HTML body",
    )
    parser.add_argument(
        "--verse-line-metadata",
        action="store_true",
        help="emit hidden verse line metadata for the LaTeX/PDF verse-line-number filter",
    )
    parser.add_argument(
        "--colophon-tex",
        action="store_true",
        help="emit a LaTeX colophon macro call for this source instead of HTML",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    parsed = parse_xml(args.input)
    if parsed.recovered:
        message = f"{args.input}: XML was recovered after strict parse failure"
        if parsed.errors:
            message += "\n" + "\n".join(f"  {error}" for error in parsed.errors)
        if args.strict:
            raise SystemExit(message)
        print(message, file=sys.stderr)
    detected = detect_format(parsed.root)
    require_format(args.format, detected, args.input)
    if args.colophon_tex:
        sys.stdout.write(render_colophon_tex(args.input, parsed, detected))
        return 0
    opts = Options(
        include_notes=not args.drop_notes,
        preserve_milestones=args.preserve_milestones,
        include_source_metadata=not args.omit_source_metadata,
        include_verse_line_metadata=args.verse_line_metadata,
    )
    sys.stdout.write(render_document(args.input, parsed, detected, opts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
