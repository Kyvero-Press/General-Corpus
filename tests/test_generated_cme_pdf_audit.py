import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit-generated-cme-pdfs.py"
SPEC = importlib.util.spec_from_file_location("audit_generated_cme_pdfs", MODULE_PATH)
audit_generated_cme_pdfs = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit_generated_cme_pdfs
assert SPEC.loader is not None
SPEC.loader.exec_module(audit_generated_cme_pdfs)


PDFINFO_OK = """Title: Example
Pages: 10
Page size: 360 x 576 pts
"""

PDFFONTS_OK = """name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
ABCDEF+Junicode-Regular              CID TrueType      Identity-H       yes yes yes      4  0
"""

PDFFONTS_UNEMBEDDED = """name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
Times-Roman                          Type 1            WinAnsi          no  no  no       4  0
"""

PDFFONTS_EMBEDDED_NOT_SUBSET = """name                                 type              encoding         emb sub uni object ID
------------------------------------ ----------------- ---------------- --- --- --- ---------
Junicode-Regular                     CID TrueType      Identity-H       yes no  yes      4  0
"""


class AuditGeneratedCmePdfsTests(unittest.TestCase):
    def test_parse_pdfinfo_page_size(self) -> None:
        info = audit_generated_cme_pdfs.parse_pdfinfo(PDFINFO_OK)

        self.assertEqual(info["pages"], "10")
        self.assertTrue(audit_generated_cme_pdfs.page_size_is_expected(audit_generated_cme_pdfs.parse_page_size(info["page size"])))
        self.assertFalse(audit_generated_cme_pdfs.page_size_is_expected((612.0, 792.0)))

    def test_unembedded_font_detection(self) -> None:
        self.assertEqual(audit_generated_cme_pdfs.unembedded_fonts(PDFFONTS_OK), [])
        self.assertEqual(audit_generated_cme_pdfs.unembedded_fonts(PDFFONTS_EMBEDDED_NOT_SUBSET), [])
        self.assertEqual(audit_generated_cme_pdfs.unembedded_fonts(PDFFONTS_UNEMBEDDED), ["Times-Roman"])

    def test_audit_pdf_flags_duplicate_frontmatter_visible_metadata_and_fonts(self) -> None:
        text = "General Corpus Edition\nColophon\nContents\nSource metadata\fColophon\nMore colophon\fGeneral Corpus Edition\nRepeated title\fTable of Contents\nEntries\fx\n"

        def fake_run(cmd):
            if cmd[0] == "pdfinfo":
                return 0, "Pages: 3\nPage size: 612 x 792 pts\n", ""
            if cmd[0] == "pdffonts":
                return 0, PDFFONTS_UNEMBEDDED, ""
            if cmd[0] == "pdftotext":
                return 0, text, ""
            raise AssertionError(cmd)

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(audit_generated_cme_pdfs, "run_text", side_effect=fake_run):
            pdf = Path(temp_dir) / "Book.pdf"
            pdf.write_bytes(b"%PDF")
            issues = audit_generated_cme_pdfs.audit_pdf(pdf)

        codes = {issue.code for issue in issues}
        self.assertIn("unexpected_page_size", codes)
        self.assertIn("unembedded_fonts", codes)
        self.assertIn("duplicate_generated_title_signal", codes)
        self.assertIn("duplicate_colophon_signal", codes)
        self.assertIn("many_contents_signals", codes)
        self.assertIn("visible_source_metadata", codes)
        self.assertIn("suspicious_last_page", codes)

    def test_cli_writes_report_and_summary_with_allow_issues(self) -> None:
        def fake_run(cmd):
            if cmd[0] == "pdfinfo":
                return 0, PDFINFO_OK, ""
            if cmd[0] == "pdffonts":
                return 0, PDFFONTS_OK, ""
            if cmd[0] == "pdftotext":
                return 0, "General Corpus Edition\nColophon\nContents\fBody text\n", ""
            raise AssertionError(cmd)

        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(audit_generated_cme_pdfs, "run_text", side_effect=fake_run):
            root = Path(temp_dir)
            pdf = root / "Book.pdf"
            report = root / "report.tsv"
            summary = root / "summary.md"
            pdf.write_bytes(b"%PDF")

            exit_code = audit_generated_cme_pdfs.main(
                [str(root), "--report", str(report), "--summary", str(summary), "--allow-issues"]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("pdf\tsource\tseverity\tcode\tmessage\tcontext", report.read_text(encoding="utf-8").splitlines()[0])
            self.assertIn("# Generated CME PDF audit", summary.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
