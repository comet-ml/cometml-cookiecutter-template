# cometml-cookiecutter-template

A [cookiecutter](https://cookiecutter.readthedocs.io/) template for scaffolding an ML project pre-wired for **Comet Experiment Management** and Claude Code agentic workflows.

## What you get

- `src/` layout managed by [`uv`](https://docs.astral.sh/uv/)
- Working example experiment that logs to Comet (pick `sklearn`, `pytorch`, `tensorflow`, or `none`)
- `.claude/` rules and skills so Claude Code (or any agent reading `AGENT.md`) behaves consistently
- Standard repo hygiene: `AGENT.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `.env.example`, `Makefile`
- Data-science folder layout (`data/`, `notebooks/`, `models/`, `reports/`) — inspired by [cookiecutter-data-science](https://github.com/drivendataorg/cookiecutter-data-science)

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/) (recommended) — or pipx/pip
- [`cookiecutter`](https://cookiecutter.readthedocs.io/en/stable/installation.html)

```bash
uv tool install cookiecutter
```

## Usage

```bash
cookiecutter gh:comet-ml/cometml-cookiecutter-template
```

You'll be prompted for:

| Variable | Description | Default |
|----------|-------------|---------|
| `project_name` | Human-readable name | `My Comet ML Project` |
| `repo_name` | Slug for the repo directory | derived from `project_name` |
| `module_name` | Python module name | derived from `project_name` |
| `description` | Short project description | `A Comet-tracked ML project.` |
| `author_name` | Author name for `pyproject.toml` | `Your Name` |
| `author_email` | Author email | `you@example.com` |
| `python_version` | Python version pin | `3.12` |
| `framework` | Example experiment framework | `sklearn` |
| `open_source_license` | License | `MIT` |

## What happens after generation

The post-generation hook will:

1. Render the framework-specific `src/<module>/train.py` and append the matching deps to `pyproject.toml`.
2. Write the chosen `LICENSE` (or delete it for `Proprietary` / `None`).
3. Run `git init` (does not commit — you inspect first).

Then:

```bash
cd <repo_name>
uv sync
cp .env.example .env       # fill in your COMET_API_KEY / COMET_WORKSPACE
make train                 # runs the example experiment
```

## Local development of this template

```bash
git clone https://github.com/comet-ml/cometml-cookiecutter-template
cd cometml-cookiecutter-template

# Generate to a scratch dir
cookiecutter . --output-dir /tmp/cc-test --no-input \
    project_name="Test Project" framework=sklearn open_source_license=MIT

# Smoke test
cd /tmp/cc-test/test-project
uv sync
make test
```