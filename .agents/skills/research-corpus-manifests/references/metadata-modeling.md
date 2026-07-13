# Work-metadata modeling

Read this after fixing the cataloging boundary and before drafting
`manifests/work-metadata/works/WORK_ID.json`.

## Identity and responsibility

Use an established work title as the preferred whole-work title. Retain a
source edition's long title as an alternative when it describes a different
layer.

Keep a catalog-supplied or inherited attribution heading distinct from a
title or rubric visibly present in the witness. Do not call catalog wording a
manuscript rubric unless direct image evidence or an explicit catalog
statement locates that wording on the physical page.

Assign roles from intellectual responsibility, not an inherited `AUTHOR`
field. Distinguish source author, translator, adapter, compiler, medieval
scribe, editor, collator, and digital contributor. Model anonymous, attributed,
and disputed creation honestly.

Treat an acrostic as direct evidence for its recovered letter sequence, not
automatically for that sequence's referent or role. Model author, scribe,
patron, person, and place interpretations separately with qualified assertions;
preserve competing readings as an open question.

When an immediate source retains an earlier editor's text but adds a new
collation or revision, represent both roles. A compact editor display may name
one primary editor or include every editor agent in a composite description.

## Dates

Separate:

- narrated or autobiographical event;
- composition, translation, compilation, and revision;
- witness production;
- genuine first publication of the work;
- immediate source-edition issue/reissue;
- encoding creation/distribution; and
- repository review.

Keep an immediate source edition's date in lineage unless it is genuinely the
work's first publication. Use qualified displays and normalized ranges only
when the range itself is sourced. Do not normalize `c. 1385` to an exact 1385
interval merely to satisfy a facet.

When the earliest surviving witnesses have overlapping production ranges and
the evidence does not establish which is earlier, model a joint qualified
attestation window. Omit a singular `source_lineage_entity_id`, and use a
supported, appropriately uncertain assertion rather than presenting either
witness as the confirmed first attestation.

## Places and languages

Type place claims as composition, translation, cultural origin, dialect,
historical setting, association, copying, publication, or current holding.
Witness production at an abbey does not by itself prove that every composition
stage occurred there.

Inspect language markup and the work itself. Scope embedded Latin, French, or
other languages to the relevant parts; do not make the whole work multilingual
because a title page, rubric, or surrounding codex is multilingual.

Every code in `language_statements` is exposed through the work's summary and
viewer language facets. When the cataloging subject is a medieval work, do not
add modern editorial prose or apparatus quotations as work-level languages
merely because the encoding retains them. Record those edition-layer languages
in content-part descriptions, summaries, and lineage instead. Use a scoped
language statement only when that language belongs to an intellectual part of
the cataloged work and should be discoverable as a work facet.

## Form, genre, subject, and tags

`form` describes expression: prose, verse, or mixed. Use whole-work `mixed`
only when both forms are intentional and substantive. Keep prose or verse when
the other form is limited to brief quotations, rubrics, framing, or excluded
editorial material, and record the exception at part level.

`genre` is a recognized textual category. `subject` is what the work discusses.
`tags` are normalized discovery terms. Do not duplicate one synonym list
across all three or tag material merely mentioned by an editor.

Reuse the same label for a normalized language code, genre term, or subject
term throughout the corpus. Put dialect, period, and work-specific nuance in
scoped notes. The viewer rejects conflicting labels even when each pair passes
isolated validation.

## Structure and summaries

Model stable intellectual parts before attaching part-level authors, dates,
languages, forms, or lineage bindings. `part` and `selected_passages` scopes
must name modeled `part_ids`.

Counts must be reproducible and labeled as encoding metrics when markup choices
affect them. Keep planned, composed-but-lost, extant, printed, and encoded
extent separate. If markup is coarse or inconsistent, use `summary` or
`partial` structure status and explain why.

Count structural nodes at the depth that represents the cataloged work.
Exclude verse lines nested inside editorial notes, quotations, or apparatus
from the direct poem-line count, report them separately, and preserve any
disagreement with a scholarly lineation as an explicit open question.

In an edited archival collection, numbered editorial units may combine several
physical documents, fragments, abstracts, or outside illustrative records.
Report editorial-unit, XML-container, physical-object, and archive-size counts
separately; do not treat them as interchangeable extent measures.

Derive `catalog_summary` from detailed records. Preserve detailed-record order
in summary language, genre, and tag arrays. Maintain exactly one preferred
whole title and one whole discovery form. Every reviewed record must also have
an `abstract` summary scoped to the whole cataloged unit; part-scoped abstracts
are supplemental and are intentionally ignored by viewer cards. Briefly account
for any retained editorial framing in the whole abstract so the scope remains
honest rather than falling back to the viewer's missing-summary placeholder.

## Metadata checklist

- Define `cataloging_subject.scope_note` against nearby layers.
- Confirm author/translator/editor roles from direct evidence.
- Keep work dates free of mere source-edition dates.
- Do not infer region from publisher or current holding.
- Use distinct genre, subject, and tag vocabularies.
- Bind every lineage entity and evidence ID to the linked lineage manifest.
- Use `partial`, qualified assertions, and open questions for real gaps.
- Use `pending_external_response` only after an enquiry has actually been
  submitted; planned outreach remains `unresolved`.
