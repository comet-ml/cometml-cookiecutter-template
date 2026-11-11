# AGENTS.md

Briefing for AI coding assistants working in this repo. Claude Code loads it through `CLAUDE.md`;
other agents (Codex, Cursor, Aider) read it directly.

## Project

**{{ cookiecutter.project_name }}** - {{ cookiecutter.description }}

## Stack

- **Python** {{ cookiecutter.python_version }}, managed by [`uv`](https://docs.astral.sh/uv/) (`uv sync`, `uv add`, `uv run`)
- **Experiment tracking**: [Comet EM](https://www.comet.com/docs/v2/) via the `comet-ml` SDK
- **ML framework**: {{ cookiecutter.framework }}
- **Layout**: `src/` layout, package `{{ cookiecutter.module_name }}`
- **Agent access to Comet**: the Comet MCP server, see the section below.

## Layout

```text
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

## The lifecycle

`make data -> make train -> make sweep -> /promote-model -> webhook -> deploy-model.yml -> make predict`.
The README's "Lifecycle" table says what each step does in Comet; `.claude/rules/comet-em-best-practices.md`
holds the conventions behind it. `train.py` ends with one `summary:` line
(`name=... dataset=iris-dataset:<v> <metric>=<final> ... registered=<version|none>`) that the skills read.

## Credentials

- `.env` is gitignored and the Read tool is denied on it in `.claude/settings.json`. Never hardcode or print
  `COMET_API_KEY`. `comet_ml.start()` and `comet_ml.API()` read it from the environment.
- CI uses a Comet **Service Account** key as the `COMET_API_KEY` repository secret.

## Before every commit

- `CHANGELOG.md` under `## [Unreleased]` when `src/` changed (`.claude/rules/changelog-discipline.md`).
- `make lint && make test`. `uv run pre-commit install` once per clone runs ruff and nbstripout.

## Comet MCP server

`.mcp.json` registers [`comet-mcp`](https://www.comet.com/docs/v2/api-and-sdk/mcp-server/overview/) and
`.claude/settings.json` pre-approves it; tools appear as `mcp__comet-mcp__<tool>`. The server reads
experiments only: no registry reads or writes (use `scripts/registry_mutate.py`), no experiment creation.

- It reads `COMET_API_KEY` / `COMET_WORKSPACE` from the **shell**, not from `.env`: launch Claude Code
  after `set -a && source .env && set +a` (or use direnv). Training and the scripts load `.env`
  themselves, so this only matters for the server.
- Always pass `workspace=` and `project_name=` from `.env`; without them the server queries the
  account's default workspace and project `general`.

| Need | Tool |
|------|------|
| Latest runs | `list_experiments(workspace, project_name, page_size=N, sort_by="startTime", sort_order="desc")` |
| Final and best metric values | `get_experiment_summary(experiment_id)` ("best" is the max, wrong for losses) |
| Curves | `get_experiment_training_progress(experiment_id, metric_names)` / `get_experiment_metric_data(experiment_ids, metric_names, x_axis)` |
| Hyperparameters, tags, URL | `get_experiment_parameters`, `get_experiment_details` |
| Runs by tag / by metric | `find_tagged_experiments(tag, ...)`, `query_experiments(name, comparison, value, ...)` |
| Many runs at once | `experiment_spreadsheet(workspace, project_name, experiment_keys)` (CSV) |
| Why a run failed | `get_experiment_output(experiment_id)` (stdout/stderr), `get_experiment_code`, `get_experiment_assets` / `analyze_experiment_asset` |
| Project overview | `list_projects`, `get_project_details`, `get_all_experiments_summary`, `get_project_tags`, `get_project_logged_item_names`, `validate_project`, `get_default_workspace`, `get_session_info` |

When a tool errors, say so and fall back to the SDK (it reads the key from the environment or
`~/.comet.config`):

```bash
uv run python - <<'EOF'
from comet_ml import API
from {{ cookiecutter.module_name }} import config

api = API()
ws = config.COMET_WORKSPACE or api.get_default_workspace()
latest = api.get_experiments(ws, config.COMET_PROJECT_NAME, page=1, page_size=5,
                             sort_by="startTime", sort_order="desc")
for exp in latest:                                   # or [api.get_experiment_by_key("<key>")]
    print(exp.name, exp.url, exp.get_tags())
    print({m["name"]: (m["valueCurrent"], m["valueMin"], m["valueMax"]) for m in exp.get_metrics_summary()})
    print({p["name"]: p["valueCurrent"] for p in exp.get_parameters_summary()})
EOF
```

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
