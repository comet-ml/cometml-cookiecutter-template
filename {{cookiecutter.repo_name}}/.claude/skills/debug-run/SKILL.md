---
name: debug-run
description: Explain why a Comet experiment failed or looks wrong by reading its stdout/stderr, code snapshot, parameters, metric curves and assets through the Comet MCP server. Use when the user asks "why did this run fail", "what went wrong with <id>", "did it diverge" or "what did run X actually log".
argument-hint: "<experiment-id | latest>"
---

# Debug Run

Depends on: Comet MCP server (`mcp__comet-mcp__*`, needs `COMET_API_KEY` / `COMET_WORKSPACE` exported
in the shell), `.env` for `COMET_WORKSPACE` / `COMET_PROJECT_NAME`.

Read-only. Nothing here changes the experiment or the code.

## Procedure

1. Resolve `latest` with `list_experiments(workspace, project_name, page_size=1, sort_by="startTime",
   sort_order="desc")`; always pass both from `.env`.
2. Pull, in parallel:
   - `get_experiment_details(id)`: name, tags, duration, whether it ended cleanly.
   - `get_experiment_output(id)`: the captured stdout/stderr. Tracebacks, `COMET WARNING` lines and the
     `not registered: ...` / `dataset lineage not recorded` messages from `train.py` live here.
   - `get_experiment_training_progress(id, metric_names=["train_loss", "val_accuracy"])`: diverging or flat
     curves.
   - `get_experiment_parameters(id)`: what the run actually used (`--epochs 0`, a wrong learning rate).
   - `get_experiment_code(id)` when the behaviour does not match the current `train.py`.
   - `get_experiment_assets(id)` and `analyze_experiment_asset(id, name_filter)` for the confusion matrix
     or any logged file.
3. Diagnose in this order: crash (traceback in output) -> configuration (parameters) -> data (lineage
   warning, dataset version) -> training dynamics (curves) -> code drift (snapshot vs `src/`).
4. Report: one paragraph with the cause, the evidence line(s) quoted, and the smallest next step
   (`make train ARGS=...`, `make data`, a code fix the user applies).

## Anti-patterns

- Editing `train.py` or re-running training from here.
- Guessing from the local log when the run reached Comet; the server has the full output.
- Calling `get_experiment_metric_data` without `metric_names`.
