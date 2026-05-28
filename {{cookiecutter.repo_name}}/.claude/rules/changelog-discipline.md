# CHANGELOG Discipline

`CHANGELOG.md` is the single source of truth for what changed and why. Keep it current.

## The rule

**Every commit that touches `src/` must also update `CHANGELOG.md`** under `## [Unreleased]`.

If a commit modifies `src/` but `CHANGELOG.md` is unchanged in the same commit:

1. Stop.
2. Propose a one-line entry under the correct subsection of `## [Unreleased]`.
3. Add the line, stage `CHANGELOG.md`, then create the commit.

Exception: docs-only or config-only commits (no `src/` touched) don't require a changelog entry — but feel free to add one if it's user-visible.

## Format

Follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

```markdown
## [Unreleased]

### Added
- Train script for the iris classifier example. (#12)

### Changed
- Switch optimizer from SGD to Adam in train.py.

### Fixed
- Avoid double-logging when re-running train.py without ending the previous Experiment.
```

Subsections (use only those that apply):

- **Added** — new features
- **Changed** — changes in existing functionality
- **Deprecated** — soon-to-be-removed features
- **Removed** — now-removed features
- **Fixed** — bug fixes
- **Security** — security fixes

## Style

- One bullet per change.
- Imperative mood: `Add ...`, `Fix ...`, `Switch ...` — not `Added` or `Adding`.
- Reference PR/issue numbers in parens at the end when applicable.
- A non-developer reading this file should understand what changed.

## On release

When cutting a version:

1. Replace `## [Unreleased]` with `## [X.Y.Z] - YYYY-MM-DD`.
2. Add a fresh empty `## [Unreleased]` block at the top.
3. Bump `version` in `pyproject.toml` and `__version__` in `src/{{ cookiecutter.module_name }}/__init__.py`.
4. Tag the commit: `git tag vX.Y.Z`.

## Helper

`.claude/skills/update-changelog/SKILL.md` proposes lines automatically by diffing `HEAD` vs `main`, but you still review before staging.
