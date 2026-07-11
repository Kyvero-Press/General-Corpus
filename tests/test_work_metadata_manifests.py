import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "validate-work-metadata-manifests.py"
SPEC = importlib.util.spec_from_file_location("validate_work_metadata_manifests", MODULE_PATH)
validate_work_metadata_manifests = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_work_metadata_manifests
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_work_metadata_manifests)


class WorkMetadataManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = (
            REPO_ROOT
            / "manifests"
            / "work-metadata"
            / "works"
            / "CME00099.json"
        )
        self.manifest = json.loads(self.path.read_text(encoding="utf-8"))

    def test_committed_work_metadata_repository_validates(self) -> None:
        self.assertEqual([], validate_work_metadata_manifests.validate_repository(REPO_ROOT))

    def test_unresolved_scope_part_is_rejected(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["responsibilities"][0]["scope"]["part_ids"] = ["part:missing"]

        errors = validate_work_metadata_manifests._semantic_manifest_errors(
            REPO_ROOT,
            self.path,
            changed,
        )

        self.assertTrue(any("unresolved content part 'part:missing'" in item for item in errors))

    def test_unresolved_lineage_entity_is_rejected(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["lineage"]["bindings"][0]["lineage_entity_id"] = "edition:missing"

        errors = validate_work_metadata_manifests._semantic_manifest_errors(
            REPO_ROOT,
            self.path,
            changed,
        )

        self.assertTrue(any("unresolved lineage entity 'edition:missing'" in item for item in errors))

    def test_reversed_normalized_date_is_rejected(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["date_statements"][0]["normalized"] = {
            "not_before": 1499,
            "not_after": 1350,
        }

        errors = validate_work_metadata_manifests._semantic_manifest_errors(
            REPO_ROOT,
            self.path,
            changed,
        )

        self.assertTrue(any("not_before exceeds not_after" in item for item in errors))

    def test_schema_rejects_unknown_top_level_property(self) -> None:
        schema_path = (
            REPO_ROOT
            / "manifests"
            / "work-metadata"
            / "schemas"
            / "work-metadata-manifest.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        changed = copy.deepcopy(self.manifest)
        changed["unscoped_region"] = "Stockholm"

        errors = validate_work_metadata_manifests._SCHEMA_SUPPORT._schema_errors(
            changed,
            schema,
            schema,
            "CME00099",
        )

        self.assertIn("CME00099: unexpected property 'unscoped_region'", errors)


if __name__ == "__main__":
    unittest.main()
