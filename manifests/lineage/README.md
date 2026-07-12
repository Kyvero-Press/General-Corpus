# Lineage manifests

This directory contains evidence-backed provenance, access, reproduction, and
rights records for individual General Corpus works.

Descriptive title, authorship, date, region, language, genre, form, subject,
and tag data lives in the parallel [`../work-metadata/`](../work-metadata/)
system.

- [`index.json`](index.json) is the discovery index.
- [`works/`](works/) contains one self-contained JSON graph per work.
- [`schemas/`](schemas/) contains the JSON Schema Draft 2020-12 contracts.
- [`../../docs/lineage-manifests.md`](../../docs/lineage-manifests.md) explains
  the model and contribution workflow.

Coverage is intentionally incremental. A missing manifest means “not yet
researched here,” not “no source is known.” Unknown facts and unsuccessful
public-access searches belong in `open_questions`; they must not be replaced
with guesses.

Verified downloadable facsimiles and supporting files are cached locally under
the Git-ignored `source-cache/<work_id>/` directory. Each cached file is linked
from its access record through `local_copies`, including its exact download
URL, relative path, SHA-256, byte count, media type, and download date. These
records remain useful when a clone does not contain the ignored files. For a
manuscript facsimile, download the complete digitized physical codex whenever
it is publicly obtainable and practical, including covers, endleaves, blanks,
and adjacent works exposed by the provider. `work_portion` records the
folios/pages/canvases occupied by this work without mislabeling selected
leaves—or a metadata-only IIIF manifest—as a complete facsimile. Never replace
an obtainable whole-codex object with a work-only excerpt. Every cached
manuscript facsimile marked `coverage=complete` must include `work_portion`.
When the complete codex is available as IIIF canvases, one `iiif_bundle` local
copy holds the provider manifest, all canvas images, and an exact-source
inventory; `source_file_count` reports the number of captured canvas images.
Where no Presentation manifest exists, `bundle_source_kind` distinguishes an
exhaustive provider-image URL inventory from a manifest-driven bundle.

Validate the index, schemas, references, source identifiers, and checksums with:

```bash
python3 scripts/validate-lineage-manifests.py
```
