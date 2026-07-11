# Manifest systems

General Corpus keeps two complementary JSON manifest systems:

- [`work-metadata/`](work-metadata/) describes intellectual and content units:
  titles, authorship, dates, regions, languages, forms, genres, subjects, tags,
  summaries, and content structure.
- [`lineage/`](lineage/) describes material and digital provenance: editions,
  manuscript witnesses, encodings, repository artifacts, reproductions,
  access, rights, and supporting evidence.

The systems are linked by stable work and entity IDs, but their facts are not
silently inherited. In particular, an editor is not automatically the author
of an anonymous historical text, a manuscript's holding location is not its
origin region, and a witness date is not automatically a composition date.

Coverage is incremental. Consult each system's `index.json` for the records
currently available.
