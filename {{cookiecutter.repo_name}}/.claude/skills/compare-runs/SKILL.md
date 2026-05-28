---
name: compare-runs
description: Pull 2+ Comet experiments via the Comet MCP server and render a side-by-side markdown table of metrics and hyperparameters. Highlights the winning value per metric row. Use when the user asks to "compare", "diff", "which run won", or "baseline vs new".
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

1. **Resolve experiment list**:
   - IDs: use as-is.
   - Tag query: `comet-mcp__list-experiments` filtered by tag.
   - `latest=N`: `comet-mcp__list-experiments` then sort by created-at, take top N.
2. **Fetch per experiment** (parallel-friendly):
   - `comet-mcp__get-experiment-metrics`
   - `comet-mcp__get-experiment-parameters`
   - `comet-mcp__get-experiment` (for tags, URL, name)
3. **Determine metric union**: the set of metric names seen in any experiment. Order: alphabetical, but pin `train_accuracy`, `test_accuracy`, `loss` to the top in that order if present.
4. **Render markdown**:
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
   - "Best" cell: max for accuracy-style metrics, min for loss/error-style. If ambiguous (custom metric name), don't auto-pick a winner — print without ✅.
   - Δ column only when N=2. For N>2, skip Δ and just bold the winners.
5. **Summary line** at the bottom: "Run X wins on K/M metrics; consider it for promotion" or similar — only if a clear winner emerges.

## Anti-patterns

- Don't promote based on this skill — call out the winner but let the user run `/evaluate-run` + `/promote-model` explicitly.
- Don't compare runs from different projects without flagging it loudly. Cross-project comparison usually means different data / different metric semantics.
- Don't hide metrics that appear in only one experiment. Show them with `—` for the others — the asymmetry itself is signal.

## Cross-references

- Logging discipline: `.claude/rules/comet-em-best-practices.md` — runs are only comparable if they log the same metric names and hyperparameter shape.
