# Corpus web viewer

The corpus viewer is a React, Vite, and TypeScript application under
`viewer/`. It joins the descriptive metadata and source-lineage manifests to
the canonical publication PDFs, presenting the result as a searchable catalog
for readers who want to download, print, or compare an edition with its known
sources.

The viewer is a read-only consumer of the corpus. Its generated catalog, staged
PDFs, and static site stay under `build/corpus-viewer/`; it does not modify the
publication set in `dist/` or the review files in `bin/pdf/`.

## Build the catalog

From the repository root, the catalog can be generated independently of the
web application:

```bash
python3 scripts/build-corpus-viewer-catalog.py
```

The generator validates both manifest systems, reads their indexes
independently, exact-joins the records by `work_id`, and scans the top-level
canonical PDFs in `dist/`. Loading the lineage index independently means a
researched source record remains visible even if descriptive metadata for that
work is still pending. The generator writes:

- `build/corpus-viewer/public/catalog/index.json`, containing cards and filter
  facets;
- `build/corpus-viewer/public/catalog/works/<work_id>.json`, containing each
  work's normalized detail record;
- copies of the source manifests under
  `build/corpus-viewer/public/catalog/manifests/`; and
- optionally, downloadable PDFs under
  `build/corpus-viewer/public/publication-pdfs/`.

For every lineage access route with `local_copies`, the normalized work record
also reports whether each ignored `source-cache/<work_id>/…` file is present
and checksum-valid in the checkout that built the catalog. The work detail UI
shows that local status, cache path, and checksum by default. Set
`VITE_SHOW_LOCAL_SOURCE_CACHE=false` at Vite build time to hide checkout-local
cache state while retaining the exact upstream download, IIIF, and work-locus
links. The GitHub Pages build uses this public presentation through
`viewer/.env.pages`; ordinary local development keeps the cache details
visible. Public mode groups duplicate upstream URLs, hides the local-copy
records and their notes, and uses neutral source-link labels rather than cached
copy labels. Access and work-locus notes remain verbatim because an individual
note can combine acquisition context with rights, uncertainty, or boundary
evidence. For an IIIF bundle the local view also identifies the retrieval
method, captured image count, bundle source kind, and exact Presentation-
manifest or official whole-facsimile source URL. When a complete manuscript
contains only one portion relevant to the current work, the viewer separately
shows the physical and digital locators and any start/end deep links recorded
in `work_portion`. Cached research sources are deliberately not copied into
the public site:
their provider terms may permit research download without permitting this
project to redistribute them.

The default command builds catalog data without copying the PDFs. Add
`--copy-pdfs` when the generated public tree must be self-contained:

```bash
python3 scripts/build-corpus-viewer-catalog.py --copy-pdfs
```

This stages all canonical PDFs currently represented by the catalog, so allow
for approximately the size of the complete `dist/` publication set. To link to
PDFs already hosted elsewhere instead, leave them uncopied and supply a URL
prefix:

```bash
python3 scripts/build-corpus-viewer-catalog.py \
  --external-pdf-base-url https://downloads.example.org/general-corpus
```

Use `--require-pdfs` for a strict release preparation: it fails if a work
indexed by either manifest system has no matching canonical PDF. Use
`--no-include-pdf-only` when a catalog should contain only works represented in
at least one manifest system.

The default deployable build additionally supplies the tracked
`manifests/publication-set/viewer-default.json` snapshot through
`--publication-inventory`. That gate requires exact equality of the complete
filename set, SHA-256 digests, byte counts, and page counts; it catches a
partial `dist/` even when the missing works do not yet have scholarly metadata.

## Develop, test, and build

Install the locked JavaScript dependencies and start the development server:

```bash
cd viewer
npm ci
npm run dev
```

`npm run dev` first regenerates the catalog without duplicating the publication
set. A development-only Vite handler serves exact top-level `dist/` filenames
at the viewer's PDF route, including byte-range requests for browser previews.
It rejects nested and non-PDF paths. The remaining checks and production build
are:

```bash
npm run test
npm run typecheck
npm run build
npm run preview
```

`npm run build` regenerates the data, type-checks the application, builds the
frontend, then validates and stages canonical PDFs into the deployable site at
`build/corpus-viewer/site/`. It fails if a work represented in either manifest
system lacks a matching canonical PDF or if the complete local set differs from
the tracked default publication snapshot. `npm run build:allow-missing`
provides an explicit non-release variant for previewing incomplete local sets.
`npm run preview` serves the production build for local inspection. Generated
content is ignored by Git and should be recreated from the manifests and
canonical PDFs.

The lower-level package commands are `npm run catalog` for data without copied
PDFs and `npm run catalog:assets` for data plus copied PDFs. The deployment-only
commands are `npm run catalog:pages` and `npm run build:pages`. They require
`PUBLICATION_PDF_BASE_URL`, validate the complete local `dist/` set against the
tracked publication inventory, write external PDF links, and build Vite in
`pages` mode without copying publication PDFs.

## Joining works to publications

The join is deliberately exact:

```text
metadata work_id == canonical PDF filename stem
CME00099         == dist/CME00099.pdf
```

There is no case folding, fuzzy matching, alias resolution, or "newest wins"
rule. Review artifacts such as `bin/pdf/CME00099-oracle-iter05.pdf` are not
publication candidates. A new naming exception must be represented explicitly
in the data pipeline rather than guessed in the browser.

The generator accepts only the identifier characters present in the corpus
(including literal `+` in URL path segments), confines indexed manifest paths
to their declared roots, rejects case-insensitive filename collisions and PDF
paths that escape `dist/`, checks the PDF header, and records a SHA-256 digest.
Development cataloging uses `pdfinfo` when available; staged or externally
published releases require it and require a positive page count and page size.
PDFs are copied into a temporary tree and their staged hashes are verified
before the prior catalog/download trees are replaced. External PDF prefixes
must be credential-free HTTPS URLs without query strings or fragments. The
output root must be a child of `build/`. These checks keep catalog generation
from weakening the repository's
[fail-closed publication-set contract](architecture.md#fail-closed-corpus-refresh-contract).

After an approved corpus refresh, replace the tracked viewer snapshot rather
than hand-editing it:

```bash
python3 scripts/snapshot-corpus-viewer-publications.py \
  --snapshot-date YYYY-MM-DD
```

Review the complete diff and rerun the strict build before committing it. The
snapshot identifies PDF artifacts; the refresh evidence remains responsible
for canonical XML choices and duplicate-stem resolutions.

## Incomplete metadata and missing PDFs

Coverage of the manifest systems is incremental. By default, a PDF without a
work-metadata manifest still appears in the viewer with a clearly marked
"metadata pending" fallback card. Its embedded PDF title and author are used
when available; otherwise the filename stem is humanized. Such a card has no
invented genres, dates, regions, or tags. If an independently indexed lineage
record exists, its known sources and scoped rights statements are still shown.

Conversely, an indexed metadata or lineage record without a canonical PDF
remains browsable, but its publication is marked unavailable and its download
action is disabled. The strict `--require-pdfs` option turns that condition into
a catalog build error. A cataloged metadata record must resolve to its declared
lineage manifest; unresolved or inconsistent manifest references fail
validation.

## Deployment

For a self-contained static deployment, run `npm run build` and publish the
contents of `build/corpus-viewer/site/` as one artifact. This includes the
generated catalog and the staged `publication-pdfs/` directory. The Vite base
path is relative, so the site can be hosted below a domain subpath as long as
the whole directory is kept together.

The public deployment is available at
[https://kyvero-press.github.io/General-Corpus/](https://kyvero-press.github.io/General-Corpus/).
It uses the same React application as local development, but its `pages` Vite
mode loads `viewer/.env.pages` and hides checkout-local source-cache status.
Upstream source-download and manuscript-location links remain visible.

### Publication PDF releases

Canonical PDFs are hosted as individual assets on a dated GitHub Release. The
release tag is derived exactly from the tracked publication snapshot:

```text
publication-set-<viewer-default snapshot_date>
```

For example, snapshot date `2026-07-11` resolves to release tag
`publication-set-2026-07-11` and PDF base URL
`https://github.com/Kyvero-Press/General-Corpus/releases/download/publication-set-2026-07-11`.
The URL is stable because a published snapshot is never replaced or uploaded
with `--clobber`, and repository release immutability locks its tag and assets
at publication. A newly approved publication set receives a new snapshot date
and release.

After completing the
[fail-closed corpus refresh](architecture.md#fail-closed-corpus-refresh-contract),
refreshing `viewer-default.json`, and committing and pushing the approved
snapshot, create its release from the validated top-level `dist/` files. Enable
immutable releases before publishing the repository's first snapshot; the
setting is idempotent and remains enabled for later snapshots.

```bash
snapshot_date="$(python3 -c 'import json; print(json.load(open("manifests/publication-set/viewer-default.json", encoding="utf-8"))["snapshot_date"])')"
release_tag="publication-set-$snapshot_date"
pdf_base_url="https://github.com/Kyvero-Press/General-Corpus/releases/download/$release_tag"

cd viewer
PUBLICATION_PDF_BASE_URL="$pdf_base_url" npm run catalog:pages
cd ..

gh api --method PUT repos/Kyvero-Press/General-Corpus/immutable-releases
gh release create "$release_tag" dist/*.pdf \
  --repo Kyvero-Press/General-Corpus \
  --target main \
  --title "General Corpus publication set $snapshot_date" \
  --notes "Canonical PDFs validated against manifests/publication-set/viewer-default.json." \
  --latest=false
```

Every approved PDF is a separate release asset, so the viewer can link directly
to one book without making readers retrieve the whole corpus. If the snapshot
commit triggered Pages before its release was available, publish the immutable
release and rerun the workflow with:

```bash
gh workflow run pages.yml --repo Kyvero-Press/General-Corpus --ref main
```

### Pages workflow

The Pages workflow derives the same tag and base URL from
`manifests/publication-set/viewer-default.json`, downloads every release PDF
into the runner's ignored `dist/`, and runs:

```bash
cd viewer
PUBLICATION_PDF_BASE_URL="$pdf_base_url" npm run build:pages
```

`catalog:pages` requires every indexed work to have a PDF and verifies the
downloaded release set's complete filename list, SHA-256 digests, byte counts,
and page counts against the tracked snapshot before emitting any external
links. It retains manifest schema, index, reference, path-containment, and
tracked-file validation while allowing an absent `repository_path` only when
that path is contained by the gitignored `source-cache/` tree, which is not
present in a clean Actions checkout. Ordinary local builds and repository gates
remain strict, and any recorded checksum is still verified when a cache file is
present.
`build:pages` then type-checks the application and builds the already prepared
catalog without copying `publication-pdfs/` into the Pages artifact.
The workflow runs the viewer tests, refuses draft or mutable releases, and fails
if that directory appears. It passes the static site to a separate deployment
job through a one-day Actions artifact. That job alone receives repository write
and Pages-build access, updates the `gh-pages` branch, and explicitly requests a
Pages build after every successful branch sync. The explicit request is
necessary because a branch push made with the workflow's `GITHUB_TOKEN` does
not itself trigger another workflow. Making the request unconditional also lets
a rerun recover when the branch update succeeded but the build request did not.
The build job has read-only repository access and retains no Git credentials
after checkout.

CI deliberately never regenerates canonical PDFs. `dist/` can be replaced only
through the reviewed fail-closed publication procedure, and the repository has
no maintained turnkey batch command that can safely reproduce that decision.
The Pages runner therefore consumes the already approved release artifacts and
uses the tracked inventory as its integrity boundary.

Configure Pages to publish the deployment branch once, then dispatch the
workflow:

```bash
gh api --method PUT repos/Kyvero-Press/General-Corpus/pages \
  -f build_type=legacy \
  -f 'source[branch]=gh-pages' \
  -f 'source[path]=/'
gh workflow run pages.yml --repo Kyvero-Press/General-Corpus --ref main
```

After deployment, verify several work records, upstream source links, and PDF
release downloads at the live URL. The external-PDF generator validates the
local release copies used for the build; it does not make a second HTTP request
to each emitted release URL, so this final live smoke test remains part of the
release procedure.
