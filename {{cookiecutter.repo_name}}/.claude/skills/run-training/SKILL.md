---
name: run-training
description: Execute `make train`, capture output, and surface the Comet experiment URL, registered models, logged artifacts, and final metrics. Use when the user asks to "run a training run", "train the model", or "kick off an experiment". Pure shell wrapper — does not use the Comet MCP server.
---

# Run Training

Invoke the project's example training script and present a clean summary of the resulting Comet experiment.

## When to run

- User asks for a training run, an experiment, or "let's train".
- After a code change in `src/<module>/train.py` to verify the run still completes.
- As the first step of any new workflow that ends with `evaluate-run` or `compare-runs`.

## Pre-flight

1. **Verify `.env` exists and `COMET_API_KEY` is non-empty.** Without it, `comet_ml.Experiment(...)` will fall back to anonymous or fail. If missing, stop and tell the user to `cp .env.example .env` and fill in their key.
2. **Verify the shell session has the env loaded** (the user must have run `set -a && source .env && set +a` before launching Claude Code). Check by reading `$COMET_API_KEY` — if empty, instruct the user how to load it.

## Procedure

1. Run training and capture both streams to a tempfile:
   ```bash
   make train 2>&1 | tee /tmp/<module>-train-$(date +%s).log
   ```
2. Capture exit code (`${PIPESTATUS[0]}`). If non-zero:
   - Print the last 30 lines of the log.
   - Identify the exception class and message.
   - **Stop** — do not retry or auto-fix. Surface the error to the user.
3. On success, extract from the log:
   - **Experiment URL** — regex: `https://www\.comet\.com/[^/\s]+/[^/\s]+/[a-f0-9]+`.
   - **Registered models** — lines matching `Successfully registered '<name>'`.
   - **Logged artifacts** — lines matching `Artifact '<workspace>/<name>:<version>' has been fully uploaded`.
   - **Final metrics** — `train.py` examples log `train_accuracy` / `test_accuracy` / `loss`. Grep the log for those metric names with their final values.
4. Print a markdown summary:
   ```markdown
   ### Training run complete

   - **Experiment:** <URL>
   - **Final metrics:** train_accuracy=0.97, test_accuracy=0.93
   - **Registered models:** iris-classifier (tagged `staging`)
   - **Logged artifacts:** iris-dataset:1.0.0
   ```
5. Suggest follow-ups: `/evaluate-run <id>` to gate the run against thresholds, or `/compare-runs <id1> <id2>` to diff against a baseline.

## Anti-patterns

- Don't retry `make train` on failure — the failure may have logged a partial experiment to Comet; re-running creates a duplicate.
- Don't auto-edit `train.py` to "fix" a failed run. Surface the error and let the user decide.
- Don't run training without confirming the user actually wants a new experiment — they cost compute + Comet quota.
- Don't print the API key or any other env var value — the log may contain it if `train.py` mis-logs.
