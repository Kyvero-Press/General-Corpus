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

## Configuration

Profiles live in `config/cme-build/profiles.toml`; reusable modules live in
`config/cme-build/modules.toml`. Pandoc variables are stored as ordered arrays of
`{ name, value }` records so repeated variables such as `mainfontoptions` and
`geometry` are preserved.

The print profiles preserve the existing geometry override rule: the default
5×8 `geometry` variables are added only when the appended Pandoc arguments do
not already set either `geometry` or `papersize`.
