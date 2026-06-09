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
import re
import sys
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


@dataclass(frozen=True)
class Options:
    include_notes: bool = True
    preserve_milestones: bool = False
    include_source_metadata: bool = True


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
    return escape(text or "", quote=False)


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
    """Return the top-level textual payload nodes, not nested quoted TEXT tags."""
    if fmt == "dlpstextclass" or fmt == "tei2":
        text = first_child(root, "TEXT")
        return [text] if text is not None else [root]

    if fmt.startswith("ets"):
        eebo = first_child(root, "EEBO")
        if eebo is None:
            return [root]
        nodes: list[etree._Element] = []
        for child in child_elements(eebo):
            child_tag = tagu(child)
            if child_tag == "TEXT":
                nodes.append(child)
            elif child_tag == "GROUP":
                nodes.extend(child_elements(child, "TEXT"))
        return nodes or [eebo]

    return [root]


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
                candidate = text_content(first_descendant(text_node, tag))
                if candidate:
                    data["title"] = candidate[:180]
                    break
            if "title" in data:
                break

    if "id" not in data:
        vid = first_descendant(root, "VID", "BIBNO", "IDNO")
        value = text_content(vid)
        if value:
            data["id"] = value

    data.setdefault("title", source.stem)
    return data


def render_attrs(el: etree._Element, css_class: str | None = None) -> str:
    pairs: list[tuple[str, str]] = []
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
        value = attr(el, xml_name)
        if value:
            if html_name == "id" and not re.match(r"^[A-Za-z][-A-Za-z0-9_:.]*$", value):
                html_name = "data-id"
            pairs.append((html_name, value))
    return "".join(f' {name}="{html_attr(value)}"' for name, value in pairs)


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


def render_inline_children(el: etree._Element, opts: Options) -> str:
    parts: list[str] = []
    if el.text:
        parts.append(html_text(el.text))
    for child in child_elements(el):
        parts.append(render_inline_node(child, opts))
        if child.tail:
            parts.append(html_text(child.tail))
    return "".join(parts)


def render_inline_node(el: etree._Element, opts: Options) -> str:
    tag = tagu(el)
    if tag == "LB":
        return "<br />"
    if tag in MILESTONE_TAGS:
        return render_milestone(el, opts)
    if NOTE_TAG_RE.match(tag):
        return render_note(el, opts)
    if tag in {"HI", "HI1"}:
        return render_hi(el, opts)
    if tag == "FOREIGN":
        lang = attr(el, "LANG") or attr(el, "XML:LANG")
        lang_attr = f' lang="{html_attr(lang)}"' if lang else ""
        return f"<em{lang_attr}>{render_inline_children(el, opts)}</em>"
    if tag in QUOTE_TAGS:
        return f"<q{render_attrs(el)}>{render_inline_children(el, opts)}</q>"
    if tag in {"REF", "PTR", "XPTR"}:
        target = attr(el, "TARGET", "HREF", "URL")
        body = render_inline_children(el, opts)
        if target:
            return f'<a href="{html_attr(target)}">{body}</a>'
        return f"<span{render_attrs(el, 'ref')}>{body}</span>"
    if tag in {"DEL"}:
        return f"<del{render_attrs(el)}>{render_inline_children(el, opts)}</del>"
    if tag in {"ADD", "INS"}:
        return f"<ins{render_attrs(el)}>{render_inline_children(el, opts)}</ins>"
    if tag == "SUP":
        return f"<sup>{render_inline_children(el, opts)}</sup>"
    if tag == "SUB":
        return f"<sub>{render_inline_children(el, opts)}</sub>"
    if tag == "GAP":
        return render_gap(el)
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
        return f"<span{render_attrs(el, tag.lower())}>{render_inline_children(el, opts)}</span>"
    if is_block_tag_name(tag):
        return render_inline_children(el, opts)
    return f"<span{render_attrs(el, tag.lower())}>{render_inline_children(el, opts)}</span>"


def heading_level_for_div(el: etree._Element) -> int:
    match = re.match(r"^DIV(\d+)$", tagu(el))
    if not match:
        return 2
    # Reserve h1 for the document title.
    return max(2, min(6, int(match.group(1)) + 1))


def render_div(el: etree._Element, opts: Options) -> str:
    head = first_child(el, "HEAD")
    level = heading_level_for_div(el)
    title = render_inline_children(head, opts) if head is not None else ""
    if not clean_text(text_content(head)):
        fallback_bits = [attr(el, "TYPE"), attr(el, "N")]
        title = " ".join(bit for bit in fallback_bits if bit)[:120]
    heading = f"<h{level}>{title}</h{level}>\n" if title else ""
    body = render_children(el, opts, skip_first_head=head is not None)
    return f"<section{render_attrs(el, 'div')}>\n{heading}{body}\n</section>\n"


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
    value = text_content(el)
    if not value:
        return ""
    return f'<span{render_attrs(el, "note")}>[{html_text(value)}]</span>'


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
    table = f"<table{render_attrs(el)}>\n{''.join(rows)}\n</table>\n"
    if surrounding:
        return f"<div{render_attrs(el, 'table-block')}>\n{''.join(surrounding)}{table}</div>\n"
    return table


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
    return f"<td{''.join(extra)}>{render_children(el, opts)}</td>"


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


def render_paragraphish(
    el: etree._Element,
    opts: Options,
    *,
    css_class: str | None = None,
) -> str:
    if has_block_child(el):
        return f"<div{render_attrs(el, css_class or 'p')}>{render_children(el, opts)}</div>\n"
    return f"<p{render_attrs(el, css_class)}>{render_children(el, opts)}</p>\n"


def render_doctitle(el: etree._Element, opts: Options) -> str:
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
                    f"<span{render_attrs(child, 'titlepart')}>{render_inline_children(child, opts)}</span>"
                )
                if index != len(children) - 1:
                    parts.append("<br />")
            else:
                parts.append(render_inline_node(child, opts))
            if child.tail:
                parts.append(html_text(child.tail))
        body = "".join(parts)
    return f"<h1{render_attrs(el, 'doctitle')}>{body}</h1>\n"


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
            parts.append(f"<div{render_attrs(child, 'item')}>{render_children(child, opts)}</div>\n")
        elif child_tag == "LABEL":
            parts.append(f"<div{render_attrs(child, 'label')}>{render_inline_children(child, opts)}</div>\n")
        elif child_tag in MILESTONE_TAGS and not opts.preserve_milestones:
            pass
        else:
            parts.append(render_node(child, opts))
        if child.tail and child.tail.strip():
            parts.append(f"<p>{html_text(child.tail)}</p>\n")
    return f"<div{render_attrs(el, 'list')}>\n{''.join(parts)}</div>\n"


def render_lg(el: etree._Element, opts: Options) -> str:
    """Render a verse line group as one HTML paragraph with explicit line breaks.

    Pandoc turns consecutive block ``div`` lines into separate LaTeX paragraphs,
    which makes widow/orphan controls ineffective for poetry: a page break can
    strand the final one or two lines of a stanza.  A single paragraph with
    ``<br />`` line breaks maps to LaTeX line breaks inside one paragraph, so the
    project LaTeX page-break penalties can keep stanza fragments together.
    """
    if el.text and el.text.strip():
        return f"<div{render_attrs(el, 'lg')}>\n{render_children(el, opts)}</div>\n"

    lines: list[str] = []
    for child in child_elements(el):
        child_tag = tagu(child)
        if child_tag == "L":
            line = render_inline_children(child, opts)
            if has_visible_html(line):
                lines.append(line)
        elif child_tag in MILESTONE_TAGS:
            marker = render_milestone(child, opts)
            if marker:
                lines.append(marker)
        elif child_tag in {"HEAD"}:
            return f"<div{render_attrs(el, 'lg')}>\n{render_children(el, opts)}</div>\n"
        else:
            return f"<div{render_attrs(el, 'lg')}>\n{render_children(el, opts)}</div>\n"

        if child.tail and child.tail.strip():
            return f"<div{render_attrs(el, 'lg')}>\n{render_children(el, opts)}</div>\n"

    if not lines:
        return f"<div{render_attrs(el, 'lg')}>\n{render_children(el, opts)}</div>\n"

    return f"<div{render_attrs(el, 'lg')}>\n<p class=\"verse-lines\">\n{'<br />\n'.join(lines)}\n</p>\n</div>\n"


def render_node(el: etree._Element, opts: Options) -> str:
    tag = tagu(el)

    if DIV_TAG_RE.match(tag) or tag == "DIV":
        return render_div(el, opts)
    if tag in {"TEXT", "BODY", "FRONT", "BACK", "GROUP"}:
        return render_children(el, opts)
    if tag in {"P", "AB"}:
        return render_paragraphish(el, opts)
    if tag == "HEAD":
        return f"<h3{render_attrs(el)}>{render_inline_children(el, opts)}</h3>\n"
    if tag in {"DOCTITLE"}:
        return render_doctitle(el, opts)
    if tag in {"TITLEPART", "BYLINE", "DOCIMPRINT", "OPENER", "CLOSER", "SIGNED", "SALUTE", "TRAILER", "DATELINE"}:
        return render_paragraphish(el, opts, css_class=tag.lower())
    if tag in {"TITLEPAGE"}:
        return f"<section{render_attrs(el, tag.lower())}>\n{render_children(el, opts)}</section>\n"
    if tag in {"HEADNOTE", "ARGUMENT"}:
        return f"<div{render_attrs(el, tag.lower())}>{render_children(el, opts)}</div>\n"
    if tag == "EPIGRAPH":
        return f"<blockquote{render_attrs(el, 'epigraph')}>{render_children(el, opts)}</blockquote>\n"
    if tag == "LG":
        return render_lg(el, opts)
    if tag == "L":
        body = render_children(el, opts)
        if not has_visible_html(body):
            return ""
        return f"<div{render_attrs(el, 'l')}>{body}</div>\n"
    if tag == "LB":
        return "<br />"
    if tag in MILESTONE_TAGS:
        return render_milestone(el, opts)
    if NOTE_TAG_RE.match(tag):
        return render_note(el, opts)
    if tag in {"LIST", "CASTLIST"}:
        return render_list(el, opts)
    if tag in {"ITEM", "CASTITEM"}:
        return f"<li{render_attrs(el)}>{render_children(el, opts)}</li>\n"
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


def render_headwords(root: etree._Element, opts: Options) -> str:
    """Render the lexical headword file as flowing paragraphs.

    Large tables or definition-list labels become oversized TeX boxes when
    converted to PDF.  Flowing paragraphs keep the lexical records readable and
    allow TeX to wrap long form lists naturally.
    """
    items: list[str] = []
    for entry in child_elements(root, "ENTRY"):
        entry_id = attr(entry, "ID") or ""
        seq = attr(entry, "SEQ") or ""
        form = first_child(entry, "FORM")
        label = " ".join(html_text(bit) for bit in (seq, entry_id) if bit)
        body = html_text(spaced_text_content(form if form is not None else entry))
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


def render_colophon_tex(path: Path, parsed: ParsedXml, fmt: str) -> str:
    meta = metadata(parsed.root, fmt, path, parsed)
    title = meta.get("title", path.stem)
    author = meta.get("author") or "Anonymous"
    values = [
        latex_text(title),
        latex_text(author),
        latex_text(meta.get("source"), break_paths=True),
        latex_text(meta.get("format")),
        latex_text(meta.get("editor")),
        latex_text(meta.get("date")),
        latex_text(meta.get("id")),
        "XML was parsed in recovery mode." if parsed.recovered else "",
    ]
    return "\\cmeColophon{" + "}{".join(values) + "}\n"


def render_document(path: Path, parsed: ParsedXml, fmt: str, opts: Options) -> str:
    root = parsed.root
    meta = metadata(root, fmt, path, parsed)
    title = meta.get("title", path.stem)
    author = meta.get("author") or "Anonymous"

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

    if fmt == "headwords":
        body = render_headwords(root, opts)
    else:
        body = "\n".join(render_node(node, opts) for node in primary_text_nodes(root, fmt))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{html_text(title)}</title>
<meta name="author" content="{html_attr(author)}" />
<style>
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
    )
    sys.stdout.write(render_document(args.input, parsed, detected, opts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
