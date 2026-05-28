# Contributing

## Setup

```bash
uv sync --all-extras       # runtime + dev deps
cp .env.example .env
# fill in COMET_API_KEY, COMET_WORKSPACE
```

## Branch naming

```
<your-handle>/<short-kebab-description>
```

Examples:

- `your-handle/add-data-augmentation`
- `your-handle/fix-train-step-logging`

## Pre-commit checklist

Before every commit:

1. **Update `CHANGELOG.md`** under `## [Unreleased]` with a line describing your change. See `.claude/rules/changelog-discipline.md` for the discipline; `.claude/skills/update-changelog/SKILL.md` for an automated helper.
2. **Format**: `make format`
3. **Lint**: `make lint`
4. **Test**: `make test`

A commit that touches `src/` must also touch `CHANGELOG.md`.

## Pull request template

```markdown
## Summary
<1-3 bullet points describing the change>

## Why
<motivation, link to issue/ticket>

## Test plan
- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] Experiment logged to Comet (link the run)
- [ ] `CHANGELOG.md` updated under [Unreleased]
```

## Working with AI assistants

This repo ships with rules and skills in `.claude/` for [Claude Code](https://docs.claude.com/en/docs/claude-code). When using Claude (or any agent that reads `AGENT.md`), it will follow:

- Comet EM logging conventions
- CHANGELOG update discipline
- Notebook hygiene (clear outputs, no secrets)

If your AI assistant suggests a change that violates one of these rules, push back.
