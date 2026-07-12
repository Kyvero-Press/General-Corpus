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

## Parallel witnesses: HMaid

An edition printing Bodley 34 and Cotton Titus D XVIII in parallel still
represents one intellectual work. Create separate witness entities and scoped
edition-to-witness edges. Keep witness-specific dates and access routes in
lineage; only a genuinely earliest attestation belongs in work metadata.

If an encoding serializes those parallel columns or pages as consecutive XML
divisions, treat the divisions as representations of separate witnesses, not
as intrinsic chapters or parts of the work. Record the layout transformation
as an encoding practice.

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

## Component records: Ayenbite

The exact BL child record ends Ayenbite at folio 94r; later folios contain other
texts. Use a component record for work boundaries and the parent codex record
for codicology/access. Do not absorb adjacent contents into the work.

For fragmentary witnesses bound into composite volumes, distinguish the leaves
carrying the cataloged work from adjacent leaves carrying other fragments.
Report total codex extent only at the physical-object layer.

## Candidate fragments: acb1675

A scholarly proposal that a difficult fragment may preserve a related text is
not a confirmed witness. Model the exact folio with a tentative, scoped
relation and an open question; do not count the fragment—or its whole host
codex—in the secure witness set until textual identity is demonstrated.

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

## Current digital versus legacy foliation: CME00026

A modern complete surrogate can label a work at current fols. 80r–93v while a
reliable older census cites the same leaves as 96r–109v. Record both as one
witness's locator crosswalk, name each numbering system, and map digital
canvases to the labels actually displayed by the current object. Do not shift
the facsimile range to agree with the older citation or create two witnesses.
