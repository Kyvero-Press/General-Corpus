import contextlib
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "cme_build_profiles.py"
SPEC = importlib.util.spec_from_file_location("cme_build_profiles", MODULE_PATH)
cme_build_profiles = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cme_build_profiles
assert SPEC.loader is not None
SPEC.loader.exec_module(cme_build_profiles)


REPO_ROOT = MODULE_PATH.parents[1]
GAWAIN = REPO_ROOT / "CME" / "source" / "CME_from_OTA" / "Gawain.xml"


def basenames(paths: list[str]) -> list[str]:
    return [path if path.startswith("{") else Path(path).name for path in paths]


class CmeBuildProfilesTests(unittest.TestCase):
    def resolve(self, profile: str, **kwargs: object):
        return cme_build_profiles.resolve_plan(
            GAWAIN,
            profile_name=profile,
            root=REPO_ROOT,
            **kwargs,
        ).to_json()

    def test_list_profiles_includes_initial_public_profiles(self) -> None:
        config = cme_build_profiles.load_build_config(REPO_ROOT)

        self.assertEqual(
            config.profile_names(),
            ["epub", "lulu-paperback-5x8-print-pdf", "print-pdf", "reader-pdf-no-notes"],
        )

    def test_print_pdf_expands_current_latex_defaults_and_order(self) -> None:
        plan = self.resolve("print-pdf", output_path="build/profile/Gawain.pdf")

        self.assertEqual(plan["profile"], "print-pdf")
        self.assertEqual(plan["output_format"], "pdf")
        self.assertEqual(plan["notes"], "footnotes")
        self.assertEqual(
            plan["modules"],
            [
                "book-frontmatter",
                "colophon",
                "running-heads",
                "lettrine",
                "footnotes",
                "verse-lines",
                "pagebreaks",
            ],
        )
        self.assertEqual(
            basenames(plan["pandoc"]["include_in_header"]),
            [
                "pandoc-book-frontmatter.tex",
                "pandoc-latex-lettrine.tex",
                "{temp_lettrine_mode_tex}",
                "pandoc-latex-verse-lines.tex",
                "pandoc-latex-pagebreaks.tex",
            ],
        )
        self.assertEqual(
            basenames(plan["pandoc"]["include_before_body"]),
            ["{temp_colophon_tex}"],
        )
        self.assertEqual(
            basenames(plan["pandoc"]["lua_filters"]),
            [
                "pandoc-latex-running-heads.lua",
                "pandoc-latex-lettrine.lua",
                "pandoc-latex-footnotes.lua",
                "pandoc-latex-verse-lines.lua",
                "pandoc-latex-pagebreaks.lua",
            ],
        )
        self.assertIn("--omit-source-metadata", plan["xml"]["options"])
        self.assertIn("--verse-line-metadata", plan["xml"]["options"])
        self.assertNotIn("--drop-notes", plan["xml"]["options"])
        self.assertEqual(plan["pandoc"]["pdf_engine"], "xelatex")
        self.assertTrue(plan["pandoc"]["toc"])

    def test_repeated_pandoc_variables_are_preserved(self) -> None:
        plan = self.resolve("print-pdf")

        variables = plan["pandoc"]["variables"]
        mainfont_options = [
            variable["value"] for variable in variables if variable["name"] == "mainfontoptions"
        ]
        self.assertEqual(
            mainfont_options,
            [
                "BoldFont=Junicode-Bold.otf",
                "ItalicFont=Junicode-Italic.otf",
                "BoldItalicFont=Junicode-BoldItalic.otf",
            ],
        )
        geometry = [variable["value"] for variable in variables if variable["name"] == "geometry"]
        self.assertEqual(geometry, ["paperwidth=5in", "paperheight=8in"])

    def test_user_geometry_or_papersize_suppresses_default_five_by_eight_geometry(self) -> None:
        geometry_plan = self.resolve(
            "print-pdf",
            pandoc_args=["-V", "geometry=paperwidth=6in"],
        )
        papersize_plan = self.resolve(
            "print-pdf",
            pandoc_args=["-V", "papersize=a5"],
        )

        for plan in (geometry_plan, papersize_plan):
            variables = [(variable["name"], variable["value"]) for variable in plan["pandoc"]["variables"]]
            self.assertNotIn(("geometry", "paperwidth=5in"), variables)
            self.assertNotIn(("geometry", "paperheight=8in"), variables)
        self.assertEqual(geometry_plan["pandoc"]["passthrough_args"], ["-V", "geometry=paperwidth=6in"])
        self.assertEqual(papersize_plan["pandoc"]["passthrough_args"], ["-V", "papersize=a5"])

    def test_reader_pdf_drops_notes_and_omits_footnote_filter(self) -> None:
        plan = self.resolve("reader-pdf-no-notes", output_path="build/profile/Gawain.reader.pdf")

        self.assertEqual(plan["notes"], "drop")
        self.assertIn("--drop-notes", plan["xml"]["options"])
        self.assertNotIn("footnotes", plan["modules"])
        self.assertNotIn("pandoc-latex-footnotes.lua", basenames(plan["pandoc"]["lua_filters"]))
        self.assertIn("--omit-source-metadata", plan["xml"]["options"])
        self.assertIn("--verse-line-metadata", plan["xml"]["options"])

    def test_lulu_paperback_profile_uses_bleed_sized_geometry(self) -> None:
        plan = self.resolve(
            "lulu-paperback-5x8-print-pdf",
            output_path="build/profile/Gawain.lulu.pdf",
        )

        self.assertEqual(plan["output_format"], "pdf")
        self.assertEqual(plan["notes"], "footnotes")
        variables = [(variable["name"], variable["value"]) for variable in plan["pandoc"]["variables"]]
        self.assertIn(("geometry", "paperwidth=5.25in"), variables)
        self.assertIn(("geometry", "paperheight=8.25in"), variables)
        self.assertIn(("geometry", "layoutwidth=5in"), variables)
        self.assertIn(("geometry", "layoutheight=8in"), variables)
        self.assertIn(("geometry", "layouthoffset=0.125in"), variables)
        self.assertIn(("geometry", "layoutvoffset=0.125in"), variables)
        self.assertEqual(
            cme_build_profiles.expected_lulu_page_size_points("5x8"),
            (378.0, 594.0),
        )

    def test_preflight_page_size_parser_accepts_single_page_pdfinfo_output(self) -> None:
        self.assertEqual(
            cme_build_profiles._parse_page_size_points("Page    1 size:  378 x 594 pts\n"),
            (378.0, 594.0),
        )

    def test_epub_uses_epub3_without_latex_modules_or_filters(self) -> None:
        plan = self.resolve("epub", output_path="build/profile/Gawain.epub")

        self.assertEqual(plan["output_format"], "epub")
        self.assertEqual(plan["notes"], "inline")
        self.assertEqual(plan["modules"], [])
        self.assertEqual(plan["xml"]["options"], [])
        self.assertEqual(plan["pandoc"]["writer"], "epub3")
        self.assertEqual(plan["pandoc"]["include_in_header"], [])
        self.assertEqual(plan["pandoc"]["include_before_body"], [])
        self.assertEqual(plan["pandoc"]["lua_filters"], [])
        self.assertIn("--to", plan["pandoc"]["command"])
        self.assertNotIn("--pdf-engine=xelatex", plan["pandoc"]["command"])

    def test_plan_json_is_serializable(self) -> None:
        plan = self.resolve("print-pdf")

        json.dumps(plan, ensure_ascii=False)

    def test_list_profiles_rejects_unexpected_args_before_stdout(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exit_code = cme_build_profiles.main(["list-profiles", "--bogus"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Unexpected arguments for list-profiles", stderr.getvalue())

    def test_preflight_missing_pdf_reports_failure_without_crashing(self) -> None:
        missing = REPO_ROOT / "build" / "does-not-exist.pdf"
        stdout = io.StringIO()

        result = cme_build_profiles.preflight_lulu_pdf(missing)
        with contextlib.redirect_stdout(stdout):
            cme_build_profiles.emit_preflight(result, json_output=False)

        self.assertFalse(result["passed"])
        self.assertIsNone(result["page_size_points"])
        output = stdout.getvalue()
        self.assertIn("FAIL", output)
        self.assertIn("page size: unavailable", output)
        self.assertIn("Missing PDF", output)

    def test_run_text_command_reports_missing_poppler_tool(self) -> None:
        with mock.patch.object(cme_build_profiles.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(cme_build_profiles.BuildProfileError, "pdfinfo not found"):
                cme_build_profiles._run_text_command(["pdfinfo", "missing.pdf"])

    def test_run_text_command_reports_stderr_from_poppler_tool(self) -> None:
        error = cme_build_profiles.subprocess.CalledProcessError(
            1,
            ["pdfinfo", "bad.pdf"],
            output="",
            stderr="Syntax Error: not a PDF",
        )
        with mock.patch.object(cme_build_profiles.subprocess, "run", side_effect=error):
            with self.assertRaisesRegex(cme_build_profiles.BuildProfileError, "Syntax Error: not a PDF"):
                cme_build_profiles._run_text_command(["pdfinfo", "bad.pdf"])

    def test_preflight_cli_reports_tool_errors_without_silent_exit(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with mock.patch.object(
            cme_build_profiles,
            "_run_text_command",
            side_effect=cme_build_profiles.BuildProfileError("pdfinfo failed with exit code 1: broken PDF"),
        ):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = cme_build_profiles.main(["preflight-lulu", str(REPO_ROOT / ".gitignore"), "--json"])

        self.assertEqual(exit_code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("pdfinfo failed with exit code 1: broken PDF", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
