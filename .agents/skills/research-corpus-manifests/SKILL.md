---
name: research-corpus-manifests
description: Research, create, review, or extend General Corpus descriptive work-metadata and source-lineage manifests. Use for manifests/work-metadata or manifests/lineage changes, for tracing a CME XML item through its electronic encoding and scholarly edition to manuscript witnesses, for cataloging title, responsibility, date, region, language, form, genre, subject, or tags, and for recording access and copyright evidence without conflating textual, physical, editorial, and digital layers.
---

# Research Corpus Manifests

Build a defensible pair of manifests for one corpus item: descriptive metadata
for the intellectual/content unit and a lineage graph for its material and
digital sources. Prefer facts read from the work, edition, encoding, and
holding institution over convenient secondary summaries.

Before researching, read:

- [`references/field-guide.md`](references/field-guide.md) for source priority,
  layer modeling, field decisions, and reusable case lessons;
- [`manifests/work-metadata/schemas/work-metadata-manifest.schema.json`](../../../manifests/work-metadata/schemas/work-metadata-manifest.schema.json)
  and [`manifests/lineage/schemas/lineage-manifest.schema.json`](../../../manifests/lineage/schemas/lineage-manifest.schema.json)
  for the current contracts; and
- one nearby manifest pair as a structural example. Use CME00099 for a
  branching, multi-witness example, not as a template for claims about a
  different work.

## Work source-first

1. Locate the exact repository artifact and verify its internal identifier.
2. Read its bibliographic header, source description, availability statement,
   editorial declaration, opening and closing matter, division structure,
   notes, milestones, and language markup.
3. Identify the immediate source edition from its own title page, preface, and
   apparatus when a scan is available.
4. Trace the edition to its explicitly named witness or witnesses. Distinguish
   a base witness, collated witnesses, later comparison editions, and a broad
   manuscript tradition.
5. Verify material and digital facts with the responsible repositories and
   reliable scholarly sources. Open the supporting page; do not cite a search
   result snippet as evidence.
6. Draft a claim ledger before writing JSON: claim, layer/entity, source,
   confidence, scope, and destination field.

Do not begin from a generic biography or modern plot summary and work backward.

## Define the cataloging boundary

State what the metadata record describes before assigning title or author.
Choose among a textual work, translation, compilation, edited selection, or
edition-level content unit. Keep the XML file, electronic encoding, print
edition, physical witness, and abstract work distinct.

Use the cataloged unit's preferred title as the lineage manifest's top-level
`title`; the manifest type already supplies the “source lineage” context.

When a corpus item contains editorial introductions, appendices, or several
source works, represent that structure explicitly. Do not silently make the
whole item inherit a part's author, date, language, place, or form.

## Build the lineage graph

Create separate entities for every evidenced layer, normally:

```text
repository artifact -> U-M/OTA encoding -> immediate print edition
                                           -> manuscript witness(es)
```

Add scans, facsimiles, prior editions, or later comparison editions only when
their relationship is known. Use scoped relations for excerpts, selected
folios, appendices, or eclectic texts. Never turn “consulted” into “derived
from,” or a repository holding location into a work's place of composition.

Record author, translator, compiler, scribe, editor, collator, digitizer, and
encoder as different responsibilities. Model anonymous or plural creators
honestly. Put an attractive but unverified attribution in `open_questions`,
not in `agents`.

## Catalog descriptive metadata

Derive the compact `catalog_summary` from the detailed assertions. Maintain:

- exactly one preferred whole-work title and one whole-work form;
- distinct composition, witness, publication, and encoding dates;
- scoped place assertions that say whether they describe origin, dialect,
  composition, copying, or publication;
- ISO language codes plus the evidence for mixed or embedded languages;
- genre as a literary/documentary category, subject as topical content, and
  tags as controlled discovery terms actually supported by the item; and
- content structure no more granular than the evidence permits.

Use `partial` or `unknown` rather than filling gaps from expectation. Preserve
disagreement among authorities in assertions and open questions.

## Treat rights and access as layer-specific

Record the source text, manuscript object, manuscript images, print edition,
electronic encoding, and repository artifact separately. Public access does
not prove public-domain status, and an old manuscript does not establish terms
for modern photography or transcription. Cite the institution's item-specific
rights statement where available, date availability checks, and avoid legal
conclusions broader than the source supports.

## Make evidence auditable

For local artifacts, record the repository-relative path, SHA-256, and Git blob
hash where the schema permits. For web evidence, use the most direct stable URL,
an access date, a concise summary of what it proves, and alternates only when
useful. One source may support several facts, but every consequential claim
must resolve to evidence that actually says it.

Before finishing, inspect all IDs and references mechanically and read the
human-facing summaries again for overstatement.

## Integrate and validate

Add both files, then derive their index entries from the completed manifests;
do not hand-invent compact values that disagree with detailed records.

Run:

```bash
python3 scripts/validate-lineage-manifests.py
python3 scripts/validate-work-metadata-manifests.py
python3 -m unittest tests.test_lineage_manifests tests.test_work_metadata_manifests
python3 scripts/build-corpus-viewer-catalog.py --output-root build/corpus-viewer/public
(cd viewer && npm test && npm run typecheck)
```

Remote URLs are not covered by offline validation. Re-open key institutional
and edition links during substantive review.

## Improve this skill from new cases

After completing a newly researched work, compare the difficulty against the
patterns in `references/field-guide.md`. Add a concise case lesson only when it
changes a future research or modeling decision. Generalize the lesson; retain
the work ID as an example and cite the manifest paths. Do not add a changelog or
duplicate facts already recorded in manifests.
