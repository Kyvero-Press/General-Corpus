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

## Unchanged reprint: 3KCol

An explicitly described reprint is still a distinct edition entity linked to
the earlier edition with scoped `version_of`. Verify the reprint's included and
omitted matter independently, and give any new cover, preliminaries, or terms a
separate rights analysis instead of inheriting every claim from the original.

## Later transcript and indirect readings: afw5744

Van Vliet's partial seventeenth-century transcript preserves now-lost Ormulum
material but was not upstream of White or Holt. Some van Vliet readings reached
them through alterations in Junius 1 itself. Model the physical route of a
reading; do not promote a related transcript into an editorial source.

A witness discovered or identified after an edition appeared belongs in the
broader tradition, not that edition's source chain, unless historical evidence
shows the editor actually knew and used it.

## Roles in a retained-text edition

When an immediate source combines an earlier editor's retained text with a new
editor's correction, represent both responsibilities. A compact display can
name the primary editor or all editor agents; it must not make the new collator
look like sole creator of the retained transcription.
