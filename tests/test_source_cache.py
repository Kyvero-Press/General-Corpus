import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "cache-source-download.py"
SPEC = importlib.util.spec_from_file_location("cache_source_download", MODULE_PATH)
cache_source_download = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cache_source_download
assert SPEC.loader is not None
SPEC.loader.exec_module(cache_source_download)


class Headers:
    def get_content_type(self) -> str:
        return "application/pdf"


class Response(io.BytesIO):
    headers = Headers()

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class SourceCacheTests(unittest.TestCase):
    def test_download_writes_gitignored_shape_and_manifest_snippet(self) -> None:
        payload = b"%PDF-1.7\nsource fixture\n%%EOF\n"
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            cache_source_download,
            "urlopen",
            return_value=Response(payload),
        ):
            root = Path(directory)
            result = cache_source_download.download(
                repo_root=root,
                work_id="CME00099",
                raw_url="https://example.test/source.pdf",
                filename="source.pdf",
                media_type=None,
                label="Complete source PDF",
                coverage="complete",
                force=False,
                work_portion={
                    "label": "The target work",
                    "locators": ["folios 10r–20v"],
                    "start_url": "https://example.test/canvas/21",
                },
            )

            cached = root / "source-cache/CME00099/source.pdf"
            self.assertEqual(payload, cached.read_bytes())
            self.assertEqual("source-cache/CME00099/source.pdf", result["path"])
            self.assertEqual("https://example.test/source.pdf", result["source_url"])
            self.assertEqual("application/pdf", result["media_type"])
            self.assertEqual(len(payload), result["bytes"])
            self.assertEqual("Complete source PDF", result["label"])
            self.assertEqual("complete", result["coverage"])
            self.assertEqual(
                {
                    "label": "The target work",
                    "locators": ["folios 10r–20v"],
                    "start_url": "https://example.test/canvas/21",
                },
                result["work_portion"],
            )

    def test_cli_builds_work_portion_with_physical_and_digital_locators(self) -> None:
        args = cache_source_download.parser().parse_args([
            "CME00099",
            "https://example.test/manuscript.pdf",
            "--work-portion-label",
            "The target work",
            "--work-locator",
            "folios 10r–20v",
            "--work-locator",
            "IIIF canvases 21–42",
            "--work-start-url",
            "https://example.test/canvas/21",
            "--work-end-url",
            "https://example.test/canvas/42",
        ])

        self.assertEqual(
            {
                "label": "The target work",
                "locators": ["folios 10r–20v", "IIIF canvases 21–42"],
                "start_url": "https://example.test/canvas/21",
                "end_url": "https://example.test/canvas/42",
            },
            cache_source_download.work_portion_from_args(args),
        )

    def test_download_rejects_html_disguised_as_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            cache_source_download,
            "urlopen",
            return_value=Response(b"<html>login required</html>"),
        ):
            with self.assertRaisesRegex(
                cache_source_download.CacheError,
                "does not have a PDF header",
            ):
                cache_source_download.download(
                    repo_root=Path(directory),
                    work_id="CME00099",
                    raw_url="https://example.test/source.pdf",
                    filename="source.pdf",
                    media_type=None,
                    label="Source PDF",
                    coverage="unknown",
                    force=False,
                )

    def test_unsafe_identifiers_and_filenames_are_rejected(self) -> None:
        with self.assertRaisesRegex(cache_source_download.CacheError, "unsafe work ID"):
            cache_source_download.download(
                repo_root=REPO_ROOT,
                work_id="../escape",
                raw_url="https://example.test/source.pdf",
                filename="source.pdf",
                media_type=None,
                label="Source PDF",
                coverage="unknown",
                force=False,
            )
        with self.assertRaisesRegex(cache_source_download.CacheError, "cache filename"):
            cache_source_download.download(
                repo_root=REPO_ROOT,
                work_id="CME00099",
                raw_url="https://example.test/source.pdf",
                filename="../source.pdf",
                media_type=None,
                label="Source PDF",
                coverage="unknown",
                force=False,
            )


if __name__ == "__main__":
    unittest.main()
