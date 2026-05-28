---
name: update-readme
description: Regenerate the auto-generated sections of README.md (project tree, common-tasks table) to reflect the current state of pyproject.toml, the Makefile, and src/. Use when project structure changes, deps change, or those sections drift from reality. Preserves any user-authored prose outside the AUTO-GENERATED markers.
---

# Update README

Regenerate the auto-generated sections of `README.md` so they reflect what's actually in the repo.

## What is auto-generated

The README has marker pairs like:

```markdown
<!-- AUTO-GENERATED:tree -->
... content ...
<!-- /AUTO-GENERATED:tree -->
```

Everything **inside** the marker pair is owned by this skill and will be replaced. Everything **outside** is user-authored — preserve it verbatim.

Sections currently under marker control:

- `AUTO-GENERATED:tree` — the project layout tree
- `AUTO-GENERATED:tasks` (if present) — the common-tasks table

## Procedure

1. **Inspect current state**:
   - List the top-level directories with `ls -la` (filter out `.git`, `.venv`, `__pycache__`).
   - List `src/<module>/` contents.
   - Parse `pyproject.toml` for `dependencies` and `optional-dependencies`.
   - Parse `Makefile` `.PHONY` targets.

2. **Rebuild the tree** as ASCII inside the `AUTO-GENERATED:tree` block. Skip:
   - dot-directories except `.claude/`
   - `__pycache__`, `.venv`, `.ruff_cache`, `.pytest_cache`
   - files under `data/`, `models/`, `reports/figures/` (just show the folder)

3. **Rebuild the common-tasks table** (if the `AUTO-GENERATED:tasks` block exists) from the Makefile's `.PHONY` targets. Map each target to a one-line description from the `help` target if present.

4. **Edit** `README.md` in place. Touch nothing outside the marker pairs.

5. **Diff check**: `git diff README.md`. If anything outside a marker block changed, revert and report the bug — the marker logic is broken.

6. **Stage**: tell the user to review and `git add README.md`. Do **not** auto-stage.

## Adding a new auto-generated section

If the user asks for a new section to be machine-managed:

1. Pick a stable marker name (kebab-case): `AUTO-GENERATED:deps`.
2. Insert the marker pair into `README.md` in the right place with placeholder content.
3. Extend this skill: add a "Procedure" step for the new section.

## Anti-patterns

- Rewriting the whole README — touches user prose. Stick to marker blocks.
- Adding emojis or marketing copy. The README documents what exists.
- Drifting from the layout actually present on disk (e.g., listing `notebooks/` if it's been deleted).
