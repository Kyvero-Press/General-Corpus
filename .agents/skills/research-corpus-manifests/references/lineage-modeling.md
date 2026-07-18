# Lineage modeling

Read this before drafting derivation entities and relations in
`manifests/lineage/works/WORK_ID.json`.

## Entities

Create one entity per evidenced material or digital layer. Normally model:

```text
repository artifact -> electronic encoding -> immediate edition
                                              -> witness(es)
```

Give the repository artifact its exact path, SHA-256, Git blob, repository,
and pinned commit. Give an encoding its stable collection/accession ID. Give an
edition full bibliographic facts. Give a witness its current shelfmark,
repository, item/component catalog record, date, and supported locators.
Preserve historical shelfmarks separately.

Before minting an entity ID, search the existing work manifests for the exact
same physical or digital object. Reuse the established ID when the layer is
identical, then restate this work's own scoped relations, access, rights, and
evidence; shared identity does not make those work-specific assertions
interchangeable. Do not reuse one ID across a witness and its facsimile, across
complete and selected provider presentations, across distinct scan carriers,
or across separately cataloged present-day manuscript parts. If legacy
manifests already contain competing aliases, prefer the most precise recent ID
for new records and preserve the other identifiers as aliases or notes instead
of creating a third spelling.

Keep a reused entity's payload limited to intrinsic identity, holding,
physical, and date facts. Move target wording, selection exclusions, and
work-specific scope or comparison commentary to this work's scoped relations,
evidence, or open questions.
Apply that test to the whole entity, not only `holding` and
`physical_description`: descriptions, notes, date labels, citations, and
bibliographic page ranges can also leak target-specific scope. A full-volume
edition or catalog entity keeps full-object bibliographic identity; put the
pages used for this work on the scoped relation or evidence record, even when
an older manifest embedded them in the shared entity.

Make every `facsimile_of` edge describe surfaces that the reproduction actually
shows. When a public selection depicts non-target leaves of a composite codex,
point it to an entity for that whole physical carrier (or another component
that really includes those leaves) and scope the target witness separately to
its own folio or fragment. Do not point non-target images at a folio-specific
target entity they do not reproduce. Keep the selection's cached copy
`target_work_presence=absent` even though it belongs to the same composite
carrier.

If an edition announces an illustration or plate suite but checked carriers
omit it, do not infer that the suite was never issued. Search later related or
reissued carriers, tie any confirmed occurrence to the exact carrier that
contains it, and keep the earlier carrier state unresolved. Count distinct
physical designs separately from title leaves, tissue guards, and repeated
scan states.

When issued print illustrations demonstrably copy or redraw manuscript images
but the schema has no visual-adaptation relation, use a part-scoped
`version_of` edge as an explicit proxy. Identify the exact issued surfaces and
manuscript loci, state that the relation models visual adaptation rather than
textual ancestry, transcription, or facsimile reproduction, and exclude
advertised-but-absent designs from confirmed scope.

When a catalog or older editor calls a witness “unique,” check current
repertories for complete and fragmentary holdings. Record “unique complete
copy” separately from surviving fragments; do not turn it into “only surviving
material” or collapse fragments held elsewhere into the complete carrier.

Set the lineage manifest's `primary_subject` to that repository-artifact
entity, which must carry `repository_file.path`; the discovery index depends
on this contract. An abstract work may remain a related lineage entity and a
metadata `related_works` record, but it is not the lineage manifest's
`primary_subject`. Under the current metadata validator, lineage bindings may
target only the cataloging subject or modeled content parts; do not bind a
`related_works` ID.

Resolve an editor's witness sigla from that edition's explicit manuscript key,
not from an intuitive expansion of a letter. Record the siglum with the
edition-to-witness relation while identifying the physical witness by its
current repository and shelfmark; a letter such as `L` may name a collection
or city different from the one a modern reader would guess.

If the key or apparatus resolves a comparison siglum to a prior editor or
printed edition, route the comparison through that printed intermediary. Do
not create a direct edition-to-manuscript consultation edge merely because the
prior edition can itself be traced to a known witness. Preserve the physical
witness as the prior edition's source and state what evidence would be needed
to establish direct consultation by the later editor.

Add scans, facsimiles, prior editions, source works, translations, transcripts,
or comparison editions only when their identity and relevance are evidenced.
Do not leave contextual entities dangling: each lineage entity should
participate in an evidenced relation or have a practical access/rights role.
Keep broader source context used only for description in metadata
`related_works` instead.

Do not type a supporting study as a `scholarly_edition` when it contains no
target text, or as a facsimile when it reproduces no target witness. If that
study needs its own current-schema entity because it has a distinct delivery,
access, or rights layer, use `catalog_description` provisionally and explain
the workaround. Keep the study expression separate from both its delivery
scan and the physical witness it discusses; verified zero target-text overlap
must remain explicit in the local-copy presence record.

Do not infer zero target overlap merely because the carrier is a monograph or
supporting study. Inspect its quotations, appendices, incipits, explicits, and
edited extracts. If the cached study reproduces any target text, mark that
local copy `target_work_presence=present`, give the reproduced passages a
page-scoped `work_portion`, and still keep the study outside the primary
transmission path unless the historical edition actually used it.

When the current schema needs conceptual nodes for an abstract work or its
recensions, `catalog_description` may be used provisionally only with an
explicit note that the node is not a material catalog record or carrier. If a
physical witness carries or attests a recension, a part-scoped `version_of`
edge may serve as the schema proxy, but its scope notes must say that only the
witness's textual component participates—the codex itself is not an abstract
textual version. Likewise, when an edition presents material from multiple
recensions through a scoped `contains` edge, say that `contains` is a proxy for
presents or embodies, not literal custody, ownership, or enclosure of the
conceptual entity.

An access, rights, or evidence role does not make a modern research source part
of the historical object's own citation graph. Do not invent a `cites` edge
from the repository artifact to a price list, legal guide, catalog, or
scholarly source merely because the manifest researcher consulted it. Keep
that dependency in evidence, access, or rights unless the relation's subject
actually contains the citation.

## Relations and direction

State exactly what derived from what and at what scope.

- Use `transcribes` for direct transcription, not general consultation.
- Use `collated_against` for variant comparison.
- Scope selections, excerpts, folio ranges, volumes, and appendices.
- Represent an eclectic edition against the named tradition or witnesses; do
  not invent a single base witness.
- Keep later comparison sources out of the upstream chain.

When a digital encoding omits an edition's textual apparatus, witnesses used
only for that apparatus remain supporting `collated_against` relations from
the source edition. Do not duplicate repository-to-encoding edges or primary
paths for readings that the downstream encoding did not carry.

“Made available through,” “distributed by,” a shared archive identifier, or a
directory name establishes association, not copying direction. Use
`version_of` with a qualified assertion until process documentation or file
comparison proves direction.

When the schema lacks `reprint_of` or `revised_edition_of`, use `version_of`
and state whether the edition was reissued, corrected, reset, revised, or newly
collated in scope notes and evidence.

A later transcript may preserve material now lost from a witness. Connect it
to what it copied, but do not place it upstream of an edition unless that
edition used it. Distinguish annotations made in the principal witness from a
copyist's separate transcript. When a provider sequence interleaves a later
transcript with original leaves, inventory the actual canvas order and label
both components; do not infer that every transcript page precedes its
same-numbered original or collapse the bound object into one textual witness.

Keep a lost or unidentified physical exemplar distinct from a surviving close
textual witness. Shared readings, likely family membership, or even very close
agreement can support a comparison relation or an open identity question, but
cannot make the surviving object the editor's, printer's, or translator's
physical source without provenance evidence.

Apply the same rule when an edition's historical siglum or shelfmark now names
a cataloged object whose language, contents, or extent conflict with the cited
source. Keep an unidentified historical-source entity for the editor's object,
the current catalog record as separate conflict evidence without a derivation
edge, and an open identity-reconciliation question. Add `same_as` or a direct
relation to the current physical object only after independent evidence resolves
the identity; a shared label or isolated excerpt does not establish continuity.

A repertory identifier for a source work, such as a BHL number, can support a
part-scoped `version_of` relation even when the translator's physical exemplar
is unknown. Model the repertory as describing that source work. Treat a later
printed edition of the source text as a supporting version or comparison—not
as the physical exemplar—unless transmission evidence establishes that use.

When authorities propose mutually incompatible source works or recensions,
model each evidenced conceptual alternative with a separately scoped,
appropriately tentative `version_of` relation and say that the edges compete.
Do not choose one, invent a physical exemplar, or leave confirmed source
lineage only in summaries; retain a reconciliation question until the evidence
resolves the alternatives.

When an editor says that a passage was absent because a leaf had been lost
from the surviving witness's exemplar, do not describe that leaf as missing
from the surviving codex itself. Model the exemplar-level textual lacuna and
the current physical object's completeness as separate claims.

When an edition interleaves parallel witnesses, replacement leaves, supplied
passages, or another edition's text, create separately scoped relations for
the evidenced ranges. Do not describe the composite result as a homogeneous
transcription from whichever source supplies most pages.

Audit every supplied run through its final token and every internal folio,
page, or canvas milestone. Do not assign a passage only to the surface on
which it opens when the source continues across later surfaces or changes
within a paragraph. If the edition proves the exact textual endpoint but no
source-side endpoint is available, retain the edition line or token boundary
and state explicitly that the source folio endpoint remains unavailable.

If a scribe copied an omitted passage later in the same manuscript and marked
its intended insertion point, create separate scoped `transcribes` relations
to that one witness: one for the main physical run and one for the displaced
supply. Record both the manuscript's physical loci and the edition's restored
reading order instead of inventing a continuous manuscript range.

A source-language text printed in parallel for comparison is not necessarily
the translator's physical exemplar. Model the editor's comparison or
alignment relation separately and leave the historical exemplar unidentified
unless transmission evidence connects that exact source object to the
translation.

When an editor translates a source-language witness to repair damaged text or
continue beyond a base witness's break, use a passage-scoped `consulted`
relation for that translation source when the schema has no `translated_from`
relation. Do not call the translated supply a transcription or a collation. If
the edition also prints the source-language passage verbatim, give that
separate printed passage its own scoped `transcribes` relation and keep its
inclusion or omission from the digital encoding explicit.

### Evidence-reviewed path classification

The viewer's legacy relation-type heuristic cannot always recover a researched
production path. A real path may need `version_of`, `contains`, or
`facsimile_of` steps between copying or transcription steps. When the research
packet has explicitly classified the complete graph, add both top-level
`primary_transmission_paths` and `supporting_relationships` to the lineage
manifest. Do not relabel a relation merely to make it appear in a preferred
viewer group.

For each primary path, list the ordered `relation_ids` and an
`entity_sequence` whose adjacent endpoints exactly match those relations in
subject-to-object direction. Group every contextual relation under a clear
supporting label. The two collections must classify every manifest relation
exactly once; no relation may be omitted or repeated across paths or groups.
Use descriptive labels and explanations to state what each reviewed path or
supporting group means. Omit both fields when the graph has not received this
complete evidence review; older manifests then retain the viewer's conservative
heuristic instead of presenting an analyst's partial grouping as definitive.

## Parts and shared objects

A codex can contain several works, and an edition can print several witnesses
or source works. Scope each relationship to exact parts or locators. Do not let
one witness's date, dialect, or rights become a whole compilation's property.
When an encoded parent contains multiple work or witness branches, give every
relation and reviewed path the exact child `NODE`, XPath, or equivalent branch
locator; for unnumbered sibling paragraphs, add a stable structural selector
and incipit. Repeating only the shared parent locator is not reproducible.

One historical textual witness can now be physically divided between two or
more repositories. Keep one witness entity for the historical textual unit,
but do not assign it a fictional singular current holding or shelfmark. Name
each surviving fragment, repository, shelfmark, and locus explicitly, give
current fragment access its own scope, and describe an aggregate digital
surrogate as complete only for its audited surviving published fragment
sequence—not for an unreconstructed original codex.

For an early printed fragment known through one bibliographic record but
reported as leaves or pieces in multiple repositories, keep one historical
print-witness entity only while the evidence supports that shared identity.
Omit a singular holding, give each provider its own fragment-scoped access and
future-image rights route, and leave physical unity, shelfmarks, and split
history open. If later evidence establishes distinct copies rather than parts
of one witness, split the entity instead of preserving a convenient aggregate.

When the entity schema has no general early-print or print-carrier type, use
`catalog_description` as the explicit workaround for an incunable, later
printing, or mechanical reprint carrier. Do not label it
`scholarly_edition` merely because bibliography calls it an edition or reprint;
reserve that type for an actual scholarly editing act. Keep an unaltered
reprint linked to the scholarly edition it reproduces, and give any provider
scan of that reprint a separate `facsimile` entity and same-object access
route.

Use exact component records for folio boundaries. A parent codex record can
support physical description and access, but it may include adjacent material
outside the cataloged work.

## Editorial practices

Record directly stated practices such as:

- omitted notes, glossary, introduction, or appendices;
- normalized spelling, punctuation, capitalization, or word division;
- abbreviation expansion and loss of typographic distinction;
- brackets, supplied text, emendation, and uncertainty markers;
- OCR/keying method and correction status;
- page/folio milestone behavior; and
- links from text to images.

Describe each layer separately. Do not infer a global practice from one local
example or treat normalized XML typography as a picture of the manuscript.

## Confidence

Use high confidence for direct self-identification, title-page facts,
institutional shelfmarks, and explicit editorial statements. Lower confidence
for scholarly reconstruction, approximate localization, inferred transfer,
and conflicting catalog data. Explain the uncertainty; confidence alone is not
an explanation.

If an edition and current repository disagree about hands, dates, or added
material, preserve each as an attributed assertion with its own evidence and
open a reconciliation question. Do not manufacture one consensus description.

## Lineage checklist

- Use the cataloged unit's preferred title as top-level `title`.
- Verify every entity, agent, relation, access, rights, evidence, and support ID.
- Ensure every edge has correct direction and scope.
- If explicit path classification is present, verify exact ordered endpoints
  and classify every relation once across primary paths and supporting groups.
- Attach witness facts to exact institutional records.
- Keep broader traditions separate from representative witnesses.
- Put attractive but unsupported ancestry in `open_questions`.
