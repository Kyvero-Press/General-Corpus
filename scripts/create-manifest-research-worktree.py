#!/usr/bin/env python3
"""Create a one-work research branch with a sparse CME submodule checkout."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def _slug(work_id: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", work_id.casefold()).strip("-")
    if not value:
        raise ValueError(f"cannot derive branch slug from {work_id!r}")
    return value


def create(root: Path, work_id: str, base: str) -> tuple[Path, str]:
    sources = sorted((root / "CME/source").rglob(f"{work_id}.xml"))
    if len(sources) != 1:
        raise ValueError(f"expected one source for {work_id!r}, found {sources!r}")
    source_in_cme = sources[0].relative_to(root / "CME")
    destination = root / "build/research-worktrees" / work_id
    branch = f"research/{_slug(work_id)}"
    if destination.exists():
        raise ValueError(f"worktree path already exists: {destination}")

    _run(
        "git",
        "worktree",
        "add",
        "-b",
        branch,
        str(destination),
        base,
        cwd=root,
    )
    try:
        _run(
            "git",
            "submodule",
            "update",
            "--init",
            "--reference",
            str(root / "CME"),
            "CME",
            cwd=destination,
        )
        _run(
            "git",
            "sparse-checkout",
            "init",
            "--no-cone",
            cwd=destination / "CME",
        )
        _run(
            "git",
            "sparse-checkout",
            "set",
            "--no-cone",
            f"/{source_in_cme}",
            cwd=destination / "CME",
        )
    except Exception:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(destination)],
            cwd=root,
            check=False,
        )
        raise
    return destination, branch


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_id")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--base", default="HEAD")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    destination, branch = create(root, args.work_id, args.base)
    shared_source_cache = root / "source-cache" / args.work_id
    shared_source_cache.mkdir(parents=True, exist_ok=True)
    print(f"worktree={destination}")
    print(f"branch={branch}")
    print(f"cache_helper_root={root}")
    print(f"shared_source_cache={shared_source_cache}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
