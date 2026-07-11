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

6. Validate:

   ```bash
   python3 scripts/validate-lineage-manifests.py
   python3 scripts/validate-work-metadata-manifests.py
   python3 scripts/validate-manifest-pair.py WORK_ID
   python3 -m unittest tests.test_lineage_manifests tests.test_work_metadata_manifests
   python3 scripts/build-corpus-viewer-catalog.py --output-root build/corpus-viewer/public
   python3 /home/tay/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
     .agents/skills/research-corpus-manifests
   git diff --check
   ```

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

## Skill update test

After each work, ask:

1. Did the agent encounter a decision not already covered?
2. Will the rule apply to another corpus item?
3. Can it replace or refine an existing sentence rather than add a new case?
4. Is the book-specific evidence already better placed in its manifests?

If the first two answers are no, validation with no skill text change still
counts as reviewing the skill for that completed book.
