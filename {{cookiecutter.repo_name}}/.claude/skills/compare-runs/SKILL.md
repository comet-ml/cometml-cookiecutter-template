---
name: compare-runs
description: Side-by-side table of metrics and hyperparameters for 2+ Comet experiments, from ids, a tag, a metric query or latest=N, via the Comet MCP server with a comet_ml.API fallback. Highlights the best value per metric. Use when the user asks to "compare", "diff", "which run won", "baseline vs new" or "candidate vs production".
argument-hint: "<id id ...> | tag=<tag> | latest=<N> | <metric><op><value>"
---

# Compare Runs

Depends on: Comet MCP server (setup, workspace/project rule, tool table, SDK fallback: `AGENTS.md` >
"Comet MCP server").
`scripts/registry_mutate.py list --status Production` gives the source `experimentKey`.

## Inputs

Any of: a list of experiment ids; `tag=<tag>`; `latest=<N>`; a metric query such as `val_accuracy>0.95`.
At least 2 runs. Above 8, use `experiment_spreadsheet` and summarize the CSV instead of a table.

## Procedure

### 1. Resolve the runs

| Input | Tool |
|-------|------|
| `latest=N` | `list_experiments(workspace, project_name, page_size=N, sort_by="startTime", sort_order="desc")` |
| `tag=x` | `find_tagged_experiments(tag="x", workspace, project_name)` |
| `metric>v` | `query_experiments(name="val_accuracy", comparison=">", value=0.95, workspace, project_name)` |
| "vs production" | `uv run python scripts/registry_mutate.py list --model <name> --status Production` -> `experimentKey` |

### 2. Fetch per run

`get_experiment_summary(experiment_id)` (final/best values; "best" = max), `get_experiment_parameters`,
`get_experiment_details` (name, tags, URL). Independent calls; issue them together. For curves, not just
final values: `get_experiment_metric_data(experiment_ids=[...], metric_names=["val_accuracy"])`.

### 3. SDK fallback

If a tool errors, use the snippet in `AGENTS.md` > "Comet MCP server" and tell the user MCP was unavailable.

### 4. Render

Metric rows: `val_accuracy`, `train_accuracy`, `train_loss` first, then the rest alphabetically. Best =
max for accuracy-like names, min for loss/error-like; anything else gets no highlight. Delta column only
for exactly two runs. Metrics present in only some runs show `-` elsewhere; the gap is information.

```markdown
### 2 runs

| Run | Tags | URL |
|-----|------|-----|
| demo-iris-classifier-20261111-1430 (a1b2c3) | example, framework=sklearn | <url> |
| demo-iris-classifier-20261110-0915 (d4e5f6) | example, framework=sklearn | <url> |

| Metric | a1b2c3 | d4e5f6 | delta |
|--------|--------|--------|-------|
| val_accuracy | **0.967** | 0.933 | +0.034 |
| train_loss | 0.21 | **0.18** | +0.03 |

| Param | a1b2c3 | d4e5f6 |
|-------|--------|--------|
| learning_rate | **0.1** | 0.01 |
| epochs | 20 | 20 |
```

End with one line: which run leads on how many metrics, and whether the hyperparameter diff explains it.

## Anti-patterns

- Comparing runs from different projects without saying so.
- Calling `get_experiment_metric_data` without `metric_names` (required) when summaries are enough.
- Promoting from here; hand off to `/evaluate-run` and `/promote-model`.
