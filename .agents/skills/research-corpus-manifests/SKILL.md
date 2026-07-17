---
name: research-corpus-manifests
description: Research, create, review, or integrate General Corpus descriptive work-metadata and source-lineage manifests. Use for manifests/work-metadata or manifests/lineage changes, tracing a corpus XML item through electronic encodings and scholarly editions to witnesses, cataloging title, responsibility, date, region, language, form, genre, subjects, and tags, or recording access and copyright evidence without conflating textual, physical, editorial, and digital layers.
---

# Research Corpus Manifests

Produce one defensible manifest pair for one corpus work. Ground claims in the
repository source, the immediate edition, responsible repositories, and
reliable scholarship. Treat uncertainty as data.

## Load guidance progressively

Do not load every reference at the start.

1. Before browsing, read
   [`references/source-research.md`](references/source-research.md).
2. After identifying the cataloging boundary, read
   [`references/metadata-modeling.md`](references/metadata-modeling.md) before
   drafting work metadata.
3. Before drawing derivation edges, read
   [`references/lineage-modeling.md`](references/lineage-modeling.md).
4. Before recording availability or reuse, read
   [`references/rights-evidence.md`](references/rights-evidence.md).
5. Read only the case reference matching a problem encountered:
   - composite works, parts, shared codices, or parallel witnesses:
     [`references/cases-boundaries.md`](references/cases-boundaries.md);
   - reissues, eclectic editions, contributor roles, or later transcripts:
     [`references/cases-editions.md`](references/cases-editions.md);
   - XML identifiers, OCR, typography, counts, or competing digital objects:
     [`references/cases-digital.md`](references/cases-digital.md);
   - provider conflicts, restricted downloads, facsimiles, or image terms:
     [`references/cases-rights.md`](references/cases-rights.md).
6. Read [`references/integration.md`](references/integration.md) only when
   integrating indexes, updating this skill, committing, or pushing.

Inspect schema definitions with targeted `jq` or `rg` queries as fields are
needed; do not load both complete schemas merely for orientation.

## Research one work

1. Locate the exact XML and verify its internal identifier, checksum, Git blob,
   and CME submodule commit.
2. Read the header, source description, availability and editorial statements,
   opening and closing matter, divisions, milestones, notes, and language
   markup.
3. Define the intellectual unit being cataloged. Keep it distinct from its XML
   artifact, encoding, edition, witness, and reproductions.
4. Inspect the immediate edition's title page, preface, and apparatus whenever
   a scan is available. Determine its actual editor, translator, compiler, base
   text, witnesses, omissions, and interventions.
5. Verify witness, bibliographic, access, and rights facts at the exact item
   level with the responsible institution. Supplement interpretation with
   reliable scholarship. Never cite a search-result snippet as evidence.
6. Cache every verified public file deliverable used as a facsimile or
   supporting source under `source-cache/WORK_ID/` with
   `scripts/cache-source-download.py`, or use `scripts/cache-iiif-bundle.py`
   when a complete source is exposed as IIIF canvases rather than one file.
   Before downloading a large object, follow the identifier-first cache search
   in `references/source-research.md`; exact URL matching alone is not enough.
   If a verified complete bundle already exists at a practical resolution,
   create a true hard link under the new work's cache directory and recheck its
   identity, inode, inventory, checksum, and ZIP; never use a symlink or
   redownload identical bytes.
   Classify every cached object explicitly after inspection: set
   `target_work_presence=present` and supply a reproducible `work_portion`
   when it contains the cataloged text or image representation; set
   `target_work_presence=absent` and omit `work_portion` when it does not.
   Do not leave presence implicit merely because schema validation accepts a
   locator. For manuscript facsimiles, download the complete physical codex
   whenever it is publicly obtainable and practical, then record this work's
   exact folio/page/canvas range in `work_portion` for every complete cached
   manuscript facsimile that contains it. Do not turn zero overlap into an
   invented locator. Never substitute a work-only
   excerpt when a complete source is obtainable; if only selected leaves are
   available, mark them `coverage=partial` and preserve the negative
   whole-object finding. Record each direct
   file or IIIF bundle in the relevant access record's `local_copies`; keep
   the landing page and exact file, Presentation-manifest, or complete-
   facsimile source URL. An inventory-driven bundle retains every exact image
   request internally.
7. Draft a claim ledger: claim, entity/layer, scope, source, confidence, and
   destination field.
8. Create both files:
   - `manifests/work-metadata/works/WORK_ID.json`
   - `manifests/lineage/works/WORK_ID.json`
9. Record unresolved material questions explicitly. Use `partial`, `unknown`,
   or qualified assertions instead of filling gaps from expectation.

## Keep the layers honest

Use separate entities and scoped relations for the usual chain:

```text
repository artifact -> electronic encoding -> immediate edition
                                              -> witness(es)
```

Add prior editions, scans, facsimiles, translations, or later comparison
sources only when evidenced. Do not turn “consulted,” “distributed through,”
or “held by” into a derivation claim. Do not transfer a witness's date,
dialect, location, or image terms to the abstract work.

Maintain exactly one preferred whole-work title and one whole-work discovery
form. Keep composition, event, witness, edition, encoding, and review dates
distinct. Separate author, translator, compiler, scribe, editor, collator,
encoder, and digitizer responsibilities.

## Researcher handoff

When working as a one-book subagent in an isolated worktree:

- edit only the two work manifest files unless explicitly assigned otherwise;
- do not edit indexes, shared schemas, validators, documentation, or the skill;
- place downloaded research files only in the ignored
  `source-cache/WORK_ID/` directory and never stage them;
- reject duplicate JSON object keys before ordinary schema validation, because
  common parsers silently keep the last duplicate value:

  ```bash
  python3 .agents/skills/research-corpus-manifests/scripts/check-json-duplicate-keys.py \
    manifests/work-metadata/works/WORK_ID.json \
    manifests/lineage/works/WORK_ID.json
  ```

- validate JSON and the pair as far as the worktree permits;
- run `python3 scripts/validate-manifest-pair.py WORK_ID`;
- send a detailed PRECOMMIT report and wait for exact-file authorization before
  staging or committing the two manifest files on the assigned branch; and
- report sources used, validation results, unresolved questions, and at most
  three genuinely reusable skill lessons.

## Improve without bloating

After each work, add guidance only when the case changes a future decision.
Put the rule in the smallest matching reference, merge it with an existing
rule when possible, and keep book-specific bibliography in manifests. Do not
add a per-work changelog.

The integrator follows [`references/integration.md`](references/integration.md).
Its changed-scope gate invokes the skill validator whenever skill files change.
While iterating on the skill alone, validate it directly with:

```bash
python3 /home/tay/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .agents/skills/research-corpus-manifests
```
