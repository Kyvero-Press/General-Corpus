import copy
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
