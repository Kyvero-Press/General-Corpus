#!/usr/bin/env python3
"""Cache a complete IIIF image object as one auditable ZIP bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


SAFE_WORK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
SAFE_IIIF_SIZE = re.compile(r"^[A-Za-z0-9!^.,:+-]+$")
USER_AGENT = (
    "General-Corpus-source-cache/1.0 "
    "(+https://github.com/Kyvero-Press/General-Corpus)"
)


class BundleError(RuntimeError):
    """Raised when an IIIF source cannot be bundled safely and completely."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_url(raw_url: str) -> str:
    if raw_url != raw_url.strip() or any(character.isspace() for character in raw_url):
        raise BundleError("URL must not contain whitespace")
    parsed = urlsplit(raw_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise BundleError("URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise BundleError("URL must not contain credentials")
    return raw_url


def normalize_provider_url(raw_url: str) -> str:
    """Encode literal provider URL spaces while rejecting all other whitespace."""

    if any(character.isspace() and character != " " for character in raw_url):
        raise BundleError("provider URL contains unsupported whitespace")
    return validate_url(raw_url.replace(" ", "%20"))


def validate_filename(filename: str) -> str:
    if not SAFE_FILENAME.fullmatch(filename):
        raise BundleError(
            "cache filename must contain only letters, digits, dot, underscore, plus, or hyphen"
        )
    if not filename.casefold().endswith(".zip"):
        raise BundleError("IIIF bundle filename must end in .zip")
    return filename


def _request(url: str) -> Request:
    return Request(validate_url(url), headers={"User-Agent": USER_AGENT})


def fetch_bytes(url: str, *, timeout: float, retries: int) -> bytes:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(_request(url), timeout=timeout) as response:
                payload = response.read()
            if not payload:
                raise BundleError(f"empty response from {url}")
            return payload
        except HTTPError as exc:
            exc.close()
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
        except (URLError, TimeoutError, OSError, BundleError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
    raise BundleError(f"request failed for {url}: {last_error}") from last_error


def _label(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, list):
        for item in value:
            result = _label(item, "")
            if result:
                return result
    if isinstance(value, dict):
        for preferred in ("en", "none"):
            result = _label(value.get(preferred), "")
            if result:
                return result
        for item in value.values():
            result = _label(item, "")
            if result:
                return result
    return fallback


def _first_mapping(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return next((item for item in value if isinstance(item, dict)), None)
    return None


def _service_for(body: dict[str, Any]) -> dict[str, Any] | None:
    return _first_mapping(body.get("service"))


def _service_url(service: dict[str, Any]) -> str | None:
    value = service.get("id") or service.get("@id")
    if not isinstance(value, str) or not value:
        return None
    return value.removesuffix("/info.json").rstrip("/")


def _is_image_api_3(service: dict[str, Any]) -> bool:
    service_type = str(service.get("type", ""))
    context = str(service.get("@context", ""))
    profile = str(service.get("profile", ""))
    return (
        service_type == "ImageService3"
        or "/image/3/" in context
        or "/image/3/" in profile
    )


def _image_url(
    body: dict[str, Any],
    *,
    image_size: str | None,
    image_format: str,
) -> tuple[str, str]:
    service = _service_for(body)
    if service is not None:
        base = _service_url(service)
        if base:
            size = image_size or ("max" if _is_image_api_3(service) else "full")
            return f"{base}/full/{size}/0/default.{image_format}", size

    direct = body.get("id") or body.get("@id")
    if isinstance(direct, str) and direct:
        return normalize_provider_url(direct), "provider_resource"
    raise BundleError("canvas painting annotation has no downloadable image body")


def _v2_canvases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sequences = manifest.get("sequences")
    if not isinstance(sequences, list) or not sequences:
        return []
    sequence = _first_mapping(sequences)
    if sequence is None or not isinstance(sequence.get("canvases"), list):
        return []
    return [item for item in sequence["canvases"] if isinstance(item, dict)]


def _v3_canvases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    items = manifest.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _v2_body(canvas: dict[str, Any]) -> dict[str, Any] | None:
    images = canvas.get("images")
    annotation = _first_mapping(images)
    if annotation is None:
        return None
    return _first_mapping(annotation.get("resource"))


def _v3_body(canvas: dict[str, Any]) -> dict[str, Any] | None:
    annotation_page = _first_mapping(canvas.get("items"))
    if annotation_page is None:
        return None
    annotation = _first_mapping(annotation_page.get("items"))
    if annotation is None:
        return None
    body = annotation.get("body")
    if isinstance(body, list):
        image_body = next(
            (
                item
                for item in body
                if isinstance(item, dict)
                and str(item.get("type", "")).casefold() in {"image", ""}
            ),
            None,
        )
        return image_body
    return _first_mapping(body)


def _non_upscaling_size(image_size: str | None, canvas: dict[str, Any]) -> str | None:
    """Use the service's native-size keyword when a simple request would upscale."""

    if image_size is None:
        return None
    width = canvas.get("width")
    height = canvas.get("height")
    width_match = re.fullmatch(r"(\d+),", image_size)
    if width_match and isinstance(width, int) and width < int(width_match.group(1)):
        return None
    height_match = re.fullmatch(r",(\d+)", image_size)
    if height_match and isinstance(height, int) and height < int(height_match.group(1)):
        return None
    box_match = re.fullmatch(r"!(\d+),(\d+)", image_size)
    if (
        box_match
        and isinstance(width, int)
        and isinstance(height, int)
        and width < int(box_match.group(1))
        and height < int(box_match.group(2))
    ):
        return None
    return image_size


def extract_canvas_sources(
    manifest: dict[str, Any],
    *,
    image_size: str | None = None,
    image_format: str = "jpg",
) -> list[dict[str, Any]]:
    canvases = _v2_canvases(manifest)
    body_reader = _v2_body
    presentation_version = 2
    if not canvases:
        canvases = _v3_canvases(manifest)
        body_reader = _v3_body
        presentation_version = 3
    if not canvases:
        raise BundleError("IIIF Presentation manifest contains no canvases")

    sources: list[dict[str, Any]] = []
    for index, canvas in enumerate(canvases, start=1):
        body = body_reader(canvas)
        if body is None:
            raise BundleError(f"canvas {index} has no painting image")
        image_url, request_size = _image_url(
            body,
            image_size=_non_upscaling_size(image_size, canvas),
            image_format=image_format,
        )
        canvas_url = canvas.get("id") or canvas.get("@id")
        if not isinstance(canvas_url, str) or not canvas_url:
            raise BundleError(f"canvas {index} has no identifier URL")
        source = {
            "index": index,
            "label": _label(canvas.get("label"), f"Canvas {index}"),
            "canvas_url": normalize_provider_url(canvas_url),
            "image_url": normalize_provider_url(image_url),
            "image_request_size": request_size,
            "presentation_version": presentation_version,
        }
        if image_size is not None and request_size == image_size:
            fallback_url, fallback_size = _image_url(
                body,
                image_size=None,
                image_format=image_format,
            )
            fallback_url = normalize_provider_url(fallback_url)
            if fallback_url != source["image_url"]:
                source["fallback_image_url"] = fallback_url
                source["fallback_image_request_size"] = fallback_size
        sources.append(source)
    return sources


def extract_image_url_sources(path: Path) -> list[dict[str, Any]]:
    """Load an explicit full-object image inventory without inventing IIIF canvases."""

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BundleError(f"cannot read image URL list {path}: {exc}") from exc
    try:
        decoded = json.loads(raw_text)
    except json.JSONDecodeError:
        decoded = [
            line.strip()
            for line in raw_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    if not isinstance(decoded, list) or not decoded:
        raise BundleError("image URL list must be a non-empty JSON array or newline URL list")

    sources: list[dict[str, Any]] = []
    for index, item in enumerate(decoded, start=1):
        if isinstance(item, str):
            image_url = item
            label = f"Image {index}"
            canvas_url = None
            reuse_path = None
        elif isinstance(item, dict):
            image_url = item.get("image_url")
            label = _label(item.get("label"), f"Image {index}")
            canvas_url = item.get("canvas_url")
            reuse_path = item.get("reuse_path")
        else:
            raise BundleError(f"image URL list item {index} must be a URL string or object")
        if not isinstance(image_url, str):
            raise BundleError(f"image URL list item {index} has no image_url")
        if canvas_url is not None and not isinstance(canvas_url, str):
            raise BundleError(f"image URL list item {index} has an invalid canvas_url")
        if reuse_path is not None and not isinstance(reuse_path, str):
            raise BundleError(f"image URL list item {index} has an invalid reuse_path")
        sources.append(
            {
                "index": index,
                "label": label,
                "canvas_url": normalize_provider_url(canvas_url) if canvas_url else None,
                "image_url": normalize_provider_url(image_url),
                "image_request_size": "provider_resource",
                "presentation_version": None,
                "reuse_path": reuse_path,
            }
        )
    return sources


def _verify_image(path: Path, image_format: str) -> None:
    if not path.is_file() or path.stat().st_size <= 0:
        raise BundleError(f"image is empty or missing: {path}")
    with path.open("rb") as stream:
        header = stream.read(16)
    normalized = image_format.casefold()
    if normalized in {"jpg", "jpeg"} and not header.startswith(b"\xff\xd8\xff"):
        raise BundleError(f"downloaded JPEG has an invalid signature: {path}")
    if normalized == "png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise BundleError(f"downloaded PNG has an invalid signature: {path}")
    if normalized == "webp" and not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
        raise BundleError(f"downloaded WebP has an invalid signature: {path}")


def _download_to(
    url: str,
    destination: Path,
    *,
    timeout: float,
    retries: int,
) -> None:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=f".{destination.name}.",
                suffix=".partial",
                dir=destination.parent,
                delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                with urlopen(_request(url), timeout=timeout) as response:
                    shutil.copyfileobj(response, stream, length=1024 * 1024)
            if temp_path.stat().st_size <= 0:
                raise BundleError(f"empty response from {url}")
            os.replace(temp_path, destination)
            temp_path = None
            return
        except HTTPError as exc:
            exc.close()
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
        except (URLError, TimeoutError, OSError, BundleError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(min(2**attempt, 8))
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
    raise BundleError(f"request failed for {url}: {last_error}") from last_error


def _reuse_path(pattern: str, *, repo_root: Path, index: int) -> Path:
    try:
        rendered = pattern.format(index=index)
    except (KeyError, IndexError, ValueError) as exc:
        raise BundleError(f"invalid --reuse-pattern: {exc}") from exc
    candidate = Path(rendered)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _literal_reuse_path(raw_path: str, *, repo_root: Path) -> Path:
    candidate = Path(raw_path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def work_portion_from_args(args: argparse.Namespace) -> dict[str, object] | None:
    supplied = any(
        (
            args.work_portion_label,
            args.work_locator,
            args.work_start_url,
            args.work_end_url,
            args.work_portion_note,
        )
    )
    if not supplied:
        return None
    if not args.work_portion_label:
        raise BundleError("--work-portion-label is required when recording a work portion")
    if not args.work_locator:
        raise BundleError("at least one --work-locator is required when recording a work portion")
    work_portion: dict[str, object] = {
        "label": args.work_portion_label,
        "locators": args.work_locator,
    }
    if args.work_start_url:
        work_portion["start_url"] = validate_url(args.work_start_url)
    if args.work_end_url:
        work_portion["end_url"] = validate_url(args.work_end_url)
    if args.work_portion_note:
        work_portion["notes"] = args.work_portion_note
    return work_portion


def bundle(
    *,
    repo_root: Path,
    work_id: str,
    source_url: str,
    filename: str,
    label: str,
    coverage: str,
    image_size: str | None,
    image_format: str,
    timeout: float,
    retries: int,
    force: bool,
    reuse_pattern: str | None = None,
    image_url_list: Path | None = None,
    work_portion: dict[str, object] | None = None,
    notes: list[str] | None = None,
    workers: int = 1,
) -> dict[str, object]:
    if not SAFE_WORK_ID.fullmatch(work_id):
        raise BundleError(f"unsafe work ID: {work_id!r}")
    source_url = validate_url(source_url)
    filename = validate_filename(filename)
    if image_format not in {"jpg", "jpeg", "png", "webp"}:
        raise BundleError("--image-format must be jpg, jpeg, png, or webp")
    if image_size is not None and not SAFE_IIIF_SIZE.fullmatch(image_size):
        raise BundleError("--image-size contains characters outside an IIIF size segment")
    if image_size is not None and re.fullmatch(r"\d+", image_size):
        raise BundleError(
            "--image-size bare numeric widths are ambiguous; use a width-only "
            "IIIF size such as '1800,'"
        )
    if timeout <= 0 or retries < 0 or not 1 <= workers <= 32:
        raise BundleError(
            "timeout must be positive, retries cannot be negative, and workers must be 1–32"
        )

    relative = Path("source-cache") / work_id / filename
    destination = repo_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        raise BundleError(f"cache destination already exists; pass --force: {relative.as_posix()}")

    source_member: str
    source_bytes: bytes
    if image_url_list is None:
        source_kind = "iiif_presentation_manifest"
        source_member = "manifest.json"
        source_bytes = fetch_bytes(source_url, timeout=timeout, retries=retries)
        try:
            manifest = json.loads(source_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BundleError(f"IIIF manifest is not valid JSON: {exc}") from exc
        if not isinstance(manifest, dict):
            raise BundleError("IIIF manifest root must be an object")
        sources = extract_canvas_sources(
            manifest,
            image_size=image_size,
            image_format=image_format,
        )
    else:
        source_kind = "image_url_inventory"
        source_member = "source-list.json"
        sources = extract_image_url_sources(image_url_list)
        source_bytes = (
            json.dumps(
                [
                    {
                        key: source[key]
                        for key in ("index", "label", "canvas_url", "image_url")
                    }
                    for source in sources
                ],
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")

    staging = destination.parent / f".{filename}.staging"
    images_dir = staging / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    extension = "jpg" if image_format == "jpeg" else image_format

    def cache_one(source: dict[str, Any]) -> dict[str, Any]:
        index = source["index"]
        member_path = f"images/{index:06d}.{extension}"
        staged_image = staging / member_path
        staged_url = staged_image.with_suffix(f"{staged_image.suffix}.source-url")
        staged_image.parent.mkdir(parents=True, exist_ok=True)
        candidates = [
            (source["image_url"], source["image_request_size"]),
        ]
        if source.get("fallback_image_url"):
            candidates.append(
                (
                    source["fallback_image_url"],
                    source["fallback_image_request_size"],
                )
            )
        staged_source_url = (
            staged_url.read_text(encoding="utf-8").strip() if staged_url.is_file() else None
        )
        staged_candidate = next(
            (candidate for candidate in candidates if candidate[0] == staged_source_url),
            None,
        )
        staged_matches = staged_image.exists() and staged_candidate is not None
        actual_url, actual_request_size = staged_candidate or candidates[0]
        if not staged_matches:
            staged_image.unlink(missing_ok=True)
            staged_url.unlink(missing_ok=True)
            if source.get("reuse_path"):
                reusable = _literal_reuse_path(source["reuse_path"], repo_root=repo_root)
                _verify_image(reusable, image_format)
                shutil.copyfile(reusable, staged_image)
            elif reuse_pattern:
                reusable = _reuse_path(reuse_pattern, repo_root=repo_root, index=index)
                _verify_image(reusable, image_format)
                shutil.copyfile(reusable, staged_image)
            else:
                last_error: BundleError | None = None
                for candidate_url, candidate_size in candidates:
                    try:
                        _download_to(
                            candidate_url,
                            staged_image,
                            timeout=timeout,
                            retries=retries,
                        )
                        actual_url = candidate_url
                        actual_request_size = candidate_size
                        break
                    except BundleError as exc:
                        last_error = exc
                else:
                    assert last_error is not None
                    raise last_error
            staged_url.write_text(f"{actual_url}\n", encoding="utf-8")
        _verify_image(staged_image, image_format)
        public_source = {
            key: value
            for key, value in source.items()
            if key
            not in {
                "reuse_path",
                "fallback_image_url",
                "fallback_image_request_size",
            }
        }
        if actual_url != source["image_url"]:
            public_source["requested_image_url"] = source["image_url"]
            public_source["requested_image_request_size"] = source["image_request_size"]
            public_source["image_url"] = actual_url
            public_source["image_request_size"] = actual_request_size
        return {
            **public_source,
            "member_path": member_path,
            "sha256": sha256(staged_image),
            "bytes": staged_image.stat().st_size,
        }

    inventory_items: list[dict[str, Any]] = []
    if workers == 1:
        cached_items = map(cache_one, sources)
    else:
        executor = ThreadPoolExecutor(max_workers=workers)
        cached_items = executor.map(cache_one, sources)
    try:
        for completed, item in enumerate(cached_items, start=1):
            inventory_items.append(item)
            if completed == 1 or completed == len(sources) or completed % 25 == 0:
                print(f"Cached IIIF image {completed}/{len(sources)}", file=sys.stderr)
    finally:
        if workers != 1:
            executor.shutdown(wait=True, cancel_futures=True)

    retrieved_on = date.today().isoformat()
    (staging / source_member).write_bytes(source_bytes)
    inventory = {
        "schema_version": "1.0.0",
        "source_kind": source_kind,
        "source_url": source_url,
        "retrieved_on": retrieved_on,
        "source_file_count": len(inventory_items),
        "image_format": extension,
        "requested_image_size": image_size or "version_default",
        "items": inventory_items,
    }
    if source_kind == "iiif_presentation_manifest":
        inventory["canvas_count"] = len(inventory_items)
    (staging / "inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{filename}.", suffix=".partial", dir=destination.parent, delete=False
        ) as stream:
            temp_path = Path(stream.name)
        with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.write(staging / source_member, source_member)
            archive.write(staging / "inventory.json", "inventory.json")
            for item in inventory_items:
                archive.write(staging / item["member_path"], item["member_path"])
        if temp_path.stat().st_size <= 0:
            raise BundleError("created IIIF bundle is empty")
        os.replace(temp_path, destination)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()
    shutil.rmtree(staging)

    request_profiles = sorted({item["image_request_size"] for item in inventory_items})
    local_notes = list(notes or [])
    if source_kind == "iiif_presentation_manifest":
        local_notes.append(
            f"ZIP contains the provider manifest, an exact-source inventory, and all "
            f"{len(inventory_items)} canvas images listed when retrieved."
        )
    else:
        local_notes.append(
            f"ZIP contains the normalized source URL list, an exact-source inventory, and "
            f"all {len(inventory_items)} images in the verified full-object list."
        )
    local_notes.append(
        "Effective IIIF image request profile(s): "
        f"{', '.join(json.dumps(profile) for profile in request_profiles)}; "
        f"format: {extension}."
    )
    if reuse_pattern or any(source.get("reuse_path") for source in sources):
        local_notes.append(
            "Canvas files were reused from explicit local source paths; the caller is "
            "responsible for having verified that they came from the recorded image requests."
        )
    local_copy: dict[str, object] = {
        "label": label,
        "path": relative.as_posix(),
        "source_url": source_url,
        "sha256": sha256(destination),
        "bytes": destination.stat().st_size,
        "media_type": "application/zip",
        "downloaded_on": retrieved_on,
        "coverage": coverage,
        "retrieval_method": "iiif_bundle",
        "bundle_source_kind": source_kind,
        "source_file_count": len(inventory_items),
        "notes": local_notes,
    }
    if work_portion is not None:
        local_copy["work_portion"] = work_portion
    return local_copy


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("work_id", help="exact corpus work ID")
    result.add_argument(
        "source_url",
        help="exact IIIF Presentation manifest or official full-facsimile source URL",
    )
    result.add_argument("--filename", required=True, help="stable .zip cache filename")
    result.add_argument("--label", help="human-readable bundle label")
    result.add_argument(
        "--coverage",
        choices=("complete", "partial", "metadata_only", "unknown"),
        default="complete",
        help="completeness of the represented source object",
    )
    result.add_argument(
        "--image-size",
        help=(
            "IIIF Image API size segment (for example 1800, for width-only); "
            "defaults to full for v2 or max for v3"
        ),
    )
    result.add_argument(
        "--image-format",
        choices=("jpg", "jpeg", "png", "webp"),
        default="jpg",
    )
    result.add_argument("--timeout", type=float, default=120.0, help="per-request timeout")
    result.add_argument("--retries", type=int, default=3, help="retries after first attempt")
    result.add_argument(
        "--workers",
        type=int,
        default=1,
        help="parallel image requests (1–32); use conservatively for provider services",
    )
    result.add_argument(
        "--reuse-pattern",
        help="optional existing image path pattern containing {index}, e.g. page-{index:03d}.jpg",
    )
    result.add_argument(
        "--image-url-list",
        type=Path,
        help=(
            "JSON/newline inventory of exact image URLs when no Presentation manifest exists; "
            "JSON objects may include label, canvas_url, and reuse_path"
        ),
    )
    result.add_argument("--note", action="append", help="bundle note; may be repeated")
    result.add_argument("--work-portion-label", help="work found within the complete source")
    result.add_argument(
        "--work-locator",
        action="append",
        help="physical or digital locator; repeat for folio and canvas ranges",
    )
    result.add_argument("--work-start-url", help="deep link to the work's first canvas")
    result.add_argument("--work-end-url", help="deep link to the work's final canvas")
    result.add_argument(
        "--work-portion-note",
        action="append",
        help="mapping note; may be repeated",
    )
    result.add_argument("--force", action="store_true", help="replace an existing bundle")
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
        local_copy = bundle(
            repo_root=args.root.resolve(),
            work_id=args.work_id,
            source_url=args.source_url,
            filename=args.filename,
            label=args.label or args.filename,
            coverage=args.coverage,
            image_size=args.image_size,
            image_format=args.image_format,
            timeout=args.timeout,
            retries=args.retries,
            force=args.force,
            reuse_pattern=args.reuse_pattern,
            image_url_list=args.image_url_list,
            work_portion=work_portion_from_args(args),
            notes=args.note,
            workers=args.workers,
        )
    except BundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"local_copies": [local_copy]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
