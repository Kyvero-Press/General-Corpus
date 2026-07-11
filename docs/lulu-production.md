# Lulu production checklist

See [architecture.md](architecture.md) for the production pipeline and artifact
contract, and [build-profiles.md](build-profiles.md) for profile syntax and
overrides. Lulu print projects still require manual project metadata, a separate
cover, upload-preview review, and a proof copy.

## Official Lulu references

The third-party requirements summarized here were last verified **2026-07-11**
and must be rechecked before every upload:

- [Publishing: The Basics](https://help.lulu.com/en/support/solutions/articles/64000255480-publishing-the-basics)
  — project and upload workflow;
- [Mandatory Print Book Distribution Requirements](https://help.lulu.com/en/support/solutions/articles/64000255462-mandatory-print-book-distribution-requirements)
  — metadata, ISBN, and distribution gates;
- [Upload Your Cover File](https://help.lulu.com/en/support/solutions/articles/64000282777-upload-your-cover-file)
  — cover upload and project-template guidance;
- [Common Retail Distribution Rejection Reasons](https://help.lulu.com/en/support/solutions/articles/64000295259-common-retail-distribution-rejection-reasons)
  — common metadata and file mismatches; and
- [Global Distribution Print Exclusions](https://help.lulu.com/en/support/solutions/articles/64000267552-global-distribution-print-exclusions)
  — excluded content and project types.

## Prerequisites

Lulu interior candidate preflight requires Poppler's `pdfinfo` and `pdffonts`.
The broader `scripts/audit-generated-cme-pdfs.py` audit additionally requires
`pdftotext`, but `pdftotext` is not a `preflight-lulu` dependency.

`rsvg-convert` from librsvg is optional. It is needed only when
`scripts/cme-cover template` writes PDF directly; SVG cover templates do not
require it.

## Interior candidate

Inspect the plan immediately before building a 5×8 paperback interior candidate
under `build/`:

```bash
scripts/cme-build plan CME/source/CME_from_OTA/Gawain.xml \
  --profile lulu-paperback-5x8-print-pdf \
  --output build/lulu/Gawain/Gawain-interior.pdf
scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml \
  --profile lulu-paperback-5x8-print-pdf \
  --output build/lulu/Gawain/Gawain-interior.pdf
```

The legacy “Lulu-ready” text retained by `list-profiles` describes geometry
only; it never makes this candidate upload-ready or bypasses the gates below.

The profile's exact geometry is:

- PDF paper: `paperwidth=5.25in`, `paperheight=8.25in` (`378×594 pt`);
- text layout: `layoutwidth=5in`, `layoutheight=8in`; and
- layout offsets: `layouthoffset=0.125in`, `layoutvoffset=0.125in`.

Thus the 5×8 in layout sits inside a page with 0.125 in bleed on each edge.
These values are owned by `config/cme-build/profiles.toml`; inspect a
`scripts/cme-build plan` after any Pandoc geometry override.

## Automated preflight

Human-readable form:

```bash
scripts/cme-build preflight-lulu build/lulu/Gawain/Gawain-interior.pdf \
  --trim 5x8 \
  --binding paperback-perfect
```

Machine-readable form:

```bash
scripts/cme-build preflight-lulu build/lulu/Gawain/Gawain-interior.pdf \
  --trim 5x8 \
  --binding paperback-perfect \
  --json > build/lulu/Gawain/preflight.json
```

The JSON object includes the PDF, trim, binding, bleed, page count, actual and
expected page sizes, encryption state, parsed font rows, individual checks, and
an overall `passed` boolean.

Exit status is part of the interface:

- **0**: every completed check passed;
- **1**: preflight completed but one or more checks failed; and
- **2**: a CLI/profile/configuration, unsupported trim or binding, missing or
  unusable external tool, or PDF parsing error was reported by `cme-build`.

Validation order determines precedence. A missing PDF completes the failed
`file-exists` check and returns 1 before binding validation, even when the
binding is also unsupported. Unsupported binding returns 2 only when execution
reaches that validation. Invalid trim is a CLI error and returns 2, including
when the PDF is missing. Missing or failed `pdfinfo`/`pdffonts` is an error, not
a silently skipped check. Machine callers must check both the JSON `passed`
value and process status; the presence of a JSON file alone is not success.

Preflight checks:

- the file exists;
- the first page size matches trim plus bleed;
- all pages have one page size;
- the PDF is not encrypted;
- paperback-perfect page count is 32–800; and
- every font reported by `pdffonts` is embedded.

Preflight does not judge title/author correctness, body placement, page rhythm,
missing glyphs, cover alignment, or Lulu's rendered upload preview.

## Covers

A paperback cover is a separate, single-page spread:

```text
back cover | spine | front cover
```

Compute dimensions from the final interior candidate's page count:

```bash
pages=$(pdfinfo build/lulu/Gawain/Gawain-interior.pdf | awk -F: '/^Pages:/{gsub(/^ +/,"",$2); print $2}')
scripts/cme-cover plan --trim 5x8 --binding paperback-perfect --pages "$pages"
```

Generate a guide template:

```bash
scripts/cme-cover template \
  --trim 5x8 \
  --binding paperback-perfect \
  --pages "$pages" \
  --title "Sir Gawain and the Green Knight" \
  --author "Kyvero Press" \
  --output build/lulu/Gawain/Gawain-cover-template.svg
```

The helper uses this repository-local softcover perfect-bound formula:

```text
spine_width_in = pages / 444 + 0.06
cover_width_in = 5 + spine_width + 5 + 0.25
cover_height_in = 8 + 0.25
```

This formula is an implementation aid, not authoritative Lulu policy. The exact
project template downloaded from Lulu remains authoritative for dimensions and
guides. The repository template is not upload-ready cover art: remove its guides
and compare final art with that exact Lulu template for the selected paper,
binding, final page count, and sales channel.

## Page count, metadata, and manual review

For Lulu paperback perfect bound:

- the interior candidate must contain 32–800 pages;
- do not use spine text below 100 pages; and
- a short work below 32 pages needs bundling, another product, or a different
  publication plan.

Before approval, inspect the complete Lulu upload preview and a physical proof.
Review trim/bleed placement, blank and boundary pages, TOC destinations,
lettrines, verse numbers, running heads, metadata, missing glyphs, font rendering,
and cover/spine/barcode placement. Automated warnings from the generated-PDF
and typography audits require human disposition; `--allow-issues` only permits
report generation and is not publication approval.

## Distribution cautions

Lulu Global Distribution has stricter requirements than private or Lulu
Bookstore projects:

- ISBN is required;
- title, subtitle, and author must match exactly across project metadata, cover,
  title page, copyright/colophon page, and running heads;
- the copyright page must include title/subtitle, author, copyright date, and
  print ISBN;
- the cover barcode must match the project ISBN;
- print and ebook projects need distinct ISBNs when ISBNs are assigned; and
- freely available public-domain or aggregated public-domain content may be
  ineligible for Global Distribution under Lulu's current rules.

Treat private, direct-sale, or Lulu Bookstore publication as the default until
each title's metadata, rights status, cover, proof, and distribution eligibility
have been reviewed against Lulu's current requirements.
