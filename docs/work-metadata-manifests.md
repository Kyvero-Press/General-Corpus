# Work metadata manifests

The work metadata system provides descriptive, searchable information about
the intellectual content represented by a General Corpus identifier. It
answers questions such as:

- What is the preferred title?
- Who wrote, compiled, edited, translated, or commented on it?
- What composition, attestation, compilation, and publication dates are known?
- What origin, dialect, or cultural regions are supported?
- Which languages, genres, subjects, and textual forms occur?
- Is the content prose, verse, mixed, or unknown?
- Which discovery tags and content summaries should a catalog expose?

Material provenance and rights remain in the separate
[`lineage`](../manifests/lineage/) system. This prevents a holding location
from becoming an origin region, an editor from becoming an anonymous text's
author, or a scan's terms from becoming the work's copyright status.

## Files

```text
manifests/work-metadata/
├── README.md
├── index.json
├── schemas/
│   ├── work-metadata-index.schema.json
│   └── work-metadata-manifest.schema.json
└── works/
    └── CME00099.json
```

`index.json` contains compact discovery fields for consumers that do not need
the complete evidence graph. Validation derives those fields from each work
record so the index cannot silently drift.

## Cataloging unit

Every manifest states what it is describing through
`cataloging_subject.unit_type`:

- `single_work`
- `collection`
- `compilation`
- `edited_selection`
- `fragment`
- `composite`
- `unknown`

CME00099 is an `edited_selection`: Holthausen selected and organized 31 texts
from two manuscript witnesses and supplied a German scholarly frame. The
record does not pretend that this selection was already one titled medieval
work, nor does it describe either complete manuscript.

## Compact summary and detailed assertions

`catalog_summary` gives simple fields suitable for a book list, search index,
or UI:

```json
{
  "title": "Rezepte, Segen und Zaubersprüche aus zwei Stockholmer Handschriften",
  "author": "Anonymous contributors",
  "editor": "Ferdinand Holthausen",
  "date": "...witness dates...; edited selection published 1897",
  "region": "Section I ...; Section II origin unknown",
  "genres": ["Edited selection", "Medical recipe", "Charm"],
  "form": "mixed",
  "language_codes": ["deu", "eng", "enm", "fra", "lat"],
  "tags": ["charms", "medical", "middle-english"]
}
```

The remaining arrays preserve the evidence, scope, confidence, and uncertainty
behind those display values. Consumers doing research should use the detailed
assertions, not infer precision from the compact strings.

## Titles and responsibility

Require one whole-record `preferred` title. Supplied translations must say who
supplied them and must not be labeled original titles.

Agents and responsibilities are separate. A responsibility records:

- role, such as `author`, `editor`, `compiler`, `transcriber`, or `commentator`;
- attribution state, such as `known`, `anonymous`, `attributed`, or `disputed`;
- scope; and
- an evidence-backed assertion.

Do not create one universal fake “Anonymous” person. An anonymous or unknown
responsibility can instead carry a local `display_name` scoped to the relevant
parts.

For CME00099, the source-text creators are anonymous and likely plural.
Holthausen is recorded as editor, compiler, transcriber, Section I collator,
commentator, and author of the German editorial apparatus. U-M's interface
placing him in an “Author” field does not make him author of the historical
recipes and charms.

## Dates

Date assertions distinguish:

- composition;
- compilation or revision;
- first known attestation in a witness;
- first publication; and
- historical setting.

A manuscript date is evidence for attestation, not automatically for
composition. CME00099 therefore records:

- Section I attestation in X 90, with both the older later-fourteenth-century
  dating and the fifteenth-century qualification;
- a modern first-quarter-fifteenth-century dating for X 90's main hand;
- Section II attestation in a manuscript dated 1597; and
- first publication of Holthausen's edited selection in 1897.

The original dates of the individual texts remain open questions.

## Regions and languages

Places are reusable records, while place statements say why a place matters.
Allowed relationships include composition place, cultural origin, dialect
region, historical setting, and first known attestation.

Do not add Stockholm simply because the manuscripts are held there, or Halle
because the edition was printed there. Those facts belong in lineage.

CME00099 records Holthausen's South-East Midlands dialect classification for
Section I and the modern Norfolk localization of X 90's main hand. The latter
is scoped away from the manuscript's other hands and from Section II. Section
II's origin remains unknown.

Language statements use lowercase ISO 639-3 codes and distinguish primary,
secondary, embedded, quoted, and editorial use. The seed record separates:

- `deu`: German editorial apparatus;
- `enm`: dominant Middle English of Section I;
- `lat`: embedded Latin;
- `fra`: French Item I.24; and
- `eng`: a tentative classification for the copied-1597 English of Section II.

The XML root omits French, so cataloging checks the actual content rather than
copying only its `LANG` attribute.

## Form, genre, subject, and tags

`form_statements` use the controlled values `prose`, `verse`, `mixed`,
`other`, and `unknown`. Exactly one whole-work form is required, with optional
part-level refinements.

Genres describe kinds of text or resource, such as medical recipe, charm,
blessing, prognostic, or scholarly edition. Subjects describe what the content
is about, such as medicine, childbirth, fever, bleeding, or exorcism. Tags are
simple lowercase discovery slugs matching:

```text
^[a-z0-9]+(?:-[a-z0-9]+)*$
```

Use existing tag spellings when possible and add a tag only when the selected
content supports it. For example, `romance` is appropriate for an actual
romance, but it is not a CME00099 tag.

The CME00099 XML contains 31 source items: 26 prose-only, four verse-only, and
one mixed item. Its five encoded line groups contain 27 verse lines. The
record's whole form is therefore `mixed`, with Section I mixed and Section II
verse.

## Content parts

Content parts are a flat, referenceable summary rather than deeply nested JSON.
They can carry sequence, parent, type, item count, form, metrics, locators, and
evidence. CME00099 begins with three conceptual parts:

1. Holthausen's editorial frame and apparatus;
2. Section I, with 28 selections from X 90; and
3. Section II, with three charms from the manuscript dated 1597.

`content_structure_status` is `summary`; the system does not yet claim to have
31 separately researched work records.

## Lineage bindings

The `lineage` object binds metadata targets to stable entities in the lineage
manifest. For CME00099 it maps the cataloged selection to Holthausen's edition,
the U-M encoding, and the repository XML, and maps each section to its source
witness.

These are identity and scope bindings only. Derivation, access, reproduction,
and rights facts remain in the linked lineage record.

## Adding a work

1. Choose the cataloging unit deliberately; do not assume every repository file
   represents one historically independent work.
2. Add exactly one whole-record preferred title and whole-record form.
3. Separate anonymous authorship, attribution, and editorial responsibility.
4. Use scoped date and place assertions; identify witness dates as
   attestations.
5. Keep genre, subject, and tags distinct.
6. Add a content summary proportionate to the available research. Use
   `summary`, `partial`, or `unknown` rather than inventing item-level detail.
7. Link stable lineage entities instead of copying holdings, scans, access, or
   rights data.
8. Put unresolved composition dates, attributions, linguistic classifications,
   and regions in `open_questions`.
9. Add the record to `index.json`, update `coverage.manifest_count`, and run the
   validator and tests.

## Validation

The validator is offline and uses the repository's standard-library JSON
Schema subset implementation:

```bash
python3 scripts/validate-work-metadata-manifests.py
python3 -m unittest tests.test_work_metadata_manifests
```

It verifies:

- the committed JSON Schemas and exact `works/*.json` index coverage;
- unique IDs and resolvable evidence, agent, place, part, parent, and scope
  references;
- exactly one preferred whole title and one whole form;
- normalized date ordering and acyclic content-part parentage;
- agreement among content metrics, compact catalog fields, and index fields;
- safe repository paths, source checksums, and CME XML identifiers; and
- linked lineage work IDs, manifest IDs, entity IDs, and evidence IDs.

Remote links are not fetched during routine validation. Each web evidence
record carries its own `accessed_on` date for later review.
