import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "audit-cme-pdf-typography.py"
SPEC = importlib.util.spec_from_file_location("cme_pdf_typography_audit", MODULE_PATH)
cme_pdf_typography_audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cme_pdf_typography_audit
assert SPEC.loader is not None
SPEC.loader.exec_module(cme_pdf_typography_audit)


def audit_xml(xml: str) -> list[object]:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "fixture.xml"
        path.write_text(xml, encoding="utf-8")
        return cme_pdf_typography_audit.audit_file(path)


def issue_codes(issues: list[object]) -> list[str]:
    return [issue.code for issue in issues]


class PdfTypographyAuditTests(unittest.TestCase):
    def test_body_title_page_of_part_is_high_risk(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="title page of part"><HEAD>Part Title</HEAD><P>Display title.</P></DIV1>
              <DIV1 TYPE="chapter"><P>Body text.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        codes = issue_codes(issues)
        self.assertIn("source_titlepage_in_body_or_back", codes)
        self.assertNotIn("nonrunning_type_not_covered_by_lettrine_skip", codes)
        issue = next(issue for issue in issues if issue.code == "source_titlepage_in_body_or_back")
        self.assertEqual(issue.severity, "blocker_candidate")
        self.assertIn("type=title page of part", issue.context)

    def test_body_encoded_list_of_contents_is_high_risk(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="list of contents"><HEAD>List of Contents</HEAD><P>Entry.</P></DIV1>
              <DIV1 TYPE="chapter"><P>Body text.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        matching = [issue for issue in issues if issue.code == "body_encoded_contents_section"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].severity, "blocker_candidate")
        self.assertIn("type=list of contents", matching[0].context)

    def test_contents_type_variants_are_high_risk_with_specific_headings(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT><BODY>
              <DIV1 TYPE="list of contents"><HEAD>LIST OF CONTENTS OF LAUD MS. 108</HEAD><P>Entry.</P></DIV1>
              <DIV1 TYPE="tables of contents"><HEAD>TABLES OF CONTENTS IN THE FAIRFAX MSS.</HEAD><P>Entry.</P></DIV1>
              <DIV1 TYPE="chapter"><P>Body text.</P></DIV1>
            </BODY></TEXT></DLPSTEXTCLASS>
            """
        )

        matching = [issue for issue in issues if issue.code == "body_encoded_contents_section"]
        self.assertEqual(len(matching), 2)
        self.assertTrue(any("type=list of contents" in issue.context for issue in matching))
        self.assertTrue(any("type=tables of contents" in issue.context for issue in matching))

    def test_back_encoded_table_of_contents_to_appendices_is_high_risk(self) -> None:
        issues = audit_xml(
            """
            <DLPSTEXTCLASS><TEXT>
              <BODY><DIV1 TYPE="chapter"><P>Body text.</P></DIV1></BODY>
              <BACK><DIV1 TYPE="table of contents to appendices"><P>Appendix entry.</P></DIV1></BACK>
            </TEXT></DLPSTEXTCLASS>
            """
        )

        matching = [issue for issue in issues if issue.code == "body_encoded_contents_section"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].severity, "blocker_candidate")
        self.assertIn("scope=back", matching[0].context)
        self.assertIn("type=table of contents to appendices", matching[0].context)

    def test_incidental_contents_phrase_in_regular_heading_is_not_high_risk(self) -> None:
        issues = audit_xml(
            """
            <ETS><EEBO><TEXT><BODY>
              <DIV1 TYPE="collection of poems">
                <DIV2 TYPE="poem"><HEAD>XIX How þe louer ys sett. Title from old table of contents.</HEAD><P>Body text.</P></DIV2>
              </DIV1>
            </BODY></TEXT></EEBO></ETS>
            """
        )

        self.assertNotIn("body_encoded_contents_section", issue_codes(issues))

    def test_cli_writes_report_summary_and_high_risk_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "fixture.xml"
            report = root / "risk.tsv"
            summary = root / "summary.md"
            high_risk = root / "high-risk.txt"
            source.write_text(
                """
                <DLPSTEXTCLASS><TEXT><BODY>
                  <DIV1 TYPE="title page of part"><HEAD>Part Title</HEAD><P>Display title.</P></DIV1>
                  <DIV1 TYPE="list of contents"><HEAD>List of Contents</HEAD><P>Entry.</P></DIV1>
                  <DIV1 TYPE="chapter"><P>Body text.</P></DIV1>
                </BODY></TEXT></DLPSTEXTCLASS>
                """,
                encoding="utf-8",
            )

            exit_code = cme_pdf_typography_audit.main(
                [
                    str(root),
                    "--report",
                    str(report),
                    "--summary",
                    str(summary),
                    "--high-risk-list",
                    str(high_risk),
                    "--allow-issues",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("source\tformat\tseverity\tcode\tmessage\tcontext", report.read_text(encoding="utf-8").splitlines()[0])
            self.assertIn("source_titlepage_in_body_or_back", report.read_text(encoding="utf-8"))
            self.assertIn("body_encoded_contents_section", report.read_text(encoding="utf-8"))
            self.assertIn("# CME PDF typography risk audit", summary.read_text(encoding="utf-8"))
            self.assertIn(str(source), high_risk.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
