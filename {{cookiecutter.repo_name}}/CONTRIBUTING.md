# Contributing

## Setup

```bash
uv sync                      # runtime + dev deps
uv run pre-commit install    # ruff + nbstripout on every commit
cp .env.example .env         # fill in COMET_API_KEY, COMET_WORKSPACE
```

Commit `uv.lock` so everyone (and CI) resolves the same versions.

## Branch naming

```
<your-handle>/<short-kebab-description>
```

Examples: `your-handle/add-data-augmentation`, `your-handle/fix-train-step-logging`.

## Pre-commit checklist

1. **Update `CHANGELOG.md`** under `## [Unreleased]` when `src/` changed
   (`.claude/rules/changelog-discipline.md`; `/update-changelog` drafts the line).
2. `make format`, `make lint`, `make test`. CI (`.github/workflows/ci.yml`) runs the last two.

## Pull request template

```markdown
## Summary
<1-3 bullet points describing the change>

## Why
<motivation, link to issue/ticket>

## Test plan
- [ ] `make lint` and `make test` pass
- [ ] Experiment logged to Comet (link the run)
- [ ] `CHANGELOG.md` updated under [Unreleased]
```

## Working with AI assistants

`AGENTS.md` (imported by `CLAUDE.md`) and `.claude/` hold the briefing, rules and skills for
[Claude Code](https://code.claude.com/docs/en/overview) and other agents that read `AGENTS.md`. They
enforce the Comet EM conventions, the changelog discipline and notebook hygiene. If an assistant
suggests a change that violates one of them, push back.
