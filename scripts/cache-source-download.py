#!/usr/bin/env python3
"""Download one exact lineage source into the gitignored local source cache."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen


SAFE_WORK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


class CacheError(RuntimeError):
    """Raised when a source cannot be cached safely."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_url(raw_url: str) -> str:
    if raw_url != raw_url.strip() or any(character.isspace() for character in raw_url):
        raise CacheError("download URL must not contain whitespace")
    parsed = urlsplit(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise CacheError("download URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise CacheError("download URL must not contain credentials")
    return raw_url


def infer_filename(raw_url: str) -> str:
    filename = unquote(Path(urlsplit(raw_url).path).name)
    if not filename:
        raise CacheError("URL has no filename; pass --filename explicitly")
    return filename


def validate_filename(filename: str) -> str:
    if not SAFE_FILENAME.fullmatch(filename):
        raise CacheError(
            "cache filename must contain only letters, digits, dot, underscore, plus, or hyphen"
        )
    return filename


def download(
    *,
    repo_root: Path,
    work_id: str,
    raw_url: str,
    filename: str,
    media_type: str | None,
    label: str,
    coverage: str,
    force: bool,
) -> dict[str, object]:
    if not SAFE_WORK_ID.fullmatch(work_id):
        raise CacheError(f"unsafe work ID: {work_id!r}")
    url = validate_url(raw_url)
    filename = validate_filename(filename)
    relative = Path("source-cache") / work_id / filename
    destination = repo_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)

    request = Request(
        url,
        headers={
            "User-Agent": "General-Corpus-source-cache/1.0 (+https://github.com/Kyvero-Press/General-Corpus)"
        },
    )
    temp_path: Path | None = None
    response_media_type = "application/octet-stream"
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{filename}.", suffix=".partial", dir=destination.parent, delete=False
        ) as temp_stream:
            temp_path = Path(temp_stream.name)
            with urlopen(request, timeout=60) as response:
                response_media_type = response.headers.get_content_type()
                shutil.copyfileobj(response, temp_stream, length=1024 * 1024)
        if temp_path.stat().st_size <= 0:
            raise CacheError("downloaded file is empty")
        # Check the content using the destination suffix without renaming the partial file.
        suffix_probe = destination
        with temp_path.open("rb") as stream:
            header = stream.read(8)
        if suffix_probe.suffix.casefold() == ".pdf" and not header.startswith(b"%PDF-"):
            raise CacheError("downloaded .pdf does not have a PDF header")
        if suffix_probe.suffix.casefold() == ".zip" and not header.startswith(b"PK"):
            raise CacheError("downloaded .zip does not have a ZIP header")

        new_digest = sha256(temp_path)
        if destination.exists() and not force:
            if destination.is_file() and sha256(destination) == new_digest:
                temp_path.unlink()
                temp_path = None
            else:
                raise CacheError(
                    f"cache destination already exists with different content: {relative.as_posix()}"
                )
        else:
            os.replace(temp_path, destination)
            temp_path = None
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise CacheError(f"download failed: {exc}") from exc
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    return {
        "label": label,
        "path": relative.as_posix(),
        "source_url": url,
        "sha256": sha256(destination),
        "bytes": destination.stat().st_size,
        "media_type": media_type or response_media_type,
        "downloaded_on": date.today().isoformat(),
        "coverage": coverage,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("work_id", help="exact corpus work ID")
    result.add_argument("url", help="exact direct file URL")
    result.add_argument(
        "--filename",
        help="safe cache filename; defaults to the decoded URL path basename",
    )
    result.add_argument("--media-type", help="override the HTTP response media type")
    result.add_argument(
        "--label",
        help="human-readable file label; defaults to the cache filename",
    )
    result.add_argument(
        "--coverage",
        choices=("complete", "partial", "metadata_only", "unknown"),
        default="unknown",
        help="how completely this file represents the described source",
    )
    result.add_argument("--force", action="store_true", help="replace differing cached content")
    result.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository root",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        local_copy = download(
            repo_root=args.root.resolve(),
            work_id=args.work_id,
            raw_url=args.url,
            filename=args.filename or infer_filename(args.url),
            media_type=args.media_type,
            label=args.label or args.filename or infer_filename(args.url),
            coverage=args.coverage,
            force=args.force,
        )
    except CacheError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"local_copies": [local_copy]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
