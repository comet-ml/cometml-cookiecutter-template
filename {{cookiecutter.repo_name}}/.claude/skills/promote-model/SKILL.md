---
name: promote-model
description: Manage a Comet Model Registry version's status and tags — set the single-value status (None / Development / Staging / QA / Production) and/or add/remove free-form tags. Confirms before mutating. Optionally gates on a passing `evaluate-run` outcome. Use when the user asks to "promote", "demote", "set status", "tag", or "retag" a model.
---

# Promote Model

Mutate a Comet Model Registry version's **status** and/or **tags**.

These are two different fields in the registry — don't conflate them:

| Field | Cardinality | Values | Purpose |
|-------|-------------|--------|---------|
| **Status** | Single value per version | `None`, `Development`, `Staging`, `QA`, `Production` (Comet's standard set — confirm against the registry UI for your workspace's exact options) | Lifecycle stage. Deploy pipelines that fetch "the production version" use this. |
| **Tags** | Multi-value list per version | Free-form strings, e.g. `champion`, `canary`, `lr=0.01`, `paper-2026` | Free-form labels for slicing, A/B groups, descriptive metadata. |

Both are write operations on a registered version. The skill always confirms before mutating.

## When to run

- "Promote 1.2.0 to production" → set status to `Production`.
- "Move it to staging for review" → set status to `Staging`.
- "Demote the current prod" → set status of the current Production version to `Development` or `None`.
- "Tag it as `champion`" → add tag.
- "Drop the `canary` tag" → remove tag.
- Combinations: "promote to production and add tag `release-2026-05`".

## Inputs

- **`model_name`** (required) — registry name, e.g. `iris-classifier`.
- **`evaluation_experiment_id`** — optional. If provided, invokes `/evaluate-run <id>` first and refuses to mutate if FAIL.

Everything else (which version, what status, which tags) is **chosen interactively** based on the registry's current state.

## Procedure

### 1. Fetch registry state

```bash
uv run python -c "
from comet_ml import API
from {{ cookiecutter.module_name }} import config

api = API(api_key=config.COMET_API_KEY)
versions = api.get_registry_model_versions(
    workspace=config.COMET_WORKSPACE,
    registry_name='<model_name>',
)
for v in versions:
    status = v.get('status') or v.get('stage') or 'None'
    tags = ','.join(v.get('tags', [])) or '(no tags)'
    print(v.get('version'), '|', status, '|', tags)
"
```

If the model isn't found, stop and list the registry models that *do* exist.

> **API surface note.** The status field has been called different things across `comet-ml` releases (`stage`, `stages`, `status`). The exact getter/setter may be `update_registry_model_version` with a `stage=` or `status=` kwarg, or a dedicated `set_model_version_stage` method. If the call below fails, run `python -c "from comet_ml import API; help(API.update_registry_model_version)"` and `python -c "from comet_ml import API; print([m for m in dir(API) if 'registry' in m.lower() or 'stage' in m.lower() or 'status' in m.lower()])"` to find the current method shape. Reference: <https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/API/>.

### 2. Render current state

```markdown
### iris-classifier — current registry state

| Version | Status      | Tags |
|---------|-------------|------|
| 1.2.0   | Staging     | candidate, lr=0.01 |
| 1.1.0   | Production  | champion |
| 1.0.0   | Development | (no tags) |
```

### 3. Ask the user what to change

Offer the menu:

- **Set status** of a version to one of: `None`, `Development`, `Staging`, `QA`, `Production` (or whatever the registry UI shows for the workspace).
- **Add tag(s)** to a version.
- **Remove tag(s)** from a version.
- **Multiple operations in one go** — collect them, then confirm together.

Interpret natural-language requests:

- "Promote 1.2.0 to production" → set status of 1.2.0 to `Production`.
- "Demote 1.1.0" → ask whether to `Development` or `None`. Don't assume.
- "Make 1.2.0 the champion" → add tag `champion` to 1.2.0; ask whether to also remove `champion` from any other version (champion is usually exclusive).
- "Move staging" → ambiguous (status or tag?). Ask the user. Default: status.

### 4. Optional eval gate

If `evaluation_experiment_id` was given, invoke `/evaluate-run <id>` and require PASS. On FAIL: refuse the mutation. Print failing metrics.

### 5. Confirmation block

Present verbatim. Wait for explicit "yes":

```
============================================================
REGISTRY MUTATION — CONFIRMATION
============================================================
Model:           iris-classifier
Operations:
  • SET STATUS    version 1.2.0:  Staging → Production
  • REMOVE STATUS version 1.1.0:  Production → None
  • ADD TAG       version 1.2.0:  +release-2026-05

Eval gate:       PASSED (experiment abc123…)

Downstream consumers that fetch by status `Production` will
receive 1.2.0 on their next pull. This is hard to undo without
manual cleanup — confirm you intend this change.
============================================================
```

For each operation type, show the before/after explicitly. If the user combined operations, list them all in this block before any mutation runs.

### 6. Execute

Run mutations sequentially. Stop on first failure — do **not** continue and leave the registry half-changed. If a mutation fails, surface the API error and tell the user the state is partially applied (and what was applied).

```bash
uv run python -c "
from comet_ml import API
from {{ cookiecutter.module_name }} import config

api = API(api_key=config.COMET_API_KEY)

# Set status — exact kwarg name depends on SDK version (see note above):
api.update_registry_model_version(
    workspace=config.COMET_WORKSPACE,
    registry_name='<model_name>',
    version='<version>',
    status='<new_status>',  # or stage='<new_status>'
)

# Add tag — preserve existing tags:
current = next(v for v in api.get_registry_model_versions(
    workspace=config.COMET_WORKSPACE,
    registry_name='<model_name>',
) if v['version'] == '<version>')
new_tags = list(set(current.get('tags', []) + ['<tag_to_add>']))
api.update_registry_model_version(
    workspace=config.COMET_WORKSPACE,
    registry_name='<model_name>',
    version='<version>',
    tags=new_tags,
)
"
```

### 7. Verify

Re-fetch the registry state and print the post-change table side by side with the pre-change one. Highlight the changed rows.

Print the registry URL: `https://www.comet.com/<workspace>/model-registry/<model_name>`.

## Anti-patterns

- **Never mutate without explicit user confirmation.** Bypass = raw API call.
- **Don't conflate status and tags.** Status is a single enum value; tags are a free-form list. The user said "tag it for production" — interpret carefully: do they mean *set status to Production* (lifecycle) or *add a tag called `production`* (label)? Default to status when ambiguous, but ask first.
- **Don't strip preserved tags.** If a version is tagged `lr=0.01,dataset=v2,canary` and you're removing `canary`, leave the others intact.
- **Don't promote a version that's already at the target status.** Print the no-op and stop.
- **Don't change status to something not in the registry's allowed set.** If the workspace customized the status list and the user asks for `Shipped`, verify that status exists first.
- **Don't auto-demote the current holder of a status** without telling the user. Comet's status field is single-value per version, but if N versions claim `Production` simultaneously (which can happen), surface that anomaly rather than silently fixing it.
- **Don't create new tags from typos.** If the user asks to add `prdcution`, confirm whether they meant `production`.

## Cross-references

- `.claude/rules/comet-em-best-practices.md` section 6 — registry conventions (status vs tags, versioning, descriptions).
- `evaluate-run` — upstream gate.
- Comet API reference: <https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/API/>.
