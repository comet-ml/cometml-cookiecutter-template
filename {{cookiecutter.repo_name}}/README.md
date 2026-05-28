# {{ cookiecutter.project_name }}

{{ cookiecutter.description }}

Python {{ cookiecutter.python_version }} · uv · Comet EM · {{ cookiecutter.framework }}

## Quickstart

```bash
uv sync
cp .env.example .env       # fill in COMET_API_KEY and COMET_WORKSPACE
make train                 # runs the example experiment
```

See your experiment at `https://www.comet.com/<your-workspace>/{{ cookiecutter.repo_name }}` — replace `<your-workspace>` with your Comet workspace slug (the value of `COMET_WORKSPACE` in your `.env`).

## Project layout

<!-- AUTO-GENERATED:tree -->
```
{{ cookiecutter.repo_name }}/
├── .claude/                       # Claude Code rules + skills
│   ├── rules/
│   └── skills/
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

Skills:

- `update-readme` — regenerate the auto-generated README sections
- `update-makefile` — keep targets in sync with installed tooling
- `update-changelog` — propose `[Unreleased]` lines from `git diff`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
