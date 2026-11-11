# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

Python {{ cookiecutter.python_version }} | uv | Comet EM | {{ cookiecutter.framework }}

## Quickstart

```bash
uv sync
cp .env.example .env               # fill in COMET_API_KEY and COMET_WORKSPACE
make train                         # builds the dataset, then runs one experiment
```

The run appears at `https://www.comet.com/<COMET_WORKSPACE>/{{ cookiecutter.repo_name }}`, named
`{{ cookiecutter.repo_name }}-iris-classifier-<YYYYMMDD>-<HHmm>`. When `val_accuracy` clears
`thresholds.yaml`, the run also registers `iris-classifier` in the Model Registry.

## Lifecycle

| Step | Command | What happens in Comet |
|------|---------|-----------------------|
| Data | `make data` | `data/processed/iris-*.csv` logged once as Artifact `iris-dataset` |
| Train | `make train` | one experiment: per-epoch metrics, confusion matrix, logged model, dataset lineage; registers the next patch version when every metric in `thresholds.yaml` passes (`ARGS="--register"` forces it) |
| Tune | `make sweep` | a `comet_ml.Optimizer` bayes search, one tagged experiment per trial |
| Promote | `/promote-model` or `uv run python scripts/registry_mutate.py set-status ...` | status Development -> Staging -> QA -> Production |
| Deploy | webhook -> `.github/workflows/deploy-model.yml` | re-checks the status, downloads the version, runs your deploy step |
| Consume | `make predict` | loads the Production version and predicts on the test split |

`make <target> ARGS="..."` passes flags to the script, e.g. `make train ARGS="--epochs 30 --learning-rate 0.05"`.

Offline: `COMET_START_ONLINE=false make train` writes `.cometml-runs/<key>.zip` for a later
`comet upload`. Offline runs skip Artifacts and registration.

## CI/CD: deploy on Model Registry status

`.github/workflows/deploy-model.yml` runs when a version's status changes in the registry.

1. Repository settings: secret `COMET_API_KEY` (use a [Service Account](https://www.comet.com/docs/v2/guides/comet-ui/admin-dashboard/service-accounts/) key),
   variable `COMET_WORKSPACE`.
2. GitHub: create a fine-grained token with **Contents: Read and write** on this repo (required to
   trigger a workflow this way).
3. Comet: open the registered model -> **Webhooks** -> **Create Webhook**:
   - URL `https://api.github.com/repos/<org>/<repo>/dispatches`
   - Secret `Bearer <your GitHub token>` (sent verbatim as the `Authorization` header)
   - Trigger **Model status changed** (fires after a change is approved)
   - **GitHub Actions Integration** on
4. **Test Webhook** should succeed. It sends a `TEST` event, so it does not start a deploy.

The workflow deploys only for the statuses listed in its `if:` (edit them to your registry's names),
re-checks the status in Comet so a stale event cannot deploy, fetches the version with `make predict`,
and ends in a placeholder deploy step. `.github/workflows/ci.yml` runs lint and the credential-free
tests on every push and pull request.
Docs: [webhooks](https://www.comet.com/docs/v2/guides/model-registry/webhooks/),
[status and approvals](https://www.comet.com/docs/v2/guides/model-registry/model-approval/).

## Claude Code + Comet MCP

`.mcp.json` registers the [Comet MCP server](https://www.comet.com/docs/v2/api-and-sdk/mcp-server/overview/)
and `.claude/settings.json` pre-approves it, so Claude Code can read experiments, metrics and projects.
The server does **not** read or write the Model Registry; `scripts/registry_mutate.py` does.

The server reads `COMET_API_KEY` / `COMET_WORKSPACE` from the shell, not from `.env`:

```bash
set -a && source .env && set +a
claude
```

[direnv](https://direnv.net/) with an `.envrc` containing `dotenv` makes that permanent.
`COMET_URL_OVERRIDE` is optional and defaults to `{{ cookiecutter.comet_url_override }}`.

## Working with AI coding assistants

`AGENTS.md` (imported by `CLAUDE.md`) briefs the agent; `.claude/rules/` holds the Comet EM, changelog
and notebook rules, scoped to the files they govern; `.claude/skills/` holds the workflows:

| Skill | Use it for |
|-------|-----------|
| `/run-training` | run `make train` and report name, URL, metrics, registered version |
| `/evaluate-run <id>` | check a run against `thresholds.yaml` |
| `/compare-runs <ids \| tag=x \| latest=N>` | metric and hyperparameter table across runs |
| `/debug-run <id>` | why a run failed: output, curves, code snapshot, assets |
| `/run-sweep` | run `make sweep` and summarise the trials |
| `/promote-model <name>` | change a version's status or tags, with confirmation |
| `/update-changelog` | draft `[Unreleased]` entries from the diff |

### Using these skills in an existing repo

Copy what you need rather than the whole scaffold:

1. `.claude/skills/<name>/` for each skill, `.claude/settings.json` (MCP pre-approval, `.env` denied)
   and `.mcp.json`.
2. `scripts/registry_mutate.py` and `thresholds.yaml` for `/promote-model` and `/evaluate-run`.
3. Each `SKILL.md` starts with a `Depends on:` line naming the commands and files it expects
   (`make train`, `thresholds.yaml`, `.env`); point those at your own entry points.
4. `config.experiment_name()` is four lines; copy it into your training package to get the naming
   convention everywhere.

## Project layout

```text
{{ cookiecutter.repo_name }}/
|-- .claude/               # settings.json, rules/, skills/
|-- .github/workflows/     # ci.yml, deploy-model.yml
|-- .mcp.json              # Comet MCP server for Claude Code
|-- data/{raw,interim,processed,external}/
|-- models/
|-- notebooks/             # exploration only; logic goes to src/
|-- reports/figures/
|-- scripts/registry_mutate.py
|-- src/{{ cookiecutter.module_name }}/
|   |-- config.py          # .env, experiment_name(), thresholds
|   |-- dataset.py         # make data
|   |-- train.py           # make train
|   |-- sweep.py           # make sweep
|   `-- predict.py         # make predict
|-- tests/                 # credential-free
|-- thresholds.yaml        # promotion gate
|-- AGENTS.md / CLAUDE.md  # agent briefing
`-- CHANGELOG.md / CONTRIBUTING.md / Makefile / pyproject.toml / .env.example
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
