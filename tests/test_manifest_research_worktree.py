import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import corpus_source_resolution


MODULE_PATH = REPO_ROOT / "scripts" / "create-manifest-research-worktree.py"
SPEC = importlib.util.spec_from_file_location("create_manifest_research_worktree", MODULE_PATH)
create_manifest_research_worktree = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = create_manifest_research_worktree
assert SPEC.loader is not None
SPEC.loader.exec_module(create_manifest_research_worktree)

INSPECT_MODULE_PATH = REPO_ROOT / "scripts" / "inspect-corpus-source.py"
INSPECT_SPEC = importlib.util.spec_from_file_location(
    "inspect_corpus_source", INSPECT_MODULE_PATH
)
inspect_corpus_source = importlib.util.module_from_spec(INSPECT_SPEC)
sys.modules[INSPECT_SPEC.name] = inspect_corpus_source
assert INSPECT_SPEC.loader is not None
INSPECT_SPEC.loader.exec_module(inspect_corpus_source)


class ManifestResearchWorktreeTests(unittest.TestCase):
    def _write_source_override(
        self,
        root: Path,
        work_id: str,
        source_xml: str,
        *,
        source_sha256: str | None = None,
    ) -> None:
        path = root / "manifests/publication-set/source-overrides.json"
        path.parent.mkdir(parents=True)
        source = root / source_xml
        digest = source_sha256 or hashlib.sha256(source.read_bytes()).hexdigest()
        path.write_text(
            json.dumps(
                {
                    "basis": "test resolution",
                    "items": [
                        {
                            "work_id": work_id,
                            "source_xml": source_xml,
                            "source_sha256": digest,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_source_path_returns_unique_match_without_override_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "CME/source/CME_phase_1-2/Foo.xml"
            source.parent.mkdir(parents=True)
            source.write_text("canonical", encoding="utf-8")

            resolution = corpus_source_resolution.resolve_source(root, "Foo")
            self.assertEqual(source, resolution.path)
            self.assertEqual("unique", resolution.mode)

    def test_source_path_uses_explicit_override_for_divergent_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            old = root / "CME/source/CME_additions/Foo.xml"
            selected = root / "CME/source/recent_changes/additions_2023/Foo.xml"
            old.parent.mkdir(parents=True)
            selected.parent.mkdir(parents=True)
            old.write_text("older representation", encoding="utf-8")
            selected.write_text("publication representation", encoding="utf-8")
            self._write_source_override(
                root,
                "Foo",
                "CME/source/recent_changes/additions_2023/Foo.xml",
            )

            resolution = corpus_source_resolution.resolve_source(root, "Foo")
            self.assertEqual(selected, resolution.path)
            self.assertEqual("explicit_override", resolution.mode)
            self.assertEqual((old, selected), resolution.candidates)

    def test_source_path_rejects_unresolved_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            first = root / "CME/source/a/Foo.xml"
            second = root / "CME/source/b/Foo.xml"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "multiple sources"):
                corpus_source_resolution.resolve_source(root, "Foo")

    def test_mapped_source_missing_does_not_fall_back_to_sole_alternate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            alternate = root / "CME/source/CME_additions/Foo.xml"
            alternate.parent.mkdir(parents=True)
            alternate.write_text("legacy", encoding="utf-8")
            self._write_source_override(
                root,
                "Foo",
                "CME/source/recent_changes/additions_2023/Foo.xml",
                source_sha256="0" * 64,
            )

            with self.assertRaisesRegex(ValueError, "mapped source.*missing"):
                corpus_source_resolution.resolve_source(root, "Foo")

    def test_mapped_sparse_selected_source_succeeds_without_alternate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            selected = root / "CME/source/recent_changes/additions_2023/Foo.xml"
            selected.parent.mkdir(parents=True)
            selected.write_text("publication representation", encoding="utf-8")
            self._write_source_override(
                root,
                "Foo",
                "CME/source/recent_changes/additions_2023/Foo.xml",
            )

            resolution = corpus_source_resolution.resolve_source(root, "Foo")
            self.assertEqual(selected, resolution.path)
            self.assertEqual((selected,), resolution.candidates)

    def test_mapped_source_fixity_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            selected = root / "CME/source/recent_changes/Foo.xml"
            selected.parent.mkdir(parents=True)
            selected.write_text("changed representation", encoding="utf-8")
            self._write_source_override(
                root,
                "Foo",
                "CME/source/recent_changes/Foo.xml",
                source_sha256="0" * 64,
            )

            with self.assertRaisesRegex(ValueError, "fixity mismatch"):
                corpus_source_resolution.resolve_source(root, "Foo")

    def test_duplicate_source_override_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "CME/source/Foo.xml"
            source.parent.mkdir(parents=True)
            source.write_text("text", encoding="utf-8")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            path = root / "manifests/publication-set/source-overrides.json"
            path.parent.mkdir(parents=True)
            item = {
                "work_id": "Foo",
                "source_xml": "CME/source/Foo.xml",
                "source_sha256": digest,
            }
            path.write_text(json.dumps({"items": [item, item]}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate source override"):
                corpus_source_resolution.resolve_source(root, "Foo")

    def test_source_override_rejects_path_outside_exact_work_filename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "CME/source/Foo.xml"
            source.parent.mkdir(parents=True)
            source.write_text("text", encoding="utf-8")
            self._write_source_override(
                root,
                "Foo",
                "CME/source/../outside/Bar.xml",
                source_sha256="0" * 64,
            )

            with self.assertRaisesRegex(ValueError, "exact path under CME/source"):
                corpus_source_resolution.resolve_source(root, "Foo")

    def test_create_uses_explicit_source_for_sparse_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            selected = root / "CME/source/recent_changes/additions_2023/Foo.xml"
            selected.parent.mkdir(parents=True)
            selected.write_text("publication representation", encoding="utf-8")
            self._write_source_override(
                root,
                "Foo",
                "CME/source/recent_changes/additions_2023/Foo.xml",
            )

            with mock.patch.object(create_manifest_research_worktree, "_run") as run:
                destination, branch = create_manifest_research_worktree.create(
                    root, "Foo", "base-ref"
                )

            self.assertEqual(root / "build/research-worktrees/Foo", destination)
            self.assertEqual("research/foo", branch)
            run.assert_any_call(
                "git",
                "sparse-checkout",
                "set",
                "--no-cone",
                "/source/recent_changes/additions_2023/Foo.xml",
                cwd=destination / "CME",
            )

    def test_repository_source_overrides_match_snapshot_and_xml_fixity(self) -> None:
        override_path = (
            REPO_ROOT / "manifests/publication-set/source-overrides.json"
        )
        snapshot_path = REPO_ROOT / "manifests/publication-set/viewer-default.json"
        override = json.loads(override_path.read_text(encoding="utf-8"))
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        publications = {item["work_id"]: item for item in snapshot["items"]}

        work_ids = [item["work_id"] for item in override["items"]]
        self.assertEqual(len(work_ids), len(set(work_ids)))
        for item in override["items"]:
            work_id = item["work_id"]
            publication = publications[work_id]
            self.assertEqual(item["publication_filename"], publication["filename"])
            self.assertEqual(item["publication_sha256"], publication["sha256"])

            selected = REPO_ROOT / item["source_xml"]
            alternate = REPO_ROOT / item["alternate_xml"]
            candidates = sorted(
                (REPO_ROOT / "CME/source").rglob(f"{work_id}.xml")
            )
            self.assertEqual(sorted((selected, alternate)), candidates)
            self.assertEqual(
                item["source_sha256"],
                hashlib.sha256(selected.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                item["alternate_sha256"],
                hashlib.sha256(alternate.read_bytes()).hexdigest(),
            )
            resolution = corpus_source_resolution.resolve_source(REPO_ROOT, work_id)
            self.assertEqual(selected, resolution.path)
            self.assertEqual("explicit_override", resolution.mode)
            if work_id == "Paston":
                self.assertEqual(item["source_sha256"], item["alternate_sha256"])

    def test_inspection_packet_discloses_explicit_cme301_resolution(self) -> None:
        packet = inspect_corpus_source.inspect(REPO_ROOT, "CME301")
        self.assertEqual(
            "CME/source/recent_changes/additions_2023/CME301.xml",
            packet["source_path"],
        )
        self.assertEqual("explicit_override", packet["source_resolution"]["mode"])
        self.assertEqual(
            "manifests/publication-set/source-overrides.json",
            packet["source_resolution"]["override_manifest"],
        )
        self.assertEqual(
            "6a910352adc2d7b2974e1a9b59abf2a773c70b7a216a261126401cc5c29c8dd7",
            packet["sha256"],
        )

    def test_main_reports_and_creates_shared_source_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            destination = root / "build/research-worktrees/CME00099"
            output = io.StringIO()
            with mock.patch.object(
                create_manifest_research_worktree,
                "create",
                return_value=(destination, "research/cme00099"),
            ), contextlib.redirect_stdout(output):
                result = create_manifest_research_worktree.main(
                    ["CME00099", "--root", str(root)]
                )

            shared_cache = root / "source-cache/CME00099"
            self.assertEqual(0, result)
            self.assertTrue(shared_cache.is_dir())
            self.assertIn(f"worktree={destination}", output.getvalue())
            self.assertIn(f"cache_helper_root={root}", output.getvalue())
            self.assertIn(f"shared_source_cache={shared_cache}", output.getvalue())


if __name__ == "__main__":
    unittest.main()
