import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
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

    def test_iiif_bundle_requires_source_count_and_zip_shape(self) -> None:
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
        access = changed["access"][0]
        access["alternate_urls"] = [
            *access.get("alternate_urls", []),
            "https://example.test/manifest",
        ]
        access["local_copies"] = [{
            "label": "Complete manuscript IIIF bundle",
            "path": "source-cache/CME00099/manuscript.zip",
            "source_url": "https://example.test/manifest",
            "sha256": "0" * 64,
            "bytes": 1,
            "media_type": "application/zip",
            "downloaded_on": "2026-07-11",
            "coverage": "complete",
            "retrieval_method": "iiif_bundle",
            "source_file_count": 496,
            "bundle_source_kind": "iiif_presentation_manifest",
            "work_portion": {
                "label": "The cataloged work",
                "locators": ["folios 10r–20v", "IIIF canvases 21–42"],
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
        self.assertEqual(
            [],
            validate_lineage_manifests._semantic_manifest_errors(
                REPO_ROOT,
                manifest_path,
                changed,
            ),
        )

        work_portion = access["local_copies"][0].pop("work_portion")
        errors = validate_lineage_manifests._schema_errors(
            changed,
            schema,
            schema,
            "CME00099",
        )
        self.assertTrue(errors)

        access["local_copies"][0]["target_work_presence"] = "absent"
        self.assertEqual(
            [],
            validate_lineage_manifests._schema_errors(
                changed,
                schema,
                schema,
                "CME00099",
            ),
        )
        self.assertEqual(
            [],
            validate_lineage_manifests._semantic_manifest_errors(
                REPO_ROOT,
                manifest_path,
                changed,
            ),
        )

        access["local_copies"][0]["work_portion"] = work_portion
        errors = validate_lineage_manifests._schema_errors(
            changed,
            schema,
            schema,
            "CME00099",
        )
        self.assertTrue(errors)

        del access["local_copies"][0]["target_work_presence"]

        del access["local_copies"][0]["source_file_count"]
        errors = validate_lineage_manifests._schema_errors(
            changed,
            schema,
            schema,
            "CME00099",
        )
        self.assertTrue(any("source_file_count" in item and "required" in item for item in errors))

        access["local_copies"][0]["source_file_count"] = 496
        access["local_copies"][0]["path"] = "source-cache/CME00099/manuscript.pdf"
        access["local_copies"][0]["media_type"] = "application/pdf"
        errors = validate_lineage_manifests._semantic_manifest_errors(
            REPO_ROOT,
            manifest_path,
            changed,
        )
        self.assertTrue(any("IIIF bundle must be a .zip" in item for item in errors))
        self.assertTrue(any("IIIF bundle must use application/zip" in item for item in errors))

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
            self.assertTrue(any("exact source URL must also appear" in item for item in errors))

    def test_complete_manuscript_facsimile_requires_work_portion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifests/lineage/works/TestWork.json"
            local_copy = {
                "label": "Complete manuscript facsimile",
                "path": "source-cache/TestWork/manuscript.pdf",
                "source_url": "https://example.test/manuscript.pdf",
                "sha256": "0" * 64,
                "bytes": 1,
                "media_type": "application/pdf",
                "downloaded_on": "2026-07-11",
                "coverage": "complete",
                "retrieval_method": "direct_download",
            }
            manifest = {
                "id": "lineage:TestWork",
                "work_id": "TestWork",
                "primary_subject": "facsimile:test",
                "entities": [
                    {"id": "witness:test", "type": "manuscript_witness"},
                    {"id": "facsimile:test", "type": "facsimile"},
                ],
                "agents": [],
                "relations": [{
                    "id": "relation:facsimile-of-witness",
                    "type": "facsimile_of",
                    "subject": "facsimile:test",
                    "object": "witness:test",
                }],
                "access": [{
                    "id": "access:test",
                    "entity": "facsimile:test",
                    "url": "https://example.test/manuscript",
                    "alternate_urls": ["https://example.test/manuscript.pdf"],
                    "local_copies": [local_copy],
                    "evidence_ids": ["evidence:test"],
                }],
                "rights": [],
                "editorial_practices": [],
                "evidence": [{"id": "evidence:test"}],
                "open_questions": [],
            }

            errors = validate_lineage_manifests._semantic_manifest_errors(
                root, manifest_path, manifest
            )
            self.assertTrue(
                any("complete manuscript facsimile requires" in item for item in errors)
            )

            local_copy["work_portion"] = {
                "label": "The work represented by TestWork",
                "locators": ["folios 10r–20v", "pages 21–42"],
            }
            self.assertEqual(
                [],
                validate_lineage_manifests._semantic_manifest_errors(
                    root, manifest_path, manifest
                ),
            )

    def test_present_iiif_bundle_inventory_is_cross_checked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifests/lineage/works/TestWork.json"
            cached = root / "source-cache/TestWork/manuscript.zip"
            cached.parent.mkdir(parents=True)
            source_url = "https://example.test/manifest"
            inventory = {
                "source_kind": "iiif_presentation_manifest",
                "source_url": source_url,
                "source_file_count": 1,
                "items": [{"member_path": "images/000001.jpg"}],
            }
            with zipfile.ZipFile(cached, "w") as archive:
                archive.writestr("manifest.json", "{}")
                archive.writestr("inventory.json", json.dumps(inventory))
                archive.writestr("images/000001.jpg", b"\xff\xd8\xfffixture")
            local_copy = {
                "label": "Complete manuscript bundle",
                "path": "source-cache/TestWork/manuscript.zip",
                "source_url": source_url,
                "sha256": hashlib.sha256(cached.read_bytes()).hexdigest(),
                "bytes": cached.stat().st_size,
                "media_type": "application/zip",
                "downloaded_on": "2026-07-11",
                "coverage": "complete",
                "retrieval_method": "iiif_bundle",
                "bundle_source_kind": "iiif_presentation_manifest",
                "source_file_count": 1,
            }
            manifest = {
                "id": "lineage:TestWork",
                "work_id": "TestWork",
                "primary_subject": "witness:test",
                "entities": [{"id": "witness:test"}],
                "agents": [],
                "relations": [],
                "access": [{
                    "id": "access:test",
                    "entity": "witness:test",
                    "url": source_url,
                    "local_copies": [local_copy],
                    "evidence_ids": ["evidence:test"],
                }],
                "rights": [],
                "editorial_practices": [],
                "evidence": [{"id": "evidence:test"}],
                "open_questions": [],
            }

            self.assertEqual(
                [],
                validate_lineage_manifests._semantic_manifest_errors(
                    root,
                    manifest_path,
                    manifest,
                ),
            )

            local_copy["source_file_count"] = 2
            errors = validate_lineage_manifests._semantic_manifest_errors(
                root,
                manifest_path,
                manifest,
            )
            self.assertTrue(any("file count does not match" in item for item in errors))
            self.assertTrue(any("item count is inconsistent" in item for item in errors))

    def _xml_identifier_errors(
        self,
        xml: str,
        work_id: str,
        xml_identifier_aliases: list[str] | None = None,
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.xml"
            path.write_text(xml, encoding="utf-8")
            errors: list[str] = []
            validate_lineage_manifests._validate_xml_work_id(
                path,
                work_id,
                "fixture",
                errors,
                xml_identifier_aliases,
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

    def test_xml_identifier_accepts_delimited_publication_id_extension(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>LayCal</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "laycal.lineated",
        )

        self.assertEqual([], errors)

    def test_xml_identifier_accepts_publication_idno_with_legacy_cme_aliases(self) -> None:
        errors = self._xml_identifier_errors(
            "<ETS><HEADER><IDNO>CME301</IDNO></HEADER><IDG ID='CME00301'>"
            "<BIBNO>CME00301</BIBNO><VID>CME00301</VID></IDG></ETS>",
            "CME301",
        )

        self.assertEqual([], errors)

    def test_xml_identifier_accepts_matching_idg_with_upstream_bibno_alias(self) -> None:
        errors = self._xml_identifier_errors(
            "<ETS><HEADER><IDNO>CME90022</IDNO></HEADER><IDG ID='CME90022'>"
            "<BIBNO>OTA0022</BIBNO><VID>CME90022</VID></IDG></ETS>",
            "CME90022",
        )

        self.assertEqual([], errors)

    def test_xml_identifier_rejects_when_every_identifier_is_an_alias(self) -> None:
        errors = self._xml_identifier_errors(
            "<ETS><HEADER><IDNO>Different</IDNO></HEADER><IDG ID='CME00301'>"
            "<BIBNO>OTA0022</BIBNO><VID>Legacy</VID></IDG></ETS>",
            "CME301",
        )

        self.assertTrue(any("no matching" in item for item in errors))

    def test_xml_identifier_rejects_undelimited_prefix(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>TroilusExtra</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "Troilus",
        )

        self.assertTrue(any("no matching" in item for item in errors))

    def test_xml_identifier_rejects_undelimited_publication_id_extension(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>LayCal</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "LayCalibration",
        )

        self.assertTrue(any("no matching" in item for item in errors))

    def test_xml_identifier_accepts_explicit_undelimited_alias(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>RuleServeLd</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "RuleServLd",
            ["RuleServeLd"],
        )

        self.assertEqual([], errors)

    def test_xml_identifier_rejects_alias_absent_from_source(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>Different</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "RuleServLd",
            ["RuleServeLd"],
        )

        self.assertTrue(any("no matching" in item for item in errors))

    def test_xml_identifier_alias_must_match_source_value_exactly(self) -> None:
        errors = self._xml_identifier_errors(
            "<DLPSTEXTCLASS><HEADER><IDNO TYPE='dlps'>RuleServeLd.variant</IDNO>"
            "</HEADER></DLPSTEXTCLASS>",
            "RuleServLd",
            ["RuleServeLd"],
        )

        self.assertTrue(any("no matching" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
