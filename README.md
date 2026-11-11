# cometml-cookiecutter-template

A [cookiecutter](https://cookiecutter.readthedocs.io/) template for an ML project pre-wired for
**Comet Experiment Management** and coding-agent workflows (Claude Code, Codex, Cursor). The generated
project runs the whole Comet EM lifecycle out of the box and is also meant as a reference: point your
agent at it and copy the pieces you need into an existing repo.

## What you get

- `src/` layout managed by [`uv`](https://docs.astral.sh/uv/); choose `sklearn`, `xgboost`, `pytorch`,
  `tensorflow` or `none`
- The Comet EM lifecycle, runnable: `make data` (dataset Artifact) -> `make train` (`comet_ml.start()`,
  per-epoch metrics, confusion matrix, logged model, gated semver registration) -> `make sweep`
  (Optimizer) -> `/promote-model` (status + tags) -> registry webhook -> `deploy-model.yml` ->
  `make predict` (consume by status)
- Experiment names `{project}-{model}-{YYYYMMDD}-{HHmm}`, a `thresholds.yaml` promotion gate,
  `scripts/registry_mutate.py` for safe registry changes
- `.claude/`: `settings.json` (Comet MCP server pre-approved, `.env` denied), path-scoped rules
  (Comet EM, changelog, notebooks) and skills: `run-training`, `evaluate-run`, `compare-runs`,
  `debug-run`, `run-sweep`, `promote-model`, `update-changelog`
- `.mcp.json` for the [Comet MCP server](https://www.comet.com/docs/v2/api-and-sdk/mcp-server/overview/)
- GitHub Actions: CI (lint + credential-free tests) and deploy-on-registry-status
- Repo hygiene: `AGENTS.md` + `CLAUDE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `.env.example`,
  `.pre-commit-config.yaml`, `Makefile`
- Data-science folder layout (`data/`, `notebooks/`, `models/`, `reports/`), after
  [cookiecutter-data-science](https://github.com/drivendataorg/cookiecutter-data-science)

## Requirements

- Python 3.10+ (`tensorflow` needs 3.12 or lower)
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- [`cookiecutter`](https://cookiecutter.readthedocs.io/en/stable/installation.html): `uv tool install cookiecutter`
- `xgboost` on macOS: `brew install libomp`

## Usage

```bash
cookiecutter gh:comet-ml/cometml-cookiecutter-template
```

| Variable | Description | Default |
|----------|-------------|---------|
| `project_name` | Human-readable name | `My Comet ML Project` |
| `repo_name` | Slug for the repo directory | derived from `project_name` |
| `module_name` | Python module name | derived from `project_name` |
| `description` | Short project description | `A Comet-tracked ML project.` |
| `author_name` | Author name for `pyproject.toml` | `Your Name` |
| `author_email` | Author email | `you@example.com` |
| `python_version` | Python version pin | `3.12` |
| `framework` | Example framework | `sklearn` |
| `comet_url_override` | Comet backend URL (single-tenant / on-prem only) | `https://www.comet.com/clientlib/` |
| `open_source_license` | License | `MIT` |

## What happens after generation

Framework deps (and the CPU-only torch index for `pytorch`) are templated in `pyproject.toml`. The
post-generation hook writes the chosen `LICENSE` (or removes it for `Proprietary` / `None`) and runs
`git init` + `git add .` without committing, so you inspect first. Then:

```bash
cd <repo_name>
uv sync
cp .env.example .env       # fill in COMET_API_KEY / COMET_WORKSPACE
make train                 # runs one experiment (builds the CSVs if missing)
```

The generated `README.md` covers the lifecycle, the deploy webhook setup, the MCP server and how to
copy the skills into an existing repo.

## Local development of this template

```bash
git clone https://github.com/comet-ml/cometml-cookiecutter-template
cd cometml-cookiecutter-template

cookiecutter . --output-dir out --no-input project_name="Test Project" framework=sklearn
cd out/test-project
uv sync && make lint && make test
```

`.github/workflows/ci.yml` does the same for every framework on each push and pull request.
`.github/workflows/*` in the template are copied without rendering (`_copy_without_render`), so GitHub
`${{ ... }}` expressions survive; everything else goes through Jinja.
