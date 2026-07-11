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

## Verify practical access

Test the exact deliverable, not only its landing page.

- A catalog can be public while its files require registration.
- A preview can exist while the full bitstream is denied.
- A collection can be open while one exact item is restricted.
- A facsimile bibliography proves existence, not online access.
- A selected image is not a complete manuscript.

When an edition publishes a few manuscript plates, model those plates as their
own reproduction entity. A complete scan of that edition makes the plates
viewable but still does not become a complete facsimile of the witness.

Do not mark a file publicly downloadable until retrieval succeeds. Record
redirects, login requirements, request forms, fees, onsite access, and negative
checks with `last_checked`.

## Cache verified file deliverables

Download every exact public file used as a manuscript/book facsimile or
supporting source—such as a PDF, ZIP, image, or IIIF manifest—to the ignored
`source-cache/WORK_ID/` directory. Ordinary landing/catalog HTML need not be
saved when it is only an access route. Do not bypass authentication, access
controls, or provider restrictions.

Use the project helper so filenames, signatures, hashes, and sizes are
reproducible:

```bash
python3 scripts/cache-source-download.py WORK_ID EXACT_FILE_URL \
  --filename stable-name.pdf \
  --label "Complete edition PDF" \
  --coverage complete
```

Add the emitted object to the access record's `local_copies` array. Its
`source_url` must also appear as `access.url` or in `alternate_urls`, while the
landing page remains available as a human-readable route. Use one array item
per deliverable or volume. Label whether coverage is `complete`, `partial`,
`metadata_only`, or `unknown`; a cached IIIF manifest alone is metadata, not a
complete facsimile. The manifest records that a research copy was made;
the viewer checks whether the ignored file is present in the current checkout.
Never infer redistribution permission from local caching, and never copy the
cache into a public web build without an independently supported right to do
so.

For manuscript images, download the provider's complete physical manuscript
when it is publicly obtainable and practical, even when the cataloged work
occupies only part of it. `coverage=complete` means the cached file covers that
whole source object, not merely the work. Add `work_portion` with the verified
folio/page range, corresponding digital canvas or image range, and start/end
deep links when exposed. If only selected leaves are obtainable, use
`coverage=partial` and say so. A complete edition scan, a miniature cycle, or
an IIIF manifest without its image files is not a complete manuscript cache.

Do not generalize a license sampled from one image to a whole collection. Use
the exact image record proposed for reuse or leave collection-wide image terms
unknown. Inspect IIIF manifests directly: their rights and attribution fields
can be more precise than the viewer page, including geographic limits.

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
- Keep copyright status separate from contract terms.
- Preserve jurisdiction and item-level attribution.
- Confirm catalog, preview, download, and reuse statements independently.
- Verify each present `local_copies` file against its recorded byte count and
  SHA-256, and retain the exact direct file URL.
- Re-read human summaries for claims broader than their cited sources.
