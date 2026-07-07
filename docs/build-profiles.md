# CME build profiles

The profile build layer sits beside the existing wrappers. It does not change
`scripts/pandoc-cme-xml` or `scripts/pandoc-all`; use those commands as before
when you want the legacy behavior.

## Commands

```bash
scripts/cme-build list-profiles
scripts/cme-build plan CME/source/CME_from_OTA/Gawain.xml --profile print-pdf
scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml --profile print-pdf --output build/profile/Gawain.pdf
scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml --profile reader-pdf-no-notes --output build/profile/Gawain.reader.pdf
scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml --profile epub --output build/profile/Gawain.epub
scripts/cme-build single CME/source/CME_from_OTA/Gawain.xml --profile lulu-paperback-5x8-print-pdf --output build/profile/Gawain.lulu.pdf
scripts/cme-build preflight-lulu build/profile/Gawain.lulu.pdf --trim 5x8 --binding paperback-perfect
scripts/cme-cover plan --trim 5x8 --binding paperback-perfect --pages 80
scripts/cme-cover template --trim 5x8 --binding paperback-perfect --pages 80 --output build/covers/Gawain-template.svg
```

`plan` prints JSON showing the XML normalization command, generated temporary
artifacts, expanded Pandoc variables, modules, filters, and final Pandoc command.
Extra Pandoc options may be appended to `plan` or `single`; they are preserved at
the end of the Pandoc command.

## Initial profiles

- `print-pdf` — 5×8 PDF, `xelatex`, book document class, Junicode fonts, notes
  converted to LaTeX footnotes, plain lettrines, running heads, verse-line
  numbers, page-break helpers, frontmatter, and generated colophon.
- `reader-pdf-no-notes` — same print shape, but XML notes are dropped and the
  footnote filter is omitted.
- `epub` — EPUB3 from normalized HTML with inline notes and no LaTeX headers or
  Lua filters.
- `lulu-paperback-5x8-print-pdf` — Lulu-oriented paperback interior profile. It
  keeps the same book modules as `print-pdf`, but emits 5.25×8.25 in PDF pages
  for a 5×8 trim with 0.125 in bleed on each edge.

## Configuration

Profiles live in `config/cme-build/profiles.toml`; reusable modules live in
`config/cme-build/modules.toml`. Pandoc variables are stored as ordered arrays of
`{ name, value }` records so repeated variables such as `mainfontoptions` and
`geometry` are preserved.

The print profiles preserve the existing geometry override rule: the default
`geometry` variables are added only when the appended Pandoc arguments do not
already set either `geometry` or `papersize`.

## Lulu production helpers

`lulu-paperback-5x8-print-pdf` is intended for Lulu interior upload checks. Lulu
asks for 0.125 in bleed on each edge, so this profile uses `paperwidth=5.25in`,
`paperheight=8.25in`, `layoutwidth=5in`, `layoutheight=8in`, and 0.125 in layout
offsets. Run `preflight-lulu` on generated interiors before upload:

```bash
scripts/cme-build preflight-lulu build/profile/Gawain.lulu.pdf --trim 5x8 --binding paperback-perfect
```

Covers are generated separately from interiors. Use `scripts/cme-cover plan` to
compute page-count-dependent spine and spread dimensions, and `scripts/cme-cover
template` to create a guide SVG/PDF. The template contains guide lines and is
not itself an upload-ready cover; remove guides or use it as a design base for a
final cover PDF.
