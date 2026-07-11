# Work metadata manifests

This directory contains evidence-backed descriptive catalog metadata for
General Corpus works.

- [`index.json`](index.json) exposes compact discovery fields.
- [`works/`](works/) contains one self-contained JSON record per work.
- [`schemas/`](schemas/) contains the JSON Schema Draft 2020-12 contracts.
- [`../../docs/work-metadata-manifests.md`](../../docs/work-metadata-manifests.md)
  explains the model and contribution workflow.

These records describe intellectual and content units. Manuscript holdings,
edition provenance, digital files, scans, access routes, and copyright belong
in the linked [`../lineage/`](../lineage/) record.

Coverage is intentionally incremental. A missing record means “not yet
cataloged here,” not “metadata unavailable.”

Validate the schemas, index, evidence, XML identifiers, and lineage bindings:

```bash
python3 scripts/validate-work-metadata-manifests.py
```
