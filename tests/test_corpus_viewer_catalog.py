import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "build-corpus-viewer-catalog.py"
SPEC = importlib.util.spec_from_file_location("build_corpus_viewer_catalog", MODULE_PATH)
build_corpus_viewer_catalog = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_corpus_viewer_catalog
assert SPEC.loader is not None
SPEC.loader.exec_module(build_corpus_viewer_catalog)


class CatalogFixture:
    def __init__(self, root: Path, work_id: str = "CME00099") -> None:
        self.root = root
        self.work_id = work_id
        self.pdf_root = root / "dist"
        self.pdf_root.mkdir(parents=True)
        self.metadata_path = (
            root / "manifests" / "work-metadata" / "works" / f"{work_id}.json"
        )
        self.lineage_path = root / "manifests" / "lineage" / "works" / f"{work_id}.json"
        self.metadata = self._metadata()
        self.lineage = self._lineage()
        self.write_manifests()

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def _metadata(self) -> dict[str, object]:
        return {
            "id": f"metadata:{self.work_id}",
            "work_id": self.work_id,
            "record_status": "reviewed",
            "last_reviewed": "2026-07-11",
            "catalog_summary": {
                "title": "A preferred title",
                "author": "Anonymous",
                "editor": "A. Editor",
                "date": "Attested 1400–1450; published 1897",
                "region": "Norfolk",
                "form": "mixed",
            },
            "titles": [
                {
                    "type": "translated",
                    "language": "eng",
                    "value": "An English title",
                    "scope": {"kind": "whole"},
                }
            ],
            "agents": [],
            "responsibilities": [],
            "date_statements": [
                {
                    "type": "first_known_attestation",
                    "normalized": {"not_before": 1400, "not_after": 1450},
                },
                {
                    "type": "first_publication",
                    "normalized": {"not_before": 1897, "not_after": 1897},
                },
            ],
            "places": [{"id": "place:norfolk", "label": "Norfolk"}],
            "place_statements": [
                {"place_id": "place:norfolk", "type": "dialect_region"}
            ],
            "language_statements": [
                {"code": "enm", "label": "Middle English"}
            ],
            "form_statements": [],
            "genre_statements": [
                {"term": "medical-recipe", "label": "Medical recipe"}
            ],
            "subject_statements": [{"term": "medicine", "label": "Medicine"}],
            "tags": ["medical"],
            "summaries": [
                {
                    "type": "abstract",
                    "scope": {"kind": "whole"},
                    "value": "A concise work summary.",
                }
            ],
            "lineage": {
                "manifest_id": f"lineage:{self.work_id}",
                "manifest_path": f"manifests/lineage/works/{self.work_id}.json",
            },
        }

    def _lineage(self) -> dict[str, object]:
        return {
            "id": f"lineage:{self.work_id}",
            "work_id": self.work_id,
            "record_status": "reviewed",
            "last_reviewed": "2026-07-11",
            "summary": "Repository XML derives from a public scholarly edition.",
            "entities": [
                {
                    "id": "edition:test",
                    "type": "scholarly_edition",
                    "label": "Test source edition",
                }
            ],
            "agents": [
                {"id": "agent:archive", "type": "organization", "name": "Archive"}
            ],
            "relations": [],
            "access": [
                {
                    "id": "access:test-scan",
                    "entity": "edition:test",
                    "provider_id": "agent:archive",
                    "resource_kind": "page_images",
                    "status": "publicly_available",
                    "access_method": "Public scan",
                    "url": "https://example.test/scan",
                    "alternate_urls": ["https://example.test/scan.pdf"],
                    "cost": "free",
                    "format": "PDF",
                    "last_checked": "2026-07-11",
                }
            ],
            "rights": [
                {
                    "id": "rights:test-edition",
                    "entity": "edition:test",
                    "component": "Underlying edition",
                    "jurisdiction": "United States",
                    "copyright_status": "public_domain",
                },
                {
                    "id": "rights:test-scan",
                    "entity": "edition:test",
                    "access_id": "access:test-scan",
                    "component": "Digital surrogate",
                    "jurisdiction": "Provider statement",
                    "copyright_status": "no_known_copyright",
                },
            ],
            "open_questions": [],
            "review_notes": [],
        }

    def write_manifests(self) -> None:
        self._write_json(self.metadata_path, self.metadata)
        self._write_json(self.lineage_path, self.lineage)
        self._write_json(
            self.root / "manifests" / "work-metadata" / "index.json",
            {
                "coverage": {"notes": "Fixture coverage is incremental."},
                "items": [
                    {
                        "work_id": self.work_id,
                        "manifest": f"works/{self.work_id}.json",
                    }
                ],
            },
        )
        self._write_json(
            self.root / "manifests" / "lineage" / "index.json",
            {
                "coverage": {"notes": "Fixture lineage coverage is incremental."},
                "items": [
                    {
                        "work_id": self.work_id,
                        "manifest": f"works/{self.work_id}.json",
                    }
                ],
            },
        )

    def add_pdf(self, stem: str | None = None, payload: bytes | None = None) -> Path:
        path = self.pdf_root / f"{stem or self.work_id}.pdf"
        path.write_bytes(payload or b"%PDF-1.7\nfixture publication\n%%EOF\n")
        return path

    def add_source_copy(self, payload: bytes | None = None) -> Path:
        content = payload or b"%PDF-1.7\nfixture source\n%%EOF\n"
        relative = Path("source-cache") / self.work_id / "test-source.pdf"
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        access = self.lineage["access"][0]
        assert isinstance(access, dict)
        source_url = "https://example.test/scan.pdf"
        access["local_copies"] = [{
            "label": "Complete test source PDF",
            "path": relative.as_posix(),
            "source_url": source_url,
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "media_type": "application/pdf",
            "downloaded_on": "2026-07-11",
            "coverage": "complete",
            "work_portion": {
                "label": "Test work",
                "locators": ["folios 10r–20v", "IIIF canvases 21–42"],
                "start_url": "https://example.test/canvas/21",
                "end_url": "https://example.test/canvas/42",
                "notes": ["The cached file contains the complete manuscript."],
            },
        }]
        self.write_manifests()
        return path

    def write_publication_inventory(self, pdf: Path, *, digest: str | None = None) -> Path:
        path = self.root / "manifests" / "publication-set" / "viewer-default.json"
        self._write_json(
            path,
            {
                "$schema": "schemas/publication-set.schema.json",
                "schema_version": "1.0.0",
                "snapshot_date": "2026-07-11",
                "description": "Fixture publication snapshot.",
                "item_count": 1,
                "items": [
                    {
                        "work_id": self.work_id,
                        "filename": f"{self.work_id}.pdf",
                        "sha256": digest or hashlib.sha256(pdf.read_bytes()).hexdigest(),
                        "bytes": pdf.stat().st_size,
                        "pages": 28,
                    }
                ],
            },
        )
        return path


def fake_pdfinfo() -> mock._patch:
    completed = subprocess.CompletedProcess(
        args=["pdfinfo", "fixture.pdf"],
        returncode=0,
        stdout="Title: Embedded title\nAuthor: Embedded author\nPages: 28\nPage size: 360 x 576 pts\n",
        stderr="",
    )
    return mock.patch.object(
        build_corpus_viewer_catalog.subprocess,
        "run",
        return_value=completed,
    )


class CorpusViewerCatalogTests(unittest.TestCase):
    def test_pages_cache_policy_is_explicit_and_propagated(self) -> None:
        args = build_corpus_viewer_catalog._parser().parse_args(
            ["--allow-missing-source-cache"]
        )
        self.assertTrue(args.allow_missing_source_cache)

        package = json.loads((REPO_ROOT / "viewer/package.json").read_text(encoding="utf-8"))
        self.assertIn("--allow-missing-source-cache", package["scripts"]["catalog:pages"])
        self.assertNotIn("--allow-missing-source-cache", package["scripts"]["catalog"])
        self.assertNotIn("--allow-missing-source-cache", package["scripts"]["build"])

        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CatalogFixture(Path(temp_dir))
            with mock.patch.object(
                build_corpus_viewer_catalog,
                "validate_manifests",
            ) as validate:
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "viewer",
                    include_pdf_only=False,
                    allow_missing_source_cache=True,
                )
            validate.assert_called_once_with(
                fixture.root.resolve(),
                allow_missing_source_cache=True,
            )

    def test_exact_work_id_joins_metadata_lineage_and_canonical_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            pdf = fixture.add_pdf()
            output = fixture.root / "build" / "viewer"

            catalog = build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                validate=False,
            )

            self.assertEqual(1, catalog["counts"]["works"])
            card = catalog["works"][0]
            self.assertEqual("CME00099", card["workId"])
            self.assertEqual("available", card["publication"]["status"])
            self.assertEqual(28, card["publication"]["pages"])
            self.assertEqual(
                hashlib.sha256(pdf.read_bytes()).hexdigest(),
                card["publication"]["sha256"],
            )
            self.assertIsNone(card["publication"]["path"])

    def test_metadata_and_lineage_work_ids_must_match_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CatalogFixture(Path(temp_dir))
            fixture.lineage["work_id"] = "CME00100"
            fixture.write_manifests()

            with self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "lineage work_id mismatch for CME00099",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "viewer",
                    include_pdf_only=False,
                    validate=False,
                )

    def test_variant_pdf_does_not_satisfy_canonical_work_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            fixture.add_pdf("CME00099-oracle-iter05")

            catalog = build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=fixture.root / "build" / "viewer",
                include_pdf_only=False,
                validate=False,
            )

            self.assertEqual("unavailable", catalog["works"][0]["publication"]["status"])
            with self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "cataloged works missing canonical PDFs: CME00099",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "strict",
                    include_pdf_only=False,
                    require_pdfs=True,
                    validate=False,
                )

    def test_existing_plus_identifier_is_a_safe_canonical_pdf_stem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            root = Path(temp_dir)
            fixture = CatalogFixture(root)
            fixture.add_pdf("Vices+V1")

            catalog = build_corpus_viewer_catalog.build_catalog(
                root,
                pdf_root=fixture.pdf_root,
                output_root=root / "build" / "viewer",
                include_pdf_only=True,
                validate=False,
            )

            by_id = {card["workId"]: card for card in catalog["works"]}
            self.assertIn("Vices+V1", by_id)
            self.assertEqual("pending", by_id["Vices+V1"]["metadataStatus"])
            self.assertEqual(
                "catalog/works/Vices+V1.json",
                by_id["Vices+V1"]["detailPath"],
            )
            self.assertTrue(build_corpus_viewer_catalog.SAFE_WORK_ID.fullmatch("Vices+V1"))
            self.assertFalse(build_corpus_viewer_catalog.SAFE_WORK_ID.fullmatch("../Vices+V1"))
            self.assertFalse(build_corpus_viewer_catalog.SAFE_WORK_ID.fullmatch("Vices/V1"))

    def test_source_links_rights_and_raw_manifests_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CatalogFixture(Path(temp_dir))
            output = fixture.root / "build" / "viewer"

            build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                validate=False,
            )

            detail = json.loads(
                (output / "catalog" / "works" / "CME00099.json").read_text(
                    encoding="utf-8"
                )
            )
            source = detail["lineage"]["sourceLinks"][0]
            self.assertEqual("Test source edition", source["entityLabel"])
            self.assertEqual("Archive", source["provider"])
            self.assertEqual("https://example.test/scan", source["url"])
            self.assertEqual(["rights:test-scan"], [item["id"] for item in source["rights"]])
            self.assertEqual(
                {"rights:test-edition", "rights:test-scan"},
                {item["id"] for item in detail["lineage"]["entities"][0]["rights"]},
            )
            self.assertEqual(
                fixture.metadata_path.read_bytes(),
                (output / "catalog" / "manifests" / "work-metadata" / "CME00099.json").read_bytes(),
            )
            self.assertEqual(
                fixture.lineage_path.read_bytes(),
                (output / "catalog" / "manifests" / "lineage" / "CME00099.json").read_bytes(),
            )

    def test_source_links_report_verified_local_copy_and_exact_download(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CatalogFixture(Path(temp_dir))
            cached = fixture.add_source_copy()
            output = fixture.root / "build" / "viewer"

            build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                validate=False,
            )

            detail = json.loads(
                (output / "catalog" / "works" / "CME00099.json").read_text(
                    encoding="utf-8"
                )
            )
            local_copy = detail["lineage"]["sourceLinks"][0]["localCopies"][0]
            self.assertTrue(local_copy["available"])
            self.assertEqual(
                "source-cache/CME00099/test-source.pdf",
                local_copy["path"],
            )
            self.assertEqual("https://example.test/scan.pdf", local_copy["sourceUrl"])
            self.assertEqual(hashlib.sha256(cached.read_bytes()).hexdigest(), local_copy["sha256"])
            self.assertEqual("direct_download", local_copy["retrievalMethod"])
            self.assertIsNone(local_copy["sourceFileCount"])
            self.assertIsNone(local_copy["bundleSourceKind"])
            self.assertEqual(
                {
                    "label": "Test work",
                    "locators": ["folios 10r–20v", "IIIF canvases 21–42"],
                    "startUrl": "https://example.test/canvas/21",
                    "endUrl": "https://example.test/canvas/42",
                    "notes": ["The cached file contains the complete manuscript."],
                },
                local_copy["workPortion"],
            )

            cached.unlink()
            build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                validate=False,
            )
            detail = json.loads(
                (output / "catalog" / "works" / "CME00099.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(
                detail["lineage"]["sourceLinks"][0]["localCopies"][0]["available"]
            )

    def test_source_cache_checksum_mismatch_fails_catalog_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CatalogFixture(Path(temp_dir))
            cached = fixture.add_source_copy()
            cached.write_bytes(b"%PDF-1.7\nchanged source\n%%EOF\n")

            with self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "local_copy (byte count|checksum) mismatch",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "viewer",
                    include_pdf_only=False,
                    validate=False,
                )

    def test_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            fixture.add_pdf()
            first = fixture.root / "build" / "first"
            second = fixture.root / "build" / "second"

            for output in (first, second):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=output,
                    include_pdf_only=False,
                    validate=False,
                )

            first_files = {
                path.relative_to(first): path.read_bytes()
                for path in first.rglob("*")
                if path.is_file()
            }
            second_files = {
                path.relative_to(second): path.read_bytes()
                for path in second.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first_files, second_files)

    def test_pdf_copying_is_explicit_and_removes_stale_downloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            pdf = fixture.add_pdf()
            output = fixture.root / "build" / "viewer"

            copied_catalog = build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                copy_pdfs=True,
                validate=False,
            )
            copied = output / "publication-pdfs" / "CME00099.pdf"
            self.assertEqual(pdf.read_bytes(), copied.read_bytes())
            self.assertEqual(
                "publication-pdfs/CME00099.pdf",
                copied_catalog["works"][0]["publication"]["path"],
            )

            uncopied_catalog = build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                copy_pdfs=False,
                validate=False,
            )
            self.assertFalse((output / "publication-pdfs").exists())
            self.assertIsNone(uncopied_catalog["works"][0]["publication"]["path"])

    def test_external_pdf_url_mode_does_not_copy_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir), work_id="Vices+V1")
            fixture.add_pdf()
            output = fixture.root / "build" / "viewer"

            catalog = build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                copy_pdfs=True,
                external_pdf_base_url="https://downloads.example.test/books/",
                validate=False,
            )

            publication = catalog["works"][0]["publication"]
            self.assertIsNone(publication["path"])
            self.assertEqual(
                "https://downloads.example.test/books/Vices+V1.pdf",
                publication["externalUrl"],
            )
            self.assertFalse((output / "publication-pdfs").exists())

    def test_external_pdf_base_url_rejects_unsafe_or_ambiguous_urls(self) -> None:
        invalid = (
            "javascript:alert(1)",
            "http://downloads.example.test/books",
            "https://user:secret@downloads.example.test/books",
            "https://downloads.example.test/books?edition=latest",
            "https://downloads.example.test/books#files",
            "https://downloads.example.test/books%ZZ",
            " https://downloads.example.test/books",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(
                build_corpus_viewer_catalog.CatalogError
            ):
                build_corpus_viewer_catalog.validate_external_pdf_base_url(value)

    def test_release_copy_requires_pdfinfo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CatalogFixture(Path(temp_dir))
            fixture.add_pdf()
            with mock.patch.object(
                build_corpus_viewer_catalog.subprocess,
                "run",
                side_effect=FileNotFoundError,
            ), self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "pdfinfo is required",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "viewer",
                    include_pdf_only=False,
                    copy_pdfs=True,
                    validate=False,
                )

    def test_failed_pdf_staging_preserves_previous_catalog_and_downloads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            pdf = fixture.add_pdf()
            output = fixture.root / "build" / "viewer"
            build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                copy_pdfs=True,
                validate=False,
            )
            prior_catalog = (output / "catalog" / "index.json").read_bytes()
            prior_pdf = (output / "publication-pdfs" / "CME00099.pdf").read_bytes()
            pdf.write_bytes(b"%PDF-1.7\nchanged fixture publication\n%%EOF\n")

            original_copyfile = build_corpus_viewer_catalog.shutil.copyfile

            def fail_pdf_copy(source: object, destination: object) -> object:
                if Path(source).suffix.casefold() == ".pdf":
                    raise OSError("simulated full disk")
                return original_copyfile(source, destination)

            with mock.patch.object(
                build_corpus_viewer_catalog.shutil,
                "copyfile",
                side_effect=fail_pdf_copy,
            ), self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "could not stage publication PDF",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=output,
                    include_pdf_only=False,
                    copy_pdfs=True,
                    validate=False,
                )

            self.assertEqual(prior_catalog, (output / "catalog" / "index.json").read_bytes())
            self.assertEqual(
                prior_pdf,
                (output / "publication-pdfs" / "CME00099.pdf").read_bytes(),
            )

    def test_case_insensitive_pdf_id_collisions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            fixture.add_pdf("CaseWork")
            fixture.add_pdf("casework")
            with self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "case-insensitive PDF work_id collision",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "viewer",
                    include_pdf_only=True,
                    validate=False,
                )

    def test_case_insensitive_collision_across_manifest_and_pdf_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            fixture.add_pdf("cme00099")
            with self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "case-insensitive work_id collision across catalog sources",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "viewer",
                    include_pdf_only=True,
                    validate=False,
                )

    def test_pdf_replacement_during_strict_inspection_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CatalogFixture(Path(temp_dir))
            pdf = fixture.add_pdf()

            def replace_during_pdfinfo(*_args: object, **_kwargs: object) -> object:
                pdf.write_bytes(b"%PDF-1.7\nreplacement bytes\n%%EOF\n")
                return subprocess.CompletedProcess(
                    args=["pdfinfo", str(pdf)],
                    returncode=0,
                    stdout="Title: Old title\nAuthor: Old author\nPages: 28\nPage size: 360 x 576 pts\n",
                    stderr="",
                )

            with mock.patch.object(
                build_corpus_viewer_catalog.subprocess,
                "run",
                side_effect=replace_during_pdfinfo,
            ), self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "PDF changed while it was being inspected",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "viewer",
                    include_pdf_only=False,
                    require_pdfs=True,
                    validate=False,
                )

    def test_publication_inventory_requires_exact_set_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            pdf = fixture.add_pdf()
            inventory = fixture.write_publication_inventory(pdf)

            catalog = build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=fixture.root / "build" / "valid",
                include_pdf_only=True,
                publication_inventory=inventory,
                validate=False,
            )
            self.assertEqual(1, catalog["counts"]["works"])
            self.assertEqual(
                {
                    "snapshotDate": "2026-07-11",
                    "itemCount": 1,
                    "manifestPath": "catalog/manifests/publication-set/viewer-default.json",
                },
                catalog["publicationInventory"],
            )
            self.assertEqual(
                inventory.read_bytes(),
                (
                    fixture.root
                    / "build"
                    / "valid"
                    / "catalog"
                    / "manifests"
                    / "publication-set"
                    / "viewer-default.json"
                ).read_bytes(),
            )

            fixture.add_pdf("Unexpected")
            with self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "unexpected PDFs: Unexpected",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "extra",
                    include_pdf_only=True,
                    publication_inventory=inventory,
                    validate=False,
                )

            (fixture.pdf_root / "Unexpected.pdf").unlink()
            fixture.write_publication_inventory(pdf, digest="0" * 64)
            with self.assertRaisesRegex(
                build_corpus_viewer_catalog.CatalogError,
                "CME00099 sha256 differs",
            ):
                build_corpus_viewer_catalog.build_catalog(
                    fixture.root,
                    pdf_root=fixture.pdf_root,
                    output_root=fixture.root / "build" / "hash",
                    include_pdf_only=True,
                    publication_inventory=inventory,
                    validate=False,
                )

    def test_repeated_scoped_facets_count_each_work_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = CatalogFixture(Path(temp_dir))
            fixture.metadata["genre_statements"].append(
                {"term": "medical-recipe", "label": "Medical recipe"}
            )
            fixture.metadata["tags"].append("medical")
            fixture.metadata["place_statements"].append(
                {"place_id": "place:norfolk", "type": "dialect_region"}
            )
            fixture.write_manifests()

            catalog = build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=fixture.root / "build" / "viewer",
                include_pdf_only=False,
                validate=False,
            )

            self.assertEqual(1, catalog["facets"]["genres"][0]["count"])
            self.assertEqual(1, catalog["facets"]["tags"][0]["count"])
            self.assertEqual(1, catalog["facets"]["regions"][0]["count"])

    def test_lineage_only_work_keeps_known_sources_while_metadata_is_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir, fake_pdfinfo():
            fixture = CatalogFixture(Path(temp_dir))
            fixture.lineage["primary_subject"] = "artifact:general-corpus:CME00099"
            entities = fixture.lineage["entities"]
            assert isinstance(entities, list)
            entities.append(
                {
                    "id": "artifact:general-corpus:CME00099",
                    "type": "repository_artifact",
                    "label": "General Corpus source XML",
                }
            )
            fixture.write_manifests()
            fixture.add_pdf()
            self._write_empty_metadata_index(fixture.root)
            output = fixture.root / "build" / "viewer"

            catalog = build_corpus_viewer_catalog.build_catalog(
                fixture.root,
                pdf_root=fixture.pdf_root,
                output_root=output,
                include_pdf_only=False,
                validate=False,
            )

            card = catalog["works"][0]
            self.assertEqual("pending", card["metadataStatus"])
            self.assertEqual("available", card["lineageStatus"])
            detail = json.loads(
                (output / "catalog" / "works" / "CME00099.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertIsNone(detail["metadata"])
            self.assertEqual("lineage:CME00099", detail["lineage"]["manifestId"])
            self.assertEqual(
                "artifact:general-corpus:CME00099",
                detail["lineage"]["primarySubjectId"],
            )
            self.assertIsNotNone(detail["lineageManifestPath"])

    @staticmethod
    def _write_empty_metadata_index(root: Path) -> None:
        CatalogFixture._write_json(
            root / "manifests" / "work-metadata" / "index.json",
            {
                "coverage": {"notes": "No fixture metadata records."},
                "items": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
