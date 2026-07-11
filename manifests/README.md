# Manifest systems

General Corpus keeps complementary JSON manifest systems:

- [`work-metadata/`](work-metadata/) describes intellectual and content units:
  titles, authorship, dates, regions, languages, forms, genres, subjects, tags,
  summaries, and content structure.
- [`lineage/`](lineage/) describes material and digital provenance: editions,
  manuscript witnesses, encodings, repository artifacts, reproductions,
  access, rights, and supporting evidence.
- [`publication-set/`](publication-set/) records the exact canonical PDF
  snapshot required by the default corpus viewer deployment.

The descriptive and lineage systems are linked by stable work and entity IDs,
but their facts are not silently inherited. In particular, an editor is not
automatically the author of an anonymous historical text, a manuscript's
holding location is not its origin region, and a witness date is not
automatically a composition date. The publication-set snapshot is an artifact
identity boundary, not a source-lineage substitute.

Descriptive and lineage coverage is incremental; consult their `index.json`
files for the records currently available. The publication-set README explains
when its complete artifact snapshot may be replaced.

For agent-assisted source research and cataloging, use the project
[`research-corpus-manifests`](../.agents/skills/research-corpus-manifests/SKILL.md)
skill. Its field guide defines source priority, layer boundaries, rights
scoping, evidence requirements, validation, and reusable lessons from
completed records.
