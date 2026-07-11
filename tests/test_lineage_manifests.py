import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "validate-lineage-manifests.py"
SPEC = importlib.util.spec_from_file_location("validate_lineage_manifests", MODULE_PATH)
validate_lineage_manifests = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_lineage_manifests
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_lineage_manifests)


class LineageManifestTests(unittest.TestCase):
    def test_committed_lineage_repository_validates(self) -> None:
        self.assertEqual([], validate_lineage_manifests.validate_repository(REPO_ROOT))

    def test_unresolved_relation_endpoint_is_rejected(self) -> None:
        path = REPO_ROOT / "manifests" / "lineage" / "works" / "CME00099.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(manifest)
        changed["relations"][0]["object"] = "witness:missing"

        errors = validate_lineage_manifests._semantic_manifest_errors(REPO_ROOT, path, changed)

        self.assertTrue(any("unresolved entity reference 'witness:missing'" in item for item in errors))

    def test_schema_rejects_unknown_top_level_property(self) -> None:
        schema_path = (
            REPO_ROOT
            / "manifests"
            / "lineage"
            / "schemas"
            / "lineage-manifest.schema.json"
        )
        manifest_path = REPO_ROOT / "manifests" / "lineage" / "works" / "CME00099.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["unreviewed_guess"] = True

        errors = validate_lineage_manifests._schema_errors(
            manifest,
            schema,
            schema,
            "CME00099",
        )

        self.assertIn("CME00099: unexpected property 'unreviewed_guess'", errors)

    def test_schema_records_work_portion_within_complete_source(self) -> None:
        schema_path = (
            REPO_ROOT
            / "manifests"
            / "lineage"
            / "schemas"
            / "lineage-manifest.schema.json"
        )
        manifest_path = REPO_ROOT / "manifests" / "lineage" / "works" / "CME00099.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(manifest)
        changed["access"][0]["local_copies"] = [{
            "label": "Complete manuscript PDF",
            "path": "source-cache/CME00099/manuscript.pdf",
            "source_url": "https://example.test/manuscript.pdf",
            "sha256": "0" * 64,
            "bytes": 1,
            "media_type": "application/pdf",
            "downloaded_on": "2026-07-11",
            "coverage": "complete",
            "work_portion": {
                "label": "The cataloged work",
                "locators": ["folios 10r–20v", "IIIF canvases 21–42"],
                "start_url": "https://example.test/canvas/21",
                "end_url": "https://example.test/canvas/42",
            },
        }]

        self.assertEqual(
            [],
            validate_lineage_manifests._schema_errors(
                changed,
                schema,
                schema,
                "CME00099",
            ),
        )

        del changed["access"][0]["local_copies"][0]["work_portion"]["locators"]
        errors = validate_lineage_manifests._schema_errors(
            changed,
            schema,
            schema,
            "CME00099",
        )
        self.assertTrue(any("locators" in item and "required" in item for item in errors))

    def test_local_copy_is_optional_but_verified_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifests/lineage/works/TestWork.json"
            payload = b"%PDF-1.7\nsource fixture\n%%EOF\n"
            local_copy = {
                "label": "Complete source PDF",
                "path": "source-cache/TestWork/source.pdf",
                "source_url": "https://example.test/source.pdf",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "media_type": "application/pdf",
                "downloaded_on": "2026-07-11",
                "coverage": "complete",
            }
            manifest = {
                "id": "lineage:TestWork",
                "work_id": "TestWork",
                "primary_subject": "edition:test",
                "entities": [{"id": "edition:test"}],
                "agents": [],
                "relations": [],
                "access": [
                    {
                        "id": "access:test",
                        "entity": "edition:test",
                        "url": "https://example.test/source",
                        "alternate_urls": ["https://example.test/source.pdf"],
                        "local_copies": [local_copy],
                        "evidence_ids": ["evidence:test"],
                    }
                ],
                "rights": [],
                "editorial_practices": [],
                "evidence": [{"id": "evidence:test"}],
                "open_questions": [],
            }

            errors = validate_lineage_manifests._semantic_manifest_errors(
                root, manifest_path, manifest
            )
            self.assertEqual([], errors)

            cached = root / local_copy["path"]
            cached.parent.mkdir(parents=True)
            cached.write_bytes(payload)
            errors = validate_lineage_manifests._semantic_manifest_errors(
                root, manifest_path, manifest
            )
            self.assertEqual([], errors)

            cached.write_bytes(b"%PDF-1.7\nchanged\n%%EOF\n")
            errors = validate_lineage_manifests._semantic_manifest_errors(
                root, manifest_path, manifest
            )
            self.assertTrue(any("local_copies[0].bytes: byte count mismatch" in item for item in errors))

    def test_local_copy_requires_exact_download_link_and_work_scoped_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifests/lineage/works/TestWork.json"
            manifest = {
                "id": "lineage:TestWork",
                "work_id": "TestWork",
                "primary_subject": "edition:test",
                "entities": [{"id": "edition:test"}],
                "agents": [],
                "relations": [],
                "access": [
                    {
                        "id": "access:test",
                        "entity": "edition:test",
                        "url": "https://example.test/source",
                        "local_copies": [{
                            "label": "Source PDF",
                            "path": "source-cache/OtherWork/source.pdf",
                            "source_url": "https://example.test/source.pdf",
                            "sha256": "0" * 64,
                            "bytes": 1,
                            "media_type": "application/pdf",
                            "downloaded_on": "2026-07-11",
                            "coverage": "unknown",
                        }],
                        "evidence_ids": ["evidence:test"],
                    }
                ],
                "rights": [],
                "editorial_practices": [],
                "evidence": [{"id": "evidence:test"}],
                "open_questions": [],
            }

            errors = validate_lineage_manifests._semantic_manifest_errors(
                root, manifest_path, manifest
            )
            self.assertTrue(any("must be one file under 'source-cache/TestWork'" in item for item in errors))
            self.assertTrue(any("exact download URL must also appear" in item for item in errors))

    def _xml_identifier_errors(self, xml: str, work_id: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.xml"
            path.write_text(xml, encoding="utf-8")
            errors: list[str] = []
            validate_lineage_manifests._validate_xml_work_id(
                path,
                work_id,
                "fixture",
                errors,
            )
            return errors

    def test_xml_identifier_accepts_legacy_cme_triplet(self) -> None:
        errors = self._xml_identifier_errors(
            "<ETS><IDG ID='CME00099'><BIBNO>CME00099</BIBNO>"
            "<VID>CME00099</VID></IDG></ETS>",
            "CME00099",
        )

        self.assertEqual([], errors)

    def test_xml_identifier_accepts_dlps_idno(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>Troilus</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "Troilus",
        )

        self.assertEqual([], errors)

    def test_xml_identifier_accepts_delimited_case_insensitive_idno(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>AFW5744.0001.001</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "afw5744",
        )

        self.assertEqual([], errors)

    def test_xml_identifier_rejects_undelimited_prefix(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>TroilusExtra</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "Troilus",
        )

        self.assertTrue(any("no matching" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
