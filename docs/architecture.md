# Build architecture

This document is the canonical map of the current CME production path. Detailed
profile syntax is in [build-profiles.md](build-profiles.md), XML behavior and the
source inventory are in [xml-formats.md](xml-formats.md), and Lulu-specific work
is in [lulu-production.md](lulu-production.md).

## Supported production path

```text
CME/source/**/*.xml
        |
        |  scripts/cme_xml_to_html.py
        v
normalized standalone HTML
        |
        |  Pandoc parses HTML into its document AST
        +------------------------------+
        |                              |
        v                              v
      EPUB3                    LaTeX + ordered headers/filters
                                       |
                                       |  XeLaTeX
                                       v
                                      PDF
```

`scripts/cme-build` and the TOML profiles under `config/cme-build/` are the
recommended, inspectable production interface. The files under `ConTeXt/` are
historical conversion utilities: no current `scripts/cme-build`,
`scripts/pandoc-cme-xml`, or `scripts/pandoc-all` entry point invokes them.

The HTML bridge is deliberate. It isolates irregular source XML and recovery
from Pandoc, gives every writer the same selected readable payload, and lets
Pandoc own the EPUB or LaTeX serialization.

## Setup and verification

The scripts are POSIX/Bash-oriented and verified on Linux. This repository
maintains no portable bootstrap, dependency lockfile, or package-manager recipe;
installation is environment-specific.

| Operation | Required tools or data |
|---|---|
| XML to normalized HTML | Python 3 and `lxml` |
| EPUB or any other final Pandoc format | Pandoc, plus the XML prerequisites |
| LaTeX/PDF profile | Pandoc, XeLaTeX/TeX Live, and the four configured Junicode font files |
| Lulu interior candidate preflight | Poppler `pdfinfo` and `pdffonts` |
| Broader generated-PDF audit | Poppler `pdfinfo`, `pdffonts`, and `pdftotext` |
| Direct PDF cover-template output | optional `rsvg-convert` from librsvg; SVG template output does not require it |

Run these non-mutating checks from the repository root:

```bash
set -eu
command -v python3
python3 -c 'import sys, lxml.etree as e; print("Python", sys.version.split()[0], "lxml", ".".join(map(str, e.LXML_VERSION)))'
command -v pandoc
pandoc --version | sed -n '1p'
command -v xelatex
xelatex --version | sed -n '1p'
```

Verify every configured filename, preferring the TeX file database and falling
back to an exact fontconfig basename match:

```bash
set -eu
command -v kpsewhich >/dev/null
command -v fc-list >/dev/null
for font in \
  Junicode-Regular.otf \
  Junicode-Bold.otf \
  Junicode-Italic.otf \
  Junicode-BoldItalic.otf
do
  path=$(kpsewhich "$font" 2>/dev/null || true)
  if [ -z "$path" ]; then
    path=$(fc-list -f '%{file}\n' 2>/dev/null |
      awk -F/ -v font="$font" '$NF == font { print; exit }')
  fi
  if [ -z "$path" ]; then
    printf 'MISSING %s\n' "$font" >&2
    exit 1
  fi
  printf '%s -> %s\n' "$font" "$path"
done
```

The expected result is exit status 0, executable/version output for the first
block, and one resolved path for each of the four exact filenames in the second.
On failure, capture the exact command, exit status, and complete standard output
and error; record the Linux distribution, Python, Pandoc, XeLaTeX/TeX Live, and
fontconfig versions. Inspect the first missing executable, Python import, or
font filename/path before attempting a build, then preserve the failing
`scripts/cme-build plan` if dependency checks pass but resolution is unexpected.

The PDF header has narrow per-character fallbacks for selected symbols when
DejaVu Sans, Noto Serif, or Noto Sans CJK KR is installed. Those fallbacks do
not replace Junicode as the configured body font and do not remove the need to
review missing-glyph warnings.

## Quick production workflow

Run commands from the repository root. Inspect before executing when exact
effective defaults matter:

```bash
scripts/cme-build list-profiles --json
scripts/cme-build plan CME/source/CME_from_OTA/Gawain.xml \
  --profile print-pdf \
  --output build/profile/Gawain.pdf
scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml \
  --profile print-pdf \
  --output build/profile/Gawain.pdf
```

The output is a review candidate, not a publication artifact. Use the compact
choose-by-goal table in [build-profiles.md](build-profiles.md#choose-by-goal)
before substituting another profile.

`--profile` is required by `plan` and `single`; `single --output` is also
required. `plan --output` is optional and otherwise resolves the profile's
output template. Put extra Pandoc arguments after an explicit `--`; they are
appended to the resolved Pandoc command:

```bash
scripts/cme-build plan CME/source/CME_from_OTA/Gawain.xml \
  --profile print-pdf --output build/profile/Gawain.pdf -- \
  -V geometry=paperwidth=6in -V geometry=paperheight=9in
```

Use `preflight-lulu` for a built Lulu interior candidate; it does not take a profile:

```bash
scripts/cme-build preflight-lulu build/lulu/Gawain/Gawain-interior.pdf \
  --trim 5x8 --binding paperback-perfect --json
```

See [build-profiles.md](build-profiles.md) for the public profiles and override
rules rather than copying their option catalog here.

## Components and sources of truth

| Concern | Authoritative repository source |
|---|---|
| XML format detection, payload selection, recovery, and normalization | `scripts/cme_xml_to_html.py`: `detect_format()`, `primary_text_nodes()`, `normalize_word_break_verbars()`, and `render_document()` |
| Public profile CLI, plan resolution, execution, temporary files, and Lulu preflight | `scripts/cme-build` and `scripts/cme_build_profiles.py`: CLI construction, `resolve_plan()`, `run_single()`, and `preflight_lulu_pdf()` |
| Profile inheritance, output templates, notes modes, writers, engine, variables, geometry, and module selection | `config/cme-build/profiles.toml` |
| Module expansion and order of headers, generated artifacts, XML flags, and Lua filters | `config/cme-build/modules.toml` |
| PDF frontmatter and presentation | `scripts/pandoc-book-frontmatter.tex`; `scripts/pandoc-latex-{running-heads,lettrine,footnotes,verse-lines,pagebreaks}.lua`; matching `scripts/pandoc-latex-{lettrine,verse-lines,pagebreaks}.tex` headers |
| Compatibility single-file and recursive batch entry points | `scripts/pandoc-cme-xml` and `scripts/pandoc-all` |
| XML inventory snapshot | `docs/xml-format-manifest.tsv`, generated with `scripts/categorize-xml-formats.py` |
| Behavioral expectations | `tests/test_cme_build_profiles.py`, `tests/test_cme_xml_to_html.py`, and the focused audit/filter tests under `tests/` |

CLI help, TOML, these functions, and tests are authoritative when prose and
implementation disagree.

## XML selection, recovery, and normalization

The converter supports `dlpstextclass`, `ets-temphead-eebo`,
`ets-header-eebo`, generic `ets`, `tei2`, and `headwords`, with `auto` detection.
It selects the known running-text payload (`TEXT`, ETS `EEBO/TEXT` or grouped
`TEXT`, or a narrow direct `BODY` fallback) rather than falling back to a root
that might contain headers or revision metadata. Headwords are intentionally
rendered as lexical records rather than running prose.

Parsing first attempts strict XML. By default, a strict failure is reparsed with
`lxml` recovery and reported; `--strict` instead fails. Recovery is a way to
produce reviewable output, not proof that damaged markup was interpreted
correctly.

Within the selected rendered payload, transcriptional U+2223 (`∣`) is removed
only when it joins alphabetic characters in one maximal inline flow. Ordinary
inline markup may be crossed, but block and line-break boundaries and NOTE,
GAP, milestone, and headword ENTRY/FORM boundaries stop a join. Included notes
are normalized as their own flows; dropped notes remain boundaries. Standalone,
edge-, punctuation-, and digit-adjacent U+2223 remains, as do ASCII `|` and
other lookalikes. Normalization happens on a copy only when the selected payload
contains U+2223, leaving the source tree and metadata unchanged; marker-free
payloads take the no-copy fast path. See [xml-formats.md](xml-formats.md) for
examples and direct converter syntax.

## Profile and presentation expansion

Module order is semantically significant because `resolve_plan()` expands
headers, before-body material, Lua filters, generated files, and XML flags in
profile order. The configured PDF order is:

```text
book-frontmatter -> colophon -> running-heads -> lettrine -> footnotes
                 -> verse-lines -> pagebreaks
```

The frontmatter header defines the title-page/colophon book presentation,
metadata use, body page style, and font fallbacks. Pandoc's standalone book
output and `--toc` provide the title/frontmatter and contents sequence; the
converter supplies the source-derived title, author, date, and other metadata.
The colophon module generates a source-specific LaTeX invocation and suppresses
the visible HTML source-metadata block. Generated colophon and selected
lettrine-mode headers are isolated with the normalized HTML in a unique
temporary directory for each `single` execution and are removed afterward.

The ordered filters then:

1. create shortened title/section running-head marks while leaving visible
   headings and the TOC unchanged;
2. mark appropriate prose openings for plain or optional decorative lettrines.
   Missing `GoudyIn.sty`/`GotIn.sty`, or unavailable Baroque Initials font
   support, emits a warning and uses a plain body-font lettrine; only a missing
   `lettrine.sty` makes the initial inline;
3. turn rendered note spans into real LaTeX footnotes where that module is
   enabled;
4. add subtle margin numbers to every fifth visible verse line, using source
   line metadata when available and avoiding the lettrine area; and
5. apply prose/verse page-break and fragment-protection hints without making
   long verse groups wholly unbreakable.

The reader PDF drops notes before HTML rendering and omits the footnote module.
The EPUB profile keeps notes inline and uses no LaTeX modules. Exact module and
variable sets belong in TOML and [build-profiles.md](build-profiles.md), not in
additional duplicated lists.

## Compatibility entry points

`scripts/pandoc-cme-xml` remains a direct single-file XML-to-Pandoc wrapper, and
`scripts/pandoc-all` recursively calls it while preserving relative paths.
These are useful compatibility paths, not the profile layer. Their hard-coded
PDF defaults overlap profile defaults and can drift independently. In
particular, `pandoc-all` is not a profile-based publication refresh command.
Use `scripts/cme-build plan` whenever the exact normalized-XML and Pandoc
commands must be reviewable.

## Artifact policy

Artifacts move through three deliberate stages:

1. Generate review candidates, intermediates, logs, audits, and other validation
   evidence under `build/`.
2. After review, place a repository-default PDF for human inspection under
   `bin/pdf/`, as required by `AGENTS.md`.
3. Materialize the publication set under `dist/` only through the fail-closed
   corpus refresh contract below; never incrementally overwrite it.

All three directories are ignored locally; their presence is not evidence that
a reproducible or complete build was performed.

## Fail-closed corpus refresh contract

There is currently **no maintained turnkey profile-based batch command** that
safely rebuilds and replaces `dist/`. A corpus publication refresh must use a
reviewed driver or equivalent procedure that implements all of these gates:

1. Before any switch, create and preserve a complete pre-switch manifest of the
   current live `dist/` tree: record every file's relative path and cryptographic
   hash, and record a successful `pdfinfo` readability result for every PDF. Do
   not switch unless the manifest is complete and every live PDF is readable.
2. Map every existing output stem to exactly one approved canonical XML source.
   Use `docs/xml-format-manifest.tsv` as the source inventory and record explicit
   resolutions for every duplicate stem, repaired/recent variant, or other
   ambiguity. Fail on missing, duplicate, or ambiguous mappings; do not infer
   “newest wins.”
3. Build each mapped source into a fresh staging tree under `build/`, never into
   live `dist/`, using a source-qualified command such as:

   ```bash
   scripts/cme-build plan CME/source/CME_from_OTA/Gawain.xml \
     --profile print-pdf \
     --output build/dist-staging/Gawain.pdf
   scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml \
     --profile print-pdf \
     --output build/dist-staging/Gawain.pdf
   ```

   Retain the approved mapping, exact command, stdout/stderr, and source path for
   every output.
4. Require every staged PDF to exist, be nonempty, and be readable by
   `pdfinfo`. A failed build or unreadable file fails the entire refresh. Record
   an approved staged manifest of relative paths and cryptographic hashes.
5. Compare the approved expected set, staged set, and pre-refresh live set.
   Missing, extra, stale, or differently named paths fail the refresh.
6. Run font and extracted-text audits across the entire staging set. Resolve or
   explicitly review every warning; report-generation mode is not a clean gate.
7. Materialize the validated candidate, if necessary, on the same filesystem as
   live `dist/`. Retain the previous complete `dist/` tree in a rollback
   location, then use a reviewed directory-swap or whole-tree transaction with
   failure traps to switch the candidate into place. Never copy publication
   files piecemeal.
8. After the switch, verify that live relative paths and cryptographic hashes
   exactly match the approved staged manifest and that every live PDF remains
   readable. On any switch or post-switch failure, restore the previous tree.
   After every attempted restoration, require live `dist/` to match the complete
   pre-switch manifest exactly, with no missing, extra, or differently hashed
   files, and require a successful readability check for every restored PDF.
   Preserve the restoration commands and logs, exact-manifest comparison, and
   PDF readability results. Declare rollback successful only when both identity
   and readability are proven. If either cannot be proven, report a hard recovery
   failure requiring operator intervention; do not report either the refresh or
   rollback as successful. Delete the rollback tree only after successful
   post-switch verification.
9. Preserve pre- and post-switch evidence under `build/`: source mapping and
   commands; manifests, hashes, sizes, and mtimes; page counts and page sizes;
   font-embedding results; extracted-text scans; generated-PDF audit reports;
   and all switch and rollback-verification evidence, including evidence from
   failed restoration attempts.

The source inventory and publication set are different concepts. The generated
inventory currently records 307 XML files, while duplicate stems,
repaired/recent variants, and non-running-text inputs prevent a one-source to
one-PDF assumption. Likewise, the presently observed 297 PDFs are **not** a
permanent invariant. The pre-refresh `dist/` snapshot plus an approved,
unambiguous mapping define the replacement set for a particular refresh.

## Tests, audits, and review

Focused behavior checks for this architecture are:

```bash
python3 -m unittest tests.test_cme_build_profiles tests.test_cme_xml_to_html
python3 -m unittest tests.test_generated_cme_pdf_audit tests.test_cme_pdf_typography_audit
```

Source audits identify structures needing editorial or visual attention:

```bash
python3 scripts/cme_contents_audit.py CME/source \
  --report build/audit/contents.tsv
python3 scripts/audit-cme-pdf-typography.py CME/source \
  --report build/audit/typography.tsv \
  --summary build/audit/typography.md
```

Audit staged PDFs after generation:

```bash
python3 scripts/audit-generated-cme-pdfs.py build/dist-staging \
  --report build/audit/generated-pdfs.tsv \
  --summary build/audit/generated-pdfs.md
```

The content, typography-risk, and generated-PDF audits exit 1 when findings are
present. Their `--allow-issues` option makes report generation exit 0 despite
findings; it does **not** certify a clean quality gate. Tool-related findings
still require resolution even when report generation is allowed. Lulu preflight
can emit machine-readable JSON and returns 0 only when all checks pass. A missing
PDF completes the failed `file-exists` check and returns 1 before binding
validation, so a simultaneously unsupported binding does not change that result;
unsupported binding returns 2 only if execution reaches its validation. Invalid
trim remains a CLI error returning 2, as do other CLI/profile/tool/parsing errors
handled by `cme-build`; see [lulu-production.md](lulu-production.md).

Automation cannot judge textual recovery, title selection, page rhythm,
lettrines, running heads, boundary pages, or cover correctness. Review warnings,
inspect representative and high-risk PDFs, and complete Lulu upload preview and
physical proof review before publication.

## Maintenance and debugging

Keep prose architectural: CLI help, TOML, converter functions, templates,
filters, and tests remain the executable sources of truth. Any change to a
pipeline stage, profile/module order, artifact contract, or audit semantics
should update this document and the affected specialist document together.

For extension or debugging, start with `list-profiles --json`, capture a `plan`,
then trace the responsible row in the source-of-truth table. Add XML behavior to
the converter and its tests; add defaults to profile/module TOML; add PDF
presentation behavior to the narrow header/filter that owns it. Do not patch a
generated command or temporary file, and do not add a second prose option
catalog.
