# XML format inventory

Scanned `CME/source` and found **307 XML files**.

| Format | Files | Strict XML failures | Main root/signature | Primary text payload |
|---|---:|---:|---|---|
| `dlpstextclass` | 148 | 0 | `DLPSTEXTCLASS/HEADER/TEXT` | `DLPSTEXTCLASS/TEXT` |
| `ets-header-eebo` | 7 | 0 | `ETS/HEADER/EEBO` | `ETS/EEBO/TEXT` |
| `ets-temphead-eebo` | 150 | 1 | `ETS/TEMPHEAD/EEBO` | `ETS/EEBO/TEXT` |
| `headwords` | 1 | 0 | `HEADWORDS/ENTRY/ENTRY/ENTRY/ENTRY` | `HEADWORDS` |
| `tei2` | 1 | 0 | `TEI.2/TEIHEADER/TEXT` | `TEI.2/TEXT` |

## Format categories

### `dlpstextclass`

Older DLPS/HTI TEI-like files. Header lives in `HEADER`; text lives in `TEXT` with `FRONT`, `BODY`, `BACK`, `DIV1`...`DIV7`, `P`, `LG`, `L`, `NOTE1`, `HI1`, `PB`, and `MILESTONE`.

Directories:
- `CME/source/CME_phase_1-2`: 129
- `CME/source/CME_from_OTA`: 16
- `CME/source/recent_changes`: 2
- `CME/source/CME_from_CTA`: 1

Most common elements:
- `L` (874137), `HI1` (286199), `NOTE1` (241294), `MILESTONE` (112355), `EPB` (69331), `PB` (69119), `P` (43773), `LG` (32010), `HEAD` (26798), `CELL` (23547), `DIV2` (9769), `ITEM` (8964)

Sample files:
- `CME/source/CME_from_CTA/DunTwa.xml`
- `CME/source/CME_from_OTA/AllitMA.xml`
- `CME/source/CME_from_OTA/CT.xml`
- `CME/source/CME_from_OTA/ChancEng.xml`
- `CME/source/CME_from_OTA/Everyman.xml`
- `CME/source/CME_from_OTA/Gawain.xml`
- `CME/source/CME_from_OTA/Herebert.xml`
- `CME/source/CME_from_OTA/Ipomydon.xml`

### `ets-header-eebo`

Newer repaired/addition ETS files where the bibliographic `HEADER` has replaced `TEMPHEAD`; payload is still under `EEBO/TEXT`.

Directories:
- `CME/source/recent_changes`: 7

Most common elements:
- `L` (20558), `LB` (9891), `MILESTONE` (4835), `P` (1013), `HI` (998), `Q` (216), `HEAD` (142), `PB` (135), `SUPPLIED` (123), `DIV2` (46), `DIV1` (30), `TITLE` (28)

Sample files:
- `CME/source/recent_changes/additions_2023/CME301.xml`
- `CME/source/recent_changes/additions_2023/CME302.xml`
- `CME/source/recent_changes/additions_2023/CME90022.xml`
- `CME/source/recent_changes/additions_2023/CME90033.xml`
- `CME/source/recent_changes/additions_2023/CME90053.xml`
- `CME/source/recent_changes/additions_2023/CME90162.xml`
- `CME/source/recent_changes/additions_2023/CME90174.xml`

### `ets-temphead-eebo`

Phase-3 EEBO/TCP-derived files with root `ETS`, a temporary revision header in `TEMPHEAD`, and payload under `EEBO/TEXT` or `EEBO/GROUP/TEXT`.

Directories:
- `CME/source/CME_phase_3`: 143
- `CME/source/CME_from_OTA`: 5
- `CME/source/CME_additions`: 2

Most common elements:
- `L` (374435), `HI` (358732), `MILESTONE` (94258), `NOTE` (90985), `ITEM` (25276), `LG` (22542), `SUP` (19126), `HEAD` (18970), `P` (17761), `PB` (17018), `LB` (11898), `SUB` (10463)

Sample files:
- `CME/source/CME_additions/CME301.xml`
- `CME/source/CME_additions/CME302.xml`
- `CME/source/CME_from_OTA/CME90022.xml`
- `CME/source/CME_from_OTA/CME90033.xml`
- `CME/source/CME_from_OTA/CME90053.xml`
- `CME/source/CME_from_OTA/CME90162.xml`
- `CME/source/CME_from_OTA/CME90174.xml`
- `CME/source/CME_phase_3/CME00002.xml`

Strict XML failures recovered by the converter:
- `CME/source/CME_from_OTA/CME90022.xml`

### `headwords`

Lexical headword list, not a running text. It is converted as flowing paragraph records rather than prose/verse so large PDFs avoid oversized LaTeX tables or labels.

Directories:
- `CME/source/old_files`: 1

Most common elements:
- `REG` (238451), `ORIG` (193605), `ORTH` (136011), `PS` (57768), `HDORTH` (57593), `ENTRY` (56899), `FORM` (56899), `POS` (56899), `HI` (691), `HEADWORDS` (1)

Sample files:
- `CME/source/old_files/Corpus/MidEngCorpus/headwords_forms_and_IDs.202112.xml`

### `tei2`

Single legacy `TEI.2` file with a standard-ish `TEIHEADER` and `TEXT/BODY`.

Directories:
- `CME/source/CME_from_OTA`: 1

Most common elements:
- `PB` (103), `P` (90), `HEAD` (87), `DIV1` (86), `TITLE` (2), `AUTHOR` (2), `EDITOR` (2), `RESPSTMT` (2), `NAME` (2), `RESP` (2), `DISTRIBUTOR` (2), `DATE` (2)

Sample files:
- `CME/source/CME_from_OTA/JulianRev.xml`

## Conversion scripts

The scripts in `scripts/` normalize the source XML to HTML and then call Pandoc.
Use the format-specific wrappers when you already know the category, or `pandoc-cme-xml` to auto-detect.

```bash
scripts/pandoc-dlpstextclass INPUT.xml OUTPUT.html [PANDOC_OPTIONS...]
scripts/pandoc-ets INPUT.xml OUTPUT.epub [PANDOC_OPTIONS...]
scripts/pandoc-tei2 INPUT.xml OUTPUT.pdf --pdf-engine=xelatex
scripts/pandoc-headwords INPUT.xml OUTPUT.html
scripts/pandoc-cme-xml INPUT.xml OUTPUT.docx
scripts/pandoc-all CME/source build/pandoc html
```

Useful XML-side options accepted before `INPUT.xml`: `--drop-notes`, `--preserve-milestones`, and `--strict`.
All remaining arguments after `OUTPUT` are passed directly to Pandoc.
For `.tex`, `.latex`, and `.pdf` output, `pandoc-cme-xml` defaults to a book-style LaTeX front matter sequence (title page, colophon, table of contents), the `book` document class, and Junicode (`Junicode-Regular.otf` from TeX Live's `junicode` package). When the XML includes a creation/original date, that date appears on the title page and in the colophon. It also automatically adds the project LaTeX pagination header and Lua filter in `scripts/pandoc-latex-pagebreaks.*` to reduce orphaned/widowed prose and verse fragments. Pass your own Pandoc `documentclass` or `mainfont` variables to override those defaults.

A complete per-file TSV manifest is generated by:

```bash
scripts/categorize-xml-formats.py CME/source --manifest docs/xml-format-manifest.tsv --output docs/xml-formats.md
```

