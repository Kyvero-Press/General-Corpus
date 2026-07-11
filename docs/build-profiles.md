# CME build profiles

See [architecture.md](architecture.md) for the supported XML → HTML → Pandoc
pipeline, component ownership, prerequisites, and artifact policy. Profiles are
the recommended production interface because `scripts/cme-build plan` exposes
the effective converter and Pandoc commands before execution.

The compatibility wrappers `scripts/pandoc-cme-xml` and `scripts/pandoc-all`
remain available, but they duplicate some PDF defaults and may drift from the
profiles. Use a profile plan when exact production behavior matters.

## Setup and verification

Installation is environment-specific: the POSIX/Bash-oriented scripts are
verified on Linux, and no portable bootstrap, dependency lockfile, or maintained
package-manager recipe exists. Complete the copyable, non-mutating
[setup checks](architecture.md#setup-and-verification) before building.

## Choose by goal

| Goal | Profile and next step |
|---|---|
| Ordinary review PDF | `print-pdf`; inspect the plan, then build under `build/` |
| Deliberate omission of source notes | `reader-pdf-no-notes`; confirm that omission in review |
| Ebook | `epub`; review the EPUB3 candidate on representative readers |
| Lulu paperback interior candidate | `lulu-paperback-5x8-print-pdf`; then follow the [Lulu checklist](lulu-production.md) |

The current `list-profiles` machine description retains the legacy phrase
“Lulu-ready.” Treat that phrase as geometry shorthand only, never as upload
readiness; every Lulu-profile output remains an **interior candidate** subject
to the checklist's preflight and manual gates.

## Commands

Run these from the repository root. Always inspect `plan` immediately before
its corresponding `single` execution:

```bash
scripts/cme-build list-profiles --json
scripts/cme-build plan CME/source/CME_from_OTA/Gawain.xml \
  --profile print-pdf \
  --output build/profile/Gawain.pdf
scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml \
  --profile print-pdf \
  --output build/profile/Gawain.pdf
```

The generated file is a review candidate under `build/`; see the
[three-stage artifact policy](architecture.md#artifact-policy) before promoting
it for inspection or publication.

`--profile` is required for both `plan` and `single`. `single --output` is
required. `plan --output` is optional; without it, the profile's
`output_template` is resolved using the input stem.

For the PDF profiles, TOML `output_format = "pdf"` is descriptive plan metadata;
it does not add Pandoc `--to`. Pandoc infers the writer from the output suffix,
so an explicit output path intended to produce PDF must end in `.pdf` unless a
writer is intentionally overridden. The CLI accepts other suffixes. In contrast,
the EPUB profile sets `to = "epub3"`, which adds `--to epub3` unless a passthrough
writer overrides it. Inspect `plan` after any writer or output-suffix override.

Arguments after an explicit `--` separator are appended to Pandoc. For example,
this plan replaces the profile geometry because the resolver sees a user
`geometry` variable:

```bash
scripts/cme-build plan CME/source/CME_from_OTA/Gawain.xml \
  --profile print-pdf \
  --output build/profile/Gawain.pdf -- \
  -V geometry=paperwidth=6in -V geometry=paperheight=9in
```

`plan` emits JSON containing the XML normalization command, temporary generated
artifacts, expanded variables, ordered modules and filters, and final Pandoc
command. Profile XML flags are resolved from the profile and its configured
modules; the post-`--` arguments are Pandoc arguments, not arbitrary converter
flags.

## Public profiles

Profile inheritance and the exact values below are defined in
`config/cme-build/profiles.toml`.

### `print-pdf`

- Output: PDF, template `build/profile/{work}.pdf`.
- Notes: included in HTML and converted to LaTeX footnotes.
- Writer: Pandoc standalone output with TOC; `xelatex`; `book` document class.
- Fonts and page: Junicode regular/bold/italic/bold-italic files; 5×8 in paper.
- Lettrine: `plain`.
- Ordered modules: `book-frontmatter`, `colophon`, `running-heads`, `lettrine`,
  `footnotes`, `verse-lines`, `pagebreaks`.

### `reader-pdf-no-notes`

- Inherits `print-pdf`; output template
  `build/profile/{work}.reader.pdf`.
- Drops source notes during XML normalization and omits only the `footnotes`
  module.
- Keeps `xelatex`, the 5×8 in geometry, plain lettrines, TOC, and the remaining
  ordered modules.

### `epub`

- Output: EPUB, template `build/profile/{work}.epub`.
- Pandoc standalone output targeting `epub3`.
- Notes remain inline. There is no PDF engine, lettrine, LaTeX header, or Lua
  filter module.

### `lulu-paperback-5x8-print-pdf`

- Inherits `print-pdf`; output template `build/profile/{work}.lulu.pdf`.
- Keeps the same notes, `xelatex`, TOC, lettrine, font, and ordered module
  behavior as `print-pdf`.
- Uses a 5×8 in text layout inside 5.25×8.25 in pages: `layoutwidth=5in`,
  `layoutheight=8in`, and 0.125 in horizontal and vertical layout offsets.

The Lulu profile produces only an interior candidate; it is not a substitute
for preflight, cover work, upload preview, or proof review. See
[lulu-production.md](lulu-production.md).

## Configuration and overrides

Reusable module definitions live in `config/cme-build/modules.toml`. Module
order is significant; it controls the expansion order of XML flags, generated
headers, include files, and Lua filters. See [architecture.md](architecture.md)
for each stage's responsibility.

Pandoc variables are ordered arrays of `{ name, value }` records so repeated
variables such as `mainfontoptions` and `geometry` are preserved. The resolver
adds a default variable only while its TOML guard permits it:

- a user `documentclass` suppresses the default document class;
- a user `mainfont` suppresses the default main font and all associated
  `mainfontoptions` entries; and
- any user `geometry` or `papersize` variable suppresses the complete default
  geometry set, including the Lulu layout values.

A passthrough Pandoc writer or `--pdf-engine` similarly prevents the resolver
from adding the corresponding profile option. Inspect the resulting `plan`
after any override rather than assuming that a partial override preserves a
coherent print layout.

`single` realizes generated HTML, colophon, and lettrine headers in an isolated
temporary directory and invokes Pandoc. It creates the requested output parent
directory, but it does not perform publication-set replacement or visual
review.

## Cover helper

Covers are separate from profile-built interiors. `scripts/cme-cover plan`
computes page-count-dependent dimensions, and `scripts/cme-cover template`
writes a guide SVG (or PDF when `rsvg-convert` is installed). See the cover and
manual-review requirements in [lulu-production.md](lulu-production.md).
