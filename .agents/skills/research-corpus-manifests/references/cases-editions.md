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

## Reprints: 3KCol, aba2096, and CME00022

An explicitly described reprint is still a distinct edition entity linked to
the earlier edition with scoped `version_of`. Verify the reprint's included and
omitted matter independently, and give any new cover, preliminaries, or terms a
separate rights analysis instead of inheriting every claim from the original.

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

A later society or series issue can reuse an earlier publication's printing
plates while adding a new title page, series statement, date, or preliminaries.
Model the plate-derived issue as a distinct immediate edition linked through
`version_of`; verify its retained and added matter independently rather than
skipping directly from the encoding to the manuscript or treating both issues
as one bibliographic object.

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

## Later transcript and indirect readings: afw5744

Van Vliet's partial seventeenth-century transcript preserves now-lost Ormulum
material but was not upstream of White or Holt. Some van Vliet readings reached
them through alterations in Junius 1 itself. Model the physical route of a
reading; do not promote a related transcript into an editorial source.

When an editor actually worked from a collaborator's transcript or collation
rather than the codex, preserve that material intermediary and its maker.
Model the edition as transcribing the working transcript and the transcript as
transcribing the codex; if it supplied variants only, use `collated_against`
at the appropriate link. Do not collapse the chain into a direct edition-to-
codex edge, and disclose any schema type used provisionally for the
intermediary.

A witness discovered or identified after an edition appeared belongs in the
broader tradition, not that edition's source chain, unless historical evidence
shows the editor actually knew and used it.

## Modern census expansion: CME00007

A current witness census can add several securely identified manuscripts to
the work's known tradition while the encoded historical edition used only two.
Record the census release itself as versioned evidence, create the additional
witnesses as collateral lineage entities, and keep edition-to-witness edges
limited to the editor's preface and apparatus. Do not let better modern
coverage retroactively turn collateral witnesses into sources of the encoded
readings.

## Roles in a retained-text edition

When an immediate source combines an earlier editor's retained text with a new
editor's correction, represent both responsibilities. A compact display can
name the primary editor or all editor agents; it must not make the new collator
look like sole creator of the retained transcription.
