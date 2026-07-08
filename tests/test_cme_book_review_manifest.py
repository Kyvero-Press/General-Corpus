import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "prepare-cme-book-review.py"
SPEC = importlib.util.spec_from_file_location("prepare_cme_book_review", MODULE_PATH)
prepare_cme_book_review = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prepare_cme_book_review
assert SPEC.loader is not None
SPEC.loader.exec_module(prepare_cme_book_review)


class PrepareCmeBookReviewTests(unittest.TestCase):
    def test_manifest_flags_duplicate_stems_missing_pdfs_and_audit_codes(self) -> None:
        manifest = [
            {
                "path": "CME/source/a/Foo.xml",
                "format": "dlpstextclass",
                "strict_xml": "yes",
                "primary_text_paths": "DLPSTEXTCLASS/TEXT",
            },
            {
                "path": "CME/source/b/Foo.xml",
                "format": "ets-temphead-eebo",
                "strict_xml": "no",
                "primary_text_paths": "ETS/EEBO/TEXT",
            },
            {
                "path": "CME/source/a/Bar.xml",
                "format": "tei2",
                "strict_xml": "yes",
                "primary_text_paths": "TEI.2/TEXT",
            },
        ]
        risk = [{"source": "CME/source/a/Foo.xml", "code": "multiple_title_pages"}]
        contents = [{"source": "CME/source/a/Bar.xml", "code": "body_chapter_sequence_gap"}]
        with tempfile.TemporaryDirectory() as temp_dir:
            dist = Path(temp_dir) / "dist"
            dist.mkdir()
            (dist / "Foo.pdf").write_bytes(b"%PDF")
            with mock.patch.object(prepare_cme_book_review, "pdf_page_count", return_value=12):
                rows = prepare_cme_book_review.build_rows(manifest, dist_dir=dist, risk_rows=risk, contents_rows=contents)

        by_source = {row.source: row for row in rows}
        self.assertEqual(by_source["CME/source/a/Foo.xml"].risk_codes, "multiple_title_pages")
        self.assertEqual(by_source["CME/source/a/Foo.xml"].priority_bucket, "1-risk")
        self.assertIn("CME/source/a/Foo.xml", by_source["CME/source/a/Foo.xml"].duplicate_stem_group)
        self.assertIn("CME/source/b/Foo.xml", by_source["CME/source/a/Foo.xml"].duplicate_stem_group)
        self.assertIn("recovery_xml", by_source["CME/source/b/Foo.xml"].notes)
        self.assertEqual(by_source["CME/source/a/Bar.xml"].contents_codes, "body_chapter_sequence_gap")
        self.assertEqual(by_source["CME/source/a/Bar.xml"].priority_bucket, "2-contents")
        self.assertIn("missing_dist_pdf", by_source["CME/source/a/Bar.xml"].notes)

    def test_chunk_rows_obeys_page_budget_except_for_single_large_book(self) -> None:
        rows = [
            prepare_cme_book_review.ReviewRow("A", "A.xml", "fmt", "yes", "TEXT", "A.pdf", 400, "", "", "", "1-risk", ""),
            prepare_cme_book_review.ReviewRow("B", "B.xml", "fmt", "yes", "TEXT", "B.pdf", 450, "", "", "", "1-risk", ""),
            prepare_cme_book_review.ReviewRow("C", "C.xml", "fmt", "yes", "TEXT", "C.pdf", 300, "", "", "", "1-risk", ""),
            prepare_cme_book_review.ReviewRow("Huge", "Huge.xml", "fmt", "yes", "TEXT", "Huge.pdf", 1200, "", "", "", "1-risk", ""),
            prepare_cme_book_review.ReviewRow("D", "D.xml", "fmt", "yes", "TEXT", "D.pdf", 100, "", "", "", "1-risk", ""),
        ]

        chunks = prepare_cme_book_review.chunk_rows(rows, page_budget=900)
        by_source = {row["source"]: row["chunk"] for row in chunks}

        self.assertEqual(by_source["A.xml"], by_source["B.xml"])
        self.assertNotEqual(by_source["B.xml"], by_source["C.xml"])
        self.assertNotEqual(by_source["C.xml"], by_source["Huge.xml"])
        self.assertNotEqual(by_source["Huge.xml"], by_source["D.xml"])
        huge = next(row for row in chunks if row["source"] == "Huge.xml")
        self.assertEqual(huge["pages"], "1200")

    def test_parse_pdf_pages(self) -> None:
        self.assertEqual(prepare_cme_book_review.parse_pdf_pages("Title: X\nPages: 123\n"), 123)
        self.assertIsNone(prepare_cme_book_review.parse_pdf_pages("Pages: unknown\n"))


if __name__ == "__main__":
    unittest.main()
