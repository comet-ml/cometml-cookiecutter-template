---
name: promote-model
description: Manage a Comet Model Registry version's status and/or tags via `scripts/registry_mutate.py`. Status is a single-value enum (None / Development / Staging / QA / Production by default; workspace-configurable). Tags are a multi-value free-form list. Confirms before mutating. Optionally gates on a passing `evaluate-run` outcome. Use when the user asks to "promote", "demote", "set status", "tag", "untag", or "retag" a model.
---

# Promote Model

Mutate a Comet Model Registry version's **status** and/or **tags** via the project-local helper script `scripts/registry_mutate.py`.

These are two different fields in the registry — don't conflate them:

| Field | Cardinality | Default values | Real SDK call |
|-------|-------------|----------------|---------------|
| **Status** | Single value per version | `None`, `Development`, `Staging`, `QA`, `Production` (workspace-configurable; check with `python scripts/registry_mutate.py allowed-statuses`) | `api.get_model(ws, name).set_status(version, status)` |
| **Tags** | Multi-value list per version | Free-form: `champion`, `canary`, `lr=0.01`, `paper-2026`, etc. | `Model.add_tag(version, tag)` / `Model.delete_tag(version, tag)` — single-tag operations, no bulk |

All mutations go through `scripts/registry_mutate.py`. The skill never invokes `python -c "..."` with interpolated user values — argparse handles quoting safely so a malicious model name like `foo'; rm -rf /` can't escape.

## When to run

- "Promote 1.2.0 to production" → set status to `Production`.
- "Move it to staging for review" → set status to `Staging`.
- "Demote the current prod" → set status of the current Production version to `Development` or `None`.
- "Tag it as `champion`" → add tag.
- "Drop the `canary` tag" → remove tag.
- Combinations: "promote to production and tag as `release-2026-05`".

## Inputs

- **`model_name`** (required) — registry name, e.g. `iris-classifier`.
- **`evaluation_experiment_id`** — optional. If provided, invoke `/evaluate-run <id>` first and refuse to mutate if FAIL.

Everything else (which version, what status, which tags) is **chosen interactively** based on the registry's current state.

## Procedure

### 1. Inspect current state

```bash
uv run python scripts/registry_mutate.py list --model <model_name>
```

Output is JSON with one entry per version: `{"version": "1.2.0", "status": "Staging", "tags": ["candidate", "lr=0.01"]}`.

If you get `Model '<x>' not found`:

```bash
uv run python scripts/registry_mutate.py list-models
```

Pick the right one or stop with "no such model".

### 2. Check the workspace's allowed status values

```bash
uv run python scripts/registry_mutate.py allowed-statuses
```

Returns a JSON list. Comet's default set is `["None", "Development", "Staging", "QA", "Production"]` but workspaces can customize. Validate the user's requested status against this list **before** mutating — otherwise the server will reject with an unclear error.

### 3. Render current state to the user

```markdown
### iris-classifier — current registry state

| Version | Status | Tags |
|---------|--------|------|
| 1.2.0 | Staging | candidate, lr=0.01 |
| 1.1.0 | Production | champion |
| 1.0.0 | Development | (no tags) |
```

### 4. Ask the user what to change

Offer the menu:

- **Set status** of a version (pick one from the allowed list).
- **Add tag(s)** to a version.
- **Remove tag(s)** from a version.
- **Combinations** — collect them, confirm together.

Interpret natural language:

- "Promote 1.2.0 to production" → set status of 1.2.0 to `Production`.
- "Demote 1.1.0" → ask whether `Development` or `None`. Don't assume.
- "Make 1.2.0 the champion" → add tag `champion` to 1.2.0; ask whether to also remove `champion` from any other version (champion is usually exclusive).
- "Move staging" → ambiguous (status or tag?). Ask. Default: status.

### 5. Optional eval gate

If `evaluation_experiment_id` was given, invoke `/evaluate-run <id>` and require PASS. On FAIL: refuse the mutation. Print failing metrics.

### 6. Confirmation block

Present verbatim. Wait for explicit "yes":

```
============================================================
REGISTRY MUTATION — CONFIRMATION
============================================================
Model:           iris-classifier
Operations:
  • SET STATUS    version 1.2.0:  Staging → Production
  • SET STATUS    version 1.1.0:  Production → None
  • ADD TAG       version 1.2.0:  +release-2026-05

Eval gate:       PASSED (experiment abc123…)

Downstream consumers that fetch by status `Production` will
receive 1.2.0 on their next pull. This is hard to undo without
manual cleanup — confirm you intend this change.
============================================================
```

### 7. Execute via the helper

Run one sub-command per operation. Stop on first non-zero exit — do NOT continue and leave the registry half-changed. Report which operations succeeded and which didn't.

```bash
# Set status
uv run python scripts/registry_mutate.py set-status \
    --model iris-classifier --version 1.2.0 --status Production

# Demote a prior holder of a single-value status (Comet doesn't auto-clear it)
uv run python scripts/registry_mutate.py set-status \
    --model iris-classifier --version 1.1.0 --status None

# Add a tag
uv run python scripts/registry_mutate.py add-tag \
    --model iris-classifier --version 1.2.0 --tag release-2026-05

# Remove a tag
uv run python scripts/registry_mutate.py remove-tag \
    --model iris-classifier --version 1.2.0 --tag canary
```

Note: status is a single-value field, but Comet does NOT automatically clear it from a prior holder when you set a new one. If you're "moving" a status (e.g. Production from 1.1.0 to 1.2.0), explicitly set the prior holder to `None` (or whatever target stage you want) — otherwise the registry briefly has two versions claiming `Production`.

### 8. Verify

Re-run `list` and print the before/after side by side. Highlight changed rows. Print the registry URL: `https://www.comet.com/<workspace>/model-registry/<model_name>`.

## Anti-patterns

- **Never mutate without explicit user confirmation.** Bypass = raw API call.
- **Don't conflate status and tags.** "Tag it for production" is ambiguous — ask whether they mean status `Production` (lifecycle) or tag `production` (label). Default to status when ambiguous.
- **Don't strip preserved tags.** Removing one tag must leave the rest intact — `Model.delete_tag(version, tag)` does this correctly (single-tag op), but don't fall back to a bulk-overwrite call.
- **Don't promote a version that's already at the target status.** Print the no-op and stop.
- **Don't change status to a value not in `allowed-statuses`.** The server rejects with a vague error.
- **Don't auto-demote the current status holder.** Surface the conflict and have the user explicitly demote.
- **Don't construct shell or Python commands by string-interpolating user input.** Always use the `scripts/registry_mutate.py` helper — argparse handles quoting.

## Cross-references

- `.claude/rules/comet-em-best-practices.md` section 6 — registry conventions.
- `evaluate-run` — upstream gate.
- `scripts/registry_mutate.py` — implementation of all mutations.
- Comet API reference: <https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/API/>.
