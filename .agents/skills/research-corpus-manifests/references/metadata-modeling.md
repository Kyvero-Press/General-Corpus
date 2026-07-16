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

Treat aggregate-catalog language flags as discovery leads, not direct evidence
for every witness. A record-level flag may come from a benediction, rubric, or
other feature unique to one collateral witness. Verify the encoded witness and
scope the language to the witness or part that actually contains it before
adding a work-level language facet.

When reliable sources disagree over a diachronic label for the same
transitional vernacular text, such as Old English versus early Middle English,
do not encode both labels as though the work were bilingual. Choose one
discovery facet from the text's date, repository context, and current
scholarship; use appropriately qualified confidence, and preserve the alternate
classification and linguistic base in evidence and notes. Add multiple
language facets only when distinct linguistic material or genuine
code-switching belongs to the cataloged work.

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

When the cataloging subject is one historical work but the encoded item also
retains a modern editor's preface or commentary, model that paratext as a
separate content part so the item boundary stays visible. Reconcile the whole-
item `extent` totals with every modeled part, including prose paragraphs, but
do not let those accounting totals make the historical work mixed-form,
multilingual, or coauthored by the modern editor.
Likewise, keep the editor's language, `textual-apparatus` label, and generic
philology or manuscript tags out of work discovery facets. Describe them in
the paratext part and lineage unless the cataloging subject truly is the
scholarly edition itself.

Inspect a numbered edition or XML unit before treating it as a work section.
A heading followed by an empty paragraph can preserve manuscript paratext such
as a catchword, gathering number, ownership note, or marginal cue rather than
the opening of another chapter. Keep the raw numbered-unit count as an encoding
metric, model the paratext separately, and use manuscript or edition evidence
to explain what it shows about a damaged or incomplete boundary.

When a printer or editor explicitly announces an intended chapter total but
the surviving body or XML merges, omits, or leaves some headings unlisted,
keep three counts separate: the announced intellectual chapters, their larger
book or section framework, and the actual encoding containers. Use the
announced total as intellectual extent only when the cataloging subject is
that exact recension, document the exceptional books or ranges, and do not
force the container count to agree by inventing or splitting units.

Count structural nodes at the depth that represents the cataloged work.
Exclude verse lines nested inside editorial notes, quotations, or apparatus
from the direct poem-line count, report them separately, and preserve any
disagreement with a scholarly lineation as an explicit open question.
Do not infer verse extent from the final printed or encoded line-number
milestone. Compare every milestone with positional line counts: duplicated,
skipped, or reset numbers can create a persistent offset. Record both the
verified textual line count and the source's numbering anomaly so locators
remain reproducible without silently "correcting" the edition.

Parallel-text encodings may also attach a pointer to every line for an
editorial concordance or cross-version alignment. Treat those pointers as
representation apparatus, not as line numbers: audit zero or unmatched
targets, duplicate targets, and the overlap between companion files, but use
the text's own line positions and specialist source descriptions for extent.
If the pointer namespace or matching rules are undocumented, keep their exact
semantics open; a maximum or unique-target count must not be used to reconcile
conflicting catalog line counts or extra blank and fragmentary positions.

The inverse encoding problem also occurs: prose containers do not prove that
their contents are prose. When direct textual inspection and scholarship
identify a brief intentional rhyme inside `P` elements, record the verse at
the smallest defensible part or item scope while retaining `prose` as the
whole-work discovery form when prose still overwhelmingly predominates. A
grounded verse-group count may coexist with `verse_lines: null` when the
edition and encoding suppress lineation; do not manufacture a line count from
punctuation or inferred rhyme breaks.

Inspect the content of line-like XML elements before treating their count as
verse extent. Speaker labels, editorial headings, and dotted rows that display
an incomplete boundary may be encoded as `L` inside `LG` even though they are
not medieval verse lines or complete stanzas. Report the raw XML count as a
representation metric, then record the verified textual line count separately
with the evidence used to exclude those display elements.

Do not assume one `LG` container equals one displayed stanza. An encoder may
place two separately numbered stanzas in one `LG`, or may retain an incomplete
stanza in its own container. When those structures occur, report `LG`
containers, displayed stanzas, and direct textual `L` children as separate
representation metrics; explain the mismatch instead of normalizing any count
to an ideal stanza form.

In an edited collection, one numbered editorial or XML container may combine
several intellectual units, alternative textual branches, physical documents,
fragments, abstracts, or outside illustrative records. Use nested parts when
needed, and report intellectual-unit, editorial-container, XML-container,
physical-object, and archive-size counts separately; do not treat them as
interchangeable extent measures.

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
