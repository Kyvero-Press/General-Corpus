import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lxml import etree


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "cme_xml_to_html.py"
SPEC = importlib.util.spec_from_file_location("cme_xml_to_html", MODULE_PATH)
cme_xml_to_html = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cme_xml_to_html
assert SPEC.loader is not None
SPEC.loader.exec_module(cme_xml_to_html)


def render_lg(xml: str, **option_overrides: object) -> str:
    element = etree.fromstring(xml.encode("utf-8"))
    options = cme_xml_to_html.Options(**option_overrides)
    return cme_xml_to_html.render_lg(element, options)


class RenderLgContinuationTests(unittest.TestCase):
    def test_exact_four_space_unnumbered_l_merges_with_previous_line(self) -> None:
        html = render_lg(
            """
            <LG>
              <L>I schal telle hit as-tit, as I in toun herde,</L>
              <L>    with tonge,</L>
              <L>  As hit is stad and stoken</L>
            </LG>
            """
        )

        self.assertIn("I schal telle hit as-tit, as I in toun herde, with tonge,", html)
        self.assertNotIn("herde,<br />\nwith tonge,", html)
        self.assertIn("with tonge,<br />\nAs hit is stad and stoken", html)

    def test_two_and_six_space_lines_remain_separate(self) -> None:
        html = render_lg(
            """
            <LG>
              <L>Base line</L>
              <L>  Wheel line</L>
              <L>AMEN.</L>
              <L>      HONY SOYT QUI MAL PENCE.</L>
            </LG>
            """
        )

        self.assertIn("Base line<br />\nWheel line", html)
        self.assertIn("AMEN.<br />\nHONY SOYT QUI MAL PENCE.", html)
        self.assertNotIn("AMEN. HONY SOYT QUI MAL PENCE.", html)

    def test_numbered_line_with_four_spaces_remains_separate(self) -> None:
        html = render_lg(
            """
            <LG>
              <L N="5">Base line</L>
              <L N="6">    Numbered line</L>
            </LG>
            """,
            include_verse_line_metadata=True,
        )

        self.assertIn('<span class="verse-line" data-line-number="5">Base line</span>', html)
        self.assertIn('<span class="verse-line" data-line-number="6">Numbered line</span>', html)
        self.assertIn("</span><br />\n<span", html)
        self.assertEqual(html.count('class="verse-line"'), 2)

    def test_metadata_mode_merged_line_has_single_span_and_base_line_number(self) -> None:
        html = render_lg(
            """
            <LG>
              <L N="5">Base line</L>
              <L>    continuation text</L>
            </LG>
            """,
            include_verse_line_metadata=True,
        )

        self.assertIn(
            '<span class="verse-line" data-line-number="5">Base line continuation text</span>',
            html,
        )
        self.assertEqual(html.count('class="verse-line"'), 1)
        self.assertNotIn("continuation text</span><br", html)

    def test_inline_markup_in_continuation_is_preserved(self) -> None:
        html = render_lg(
            """
            <LG>
              <L>Base line</L>
              <L>    <HI1 REND="i">marked</HI1> tail</L>
            </LG>
            """
        )

        self.assertIn("Base line <em>marked</em> tail", html)
        self.assertNotIn("Base line<br />", html)


class PandocCmeXmlMarkdownTests(unittest.TestCase):
    def test_default_markdown_output_is_reader_facing_without_source_attrs(self) -> None:
        if shutil.which("pandoc") is None:
            self.skipTest("pandoc is not installed")

        xml = """
        <DLPSTEXTCLASS>
          <TEXT><BODY><DIV1 TYPE="passus" N="I" NODE="fixture:1">
            <HEAD>Passus I</HEAD>
            <LG TYPE="verse-paragraph" N="1">
              <L>Base line,<NOTE1 N="1">editorial note</NOTE1></L>
              <L>    continuation text,</L>
              <L>  wheel line</L>
            </LG>
            <TABLE><ROW><CELL>Cell A</CELL><CELL>Cell B</CELL></ROW></TABLE>
          </DIV1></BODY></TEXT>
        </DLPSTEXTCLASS>
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "fixture.xml"
            output = temp / "fixture.md"
            source.write_text(xml, encoding="utf-8")

            subprocess.run(
                [str(MODULE_PATH.parent / "pandoc-cme-xml"), str(source), str(output)],
                check=True,
                cwd=MODULE_PATH.parents[1],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            markdown = output.read_text(encoding="utf-8")

        self.assertIn(r"Base line,\[editorial note\] continuation text,", markdown)
        self.assertNotRegex(markdown, r"(?m)^:+ \{", msg=markdown)
        self.assertNotIn("data-type=", markdown)
        self.assertNotIn("fixture:1", markdown)
        self.assertNotIn("{.lg", markdown)
        self.assertNotIn("<span", markdown)
        self.assertNotIn("[TABLE]", markdown)
        self.assertIn("Cell A", markdown)
        self.assertIn("Cell B", markdown)
        self.assertIn("|", markdown)


if __name__ == "__main__":
    unittest.main()
