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

An official repository publication of an older handwritten, unpublished, or
legacy catalog description is authoritative evidence for what that attributed
description says, but it is not automatically the repository's current
manuscript record. Identify its author and historical status, preserve its
claims at that layer, and continue looking for current institutional catalog,
access, and reproduction guidance.

Do not treat a microfilm, photostat, or reproduction-collection call number as
the manuscript's shelfmark. Identify the surrogate as its own entity and
verify which source objects and ranges it reproduces; one film number may
contain several manuscripts or only selected leaves.

First test whether apparently different foliation is only a notation
crosswalk: `a/b` and `r/v` commonly name the same recto/verso sides. Normalize
that equivalence before alleging historical refoliation. If one source then
ends at `75a` while direct milestones, a catalog, or an image-supported source
continue through `75b`/`75v`, preserve the first value as a source-layer
endpoint conflict rather than inventing a second foliation system.

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

Apply the same separation within one edition when a source caption conflicts
with inline folio marks, and again when a later encoding introduces a third
locator. Preserve the caption, inline marks, and encoding milestone as
layer-specific claims. Sequence, chronology, or neighboring entries may
support a preferred candidate, but they do not authorize silently correcting
the edition or declaring the conflict resolved without witness images or
repository confirmation.

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

Treat XML `PB` and equivalent milestones as boundaries in document order, not
as automatic inclusive starts for their containing part. When a heading or
text precedes the first internal page milestone, inherit the previously active
printed page, confirm the resulting range against the scan or OCR, and freeze
the source-specific range instead of dropping the unmarked opening page.

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

## Reuse cached sources by identity

Before downloading a large facsimile or other source object, search all of
`source-cache/`, not only the current work directory. Search by normalized and
legacy shelfmark variants, repository or provider object identifiers, and
likely filenames as well as by exact source URL. Different work directories or
filenames do not imply different source bytes.

For a candidate IIIF ZIP, inspect its embedded `manifest.json` and
`inventory.json` with `unzip -p`. Compare the source and manifest identities,
canvas count and order, effective image request profile, target canvas or
folio, ZIP integrity, member inventory, and whole-file checksum. For other
formats, compare the equivalent item identity, request or download profile,
extent, checksum, and format integrity. Reuse only when those checks establish
that the cached object is the same complete source at the needed practical
resolution.

Create a true hard link in the new work's cache directory and then verify the
source and link share an inode and exact bytes. Record the new work's own
target portion and access relationship; cache reuse never transfers a locator
or proves that the target work is present in the source.

Do not freeze `st_nlink` or infer the original donor, first download, or
acquisition order from a live link count: it changes as mirrors and worktrees
are created or removed. Freeze explicit donor or reuse provenance when it is
known, plus byte count, checksum, and inventory; validate specifically named
live peers by device and inode at runtime.

## Probe Raw Michigan Book packages

For every U-M DLPS item, probe the Internet Archive metadata endpoint for the
lowercased item identifier plus `.umich.edu`, for example
`https://archive.org/metadata/anz4364.0001.001.umich.edu`. Inspect the returned
file list for the exact `*_umichbook.zip` member; do not infer that a package
exists merely from the naming pattern. When it is public, cache both the
metadata response and the complete ZIP, even when the encoded work occupies
only part of the scanned volume.

Audit the package before modeling it:

- compare its byte count, MD5, and SHA-1 with the provider metadata and record
  a local SHA-256;
- run the ZIP CRC test, inventory every member, and verify that the TIFF names
  form the advertised contiguous sequence;
- identify the raw XML, text, header, page-view map, and production log rather
  than treating the ZIP as an undifferentiated facsimile;
- map title, body, apparatus, and back-matter TIFFs from the XML `PB` values
  and page-view data, retaining unreferenced images as part of the complete
  carrier; and
- compare the embedded raw XML with the pinned CME XML element by element.
  Classify every changed attribute and every character-data difference. Assert
  `copied_from` only when a bounded reversal of deterministic identifiers,
  editorial-level changes, and formatting whitespace leaves no unexplained
  difference; record both original hashes and the normalized equality proof.

Model three documentary layers even though one ZIP delivers all of them: an
Internet Archive package artifact, the raw U-M encoding, and the U-M TIFF
facsimile. The package `contains` the encoding and TIFF set; the encoding is
`encoded_from` the TIFFs when the raw header and page links establish that
process; and the TIFF set is `facsimile_of` the scanned edition. Do not make
the package itself an encoding or facsimile. Attach the same verified package
local-copy object to each access route that genuinely delivers a contained
layer so the viewer can show that layer as downloaded, but count the bytes and
unique cache path only once. Keep package-wrapper rights, the current U-M item
statement, and any older raw-header warning in separate, time- and
component-scoped rights records.

## Keep a claim ledger

Before JSON, record each consequential claim with:

```text
claim | layer/entity | scope | direct source | confidence | manifest field
```

Open every supporting URL. Record exact item/component URLs and access dates.
Negative findings such as “no public facsimile found” require a dated search
scope and must not become proof that no digitization exists.
