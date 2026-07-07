# Lulu production checklist

This repository can generate review PDFs at the finished trim size and Lulu-oriented
production interiors with bleed. Lulu print projects still require manual project
metadata and a separate cover file.

## Interior PDFs

Use the Lulu profile for 5×8 paperback interiors:

```bash
scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml \
  --profile lulu-paperback-5x8-print-pdf \
  --output build/lulu/Gawain/Gawain-interior.pdf
```

For a 5×8 trim, Lulu asks for 0.125 in bleed on each edge, so the generated PDF
page size should be 5.25×8.25 in (`378×594 pt`). The profile keeps the 5×8 text
layout inside the bleed-sized page by using geometry layout dimensions and 0.125
in offsets.

Run preflight:

```bash
scripts/cme-build preflight-lulu build/lulu/Gawain/Gawain-interior.pdf \
  --trim 5x8 \
  --binding paperback-perfect
```

The preflight checks:

- file exists;
- first page size matches trim + bleed;
- all pages share one page size;
- PDF is not encrypted;
- paperback-perfect page count is 32–800;
- all fonts reported by `pdffonts` are embedded.

It does not replace Lulu's upload preview/proof copy review.

## Covers

Lulu print covers are separate from the interior PDF. A paperback cover is a
single-page spread in this order:

```text
back cover | spine | front cover
```

Generate a cover plan from the final interior page count:

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

If `rsvg-convert` is available, the template can also be written as PDF by using
`.pdf` as the output extension.

The local cover template uses Lulu's softcover perfect-bound spine formula:

```text
spine_width_in = pages / 444 + 0.06
```

A 5×8 paperback cover spread uses:

```text
cover_width_in  = 5 + spine_width + 5 + 0.25
cover_height_in = 8 + 0.25
```

The generated template includes guide lines for bleed, trim, safe areas, spine,
and barcode placement. Do **not** upload the guide template as a final cover with
the guide lines still visible. Use it as a design base, or compare final cover
art against Lulu's downloaded template for the exact project, paper, binding,
page count, and sales channel.

## Page count and spine rules

For Lulu paperback perfect bound:

- minimum: 32 interior pages;
- maximum: 800 interior pages;
- do not include spine text when the book has fewer than 100 pages.

Short corpus works below 32 pages need bundling, another binding/product, or a
non-standalone publication plan.

## Distribution cautions

Lulu Global Distribution has stricter requirements than private/Lulu Bookstore
projects:

- ISBN is required;
- title/subtitle/author must match exactly across project metadata, cover,
  title page, copyright page, and running heads;
- copyright page must include title/subtitle, author, copyright date, and print
  ISBN;
- cover barcode must match the project ISBN;
- each print/ebook project needs its own ISBN if ISBNs are assigned;
- Lulu's distribution rules state that freely available public-domain or
  aggregated public-domain content may be ineligible for Global Distribution.

Treat Lulu Bookstore/private/direct sales as the default until each title's
metadata, public-domain status, and distribution eligibility have been reviewed.
