# Rights, access, and evidence

Read this before writing `access`, `rights`, and final evidence records.

## Separate rights layers

Consider separately:

- underlying historical text;
- witness as a physical object;
- print edition, readings, and apparatus;
- electronic transcription and markup;
- manuscript/book photographs and interface assets;
- local repository artifact; and
- provider contracts or legacy availability terms.

An old text does not settle rights in a modern edition, encoding, or image.
Public access is not a license. “No Copyright–United States” is
jurisdiction-specific, not a worldwide dedication.

Record the provider's exact assertion, jurisdiction, component, date, and
source. Avoid a stronger legal conclusion than the evidence supports. When a
legacy XML restriction conflicts with a current provider label, preserve both
as distinct dated layers and open a question; do not silently choose the more
permissive statement.

Before marking the modern repository transcription or XML markup as
unlicensed or unknown, inspect the exact pinned repository revision for a root
license and any path- or file-specific notice. Cite the license at that
revision and scope its effect only to the material its wording covers. A
repository source license does not silently license the underlying historical
text, a source edition, provider photographs, or third-party interface assets;
if its application to data or markup is ambiguous, preserve that ambiguity
instead of broadening a software-only grant.

## Verify practical access

Test the exact deliverable, not only its landing page.

- A catalog can be public while its files require registration.
- A preview can exist while the full bitstream is denied.
- A collection can be open while one exact item is restricted.
- A facsimile bibliography proves existence, not online access.
- A selected image is not a complete manuscript.

When a provider exposes selected leaves but no obtainable whole codex, retain
the selected-leaf access as `coverage=partial` and record the negative
whole-object result explicitly in notes, a separate unavailable access route,
or an open question. This prevents the viewer and later researchers from
mistaking “some images exist” for complete digitization.

When an edition publishes a few manuscript plates, model those plates as their
own reproduction entity. A complete scan of that edition makes the plates
viewable but still does not become a complete facsimile of the witness.

Do not mark a file publicly downloadable until retrieval succeeds. Record
redirects, login requirements, request forms, fees, onsite access, and negative
checks with `last_checked`.

Do not reject an official bitstream solely because a `HEAD` response reports
HTML or another generic content type. Some repository routes describe the
landing response on `HEAD` but return the advertised PDF or image on `GET`.
Retrieve the exact public URL without bypassing access controls, then validate
the final bytes by signature, parser, size, and expected contents; record the
final URL and actual media type rather than trusting request-method metadata.

## Cache verified file deliverables

Download every exact public file used as a manuscript/book facsimile or
supporting source—such as a PDF, ZIP, image, or IIIF manifest—to the ignored
`source-cache/WORK_ID/` directory. Ordinary landing/catalog HTML need not be
saved when it is only an access route. Do not bypass authentication, access
controls, or provider restrictions.

Inspect the delivered file's own cover pages, colophon, metadata, and usage or
rights notices as well as its landing-page metadata. Attach embedded provider
terms to the scan or delivery-file layer, not to the historical edition or
underlying work, and retain them even when the item record supplies no license.
This is especially important when an old public-domain edition is delivered
with a modern noncommercial-use request or other provider condition.

Unclear redistribution rights do not by themselves prevent an ignored private
research cache of files that the provider makes directly public. Cache the
complete public object, record the rights uncertainty or permission requirement
separately, and do not commit or redistribute the cached bytes without an
applicable grant.

Treat a provider TLS failure as a security condition, not as evidence that the
file is absent. Only when the official landing page independently exposes the
exact file URL may a private research cache use a transfer with certificate
verification disabled; then validate the delivered file's signature, media
type, size, and fixity and record the condition. Never use this exception to
bypass authentication, authorization, or an access restriction.

An exact provider PDF can be usable while retaining recoverable structural
defects. If independent tools confirm the expected page tree and successfully
extract every page but an integrity checker reports recoverable object-offset
warnings or a simpler file-identification tool miscounts pages, preserve the
download byte-for-byte. Record the tools, results, and no-repair decision in
the local-copy notes; do not silently rewrite the file or call it incomplete
from one parser's result alone.

An official journal or repository PDF and an aggregator mirror can be
byte-distinct even when they represent the same article and pagination. Compare
their hashes, sizes, internal title pages, and rights metadata; retain both as
separate local copies when each is useful, and prefer the official item page
for the license assertion. Do not transfer an official copy's open license to
a mirror unless the mirror itself or the license scope supports that result.

Keep public availability and local cache state separate. A large deliverable
is still cacheable when the task calls for the complete object, available disk
is sufficient, and provider terms permit the intended private research copy;
check those facts before declining it for size alone. If an exact public file
cannot responsibly be cached, leave its access status publicly available,
omit `local_copies`, and state the concrete reason—such as a bulk-download
restriction, unresolved image terms, insufficient storage, or a reproducible
transfer failure. Never turn a no-cache decision into an availability claim.

Use the project helper so filenames, signatures, hashes, and sizes are
reproducible:

```bash
python3 scripts/cache-source-download.py WORK_ID EXACT_FILE_URL \
  --filename stable-name.pdf \
  --label "Complete edition PDF" \
  --coverage complete
```

When a complete manuscript is delivered as IIIF canvases rather than a single
file, create one auditable bundle instead of hundreds of manifest entries:

```bash
python3 scripts/cache-iiif-bundle.py WORK_ID EXACT_IIIF_MANIFEST_URL \
  --filename complete-manuscript.zip \
  --label "Complete manuscript IIIF bundle" \
  --work-portion-label "Cataloged work" \
  --work-locator "folios 10r–20v" \
  --work-locator "IIIF canvases 21–42" \
  --work-start-url https://example.org/viewer/canvas/21 \
  --work-end-url https://example.org/viewer/canvas/42
```

The ZIP contains the provider manifest, every canvas image, and an inventory
mapping canvas labels and URLs to exact image requests, member paths, sizes,
and checksums. The emitted `local_copies` object uses
`retrieval_method=iiif_bundle` and records `source_file_count`; add its exact
Presentation-manifest URL to the access route. `coverage=complete` means all
canvases in that physical-source manifest were captured, not that the image
request necessarily reproduces the provider's preservation master. Preserve
the recorded request-size profile in `notes`.
Do not relabel or mechanically repack an arbitrary TAR or image directory as
an IIIF ZIP. The validator expects the helper's canonical root
`manifest.json`, `inventory.json`, and `images/` structure, with the inventory
matching the exact source URLs and archived bytes; rebuild through the helper
when an older cache lacks that structure.
For a large whole-codex bundle, normally request a practical non-upscaling
access derivative around 1600–1800 pixels wide rather than service-native
preservation-master files, unless the research question or user explicitly
requires master resolution. Completeness is the presence of every exposed
surface; resolution is a separate property. Record every effective request
profile in the inventory and notes, including any native fallback retained for
a canvas that cannot supply the chosen derivative.
Interrupted bundles resume only from staging images whose recorded URL still
matches. Keep the default single worker for fragile services; use a modest
`--workers` value only when the provider can sustain parallel requests.
Retain the original Presentation manifest even when retrieval must percent-
encode literal spaces in provider service URLs. Do not force an upscale of
narrow canvases: use their native `full`/`max` response and preserve mixed
effective request profiles in the bundle inventory.
When a provider rejects a plausible derivative for an individual canvas, keep
Presentation-manifest mode and retry that canvas at service-native size. Audit
both the requested and successful exact URLs in the inventory rather than
inventing a separate image list merely to work around the service failure.

If the provider publishes every Image API surface but no Presentation
manifest, do not invent canvases or downgrade an obtainable whole codex to a
target-leaf cache. Supply `--image-url-list PATH`, where the file is a JSON
array or newline list of exact image request URLs, and use the provider's
official complete-facsimile record as the positional source URL. JSON objects
may add `label`, a genuine `canvas_url` when one exists, and an ignored local
`reuse_path` for already downloaded bytes. The helper records
`bundle_source_kind=image_url_inventory`, includes the normalized exact URL
list in the ZIP, and does not expose machine-local reuse paths. Confirm from
provider evidence that the list covers the whole physical object before using
`coverage=complete`.

Treat a compound-book Presentation manifest with zero canvases the same way:
it is metadata, not evidence that the page images are absent. Inspect the
official book viewer or media endpoint for a declared complete page count,
enumerate every provider page resource into an exact image inventory, and
verify the first, target, and final surfaces before marking that inventory
complete. Preserve the empty manifest as an alternate metadata route rather
than presenting it as the image source.

A provider's complete facsimile project may aggregate the main codex with
detached leaves or fragments now held elsewhere. Cache the complete published
project inventory, but state that its coverage is project-level rather than a
claim that every image belongs to one currently bound physical codex. Map
discontiguous work portions by the provider's item numbers and each holding
repository's foliation. When those orders differ from the reconstructed
textual sequence, retain both orders explicitly; do not replace either with
one invented continuous range.

Add the emitted object to the access record's `local_copies` array. Its
`source_url` must also appear as `access.url` or in `alternate_urls`, while the
landing page remains available as a human-readable route. Use one array item
per deliverable or volume. Label whether coverage is `complete`, `partial`,
`metadata_only`, or `unknown`; a cached IIIF manifest alone is metadata, not a
complete facsimile. Coverage is relative to the represented source: a fully
downloaded order form, rate card, rights sheet, or catalog export is still
`metadata_only` for manuscript-facsimile access. The manifest records that a
research copy was made;
the viewer checks whether the ignored file is present in the current checkout.
Never infer redistribution permission from local caching, and never copy the
cache into a public web build without an independently supported right to do
so.

When site terms expressly permit viewing or downloading for private purposes
but reserve storage, reproduction, transmission, or publication for other
purposes, a Git-ignored private research cache may record that narrow access;
it is not a redistributable corpus asset. Cite the exact controlling clause,
attach the restriction to that access object, and keep the bytes out of Git,
the viewer's public tree, and publication packages unless separate permission
is obtained.

When the exact same downloaded object is relevant to several corpus works,
keep one work-local path per manifest but avoid storing or downloading the
bytes repeatedly. After verifying identical exact source URL, byte count, and
SHA-256, create a hard link (or filesystem reflink) under each required
`source-cache/WORK_ID/` directory and re-run validation. Each manifest still
records its own path and, when the target is present, work-specific
`work_portion`; a verified zero-overlap supporting object instead records
`target_work_presence=absent`. Do not reuse a merely similar scan or
independently generated IIIF ZIP whose checksum differs.

For manuscript images, download the provider's complete physical manuscript
when it is publicly obtainable and practical, even when the cataloged work
occupies only part of it. `coverage=complete` means the cached file covers that
whole source object, not merely the work. Add `work_portion` with the verified
folio/page range, corresponding digital canvas or image range, and start/end
deep links when exposed. If the complete supporting or analogue object is
verified not to contain the target work, set `target_work_presence=absent` and
omit `work_portion`. If only selected leaves are obtainable, use
`coverage=partial` and say so. A complete edition scan, a miniature cycle, or
an IIIF manifest without its image files is not a complete manuscript cache.
Test every human-facing boundary link with an unauthenticated request. When a
provider publishes a Canvas identifier that does not dereference successfully,
retain that identifier in the inventory or locators but use a working viewer
deep link or exact Image API request for `start_url`, `end_url`, and access
alternates.
If a provider calls a recto-verso leaf run complete but exposes no covers,
boards, spine, pastedowns, or flyleaves, qualify `coverage=complete` to the
published leaf inventory in notes; do not call it complete physical-object
coverage. Record the omitted exterior surfaces and a request route for a fuller
surrogate.
Do not list one `local_copies` object per canvas when a single bundle and exact
source inventory can represent the complete set.

The same rule applies when a work occupies almost the entire codex: retain the
remaining covers, endleaves, blank or adjacent leaves in the complete cache,
then map the work's slightly narrower folio range instead of treating “nearly
all” as physically complete.

A provider's “complete” bound object may also include later inserted leaves,
replacement facsimiles, modern bindings, or other post-production material.
Retain those canvases in the complete source cache, but exclude or separately
scope them in `work_portion` rather than treating every digitized surface as
an authentic leaf of the cataloged work.

For a mediated complete-codex reproduction request, name the physical
surfaces required—covers or boards, spine, pastedowns, flyleaves, blanks,
edges when offered, and every manuscript leaf—then give the work's folio range
separately. A request for “the work” alone may otherwise be fulfilled as a
cropped selection and cannot support a complete-source claim.

Do not generalize a license sampled from one image to a whole collection. Use
the exact image record proposed for reuse or leave collection-wide image terms
unknown. Inspect IIIF manifests directly: their rights and attribution fields
can be more precise than the viewer page, including geographic limits.

When a provider's current guidance explicitly warns that older blanket
Creative Commons labels may be obsolete, prefer the exact object's current
rights statement. If that guidance also says faithful digitizations retain the
original's status and waives residual digitization-layer rights, record those
two propositions separately instead of carrying forward the obsolete blanket
license. Date both pieces of evidence and retain an open conflict only when the
item statement and current policy genuinely disagree.

Describe a facsimile's color and visual fidelity from representative page
inspection, including ordinary text and any painted leaves. Do not infer that
an object is monochrome from a “microfilm” provenance label, or that it is
meaningfully full color merely because its JPEGs have three channels.

## Make evidence auditable

Every consequential claim needs evidence that actually supports its layer and
scope. An evidence record should answer:

- what source was consulted;
- its direct stable URL or repository path;
- when it was consulted;
- the exact facts it supports; and
- whether it is primary, institutional, or scholarly interpretation.

For local evidence, record repository-relative paths and checksums. For web
evidence, prefer item/component records and direct digital objects. A
collection home or repository contact page can support an enquiry route but
must not masquerade as the catalog or image terms for a shelfmark.
Likewise, reserve a witness `holding.catalog_url` for a repository-owned exact
item/component record. Record an exact scholarly handlist as scholarly evidence
and access, explicitly labeled as such, rather than making it look like the
holding institution's online catalog.

Test URLs during substantive review. Replace dead legacy paths with current
official routes while retaining useful persistent identifiers as alternates.
When a dead legacy viewer is evidence that a complete surrogate once existed,
keep it as a separately dated `unavailable` access route and add current
catalog, request, subscription, or reproduction routes independently. An
archived viewer shell or license record does not make its missing image payload
currently public or cacheable.

## Handle incomplete evidence

Use an open question when:

- the immediate edition does not identify its precise witness method;
- a current provider statement conflicts with embedded terms;
- only a generic catalog or representative image was found;
- a source is cited but the exact item cannot be opened;
- copyright renewal, restoration, permission, or territorial status remains
  unresolved; or
- a negative search might be overturned by institutional enquiry.

State next steps and impact. Do not write “lost,” “not digitized,” or “no
scholarly reproduction” merely because a quick public search failed.

## Final evidence audit

- Resolve every evidence and `supports` reference.
- Ensure rights attach to the correct entity and access record.
- Diff the complete entity-ID set against `rights[].entity`: every modeled
  entity, including each separately cached scan, OCR, catalog expression, and
  other delivery layer, must have at least one conservatively scoped rights
  record. `unknown` is acceptable when evidenced certainty is unavailable;
  omission is not.
- Keep copyright status separate from contract terms.
- Preserve jurisdiction and item-level attribution.
- Confirm catalog, preview, download, and reuse statements independently.
- Verify each present `local_copies` file against its recorded byte count and
  SHA-256, and retain the exact direct file URL.
- Re-read human summaries for claims broader than their cited sources.
