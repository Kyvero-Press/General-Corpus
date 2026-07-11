# XML formats and inventory

See [architecture.md](architecture.md) for the complete production pipeline and
component ownership.

The format table below and `docs/xml-format-manifest.tsv` are a generation-time
snapshot of `CME/source`, which contained **307 XML files** when the inventory was
last generated. This document now combines maintained explanatory prose with
generated inventory data. The snapshot is not a timeless corpus total and does
not define the PDF publication set. Duplicate stems, repaired/recent variants,
and non-running-text inputs mean source count cannot be equated with `dist/`
count. Follow [Inventory provenance](#inventory-provenance) to refresh the
inventory without replacing the maintained sections of this document.

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

## Converter behavior

`scripts/cme_xml_to_html.py` detects `dlpstextclass`, ETS with `TEMPHEAD` or
`HEADER`, generic ETS, `tei2`, and `headwords`. It selects the known readable
payload: `TEXT` for DLPS/TEI.2; direct or grouped `EEBO/TEXT` for ETS; and the
`HEADWORDS` root for lexical records. A direct `BODY` is a narrow fallback when
a known wrapper is missing. The converter deliberately renders no body rather
than treating headers or revision metadata as primary text.

Parsing first uses strict XML. Unless `--strict` is given, a strict parse failure
is reparsed with `lxml` recovery and reported on standard error; source metadata
also carries a visible recovery warning when that metadata block is enabled.
Recovery makes malformed input reviewable but does not guarantee an editorially
correct interpretation.

Direct HTML conversion is useful for converter debugging:

```bash
mkdir -p build/xml
python3 scripts/cme_xml_to_html.py --format auto \
  CME/source/CME_from_OTA/Gawain.xml > build/xml/Gawain.html
```

The converter's normal XML options are `--format`, `--drop-notes`,
`--preserve-milestones`, and `--strict`; build plumbing also uses
`--omit-source-metadata`, `--verse-line-metadata`, and `--colophon-tex`.

### Transcriptional word-break verbar (U+2223)

The U+2223 character `∣` is treated as a transcriptional word-break marker only
when its immediately adjacent visible characters are alphabetic within one
maximal inline flow. For example, `dili∣gatis` becomes `diligatis`, and the join
may cross ordinary inline emphasis markup in either direction.

A flow cannot cross a block, `LB`, NOTE/NOTE1, GAP, milestone such as PB/EPB/FW,
or (for headwords) ENTRY/FORM boundary. Included note content is normalized in
its own flow; an omitted note remains a boundary. Consequently, standalone,
leading, trailing, punctuation-adjacent, and digit-adjacent U+2223 markers stay
visible. ASCII `|`, double vertical line `‖`, and other lookalikes are untouched.

Only the selected rendered payload is normalized. When it contains U+2223,
`render_document()` copies the source tree, changes that copy, and leaves source
metadata and the caller's XML tree unchanged. A marker-free selected payload
uses the no-copy fast path. These rules apply before Pandoc, so all final output
formats receive the same normalized readable text.

## Direct and compatibility wrappers

The direct wrappers normalize XML to standalone HTML and then call Pandoc. Use a
format-specific name only when the category is already known; otherwise use the
auto-detecting wrapper:

```bash
scripts/pandoc-dlpstextclass INPUT.xml OUTPUT.html [PANDOC_OPTIONS...]
scripts/pandoc-ets INPUT.xml OUTPUT.epub [PANDOC_OPTIONS...]
scripts/pandoc-tei2 INPUT.xml OUTPUT.pdf --pdf-engine=xelatex
scripts/pandoc-headwords INPUT.xml OUTPUT.html
scripts/pandoc-cme-xml INPUT.xml OUTPUT.docx
scripts/pandoc-all CME/source build/pandoc html
```

For `scripts/pandoc-cme-xml`, XML options (`--xml-format`, `--drop-notes`,
`--preserve-milestones`, and `--strict`) go before `INPUT.xml`. The wrapper's
`--lettrine MODE` may appear before the input or after the output and is removed
before Pandoc runs. Other arguments after `OUTPUT` pass to Pandoc. The recursive
`scripts/pandoc-all` forwards arguments after its output extension to each
`scripts/pandoc-cme-xml` invocation.

These wrappers retain hard-coded LaTeX/PDF defaults for compatibility. The
recommended production interface is `scripts/cme-build`; see
[build-profiles.md](build-profiles.md). Profile XML flags come from
`config/cme-build/profiles.toml` and the selected definitions in
`config/cme-build/modules.toml`. Arguments after `--` on profile `plan` or
`single` are Pandoc passthrough and cannot be used to inject arbitrary XML
converter options. Inspect a profile plan for the effective XML command.

## Inventory provenance

The format table, its supporting inventory details, and
`docs/xml-format-manifest.tsv` are generated from the same scan. Because this
document now combines that generated inventory data with maintained explanatory
prose, always generate refresh candidates at temporary paths:

```bash
mkdir -p build/inventory-refresh
scripts/categorize-xml-formats.py CME/source \
  --manifest build/inventory-refresh/xml-format-manifest.tsv \
  --output build/inventory-refresh/xml-formats.generated.md
```

Review the temporary Markdown report and TSV together. If an inventory refresh
is approved, deliberately integrate only inventory data and count changes from
the generated report into this maintained document, and update
`docs/xml-format-manifest.tsv` from the reviewed temporary TSV in the same
change.

**Warning:** pointing `--output` at `docs/xml-formats.md` replaces the whole
document with the generator's legacy report and discards all maintained sections
until/unless the generator is modernized. Do not use the maintained document as
the generator's output path.

The manifest inventories source files and detected payloads; it is not an
approved source-to-publication mapping and does not imply that each XML file
should produce one PDF.

