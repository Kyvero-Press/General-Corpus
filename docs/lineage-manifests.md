# Source lineage and rights manifests

The lineage manifests answer four different questions without conflating them:

1. What repository artifact is used to build a work?
2. Which digital text, printed edition, and manuscript witness precede it?
3. Where can each layer be read, downloaded, requested, or purchased?
4. What rights statement or uncertainty applies to that particular layer?

General descriptive catalog data—titles, authorship, dates, regions,
languages, textual form, genres, subjects, and tags—lives in the separate
[`work metadata`](work-metadata-manifests.md) system.

The records are JSON graphs, because a work does not always have one straight
source chain. CME00099 is the motivating example: its first section comes from
KB X 90, while its second section comes from a different 1597 manuscript whose
modern shelfmark is unresolved.

## Files

```text
manifests/lineage/
├── README.md
├── index.json
├── schemas/
│   ├── lineage-index.schema.json
│   └── lineage-manifest.schema.json
└── works/
    ├── CME00099.json
    └── … one JSON file per researched work
```

`index.json` is the only discovery list. Its `coverage.strategy` is currently
`incremental`: the repository has many more works than researched manifests.
Do not create empty or speculative manifests merely to increase the count.

## Local source cache

Exact downloadable facsimiles and supporting research files live outside Git
under `source-cache/<work_id>/`. Cache a verified file with:

```bash
python3 scripts/cache-source-download.py CME00099 \
  https://example.org/exact-source.pdf \
  --filename complete-manuscript.pdf \
  --label "Complete manuscript PDF" \
  --coverage complete \
  --work-portion-label "Work represented by CME00099" \
  --work-locator "folios 10r–20v" \
  --work-locator "IIIF canvases 21–42" \
  --work-start-url https://example.org/canvas/21 \
  --work-end-url https://example.org/canvas/42
```

The command prints a JSON `local_copies` snippet containing the relative path,
exact direct URL, SHA-256, byte count, media type, and date. Add the object to
the matching access record and keep the human-facing landing page in `url`;
the exact `source_url` must also be present in `url` or `alternate_urls`.
Multiple files or volumes belong in the same `local_copies` array when they
share an access route. Every file states whether its coverage is `complete`,
`partial`, `metadata_only`, or `unknown`, so an IIIF manifest or selected image
cannot masquerade as a locally complete facsimile.

If a provider exposes a complete object only as IIIF canvas images, cache the
whole Presentation manifest as one ZIP bundle:

```bash
python3 scripts/cache-iiif-bundle.py CME00099 \
  https://example.org/iiif/complete-manuscript/manifest \
  --filename complete-manuscript.zip \
  --label "Complete manuscript IIIF bundle" \
  --work-portion-label "Work represented by CME00099" \
  --work-locator "folios 10r–20v" \
  --work-locator "IIIF canvases 21–42" \
  --work-start-url https://example.org/viewer/canvas/21 \
  --work-end-url https://example.org/viewer/canvas/42
```

The helper downloads every canvas, then stores `manifest.json`, all images,
and `inventory.json` in one ignored ZIP. The inventory retains the exact image
request, canvas URL and label, ZIP member path, checksum, and byte count for
each image. Its compact manifest record sets `retrieval_method` to
`iiif_bundle`, records `source_file_count`, and uses the exact IIIF manifest as
`source_url`. The generated notes disclose the image request-size profile.
Thus `coverage=complete` means every canvas in that manifest was cached; it
does not claim access to an archive's preservation masters.
Large objects can be resumed from URL-matched staging files. The default uses
one request at a time; `--workers 4` (up to 32) permits conservative parallel
retrieval when the provider service can support it.
Provider manifests are stored byte-for-byte even when their service URLs need
standards-compliant `%20` encoding for literal spaces. For simple width,
height, or bounding-box requests, canvases smaller than the requested size use
the Image API's native `full`/`max` form instead of requesting an unsupported
upscale; every effective request profile remains recorded in the inventory and
bundle notes.
If a provider rejects an otherwise plausible derivative, Presentation mode
retries that canvas at service-native `full`/`max`. The inventory then records
both the failed requested URL/profile and the exact fallback URL/profile that
supplied the cached bytes.

Some providers publish a complete facsimile as individual Image API services
without a Presentation manifest. In that case, pass the official whole-
facsimile source record as the positional URL and an exhaustive JSON or
newline inventory of exact image requests:

```bash
python3 scripts/cache-iiif-bundle.py CME00099 \
  https://example.org/complete-manuscript \
  --image-url-list build/complete-manuscript-images.json \
  --filename complete-manuscript.zip \
  --label "Complete manuscript IIIF image bundle"
```

The emitted `bundle_source_kind` is `image_url_inventory`, and the ZIP stores
the normalized exact URL list without fabricating canvas identifiers. JSON
inventory objects may contain `label`, a real `canvas_url`, and `reuse_path`
for a previously downloaded local image; machine-local reuse paths are removed
from the ZIP. Use `coverage=complete` only after verifying that the provider's
list covers the whole physical object.

For a manuscript witness, download the provider's complete digitized physical
codex whenever it is publicly obtainable and practical rather than downloading
only the leaves that contain the cataloged work. Retain all surfaces exposed as
part of that object, including covers, endleaves, blanks, and adjacent works.
Here, `coverage` describes the completeness of the cached source object: use
`complete` for the whole codex and `partial` for selected leaves. The optional
`work_portion` then maps this manifest's work back into that larger source with
one or more physical and digital locators and, when available, deep links to
its first and final page or canvas. Never substitute an excerpt for an
obtainable whole-codex object, and do not call an IIIF presentation manifest
alone a complete image cache.

The cache is research storage, not a redistribution channel. It is never
copied into the viewer's public tree automatically. Manifest validation checks
the location, URL linkage, and any locally present file; a missing ignored file
is valid so the committed manifest remains portable between clones.

## Data model

Each work manifest contains:

- `entities`: repository files, digital encodings, editions, manuscript
  witnesses, facsimiles, and catalogues;
- `agents`: people and institutions referenced by those entities;
- `relations`: directed, scoped provenance edges;
- `access`: dated routes to public files, catalogues, reading-room access,
  reproduction orders, documented negative searches, and checksummed local
  copies of verified file deliverables;
- `rights`: component- and jurisdiction-specific assessments;
- `editorial_practices`: transformations such as expanded abbreviations or
  normalized punctuation;
- `evidence`: local files, scans, official catalogues, laws, and authority
  records supporting assertions; and
- `open_questions`: unresolved facts with concrete next steps.

Stable local IDs make cross-references explicit. For example,
`edition:holthausen:anglia-19-1897` is connected separately to
`witness:kb:X90` and `witness:kb:legacy-miscellany-vii`. Every partial-source
relation describes the relevant section and manuscript pages.

### Status language

Use precise states:

- `extant`, `missing`, `reported_lost`, and `destroyed` describe survival;
- `publicly_available`, `requestable`, `purchasable`, `onsite_only`, and
  `no_public_copy_found` describe access; and
- `public_domain`, `copyright_may_apply`, and `unknown` describe a particular
  component in a named jurisdiction.

“No public copy found as of DATE” does not mean “not digitized,” and “not
digitized” does not mean “lost.” Negative searches require both evidence and a
`last_checked` date.

## Rights are not inherited through the graph

A medieval text, an editor's notes, a keyed XML text, a photograph, and the
provider's delivery terms are different things. The public-domain status of
one does not automatically settle the others.

For CME00099, the current record distinguishes:

| Component | Recorded position |
| --- | --- |
| U-M CME00099 digital materials | U-M marks them Public Domain / No Copyright–United States |
| Holthausen 1897 edition in the United States | Public domain |
| Protectable Holthausen editorial contribution in Sweden | Cautiously treated as potentially protected through 2026-12-31; review on 2027-01-01 |
| Medieval and 1597 manuscript text | Public domain in the United States |
| A future KB-supplied facsimile | Unknown until the supplied terms and written answer are recorded |
| Local 14-TIFF archive | Images the printed edition, not a manuscript; scan provenance and image-level terms remain unknown |
| BSB scan of Stephens's 1847 catalogue | Host applies No Copyright–Non-Commercial Use Only; link rather than assuming open commercial redistribution |

Rights statements such as Public Domain Mark, No Copyright–United States, and
No Copyright–Non-Commercial Use Only are stored as statements, not mislabeled
as licenses. This metadata is research documentation, not legal advice.

## CME00099 lineage

The supported upstream graph is:

```text
KB X 90 ───────────────┐
                       ├─> Holthausen 1897 ─> U-M CME00099 ─> repository XML
KB Miscellany VII ─────┘

KB X 90 ───────────────┐
                       ├─> Stephens 1844 ──> consulted by Holthausen
KB Miscellany VII ─────┘
```

Stephens 1844 is a prior edition, not Holthausen's sole source. Holthausen says
he made a new collation and marks the Section I items that Stephens had not
printed. The manifest also links a later, broader edition of X 90's prose
recipes by Gottfried Müller (1929), but explicitly keeps it outside the
upstream CME00099 chain.

The formatting information is provenance too. Holthausen states that:

- expanded manuscript contractions appear in italics;
- red manuscript writing appears in bold;
- capitalization is normalized; and
- punctuation is normalized.

Consequently, the italic spans in CME00099 generally represent supplied
letters used to expand manuscript abbreviations—not manuscript italics and not
an ellipsis. A manuscript facsimile is still needed to determine the exact
abbreviation sign behind each expansion.

## Adding or updating a work

1. Copy the structure of a reviewed work manifest, give every record a stable
   ID, and keep the record self-contained.
2. Represent every material layer separately. Do not collapse a scan, its
   underlying edition, and a manuscript into one entity.
3. Scope every partial provenance relation to printed pages, sections, items,
   manuscript pages, or folios. State whether numbering is pages or folios.
4. Attach access and rights records to the exact entity or digital surrogate
   they describe. Date all availability checks.
5. Cite local files structurally where possible; XML line numbers are unstable.
6. Put unverified shelfmarks, access claims, and rights questions in
   `open_questions` rather than asserting them as facts.
7. Add the manifest to `index.json`, update `coverage.manifest_count`, and run
   the validator and tests.

The index is committed for easy consumption, but validation fails if it drifts
from `works/*.json` or disagrees with a manifest's identifying fields.

## When a requested facsimile arrives

Before recording any supplied images:

1. Preserve the institution's written rights/terms response and supplied files
   under ignored local storage if they contain personal information or cannot
   be redistributed. Add a `local_copies` record only when its non-sensitive
   path, URL, hash, and terms can safely be committed.
2. Create a new facsimile entity recording provider, request date, production
   date if known, exact manuscript coverage, format, resolution, color mode,
   file count, and checksums.
3. Create a separate rights record for the supplied image files and another for
   any provider contract terms. Quote only the minimum factual language needed.
4. Remove private addresses, telephone numbers, customer/order numbers,
   signatures, invoices, and payment details from committed evidence.
5. If redistribution is not permitted, do not commit or publicly stage the
   images. A terms-compliant research copy may remain in `source-cache/`;
   record a non-sensitive citation and public request route so another
   researcher can obtain a copy independently.

## Validation

The validator is offline and uses only Python's standard library:

```bash
python3 scripts/validate-lineage-manifests.py
python3 -m unittest tests.test_lineage_manifests
```

It enforces the committed JSON Schemas and additionally checks:

- unique IDs and resolvable entity, agent, access, and evidence references;
- exact index coverage of `works/*.json`;
- repository-relative, non-escaping paths that exist;
- work-scoped `source-cache/` paths whose exact URLs are exposed by their
  access records, with byte/hash verification whenever the ignored file is
  present;
- structured `work_portion` locators that keep whole-source coverage distinct
  from the leaves or canvases occupied by this work;
- SHA-256 and git-blob hashes for repository artifacts;
- agreement between a manifest work ID and the XML identifier family used by
  that source (`IDG`/`BIBNO`/`VID` or `IDNO`);
  and
- agreement between index fields and their work manifest.

Remote links are deliberately not fetched during normal validation. Their
availability dates live in the records and should be rechecked during a
substantive manifest review.
