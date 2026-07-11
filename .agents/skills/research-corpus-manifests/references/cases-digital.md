# Cases: digital encodings and structure

Read only for identifier-family differences, OCR/keying uncertainty,
typographic transformations, encoding counts, or multiple digital objects.

## Identifier families

Phase-3 CME XML commonly uses `IDG/@ID`, `BIBNO`, and `VID`; older
DLPSTEXTCLASS and OTA-derived files use `IDNO`; scanned books can extend a work
stem with dot- or colon-delimited volume IDs. Validate the source's actual
family and a structurally delimited case-insensitive extension. Never accept an
undelimited prefix such as `TroilusExtra` for `Troilus`.

## Typography is editorial data: CME00099 and Ayenbite

Italics can mark expanded abbreviations or supplied material rather than
emphasis. Ayenbite's XML explicitly loses the print edition's italics for
expansions. Trace brackets, italics, expansions, supplies, and omissions across
manuscript, edition, and encoding; normalized XML cannot reveal manuscript
letterforms by itself.

## Counts are representation metrics: Gawain and Pearl

XML `L`, `LG`, and division totals can differ from canonical line or stanza
counts because headings and grouping choices vary. State the counting method
and label totals as encoding metrics rather than properties of every edition.

## Planned, extant, and encoded extent: afw5744

The Ormulum's 242-item plan, material once composed but lost, surviving
autograph content, and 22 encoded body units are different quantities. Keep
planned, composed, extant, printed, and encoded extent separate.

## Duplicate digital objects: afw5744

Digital Bodleian exposes two Junius 1 objects, but only one has the complete
263-canvas sequence; another has two older images. Compare canvas/page count,
start/end coverage, and item metadata before calling an object a complete
facsimile.

## Generic production language versus item facts

A collection may describe manual keying and proofreading while one item says
uncorrected OCR/TEI Level 1. Prefer the item-specific production statement and
record the collection description only as broader context.

A complete page-image package can be a facsimile of an entire printed volume
while its associated OCR or TEI encodes only selected text. Scope the
facsimile relation to the whole edition and the encoding relation to the
actually transcribed pages; do not infer textual completeness from image
count alone.
