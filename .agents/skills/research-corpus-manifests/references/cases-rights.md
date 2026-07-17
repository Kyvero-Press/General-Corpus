# Cases: access and rights

Read only for provider conflicts, facsimiles, restricted downloads, image
terms, or jurisdiction-qualified assertions.

## Access and permission are separate: CME00099

A public U-M text, old print edition, manuscript, microfilm, and newly supplied
facsimile have different access and reuse layers. Record request routes even
when redistribution permission remains unresolved; never propagate one
layer's status to another.

## Restricted originals and substitute microfilm: EEWills

When an exact archive record marks the original unavailable but directs users
to microfilm, create separate access records for the restricted original and
the substitute surrogate; do not describe the original as normally orderable
onsite. If item-detail URLs are session-bound, cite the stable catalog entry
point together with the exact reference and any persistent internal record
number, and tell researchers how to reproduce the search.

## Conflicting provider and edition signals: Troilus

U-M labels its item No Copyright–United States while the keyed source is a
1984 critical edition and legacy text limits use to personal scholarship.
Preserve every statement with source, date, entity, component, and
jurisdiction. Ask the provider; do not choose the most permissive label.

## Cataloged facsimile is not image access: AllitMA and HMaid

A library record can prove that a printed facsimile exists without proving a
free online copy. Distinguish catalog, selected image, mediated copying,
purchase, and complete public facsimile. Verify what can actually be opened.
Likewise, a DOI or DataCite record whose description says “digitized version”
is still `metadata_only` when it exposes no content URL, rights statement,
manifest, or auditable image inventory. Cache the structured record if useful,
but do not create a facsimile entity merely because the landing page belongs
to a digital-collections repository.
Generic Mirador or IIIF interface chrome can also render on a discovery page
that explicitly has no digital object. Require a resolvable Presentation
manifest with canvases, an image inventory, or an item-specific institutional
digital-content link before recording the manuscript as digitized.
A generic legacy “digital images” link whose inventory cannot be audited proves
at most unknown-extent image access. Do not infer cover-to-cover coverage or
bypass CAPTCHA, login, or human-verification controls to enumerate it; retain
the catalog claim, record the uncertainty, and use the provider's enquiry or
reproduction route.

Keep the rights for a mediated reproduction route separate from the rights in
the underlying historical text. The witness's medieval wording can be public
domain while any photography supplied after an order remains item-specific
and subject to provider terms. Leave the textual-content right entity-scoped
or attached to a genuine textual/catalog access, and create a distinct
access-layer right for the order route with unknown image status, the exact
provider evidence, and no inferred grant or availability. Omit an unverified
optional contact instead of storing `null` or inventing an address.

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

## Complete viewer with no systematic extraction: CME00025

A provider can expose every manuscript image for private viewing while its
terms prohibit systematic extraction or reuse of a substantial portion. Record
the complete viewer, exact work folios/images, and terms, but do not turn the
public sequence into a local bulk bundle merely because every request is
technically reachable. Use the repository's authorized reproduction route for
a retained complete copy and keep separately permitted printed plates partial.

## Direct IIIF rights: JulianRev

The Sloane 2499 IIIF manifest states public domain in most countries other than
the UK. Record the provider's geographic qualification, preserve UK
uncertainty separately, and link its reuse terms. Do not restate the assertion
as a worldwide open license.

## Item-linked rights page now returns 404

When an exact item manifest still points to an official rights page but that
page now returns 404, record the item-to-policy link, the dated live failure,
and an archived capture of the exact official page as separate evidence. Cache
the archived statement and preserve its declaration, attribution wording, and
requests at their original scope. Link rot alone does not prove that the
provider revoked the recorded declaration, but an archived capture is not a
current live policy page either; retain the capture date and leave any current
replacement terms open until the provider supplies them.

## Medieval does not automatically mean UK public domain: afw1075

Do not infer a worldwide or United Kingdom public-domain status merely from a
manuscript text's medieval date. UK Intellectual Property Office guidance says
that some literary works unpublished at the end of 1988 remain protected
through 31 December 2039 even when their authors died centuries ago. Determine
whether the exact witness text was validly made available to the public, not
just whether some version of the work appeared in print. Until that
publication history is established, keep any supported United States
public-domain conclusion jurisdiction-specific and record UK status as an open
question separate from rights in modern editions, catalog descriptions, and
manuscript photography. See the official [duration guidance](https://www.gov.uk/government/publications/copyright-notice-duration-of-copyright-term/copyright-notice-duration-of-copyright-term).

## Namesake lifespans are not rights evidence

Never calculate a life-plus copyright term from a name-only lifespan match.
Reconcile the person through authoritative identifiers, occupation,
associated works, and compatible places and dates. If a plausible namesake
owns the apparent death date, record the rejected identity and leave the
target person's death date unknown. Publication-based or typographical-term
conclusions may still be stated separately, but the authorial or editorial
literary layer must remain unresolved until its own identity evidence supports
the term calculation.

## Foreign historical editions and current manuscript components

Do not apply an annual cutoff stated specifically for works published in the
United States to an edition whose title page gives London or another foreign
place of publication. For a United States conclusion, ground the foreign-work
analysis in the applicable restoration and duration rules. In particular,
17 U.S.C. 104A(a)(1)(B) limits any restored copyright to the remaining United
States term, while section 304 supplies the relevant maximum term for
pre-1978 copyrights. Cite the official law and the edition's exact publication
date and place; do not turn that United States conclusion into a source-country
or worldwide claim.

Likewise, do not transfer a published edition's public-domain conclusion to
newly cataloged physical components merely because their dates overlap the
historical witness. Until an institutional concordance identifies the exact
current leaves or passages represented by the edition, leave the underlying
component text conservatively `unknown`. A separately proved passage may carry
its own narrow conclusion without clearing the rest of the component or any
new manuscript image.

## Representative-image trap: Gawain and Pearl

A sampled Calgary image carries a public-domain label alongside enumerated use
categories. Do not generalize it across the collection or to commercial reuse.
Use exact image records and leave collection-wide status unknown if necessary.

## Multiple selected-image objects: CME00023

One physical codex can have several public image objects—for example, one
multi-canvas slide set and several single-image records—with different item-
level licenses. Cache each complete published selection as its own bundle but
mark coverage `partial` for the manuscript. Do not merge their licenses,
invent one aggregate facsimile, or let complete capture of every selected
object erase the dated finding that no whole-codex surrogate was available.
If an official selection exposes no leaf occupied by the corpus work, do not
invent a `work_portion`: set `target_work_presence=absent`, state the zero
overlap, retain the selection only as supporting witness evidence, and keep the
work-image request route open. This also permits `coverage=complete` when every
canvas of the represented supporting object is cached; coverage and target-
work presence are independent claims.
Apply the same rule to a completely cached source-analogue manuscript that
does not contain the target text. Keep the full-object cache and downloaded
access record, but put analogue folio/canvas ranges in scoped comparison
relations and local-copy notes rather than mislabeling them as `work_portion`.
When the provider's own manuscript list distinguishes “Images” from “Digital
Facsimile,” preserve that item-level label as coverage evidence: inventory all
published images, but do not upgrade an “Images” item to a complete facsimile
without an audited whole-object sequence.

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
