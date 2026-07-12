import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "validate-metadata-vocabulary.py"
SPEC = importlib.util.spec_from_file_location("validate_metadata_vocabulary", MODULE_PATH)
validate_metadata_vocabulary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validate_metadata_vocabulary
assert SPEC.loader is not None
SPEC.loader.exec_module(validate_metadata_vocabulary)


class MetadataVocabularyTests(unittest.TestCase):
    @staticmethod
    def _write(root: Path, name: str, *, language_label: str) -> None:
        path = root / "manifests/work-metadata/works" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "language_statements": [
                        {"code": "enm", "label": language_label}
                    ],
                    "genre_statements": [
                        {"term": "romance", "label": "Romance"}
                    ],
                    "subject_statements": [
                        {"term": "medicine", "label": "Medicine"}
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_repository_vocabulary_is_consistent(self) -> None:
        self.assertEqual(
            [],
            validate_metadata_vocabulary.validate_vocabulary(REPO_ROOT),
        )

    def test_conflicting_labels_report_each_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._write(root, "One", language_label="Middle English")
            self._write(root, "Two", language_label="English, Middle")

            errors = validate_metadata_vocabulary.validate_vocabulary(root)

            self.assertEqual(1, len(errors))
            self.assertIn("language_statements.code 'enm'", errors[0])
            self.assertIn("One.json", errors[0])
            self.assertIn("Two.json", errors[0])


if __name__ == "__main__":
    unittest.main()
