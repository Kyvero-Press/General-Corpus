# Repository Agent Instructions

Use the project task graph `general-corpus-pandoc-pdf` for any repository change that aims to affect the final/end PDF output, including XML conversion behavior, Pandoc-to-LaTeX output, LaTeX frontmatter, typography, pagination, PDF metadata, or visible PDF layout.

When generating final PDFs for user inspection with the repository default parameters, write or copy them to `./bin/pdf/`. Keep intermediate validation artifacts under `build/` unless the user asks otherwise.

Create that workflow with:

```js
task_graph_create({
  mode: "custom",
  input: "<task>",
  options: { customGraph: "general-corpus-pandoc-pdf" }
})
```

The graph is also configured as the default custom graph in `.pi/task-graph.json`.
