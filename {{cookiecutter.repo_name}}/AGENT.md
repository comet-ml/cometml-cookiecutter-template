# AGENT.md

Briefing for AI coding assistants working in this repo (Claude Code, Cursor, Aider, etc.).

## Project

**{{ cookiecutter.project_name }}** — {{ cookiecutter.description }}

## Stack

- **Python** {{ cookiecutter.python_version }}
- **Dependency management**: [`uv`](https://docs.astral.sh/uv/) (use `uv sync`, `uv add`, `uv run`)
- **Experiment tracking**: [Comet EM](https://www.comet.com/docs/v2/) via the `comet-ml` Python SDK
- **ML framework**: {{ cookiecutter.framework }}
- **Layout**: `src/` layout, package = `{{ cookiecutter.module_name }}`

## Layout

```
src/{{ cookiecutter.module_name }}/   # Production Python code
data/{raw,interim,processed,external}/  # Datasets
notebooks/                              # Exploration (push logic to src/)
models/                                 # Trained artifacts
reports/figures/                        # Output figures, plots
tests/                                  # pytest
.claude/{rules,skills}/                 # Agent behavioral rules and skills
```

## How to run things

```bash
make install         # uv sync
make install-dev     # uv sync --all-extras
make train           # run the example experiment in src/{{ cookiecutter.module_name }}/train.py
make test            # pytest
make lint            # ruff check
make format          # ruff format
```

## Logging experiments to Comet

The example in `src/{{ cookiecutter.module_name }}/train.py` shows the canonical shape. Always:

1. Construct `comet_ml.Experiment(api_key=..., workspace=..., project_name=...)` with values from `src/{{ cookiecutter.module_name }}/config.py` (which reads `.env`).
2. Call `experiment.log_parameters(dict)` for hyperparams, `experiment.log_metric(name, value, step=...)` for scalars.
3. Call `experiment.end()` (or use it as a context manager) to flush.

Detailed rules in `.claude/rules/comet-em-best-practices.md`.

## Credentials

- `.env` is gitignored. Never hardcode `COMET_API_KEY` or `COMET_WORKSPACE` in code or notebooks.
- Copy `.env.example` to `.env` and fill in values.

## Before every commit

- Update `CHANGELOG.md` under `## [Unreleased]` — see `.claude/rules/changelog-discipline.md`.
- Run `make lint && make test`.

## Where to look first

- `.claude/rules/` — behavioral rules you must follow.
- `.claude/skills/` — guided multi-step workflows (update-readme, update-makefile, update-changelog).
- `CONTRIBUTING.md` — branch naming, PR checklist.
- `pyproject.toml` — dependency list, tool config.
