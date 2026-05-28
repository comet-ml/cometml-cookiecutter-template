---
name: evaluate-run
description: Query a single Comet experiment via the Comet MCP server (or `comet_ml.API` as a fallback), fetch its metrics and parameters, and compare against thresholds (inline or from `thresholds.yaml`). Reports pass/fail per metric with a markdown table. Use when the user asks to "evaluate", "gate", or "check" a specific run before promotion.
---

# Evaluate Run

Pull a single experiment's metrics from Comet and compare against thresholds. Outputs a pass/fail report that gates the next workflow step (typically `promote-model`).

## When to run

- After `run-training` completes, before deciding whether to promote.
- When a user wants to verify a historical run still meets quality bars.
- As an automated gate inside `promote-model`.

## Inputs

- **`experiment_id`** (required) — the Comet experiment ID. If the user says "the latest run", discover it.
- **`thresholds`** — optional. Two sources, checked in order:
  1. User provides inline: `{"test_accuracy": ">=0.85", "loss": "<=0.5"}`.
  2. `thresholds.yaml` in project root, shape:
     ```yaml
     test_accuracy: ">=0.85"
     loss: "<=0.5"
     ```
  If neither, skip pass/fail — just print metrics summary.

## Procedure

### 1. Resolve experiment

- If `experiment_id` given: use it.
- If user said "latest": use the **Comet MCP** tool `list_experiments` for `${COMET_WORKSPACE}/${COMET_PROJECT_NAME}` and take the most recent.

### 2. Fetch via MCP

The Comet MCP server exposes these tools (note: snake_case, NOT `comet-mcp__list-experiments` style):

| MCP tool | Purpose |
|----------|---------|
| `list_experiments` | List experiments in a project |
| `get_experiment_details` | Metadata, tags, URL for one experiment |
| `get_experiment_metric_data` | All logged metric values + steps |
| `get_experiment_parameters` | Hyperparameters |
| `list_projects` | Projects in the workspace |

Call `get_experiment_details`, `get_experiment_metric_data`, and `get_experiment_parameters` for the target experiment ID.

### 3. SDK fallback (if MCP tool fails)

If the MCP server is unavailable or the tool name has shifted, fall back to `comet_ml.API` directly:

```bash
uv run python -c "
from comet_ml import API
api = API()
exp = api.get_experiment('$EXP_ID')
print('metrics:', exp.get_metrics())
print('params:', exp.get_parameters_summary())
print('tags:', exp.get_tags())
print('url:', exp.url)
"
```

For "latest" discovery via SDK:

```bash
uv run python -c "
from comet_ml import API
from {{ cookiecutter.module_name }} import config
api = API()
exps = api.get_experiments(workspace=config.COMET_WORKSPACE, project_name=config.COMET_PROJECT_NAME)
exps.sort(key=lambda e: e.start_server_timestamp, reverse=True)
print(exps[0].id, exps[0].url)
"
```

### 4. Apply thresholds (if provided)

For each declared metric:

- Parse the comparison (`>=`, `<=`, `>`, `<`, `==`).
- Evaluate `actual <op> threshold`.
- Collect pass/fail per metric.

### 5. Render markdown table

```markdown
### Experiment <id> — <PASS|FAIL>

**URL:** <experiment_url>
**Tags:** example, framework=sklearn

| Metric | Value | Threshold | Result |
|--------|-------|-----------|--------|
| test_accuracy | 0.93 | >=0.85 | ✅ |
| loss          | 0.41 | <=0.5  | ✅ |

**Hyperparameters:**
- max_iter: 200
- solver: lbfgs
```

### 6. Hand off

- PASS → tell user they can `/promote-model <model_name>` referencing this experiment ID.
- FAIL → list failing metrics; suggest checking the run details, adjusting hyperparams, or retraining.

## Anti-patterns

- Don't fabricate thresholds. If none are provided, just summarize.
- Don't promote a model from this skill — that's `promote-model`'s job (irreversible-ish).
- Don't fetch metrics by parsing local logs. The MCP server (or `comet_ml.API`) is the source of truth — local logs may be stale.
- Don't treat "metric exists but not in threshold list" as failing. Only declared thresholds count.
- Don't silently swallow an MCP tool-not-found error. Fall back to the SDK and tell the user that MCP was unavailable.

## Cross-references

- Logging discipline (what gets logged so we can evaluate it): `.claude/rules/comet-em-best-practices.md`.
- SDK configuration reference (for timeouts when MCP queries are slow): <https://www.comet.com/docs/v2/guides/experiment-management/configure-sdk/>.
- Comet API reference: <https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/API/>.
