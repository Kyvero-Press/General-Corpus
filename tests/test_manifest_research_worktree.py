import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "create-manifest-research-worktree.py"
SPEC = importlib.util.spec_from_file_location("create_manifest_research_worktree", MODULE_PATH)
create_manifest_research_worktree = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = create_manifest_research_worktree
assert SPEC.loader is not None
SPEC.loader.exec_module(create_manifest_research_worktree)


class ManifestResearchWorktreeTests(unittest.TestCase):
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
