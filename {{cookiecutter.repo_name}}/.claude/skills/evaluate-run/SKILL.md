---
name: evaluate-run
description: Query a single Comet experiment via the Comet MCP server, fetch its metrics and parameters, and compare against thresholds (inline or from `thresholds.yaml`). Reports pass/fail per metric with a markdown table. Use when the user asks to "evaluate", "gate", or "check" a specific run before promotion.
---

# Evaluate Run

Pull a single experiment's metrics from Comet via MCP and compare against thresholds. Outputs a pass/fail report that gates the next workflow step (typically `promote-model`).

## When to run

- After `run-training` completes, before deciding whether to promote.
- When a user wants to verify a historical run still meets quality bars.
- As an automated gate inside `promote-model`.

## Inputs

- **`experiment_id`** (required) — the Comet experiment ID (32-char hex). If the user says "the latest run", use the MCP to find it.
- **`thresholds`** — optional. Two sources, checked in order:
  1. User provides inline: `{"test_accuracy": ">=0.85", "loss": "<=0.5"}`.
  2. `thresholds.yaml` in project root, shape:
     ```yaml
     test_accuracy: ">=0.85"
     loss: "<=0.5"
     ```
  If neither, skip pass/fail — just print metrics summary.

## Procedure

1. **Resolve experiment**:
   - If `experiment_id` given: use it.
   - If user said "latest": call MCP tool `comet-mcp__list-experiments` for `${COMET_WORKSPACE}/${COMET_PROJECT_NAME}` and take the most recent.
2. **Fetch via MCP**:
   - `comet-mcp__get-experiment` (metadata, tags, URL).
   - `comet-mcp__get-experiment-metrics` (final values).
   - `comet-mcp__get-experiment-parameters` (hyperparams).
3. **Apply thresholds** (if provided):
   - For each declared metric, parse the comparison (`>=`, `<=`, `>`, `<`, `==`).
   - Evaluate `actual <op> threshold`.
   - Collect pass/fail per metric.
4. **Render markdown table**:
   ```markdown
   ### Experiment <id> — <PASS|FAIL>

   **URL:** <experiment_url>
   **Tags:** baseline, framework=sklearn

   | Metric | Value | Threshold | Result |
   |--------|-------|-----------|--------|
   | test_accuracy | 0.93 | >=0.85 | ✅ |
   | loss          | 0.41 | <=0.5  | ✅ |

   **Hyperparameters:**
   - max_iter: 200
   - solver: lbfgs
   ```
5. **Hand off**:
   - PASS → tell user they can `/promote-model <model_name>` referencing this experiment ID.
   - FAIL → list failing metrics; suggest checking the run details, adjusting hyperparams, or retraining.

## Anti-patterns

- Don't fabricate thresholds. If none are provided, just summarize.
- Don't promote a model from this skill — that's `promote-model`'s job (and it's irreversible-ish).
- Don't fetch metrics by parsing local logs. The MCP server is the source of truth — local logs may be stale.
- Don't treat "metric exists but not in threshold list" as failing. Only declared thresholds count.

## Cross-references

- Logging discipline (what gets logged so we can evaluate it): `.claude/rules/comet-em-best-practices.md`.
- SDK configuration reference (for timeouts when MCP queries are slow): <https://www.comet.com/docs/v2/guides/experiment-management/configure-sdk/>.
