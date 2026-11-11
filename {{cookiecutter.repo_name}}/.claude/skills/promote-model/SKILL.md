---
name: promote-model
description: Change a Comet Model Registry version's status and/or tags through `scripts/registry_mutate.py`. Status is one value per version (Development / Staging / QA / Production by default, workspace-configurable); tags are free-form and many. Shows current state, confirms every mutation, demotes the previous holder on request, and can gate on `/evaluate-run`. Use when the user asks to "promote", "demote", "set status", "tag", "untag" or "retag" a model.
argument-hint: "<model-name> [evaluation-experiment-id]"
disable-model-invocation: true
---

# Promote Model

Depends on: `scripts/registry_mutate.py` (`uv run`), `.env` with `COMET_API_KEY` / `COMET_WORKSPACE`,
optionally `/evaluate-run`. Registry API details: [reference.md](reference.md).

| Field | Cardinality | Values | Set with |
|-------|-------------|--------|----------|
| **Status** | one per version | `None`, `Development`, `Staging`, `QA`, `Production` by default; `allowed-statuses` shows the workspace's list | `set-status` |
| **Tags** | many per version | free-form (`champion`, `canary`, `lr=0.01`) | `add-tag` / `remove-tag` |

Every mutation goes through the script with argparse arguments. Never `python -c` with interpolated
user input. The MCP server has no registry tools, so reads go through the script too.

## When to run

- "Promote 1.2.0 to production" -> `set-status ... --status Production`, then demote the old holder.
- "Move it to staging" -> `set-status ... --status Staging`.
- "Tag it champion" / "drop the canary tag" -> `add-tag` / `remove-tag`.
- Workspaces with the approval workflow on: `set-status` files a request a workspace owner approves in
  the UI; say so instead of reporting the change as done.

## Procedure

### 1. Current state

```bash
uv run python scripts/registry_mutate.py list --model <model-name>
uv run python scripts/registry_mutate.py list --model <model-name> --status Production
uv run python scripts/registry_mutate.py allowed-statuses
```

`list` prints one row per version: `version`, `status`, `tags`, `experimentKey` (the source run, for
`/compare-runs` or `/evaluate-run`). "Model not found": run `list-models` and ask which one.

Render it:

```markdown
### iris-classifier

| Version | Status | Tags | Source experiment |
|---------|--------|------|-------------------|
| 1.0.3 | Development | example | a1b2c3 |
| 1.0.2 | Production | champion | d4e5f6 |
```

### 2. Decide the operations

Interpret the request against the table and the allowed statuses. Ambiguous cases ("tag it for
production": status or tag?) get a question. When a status that should be unique (`Production`) moves
to a new version, include the demotion of the current holder as a second operation; Comet does not
clear it for you.

### 3. Optional gate

With an evaluation experiment id (second argument, or the source `experimentKey`): run
`/evaluate-run <id>` and refuse on FAIL, printing the failing metrics.

### 4. Confirm, verbatim, and wait for "yes"

```
============================================================
REGISTRY MUTATION
============================================================
Model:   iris-classifier
  SET STATUS  1.0.3:  Development -> Production
  SET STATUS  1.0.2:  Production  -> None
  ADD TAG     1.0.3:  +release-2026-11
Gate:    PASSED (experiment a1b2c3)

Pipelines that fetch by status Production (predict.py, the deploy
workflow) pick up 1.0.3 on their next run.
============================================================
```

### 5. Execute, one operation per command, stop on the first failure

```bash
uv run python scripts/registry_mutate.py set-status --model iris-classifier --version 1.0.3 --status Production
uv run python scripts/registry_mutate.py set-status --model iris-classifier --version 1.0.2 --status None
uv run python scripts/registry_mutate.py add-tag --model iris-classifier --version 1.0.3 --tag release-2026-11
```

Report which operations ran. A half-applied change is reported as such, not retried.

### 6. Verify

Re-run `list`, show before/after, and link the registry page:
`<COMET_URL_OVERRIDE host, default https://www.comet.com>/<workspace>/model-registry/<model-name>`.

## Anti-patterns

- Mutating without the confirmation block.
- Setting a status that is not in `allowed-statuses` (the server error is unhelpful).
- Leaving two versions in `Production`.
- Promoting a version already at the target status: print the no-op and stop.
- Removing tags with anything but single `remove-tag` calls (there is no bulk setter; don't invent one).
