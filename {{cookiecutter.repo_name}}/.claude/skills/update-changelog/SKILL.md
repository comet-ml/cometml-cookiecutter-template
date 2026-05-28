---
name: update-changelog
description: Diff HEAD against main, group the changes by Keep-a-Changelog type (Added/Changed/Fixed/...), propose one-line entries under [Unreleased] in CHANGELOG.md, then edit the file inline. User reviews the diff and stages it themselves. Use before any commit that touches src/.
---

# Update Changelog

Propose `[Unreleased]` lines for `CHANGELOG.md` based on the current branch's diff. Edit the file inline; user reviews and stages.

## When to run

- Before every commit that touches `src/` (see `.claude/rules/changelog-discipline.md`).
- Before opening a PR — make sure `[Unreleased]` reflects everything on the branch.
- On release — when collapsing `[Unreleased]` into a versioned section.

## Procedure

1. **Identify the base**: `git merge-base HEAD main` (or `master`). Fall back to `origin/main` if local `main` doesn't exist.

2. **Diff**:
   - `git diff --name-status <base>..HEAD` — file-level changes.
   - `git log <base>..HEAD --pretty=format:"%h %s"` — commits since base.

3. **Classify** each change into Keep-a-Changelog sections:

   | Pattern | Section |
   |---------|---------|
   | New file under `src/`, new public function/class | **Added** |
   | Modified function/class behavior, new dependency, refactor | **Changed** |
   | Removed file, removed function/class | **Removed** |
   | Bug fix (look for "fix", "bug" in commit msgs, or fixed test) | **Fixed** |
   | Feature flag for removal, scheduled deletion | **Deprecated** |
   | CVE patch, auth/crypto fix | **Security** |

4. **Draft** one bullet per change. Style:
   - Imperative mood (`Add ...`, `Fix ...`, `Switch ...`).
   - One sentence, under ~80 chars.
   - Reference PR/issue numbers in parens at the end if known.

5. **Edit** `CHANGELOG.md` inline:
   - Locate the `## [Unreleased]` block.
   - Insert each line under its matching subsection.
   - Create subsections in order: Added, Changed, Deprecated, Removed, Fixed, Security.
   - Don't overwrite existing entries — append.

6. **Show the diff** to the user:
   ```
   git diff CHANGELOG.md
   ```

7. **Hand off**: tell the user to review the proposed lines and stage them:
   ```bash
   git add CHANGELOG.md
   ```

   Do **not** run `git add` automatically.

## Releasing a version

When the user says "cut version X.Y.Z":

1. Replace `## [Unreleased]` heading with `## [X.Y.Z] - YYYY-MM-DD` (today's date).
2. Insert a fresh empty `## [Unreleased]` block at the top of the version history.
3. Bump `version` in `pyproject.toml` and `__version__` in `src/<module>/__init__.py`.
4. Show the diff. User commits and tags (`git tag vX.Y.Z`).

## Anti-patterns

- Auto-staging the file — user must review wording.
- Vague lines like "Updated code" or "Various improvements." Be specific.
- Dropping lines for "minor" changes that touched `src/`. If it changed behavior, it goes in the log.
- Re-classifying user-authored entries — leave them alone unless asked.
