import copy
import importlib.util
import json
import sys
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


if __name__ == "__main__":
    unittest.main()
