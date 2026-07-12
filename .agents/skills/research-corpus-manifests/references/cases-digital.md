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

## Counts are representation metrics: Gawain, Pearl, and CME00039

XML `L`, `LG`, and division totals can differ from canonical line or stanza
counts because headings and grouping choices vary. State the counting method
and label totals as encoding metrics rather than properties of every edition.
Also separate intrinsic work lines from `L` or `LG` descendants inside notes,
headnotes, quotations, and apparatus. A raw `count(//L)` can equal a printed
headline while still hiding omitted base lines and inserted variant-only
lines; report both layers instead of letting apparatus determine work form or
extent.
If a scholarly 1,034-line extent coexists with 1,033 main-stream XML `L`
elements and dozens of apparatus `L` elements, preserve all three measurements
and open the one-line discrepancy. Do not manufacture the missing base line by
folding variant-only apparatus into the work text.
Apply the same hierarchy rule to prose or lexical items: count `ITEM` nodes
inside the textual body separately from administrative `TEMPHEAD`, header, or
workflow containers, and name the XPath or ancestor boundary used.

## Planned, extant, and encoded extent: afw5744

The Ormulum's 242-item plan, material once composed but lost, surviving
autograph content, and 22 encoded body units are different quantities. Keep
planned, composed, extant, printed, and encoded extent separate.

## Duplicate digital objects: afw5744

Digital Bodleian exposes two Junius 1 objects, but only one has the complete
263-canvas sequence; another has two older images. Compare canvas/page count,
start/end coverage, and item metadata before calling an object a complete
facsimile.

For IIIF Image API width requests, preserve the width-only comma in forms such
as `1800,`. A bare `1800` can be interpreted differently or redirected to the
native full image by some services. After retrieval, inspect the exact request
URLs recorded in the bundle inventory and sample actual image dimensions; do
not infer the effective profile from the command-line argument alone. A canvas
with no resizable image service may legitimately require its provider-supplied
`full` image, but record that per-canvas exception rather than silently treating
the whole bundle as one uniform profile.

## Generic production language versus item facts

A collection may describe manual keying and proofreading while one item says
uncorrected OCR/TEI Level 1. Prefer the item-specific production statement and
record the collection description only as broader context.

A complete page-image package can be a facsimile of an entire printed volume
while its associated OCR or TEI encodes only selected text. Scope the
facsimile relation to the whole edition and the encoding relation to the
actually transcribed pages; do not infer textual completeness from image
count alone.

Likewise, verify a header claim that “all material” was included against the
actual XML structure and the source volume. Indexes or plates may be absent,
and a surviving figure caption is not evidence that the corresponding image
was encoded.
