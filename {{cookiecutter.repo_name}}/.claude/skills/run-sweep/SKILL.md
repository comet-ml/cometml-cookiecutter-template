---
name: run-sweep
description: Run `make sweep` (a comet_ml.Optimizer bayes search over train()), then summarise the trials with the Comet MCP server and point at the best one. Use when the user asks to "sweep", "tune", "search hyperparameters" or "find a better learning rate".
argument-hint: "[--max-combo N]"
disable-model-invocation: true
---

# Run Sweep

Depends on: `make sweep` (`src/<module>/sweep.py`, `OPTIMIZER_CONFIG`), `make data`, Comet MCP server for
the summary, `.env`. Optimizer details: [reference.md](reference.md).

The sweep creates one experiment per trial, tagged `sweep`, in the project from `.env`. It never
registers a model: the follow-up is `make train ARGS="--learning-rate <best> --epochs <best>"`
through `/run-training`, which applies the threshold gate.

## Procedure

1. Confirm with the user: `max_combo` trials (default 8, from `OPTIMIZER_CONFIG`) each cost a full
   `train()` run. Adjust the space in `sweep.py` first if they want other parameters.
2. Run, capturing the exit code in the same command:
   ```bash
   LOG=/tmp/$(basename "$PWD")-sweep-$(date +%s).log
   make sweep ARGS="$ARGUMENTS" > >(tee "$LOG") 2>&1; echo "SWEEP_EXIT_CODE=$?"
   ```
   The script prints `best val_accuracy=<v> experiment=<key>` and `sweep id: <id>` at the end.
3. Summarise with MCP (`AGENTS.md` > "Comet MCP server" for setup):
   `find_tagged_experiments(tag="sweep=<sweep id>", ...)` for this sweep's trial keys (plain `sweep`
   returns every past sweep), then
   `experiment_spreadsheet(workspace, project_name, experiment_keys=[...])` for a CSV of parameters and
   final metrics, or `get_experiment_summary` per trial when there are few.
4. Report: a table of trials (`learning_rate`, `epochs`, `val_accuracy`), the best trial's name, key and
   URL, and the exact `make train ARGS=...` line to reproduce it. Mention the parallel coordinates
   chart in the project view for the visual version.

## Anti-patterns

- Running a sweep the user did not ask for, or raising `max_combo` silently.
- Registering the best trial from here.
- Reading results from the log alone when the MCP server is available; the log has only the best one.
