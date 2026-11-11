---
paths:
  - "src/**"
  - "CHANGELOG.md"
---

# CHANGELOG Discipline

`CHANGELOG.md` is the single source of truth for what changed and why. Keep it current.

## The rule

**Every commit that touches `src/` must also update `CHANGELOG.md`** under `## [Unreleased]`.

If a change modifies `src/` and `CHANGELOG.md` is untouched:

1. Stop.
2. Propose a one-line entry under the right subsection of `## [Unreleased]` (`/update-changelog` drafts it).
3. Edit the file. The user reviews the diff and stages it; the agent does not run `git add` or commit.

Docs-only or config-only changes (no `src/`) need no entry, but add one when it is user-visible.

## Format

Follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

```markdown
## [Unreleased]

### Added
- Train script for the iris classifier example. (#12)

### Changed
- Switch optimizer from SGD to Adam in train.py.

### Fixed
- Avoid double-logging when re-running train.py without ending the previous experiment.
```

Subsections, only those that apply: **Added**, **Changed**, **Deprecated**, **Removed**, **Fixed**, **Security**.

## Style

- One bullet per change, imperative mood (`Add ...`, `Fix ...`), PR/issue number in parens at the end.
- A non-developer reading this file should understand what changed.

## On release

1. Replace `## [Unreleased]` with `## [X.Y.Z] - YYYY-MM-DD` and add a fresh empty `## [Unreleased]` on top.
2. Bump `version` in `pyproject.toml` and `__version__` in `src/{{ cookiecutter.module_name }}/__init__.py`.
3. Tag the commit: `git tag vX.Y.Z`.
