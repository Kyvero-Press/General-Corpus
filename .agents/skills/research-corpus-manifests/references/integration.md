# Integration and one-book commits

Read this only when integrating a completed research branch into the main
worktree.

## Integrate one work at a time

1. Confirm the main worktree contains no unrelated staged changes.
2. Bring in only the finished work's metadata and lineage files.
3. Review the agent's direct sources, claims, uncertainty, access checks, and
   reusable lessons. Correct overstatement before indexing.
4. Improve the smallest matching skill reference only when the lesson changes
   a future decision. Merge with an existing rule when possible.
5. Rebuild both discovery indexes deterministically:

   ```bash
   python3 scripts/rebuild-manifest-indexes.py
   ```

6. Run the changed-scope gate against the remote branch:

   ```bash
   python3 scripts/run-changed-gate.py --base origin/main
   ```

   The normal one-book path validates each changed manifest pair and its
   production viewer projection, checks that both indexes are deterministic,
   checks corpus-wide normalized vocabulary labels, validates the skill only
   when it changed, and runs `git diff --check`. It deliberately skips the
   full catalog rebuild and unrelated unit suites. Use `--dry-run` to inspect
   the selected commands.

   Changes to shared schemas, manifest validators, the index generator, the CME
   source checkout, or the publication-set manifest automatically escalate to
   the full corpus gate. A deleted or renamed half of a manifest pair also
   escalates. Force that gate with `--full` for a periodic batch audit or final
   corpus-completion audit; do not run it before every one-book push.

7. Stage only that work's pair, both indexes, and any narrowly required skill,
   validator, schema, documentation, or test change.
8. Commit with the work ID and title, push the current main branch, and verify
   it matches the remote before integrating another completed work.

## Avoid concurrent contamination

Research agents should work in dedicated Git worktrees and branches. They must
not edit shared indexes or the skill. If several agents finish together,
integrate and push their branches sequentially. Never validate one book while
another finished book's unindexed files are sitting uncommitted in the main
worktree.

Create a disk-efficient worktree with:

```bash
python3 scripts/create-manifest-research-worktree.py WORK_ID
```

The helper sparsely checks out only that work's XML from the CME submodule.
Ignored `source-cache/` files are local to each worktree. Pass the main
checkout as the cache helper's `--root`, or hard-link every completed cache
artifact into the main checkout's `source-cache/WORK_ID/` before integration.
Verify file counts, inodes, checksums, and main-checkout manifest validation;
never remove a research worktree while it holds the only copy of a source.
When validating the pair before cherry-pick, true-hard-link the canonical main
cache back into the worktree's matching path so its repository-relative
references resolve there too; remove that disposable mirror with the worktree.

## Skill update test

After each work, ask:

1. Did the agent encounter a decision not already covered?
2. Will the rule apply to another corpus item?
3. Can it replace or refine an existing sentence rather than add a new case?
4. Is the book-specific evidence already better placed in its manifests?

If the first two answers are no, validation with no skill text change still
counts as reviewing the skill for that completed book.
