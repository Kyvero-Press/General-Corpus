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

## Relations and direction

State exactly what derived from what and at what scope.

- Use `transcribes` for direct transcription, not general consultation.
- Use `collated_against` for variant comparison.
- Scope selections, excerpts, folio ranges, volumes, and appendices.
- Represent an eclectic edition against the named tradition or witnesses; do
  not invent a single base witness.
- Keep later comparison sources out of the upstream chain.

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
copyist's separate transcript.

Keep a lost or unidentified physical exemplar distinct from a surviving close
textual witness. Shared readings, likely family membership, or even very close
agreement can support a comparison relation or an open identity question, but
cannot make the surviving object the editor's, printer's, or translator's
physical source without provenance evidence.

A repertory identifier for a source work, such as a BHL number, can support a
part-scoped `version_of` relation even when the translator's physical exemplar
is unknown. Model the repertory as describing that source work. Treat a later
printed edition of the source text as a supporting version or comparison—not
as the physical exemplar—unless transmission evidence establishes that use.

When an editor says that a passage was absent because a leaf had been lost
from the surviving witness's exemplar, do not describe that leaf as missing
from the surviving codex itself. Model the exemplar-level textual lacuna and
the current physical object's completeness as separate claims.

When an edition interleaves parallel witnesses, replacement leaves, supplied
passages, or another edition's text, create separately scoped relations for
the evidenced ranges. Do not describe the composite result as a homogeneous
transcription from whichever source supplies most pages.

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

## Parts and shared objects

A codex can contain several works, and an edition can print several witnesses
or source works. Scope each relationship to exact parts or locators. Do not let
one witness's date, dialect, or rights become a whole compilation's property.

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
- Attach witness facts to exact institutional records.
- Keep broader traditions separate from representative witnesses.
- Put attractive but unsupported ancestry in `open_questions`.
