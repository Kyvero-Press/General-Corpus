#!/usr/bin/env python3
"""Run the smallest safe manifest/viewer validation gate since a Git ref."""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
WORK_MANIFEST = re.compile(
    r"^manifests/(?:lineage|work-metadata)/works/([^/]+)\.json$"
)
SAFE_WORK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
INDEX_PATHS = {
    "manifests/lineage/index.json",
    "manifests/work-metadata/index.json",
}
FULL_TRIGGER_PREFIXES = (
    "CME/",
    "dist/",
    "manifests/lineage/schemas/",
    "manifests/publication-set/",
    "manifests/work-metadata/schemas/",
)
FULL_TRIGGER_FILES = {
    "CME",
    ".gitmodules",
    "scripts/build-corpus-viewer-catalog.py",
    "scripts/rebuild-manifest-indexes.py",
    "scripts/run-changed-gate.py",
    "scripts/validate-lineage-manifests.py",
    "scripts/validate-manifest-pair.py",
    "scripts/validate-metadata-vocabulary.py",
    "scripts/validate-viewer-work.py",
    "scripts/validate-work-metadata-manifests.py",
}
GATE_TEST_FILES = {
    "tests/test_changed_gate.py",
    "tests/test_metadata_vocabulary.py",
    "tests/test_viewer_work_projection.py",
}
VIEWER_FILES = {
    "tests/test_corpus_viewer_catalog.py",
}
TARGETED_TESTS = {
    "scripts/cache-iiif-bundle.py": "tests.test_iiif_bundle_cache",
    "scripts/cache-source-download.py": "tests.test_source_cache",
    "scripts/corpus_source_resolution.py": "tests.test_manifest_research_worktree",
    "scripts/create-manifest-research-worktree.py": "tests.test_manifest_research_worktree",
    "scripts/inspect-corpus-source.py": "tests.test_manifest_research_worktree",
    "tests/test_iiif_bundle_cache.py": "tests.test_iiif_bundle_cache",
    "tests/test_lineage_manifests.py": "tests.test_lineage_manifests",
    "tests/test_manifest_research_worktree.py": "tests.test_manifest_research_worktree",
    "tests/test_source_cache.py": "tests.test_source_cache",
    "tests/test_work_metadata_manifests.py": "tests.test_work_metadata_manifests",
}
RELEVANT_UNTRACKED_PREFIXES = (
    ".agents/skills/",
    "manifests/",
    "scripts/",
    "tests/",
    "viewer/",
)


@dataclass(frozen=True)
class GateCommand:
    label: str
    argv: tuple[str, ...]
    cwd: str = "."


@dataclass(frozen=True)
class GatePlan:
    paths: tuple[str, ...]
    work_ids: tuple[str, ...]
    full: bool
    reasons: tuple[str, ...]
    commands: tuple[GateCommand, ...]


def _python(*args: str, label: str, cwd: str = ".") -> GateCommand:
    return GateCommand(label, (sys.executable, *args), cwd)


def _deduplicate(commands: Iterable[GateCommand]) -> tuple[GateCommand, ...]:
    seen: set[tuple[str, tuple[str, ...]]] = set()
    result: list[GateCommand] = []
    for command in commands:
        key = (command.cwd, command.argv)
        if key in seen:
            continue
        seen.add(key)
        result.append(command)
    return tuple(result)


def _full_commands() -> list[GateCommand]:
    return [
        _python(
            "scripts/rebuild-manifest-indexes.py",
            "--check",
            label="deterministic manifest indexes",
        ),
        _python("scripts/validate-lineage-manifests.py", label="all lineage manifests"),
        _python(
            "scripts/validate-work-metadata-manifests.py",
            label="all work-metadata manifests",
        ),
        _python(
            "scripts/validate-metadata-vocabulary.py",
            label="corpus metadata vocabulary",
        ),
        _python(
            "-m",
            "unittest",
            "tests.test_lineage_manifests",
            "tests.test_work_metadata_manifests",
            "tests.test_manifest_index_rebuilder",
            "tests.test_manifest_research_worktree",
            "tests.test_iiif_bundle_cache",
            "tests.test_source_cache",
            "tests.test_corpus_viewer_catalog",
            "tests.test_changed_gate",
            "tests.test_metadata_vocabulary",
            "tests.test_viewer_work_projection",
            label="full manifest and viewer unit suite",
        ),
        _python(
            "scripts/build-corpus-viewer-catalog.py",
            "--output-root",
            "build/corpus-viewer/public",
            "--skip-manifest-validation",
            "--require-pdfs",
            "--publication-inventory",
            "manifests/publication-set/viewer-default.json",
            label="full viewer catalog",
        ),
        GateCommand("viewer tests", ("npm", "test", "--", "--run"), "viewer"),
        GateCommand("viewer typecheck", ("npm", "run", "typecheck"), "viewer"),
        GateCommand("viewer production build", ("npm", "exec", "vite", "build"), "viewer"),
    ]


def plan_for_paths(
    paths: Iterable[str],
    *,
    base: str,
    force_full: bool = False,
    root: Path | None = None,
    untracked_paths: Iterable[str] = (),
) -> GatePlan:
    normalized = tuple(sorted({path.removeprefix("./") for path in paths if path}))
    work_ids = tuple(
        sorted(
            {
                match.group(1)
                for path in normalized
                if (match := WORK_MANIFEST.fullmatch(path)) is not None
            }
        )
    )
    reasons: list[str] = []
    if force_full:
        reasons.append("full gate explicitly requested")
    for work_id in work_ids:
        if SAFE_WORK_ID.fullmatch(work_id) is None:
            reasons.append(f"unsafe work ID in manifest filename: {work_id!r}")
    if root is not None:
        for work_id in work_ids:
            expected_pair = (
                root / "manifests" / "lineage" / "works" / f"{work_id}.json",
                root / "manifests" / "work-metadata" / "works" / f"{work_id}.json",
            )
            if not all(path.is_file() for path in expected_pair):
                reasons.append(
                    f"work manifest deleted or renamed; pair is incomplete: {work_id}"
                )
    for path in normalized:
        if path in FULL_TRIGGER_FILES or path.startswith(FULL_TRIGGER_PREFIXES):
            reasons.append(f"shared manifest infrastructure changed: {path}")
        elif (
            (path.startswith("scripts/") or path.startswith("tests/"))
            and path.endswith(".py")
            and path not in GATE_TEST_FILES
            and path not in VIEWER_FILES
            and path not in TARGETED_TESTS
        ):
            reasons.append(f"unmapped Python infrastructure changed: {path}")
    if INDEX_PATHS.intersection(normalized) and not work_ids:
        reasons.append("manifest indexes changed without a work-manifest change")

    full = bool(reasons)
    commands: list[GateCommand] = [
        GateCommand("whitespace errors", ("git", "diff", "--check", base, "--"))
    ]
    normalized_untracked = tuple(
        sorted({path.removeprefix("./") for path in untracked_paths if path})
    )
    if normalized_untracked:
        whitespace_args: list[str] = [
            "scripts/run-changed-gate.py",
            "--check-untracked-whitespace",
        ]
        for path in normalized_untracked:
            whitespace_args.extend(("--whitespace-path", path))
        commands.append(
            _python(*whitespace_args, label="untracked-file whitespace errors")
        )
    if full:
        commands.extend(_full_commands())
    else:
        for work_id in work_ids:
            commands.extend(
                [
                    _python(
                        "scripts/validate-manifest-pair.py",
                        "--",
                        work_id,
                        label=f"manifest pair {work_id}",
                    ),
                    _python(
                        "scripts/validate-viewer-work.py",
                        "--",
                        work_id,
                        label=f"viewer projection {work_id}",
                    ),
                ]
            )
        if work_ids:
            commands.extend(
                [
                    _python(
                        "scripts/rebuild-manifest-indexes.py",
                        "--check",
                        label="deterministic manifest indexes",
                    ),
                    _python(
                        "scripts/validate-metadata-vocabulary.py",
                        label="corpus metadata vocabulary",
                    ),
                ]
            )

        if GATE_TEST_FILES.intersection(normalized):
            commands.append(
                _python(
                    "-m",
                    "unittest",
                    "tests.test_changed_gate",
                    "tests.test_metadata_vocabulary",
                    "tests.test_viewer_work_projection",
                    label="changed-gate unit tests",
                )
            )

        viewer_changed = any(path.startswith("viewer/") for path in normalized) or bool(
            VIEWER_FILES.intersection(normalized)
        )
        if viewer_changed:
            commands.extend(
                [
                    _python(
                        "-m",
                        "unittest",
                        "tests.test_corpus_viewer_catalog",
                        label="viewer catalog unit tests",
                    ),
                    _python(
                        "scripts/build-corpus-viewer-catalog.py",
                        "--output-root",
                        "build/corpus-viewer/public",
                        "--skip-manifest-validation",
                        label="viewer catalog build",
                    ),
                    GateCommand("viewer tests", ("npm", "test", "--", "--run"), "viewer"),
                    GateCommand("viewer typecheck", ("npm", "run", "typecheck"), "viewer"),
                    GateCommand(
                        "viewer production build",
                        ("npm", "exec", "vite", "build"),
                        "viewer",
                    ),
                ]
            )

        targeted_modules = sorted(
            {TARGETED_TESTS[path] for path in normalized if path in TARGETED_TESTS}
        )
        if targeted_modules:
            commands.append(
                _python(
                    "-m",
                    "unittest",
                    *targeted_modules,
                    label="targeted Python unit tests",
                )
            )

    if any(path.startswith(".agents/skills/") for path in normalized):
        validator = (
            Path.home()
            / ".codex/skills/.system/skill-creator/scripts/quick_validate.py"
        )
        commands.append(
            _python(
                str(validator),
                ".agents/skills/research-corpus-manifests",
                label="project manifest-research skill",
            )
        )

    return GatePlan(
        paths=normalized,
        work_ids=work_ids,
        full=full,
        reasons=tuple(dict.fromkeys(reasons)),
        commands=_deduplicate(commands),
    )


def _git_output(root: Path, *args: str) -> bytes:
    process = subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        message = process.stderr.decode(errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return process.stdout


def _ref_exists(root: Path, ref: str) -> bool:
    process = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return process.returncode == 0


def default_base(root: Path) -> str:
    for candidate in ("origin/main", "HEAD^"):
        if _ref_exists(root, candidate):
            return candidate
    return "HEAD"


def changed_paths(root: Path, base: str) -> set[str]:
    tracked = {
        item.decode()
        for item in _git_output(root, "diff", "--name-only", "-z", base, "--").split(b"\0")
        if item
    }
    return tracked | untracked_paths(root)


def untracked_paths(root: Path) -> set[str]:
    return {
        item.decode()
        for item in _git_output(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ).split(b"\0")
        if item and item.decode().startswith(RELEVANT_UNTRACKED_PREFIXES)
    }


def check_untracked_whitespace(root: Path, paths: Iterable[str]) -> int:
    failed = False
    normalized = tuple(sorted(set(paths)))
    for relative in normalized:
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            print(f"ERROR: whitespace path escapes repository: {relative}", file=sys.stderr)
            failed = True
            continue
        if not candidate.is_file():
            print(f"ERROR: untracked whitespace path is not a file: {relative}", file=sys.stderr)
            failed = True
            continue
        process = subprocess.run(
            ["git", "diff", "--no-index", "--check", "--", "/dev/null", str(candidate)],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if process.stdout:
            print(process.stdout, end="", file=sys.stderr)
            failed = True
        elif process.returncode not in {0, 1}:
            message = process.stderr.strip() or f"git diff exited {process.returncode}"
            print(f"ERROR: could not check whitespace in {relative}: {message}", file=sys.stderr)
            failed = True
    if not failed:
        print(f"Checked whitespace in {len(normalized)} untracked file(s).")
    return int(failed)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--base", help="Git ref to compare (defaults to origin/main)")
    parser.add_argument("--path", action="append", default=[], help="plan for an explicit path")
    parser.add_argument("--dry-run", action="store_true", help="print commands without running them")
    parser.add_argument("--full", action="store_true", help="force the full corpus gate")
    parser.add_argument(
        "--check-untracked-whitespace",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--whitespace-path",
        action="append",
        default=[],
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    if args.check_untracked_whitespace:
        return check_untracked_whitespace(root, args.whitespace_path)
    base = args.base or default_base(root)
    if not _ref_exists(root, base):
        print(f"ERROR: base ref does not resolve to a commit: {base}", file=sys.stderr)
        return 2
    detected_untracked = untracked_paths(root)
    paths = changed_paths(root, base)
    paths.update(args.path)
    plan = plan_for_paths(
        paths,
        base=base,
        force_full=args.full,
        root=root,
        untracked_paths=detected_untracked,
    )

    print(f"Changed-scope gate: {'FULL' if plan.full else 'TARGETED'}")
    print(f"Base: {base}")
    if plan.work_ids:
        print(f"Work IDs: {', '.join(plan.work_ids)}")
    if plan.reasons:
        for reason in plan.reasons:
            print(f"Escalation: {reason}")
    if not plan.paths:
        print("No changed paths detected.")
    for command in plan.commands:
        rendered = shlex.join(command.argv)
        prefix = f"(cd {command.cwd} && " if command.cwd != "." else ""
        suffix = ")" if command.cwd != "." else ""
        print(f"[{command.label}] {prefix}{rendered}{suffix}")
        if args.dry_run:
            continue
        process = subprocess.run(command.argv, cwd=root / command.cwd, check=False)
        if process.returncode != 0:
            print(f"FAILED: {command.label}", file=sys.stderr)
            return process.returncode
    print("Changed-scope gate passed." if not args.dry_run else "Dry-run plan complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
