import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "cme_contents_audit.py"
SPEC = importlib.util.spec_from_file_location("cme_contents_audit", MODULE_PATH)
cme_contents_audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cme_contents_audit
assert SPEC.loader is not None
SPEC.loader.exec_module(cme_contents_audit)


APE9595 = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "ape9595.xml"
AHA2738 = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "aha2738.xml"
LOVEMIRROUR = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "LoveMirrour.xml"
THIRD_FRAN_RULE = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "3rdFranRule.xml"
MELUSINE = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "Melusine.xml"
KNTTOUR_L = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "KntTour-L.xml"
AHA2727 = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "aha2727.xml"
AHA2749 = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "aha2749.xml"
MALORYWKS2 = REPO_ROOT / "CME" / "source" / "CME_phase_1-2" / "MaloryWks2.xml"


def audit_xml(xml: str) -> list[object]:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "fixture.xml"
        path.write_text(xml, encoding="utf-8")
        return cme_contents_audit.audit_file(path)


def body_index_for_xml(xml: str) -> object:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "fixture.xml"
        path.write_text(xml, encoding="utf-8")
        parsed = cme_contents_audit.parse_xml(path)
        fmt = cme_contents_audit.detect_format(parsed.root)
        return cme_contents_audit.build_body_index(parsed.root, fmt)


def issue_codes(issues: list[object]) -> list[str]:
    return [issue.code for issue in issues]


class OrdinalParsingTests(unittest.TestCase):
    def test_parses_arabic_roman_medieval_j_and_english_ordinals(self) -> None:
        self.assertEqual(cme_contents_audit.parse_ordinals("1, 2nd, III"), (1, 2, 3))
        self.assertEqual(cme_contents_audit.parse_ordinals("iij, iiij, vj, vij"), (3, 4, 6, 7))
        self.assertEqual(cme_contents_audit.parse_ordinals("first seconde fyfthe"), (1, 2, 5))
        self.assertEqual(cme_contents_audit.parse_ordinals("secunda tercia vndecimum"), (2, 3, 11))

    def test_expands_multiple_ordinals_without_dropping_later_values(self) -> None:
        self.assertEqual(cme_contents_audit.parse_ordinals("fyfthe, vj, and vij"), (5, 6, 7))

    def test_labeled_ordinals_allow_high_single_romans_after_explicit_labels(self) -> None:
        self.assertEqual(cme_contents_audit.parse_ordinals("L C"), ())
        self.assertEqual(cme_contents_audit.labeled_ordinals("Cap. L. Of Melusine", "chapter"), (50,))
        self.assertEqual(cme_contents_audit.labeled_ordinals("[CHAPTER C.]", "chapter"), (100,))
        self.assertEqual(cme_contents_audit.labeled_ordinals("Cap m. xix.", "chapter"), (19,))
        self.assertEqual(cme_contents_audit.labeled_ordinals("Capitulo xj", "chapter"), (11,))
        self.assertEqual(cme_contents_audit.labeled_ordinals("partie II", "part"), (2,))
        self.assertEqual(cme_contents_audit.labeled_ordinals("party III", "part"), (3,))


class BodySequenceAuditTests(unittest.TestCase):
    def test_reports_sibling_scoped_body_chapter_gap(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="chapter" N="I"><P>First chapter.</P></DIV1>
              <DIV1 TYPE="chapter" N="III"><P>Third chapter.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertIn("body_chapter_sequence_gap", issue_codes(issues))
        self.assertTrue(
            any(issue.code == "body_chapter_sequence_gap" and "2" in issue.context for issue in issues)
        )

    def test_ranges_and_multiple_ordinals_do_not_create_false_gap_before_next_sibling(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="chapter" N="fyfthe, vj, and vij"><P>Combined chapters.</P></DIV1>
              <DIV1 TYPE="chapter" N="VIII"><P>Eighth chapter.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertNotIn("body_chapter_sequence_gap", issue_codes(issues))

    def test_chapter_abbreviation_m_before_roman_numeral_is_not_parsed_as_1000(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="chapter"><HEAD>Capitulum xj.</HEAD><P>Eleventh.</P></DIV1>
              <DIV1 TYPE="chapter"><HEAD>Cap m. xix.</HEAD><P>Nineteenth.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        gap_contexts = [issue.context for issue in issues if issue.code == "body_chapter_sequence_gap"]
        self.assertEqual(len(gap_contexts), 1)
        self.assertIn("missing=12,13,14,15,16,17,18", gap_contexts[0])
        self.assertNotIn("999", gap_contexts[0])

    def test_body_chapter_heading_with_contents_word_is_not_excluded(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="chapter" N="I"><HEAD>First chapter.</HEAD><P>One.</P></DIV1>
              <DIV1 TYPE="chapter" N="II"><HEAD>Chapter II: contents of the box.</HEAD><P>Two.</P></DIV1>
              <DIV1 TYPE="chapter" N="III"><HEAD>Third chapter.</HEAD><P>Three.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertNotIn("body_chapter_sequence_gap", issue_codes(issues))

    def test_capm_cam_headings_with_abbreviation_suffix_index_body_chapters(self) -> None:
        body = body_index_for_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="chapter"><HEAD>¶Capm.jm.<LB/>First.</HEAD><P>One.</P></DIV1>
              <DIV1 TYPE="chapter"><HEAD>¶Cam.xm.<LB/>Tenth.</HEAD><P>Ten.</P></DIV1>
              <DIV1 TYPE="chapter"><HEAD>¶Capm.3m.<LB/>Third.</HEAD><P>Three.</P></DIV1>
              <DIV1 TYPE="chapter"><HEAD>¶Cam.lm.<LB/>Fiftieth.</HEAD><P>Fifty.</P></DIV1>
              <DIV1 TYPE="chapter"><HEAD>Capi m. ix.</HEAD><P>Ninth.</P></DIV1>
              <DIV1 TYPE="chapter"><HEAD>Caplm. j.</HEAD><P>First again.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertIn(1, body.chapters)
        self.assertIn(3, body.chapters)
        self.assertIn(9, body.chapters)
        self.assertIn(10, body.chapters)
        self.assertIn(50, body.chapters)
        self.assertNotIn(990, body.chapters)


class ContentsReferenceAuditTests(unittest.TestCase):
    def test_reports_structured_toc_part_and_chapter_refs_missing_from_body(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <FRONT>
                <DIV1 TYPE="contents">
                  <HEAD>Contents</HEAD>
                  <DIV2 TYPE="part" N="I"><HEAD>Part I</HEAD></DIV2>
                  <DIV2 TYPE="part" N="II"><HEAD>Part II</HEAD></DIV2>
                  <DIV2 TYPE="chapter" N="III"><HEAD>Chapter III</HEAD></DIV2>
                </DIV1>
              </FRONT>
              <BODY>
                <DIV1 TYPE="part" N="I">
                  <DIV2 TYPE="chapter" N="I"><P>First.</P></DIV2>
                  <DIV2 TYPE="chapter" N="II"><P>Second.</P></DIV2>
                </DIV1>
              </BODY>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        codes = issue_codes(issues)
        self.assertIn("toc_part_missing_from_body", codes)
        self.assertIn("toc_chapter_missing_from_body", codes)

    def test_reports_conservative_unstructured_toc_items_and_rows_missing_from_body(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <FRONT>
                <DIV1 TYPE="table of contents">
                  <HEAD>Contents</HEAD>
                  <P>Part I. Present part</P>
                  <TABLE>
                    <ROW><CELL>Chapter II</CELL><CELL>Missing chapter</CELL></ROW>
                  </TABLE>
                </DIV1>
              </FRONT>
              <BODY>
                <DIV1 TYPE="part" N="I">
                  <DIV2 TYPE="chapter" N="I"><P>First.</P></DIV2>
                </DIV1>
              </BODY>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertIn("toc_chapter_missing_from_body", issue_codes(issues))

    def test_reports_trailing_capm_toc_refs_missing_from_body(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <FRONT>
                <DIV1 TYPE="table of contents">
                  <HEAD>Contents</HEAD>
                  <LIST><ITEM>¶ Of the manere of lyuynge <REF>Capm. ijm.</REF></ITEM></LIST>
                </DIV1>
              </FRONT>
              <BODY>
                <DIV1 TYPE="chapter"><HEAD>¶Capm.jm.<LB/>First.</HEAD><P>One.</P></DIV1>
              </BODY>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertIn("toc_chapter_missing_from_body", issue_codes(issues))

    def test_trailing_capm_toc_ref_matches_cam_body_heading(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <FRONT>
                <DIV1 TYPE="table of contents">
                  <HEAD>Contents</HEAD>
                  <LIST><ITEM>¶ Of the fleynge into Egipte <REF>Capm. xm.</REF></ITEM></LIST>
                </DIV1>
              </FRONT>
              <BODY>
                <DIV1 TYPE="chapter"><HEAD>¶Cam.xm.<LB/>Of the fleynge.</HEAD><P>Ten.</P></DIV1>
              </BODY>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertNotIn("toc_chapter_missing_from_body", issue_codes(issues))

    def test_unstructured_scan_prunes_structured_toc_division_prose(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <FRONT>
                <DIV1 TYPE="table of contents">
                  <DIV2 TYPE="chapter" N="I"><P>See Chapter II for a cross reference.</P></DIV2>
                </DIV1>
              </FRONT>
              <BODY><DIV1 TYPE="chapter" N="I"><P>Present.</P></DIV1></BODY>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertNotIn("toc_chapter_missing_from_body", issue_codes(issues))

    def test_toc_part_ref_is_not_missing_when_body_has_unnumbered_part_divisions(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <FRONT>
                <DIV1 TYPE="table of contents"><ITEM>The sixte part for Saturday</ITEM></DIV1>
              </FRONT>
              <BODY><DIV1 TYPE="part"><HEAD>Sabbato.</HEAD><P>Represented but not numbered.</P></DIV1></BODY>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertNotIn("toc_part_missing_from_body", issue_codes(issues))

    def test_body_encoded_contents_are_audited(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="version">
                <DIV2 TYPE="contents"><ITEM>Chapter II. Missing chapter.</ITEM></DIV2>
              </DIV1>
              <DIV1 TYPE="chapter" N="I"><P>Present.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertIn("toc_chapter_missing_from_body", issue_codes(issues))

    def test_body_encoded_structured_contents_are_not_counted_as_body_chapters(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="contents"><DIV2 TYPE="chapter" N="II"><HEAD>Chapter II</HEAD></DIV2></DIV1>
              <DIV1 TYPE="chapter" N="I"><P>Present.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        codes = issue_codes(issues)
        self.assertIn("toc_chapter_missing_from_body", codes)
        self.assertNotIn("body_chapter_sequence_gap", codes)

    def test_part_scoped_toc_chapter_does_not_fall_back_to_global_chapter(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <FRONT>
                <DIV1 TYPE="contents">
                  <DIV2 TYPE="part" N="II"><DIV3 TYPE="chapter" N="I"><HEAD>Chapter I</HEAD></DIV3></DIV2>
                </DIV1>
              </FRONT>
              <BODY>
                <DIV1 TYPE="part" N="I"><DIV2 TYPE="chapter" N="I"><P>Part one.</P></DIV2></DIV1>
                <DIV1 TYPE="part" N="II"><P>No chapters here.</P></DIV1>
              </BODY>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertIn("toc_chapter_missing_from_body", issue_codes(issues))

    def test_unstructured_toc_does_not_treat_parts_of_speech_as_part_reference(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <FRONT>
                <DIV1 TYPE="table of contents">
                  <HEAD>Contents</HEAD>
                  <LIST>
                    <ITEM>NOUN. § 1. Relations between the Noun and the other parts of speech, p. v.</ITEM>
                  </LIST>
                </DIV1>
              </FRONT>
              <BODY><DIV1 TYPE="section"><P>Grammar.</P></DIV1></BODY>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        self.assertNotIn("toc_part_missing_from_body", issue_codes(issues))


class FormatFilterTests(unittest.TestCase):
    def test_headwords_format_is_excluded(self) -> None:
        issues = audit_xml("<HEADWORDS><ENTRY><WORD>abide</WORD></ENTRY></HEADWORDS>")

        self.assertEqual(issues, [])


class RealCmeRegressionTests(unittest.TestCase):
    def test_ape9595_front_parts_are_not_represented_as_body_part_divisions(self) -> None:
        issues = cme_contents_audit.audit_file(APE9595)
        codes = issue_codes(issues)

        self.assertIn("front_parts_not_represented_in_body", codes)
        self.assertFalse([code for code in codes if "line" in code])

    def test_aha2738_front_parts_are_represented_in_body(self) -> None:
        issues = cme_contents_audit.audit_file(AHA2738)

        self.assertNotIn("front_parts_not_represented_in_body", issue_codes(issues))

    def test_third_fran_rule_common_chapter_abbreviations_are_detected(self) -> None:
        parsed = cme_contents_audit.parse_xml(THIRD_FRAN_RULE)
        fmt = cme_contents_audit.detect_format(parsed.root)
        refs = cme_contents_audit.collect_toc_refs(parsed.root, fmt)
        body = cme_contents_audit.build_body_index(parsed.root, fmt)
        issues = cme_contents_audit.audit_file(THIRD_FRAN_RULE)
        toc_chapters = {ref.ordinal for ref in refs if ref.kind == "chapter"}

        self.assertIn(1, toc_chapters)
        self.assertIn(9, toc_chapters)
        self.assertIn(10, toc_chapters)
        self.assertIn(1, body.chapters)
        self.assertIn(9, body.chapters)
        self.assertIn(10, body.chapters)
        self.assertNotIn("toc_chapter_missing_from_body", issue_codes(issues))

    def test_body_encoded_real_contents_are_detected(self) -> None:
        for path in (AHA2727, AHA2749):
            parsed = cme_contents_audit.parse_xml(path)
            fmt = cme_contents_audit.detect_format(parsed.root)
            refs = cme_contents_audit.collect_toc_refs(parsed.root, fmt)
            self.assertGreater(len(refs), 0, path)

    def test_malory_capitulo_toc_entries_are_detected(self) -> None:
        parsed = cme_contents_audit.parse_xml(MALORYWKS2)
        fmt = cme_contents_audit.detect_format(parsed.root)
        refs = cme_contents_audit.collect_toc_refs(parsed.root, fmt)
        toc_chapters = {ref.ordinal for ref in refs if ref.kind == "chapter"}

        self.assertGreater(len(toc_chapters), 20)
        self.assertIn(11, toc_chapters)

    def test_high_single_roman_real_chapters_are_detected(self) -> None:
        melusine = cme_contents_audit.parse_xml(MELUSINE)
        melusine_body = cme_contents_audit.build_body_index(
            melusine.root,
            cme_contents_audit.detect_format(melusine.root),
        )
        knttour = cme_contents_audit.parse_xml(KNTTOUR_L)
        knttour_body = cme_contents_audit.build_body_index(
            knttour.root,
            cme_contents_audit.detect_format(knttour.root),
        )

        self.assertIn(50, melusine_body.chapters)
        self.assertIn(100, knttour_body.chapters)

    def test_lovemirrour_capm_cam_toc_and_body_chapter_refs_are_detected(self) -> None:
        parsed = cme_contents_audit.parse_xml(LOVEMIRROUR)
        fmt = cme_contents_audit.detect_format(parsed.root)
        refs = cme_contents_audit.collect_toc_refs(parsed.root, fmt)
        body = cme_contents_audit.build_body_index(parsed.root, fmt)
        toc_chapters = {ref.ordinal for ref in refs if ref.kind == "chapter"}

        self.assertGreaterEqual(len(toc_chapters), 60)
        self.assertIn(10, toc_chapters)
        self.assertIn(50, toc_chapters)
        self.assertIn(10, body.chapters)
        self.assertIn(11, body.chapters)
        self.assertIn(50, body.chapters)
        self.assertNotIn(990, body.chapters)


class ContentsAuditCliTests(unittest.TestCase):
    def test_main_passes_explicit_empty_argv_to_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = root / "contents.tsv"
            parsed_args = cme_contents_audit.argparse.Namespace(
                root=root,
                report=report,
                allow_issues=True,
                allow_empty=True,
            )
            with mock.patch.object(cme_contents_audit.sys, "argv", ["audit-cme-contents.py", "--bogus"]):
                with mock.patch.object(cme_contents_audit, "parse_args", return_value=parsed_args) as parse_args:
                    exit_code = cme_contents_audit.main([])

        self.assertEqual(exit_code, 0)
        parse_args.assert_called_once_with([])

    def test_cli_writes_tsv_and_allow_issues_returns_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "fixture.xml"
            report = root / "contents.tsv"
            source.write_text(
                """
                <DLPSTEXTCLASS><TEXT><BODY>
                  <DIV1 TYPE="chapter" N="1"><P>One.</P></DIV1>
                  <DIV1 TYPE="chapter" N="3"><P>Three.</P></DIV1>
                </BODY></TEXT></DLPSTEXTCLASS>
                """,
                encoding="utf-8",
            )

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = cme_contents_audit.main(
                    [str(root), "--report", str(report), "--allow-issues"]
                )

            self.assertEqual(exit_code, 0)
            text = report.read_text(encoding="utf-8")
            self.assertIn("source\tformat\tcode\tmessage\tcontext", text.splitlines()[0])
            self.assertIn("body_chapter_sequence_gap", text)


if __name__ == "__main__":
    unittest.main()
