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
records remain useful when a clone does not contain the ignored files.

Validate the index, schemas, references, source identifiers, and checksums with:

```bash
python3 scripts/validate-lineage-manifests.py
```
