"""Fail-closed selection of the XML representation behind a corpus publication."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SOURCE_OVERRIDES = Path("manifests/publication-set/source-overrides.json")
SAFE_WORK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SourceResolution:
    path: Path
    mode: str
    candidates: tuple[Path, ...]
    override_manifest: Path | None = None
    basis: str | None = None


def _relative(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def _candidate_paths(root: Path, work_id: str) -> tuple[Path, ...]:
    expected_name = f"{work_id}.xml"
    return tuple(
        sorted(
            path
            for path in (root / "CME/source").rglob("*.xml")
            if path.name == expected_name
        )
    )


def _load_overrides(root: Path) -> tuple[dict[str, dict[str, Any]], str | None]:
    manifest_path = root / SOURCE_OVERRIDES
    if not manifest_path.is_file():
        return {}, None
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read source override manifest {manifest_path}: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise ValueError(f"invalid source override manifest: {manifest_path}")
    basis = document.get("basis")
    if basis is not None and not isinstance(basis, str):
        raise ValueError(f"invalid source override basis in {manifest_path}")

    overrides: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(document["items"]):
        if not isinstance(item, dict):
            raise ValueError(f"invalid source override item {index} in {manifest_path}")
        item_work_id = item.get("work_id")
        source_xml = item.get("source_xml")
        source_sha256 = item.get("source_sha256")
        if not isinstance(item_work_id, str) or SAFE_WORK_ID.fullmatch(item_work_id) is None:
            raise ValueError(f"invalid work_id in source override item {index}: {item_work_id!r}")
        if item_work_id in overrides:
            raise ValueError(f"duplicate source override for {item_work_id!r}")
        if not isinstance(source_xml, str):
            raise ValueError(f"invalid source_xml override for {item_work_id!r}")
        relative = Path(source_xml)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or relative.parts[:2] != ("CME", "source")
            or relative.name != f"{item_work_id}.xml"
        ):
            raise ValueError(
                f"source override for {item_work_id!r} is not its exact path under "
                f"CME/source: {source_xml!r}"
            )
        if not isinstance(source_sha256, str) or SHA256.fullmatch(source_sha256) is None:
            raise ValueError(f"invalid source_sha256 override for {item_work_id!r}")
        overrides[item_work_id] = item
    return overrides, basis


def resolve_source(root: Path, work_id: str) -> SourceResolution:
    root = root.resolve()
    if SAFE_WORK_ID.fullmatch(work_id) is None:
        raise ValueError(f"unsafe corpus work ID: {work_id!r}")

    overrides, basis = _load_overrides(root)
    candidates = _candidate_paths(root, work_id)
    override = overrides.get(work_id)
    if override is not None:
        selected = root / override["source_xml"]
        if not selected.is_file():
            available = [_relative(path, root) for path in candidates]
            raise ValueError(
                f"mapped source for {work_id!r} is missing: {override['source_xml']!r}; "
                f"available candidates: {available!r}"
            )
        source_root = (root / "CME/source").resolve()
        if not selected.resolve().is_relative_to(source_root):
            raise ValueError(
                f"mapped source for {work_id!r} resolves outside CME/source: "
                f"{override['source_xml']!r}"
            )
        actual_sha256 = hashlib.sha256(selected.read_bytes()).hexdigest()
        if actual_sha256 != override["source_sha256"]:
            raise ValueError(
                f"mapped source fixity mismatch for {work_id!r}: "
                f"expected {override['source_sha256']}, got {actual_sha256}"
            )
        return SourceResolution(
            path=selected,
            mode="explicit_override",
            candidates=candidates,
            override_manifest=root / SOURCE_OVERRIDES,
            basis=basis,
        )

    if len(candidates) == 1:
        return SourceResolution(path=candidates[0], mode="unique", candidates=candidates)
    if not candidates:
        raise ValueError(f"expected a source for {work_id!r}, found none")
    raise ValueError(
        f"multiple sources for {work_id!r} without an explicit override: "
        f"{[_relative(path, root) for path in candidates]!r}"
    )
