import importlib.util
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "rebuild-manifest-indexes.py"
SPEC = importlib.util.spec_from_file_location("rebuild_manifest_indexes", MODULE_PATH)
rebuild_manifest_indexes = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rebuild_manifest_indexes
assert SPEC.loader is not None
SPEC.loader.exec_module(rebuild_manifest_indexes)


class ManifestIndexRebuilderTests(unittest.TestCase):
    def test_metadata_index_is_generated_from_manifests(self) -> None:
        expected = json.loads(
            (REPO_ROOT / "manifests/work-metadata/index.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            expected,
            rebuild_manifest_indexes.build_metadata_index(REPO_ROOT),
        )

    def test_lineage_index_is_generated_from_manifests(self) -> None:
        expected = json.loads(
            (REPO_ROOT / "manifests/lineage/index.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            expected,
            rebuild_manifest_indexes.build_lineage_index(REPO_ROOT),
        )


if __name__ == "__main__":
    unittest.main()
