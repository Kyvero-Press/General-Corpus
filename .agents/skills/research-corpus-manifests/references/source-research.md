# Source research

Read this reference before web research. Build outward from the exact corpus
artifact rather than backward from a generic biography or plot summary.

## Assemble the local packet

Collect:

- work ID, repository-relative XML path, and internal XML identifiers;
- SHA-256, Git blob, and pinned CME submodule commit;
- title, contributor, publication, source, availability, language, class, and
  editorial statements from the header;
- opening and closing matter, colophons, divisions, page/folio milestones,
  notes, and declared omissions or transformations; and
- reproducible structural counts useful for describing this encoding.

Useful checks:

```bash
python3 scripts/inspect-corpus-source.py WORK_ID
rg --files CME/source | rg '/WORK_ID\.xml$'
rg -n '<TITLE|<AUTHOR|<EDITOR|<SOURCEDESC|<AVAILABILITY|<EDITORIALDECL|<LANGUAGE|<CLASSCODE' SOURCE.xml
sha256sum SOURCE.xml
git hash-object --no-filters SOURCE.xml
git -C CME rev-parse HEAD
```

The inspection script emits a bounded factual packet and does not replace
reading the relevant source passages or edition pages.

Many files are minified. Reshape diagnostic output and use XML element paths,
IDs, milestones, page numbers, or folios as evidence locators instead of an
unstable source line number.

## Define the cataloging boundary

State what the metadata record describes: an abstract work, translation,
version, compilation, edited selection, or edition-level content unit. Ask for
every proposed fact:

1. Which object or intellectual unit does this describe?
2. Does the cited source directly support that scope?

Keep these layers distinct when present:

| Layer | Typical facts |
| --- | --- |
| Work | creator, title, composition, genre, subject |
| Version/translation | translator, source work, adaptation, form |
| Compilation/selection | compiler/editor, chosen parts, organizing title |
| Witness | shelfmark, date, origin, scribe, folios, holding |
| Edition | editor, publication, base/collated witnesses, apparatus |
| Reproduction | scan/facsimile extent, format, provider, terms |
| Encoding | institution, date, source edition, transformations |
| Repository artifact | path, checksums, pinned local derivation |

A witness can attest a text without fixing the work's composition date or
place. An edition's publication place does not locate the medieval work. An
encoding header can name an edition without proving every claim in it.

## Follow source priority

Prefer, in order:

1. repository XML and the immediate edition's title page, preface, colophon,
   apparatus, or facsimile;
2. the holding institution's item/component catalog and digital surrogate;
3. the digital collection's item record, documentation, and rights statement;
4. a current scholarly edition/project, Middle English Compendium record, or
   peer-reviewed specialist source;
5. national- or research-library bibliographic records; and
6. general references only as discovery leads.

Use lower tiers to supplement higher ones, not silently override them. Do not
use unsourced retail copy, scraped genealogy pages, AI summaries, or search
snippets as final evidence. When authorities disagree, preserve the competing
claims with attribution and confidence; do not average dates or select the
most precise one merely because it is precise.

Treat “lost,” “whereabouts unknown,” and former shelfmarks in an older edition
as historical assertions. Search later accession reports and current catalogs;
record both the older status and a verified modern identification instead of
silently rewriting the source's history.

Compare shelfmark forms in the encoding header, internal headings, source
edition, and current institutional record. Use the repository's current exact
shelfmark for the witness, but preserve malformed or legacy source forms in
notes with the evidence that resolves them.

For archival series that have been reorganized or renumbered, establish a
legacy-to-current crosswalk from matching parties, titles, dates, contents, and
context—not number resemblance alone. Preserve unresolved reference history
instead of presenting a plausible numeric substitution as certain.

## Inspect the immediate edition

Whenever possible, open the actual book and inspect:

- title page and edition statement;
- preface/introduction statements about source, base witness, collation, and
  prior editions;
- apparatus, brackets, italics, expansions, supplied text, and normalization;
- included and omitted front/back matter; and
- whether a later issue is a reprint, reset, corrected reissue, revision, or
  new edition.

Scanned-book OCR and inherited TEI division labels can be misleading. Compare
markup with visible headings, page milestones, the scan, and surrounding text.
Record a demonstrably misleading label as an encoding practice or open
question rather than normalizing it silently.

## Keep a claim ledger

Before JSON, record each consequential claim with:

```text
claim | layer/entity | scope | direct source | confidence | manifest field
```

Open every supporting URL. Record exact item/component URLs and access dates.
Negative findings such as “no public facsimile found” require a dated search
scope and must not become proof that no digitization exists.
