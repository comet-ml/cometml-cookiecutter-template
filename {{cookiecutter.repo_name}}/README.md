# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

Python {{ cookiecutter.python_version }} · uv · Comet EM · {{ cookiecutter.framework }}

## Quickstart

```bash
uv sync
cp .env.example .env       # fill in COMET_API_KEY and COMET_WORKSPACE
set -a && source .env && set +a   # export the variables into your shell session
make train                 # runs the example experiment
```

See your experiment at `https://www.comet.com/<your-workspace>/{{ cookiecutter.repo_name }}` — replace `<your-workspace>` with your Comet workspace slug (the value of `COMET_WORKSPACE` in your `.env`).

## Claude Code + Comet MCP setup

This project ships a `.mcp.json` at the repo root. When you launch [Claude Code](https://docs.claude.com/en/docs/claude-code) from inside this directory, it auto-loads the [Comet MCP server](https://www.comet.com/docs/v2/api-and-sdk/mcp-server/overview/), which lets the AI query your experiments, metrics, projects, and registry directly.

One-time install:

```bash
uv tool install comet-mcp     # or rely on `uvx` to fetch on demand
```

Every Claude Code session needs your `.env` values exported into the shell *before* launch (the MCP server reads `COMET_API_KEY` / `COMET_WORKSPACE` / `COMET_URL_OVERRIDE` from the environment, not from `.env` directly):

```bash
set -a && source .env && set +a
claude    # launches Claude Code, which auto-loads .mcp.json
```

For a permanent setup, use [direnv](https://direnv.net/) — add `.envrc` containing `dotenv` and the env loads automatically on `cd`.

## Project layout

<!-- AUTO-GENERATED:tree -->
```
{{ cookiecutter.repo_name }}/
├── .claude/                       # Claude Code rules + skills
│   ├── rules/                     # Comet EM best practices, CHANGELOG discipline, notebook hygiene
│   └── skills/                    # run-training, evaluate-run, compare-runs, promote-model, update-{readme,makefile,changelog}
├── .mcp.json                      # Auto-loads Comet MCP server in Claude Code
├── data/
│   ├── raw/                       # Immutable, as received
│   ├── interim/                   # Intermediate transformations
│   ├── processed/                 # Canonical, ready for modeling
│   └── external/                  # Third-party sources
├── models/                        # Trained model artifacts
├── notebooks/                     # Exploration only — production code lives in src/
├── reports/
│   └── figures/
├── src/
│   └── {{ cookiecutter.module_name }}/
│       ├── config.py              # Loads .env, exposes COMET_* settings
│       ├── dataset.py             # Data loading
│       └── train.py               # Example experiment (logs to Comet)
├── tests/
├── AGENT.md                       # Briefing for AI coding assistants
├── CHANGELOG.md
├── CONTRIBUTING.md
├── Makefile
├── pyproject.toml
└── .env.example
```
<!-- /AUTO-GENERATED:tree -->

## Common tasks

| Task | Command |
|------|---------|
| Install runtime deps | `make install` |
| Install dev deps (ruff, pytest) | `make install-dev` |
| Format code | `make format` |
| Lint | `make lint` |
| Run tests | `make test` |
| Run example experiment | `make train` |

## Working with AI coding assistants

This project ships with `AGENT.md` and a `.claude/` folder containing rules and skills for [Claude Code](https://docs.claude.com/en/docs/claude-code). The rules cover:

- Comet EM best practices (what to log, tagging conventions, credentials handling)
- CHANGELOG discipline (update `## [Unreleased]` before every commit)
- Notebook hygiene (clear outputs, no secrets, push logic into `src/`)

Comet-EM lifecycle skills (use the auto-loaded MCP server):

- `run-training` — execute `make train`, surface the experiment URL + final metrics
- `evaluate-run` — pull a run's metrics via MCP, compare against thresholds, pass/fail
- `compare-runs` — side-by-side metric diff across 2+ runs via MCP
- `promote-model` — set a registry version's status (None/Development/Staging/QA/Production) and/or tags, with confirmation

Repo upkeep skills:

- `update-readme` — regenerate the auto-generated README sections
- `update-makefile` — keep targets in sync with installed tooling
- `update-changelog` — propose `[Unreleased]` lines from `git diff`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
