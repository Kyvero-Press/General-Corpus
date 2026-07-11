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

## Parallel witnesses: HMaid

An edition printing Bodley 34 and Cotton Titus D XVIII in parallel still
represents one intellectual work. Create separate witness entities and scoped
edition-to-witness edges. Keep witness-specific dates and access routes in
lineage; only a genuinely earliest attestation belongs in work metadata.

If an encoding serializes those parallel columns or pages as consecutive XML
divisions, treat the divisions as representations of separate witnesses, not
as intrinsic chapters or parts of the work. Record the layout transformation
as an encoding practice.

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
