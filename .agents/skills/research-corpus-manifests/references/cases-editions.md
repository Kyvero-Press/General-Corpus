# Cases: editions, roles, and transmission

Read only for eclectic editions, retained prior texts, confusing contributor
labels, reissues, later transcripts, or indirect transmission.

## Eclectic edition: Troilus

Windeatt collates a manuscript tradition rather than following one universal
base witness. Model the aggregate tradition and representative witnesses until
reading-level dependencies are verified. Do not transfer one witness's dialect
or date to the poem.

When an eclectic edition's dependency is explicit, go beyond one aggregate
edge: scope separate `transcribes` relations for the principal base and any
supplied passages, then add `collated_against` edges for variant witnesses.
A title page or editorial headline saying “printed from” one manuscript is
only a summary claim: inspect the notes for continuous supplied spans and
isolated borrowed readings. Give continuous supplies their own exact
`transcribes` scopes, while isolated readings remain `collated_against`.

If foreign-language witnesses were consulted only for notes or specimens,
scope their `collated_against` relations to that apparatus. They are not base
witnesses or intrinsic parallel parts of the cataloged work.

An editor can describe or examine a manuscript without using any of its
readings. If the apparatus never cites that witness's siglum or a supplied
reading, record `consulted`, not `collated_against`; similarity of arrangement
to a base witness is not evidence of collation.

When an editor states that an independent manuscript transcript predates a
prior edition, connect the prior edition with `consulted` at the supported
scope. Do not make it the transcription source merely because it influenced
later discussion or selected emendations.

Conversely, a separately printed manuscript specimen inside an edition does
not make that manuscript the base of the edition's continuous text. Model the
specimen with its own narrow `transcribes` scope, then establish the main text's
actual base edition or witness independently. An electronic selection ending
at the same boundary as the manuscript specimen or fragment is not evidence
that all selected text was keyed from that manuscript.

## Source author versus translator: ChaucerBo

Separate Boethius as source author, Chaucer as Middle English translator and
adapter, and Morris as editor/collator. Determine form for Chaucer's cataloged
translation, not for the Latin source or surrounding apparatus. Inherited
bibliographic `AUTHOR` labels do not decide intellectual roles.

## Corrected reissue: Ayenbite

Gradon's 1965 volume retains Morris's 1866 transcription and newly collates it
against Arundel 57. Model `version_of` the prior edition plus a distinct
`collated_against` witness edge. Do not describe the 1965 edition date as a
revision date of the medieval work.

Reading or correcting proof sheets against a manuscript likewise establishes
collation, not necessarily a fresh continuous transcription. When the editor
retains a prior edition as the textual base, preserve both relations and use
`transcribes` only if the method statement independently supports it.

## Reprints: 3KCol, aba2096, and CME00022

An explicitly described reprint is still a distinct edition entity linked to
the earlier edition with scoped `version_of`. Verify the reprint's included and
omitted matter independently, and give any new cover, preliminaries, or terms a
separate rights analysis instead of inheriting every claim from the original.

A current publisher or learned-society backlist entry can establish that a
title is purchasable without identifying the sold carrier with the historical
issue named by an encoding. Model the current paperback, print-on-demand copy,
or other offered carrier separately; record its ISBN, price, and purchase route,
but leave its printing ancestry, collation, and carrier-specific rights
unverified until a copy or explicit publisher statement establishes them.

When a revised reissue changes the membership or numbering of an edited
selection, a complete scan of the prior edition is not complete coverage of the
immediate source. Keep the scan's source-object coverage complete, but scope its
`work_portion` to the overlapping prior-version material and name additions,
omissions, splits, mergers, and renumbering explicitly. Never map a newly added
item onto the earlier pagination merely because the collection title persisted.

Do not call a reset reprint a facsimile merely because it reproduces an earlier
title page or retains the text. Compare type, pagination, preliminaries, and
printing colophons to establish the reset and its edition-specific scope.
When an encoding includes the inherited old title page but also an interior
later-printer colophon, attach the encoding to the reset reprint and connect
the old edition through `version_of`; do not let the title-page imprint erase
the immediate physical source.

Repository metadata can also conflate companion parts, notes volumes, and
later photographic or lithographic reprints. Inspect each scan's internal
title page and verso, printed pagination, contents, and opening/closing matter
before assigning it to the encoding. Model a companion notes volume or later
reprint as its own entity even when the repository title and author strings
make the objects look interchangeable.

## Complete work inside an unfinished publication plan

A volume labeled `Part I` can still contain the complete intellectual work
when a projected later part was limited to an introduction, facsimiles,
glossary, notes, or other apparatus. Verify the text's opening and ending,
contents, colophon, and contemporary publication plans independently. Preserve
the part label as bibliographic evidence, but model textual completeness and
publication-package completeness separately; do not report a missing narrative
continuation merely because the apparatus plan was never completed.

A later society or series issue can reuse an earlier publication's printing
plates while adding a new title page, series statement, date, or preliminaries.
Model the plate-derived issue as a distinct immediate edition linked through
`version_of`; verify its retained and added matter independently rather than
skipping directly from the encoding to the manuscript or treating both issues
as one bibliographic object. A dated correction notice retained in a later
carrier can expose an otherwise easy-to-miss intermediate plate issue; verify
that issue against an independent bibliographic record. If the later carrier
preserves the notice and its named additions but has not itself been inspected,
record descent through that issue as supported rather than confirmed.

## Recurring serial installments

When one editor publishes several installments under a recurring title in
different journal issues or years, model each independently published article
as its own scholarly-edition entity. Scope the encoding to the exact selected
pages in each installment; a shared series title does not turn the articles
into one homogeneous edition object.

## Separately issued matter later bound together: CME00018

A text, introduction, notes, or glossary can be issued in different years and
later appear inside one bound scan. Model the dated issues and the later bound
reproduction separately, then scope the encoding to the matter it actually
includes. Do not assign the bound object's broad date range to every component
or infer that a single present-day PDF proves simultaneous first publication.

When separately issued appendices or plate sets remain movable when later
bound, do not infer intellectual issue order from one carrier's leaf order.
Establish issue order from wrappers, part title pages, contents notices, or
unbound sets, and record each inspected binding's physical sequence separately.
A bound copy can place appendices or plates earlier or later without changing
their publication relationship.

## Later transcript and indirect readings: afw5744

Van Vliet's partial seventeenth-century transcript preserves now-lost Ormulum
material but was not upstream of White or Holt. Some van Vliet readings reached
them through alterations in Junius 1 itself. Model the physical route of a
reading; do not promote a related transcript into an editorial source.

Likewise, a thesis or edition that later prints and studies a machine-readable
transcription cannot be the source of an earlier archive deposit. Keep the
deposit date, the later title-page date, and any still later repository issue
date distinct. Bind the later publication as a `related_source` unless direct
comparison or project documentation proves a revision or version relation;
shared title, witness, author, and line count alone do not establish the exact
file history.

When an editor actually worked from a collaborator's transcript or collation
rather than the codex, preserve that material intermediary and its maker.
Model the edition as transcribing the working transcript and the transcript as
transcribing the codex; if it supplied variants only, use `collated_against`
at the appropriate link. Do not collapse the chain into a direct edition-to-
codex edge, and disclose any schema type used provisionally for the
intermediary.

Under the current entity vocabulary, use `manuscript_witness` provisionally
for a material handwritten working transcript when no dedicated transcript
type exists; `repository_artifact` is reserved for a project-held repository
file, not an unlocated historical research carrier. State explicitly that the
transcript is modern rather than a medieval witness, identify its maker and
function, and keep its location and survival status unknown unless evidenced.

When one source statement credits the same collaborator with copies of several
sigla, one aggregate working-copy entity can keep the graph manageable only if
separate scoped `transcribes` relations preserve every copy-to-witness mapping.
Connect the edition to that intermediary and remove parallel direct edition-
to-codex edges; keeping both paths would falsely imply independent autopsy.

When acknowledgements instead name several suppliers and several witnesses but
do not map people to sigla, do not manufacture person-to-witness assignments or
one material transcript for each person. At most, use a provisional aggregate
description for the evidenced class of working transcripts or collations, join
it collectively to the supported witness scopes, and state that its membership,
survival, holdings, and individual supplier mappings remain unknown. Such an
aggregate is an editorial intermediary model, not a newly discovered object,
and it receives no physical holding or access route without further evidence.

A passive statement that a collaborator's transcript “was compared with the
original” supports edition-level collation, but not the identity of the
collator. It also does not prove that the transcript's source photographs
covered the complete physical object; keep both questions explicit.

A witness discovered or identified after an edition appeared belongs in the
broader tradition, not that edition's source chain, unless historical evidence
shows the editor actually knew and used it.

When an encoding takes its continuous readings from one witness or edition but
imports page milestones from another, keep those functions separate. Use
`encoded_from` for the textual base and a narrowly scoped `consulted` relation
for the pagination source; matching page breaks do not make that second source
the blanket source of the encoded wording.

## Modern census expansion: CME00007

A current witness census can add several securely identified manuscripts to
the work's known tradition while the encoded historical edition used only two.
Record the census release itself as versioned evidence, create the additional
witnesses as collateral lineage entities, and keep edition-to-witness edges
limited to the editor's preface and apparatus. Do not let better modern
coverage retroactively turn collateral witnesses into sources of the encoded
readings.

## Repertory occurrences versus physical witnesses: CME00142

Do not report a repertory's active occurrence-row count as a physical-witness
count. One codex can contain two separately indexed copies of the same work:
retain one physical witness entity, add one scoped `describes` relation for
each occurrence and locator, and state both totals explicitly. Conversely,
exclude ghost, commented-out, deleted, or otherwise inactive rows from an
active-occurrence total; preserve them as attributed catalog history or an
open reconciliation question when they may explain older scholarship.

Keep a modern repertory census collateral to the historical edition unless
the editor demonstrably used those witnesses. If an occurrence locator is
malformed, retain the exact source expression, flag the defect, and do not
silently repair it without manuscript-specific evidence.

## Roles in a retained-text edition

When an immediate source combines an earlier editor's retained text with a new
editor's correction, represent both responsibilities. A compact display can
name the primary editor or all editor agents; it must not make the new collator
look like sole creator of the retained transcription.
