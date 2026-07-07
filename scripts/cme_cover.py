#!/usr/bin/env python3
"""Plan and generate Lulu paperback cover templates."""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

POINTS_PER_INCH = 72.0
TRIM_SIZES_IN = {
    "5x8": (5.0, 8.0),
    "5x8in": (5.0, 8.0),
    "5x8-in": (5.0, 8.0),
}


class CoverError(ValueError):
    """Raised when a cover plan cannot be created."""


@dataclass(frozen=True)
class CoverPlan:
    trim: str
    binding: str
    pages: int
    bleed_in: float
    safety_margin_in: float
    spine_width_in: float
    cover_width_in: float
    cover_height_in: float
    back: dict[str, float]
    spine: dict[str, float]
    front: dict[str, float]
    barcode: dict[str, float]
    spine_text_allowed: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "trim": self.trim,
            "binding": self.binding,
            "pages": self.pages,
            "bleed_in": self.bleed_in,
            "safety_margin_in": self.safety_margin_in,
            "spine_width_in": self.spine_width_in,
            "cover_width_in": self.cover_width_in,
            "cover_height_in": self.cover_height_in,
            "back": self.back,
            "spine": self.spine,
            "front": self.front,
            "barcode": self.barcode,
            "spine_text_allowed": self.spine_text_allowed,
            "warnings": warnings_for_plan(self),
        }


def normalize_trim(trim: str) -> str:
    normalized = trim.lower().replace(" ", "").replace("×", "x")
    if normalized not in TRIM_SIZES_IN:
        raise CoverError(f"Unsupported trim '{trim}'. Known trims: {', '.join(sorted(TRIM_SIZES_IN))}")
    return normalized


def trim_size_inches(trim: str) -> tuple[float, float]:
    return TRIM_SIZES_IN[normalize_trim(trim)]


def paperback_spine_width_in(pages: int) -> float:
    if pages <= 0:
        raise CoverError("Page count must be positive")
    return pages / 444.0 + 0.06


def plan_cover(
    pages: int,
    trim: str = "5x8",
    binding: str = "paperback-perfect",
    bleed: float = 0.125,
    safety_margin: float = 0.5,
) -> CoverPlan:
    if binding != "paperback-perfect":
        raise CoverError("Only paperback-perfect is implemented in this first Lulu cover slice")
    trim_key = normalize_trim(trim)
    trim_width, trim_height = trim_size_inches(trim_key)
    spine_width = paperback_spine_width_in(pages)
    cover_width = trim_width * 2 + spine_width + 2 * bleed
    cover_height = trim_height + 2 * bleed

    back_x = bleed
    spine_x = bleed + trim_width
    front_x = spine_x + spine_width
    trim_y = bleed
    barcode_width = 2.0
    barcode_height = 1.2
    barcode_margin = 0.25
    barcode = {
        "x": back_x + trim_width - barcode_margin - barcode_width,
        "y": trim_y + trim_height - barcode_margin - barcode_height,
        "width": barcode_width,
        "height": barcode_height,
        "margin_from_trim_edge": barcode_margin,
    }
    return CoverPlan(
        trim=trim_key,
        binding=binding,
        pages=pages,
        bleed_in=bleed,
        safety_margin_in=safety_margin,
        spine_width_in=spine_width,
        cover_width_in=cover_width,
        cover_height_in=cover_height,
        back={"x": back_x, "y": trim_y, "width": trim_width, "height": trim_height},
        spine={"x": spine_x, "y": trim_y, "width": spine_width, "height": trim_height},
        front={"x": front_x, "y": trim_y, "width": trim_width, "height": trim_height},
        barcode=barcode,
        spine_text_allowed=pages >= 100,
    )


def warnings_for_plan(plan: CoverPlan) -> list[str]:
    warnings: list[str] = []
    if plan.pages < 32:
        warnings.append("Paperback perfect-bound books require at least 32 interior pages on Lulu.")
    if plan.pages > 800:
        warnings.append("Paperback perfect-bound books exceed Lulu's 800-page maximum.")
    if not plan.spine_text_allowed:
        warnings.append("Do not include spine text on Lulu covers for books under 100 pages.")
    warnings.append(
        "This generated template includes guide lines; do not upload it as a final cover without removing guides."
    )
    warnings.append(
        "Compare final production covers against Lulu's downloaded template for the exact project/channel."
    )
    return warnings


def inches(value: float) -> str:
    return f"{value:.5f}".rstrip("0").rstrip(".")


def svg_rect(x: float, y: float, width: float, height: float, css_class: str, extra: str = "") -> str:
    return (
        f'<rect class="{css_class}" x="{inches(x)}" y="{inches(y)}" '
        f'width="{inches(width)}" height="{inches(height)}" {extra}/>'
    )


def svg_text(x: float, y: float, text: str, css_class: str = "label", extra: str = "") -> str:
    return f'<text class="{css_class}" x="{inches(x)}" y="{inches(y)}" {extra}>{html.escape(text)}</text>'


def wrap_text(text: str, max_chars: int = 24) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def cover_template_svg(plan: CoverPlan, title: str | None = None, author: str | None = None) -> str:
    width = plan.cover_width_in
    height = plan.cover_height_in
    back = plan.back
    spine = plan.spine
    front = plan.front
    bleed = plan.bleed_in
    safe = plan.safety_margin_in
    title_text = title or "Front cover title"
    author_text = author or "Author / editor"
    warning_lines = warnings_for_plan(plan)

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{inches(width)}in" height="{inches(height)}in" '
            f'viewBox="0 0 {inches(width)} {inches(height)}">'
        ),
        "<defs>",
        "<style><![CDATA[",
        ".background{fill:#fdfbf5}",
        ".bleed{fill:none;stroke:#0099cc;stroke-width:0.01;stroke-dasharray:0.08 0.04}",
        ".trim{fill:none;stroke:#222;stroke-width:0.008}",
        ".safe{fill:none;stroke:#3366cc;stroke-width:0.008;stroke-dasharray:0.05 0.035}",
        ".spine{fill:#efe7d2;stroke:#aa66aa;stroke-width:0.008}",
        ".barcode{fill:#fff;stroke:#d6a300;stroke-width:0.01}",
        ".label{font-family:serif;font-size:0.13px;fill:#222;text-anchor:middle}",
        ".small{font-family:sans-serif;font-size:0.08px;fill:#333}",
        ".title{font-family:serif;font-size:0.24px;fill:#222;text-anchor:middle;font-weight:bold}",
        ".author{font-family:serif;font-size:0.16px;fill:#222;text-anchor:middle}",
        "]]></style>",
        "</defs>",
        svg_rect(0, 0, width, height, "background"),
        svg_rect(0, 0, width, height, "bleed"),
        svg_rect(back["x"], back["y"], back["width"], back["height"], "trim"),
        svg_rect(spine["x"], spine["y"], spine["width"], spine["height"], "spine"),
        svg_rect(front["x"], front["y"], front["width"], front["height"], "trim"),
        svg_rect(back["x"] + safe, back["y"] + safe, back["width"] - 2 * safe, back["height"] - 2 * safe, "safe"),
        svg_rect(front["x"] + safe, front["y"] + safe, front["width"] - 2 * safe, front["height"] - 2 * safe, "safe"),
        svg_rect(plan.barcode["x"], plan.barcode["y"], plan.barcode["width"], plan.barcode["height"], "barcode"),
        svg_text(back["x"] + back["width"] / 2, bleed + 0.35, "BACK COVER", "label"),
        svg_text(spine["x"] + spine["width"] / 2, bleed + 0.35, "SPINE", "label"),
        svg_text(front["x"] + front["width"] / 2, bleed + 0.35, "FRONT COVER", "label"),
    ]
    title_lines = wrap_text(title_text)
    title_start_y = front["y"] + front["height"] * (0.40 if len(title_lines) == 1 else 0.37)
    for index, line in enumerate(title_lines):
        parts.append(svg_text(front["x"] + front["width"] / 2, title_start_y + index * 0.3, line, "title"))
    parts.extend([
        svg_text(front["x"] + front["width"] / 2, front["y"] + front["height"] * 0.54, author_text, "author"),
        svg_text(plan.barcode["x"] + plan.barcode["width"] / 2, plan.barcode["y"] + plan.barcode["height"] / 2, "ISBN barcode area", "label"),
    ])
    footer_source_lines = [
        f"trim={plan.trim} pages={plan.pages} spine={plan.spine_width_in:.4f}in size={plan.cover_width_in:.4f}x{plan.cover_height_in:.4f}in",
        *warning_lines,
    ]
    footer_lines: list[str] = []
    for line in footer_source_lines:
        footer_lines.extend(wrap_text(line, max_chars=48))
    footer_x = back["x"] + 0.15
    footer_start_y = back["y"] + 0.65
    for index, line in enumerate(footer_lines):
        parts.append(svg_text(footer_x, footer_start_y + index * 0.105, line, "small", 'text-anchor="start"'))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def write_template(plan: CoverPlan, output: Path, title: str | None = None, author: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    svg = cover_template_svg(plan, title=title, author=author)
    if output.suffix.lower() == ".svg":
        output.write_text(svg, encoding="utf-8")
        return
    if output.suffix.lower() == ".pdf":
        converter = shutil.which("rsvg-convert")
        if converter is None:
            raise CoverError("Writing PDF templates requires rsvg-convert; write .svg instead or install librsvg")
        with tempfile.NamedTemporaryFile("w", suffix=".svg", encoding="utf-8", delete=False) as handle:
            handle.write(svg)
            temp_svg = Path(handle.name)
        try:
            subprocess.run([converter, "-f", "pdf", "-o", str(output), str(temp_svg)], check=True)
        finally:
            temp_svg.unlink(missing_ok=True)
        return
    raise CoverError("Cover template output must end in .svg or .pdf")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Emit a JSON Lulu cover plan")
    add_cover_args(plan_parser)

    template_parser = subparsers.add_parser("template", help="Write a Lulu cover guide template as SVG or PDF")
    add_cover_args(template_parser)
    template_parser.add_argument("--output", required=True, type=Path, help="Template output path (.svg or .pdf)")
    template_parser.add_argument("--title", help="Placeholder front-cover title")
    template_parser.add_argument("--author", help="Placeholder front-cover author/editor")

    return parser


def add_cover_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--trim", default="5x8", help="Trim size, currently 5x8")
    parser.add_argument("--binding", default="paperback-perfect", help="Binding, currently paperback-perfect")
    parser.add_argument("--pages", type=int, required=True, help="Interior page count")
    parser.add_argument("--bleed", type=float, default=0.125, help="Bleed in inches on each edge")
    parser.add_argument("--safety-margin", type=float, default=0.5, help="Cover safety margin in inches")


def main(argv: Sequence[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    try:
        plan = plan_cover(
            pages=args.pages,
            trim=args.trim,
            binding=args.binding,
            bleed=args.bleed,
            safety_margin=args.safety_margin,
        )
        if args.command == "plan":
            json.dump(plan.to_json(), sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
            return 0
        if args.command == "template":
            write_template(plan, args.output, title=args.title, author=args.author)
            return 0
        parser.error(f"Unknown command: {args.command}")
    except CoverError as exc:
        print(f"cme-cover: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
