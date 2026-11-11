---
name: evaluate-run
description: Check one Comet experiment against thresholds.yaml (or inline thresholds) using the Comet MCP server, with a comet_ml.API fallback. Reports pass/fail per metric with the final values. Use when the user asks to "evaluate", "gate", "check" or "does it pass" for a specific run or "the latest run", and as the gate inside /promote-model.
argument-hint: "<experiment-id | latest> [metric: \">=0.9\" ...]"
---

# Evaluate Run

Depends on: Comet MCP server (`mcp__comet-mcp__*`, needs `COMET_API_KEY` / `COMET_WORKSPACE` exported
in the shell), `thresholds.yaml`, `.env` for `COMET_WORKSPACE` / `COMET_PROJECT_NAME`.

## Inputs

- **experiment**: an experiment id/key, or `latest`.
- **thresholds**: inline (`val_accuracy: ">=0.9"`) or, by default, `thresholds.yaml` at the project
  root. `make train` applies the same file, so a PASS here means the run would have registered.
  "Value" is the metric's **final** value; say so in the report. Best values are available from the
  same summary call if the user asks.

## Procedure

### 1. Resolve the experiment

`latest`: `list_experiments(workspace=<COMET_WORKSPACE>, project_name=<COMET_PROJECT_NAME>,
page_size=1, sort_by="startTime", sort_order="desc")`. Always pass both; without them the server
queries the account default workspace and project `general`.

### 2. Fetch

- `get_experiment_summary(experiment_id)`: final and best value per metric ("best" is the max; for losses read the SDK fallback's `valueMin`).
- `get_experiment_parameters(experiment_id)` and `get_experiment_details(experiment_id)`: hyperparameters,
  tags, name, URL.

### 3. SDK fallback (MCP unavailable or a tool errors; tell the user)

```bash
uv run python - <<'EOF'
from comet_ml import API
from {{ cookiecutter.module_name }} import config

api = API()
ws = config.COMET_WORKSPACE or api.get_default_workspace()
exp = api.get_experiment_by_key("<experiment-key>")   # or, for latest:
# exp = api.get_experiments(ws, config.COMET_PROJECT_NAME,
#                           page=1, page_size=1, sort_by="startTime", sort_order="desc")[0]
print(exp.name, exp.url, exp.get_tags())
for m in exp.get_metrics_summary():
    print(m["name"], "final", m["valueCurrent"], "max", m["valueMax"], "min", m["valueMin"])
print(exp.get_parameters_summary())
EOF
```

### 4. Apply thresholds

Parse `<op><number>` with op in `>=`, `<=`, `>`, `<`, `==`; evaluate against the final value. A metric
named in the thresholds but absent from the run is a FAIL with value `missing`. Metrics not named in the
thresholds are reported without a verdict.

### 5. Report

```markdown
### demo-iris-classifier-20261111-1430 (a1b2c3) -- PASS

URL: <url>   Tags: example, framework=sklearn   Dataset: iris-dataset:1.0.0

| Metric | Final | Threshold | Result |
|--------|-------|-----------|--------|
| val_accuracy | 0.967 | >=0.9 | pass |
| train_accuracy | 0.983 | - | - |

Hyperparameters: epochs=20, learning_rate=0.1, alpha=0.001
```

PASS: point to `/promote-model <model-name> <experiment-id>`. FAIL: list the failing metrics and suggest
`/compare-runs` against a passing run or a `/run-sweep`.

## Anti-patterns

- Fabricating thresholds when none exist: summarize instead.
- Reading metrics from local logs; Comet is the source of truth.
- Promoting from here. That is `/promote-model`.
- Swallowing an MCP error silently.
