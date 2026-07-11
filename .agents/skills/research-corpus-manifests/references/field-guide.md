# General Corpus manifest research field guide

Use this guide after the skill's core workflow. It records source-selection
rules, schema-oriented decisions, and reusable lessons discovered while
cataloging actual corpus works.

## Contents

1. [Research packet](#research-packet)
2. [Source priority](#source-priority)
3. [Claim and layer model](#claim-and-layer-model)
4. [Descriptive field decisions](#descriptive-field-decisions)
5. [Lineage field decisions](#lineage-field-decisions)
6. [Rights and access](#rights-and-access)
7. [Evidence and confidence](#evidence-and-confidence)
8. [Review checklist](#review-checklist)
9. [Case lessons](#case-lessons)

## Research packet

Collect the following before drafting JSON:

```text
Identity
- repository work ID and exact source path
- internal XML identifiers
- proposed cataloging subject and why it is the right boundary

Immediate digital layer
- responsible institution or archive
- creation/publication date and named contributors
- availability and rights language
- declared omissions, transformations, and markup conventions

Immediate edition
- full title-page transcription or reliable catalog record
- editor/translator/compiler and publication facts
- edition statement, series, volumes, and included apparatus
- named base text, witness, collation, or editorial method

Witnesses and related sources
- current shelfmark, repository, date, origin/localization, contents
- exact role in this edition
- digitization/request routes and image terms, if known

Work description
- preferred and alternative titles
- creators and responsibility roles
- composition/translation/compilation date range
- region and dialect with the type of claim identified
- languages, prose/verse/mixed form, genres, subjects, tags
- content structure and concise abstract

Audit
- claim ledger with evidence and confidence
- unresolved questions
- local hashes and remote access dates
```

Useful local checks include:

```bash
rg --files CME/source | rg '/WORK_ID\.xml$'
rg -n '<TITLE|<AUTHOR|<EDITOR|<SOURCEDESC|<AVAILABILITY|<EDITORIALDECL|<LANGUAGE|<CLASSCODE' SOURCE.xml
sha256sum SOURCE.xml
git hash-object --no-filters SOURCE.xml
git -C CME rev-parse HEAD
```

Many CME files are minified onto one line. Limit or reshape diagnostic output;
do not mistake source line numbers for stable structural locators.

Scanned-book OCR may also carry automated or inherited TEI division labels
that do not describe the visible book accurately. Compare structural markup
with page milestones, headings, the scan, and surrounding text before using a
`DIV` type as intellectual structure. Record demonstrably misleading markup as
an encoding practice or open question rather than normalizing it silently.

## Source priority

Prefer sources in this order, using a lower tier to supplement rather than
override a higher one without explanation:

1. The repository XML and the immediate edition's title page, preface,
   colophon, apparatus, or facsimile.
2. The holding institution's manuscript catalogue and digital surrogate.
3. The digital collection's item record, project documentation, and
   item-specific rights statement.
4. A current scholarly edition/project, the Middle English Compendium
   bibliography, or a peer-reviewed/catalogued specialist resource.
5. National-library or research-library bibliographic records.
6. General reference works and aggregators as discovery leads.

Do not use unsourced retail descriptions, copied genealogy pages, AI summaries,
or a search snippet as final evidence. A modern scholarly source can interpret
date, dialect, genre, or textual relationships; label interpretation as such.

When authorities disagree, retain both claims with attribution and confidence.
Do not average dates or silently choose the most precise claim.

## Claim and layer model

Ask two questions for every fact:

1. Which object or intellectual unit does this describe?
2. Does the cited source directly support that scope?

Use at least these conceptual layers when present:

| Layer | Typical facts |
| --- | --- |
| Abstract/textual work | creator, title, composition, genre, subject |
| Version or translation | translator, source work, adaptation date, form |
| Compilation/selection | compiler/editor, chosen parts, organizing title |
| Manuscript witness | shelfmark, date, origin, scribe, folios, holding |
| Print edition | editor, publisher, date, base/collated witnesses, apparatus |
| Reproduction | scan/facsimile creator, extent, image format, terms |
| Electronic encoding | institution, date, source edition, transformations |
| Repository artifact | path, checksum, submodule commit, local derivation |

A physical manuscript can attest a text without fixing its original
composition date or place. A print publication place belongs to the edition,
not automatically to the medieval work. An encoding header can describe a
source edition without proving every claim made in that edition.

## Descriptive field decisions

### Identity, title, and responsibility

Define `cataloging_subject.scope_note` in contrast with nearby layers. Prefer a
title used by the work or established scholarship; retain the source edition's
long catalog title as an alternative when it is not the intellectual work's
preferred title.

Assign responsibilities rather than relying on a title page's MARC-style
`AUTHOR` label. A title-page contributor may actually be an editor. For a
translation, represent the source author and translator separately, and decide
which responsibility belongs in the human-readable summary based on the
cataloged unit.

When an immediate source combines an earlier editor's retained text with a new
editor's collation or revision, the compact editor display may name one primary
editor or describe the team, but a composite display must include every editor
agent represented at that layer.

### Dates

Keep these separate:

- event narrated or revelation experienced;
- work composed, translated, revised, or compiled;
- surviving witness copied;
- edition first issued or reissued;
- encoding created or distributed; and
- repository artifact pinned or reviewed.

Use a range and a qualified display string when scholarship supports only a
range. Put popular but unverified exact dates in an open question.

Keep an immediate source edition's issue date in its lineage entity unless it
is also genuinely the cataloged work's first publication. Do not label “the
edition used by this encoding appeared in 1984” as the medieval work's
`first_publication` or let that year dominate the work-date display.

For visionary, autobiographical, or documentary writing, a precisely dated
experience is not automatically the date of the surviving account. Create a
separate event assertion, then model each supported composition or revision
stage and each witness date independently.

### Places and language

Label place assertions as composition, translation, copying, dialect
localization, publication, or current holding. Region displays may summarize
several scoped facts but must not erase uncertainty.

Do not infer language solely from a collection name or modern title. Inspect
the text and language markup. Record embedded Latin, French, German, or other
material only at its supported scope.

### Form, genre, subject, and tags

`form` answers how the content is expressed: prose, verse, or mixed. Editorial
front matter does not necessarily change the form of the cataloged medieval
work; scope it as a part when needed.

Use whole-work `mixed` when prose and verse are both intentional, substantive
parts of the cataloged unit. Keep whole-work `prose` or `verse` when the other
form is only a brief quotation, rubric, source-language feature, or excluded
editorial apparatus, and record that exception at part or passage scope.

`genre` names a recognized textual category. `subject` states what the work is
about. `tags` provide normalized discovery terms. Do not use all three as
synonym lists, and do not tag material merely mentioned in an introduction.

Reuse one display label for the same normalized language code, genre term, or
subject term across the corpus. Put period, dialect, or work-specific nuance in
scoped assertions and notes rather than changing a shared facet label. The
viewer catalog rejects conflicting labels even when each manifest validates in
isolation.

### Structure and extent

Use divisions declared in the source and stable intellectual divisions from
the edition. Counts should be reproducible. If source markup is too coarse or
inconsistent, set `content_structure_status` to `summary` or `partial` and say
why. Do not create item-level records from visual impressions alone.

## Lineage field decisions

### Entities

Create a stable entity ID for each evidenced material or digital layer. Give a
repository artifact its exact file path and hashes. Give an encoding its stable
collection identifier. Give editions full bibliographic facts. Give witnesses
current shelfmarks and holding repositories, preserving superseded shelfmarks
as identifiers or notes when useful.

### Relations

Relations should say what was derived from what and at what scope. Model:

- direct transcription separately from collation or consultation;
- an eclectic edition against the witness tradition or named witnesses rather
  than inventing one base manuscript;
- selections from multiple witnesses with separate scoped edges;
- a reissue/reprint separately from the original edition when transformations
  differ; and
- later comparison sources without placing them upstream.

Wording such as “made available through,” “distributed by,” or a shared archive
identifier establishes association and distribution, not transformation
direction. Use `version_of` or a qualified relation until file comparison or
process documentation proves which encoding derived from which.

When the immediate edition does not explain its method, record only the known
edition-to-witness association and open a question about the exact derivation.

When the schema has no specific `reprint_of` or `revised_edition_of` relation,
use `version_of` and state the exact reissue, correction, revision, or reset
relationship in the scope notes and evidence. Do not erase meaningful edition
stages merely because they share a broad title.

A later transcript can preserve readings from leaves now lost from an extant
manuscript. Model the transcript, the manuscript's historical state, and the
lost material separately. Connect the transcript to the witness it copied, but
do not put it upstream of an immediate edition unless that edition explicitly
used it.

### Editorial practices

Record omissions, normalized spelling, supplied text, expansion of
abbreviations, retained brackets, excluded notes/front matter, OCR status,
page/folio milestones, and image links from the encoding declaration and
edition. Describe what the evidence states; do not infer a global practice from
one local example.

## Rights and access

Create separate records for each entity or component. At minimum, consider:

- medieval/early textual content;
- print edition and editorial apparatus;
- electronic transcription/markup;
- manuscript or book page images;
- local repository artifact; and
- provider contractual terms.

Record the institution's label and statement, not a stronger legal conclusion.
“Public domain in the United States” is jurisdiction-specific. “Available
online” is access, not a license. A digital facsimile can have provider terms
even when the depicted manuscript is ancient. Date checks of missing,
restricted, request-only, or purchase-only access.

Test the exact deliverable, not only the item page. A public catalog can list
or preview files whose bitstreams require login or remain unavailable. Record
catalog visibility, preview, download, and authenticated access separately,
and do not call a file publicly downloadable until a retrieval succeeds.

Do not generalize an image license from a representative page to an entire
collection. Cite the exact image record proposed for reuse or leave the
collection-wide status unknown and open a question.

If local XML contains a restrictive legacy availability paragraph while the
current item page states public-domain status, record both as scoped,
time-stamped evidence and explain the mismatch. Do not silently discard either.

## Evidence and confidence

Each evidence record should let another researcher answer:

- What source was consulted?
- Where is it?
- When was it consulted?
- What exact kind of fact does it support?
- Is it primary, institutional, or scholarly interpretation?

Link a holding to an item-level record when one is verified. A collection-level
record, repository home page, or discovery portal can support an enquiry route
but must not masquerade as the catalogue record or image terms for one exact
shelfmark. Test URLs during substantive review and replace dead legacy paths
with current official access/contact pages.

Use `high` confidence for direct self-identification, title-page facts,
institutional shelfmarks, and explicit editorial statements. Use lower
confidence for scholarly reconstruction, approximate localization, inferred
relationships, and conflicting catalog data. Confidence is not a substitute
for explaining the uncertainty.

Resolve every evidence ID, entity ID, agent ID, place ID, part ID, lineage
binding, and `supports` target. Bind metadata records only to entities and
evidence that exist in the linked lineage manifest.

For metadata assertions, `part` and `selected_passages` scopes must name the
modeled `part_ids`; a free-text scope description is not a substitute. Preserve
the detailed-record order when copying language, genre, or tag arrays into the
compact catalog summary and index.

## Review checklist

Before indexing a pair, verify:

- the source XML path, SHA-256, Git blob, and internal ID;
- one preferred whole title and whole form;
- catalog summary values exactly match detailed records;
- authors, translators, editors, scribes, and encoders are not conflated;
- composition, witness, publication, and encoding dates are distinct;
- region is not inferred from publisher or current holding;
- form, genre, subject, and tags have different jobs;
- every lineage edge has the correct direction and scope;
- witness shelfmarks and repositories are current and evidenced;
- rights and access attach to the correct entity and date;
- negative claims and unverified precision are in open questions;
- index entries are derived from manifests; and
- all offline validators, tests, and the viewer catalog pass.

## Case lessons

Keep this section compact and add only generalizable discoveries.

### CME00099: edited selections can branch across witnesses

[`manifests/work-metadata/works/CME00099.json`](../../../../manifests/work-metadata/works/CME00099.json)
catalogs Holthausen's selected and organized content rather than pretending it
is one medieval work or one manuscript. Its linked
[`lineage manifest`](../../../../manifests/lineage/works/CME00099.json) gives
the two manuscript sources separate entities and scoped derivation edges.

Reusable rule: when sections derive from different witnesses, make the
cataloging boundary explicit, scope metadata to the section when necessary,
and branch the lineage graph. Do not assign the whole selection one witness's
date, dialect, or rights status.

### CME00099: typography can encode editorial intervention

The XML and immediate edition show that italics can represent expanded or
supplied material rather than emphasis. The visual manuscript question cannot
be answered from normalized XML typography alone.

Reusable rule: trace italics, brackets, supplied elements, abbreviation
expansion, and omissions through the encoding declaration, print edition, and
facsimile. Describe each layer's convention separately.

### CME00099: access and permission are not one fact

The public U-M text, an old print edition, manuscript photography, and a newly
ordered institutional facsimile have different access routes and terms.

Reusable rule: never propagate one layer's public-domain or availability
statement to another layer. Record request routes even when redistribution
permission remains unknown.

### CME source families use different identifier conventions

CME00099's Phase-3 XML identifies itself through `IDG/@ID`, `BIBNO`, and
`VID`. Older DLPSTEXTCLASS and OTA-derived files commonly use `IDNO` instead,
and a scanned-book identifier can extend the work stem with dot-delimited
volume identifiers.

Reusable rule: inspect the source's actual identifier family. Validate an
exact identifier or a case-insensitive, structurally delimited extension; do
not require one XML dialect globally and do not accept an undelimited prefix
match.

### Troilus: an eclectic edition is not one witness

[`Troilus`](../../../../manifests/lineage/works/Troilus.json) records
Windeatt's edition against an aggregate manuscript tradition and separately
describes representative witnesses. It does not invent a universal base
manuscript or assign one witness's dialect to the poem.

Reusable rule: when an edition collates a tradition, model the aggregate
relationship until the edition's reading-level dependencies are verified.
Keep the exact witness list and editorial principles as an open research task.

### ChaucerBo: bibliographic labels do not determine roles or form

[`ChaucerBo`](../../../../manifests/work-metadata/works/ChaucerBo.json)
separates Boethius as source author, Chaucer as Middle English
translator/adapter, and Morris as editor, transcriber, and collator. Chaucer's
translation remains prose even though its Latin source alternates prose and
metres and the edition package contains verse-related apparatus.

Reusable rule: derive responsibility from the intellectual relationship, not
an inherited `AUTHOR` field. Determine form for the cataloged unit and scope
surrounding editorial or source-work forms separately.

### ChaucerAstr: parts can have different witnesses and attribution status

[`ChaucerAstr`](../../../../manifests/lineage/works/ChaucerAstr.json) maps
section ranges to the witnesses named by the encoding and distinguishes the
Chaucerian core from supplementary conclusions whose authorship is disputed.

Reusable rule: give content parts stable IDs before assigning part-level
languages, responsibilities, dates, or witness relations. Do not let a
whole-work attribution erase a supplementary part's uncertainty.

### A provider label can conflict with an edition's likely rights

The current U-M page for `Troilus` labels its presented item public domain,
while the keyed source is a 1984 critical edition and the legacy OTA header
limits use to personal scholarship.

Reusable rule: record each statement with its source, date, entity, component,
and jurisdiction. Preserve the conflict and ask the provider about permission;
do not resolve it by choosing the most permissive label.

### Gawain and Pearl: one codex does not make one work

[`Gawain`](../../../../manifests/lineage/works/Gawain.json) and
[`Pearl`](../../../../manifests/lineage/works/Pearl.json) occupy the same
British Library codex but remain distinct intellectual works with different
folio ranges. Legacy XML foliation and the current catalogue's part-level
designation are both useful and not always formatted alike.

Reusable rule: identify the physical codex once per work graph, scope each
work-to-witness relation to its folios, and preserve historical or legacy
locators alongside the current shelfmark rather than forcing false agreement.

### Gawain and Pearl: encoding counts are not canonical line counts

XML `L` and `LG` totals can differ from an edition's or scholarship's verse
count because headings, embedded material, grouping, or encoding choices are
counted differently. Legacy headers can also omit later revisers or blur the
roles of OTA and U-M.

Reusable rule: label machine-derived totals as encoding metrics and cite the
counting method. Corroborate inherited headers against the edition and current
institutional records before turning their contributor or transfer history
into a confirmed claim.

### HMaid: parallel texts can represent one intellectual work

[`HMaid`](../../../../manifests/lineage/works/HMaid.json) descends from an
edition that prints Bodley 34 and Cotton Titus D XVIII in parallel. The two
witnesses have different dates, readings, and access routes but do not become
two authored works merely because both are encoded.

Reusable rule: catalog the shared intellectual work once, create separate
witness entities, and scope edition-to-witness relations and witness-specific
metadata. Keep editor, prior editor, and medieval anonymous author distinct.

### A facsimile catalog record is not facsimile access

For `AllitMA` and `HMaid`, library records confirm that print facsimiles exist,
while the manuscript repositories' current pages do not establish a free full
digital facsimile. A catalogue, selected image, mediated-copying service, and
complete online facsimile are different access states.

Reusable rule: record what can actually be opened, requested, or purchased.
Do not convert bibliographic proof that a reproduction exists into a claim
that its images are publicly downloadable or reusable.

### Ayenbite: a corrected reissue has two editorial dependencies

Gradon's 1965 volume retains Morris's 1866 transcription but newly collates
and corrects it against Arundel MS 57. The XML also drops the italics that
marked expanded abbreviations in print. The BL's work-level child record, not
the codex summary alone, fixes Ayenbite's endpoint before adjacent prayers and
treatises.

Reusable rule: model the reissue as a version of the earlier edition and add a
separate collation edge to the witness. Record typographic information loss;
do not infer manuscript characters from a normalized electronic form. Use the
exact component record for folio boundaries and do not absorb neighboring
codex contents into the work.

### JulianRev: narrated event, composition, and copy date differ

Julian's visions are dated to 1373, while the Long Text was composed or revised
later and the explicit base witness was copied around 1650. Its direct IIIF
manifest also supplies a rights assertion qualified by jurisdiction that is
more precise than the surrounding viewer page.

Reusable rule: distinguish the dated experience from the work's composition
and every witness's production. Identify Long and Short Text versions before
assigning dates, witnesses, structure, or a preferred title. Inspect IIIF
metadata directly and preserve geographic limits instead of restating a
provider's public-domain label as worldwide permission.

### OTA item visibility does not prove anonymous file access

The OTA records reviewed for `AllitMA` and `Pearl` expose metadata, file names,
previews, and license labels while their bitstreams disallow anonymous access
and download-all routes redirect to login.

Reusable rule: model the license assertion and practical access separately.
Use `registration_required` or `unknown` until the exact file is retrieved,
and preserve the observed redirect or denial in the evidence summary.

### afw5744: verify completeness and indirect transmission

Two Digital Bodleian objects describe Junius 1, but only the 263-canvas object
is complete. Van Vliet's later partial transcript preserves material now lost,
while some of his readings reached White and Holt through annotations made in
the principal manuscript rather than through that separate transcript.

Reusable rule: compare object extent before linking a “facsimile,” and model
the physical route by which a reading traveled. Keep a work's planned units,
material once composed but now lost, extant witness content, and encoded units
as distinct quantities.
