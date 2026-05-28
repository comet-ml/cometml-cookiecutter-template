---
name: compare-runs
description: Pull 2+ Comet experiments via the Comet MCP server (or `comet_ml.API` as fallback) and render a side-by-side markdown table of metrics and hyperparameters. Highlights the winning value per metric row. Use when the user asks to "compare", "diff", "which run won", or "baseline vs new".
---

# Compare Runs

Side-by-side comparison of N experiments. Surfaces metric deltas + hyperparameter differences so the user can pick a winner or spot the variable that mattered.

## When to run

- "Compare run X to run Y" / "diff these experiments".
- "Which baseline beat which?" — pass the tag (e.g. `baseline`) or a list of IDs.
- Before promotion: confirm the candidate beats the current production model.

## Inputs

Accept any of:

- A list of experiment IDs: `[id1, id2, ...]`.
- A tag query: `tag=baseline` or `tag=arch=resnet50`.
- A project + N-most-recent: `latest=5`.

Minimum 2 experiments. Maximum 8 (table becomes unreadable beyond that — warn the user and ask which to drop).

## Procedure

### 1. Resolve experiment list

- **IDs**: use as-is.
- **Tag query**: MCP tool `list_experiments` filtered by tag (post-filter the results if the MCP tool doesn't accept a tag arg).
- **`latest=N`**: MCP `list_experiments`, sort by created-at, take top N.

### 2. Fetch per experiment

MCP tools (snake_case, NOT `comet-mcp__list-experiments` style):

| MCP tool | Purpose |
|----------|---------|
| `list_experiments` | List experiments in a project |
| `get_experiment_details` | Metadata, tags, URL |
| `get_experiment_metric_data` | All logged metric values + steps |
| `get_experiment_parameters` | Hyperparameters |

For each experiment, call all three of `get_experiment_details`, `get_experiment_metric_data`, `get_experiment_parameters`. Fan out — the queries are independent.

### 3. SDK fallback (if MCP tool fails)

```bash
uv run python -c "
from comet_ml import API
from {{ cookiecutter.module_name }} import config
api = API()
for eid in ['$ID1', '$ID2']:
    exp = api.get_experiment(eid)
    print('---')
    print('id:', exp.id)
    print('url:', exp.url)
    print('tags:', exp.get_tags())
    print('metrics:', exp.get_metrics())
    print('params:', exp.get_parameters_summary())
"
```

For tag-based discovery via SDK:

```bash
uv run python -c "
from comet_ml import API
from {{ cookiecutter.module_name }} import config
api = API()
exps = api.get_experiments(workspace=config.COMET_WORKSPACE, project_name=config.COMET_PROJECT_NAME)
matches = [e for e in exps if 'baseline' in e.get_tags()]
for e in matches: print(e.id, e.url)
"
```

### 4. Determine metric union

The set of metric names seen in any experiment. Order: alphabetical, but pin `train_accuracy`, `test_accuracy`, `loss` to the top in that order if present.

### 5. Render markdown

```markdown
### Comparison: <N> experiments

| Experiment | URL | Tags |
|------------|-----|------|
| <name1> (<short_id1>) | <url> | baseline |
| <name2> (<short_id2>) | <url> | candidate |

#### Metrics

| Metric | <short_id1> | <short_id2> | Δ |
|--------|-------------|-------------|---|
| test_accuracy | 0.93 | **0.95** ✅ | +0.02 |
| loss          | **0.41** ✅ | 0.45 | +0.04 |

#### Hyperparameter diff

| Param | <short_id1> | <short_id2> |
|-------|-------------|-------------|
| learning_rate | 0.01 | **0.001** |
| max_iter      | 200  | 200 |
```

- "Best" cell: max for accuracy-style metrics, min for loss/error-style. If ambiguous (custom metric name), don't auto-pick — print without ✅.
- Δ column only when N=2. For N>2, skip Δ and just bold the winners.

### 6. Summary line

At the bottom: "Run X wins on K/M metrics; consider it for promotion" — only if a clear winner emerges.

## Anti-patterns

- Don't promote based on this skill — call out the winner but let the user run `/evaluate-run` + `/promote-model` explicitly.
- Don't compare runs from different projects without flagging it loudly. Cross-project comparison usually means different data / different metric semantics.
- Don't hide metrics that appear in only one experiment. Show them with `—` for the others — the asymmetry itself is signal.
- Don't silently swallow an MCP tool-not-found error. Fall back to the SDK and tell the user MCP was unavailable.

## Cross-references

- Logging discipline: `.claude/rules/comet-em-best-practices.md` — runs are only comparable if they log the same metric names and hyperparameter shape.
- `evaluate-run` — single-experiment threshold check.
- `promote-model` — once a winner emerges and passes evaluation.
- Comet API reference: <https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/API/>.
