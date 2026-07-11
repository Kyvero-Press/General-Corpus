import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "cache-iiif-bundle.py"
SPEC = importlib.util.spec_from_file_location("cache_iiif_bundle", MODULE_PATH)
cache_iiif_bundle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cache_iiif_bundle
assert SPEC.loader is not None
SPEC.loader.exec_module(cache_iiif_bundle)


class Response(io.BytesIO):
    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def iiif_v2_manifest() -> dict[str, object]:
    return {
        "@context": "http://iiif.io/api/presentation/2/context.json",
        "@id": "https://example.test/manifest",
        "@type": "sc:Manifest",
        "sequences": [{
            "canvases": [
                {
                    "@id": f"https://example.test/canvas/{index}",
                    "label": f"folio {index}r",
                    "images": [{
                        "resource": {
                            "@id": f"https://example.test/image/{index}/full/full/0/default.jpg",
                            "service": {
                                "@id": f"https://example.test/image/{index}",
                                "profile": "http://iiif.io/api/image/2/level2.json",
                            },
                        }
                    }],
                }
                for index in (1, 2)
            ]
        }],
    }


class IiifBundleCacheTests(unittest.TestCase):
    def test_complete_v2_manifest_becomes_one_auditable_zip(self) -> None:
        manifest_url = "https://example.test/manifest"
        manifest_bytes = json.dumps(iiif_v2_manifest()).encode("utf-8")
        jpeg_one = b"\xff\xd8\xff\xe0first-image"
        jpeg_two = b"\xff\xd8\xff\xe0second-image"
        responses = {
            manifest_url: manifest_bytes,
            "https://example.test/image/1/full/full/0/default.jpg": jpeg_one,
            "https://example.test/image/2/full/full/0/default.jpg": jpeg_two,
        }

        def fake_urlopen(request: object, **_kwargs: object) -> Response:
            url = request.full_url  # type: ignore[attr-defined]
            return Response(responses[url])

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            cache_iiif_bundle,
            "urlopen",
            side_effect=fake_urlopen,
        ):
            root = Path(directory)
            result = cache_iiif_bundle.bundle(
                repo_root=root,
                work_id="TestWork",
                source_url=manifest_url,
                filename="complete-manuscript.zip",
                label="Complete manuscript IIIF bundle",
                coverage="complete",
                image_size=None,
                image_format="jpg",
                timeout=10,
                retries=0,
                force=False,
                work_portion={
                    "label": "Target work",
                    "locators": ["folios 1r–2r", "IIIF canvases 1–2"],
                },
            )

            bundle_path = root / "source-cache/TestWork/complete-manuscript.zip"
            self.assertTrue(bundle_path.is_file())
            self.assertEqual("iiif_bundle", result["retrieval_method"])
            self.assertEqual(
                "iiif_presentation_manifest",
                result["bundle_source_kind"],
            )
            self.assertEqual(2, result["source_file_count"])
            self.assertEqual("application/zip", result["media_type"])
            self.assertEqual("complete", result["coverage"])
            self.assertEqual(manifest_url, result["source_url"])
            self.assertEqual("Target work", result["work_portion"]["label"])

            with zipfile.ZipFile(bundle_path) as archive:
                self.assertEqual(
                    [
                        "manifest.json",
                        "inventory.json",
                        "images/000001.jpg",
                        "images/000002.jpg",
                    ],
                    archive.namelist(),
                )
                self.assertEqual(manifest_bytes, archive.read("manifest.json"))
                self.assertEqual(jpeg_one, archive.read("images/000001.jpg"))
                inventory = json.loads(archive.read("inventory.json"))
            self.assertEqual(2, inventory["canvas_count"])
            self.assertEqual(2, inventory["source_file_count"])
            self.assertEqual(
                "https://example.test/canvas/1",
                inventory["items"][0]["canvas_url"],
            )
            self.assertEqual(
                "https://example.test/image/1/full/full/0/default.jpg",
                inventory["items"][0]["image_url"],
            )
            self.assertEqual("images/000001.jpg", inventory["items"][0]["member_path"])

    def test_inventory_mode_bundles_exact_urls_without_inventing_canvases(self) -> None:
        source_url = "https://example.test/complete-facsimile"
        first_url = "https://example.test/iiif/image-a/full/full/0/default.jpg"
        second_url = "https://example.test/iiif/image-b/full/full/0/default.jpg"
        reused_jpeg = b"\xff\xd8\xff\xe0reused-image"
        downloaded_jpeg = b"\xff\xd8\xff\xe0downloaded-image"

        def fake_urlopen(request: object, **_kwargs: object) -> Response:
            url = request.full_url  # type: ignore[attr-defined]
            self.assertEqual(second_url, url)
            return Response(downloaded_jpeg)

        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            cache_iiif_bundle,
            "urlopen",
            side_effect=fake_urlopen,
        ):
            root = Path(directory)
            reused = root / "already-downloaded.jpg"
            reused.write_bytes(reused_jpeg)
            source_list = root / "images.json"
            source_list.write_text(
                json.dumps([
                    {
                        "label": "folio 1r",
                        "image_url": first_url,
                        "reuse_path": str(reused),
                    },
                    {"label": "folio 1v", "image_url": second_url},
                ]),
                encoding="utf-8",
            )

            result = cache_iiif_bundle.bundle(
                repo_root=root,
                work_id="TestWork",
                source_url=source_url,
                filename="inventory-manuscript.zip",
                label="Complete inventory-driven manuscript bundle",
                coverage="complete",
                image_size=None,
                image_format="jpg",
                timeout=10,
                retries=0,
                force=False,
                image_url_list=source_list,
            )

            self.assertEqual("image_url_inventory", result["bundle_source_kind"])
            self.assertEqual(2, result["source_file_count"])
            bundle_path = root / "source-cache/TestWork/inventory-manuscript.zip"
            with zipfile.ZipFile(bundle_path) as archive:
                self.assertEqual(
                    [
                        "source-list.json",
                        "inventory.json",
                        "images/000001.jpg",
                        "images/000002.jpg",
                    ],
                    archive.namelist(),
                )
                source_items = json.loads(archive.read("source-list.json"))
                inventory = json.loads(archive.read("inventory.json"))
                self.assertEqual(reused_jpeg, archive.read("images/000001.jpg"))
                self.assertEqual(downloaded_jpeg, archive.read("images/000002.jpg"))
            self.assertNotIn("reuse_path", source_items[0])
            self.assertIsNone(source_items[0]["canvas_url"])
            self.assertEqual("image_url_inventory", inventory["source_kind"])
            self.assertEqual(2, inventory["source_file_count"])
            self.assertEqual(first_url, inventory["items"][0]["image_url"])

    def test_v3_uses_max_image_request_by_default(self) -> None:
        manifest = {
            "type": "Manifest",
            "items": [{
                "id": "https://example.test/canvas/1",
                "type": "Canvas",
                "label": {"en": ["Page 1"]},
                "items": [{
                    "type": "AnnotationPage",
                    "items": [{
                        "type": "Annotation",
                        "motivation": "painting",
                        "body": {
                            "id": "https://example.test/image/1/full/max/0/default.jpg",
                            "type": "Image",
                            "service": [{
                                "id": "https://example.test/image/1",
                                "type": "ImageService3",
                                "profile": "level2",
                            }],
                        },
                    }],
                }],
            }],
        }

        sources = cache_iiif_bundle.extract_canvas_sources(manifest)

        self.assertEqual("Page 1", sources[0]["label"])
        self.assertEqual("max", sources[0]["image_request_size"])
        self.assertEqual(
            "https://example.test/image/1/full/max/0/default.jpg",
            sources[0]["image_url"],
        )

    def test_work_portion_requires_label_and_locator(self) -> None:
        args = cache_iiif_bundle.parser().parse_args([
            "TestWork",
            "https://example.test/manifest",
            "--filename",
            "manuscript.zip",
            "--work-portion-label",
            "Target work",
        ])

        with self.assertRaisesRegex(cache_iiif_bundle.BundleError, "work-locator"):
            cache_iiif_bundle.work_portion_from_args(args)


if __name__ == "__main__":
    unittest.main()
