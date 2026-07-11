# Lineage manifests

This directory contains evidence-backed provenance, access, reproduction, and
rights records for individual General Corpus works.

- [`index.json`](index.json) is the discovery index.
- [`works/`](works/) contains one self-contained JSON graph per work.
- [`schemas/`](schemas/) contains the JSON Schema Draft 2020-12 contracts.
- [`../../docs/lineage-manifests.md`](../../docs/lineage-manifests.md) explains
  the model and contribution workflow.

Coverage is intentionally incremental. A missing manifest means “not yet
researched here,” not “no source is known.” Unknown facts and unsuccessful
public-access searches belong in `open_questions`; they must not be replaced
with guesses.

Validate the index, schemas, references, source identifiers, and checksums with:

```bash
python3 scripts/validate-lineage-manifests.py
```
