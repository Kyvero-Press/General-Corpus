# Cases: access and rights

Read only for provider conflicts, facsimiles, restricted downloads, image
terms, or jurisdiction-qualified assertions.

## Access and permission are separate: CME00099

A public U-M text, old print edition, manuscript, microfilm, and newly supplied
facsimile have different access and reuse layers. Record request routes even
when redistribution permission remains unresolved; never propagate one
layer's status to another.

## Conflicting provider and edition signals: Troilus

U-M labels its item No Copyright–United States while the keyed source is a
1984 critical edition and legacy text limits use to personal scholarship.
Preserve every statement with source, date, entity, component, and
jurisdiction. Ask the provider; do not choose the most permissive label.

## Cataloged facsimile is not image access: AllitMA and HMaid

A library record can prove that a printed facsimile exists without proving a
free online copy. Distinguish catalog, selected image, mediated copying,
purchase, and complete public facsimile. Verify what can actually be opened.

A second repository's microfilm can be the best known scholarly reproduction
route even when the holding library has no public images. Model it as a
facsimile with its own request/access and rights records, outside the upstream
textual chain. If a collection finding aid says its reels reproduce
manuscripts “in full or in part” but does not identify this reel's extent,
record coverage as unknown until the reel or an institutional answer is
checked.

## Complete edition, partial manuscript image: CME00006

One cached PDF can be complete relative to its printed edition while the
edition's frontispiece reproduces only one leaf of a manuscript. Keep the
complete edition scan and its work-page mapping, but create a separately
scoped manuscript-image access record with `coverage=partial` and the exact
folio. Never let file-level completeness imply whole-codex coverage across a
different entity layer.

## Public item page, restricted bitstream: AllitMA and Pearl

OTA item records expose metadata, file names, previews, and CC labels while
bitstreams deny anonymous access and download-all redirects to login. Model
license assertion separately from practical access. Use
`registration_required` or `unknown` until retrieval succeeds.

## Public viewer with explicit no-download terms: CME00009

A public image viewer can expose technically retrievable files while its
item-specific terms expressly prohibit downloading. Record the selected
view-only coverage, exact terms, and negative whole-object status, but do not
cache those images. Technical reachability does not override an explicit
provider restriction; pursue a repository-supplied whole-codex copy through
the recorded request route instead.

## Direct IIIF rights: JulianRev

The Sloane 2499 IIIF manifest states public domain in most countries other than
the UK. Record the provider's geographic qualification, preserve UK
uncertainty separately, and link its reuse terms. Do not restate the assertion
as a worldwide open license.

## Representative-image trap: Gawain and Pearl

A sampled Calgary image carries a public-domain label alongside enumerated use
categories. Do not generalize it across the collection or to commercial reuse.
Use exact image records and leave collection-wide status unknown if necessary.

## Conflicting derivative-provider claims: Purity

When one repository republishes another provider's derivative and applies a
public-domain label that conflicts with the source provider's license or use
conditions, preserve both as access-specific claims. Provenance does not make
the more permissive claim automatically control the upstream images, nor does
the upstream restriction erase what the downstream provider actually asserts.

An item-level IIIF license and a provider-wide publication or permission
policy may also address different acts. Record the exact object's license and
the institution's broader reproduction/publication conditions separately;
neither silently cancels the other when their practical permissions diverge.
