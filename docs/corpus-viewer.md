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
shows that status, the cache path and checksum, and the exact upstream file
URL. Cached research sources are deliberately not copied into the public site:
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
PDFs and `npm run catalog:assets` for data plus copied PDFs.

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

For externally hosted PDFs, generate the catalog with
`--external-pdf-base-url`, then build the already-prepared public tree without
running the package's catalog-rebuilding `build` wrapper:

```bash
python3 scripts/build-corpus-viewer-catalog.py \
  --require-pdfs \
  --publication-inventory manifests/publication-set/viewer-default.json \
  --external-pdf-base-url https://downloads.example.org/general-corpus
cd viewer
npm run typecheck
npm exec vite build
```

Deploy `build/corpus-viewer/site/` only after verifying several work pages,
source links, and PDF downloads. There is currently no repository CI or hosting
configuration that publishes the viewer automatically. Because `dist/` and
`build/` are intentionally untracked, a deployment job must either obtain the
approved publication PDFs as an artifact, build them through the documented
publication workflow, or use an external PDF host. The viewer generator does
not verify remote objects in external-PDF mode, so a release operator must
sample hosted downloads and confirm that deployment preserves the locally
validated filenames and hashes.
