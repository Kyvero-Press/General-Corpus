import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_corpus_viewer_catalog import CatalogFixture, fake_pdfinfo


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "validate-viewer-work.py"
SPEC = importlib.util.spec_from_file_location("validate_viewer_work", MODULE_PATH)
validate_viewer_work = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_viewer_work
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_viewer_work)


class ViewerWorkProjectionTests(unittest.TestCase):
    def test_builds_one_work_with_production_normalizers(self) -> None:
        with tempfile.TemporaryDirectory() as directory, fake_pdfinfo():
            fixture = CatalogFixture(Path(directory))
            fixture.lineage["primary_subject"] = "edition:test"
            fixture.write_manifests()
            pdf = fixture.add_pdf()
            fixture.write_publication_inventory(pdf)

            detail = validate_viewer_work.validate_projection(
                fixture.root,
                fixture.work_id,
            )

        self.assertEqual(fixture.work_id, detail["work"]["workId"])
        self.assertEqual("available", detail["work"]["publication"]["status"])
        self.assertEqual("edition:test", detail["lineage"]["primarySubjectId"])
        self.assertEqual(
            "catalog/manifests/work-metadata/CME00099.json",
            detail["metadataManifestPath"],
        )

    def test_checks_only_this_works_local_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory, fake_pdfinfo():
            fixture = CatalogFixture(Path(directory))
            fixture.lineage["primary_subject"] = "edition:test"
            fixture.add_source_copy()
            pdf = fixture.add_pdf()
            fixture.write_publication_inventory(pdf)

            detail = validate_viewer_work.validate_projection(
                fixture.root,
                fixture.work_id,
            )

            local_copy = detail["lineage"]["sourceLinks"][0]["localCopies"][0]
            self.assertTrue(local_copy["available"])

    def test_rejects_case_insensitive_collision_with_another_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory, fake_pdfinfo():
            fixture = CatalogFixture(Path(directory))
            fixture.lineage["primary_subject"] = "edition:test"
            fixture.write_manifests()
            pdf = fixture.add_pdf()
            fixture.write_publication_inventory(pdf)
            collision = fixture.metadata_path.with_name("cme00099.json")
            collision.write_text("{}\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "case-insensitive work_id collision"):
                validate_viewer_work.validate_projection(fixture.root, fixture.work_id)


if __name__ == "__main__":
    unittest.main()
