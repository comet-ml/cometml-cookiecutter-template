---
name: update-makefile
description: Audit the Makefile against the tooling actually installed (ruff, pytest, mypy, etc.) and the scripts under src/<module>/, then propose missing targets or fix stale ones. Use when adding a new tool or script that should be invokable via make. Preserves user-added custom targets.
---

# Update Makefile

Keep `Makefile` targets in sync with the tooling installed in `pyproject.toml` and the scripts under `src/<module>/`.

## Canonical targets

These should always exist (the cookiecutter ships them):

| Target | Command |
|--------|---------|
| `install` | `uv sync` |
| `install-dev` | `uv sync --all-extras` |
| `format` | `uv run ruff format src tests` |
| `lint` | `uv run ruff check src tests` |
| `test` | `uv run pytest` |
| `train` | `uv run python -m <module>.train` |
| `clean` | remove caches and build artifacts |
| `help` | print the target list |

If any of these are missing, restore them.

## Conditionally added targets

Inspect `pyproject.toml` `[project.optional-dependencies]` and propose additions when a tool is installed but no Makefile target exists:

| Tool present in deps | Target to add | Command |
|----------------------|---------------|---------|
| `mypy` | `typecheck` | `uv run mypy src` |
| `bandit` | `security` | `uv run bandit -r src` |
| `pre-commit` | `pre-commit` | `uv run pre-commit run --all-files` |
| `mkdocs` | `docs` / `docs-serve` | `uv run mkdocs build` / `uv run mkdocs serve` |
| `nbstripout` | `nb-clean` | `uv run nbstripout notebooks/*.ipynb` |

For new training scripts: if `src/<module>/eval.py` or `src/<module>/predict.py` exists, propose `make eval` and `make predict` targets that invoke them with `uv run python -m`.

## Procedure

1. Read `Makefile` and `pyproject.toml`.
2. Build the expected target set (canonical + conditional).
3. For each missing target, propose the addition.
4. For each existing target whose command is stale (e.g., references a tool not installed), propose the fix.
5. **Do not delete user-added targets** without asking. Treat any unknown target as user-authored.
6. Edit `Makefile` in place. Update the `help` target to list all `.PHONY` targets.
7. Tell the user to review and `git add Makefile`. Do not auto-stage.

## Anti-patterns

- Replacing the entire Makefile — loses user customizations.
- Adding targets for tools that aren't installed — `make foo` will fail with `command not found`.
- Forgetting to update `.PHONY` and `help` when adding a new target.
