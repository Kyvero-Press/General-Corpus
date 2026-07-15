# Cases: digital encodings and structure

Read only for identifier-family differences, OCR/keying uncertainty,
typographic transformations, encoding counts, or multiple digital objects.

## Identifier families

Phase-3 CME XML commonly uses `IDG/@ID`, `BIBNO`, and `VID`; older
DLPSTEXTCLASS and OTA-derived files use `IDNO`; a scanned-book identifier or a
publication work ID can extend the other's stem with a dot- or colon-delimited
volume, version, or presentation qualifier. Validate the source's actual
family and accept the extension in either direction only at that structural
delimiter. Never accept an undelimited prefix such as `TroilusExtra` for
`Troilus`.
Repaired headers can legitimately mix identifier schemes: an item-level
`IDNO` or `VID` may identify the current CME publication while `BIBNO` retains
an upstream OTA number, or a current short ID may coexist with a zero-padded
legacy CME handle. Treat those values as explicit aliases. Require at least one
recognized identifier to match the work ID exactly or by the permitted
delimiter rule, but do not require every identifier family to match and do not
invent a general zero-stripping heuristic. Prefer `VID`, then `IDNO`, then
`IDG/@ID`, when constructing a U-M resolver URL from the source itself.

DIMEV's live `recID` is the DIMEV record number encoded in identifiers such as
`record-2973`; it is not necessarily the same as an IMEV or NIMEV number cited
inside that record. Verify all three fields in the versioned data before
building a URL. A substituted IMEV/NIMEV number can resolve successfully to a
different, unrelated DIMEV record and therefore evade a simple HTTP check.

When a pinned and current XML file differ in wrappers, headers, comments,
stylesheets, or rights metadata, canonicalize and compare the actual textual
subtree before declaring a new content version. Keep a newer item-level rights
statement attached to its own distribution even when the encoded body is
identical.

An archive item's inherited `sourceDesc` can conflict with its deposited
text's title page, edition statement, creator/depositor record, or explicit
`isVersionOf` link. Inspect both the metadata wrapper and the actual payload.
Preserve the archive-confirmed version relation, but qualify any source-edition
relation whose only contradictory support is the inherited `sourceDesc`; expose
the conflict as an open question instead of silently choosing one statement.

## Hidden headers in migrated archives

A repository migration can leave a TEI deposit header reachable as a direct
bitstream while omitting it from the current landing page and `allzip`
download. Check the predecessor handle namespace, the current namespace, and
the exact bitstream sequences. Cache the header separately from the advertised
data bundle, and retain both landing-page and direct-file URLs. In DSpace-style
routes the sequence selects the bitstream; a plausible filename is not enough
to establish that the returned bytes are the intended file.

Hash current and legacy endpoints before treating them as aliases. If they are
byte-identical, one local copy can cite both verified routes. If migration has
changed the header, preserve each state under a distinct name, checksum, and
source URL. A migrated header may drop the depositor, deposit date, identifiers,
or revision history and can even become malformed through unmatched elements;
do not replace a fuller valid legacy record with that damaged state merely
because its namespace is newer. Use the current landing as the active access
route while citing the exact header state that supports each provenance claim.

Finally, test catalog dates against the payload and source edition. Embedded
machine trailers can establish that a file passed through a system on a given
date, but they are processing evidence rather than an automatic deposit date.
Record unresolved contradictions instead of forcing a chronology. Keep the
archive's license on the deposited digital resource; it does not flow upstream
to the source edition, witness, or historical work.

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
When an edition numbers a blank, dotted, or otherwise contentless row as a
missing line, distinguish numbered line positions from positions containing
verbal text. Likewise, keep any post-explicit saying or scribal tag separate
from the preceding work even when the encoding places every row in one `LG`.
Across encoding generations, also inspect line-like text outside `L`, headings
moved into or out of `L`, duplicates later replaced by empty nodes,
lacuna-marker rows, and supplied or omitted terminal lines. Report each
version's raw tagged count, conventional numbered positions, and positions
containing verbal text separately. Name observed repairs, but use `version_of`
and leave their direction, date, and authorship unassigned unless production
evidence establishes them.
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

Image-object availability can change. A current official catalog TEI record
may link a newly published complete IIIF object while an older slide selection
remains discoverable. Model both digital objects separately, re-audit their
inventories and work overlap, and retire the dated whole-object negative; never
let the older partial selection conceal or stand in for the newer complete
surrogate.

LUNA searches can mix `mediaType: Image` records with compound `mediaType:
Book` records. Audit the complete result set by media type and open every Book
manifest; an image-only loop can capture dozens of single folios while silently
missing multi-canvas published selections. Model distinct compound Books as
separate facsimile objects, cache every canvas of each published object, and
state both selection-level completeness and physical-manuscript partiality.
Do not infer that a named provider ZIP exists from a Book descriptor: verify
that any archive response is nonempty and valid, and otherwise use an audited
IIIF bundle with the exact manifest and image requests preserved.

Conversely, two live Presentation-manifest URLs can be alternate records for
the same published image object. Compare every canvas ID, Image API service ID,
sequence order, license, attribution, and effective request profile. When those
are identical, preserve both exact manifest URLs but cache the images only once
and record which manifest supplied the bundle. Treat them as separate digital
objects if their inventories, order, rights, or attribution differ; matching
canvas counts alone are not enough.

A viewer's page or slot count is not necessarily a count of unique manuscript
images. Parallel transcription panes can repeat one full-folio JPEG in several
left/right slots, and separately paginated sequences can overlap. Compare
canvas or slot identifiers, image-service URLs, order, and image fixity across
every sequence. Record both the published slot count and the deduplicated image
inventory, name overlaps and repetitions, and never infer physical coverage
from the larger number alone.

A provider-generated PDF can add a cover or metadata page that is absent from
the IIIF canvas sequence. Compare total PDF pages with manifest canvases and
inspect the first, target, and last pages before mapping them. When an offset
exists, record both the exact canvas range and the shifted PDF-page range,
state which generated pages cause the offset, and describe coverage at both
levels; never assume canvas number *n* equals PDF page *n*.

For IIIF Image API width requests, preserve the width-only comma in forms such
as `1800,`. A bare `1800` can be interpreted differently or redirected to the
native full image by some services. After retrieval, inspect the exact request
URLs recorded in the bundle inventory and sample actual image dimensions; do
not infer the effective profile from the command-line argument alone. A canvas
with no resizable image service may legitimately require its provider-supplied
`full` image, but record that per-canvas exception rather than silently treating
the whole bundle as one uniform profile.

An official Presentation 2 document can be structurally nonconforming—for
example, placing Canvas objects directly in `sequences` instead of under one
Sequence's `canvases`. Preserve the exact provider document, enumerate every
official canvas/image resource into one `image_url_inventory` bundle when the
normal parser cannot consume it, and verify count, first/target/last mappings,
request profiles, image dimensions, and ZIP integrity. Malformed structure is
not permission to discard surrounding leaves or cache only the target range.

An exact provider manifest may survive only in a dated web archive while the
provider's Image API resources remain live. In that case, model the archived
Presentation document, the current manifest failure, and the live image
delivery as separate dated facts. A complete private bundle may be reconstructed
from the archived official inventory only after every listed image is retrieved
and count, order, target boundaries, first/last surfaces, fixity, and archive
integrity are checked. Keep the archived manifest URL as the bundle source and
the live image URLs in its inventory; do not imply that the current manifest
endpoint works merely because the images do. Re-audit current rights statements
separately from any license wording preserved in the archived manifest.

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

When XML page-reference numbering jumps inside an edition, inspect every
intervening surface in the complete scan. The gap may represent unpaginated
plate leaves and their blank backs rather than omitted numbered text. Map each
surface, retain the complete carrier volume, and model manuscript plates as
partial reproduction objects separate from the encoded textual selection;
complete capture of an article's plates is not a complete manuscript facsimile.
