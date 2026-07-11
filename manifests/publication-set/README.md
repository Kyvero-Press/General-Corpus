# Viewer publication-set snapshot

`viewer-default.json` is the tracked identity boundary for the default static
viewer release. It records every expected canonical PDF by exact `work_id`,
filename, SHA-256 digest, byte count, and page count. The strict viewer build
rejects missing, extra, renamed, rebuilt, or unreadable PDFs.

This snapshot is not a claim that 297 is a permanent corpus size. Replace it
only after completing the fail-closed corpus refresh procedure in
[`docs/architecture.md`](../../docs/architecture.md#fail-closed-corpus-refresh-contract),
then review and commit the resulting diff:

```bash
python3 scripts/snapshot-corpus-viewer-publications.py \
  --snapshot-date YYYY-MM-DD
cd viewer
npm run build
```

The snapshot identifies publication files, not their canonical XML source
choices. Source mappings and duplicate-stem decisions remain part of the
publication refresh evidence; work-specific scholarly derivation belongs in
the lineage manifests.
