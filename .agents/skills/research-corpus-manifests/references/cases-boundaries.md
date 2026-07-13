# Cases: cataloging boundaries and parts

Read only for composite items, selections, shared codices, part-level
attribution, or parallel witnesses.

## Branching selections: CME00099

Holthausen's organized selection draws sections from two manuscripts. Model the
cataloged edited selection explicitly, give each witness a scoped derivation
edge, and do not assign the whole selection one witness's date, dialect, or
rights status.

## Part-level attribution: ChaucerAstr

The Chaucerian core and supplementary conclusions have different attribution
status and witness mappings. Create stable content-part IDs before attaching
authors, languages, dates, or lineage relations. Whole-work attribution must
not erase a disputed supplement.

## Shared codex, distinct works: Gawain and Pearl

Works in Cotton Nero A X/2 remain separate intellectual units with exact folio
ranges. Preserve current part-level shelfmarks and legacy foliation without
forcing false agreement. Reuse of the same physical codex does not merge work
metadata or image-rights analysis.

When one image or PDF page contains the end of one work and the opening
illustration or text of the next, include that shared surface in both verified
work mappings and say that the boundary is shared. Do not crop the cached
complete-codex surrogate or imply that the page belongs exclusively to either
work.

A modern census can describe a continuous manuscript run as one broad witness
unit even when direct images show two separately rubricated works within it.
Preserve the census unit as an attributed catalog claim, but let the visible
rubric, incipit, explicit, and shared-surface evidence control the part
mappings. Do not force the census record boundary onto the intellectual works
or retroactively make the collateral facsimile a source of an older edition.

One historical codex can now survive as two or more separately held physical
objects. Give every present shelfmark its own witness entity and do not join
them with `same_as`. Request or cache the whole of each present object, then
map the relevant work portion within each delivery; describe the historical
join and unresolved current foliation separately.

## Parallel witnesses: HMaid

An edition printing Bodley 34 and Cotton Titus D XVIII in parallel still
represents one intellectual work. Create separate witness entities and scoped
edition-to-witness edges. Keep witness-specific dates and access routes in
lineage; only a genuinely earliest attestation belongs in work metadata.

If an encoding serializes those parallel columns or pages as consecutive XML
divisions, treat the divisions as representations of separate witnesses, not
as intrinsic chapters or parts of the work. Record the layout transformation
as an encoding practice.

A repertory may assign a separate record to a witness version because it has
an added preface, prologue, or other incipit-changing material. Preserve both
record identifiers and model the forms as related versions unless the
repertory or scholarship establishes separate intellectual works. Do not
silently merge the records, but also do not multiply one encoded work merely
because its collateral version has a separately indexed opening.

When an edition prints one complete witness version and collates shorter or
longer collateral copies, derive encoded stanza and line extent from the
printed base version. Record each collateral extent separately. A later
edition that chooses a different base does not redefine the older encoding's
extent, even when both editions represent the same abstract work.

When an encoding serializes several complete witness versions of one abstract
work, count the abstract work once. Model one parent work part with
`item_count: 1`, give each witness-version child `item_count: 0`, and record
the children's stanza, line, or prose metrics separately. Do not sum parallel
versions into a fictitious whole-work length or let validator accounting turn
the witnesses into multiple intellectual works.

A witness-labeled stream can itself be composite when the editor supplies
lacunae or selected passages from other manuscripts. Keep the stream's main
witness edge, then add passage-scoped source relations for every explicitly
supplied segment; a column heading is not proof that all its readings derive
from one physical object.

If every serialized witness stream stops at the same line even though the
printed edition continues, test for a shared encoding cutoff before proposing
parallel manuscript loss. Record the omitted edition pages and lines as an
encoding boundary unless witness-specific evidence establishes genuine
lacunae.

## Parallel comparison text: CME00108

Zupitza interleaves a Middle English manuscript transcription with Latin from
Grässe for comparison, while the U-M encoding serializes the two languages as
consecutive version streams. Catalog the surviving Middle English saint's life
as the work and its sole intrinsic language; do not make it bilingual merely
because the digital artifact also contains the Latin alignment text. Record
the encoding's layout transformation, connect the Latin stream to Grässe with
a part-scoped comparison or excerpt relation, and keep both the Latin source
work and the translator's still-unidentified physical exemplar distinct.

## Component records: Ayenbite

The exact BL child record ends Ayenbite at folio 94r; later folios contain other
texts. Use a component record for work boundaries and the parent codex record
for codicology/access. Do not absorb adjacent contents into the work.

For fragmentary witnesses bound into composite volumes, distinguish the leaves
carrying the cataloged work from adjacent leaves carrying other fragments.
Report total codex extent only at the physical-object layer.

When a paper slip, letter, or other document is pasted or mounted onto a host
leaf, keep the attached document and host folio as separate physical layers.
Scope support, dimensions, recto/verso locators, and attachment evidence to the
correct layer rather than transferring the host leaf's material to the target.

## Fluid proverb compilations: CME00074

A proverb sequence can be a manuscript-specific compilation rather than one
stable authorial work. Catalog the exact witnessed sequence, preserve directly
legible internal units such as separately rubricated components, and describe
finer proposed strata as scholarly analysis unless the boundaries are secure.
Do not silently reconcile conflicting catalog line counts or witness censuses:
retain each as a versioned, attributed claim and open a reconciliation question.

Keep authorial dialect localization, scribal language, manuscript production,
and compilation place separate. Rhyme evidence that tentatively associates a
poet with a region supports a scoped `dialect_region` claim; it does not prove
`place_of_composition` or the place where the surviving compilation was made.

## Candidate fragments: acb1675

A scholarly proposal that a difficult fragment may preserve a related text is
not a confirmed witness. Model the exact folio with a tentative, scoped
relation and an open question; do not count the fragment—or its whole host
codex—in the secure witness set until textual identity is demonstrated.

## Target lines interpolated in a host work: CME00079

When lines of the cataloged work survive only as interpolations inside a
different host work, keep both intellectual identities distinct. Model the
physical manuscript as a collateral witness with the exact interpolated line
runs, not as a source of the immediate edition unless the edition actually
uses it and not as a complete independent copy of the target work.

A published image of the host codex supplies target-work coverage only after a
folio-to-line concordance proves that the pictured surface contains one of the
interpolated runs. Until then, cache and describe the image at its physical
folio scope, explicitly mark target overlap unverified, and retain a whole-
object acquisition route for the complete codex.

## Catalog-inferred locus versus written extent: CME00008

A repository TEI record may infer a sole `msItem` locus from the physical
codex's first and last leaves even when its own collation identifies terminal
blanks. Preserve that repository assertion with its inference status, then
use direct editorial or visual evidence to map the narrower written extent of
the work. Do not silently convert total-object extent into text-bearing
folios; the complete-facsimile request should still include those blanks.

## Discontiguous edition selections: CME00012

An encoding can resume after silently omitted editorial pages even when its
included page milestones appear to describe one broad span. Compare the XML
boundary against the complete edition page by page, then record every included
run separately in the cataloging boundary and cached source's `work_portion`.
Do not collapse printed pp. 1–73 and 76–145 into the false continuous range
pp. 1–145; retain the omitted pp. 74–75 as part of the complete cached volume.
If a selected run begins or ends partway through a page shared with unencoded
material, record the exact textual or spatial boundary in relation scope and
`work_portion`; a terminal page number alone does not imply whole-page coverage.

An encoder may also relocate a supplied article title or heading from an
earlier page to sit before a later selected passage. Preserve the heading and
passage as separate source loci even when the XML places the heading after the
later passage's `PB`. Element adjacency establishes encoding order, not source-
page provenance; cite the heading's original page and record the relocation.

Page-break element counts need not equal distinct source pages. One printed
page can be cited by two adjacent structural divisions when the first text
ends and the next begins on that same page. Compare the ordered unique page
references and inspect the shared boundary before diagnosing a missing or
duplicate page; preserve both structural milestones when both are meaningful.
Parallel source-language and editorial-translation streams can likewise repeat
the same page/image milestones. Deduplicate locators only for physical coverage
audits; keep the language streams and their editorial responsibilities separate.

A recurring article or series title across journal volumes does not establish
one continuous or complete intellectual work. Inspect every encoded
installment against its volume contents, opening and closing pages, and any
earlier or later continuation in the same volume. Model the digital item as a
selective compilation when appropriate, keep each issue- or volume-level
edition distinct, and scope derivation only to the runs the encoding actually
includes.

Two independent texts can also continue simultaneously in different zones of
the same printed pages—for example, one stream below and an addendum above.
Preserve the overlapping page range in both scoped parts and record the spatial
layout. Do not treat the repeated page breaks as duplicate pagination, force the
streams into one false linear sequence, or assign either stream exclusive
ownership of the shared physical pages.

## Scholarly fragments and detached witnesses: CME00038

Stable attribution, dialect, or source fragments can be useful descriptive
parts even when the manuscript copies one continuous text. Preserve those
parts for scoped authorship and dating claims, but state that they are
scholarly analysis rather than manuscript-imposed divisions.

Likewise, qualify a claim that a work survives in a “unique manuscript” when a
detached collateral leaf also preserves an overlapping passage. Distinguish
the sole continuous or principal codex witness from the separate fragment;
neither erase the leaf nor inflate it into a second complete witness.

## Acephalous text in an intact codex: CME00014

A work can begin imperfectly even when the current manuscript collation is
physically intact: the exemplar copied by the scribe may already have lacked
its opening. Keep textual acephaly separate from present leaf loss, and do not
invent a missing quire or earlier folio range without codicological evidence.
A complete-codex facsimile is still needed to test the support, ruling, hand,
and boundary with adjacent works.

## Archival selections across catalog records: CME00024

A named edition centered on one archival series can append excerpts from
separately cataloged court books, rolls, or accounts. Keep one cataloging unit
for the edited selection, but give each appended part its own scoped source
relation and current request route. Overlapping modern date ranges, old box
labels, and broad parent descriptions do not justify inventing a one-to-one
historical item crosswalk when exact child-record evidence is incomplete.

For a large archival calendar, keep at least four counts distinct: the
edition/XML's editorial units, current catalogue entry groups, separately held
physical copies, and digital manifests/canvases. Give every identifiable roll
or copy its own witness and exact edition-page relation; a parent series is not
one physical manuscript.

Audit an unbound roll by its applicable surfaces—face, dorse, membranes,
schedules, tabs, and rolled views—not by codex furniture. A face-only inventory
is `coverage=partial`. If one provider manifest mixes images from separately
cataloged copies, retain the complete published digital inventory but keep the
physical witnesses distinct, mark the affected coverage partial, and record
the aggregation as an unresolved provider-layer fact.

When extracting a large hierarchical catalog, traverse every entry container
rather than assuming all child IDs share one prefix; audit per-series citation
and IIIF counts so an identifier-family change cannot silently omit a section.
Follow explicit cross-references to their target catalog groups and do not
invent duplicate unavailable witnesses for the referring rows. Test an
edition citation against each copy-level or digital-object record inside the
target group: a citation attached to one copy does not make every sibling copy
a source for that edition. When canvas labels are generic, claim only a
complete provider-published inventory and leave physical-side completeness
open.

## Current digital versus legacy foliation: CME00026

A modern complete surrogate can label a work at current fols. 80r–93v while a
reliable older census cites the same leaves as 96r–109v. Record both as one
witness's locator crosswalk, name each numbering system, and map digital
canvases to the labels actually displayed by the current object. Do not shift
the facsimile range to agree with the older citation or create two witnesses.

A historical foliation can begin above 1 while still agreeing with the
physical extent—for example, sixteen surviving leaves numbered 4–19. Do not
silently renumber them 1–16. Retain the historical locator and request a
repository-confirmed crosswalk to the current foliation.

Do not extrapolate a constant folio offset across a lacuna or other large
discontinuity. Align the cited passage's text against current folio labels and
IIIF canvases, record the missing-leaf span, and retain both locator systems.
Until a repository concordance or equivalent codicological source confirms the
mapping, label the historical-to-current crosswalk inferential even when the
textual alignment is strong.

## Displaced leaves and incomplete reproductions: CME00134

An institutional component range can be continuous while the target work's
current physical run is not. If codicological evidence places displaced leaves
from another work inside that range, preserve the provider's broad component
locator as its catalog claim, but give the target work a discontiguous current-
folio and canvas sequence. Do not assign the intervening leaves to the target
merely to make its range continuous.

A downloaded provider object can be complete as delivered yet incomplete as a
reproduction of its stated edition. Audit the represented pages, not only file
integrity and provider leaf count. Record provider-object completeness
separately from source coverage, mark the facsimile relation partial when even
one source page is absent, and name the missing page or passage explicitly.

## Different causes of supplied text: CME00135

Do not merge every editor-supplied passage into one generic lacuna. Distinguish
an opening already absent from the surviving witness, a later passage omitted
by that witness's copyist, and source material the translator never translated.
Model each cause and supplied range separately, and do not infer physical leaf
loss for a translator's omission merely because the edition prints source-
language prose in its place.

A bound scan can combine a historical text edition with a separately issued
later study. If an encoding retains only the later study's series half-title,
create a separate publication entity and paratext part for that leaf. Do not
extend the earlier editor's responsibility or the medieval work's date,
language, form, or extent across the retained carrier fragment.

## Later-hand additions and competing unit counts: CME00137

When a current component record explicitly excludes a target folio from the
main scribe's work, do not inherit that scribe's date, dialect, or locality for
the addition. Preserve older absolute dates, repertory dates, and modern
relative hand chronology as separate assertions; a statement such as "not much
later" does not justify inventing a normalized year range.

An edition can divide one manuscript article into multiple procedural
paragraphs. Retain both the manuscript-article count and the edition or XML
paragraph count, explain the crosswalk, and catalog at the intellectual depth
the evidence supports. Verse quoted inside an editor's footnote remains
paratext and does not make the medieval prose collection mixed-form.
