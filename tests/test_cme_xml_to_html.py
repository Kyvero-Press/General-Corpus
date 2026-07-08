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


class RenderLgTrailingCloserTests(unittest.TestCase):
    def test_trailing_simple_closer_preserves_optimized_verse_lines(self) -> None:
        html = render_lg(
            """
            <LG>
              <L N="5">Þe feste of corpus day cristy</L>
              <L>Þe hyȝe feste of þe holy sacrament</L>
              <CLOSER>Ame<HI REND="italic">n.</HI></CLOSER>
            </LG>
            """,
            include_verse_line_metadata=True,
        )

        self.assertIn('<p class="verse-lines">', html)
        self.assertIn(
            '<span class="verse-line" data-line-number="5">Þe feste of corpus day cristy</span><br />\n'
            '<span class="verse-line">Þe hyȝe feste of þe holy sacrament</span>',
            html,
        )
        self.assertIn('<p class="closer">Ame<em>n.</em></p>', html)
        self.assertNotIn('<div class="l"', html)

    def test_lg_with_head_still_uses_generic_fallback(self) -> None:
        html = render_lg(
            """
            <LG>
              <HEAD>Head inside group</HEAD>
              <L>First line</L>
              <L>Second line</L>
            </LG>
            """
        )

        self.assertNotIn('<p class="verse-lines">', html)
        self.assertIn('<h3>Head inside group</h3>', html)
        self.assertIn('<div class="l">First line</div>', html)

    def test_non_trailing_closer_still_uses_generic_fallback(self) -> None:
        html = render_lg(
            """
            <LG>
              <L>First line</L>
              <CLOSER>Amen.</CLOSER>
              <L>Second line</L>
            </LG>
            """
        )

        self.assertNotIn('<p class="verse-lines">', html)
        self.assertIn('<div class="l">First line</div>', html)
        self.assertIn('<p class="closer">Amen.</p>', html)
        self.assertIn('<div class="l">Second line</div>', html)


class PandocCmeXmlLatexLettrineTests(unittest.TestCase):
    def render_latex(self, xml: str) -> str:
        if shutil.which("pandoc") is None:
            self.skipTest("pandoc is not installed")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "fixture.xml"
            output = temp / "fixture.tex"
            source.write_text(xml, encoding="utf-8")

            subprocess.run(
                [str(MODULE_PATH.parent / "pandoc-cme-xml"), str(source), str(output)],
                check=True,
                cwd=MODULE_PATH.parents[1],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return output.read_text(encoding="utf-8")

    def render_html_latex_fragment(self, html: str) -> str:
        if shutil.which("pandoc") is None:
            self.skipTest("pandoc is not installed")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "fixture.html"
            output = temp / "fixture.tex"
            source.write_text(html, encoding="utf-8")

            subprocess.run(
                [
                    "pandoc",
                    "--from",
                    "html",
                    "--to",
                    "latex",
                    "--lua-filter",
                    str(MODULE_PATH.parent / "pandoc-latex-lettrine.lua"),
                    str(source),
                    "-o",
                    str(output),
                ],
                check=True,
                cwd=MODULE_PATH.parents[1],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            return output.read_text(encoding="utf-8")

    def test_lineated_blocks_do_not_receive_prose_lettrines(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1 TYPE="poem"><HEAD>Lineated Fixture</HEAD>
                <L N="1">at london in englonde</L>
                <L N="2">sythen crist suffride</L>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertNotIn(r"\cmeLettrine{a}{t} london", latex)
        self.assertIn("at london in englonde", latex)
        self.assertIn("sythen crist suffride", latex)

    def test_opener_apparatus_does_not_receive_dropcap_before_body(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1 TYPE="poem"><HEAD>Work</HEAD>
                <OPENER>
                  <BYLINE>Oxford Text Archive copy.</BYLINE>
                  <DATELINE>February, 2023</DATELINE>
                </OPENER>
                <P>In Dei nomine begins the body.</P>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertNotIn(r"\cmeLettrine{O}{xford} Text Archive copy.", latex)
        self.assertIn(r"\cmeLettrine{I}{n} Dei nomine begins the body.", latex)

    def test_egilds_toc_list_sections_do_not_receive_dropcaps(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><FRONT>
                <DIV1 TYPE="TOC"><HEAD>Contents</HEAD>
                  <LIST><HEAD>PART I.</HEAD>
                    <ITEM>Gild Ordinances from Returns made, in English.</ITEM>
                  </LIST>
                </DIV1>
                <DIV1 TYPE="preface"><HEAD>Preface</HEAD>
                  <P>IN order to study the English labour-question.</P>
                </DIV1>
              </FRONT></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn("Gild Ordinances from Returns made, in English.", latex)
        self.assertNotIn(r"\cmeLettrine{G}{ild} Ordinances", latex)
        self.assertIn(r"\cmeLettrine{I}{N} order to study", latex)

    def test_egilds_argument_sections_do_not_receive_dropcaps(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><FRONT>
                <DIV1 TYPE="argument"><HEAD>Argument</HEAD>
                  <P>Origin of the Religious Gilds, p. lxxxi. The Capitulary.</P>
                </DIV1>
                <DIV1 TYPE="preface"><HEAD>Preface</HEAD>
                  <P>IN order to study the English labour-question.</P>
                </DIV1>
              </FRONT></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn("Origin of the Religious Gilds", latex)
        self.assertNotIn(r"\cmeLettrine{O}{rigin} of the Religious Gilds", latex)
        self.assertIn(r"\cmeLettrine{I}{N} order to study", latex)

    def test_title_page_of_part_sections_do_not_receive_dropcaps(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY>
                <DIV1 TYPE="title page of part"><HEAD>Part Title</HEAD>
                  <P>Her begynnythe a noble boke.</P>
                </DIV1>
                <DIV1 TYPE="chapter"><HEAD>Chapter</HEAD>
                  <P>Alpha prose begins here.</P>
                </DIV1>
              </BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn("Her begynnythe a noble boke.", latex)
        self.assertNotIn(r"\cmeLettrine{H}{er} begynnythe", latex)
        before_title_section = latex.split(r"\section{Part Title}", 1)[0].rsplit("\n", 4)[-1]
        self.assertNotIn(r"\Needspace{20\baselineskip}%", before_title_section)
        self.assertIn(r"\cmeLettrine{A}{lpha} prose begins here.", latex)

    def test_list_of_contents_sections_do_not_receive_dropcaps(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><FRONT>
                <DIV1 TYPE="list of contents"><HEAD>List of Contents</HEAD>
                  <P>Alpha table entry should stay plain.</P>
                </DIV1>
                <DIV1 TYPE="preface"><HEAD>Preface</HEAD>
                  <P>Beta prose begins here.</P>
                </DIV1>
              </FRONT></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn("Alpha table entry should stay plain.", latex)
        self.assertNotIn(r"\cmeLettrine{A}{lpha} table entry", latex)
        self.assertIn(r"\cmeLettrine{B}{eta} prose begins here.", latex)

    def test_titlepage_and_contents_type_variants_do_not_receive_dropcaps(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><FRONT>
                <DIV1 TYPE="table of contents"><HEAD>Table of Contents</HEAD>
                  <P>Alpha contents row should stay plain.</P>
                </DIV1>
                <DIV1 TYPE="volume title page"><HEAD>Volume Title</HEAD>
                  <P>Beta volume title should stay plain.</P>
                </DIV1>
                <DIV1 TYPE="verso of title page"><HEAD>Verso</HEAD>
                  <P>Gamma verso note should stay plain.</P>
                </DIV1>
                <DIV1 TYPE="title-page"><HEAD>Hyphenated Title Page</HEAD>
                  <P>Delta title page should stay plain.</P>
                </DIV1>
                <DIV1 TYPE="preface"><HEAD>Preface</HEAD>
                  <P>Epsilon prose begins here.</P>
                </DIV1>
              </FRONT></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertNotIn(r"\cmeLettrine{A}{lpha} contents row", latex)
        self.assertNotIn(r"\cmeLettrine{B}{eta} volume title", latex)
        self.assertNotIn(r"\cmeLettrine{G}{amma} verso note", latex)
        self.assertNotIn(r"\cmeLettrine{D}{elta} title page", latex)
        self.assertIn(r"\cmeLettrine{E}{psilon} prose begins here.", latex)

    def test_raw_html_type_attribute_uses_same_nonrunning_classifier(self) -> None:
        latex = self.render_html_latex_fragment(
            """
            <section type="title page of part">
              <h1>Part Title</h1>
              <p>Her raw title should stay plain.</p>
            </section>
            <section>
              <h1>Chapter</h1>
              <p>Alpha prose begins here.</p>
            </section>
            """
        )

        self.assertNotIn(r"\cmeLettrine{H}{er} raw title", latex)
        self.assertIn(r"\cmeLettrine{A}{lpha} prose begins here.", latex)

    def test_cme00065_style_nested_initial_heads_are_in_pdf_title(self) -> None:
        latex = self.render_latex(
            """
            <ETS>
              <TEMPHEAD />
              <EEBO><IDG><BIBNO>CME00065</BIBNO></IDG><TEXT><BODY>
                <DIV1 TYPE="poem">
                  <PB N="16" REF="1" />
                  <DIV2 N="H." TYPE="version">
                    <HEAD>H.</HEAD>
                    <HEAD>DE TYOPHILO CLERICO NARRATIO.</HEAD>
                    <LG><L>A bisschop wond biȝond þe se,</L></LG>
                  </DIV2>
                </DIV1>
              </BODY></TEXT></EEBO>
            </ETS>
            """
        )

        self.assertIn("pdftitle={H. --- DE TYOPHILO CLERICO NARRATIO.}", latex)
        self.assertIn(r"\title{H. --- DE TYOPHILO CLERICO NARRATIO.}", latex)

    def test_running_head_page_numbers_move_to_footer(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1 TYPE="poem"><HEAD>Lineated Fixture</HEAD>
                <P>Text body for a numbered page.</P>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        fancyhead_lines = [line for line in latex.splitlines() if r"\fancyhead" in line]
        self.assertTrue(fancyhead_lines)
        for line in fancyhead_lines:
            self.assertNotIn(r"\thepage", line)
        self.assertIn(r"\fancyfoot[C]{\small\thepage}", latex)

    def test_lettrines_reserve_space_before_page_breaks(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY>
                <P>Alpha paragraph starts a section.</P>
              </BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn(r"\usepackage{needspace}", latex)
        self.assertIn(r"\Needspace{6\baselineskip}%", latex)
        self.assertNotIn(r"\Needspace{20\baselineskip}%", latex)

    def test_heading_before_dropcap_reserves_section_opening_space(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1 TYPE="prose"><HEAD>Fixture Heading</HEAD>
                <P>Alpha paragraph starts a section.</P>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        section_needspace = r"\Needspace{20\baselineskip}%"
        dropcap_needspace = r"\Needspace{6\baselineskip}%"
        section = r"\section{Fixture Heading}"
        lettrine = r"\cmeLettrine{A}{lpha} paragraph starts a section."
        self.assertIn(section_needspace, latex)
        self.assertLess(latex.index(section_needspace), latex.index(section))
        self.assertLess(latex.index(section), latex.index(dropcap_needspace, latex.index(section)))
        self.assertLess(latex.index(dropcap_needspace, latex.index(section)), latex.index(lettrine))

    def test_punctuation_prefixed_dropcap_keeps_prefix_with_initial(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY>
                <P>"Alpha paragraph starts with quote.</P>
              </BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        needspace = r"\Needspace{6\baselineskip}%"
        quoted_dropcap = r'\cmeLettrineAnte{"}{A}{lpha} paragraph starts with quote.'
        self.assertIn(needspace, latex)
        self.assertIn(quoted_dropcap, latex)
        self.assertLess(latex.index(needspace), latex.index(quoted_dropcap))
        self.assertNotIn(r'"\cmeLettrine{A}{lpha}', latex)

    def test_separate_leading_quote_is_absorbed_into_emphasized_dropcap(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY>
                <P>" <HI REND="i">Dixit Mater Iesu</HI> follows.</P>
              </BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn(r'\emph{\cmeLettrineAnte{"}{D}{ixit} Mater Iesu}', latex)
        self.assertNotIn(r'" \emph{\cmeLettrine{D}{ixit}', latex)

    def test_lineated_heading_does_not_reserve_dropcap_opening_space(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1 TYPE="poem"><HEAD>Lineated Fixture</HEAD>
                <L N="1">at london in englonde</L>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertNotIn(r"\Needspace{20\baselineskip}%", latex)

    def test_hard_line_break_opening_does_not_receive_or_defer_dropcap(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1 TYPE="sermon"><HEAD>Line Break Fixture</HEAD>
                <P>First preserved line<LB />second preserved line</P>
                <P>Later prose should not receive a deferred drop cap.</P>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn(r"First preserved line\\", latex)
        self.assertNotIn(r"\Needspace{20\baselineskip}%", latex)
        self.assertNotIn(r"\Needspace{6\baselineskip}%", latex)
        self.assertNotIn(r"\cmeLettrine{F}{irst} preserved line", latex)
        self.assertNotIn(r"\cmeLettrine{L}{ater} prose", latex)

    def test_needspace_fallbacks_are_idempotent(self) -> None:
        lettrine_header = (MODULE_PATH.parent / "pandoc-latex-lettrine.tex").read_text(
            encoding="utf-8"
        )
        pagebreak_header = (MODULE_PATH.parent / "pandoc-latex-pagebreaks.tex").read_text(
            encoding="utf-8"
        )

        self.assertIn(r"\providecommand{\Needspace}[1]{}", lettrine_header)
        self.assertIn(r"\providecommand{\Needspace}[1]{}", pagebreak_header)
        self.assertNotIn(r"\newcommand{\Needspace}[1]{}", lettrine_header)
        self.assertNotIn(r"\newcommand{\Needspace}[1]{}", pagebreak_header)
        self.assertNotIn(r"\Needspace{6\baselineskip}%", lettrine_header)

    def test_lettrine_ante_fallback_preserves_leading_punctuation(self) -> None:
        if shutil.which("xelatex") is None or shutil.which("pdftotext") is None:
            self.skipTest("xelatex and pdftotext are required")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            source = temp / "ante-fallback.tex"
            header = (MODULE_PATH.parent / "pandoc-latex-lettrine.tex").resolve()
            source.write_text(
                rf"""
                \documentclass{{article}}
                \input{{{header}}}
                \begin{{document}}
                \cmehaslettrinefalse
                \cmeLettrineAnte{{"}}{{A}}{{lpha}}
                \par
                \cmeLettrineWithFontHookAnte{{\relax}}{{"}}{{B}}{{eta}}
                \end{{document}}
                """,
                encoding="utf-8",
            )
            subprocess.run(
                [
                    "xelatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    str(source),
                ],
                cwd=temp,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            result = subprocess.run(
                ["pdftotext", str(source.with_suffix(".pdf")), "-"],
                cwd=temp,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        text = " ".join(result.stdout.split())
        self.assertRegex(text, r'["”]Alpha')
        self.assertRegex(text, r'["”]Beta')

    def test_latex_notes_in_verse_lines_render_as_footnotes(self) -> None:
        latex = self.render_latex(
            """
            <ETS>
              <TEMPHEAD />
              <EEBO><IDG><BIBNO>CME00065</BIBNO></IDG><TEXT><BODY>
                <DIV1 TYPE="poem"><DIV2 N="H." TYPE="version">
                  <HEAD>H.</HEAD>
                  <HEAD>DE TYOPHILO CLERICO NARRATIO.</HEAD>
                  <LG>
                    <L>A bisschop wond biȝond þe se,</L>
                    <L>and Cicile hight [þe same cete <NOTE N="1)" PLACE="foot">þonne þe cuntre <HI REND="italic">T. Schon im blick</HI> cuntre.</NOTE>.</L>
                  </LG>
                </DIV2></DIV1>
              </BODY></TEXT></EEBO>
            </ETS>
            """
        )

        self.assertIn(r"\footnote{þonne þe cuntre", latex)
        self.assertIn(r"\emph{T. Schon im blick}", latex)
        self.assertNotIn(r"{{[}þonne þe cuntre", latex)

    def test_fallback_title_excludes_heading_notes_without_mid_word_truncation(self) -> None:
        latex = self.render_latex(
            """
            <ETS>
              <TEMPHEAD />
              <EEBO><IDG><BIBNO>CMEFIXTURE</BIBNO></IDG><TEXT><BODY>
                <DIV1 TYPE="collection of legends">
                  <HEAD>Des Ms. Bodl. 779 jüngere Zusatzlegenden zur südlichen Legendensammlung. <NOTE>Vgl. Altengl. Leg. 1875, p. XXXV ff., und South Engl. Legendary 1887, p. XX (wo ein paar Heiligentage unrichtig aufgeführt sind). Ms. Bodl. ist die einzige Hs.</NOTE></HEAD>
                  <P>Body text.</P>
                </DIV1>
              </BODY></TEXT></EEBO>
            </ETS>
            """
        )

        self.assertIn(
            "pdftitle={Des Ms. Bodl. 779 jüngere Zusatzlegenden zur südlichen Legendensammlung.}",
            latex,
        )
        title_block = latex.split(r"\title{", 1)[1].split(r"\author{", 1)[0]
        self.assertIn("Des Ms. Bodl. 779 jüngere Zusatzlegenden zur südlichen", title_block)
        self.assertIn("Legendensammlung.", title_block)
        self.assertNotIn("unric", title_block)
        self.assertNotIn("Vgl. Altengl", title_block)

    def test_four_column_tables_emit_wrapping_latex_columns(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1><HEAD>Table Fixture</HEAD>
                <TABLE COLS="4">
                  <ROW><CELL>NO.</CELL><CELL>A.D.</CELL><CELL></CELL><CELL></CELL></ROW>
                  <ROW><CELL>1.</CELL><CELL>1387.</CELL><CELL>Robert CORN, Citizen of London with a long description that must wrap in a narrow book table.</CELL><CELL>1</CELL></ROW>
                </TABLE>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn(r"\real{0.6500}", latex)
        self.assertIn(r"p{(\linewidth", latex)
        self.assertNotIn(r"@{}llll@{}", latex)

    def test_nested_tables_in_cells_are_flattened_for_latex(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1><HEAD>Nested Table Fixture</HEAD>
                <TABLE><ROW><CELL>Outer before
                  <TABLE>
                    <HEAD>Wherof in:—</HEAD>
                    <ROW><CELL>1st.</CELL><CELL>Inner cell text.</CELL></ROW>
                    <ROW><CELL>2nd.</CELL><CELL>More inner text.</CELL></ROW>
                  </TABLE>
                Outer after</CELL></ROW></TABLE>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertEqual(latex.count(r"\begin{longtable}"), 1)
        self.assertIn("Outer before", latex)
        self.assertIn("Wherof in", latex)
        self.assertIn("1st. --- Inner cell text.", latex)
        self.assertIn("2nd. --- More inner text.", latex)
        self.assertIn("Outer after", latex)

    def test_latex_preamble_drops_fragile_xelatex_inline_decorations(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1><HEAD>Decoration Fixture</HEAD>
                <P><HI REND="u">underlined editorial text</HI> and <DEL>deleted text</DEL>.</P>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn(r"\renewcommand{\ul}[1]{#1}", latex)
        self.assertIn(r"\renewcommand{\st}[1]{#1}", latex)

    def test_latex_preamble_maps_unavailable_source_glyphs(self) -> None:
        latex = self.render_latex(
            """
            <DLPSTEXTCLASS>
              <TEXT><BODY><DIV1><HEAD>Glyph Fixture</HEAD>
                <P>chircℏ ∣ marker</P>
              </DIV1></BODY></TEXT>
            </DLPSTEXTCLASS>
            """
        )

        self.assertIn("\\newunicodechar{ℏ}{h}", latex)
        self.assertIn("\\newunicodechar{∣}{\\textbar{}}", latex)
        self.assertIn("\\newunicodechar{̘}{}", latex)


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
