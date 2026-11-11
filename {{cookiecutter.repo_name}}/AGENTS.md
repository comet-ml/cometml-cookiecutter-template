# AGENTS.md

Briefing for AI coding assistants working in this repo. Claude Code loads it through `CLAUDE.md`;
other agents (Codex, Cursor, Aider) read it directly.

## Project

**{{ cookiecutter.project_name }}** — {{ cookiecutter.description }}

## Stack

- **Python** {{ cookiecutter.python_version }}, managed by [`uv`](https://docs.astral.sh/uv/) (`uv sync`, `uv add`, `uv run`)
- **Experiment tracking**: [Comet EM](https://www.comet.com/docs/v2/) via the `comet-ml` SDK
- **ML framework**: {{ cookiecutter.framework }}
- **Layout**: `src/` layout, package `{{ cookiecutter.module_name }}`
- **Agent access to Comet**: `.mcp.json` registers the [Comet MCP server](https://www.comet.com/docs/v2/api-and-sdk/mcp-server/overview/)
  (read-only: experiments, metrics, projects; **no registry access**). It needs `COMET_API_KEY` and
  `COMET_WORKSPACE` exported in the shell before launch: `set -a && source .env && set +a`.

## Layout

```
src/{{ cookiecutter.module_name }}/
  config.py        # .env, experiment_name(), thresholds.yaml
  dataset.py       # make data: iris CSVs + the iris-dataset Artifact
  train.py         # make train: one experiment, gated registration
  sweep.py         # make sweep: Optimizer over train()
  predict.py       # make predict: load the Production version
scripts/registry_mutate.py   # registry reads + status/tag changes (used by /promote-model)
thresholds.yaml              # promotion gate (val_accuracy >= 0.9)
.github/workflows/           # ci.yml (lint + tests), deploy-model.yml (registry webhook -> deploy)
.claude/                     # settings.json, rules/, skills/
data/ models/ notebooks/ reports/ tests/
```

## Commands

```bash
make install    # uv sync (runtime + dev)
make data       # build the CSVs, log the dataset Artifact
make train      # one experiment; ARGS="--register --epochs 30" passes flags
make sweep      # Optimizer sweep (tagged `sweep`)
make predict    # predict with the Production registry version
make lint test  # ruff + credential-free pytest
```

## The lifecycle, in one paragraph

`make data` writes `data/processed/iris-*.csv` and logs them once as Artifact `iris-dataset`.
`make train` starts an experiment with `comet_ml.start()`, named `{project}-{model}-{YYYYMMDD}-{HHmm}`,
records which Artifact version it read, logs `train_*` / `val_*` per epoch plus a confusion matrix, logs
the model, and registers the next patch version with `status="Development"` only when `thresholds.yaml`
passes. `/promote-model` moves a version through Staging / QA / Production (and demotes the old holder).
A status change fires the registry webhook, which starts `deploy-model.yml`; `make predict` is what that
workflow runs to fetch and smoke-test the version. The full rules live in
`.claude/rules/comet-em-best-practices.md`.

## Credentials

- `.env` is gitignored and denied to the agent in `.claude/settings.json`. Never hardcode or print
  `COMET_API_KEY`. `comet_ml.start()` and `comet_ml.API()` read it from the environment.
- CI uses a Comet **Service Account** key as the `COMET_API_KEY` repository secret.

## Before every commit

- `CHANGELOG.md` under `## [Unreleased]` when `src/` changed (`.claude/rules/changelog-discipline.md`).
- `make lint && make test`. `uv run pre-commit install` once per clone runs ruff and nbstripout.

## Skills

| Skill | Does | Side effects |
|-------|------|--------------|
| `/run-training` | `make train`, reports name, URL, metrics, registration | new experiment |
| `/evaluate-run <id>` | thresholds.yaml vs a run's final metrics (MCP) | none |
| `/compare-runs ...` | metric + parameter table across runs (MCP) | none |
| `/debug-run <id>` | reads output, curves, code, assets of a run (MCP) | none |
| `/run-sweep` | `make sweep`, summarises trials | many experiments |
| `/promote-model <name>` | status / tag changes with confirmation | registry |
| `/update-changelog` | drafts `[Unreleased]` entries from the diff | edits CHANGELOG.md |

Skills that spend compute or change the registry are user-invoked only (`disable-model-invocation`).

## Typical agentic workflow

1. "Train a new run" -> `/run-training` -> experiment name + URL + whether a version was registered.
2. "Does it pass?" -> `/evaluate-run <id>`.
3. "How does it compare to prod?" -> `/compare-runs <id> vs production` (source run from the registry).
4. "Why did yesterday's run fail?" -> `/debug-run <id>`.
5. "Ship it" -> `/promote-model iris-classifier <id>` -> webhook -> `deploy-model.yml`.
