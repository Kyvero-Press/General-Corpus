#!/usr/bin/env python3
"""Profile-driven CME XML -> Pandoc build planning and execution."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "config" / "cme-build"
CME_XML_TO_HTML = REPO_ROOT / "scripts" / "cme_xml_to_html.py"
PLACEHOLDERS = {
    "html": "{temp_html}",
    "colophon_tex": "{temp_colophon_tex}",
    "lettrine_mode_tex": "{temp_lettrine_mode_tex}",
}


class BuildProfileError(ValueError):
    """Raised when a build profile cannot be resolved."""


@dataclass(frozen=True)
class BuildConfig:
    root: Path
    profiles: Mapping[str, Mapping[str, Any]]
    modules: Mapping[str, Mapping[str, Any]]

    def profile_names(self) -> list[str]:
        return sorted(
            name
            for name, profile in self.profiles.items()
            if not name.startswith("_") and bool(profile.get("public", True))
        )

    def resolve_profile(self, name: str) -> dict[str, Any]:
        return self._resolve_profile(name, stack=())

    def _resolve_profile(self, name: str, stack: tuple[str, ...]) -> dict[str, Any]:
        if name not in self.profiles:
            known = ", ".join(self.profile_names())
            raise BuildProfileError(f"Unknown profile '{name}'. Known profiles: {known}")
        if name in stack:
            chain = " -> ".join((*stack, name))
            raise BuildProfileError(f"Profile inheritance cycle: {chain}")

        raw = dict(self.profiles[name])
        parent_name = raw.pop("inherits", None)
        if parent_name is None:
            return raw

        parent = self._resolve_profile(str(parent_name), (*stack, name))
        merged = dict(parent)
        merged.update(raw)
        return merged


@dataclass(frozen=True)
class BuildPlan:
    profile: str
    input: str
    output: str
    output_format: str
    notes: str
    lettrine: str
    modules: list[str]
    generated: dict[str, str]
    xml: dict[str, Any]
    pandoc: dict[str, Any]

    def to_json(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "input": self.input,
            "output": self.output,
            "output_format": self.output_format,
            "notes": self.notes,
            "lettrine": self.lettrine,
            "modules": list(self.modules),
            "generated": dict(self.generated),
            "xml": self.xml,
            "pandoc": self.pandoc,
        }


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_build_config(root: Path | str | None = None) -> BuildConfig:
    repo_root = Path(root) if root is not None else REPO_ROOT
    config_dir = repo_root / "config" / "cme-build"
    profiles_doc = load_toml(config_dir / "profiles.toml")
    modules_doc = load_toml(config_dir / "modules.toml")
    return BuildConfig(
        root=repo_root,
        profiles=profiles_doc.get("profiles", {}),
        modules=modules_doc.get("modules", {}),
    )


def _normalize_path(value: str, root: Path) -> str:
    if value.startswith("{") and value.endswith("}"):
        return value
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str(root / path)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _strip_passthrough_separator(args: Sequence[str]) -> list[str]:
    values = list(args)
    if values and values[0] == "--":
        return values[1:]
    return values


def has_pandoc_variable(key: str, args: Sequence[str]) -> bool:
    expect_value = False
    for arg in args:
        if expect_value:
            if arg == key or arg.startswith(f"{key}=") or arg.startswith(f"{key}:"):
                return True
            expect_value = False
            continue
        if arg in {"-V", "--variable", "-M", "--metadata"}:
            expect_value = True
            continue
        prefixes = (
            f"-V{key}=",
            f"-M{key}=",
            f"-V{key}:",
            f"-M{key}:",
            f"--variable={key}=",
            f"--metadata={key}=",
            f"--variable={key}:",
            f"--metadata={key}:",
        )
        if arg.startswith(prefixes):
            return True
    return False


def has_pandoc_flag(flag: str, args: Sequence[str]) -> bool:
    return any(arg == flag for arg in args)


def has_pandoc_option(option: str, args: Sequence[str]) -> bool:
    expect_value = False
    for arg in args:
        if expect_value:
            expect_value = False
            continue
        if arg == option or arg.startswith(f"{option}="):
            return True
        if arg == option:
            expect_value = True
    return False


def has_pandoc_writer_option(args: Sequence[str]) -> bool:
    for arg in args:
        if arg in {"-t", "--to", "-w", "--write"}:
            return True
        if arg.startswith(("-t", "-w", "--to=", "--write=")) and arg not in {"-", "--"}:
            return True
    return False


def _variable_enabled(spec: Mapping[str, Any], user_args: Sequence[str]) -> bool:
    unless_variable = spec.get("unless_variable")
    if unless_variable and has_pandoc_variable(str(unless_variable), user_args):
        return False
    unless_any = spec.get("unless_any_variable", [])
    if any(has_pandoc_variable(str(key), user_args) for key in unless_any):
        return False
    return True


def _resolve_variables(profile: Mapping[str, Any], user_args: Sequence[str]) -> list[dict[str, str]]:
    variables: list[dict[str, str]] = []
    for spec in profile.get("variables", []):
        if not _variable_enabled(spec, user_args):
            continue
        try:
            name = str(spec["name"])
            value = str(spec["value"])
        except KeyError as exc:
            raise BuildProfileError(f"Pandoc variable is missing required key: {exc}") from exc
        variables.append({"name": name, "value": value})
    return variables


def normalize_lettrine_mode(raw: str) -> str:
    normalized = raw.lower().replace("-", "").replace("_", "")
    aliases = {
        "none": "none",
        "no": "none",
        "off": "none",
        "plain": "plain",
        "default": "plain",
        "body": "plain",
        "bodyfont": "plain",
        "goudyinitialen": "goudyinitialen",
        "goudy": "goudyinitialen",
        "gotischeinitialen": "gotischeinitialen",
        "gotische": "gotischeinitialen",
        "gotin": "gotischeinitialen",
        "baroqueinitials": "baroqueinitials",
        "baroque": "baroqueinitials",
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise BuildProfileError(
            f"Invalid lettrine mode '{raw}'. Expected none, plain, goudyinitialen, "
            "gotischeinitialen, or baroqueinitials."
        ) from exc


def lettrine_mode_header(mode: str) -> str:
    normalized = normalize_lettrine_mode(mode)
    if normalized == "plain":
        return """% CME lettrine mode: plain body-font initial.
\\renewcommand{\\cmeLettrine}[2]{\\cmeLettrinePlain{#1}{#2}}
\\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrinePlainAnte{#1}{#2}{#3}}
"""
    if normalized == "goudyinitialen":
        return """% CME lettrine mode: Goudy Initialen when available.
\\IfFileExists{GoudyIn.sty}{%
  \\usepackage{GoudyIn}%
  \\renewcommand{\\cmeLettrine}[2]{\\cmeLettrineWithFontHook{\\GoudyInfamily}{##1}{##2}}%
  \\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrineWithFontHookAnte{\\GoudyInfamily}{##1}{##2}{##3}}%
}{%
  \\PackageWarningNoLine{cme-lettrine}{GoudyIn.sty not found; falling back to plain lettrine}%
  \\renewcommand{\\cmeLettrine}[2]{\\cmeLettrinePlain{##1}{##2}}%
  \\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrinePlainAnte{##1}{##2}{##3}}%
}
"""
    if normalized == "gotischeinitialen":
        return """% CME lettrine mode: Gotische Initialen when available.
\\IfFileExists{GotIn.sty}{%
  \\usepackage{GotIn}%
  \\renewcommand{\\cmeLettrine}[2]{\\cmeLettrineWithFontHook{\\GotInfamily}{##1}{##2}}%
  \\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrineWithFontHookAnte{\\GotInfamily}{##1}{##2}{##3}}%
}{%
  \\PackageWarningNoLine{cme-lettrine}{GotIn.sty not found; falling back to plain lettrine}%
  \\renewcommand{\\cmeLettrine}[2]{\\cmeLettrinePlain{##1}{##2}}%
  \\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrinePlainAnte{##1}{##2}{##3}}%
}
"""
    if normalized == "baroqueinitials":
        return """% CME lettrine mode: Baroque Initials system font when available.
\\makeatletter
\\@ifundefined{IfFontExistsTF}{%
  \\PackageWarningNoLine{cme-lettrine}{\\string\\IfFontExistsTF not available; falling back to plain lettrine}%
  \\renewcommand{\\cmeLettrine}[2]{\\cmeLettrinePlain{#1}{#2}}%
  \\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrinePlainAnte{#1}{#2}{#3}}%
}{%
  \\IfFontExistsTF{Baroque Initials}{%
    \\@ifundefined{newfontfamily}{%
      \\PackageWarningNoLine{cme-lettrine}{\\string\\newfontfamily not available; falling back to plain lettrine}%
      \\renewcommand{\\cmeLettrine}[2]{\\cmeLettrinePlain{#1}{#2}}%
      \\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrinePlainAnte{#1}{#2}{#3}}%
    }{%
      \\newfontfamily\\cmeBaroqueInitials{Baroque Initials}%
      \\renewcommand{\\cmeLettrine}[2]{\\cmeLettrineWithFontHook{\\cmeBaroqueInitials}{#1}{#2}}%
      \\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrineWithFontHookAnte{\\cmeBaroqueInitials}{#1}{#2}{#3}}%
    }%
  }{%
    \\PackageWarningNoLine{cme-lettrine}{Baroque Initials font not found; falling back to plain lettrine}%
    \\renewcommand{\\cmeLettrine}[2]{\\cmeLettrinePlain{#1}{#2}}%
    \\renewcommand{\\cmeLettrineAnte}[3]{\\cmeLettrinePlainAnte{#1}{#2}{#3}}%
  }%
}
\\makeatother
"""
    if normalized == "none":
        return ""
    raise BuildProfileError(f"Unsupported lettrine mode '{mode}'")


def _resolve_token(value: str, root: Path, generated_paths: Mapping[str, str]) -> str:
    if value.startswith("{") and value.endswith("}"):
        key = value[1:-1]
        if key not in generated_paths:
            raise BuildProfileError(f"Unknown generated artifact placeholder '{value}'")
        return generated_paths[key]
    return _normalize_path(value, root)


def _profile_output(profile: Mapping[str, Any], input_path: Path, output_path: Path | str | None) -> str:
    if output_path is not None:
        return str(output_path)
    template = str(profile.get("output_template", "build/profile/{work}.{ext}"))
    return template.format(
        work=input_path.stem,
        profile=profile.get("name", "profile"),
        ext=profile.get("extension", profile.get("output_format", "out")),
    )


def resolve_plan(
    input_path: Path | str,
    profile_name: str,
    output_path: Path | str | None = None,
    pandoc_args: Sequence[str] = (),
    lettrine: str | None = None,
    root: Path | str | None = None,
    generated_paths: Mapping[str, str] | None = None,
) -> BuildPlan:
    config = load_build_config(root)
    repo_root = config.root
    profile = config.resolve_profile(profile_name)
    profile["name"] = profile_name

    source = Path(input_path)
    output = _profile_output(profile, source, output_path)
    user_args = _strip_passthrough_separator(pandoc_args)
    notes = str(profile.get("notes", "inline"))
    if notes not in {"drop", "inline", "footnotes"}:
        raise BuildProfileError(f"Profile '{profile_name}' has unsupported notes mode '{notes}'")

    effective_lettrine = normalize_lettrine_mode(str(lettrine if lettrine is not None else profile.get("lettrine", "none")))
    all_generated = dict(PLACEHOLDERS)
    if generated_paths:
        all_generated.update({key: str(value) for key, value in generated_paths.items()})

    modules: list[str] = []
    xml_flags: list[str] = []
    include_in_header: list[str] = []
    include_before_body: list[str] = []
    lua_filters: list[str] = []
    used_generated = {"html"}

    for module_name in profile.get("modules", []):
        name = str(module_name)
        if name == "lettrine" and effective_lettrine == "none":
            continue
        if name not in config.modules:
            raise BuildProfileError(f"Profile '{profile_name}' references unknown module '{name}'")
        module = config.modules[name]
        modules.append(name)
        for flag in module.get("xml_flags", []):
            _add_unique(xml_flags, str(flag))
        for generated in module.get("generated", []):
            used_generated.add(str(generated))
        for header in module.get("include_in_header", []):
            include_in_header.append(_resolve_token(str(header), repo_root, all_generated))
        for before_body in module.get("include_before_body", []):
            include_before_body.append(_resolve_token(str(before_body), repo_root, all_generated))
        for lua_filter in module.get("lua_filters", []):
            lua_filters.append(_resolve_token(str(lua_filter), repo_root, all_generated))

    xml_options: list[str] = []
    if notes == "drop":
        xml_options.append("--drop-notes")
    for flag in profile.get("xml_flags", []):
        _add_unique(xml_options, str(flag))
    for flag in xml_flags:
        _add_unique(xml_options, flag)
    if bool(profile.get("preserve_milestones", False)):
        _add_unique(xml_options, "--preserve-milestones")
    if bool(profile.get("strict", False)):
        _add_unique(xml_options, "--strict")

    xml_format = str(profile.get("xml_format", "auto"))
    input_string = str(input_path)
    html_command = ["python3", str(repo_root / "scripts" / "cme_xml_to_html.py"), "--format", xml_format]
    html_command.extend(xml_options)
    html_command.append(input_string)

    colophon_command: list[str] | None = None
    if "colophon_tex" in used_generated:
        colophon_command = ["python3", str(repo_root / "scripts" / "cme_xml_to_html.py"), "--format", xml_format]
        colophon_command.extend(xml_options)
        colophon_command.extend(["--colophon-tex", input_string])

    variables = _resolve_variables(profile, user_args)
    pandoc_command = ["pandoc", "--from", "html"]
    if bool(profile.get("standalone", True)):
        pandoc_command.append("--standalone")
    pandoc_command.extend([all_generated["html"], "--output", output])

    writer = profile.get("to")
    resolved_writer = None
    if writer and not has_pandoc_writer_option(user_args):
        resolved_writer = str(writer)
        pandoc_command.extend(["--to", resolved_writer])

    pdf_engine = profile.get("pdf_engine")
    resolved_pdf_engine = None
    if pdf_engine and not has_pandoc_option("--pdf-engine", user_args):
        resolved_pdf_engine = str(pdf_engine)
        pandoc_command.append(f"--pdf-engine={resolved_pdf_engine}")

    for variable in variables:
        pandoc_command.extend(["-V", f"{variable['name']}={variable['value']}"])

    toc_added = False
    if bool(profile.get("toc", False)) and not (
        has_pandoc_flag("--toc", user_args) or has_pandoc_flag("--table-of-contents", user_args)
    ):
        pandoc_command.append("--toc")
        toc_added = True

    for header in include_in_header:
        pandoc_command.extend(["--include-in-header", header])
    for before_body in include_before_body:
        pandoc_command.extend(["--include-before-body", before_body])
    for lua_filter in lua_filters:
        pandoc_command.extend(["--lua-filter", lua_filter])
    pandoc_command.extend(user_args)

    generated = {key: all_generated[key] for key in sorted(used_generated)}
    return BuildPlan(
        profile=profile_name,
        input=input_string,
        output=output,
        output_format=str(profile.get("output_format", profile.get("extension", "out"))),
        notes=notes,
        lettrine=effective_lettrine,
        modules=modules,
        generated=generated,
        xml={
            "format": xml_format,
            "options": xml_options,
            "html_command": html_command,
            "colophon_command": colophon_command,
        },
        pandoc={
            "command": pandoc_command,
            "writer": resolved_writer,
            "pdf_engine": resolved_pdf_engine,
            "variables": variables,
            "toc": toc_added,
            "include_in_header": include_in_header,
            "include_before_body": include_before_body,
            "lua_filters": lua_filters,
            "passthrough_args": user_args,
        },
    )


def run_single(
    input_path: Path | str,
    profile_name: str,
    output_path: Path | str,
    pandoc_args: Sequence[str] = (),
    lettrine: str | None = None,
    root: Path | str | None = None,
) -> BuildPlan:
    with tempfile.TemporaryDirectory(prefix="cme-build-") as temp_dir:
        temp = Path(temp_dir)
        generated_paths = {
            "html": str(temp / "source.cme.html"),
            "colophon_tex": str(temp / "source.cme-colophon.tex"),
            "lettrine_mode_tex": str(temp / "source.cme-lettrine.tex"),
        }
        plan = resolve_plan(
            input_path,
            profile_name=profile_name,
            output_path=output_path,
            pandoc_args=pandoc_args,
            lettrine=lettrine,
            root=root,
            generated_paths=generated_paths,
        )

        output = Path(plan.output)
        if output.parent != Path(""):
            output.parent.mkdir(parents=True, exist_ok=True)

        if plan.xml.get("colophon_command"):
            with Path(plan.generated["colophon_tex"]).open("w", encoding="utf-8") as stdout:
                subprocess.run(plan.xml["colophon_command"], check=True, stdout=stdout, text=True)

        if "lettrine_mode_tex" in plan.generated:
            Path(plan.generated["lettrine_mode_tex"]).write_text(
                lettrine_mode_header(plan.lettrine),
                encoding="utf-8",
            )

        with Path(plan.generated["html"]).open("w", encoding="utf-8") as stdout:
            subprocess.run(plan.xml["html_command"], check=True, stdout=stdout, text=True)

        subprocess.run(plan.pandoc["command"], check=True)
        return plan


POINTS_PER_INCH = 72.0
TRIM_SIZES_IN = {
    "5x8": (5.0, 8.0),
    "5x8in": (5.0, 8.0),
    "5x8-in": (5.0, 8.0),
}
BINDING_PAGE_LIMITS = {
    "paperback-perfect": (32, 800),
}
PAGE_SIZE_RE = re.compile(r"^Page(?:\s+\d+)?\s+size:\s+([0-9.]+) x ([0-9.]+) pts", re.MULTILINE)
PAGES_RE = re.compile(r"^Pages:\s+(\d+)", re.MULTILINE)
ENCRYPTED_RE = re.compile(r"^Encrypted:\s+(\S+)", re.MULTILINE)


def normalize_trim(trim: str) -> str:
    normalized = trim.lower().replace(" ", "").replace("×", "x")
    if normalized not in TRIM_SIZES_IN:
        known = ", ".join(sorted(TRIM_SIZES_IN))
        raise BuildProfileError(f"Unsupported trim '{trim}'. Known trims: {known}")
    return normalized


def trim_size_inches(trim: str) -> tuple[float, float]:
    return TRIM_SIZES_IN[normalize_trim(trim)]


def expected_lulu_page_size_points(trim: str, bleed: float = 0.125) -> tuple[float, float]:
    width, height = trim_size_inches(trim)
    return ((width + 2 * bleed) * POINTS_PER_INCH, (height + 2 * bleed) * POINTS_PER_INCH)


def _run_text_command(command: Sequence[str]) -> str:
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError as exc:
        tool = command[0] if command else "command"
        raise BuildProfileError(f"{tool} not found; install poppler-utils and ensure it is on PATH") from exc
    except subprocess.CalledProcessError as exc:
        tool = command[0] if command else "command"
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        detail = stderr or stdout or "no diagnostic output"
        raise BuildProfileError(f"{tool} failed with exit code {exc.returncode}: {detail}") from exc
    return result.stdout


def _parse_required_int(pattern: re.Pattern[str], text: str, label: str) -> int:
    match = pattern.search(text)
    if not match:
        raise BuildProfileError(f"Could not parse {label} from pdfinfo output")
    return int(match.group(1))


def _parse_page_size_points(text: str) -> tuple[float, float]:
    match = PAGE_SIZE_RE.search(text)
    if not match:
        raise BuildProfileError("Could not parse page size from pdfinfo output")
    return (float(match.group(1)), float(match.group(2)))


def _parse_encrypted(text: str) -> str:
    match = ENCRYPTED_RE.search(text)
    if not match:
        return "unknown"
    return match.group(1).lower()


def _font_rows(pdffonts_output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in pdffonts_output.splitlines():
        if not line.strip() or line.startswith("name ") or line.startswith("----"):
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        rows.append({"name": parts[0], "embedded": parts[-5], "subset": parts[-4], "unicode": parts[-3]})
    return rows


def preflight_lulu_pdf(
    pdf_path: Path | str,
    trim: str = "5x8",
    binding: str = "paperback-perfect",
    bleed: float = 0.125,
    tolerance_points: float = 0.5,
) -> dict[str, Any]:
    path = Path(pdf_path)
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    if not path.exists():
        add_check("file-exists", False, f"Missing PDF: {path}")
        expected_size = expected_lulu_page_size_points(trim, bleed)
        return {
            "pdf": str(path),
            "trim": trim,
            "binding": binding,
            "bleed_in": bleed,
            "pages": None,
            "page_size_points": None,
            "expected_page_size_points": {"width": expected_size[0], "height": expected_size[1]},
            "encrypted": None,
            "fonts": [],
            "checks": checks,
            "passed": False,
        }
    add_check("file-exists", True, str(path))

    info = _run_text_command(["pdfinfo", str(path)])
    pages = _parse_required_int(PAGES_RE, info, "page count")
    first_page_size = _parse_page_size_points(info)
    encrypted = _parse_encrypted(info)
    expected_size = expected_lulu_page_size_points(trim, bleed)
    page_size_ok = all(abs(actual - expected) <= tolerance_points for actual, expected in zip(first_page_size, expected_size))
    add_check(
        "page-size",
        page_size_ok,
        f"first page {first_page_size[0]:.2f} x {first_page_size[1]:.2f} pt; expected "
        f"{expected_size[0]:.2f} x {expected_size[1]:.2f} pt for trim {trim} with {bleed:g}in bleed",
    )

    unique_page_sizes: set[tuple[float, float]] = set()
    for page in range(1, pages + 1):
        page_info = _run_text_command(["pdfinfo", "-f", str(page), "-l", str(page), str(path)])
        size = _parse_page_size_points(page_info)
        unique_page_sizes.add((round(size[0], 2), round(size[1], 2)))
    add_check(
        "uniform-page-size",
        len(unique_page_sizes) == 1,
        f"unique page sizes: {sorted(unique_page_sizes)}",
    )

    add_check("not-encrypted", encrypted == "no", f"Encrypted: {encrypted}")

    if binding not in BINDING_PAGE_LIMITS:
        raise BuildProfileError(f"Unsupported binding '{binding}'. Known bindings: {', '.join(sorted(BINDING_PAGE_LIMITS))}")
    minimum, maximum = BINDING_PAGE_LIMITS[binding]
    add_check("page-count-range", minimum <= pages <= maximum, f"{pages} pages; {binding} requires {minimum}-{maximum}")

    fonts_output = _run_text_command(["pdffonts", str(path)])
    fonts = _font_rows(fonts_output)
    unembedded = [font["name"] for font in fonts if font["embedded"].lower() != "yes"]
    add_check(
        "fonts-embedded",
        not unembedded,
        "all fonts embedded" if not unembedded else "unembedded fonts: " + ", ".join(unembedded),
    )

    return {
        "pdf": str(path),
        "trim": trim,
        "binding": binding,
        "bleed_in": bleed,
        "pages": pages,
        "page_size_points": {"width": first_page_size[0], "height": first_page_size[1]},
        "expected_page_size_points": {"width": expected_size[0], "height": expected_size[1]},
        "encrypted": encrypted,
        "fonts": fonts,
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
    }


def emit_preflight(result: Mapping[str, Any], json_output: bool) -> None:
    if json_output:
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    status = "PASS" if result.get("passed") else "FAIL"
    print(f"{status}: {result.get('pdf')}")
    print(f"pages: {result.get('pages')}  trim: {result.get('trim')}  binding: {result.get('binding')}")
    size = result.get("page_size_points")
    expected = result.get("expected_page_size_points")
    if isinstance(size, Mapping) and isinstance(expected, Mapping):
        print(
            "page size: "
            f"{size.get('width'):.2f} x {size.get('height'):.2f} pt "
            f"(expected {expected.get('width'):.2f} x {expected.get('height'):.2f} pt)"
        )
    elif isinstance(expected, Mapping):
        print(
            "page size: unavailable "
            f"(expected {expected.get('width'):.2f} x {expected.get('height'):.2f} pt)"
        )
    else:
        print("page size: unavailable")
    for check in result.get("checks", []):
        marker = "✓" if check["passed"] else "✗"
        print(f"{marker} {check['name']}: {check['detail']}")


def _add_common_build_args(parser: argparse.ArgumentParser, require_output: bool) -> None:
    parser.add_argument("input", type=Path, help="CME XML input file")
    parser.add_argument("--profile", required=True, help="Build profile name")
    parser.add_argument("--output", type=Path, required=require_output, help="Output path")
    parser.add_argument("--lettrine", help="Override profile lettrine mode")


def make_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-profiles", help="List available public profiles")
    list_parser.add_argument("--json", action="store_true", help="Emit profile data as JSON")

    plan_parser = subparsers.add_parser("plan", help="Print a JSON build plan")
    _add_common_build_args(plan_parser, require_output=False)

    single_parser = subparsers.add_parser("single", help="Build one input with one profile")
    _add_common_build_args(single_parser, require_output=True)

    preflight_parser = subparsers.add_parser("preflight-lulu", help="Preflight a Lulu interior PDF")
    preflight_parser.add_argument("pdf", type=Path, help="Interior PDF to inspect")
    preflight_parser.add_argument("--trim", default="5x8", help="Trim size, currently 5x8")
    preflight_parser.add_argument(
        "--binding",
        default="paperback-perfect",
        help="Binding/product rule, currently paperback-perfect",
    )
    preflight_parser.add_argument("--bleed", type=float, default=0.125, help="Bleed in inches on each edge")
    preflight_parser.add_argument("--json", action="store_true", help="Emit preflight result as JSON")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = make_arg_parser()
    args, unknown = parser.parse_known_args(argv)
    passthrough_args = _strip_passthrough_separator(unknown)

    try:
        if args.command == "list-profiles":
            if passthrough_args:
                raise BuildProfileError(f"Unexpected arguments for list-profiles: {' '.join(passthrough_args)}")
            config = load_build_config()
            if args.json:
                payload = [
                    {"name": name, "description": config.resolve_profile(name).get("description", "")}
                    for name in config.profile_names()
                ]
                json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
                sys.stdout.write("\n")
            else:
                for name in config.profile_names():
                    print(name)
            return 0

        if args.command == "plan":
            plan = resolve_plan(
                args.input,
                profile_name=args.profile,
                output_path=args.output,
                pandoc_args=passthrough_args,
                lettrine=args.lettrine,
            )
            json.dump(plan.to_json(), sys.stdout, indent=2, ensure_ascii=False)
            sys.stdout.write("\n")
            return 0

        if args.command == "single":
            run_single(
                args.input,
                profile_name=args.profile,
                output_path=args.output,
                pandoc_args=passthrough_args,
                lettrine=args.lettrine,
            )
            return 0

        if args.command == "preflight-lulu":
            if passthrough_args:
                raise BuildProfileError(f"Unexpected arguments for preflight-lulu: {' '.join(passthrough_args)}")
            result = preflight_lulu_pdf(args.pdf, trim=args.trim, binding=args.binding, bleed=args.bleed)
            emit_preflight(result, args.json)
            return 0 if result["passed"] else 1

        parser.error(f"Unknown command: {args.command}")
    except BuildProfileError as exc:
        print(f"cme-build: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
