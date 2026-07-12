import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "run-changed-gate.py"
SPEC = importlib.util.spec_from_file_location("run_changed_gate", MODULE_PATH)
run_changed_gate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = run_changed_gate
assert SPEC.loader is not None
SPEC.loader.exec_module(run_changed_gate)


class ChangedGateTests(unittest.TestCase):
    def plan(
        self,
        *paths: str,
        full: bool = False,
        root: Path | None = None,
        untracked: tuple[str, ...] = (),
    ):
        return run_changed_gate.plan_for_paths(
            paths,
            base="origin/main",
            force_full=full,
            root=root,
            untracked_paths=untracked,
        )

    def test_manifest_pair_uses_targeted_pair_index_and_vocabulary_checks(self) -> None:
        plan = self.plan(
            "manifests/lineage/works/CME00071.json",
            "manifests/work-metadata/works/CME00071.json",
            "manifests/lineage/index.json",
            "manifests/work-metadata/index.json",
            ".agents/skills/research-corpus-manifests/references/metadata-modeling.md",
        )

        self.assertFalse(plan.full)
        self.assertEqual(("CME00071",), plan.work_ids)
        labels = [command.label for command in plan.commands]
        self.assertIn("manifest pair CME00071", labels)
        self.assertIn("viewer projection CME00071", labels)
        self.assertIn("deterministic manifest indexes", labels)
        self.assertIn("corpus metadata vocabulary", labels)
        self.assertIn("project manifest-research skill", labels)
        self.assertNotIn("full viewer catalog", labels)

    def test_multiple_work_pairs_each_validate_without_full_escalation(self) -> None:
        plan = self.plan(
            "manifests/lineage/works/CME00070.json",
            "manifests/work-metadata/works/CME00070.json",
            "manifests/lineage/works/CME00071.json",
            "manifests/work-metadata/works/CME00071.json",
            "manifests/lineage/index.json",
            "manifests/work-metadata/index.json",
        )

        self.assertFalse(plan.full)
        self.assertEqual(("CME00070", "CME00071"), plan.work_ids)
        pair_labels = [
            command.label
            for command in plan.commands
            if command.label.startswith("manifest pair")
        ]
        self.assertEqual(
            ["manifest pair CME00070", "manifest pair CME00071"],
            pair_labels,
        )

    def test_schema_or_shared_validator_change_escalates_to_full_gate(self) -> None:
        for path in (
            "manifests/lineage/schemas/lineage-manifest.schema.json",
            "scripts/validate-lineage-manifests.py",
            "scripts/rebuild-manifest-indexes.py",
        ):
            with self.subTest(path=path):
                plan = self.plan(path)
                self.assertTrue(plan.full)
                self.assertIn("full viewer catalog", [item.label for item in plan.commands])

    def test_source_and_publication_wide_changes_escalate(self) -> None:
        for path in (
            ".gitmodules",
            "CME",
            "CME/CME00071.xml",
            "dist/CME00071.pdf",
            "manifests/publication-set/viewer-default.json",
        ):
            with self.subTest(path=path):
                self.assertTrue(self.plan(path).full)

    def test_deleted_or_renamed_manifest_escalates_in_repository_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lineage = root / "manifests/lineage/works/CME00071.json"
            lineage.parent.mkdir(parents=True)
            lineage.write_text("{}\n", encoding="utf-8")
            plan = self.plan(
                "manifests/lineage/works/CME00071.json",
                "manifests/work-metadata/works/CME00071.json",
                root=root,
            )

        self.assertTrue(plan.full)
        self.assertTrue(any("deleted or renamed" in item for item in plan.reasons))

    def test_unsafe_filename_work_id_escalates_instead_of_becoming_an_option(self) -> None:
        plan = self.plan("manifests/lineage/works/--help.json")

        self.assertTrue(plan.full)
        self.assertTrue(any("unsafe work ID" in item for item in plan.reasons))

    def test_index_only_change_escalates_to_full_gate(self) -> None:
        plan = self.plan("manifests/lineage/index.json")

        self.assertTrue(plan.full)
        self.assertTrue(any("without a work-manifest" in item for item in plan.reasons))

    def test_viewer_change_runs_only_viewer_and_catalog_tests(self) -> None:
        plan = self.plan("viewer/src/components/WorkDetail.tsx")

        self.assertFalse(plan.full)
        labels = [command.label for command in plan.commands]
        self.assertIn("viewer catalog unit tests", labels)
        self.assertIn("viewer catalog build", labels)
        self.assertIn("viewer tests", labels)
        self.assertIn("viewer typecheck", labels)
        self.assertIn("viewer production build", labels)
        self.assertNotIn("all lineage manifests", labels)

    def test_gate_implementation_change_requires_full_audit(self) -> None:
        plan = self.plan(
            "scripts/run-changed-gate.py",
            "scripts/validate-metadata-vocabulary.py",
            "scripts/validate-viewer-work.py",
        )

        self.assertTrue(plan.full)
        labels = [command.label for command in plan.commands]
        self.assertIn("full manifest and viewer unit suite", labels)

    def test_gate_test_change_runs_its_own_tests_without_recursing(self) -> None:
        plan = self.plan(
            "tests/test_changed_gate.py",
            "tests/test_metadata_vocabulary.py",
            "tests/test_viewer_work_projection.py",
        )

        self.assertFalse(plan.full)
        labels = [command.label for command in plan.commands]
        self.assertEqual(1, labels.count("changed-gate unit tests"))

    def test_untracked_files_get_a_separate_whitespace_check(self) -> None:
        path = "scripts/new-tool.py"
        plan = self.plan(path, untracked=(path,))

        labels = [command.label for command in plan.commands]
        self.assertIn("untracked-file whitespace errors", labels)

    def test_untracked_whitespace_helper_fails_on_trailing_space(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            clean = root / "clean.py"
            clean.write_text("value = 1\n", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    0,
                    run_changed_gate.check_untracked_whitespace(root, ["clean.py"]),
                )
            clean.write_text("value = 1 \n", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(
                    1,
                    run_changed_gate.check_untracked_whitespace(root, ["clean.py"]),
                )

    def test_catalog_builder_change_requires_full_audit(self) -> None:
        self.assertTrue(self.plan("scripts/build-corpus-viewer-catalog.py").full)

    def test_cache_helper_change_runs_its_targeted_test(self) -> None:
        plan = self.plan("scripts/cache-source-download.py")

        self.assertFalse(plan.full)
        command = next(item for item in plan.commands if item.label == "targeted Python unit tests")
        self.assertIn("tests.test_source_cache", command.argv)

    def test_unmapped_python_change_escalates_but_documentation_does_not(self) -> None:
        self.assertTrue(self.plan("scripts/new-unmapped-tool.py").full)
        docs_plan = self.plan("docs/corpus-viewer.md")
        self.assertFalse(docs_plan.full)
        self.assertEqual(["whitespace errors"], [item.label for item in docs_plan.commands])

    def test_full_flag_forces_full_gate(self) -> None:
        plan = self.plan("docs/corpus-viewer.md", full=True)

        self.assertTrue(plan.full)
        self.assertIn("full gate explicitly requested", plan.reasons)
        labels = [item.label for item in plan.commands]
        self.assertIn("deterministic manifest indexes", labels)
        unit_command = next(
            item for item in plan.commands if item.label == "full manifest and viewer unit suite"
        )
        self.assertIn("tests.test_manifest_index_rebuilder", unit_command.argv)
        catalog_command = next(
            item for item in plan.commands if item.label == "full viewer catalog"
        )
        self.assertIn("--require-pdfs", catalog_command.argv)
        self.assertIn("--publication-inventory", catalog_command.argv)


if __name__ == "__main__":
    unittest.main()
