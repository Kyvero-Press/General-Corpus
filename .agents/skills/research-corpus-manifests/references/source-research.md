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

When an index or scholarly database points to a related record, open the
target record and verify its title, incipit, witness, and claimed relationship
before creating a lineage edge. A syntactically valid record ID can still lead
to an unrelated work. Preserve a mistaken pointer as a source-data issue and
use the verified target record, if one can be established, rather than silently
propagating the bad cross-reference.

Treat “lost,” “whereabouts unknown,” and former shelfmarks in an older edition
as historical assertions. Search later accession reports and current catalogs;
record both the older status and a verified modern identification instead of
silently rewriting the source's history.

Compare shelfmark forms in the encoding header, internal headings, source
edition, and current institutional record. Use the repository's current exact
shelfmark for the witness, but preserve malformed or legacy source forms in
notes with the evidence that resolves them.

Do not treat a microfilm, photostat, or reproduction-collection call number as
the manuscript's shelfmark. Identify the surrogate as its own entity and
verify which source objects and ranges it reproduces; one film number may
contain several manuscripts or only selected leaves.

Treat legacy and corrected foliation as a locator crosswalk for one physical
witness unless evidence establishes distinct objects. Record both ranges and
name which system each source uses; do not create a second witness merely
because an older edition is offset by a skipped or duplicated folio number.

An enclosing catalog title or inherited author heading can describe a whole
miscellany while an exact contents entry rejects that attribution for one
work. Prefer the component-level statement for work responsibility and retain
the broader label only as attribution history or catalog context.
That preference is not automatic when an exact component locator contradicts
both its own parent contents and direct edition evidence. Preserve the
conflicting loci, keep the work mapping provisional, and verify current
foliation from the manuscript images or repository clarification.

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

Audit encoded notes and appendices as their own source layer. A quoted,
collated, or transcribed passage taken through another printed edition may
introduce that edition and its deeper witness as passage-scoped lineage;
a bibliographic citation that supplies no reading does not by itself create a
derivation edge. When an editor names a manuscript siglum but identifies its
text through an earlier printed edition, route the comparison through that
edition unless direct codex consultation is evidenced; concordance line
numbers and variant citations alone do not prove physical consultation.

For serial publications, inspect the issue wrapper or issue title page, the
completed-volume title page, and current catalog metadata independently. They
may legitimately carry different years, imprints, publishers, or places;
record each at its own issue/volume/catalog layer instead of forcing one
synthetic citation.

If an institutional manuscript catalog cites a source with a year, volume, or
page detail contradicted by the inspected source's own title page and
pagination, do not copy the catalog error into the edition entity. Use the
primary bibliographic evidence for the edition, preserve the catalog's wording
as a separately attributed assertion, and explain the correction so later
researchers can still reproduce the catalog search.

When the immediate edition itself prints a demonstrably wrong volume, page, or
shelfmark, preserve that literal target with a scoped `cites` relation. Model
the evidence-supported source that actually supplies the reading as a separate
transmission relation, and record the exact-text comparison and remaining
uncertainty. Do not silently replace the printed citation or imply that a
matching correction is documented by an erratum when it is only inferred.

Scanned-book OCR and inherited TEI division labels can be misleading. Compare
markup with visible headings, page milestones, the scan, and surrounding text.
Record a demonstrably misleading label as an encoding practice or open
question rather than normalizing it silently.

Never resolve a manuscript shelfmark from OCR alone. Inspect the cited page
image at high enough resolution to distinguish punctuation and adjacent
digits, then test the reading against current candidate catalogs and their
contents. If the OCR string names a different real manuscript, preserve it as
an OCR-layer error; do not create an ambiguous or false witness edge merely
because both identifiers resolve.

When an editor's preliminary notice and final edition report different counts
of leaves, omissions, recipes, items, or supplied passages, preserve both as
dated assertions. Prefer the final edition for that edition's settled scope
unless later evidence corrects it, while retaining the preliminary notice for
provenance or physical-description details it uniquely supplies.

## Keep a claim ledger

Before JSON, record each consequential claim with:

```text
claim | layer/entity | scope | direct source | confidence | manifest field
```

Open every supporting URL. Record exact item/component URLs and access dates.
Negative findings such as “no public facsimile found” require a dated search
scope and must not become proof that no digitization exists.
