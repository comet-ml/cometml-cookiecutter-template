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

1. **Verify `.env` exists and `COMET_API_KEY` is non-empty.** Without it, `comet_ml.Experiment(...)` falls back to anonymous or fails. If missing, stop and tell the user to `cp .env.example .env` and fill in their key.
2. **Verify the shell session has env loaded** (the user must have run `set -a && source .env && set +a` before launching Claude Code). Check by reading `$COMET_API_KEY` — if empty, instruct the user how to load it.

## Procedure

### 1. Run training and capture exit code in the same shell invocation

`$PIPESTATUS` is process-local — it does **not** survive across separate Bash tool calls. Capture the exit code inside the same command:

```bash
LOG=/tmp/$(basename "$PWD")-train-$(date +%s).log
make train > >(tee "$LOG") 2>&1; echo "TRAIN_EXIT_CODE=$?"
```

(Using process substitution `> >(tee …) 2>&1` rather than a pipe to `tee`, so `$?` reflects `make`'s exit, not `tee`'s. Works in `bash`; if the shell is plain `sh` use `make train 2>&1 | tee "$LOG"; echo "TRAIN_EXIT_CODE=${PIPESTATUS[0]}"` instead — same line, no separate tool call.)

Grep the output for `TRAIN_EXIT_CODE=` to determine success.

### 2. On non-zero exit

- Print the last 30 lines of `$LOG`.
- Identify the exception class and message.
- **Stop** — do not retry or auto-fix. Surface the error to the user.

### 3. On success, extract from the log

- **Experiment URL** — domain-agnostic regex (matches both SaaS `www.comet.com` and self-hosted via `COMET_URL_OVERRIDE`):
  ```
  https://[^/\s]+/[^/\s]+/[^/\s]+/[a-z0-9]{32,50}
  ```
  Comet experiment IDs are 32-50 alphanumeric characters.
- **Registered models** — lines matching `Successfully registered '<name>'`.
- **Logged artifacts** — lines matching `Artifact '<workspace>/<name>:<version>' has been fully uploaded`.
- **Final metrics** — `train.py` examples log `train_accuracy` / `test_accuracy` / `loss`. Grep the log for those metric names with their final values.

### 4. Print a markdown summary

```markdown
### Training run complete

- **Experiment:** <URL>
- **Final metrics:** train_accuracy=0.97, test_accuracy=0.93
- **Registered models:** iris-classifier (status: Development, tag: example)
- **Logged artifacts:** iris-dataset:1.0.0
```

The training examples register models with `status="Development"` + `tags=["example"]`. To promote, use the `promote-model` skill — `register_model` only initializes; later status changes go through `scripts/registry_mutate.py`.

### 5. Suggest follow-ups

- `/evaluate-run <id>` to gate the run against thresholds.
- `/compare-runs <id1> <id2>` to diff against a baseline.
- `/promote-model <model_name>` to advance the model's registry status once eval passes.

## Anti-patterns

- Don't retry `make train` on failure — the failure may have partially logged to Comet; re-running creates a duplicate.
- Don't auto-edit `train.py` to "fix" a failed run. Surface the error and let the user decide.
- Don't run training without confirming the user actually wants a new experiment — they cost compute + Comet quota.
- Don't print the API key or any other env var value — the log may contain it if `train.py` mis-logs.
- Don't assume `$PIPESTATUS` survives across Bash tool invocations. It doesn't.

## Cross-references

- `.claude/rules/comet-em-best-practices.md` — what to log and how.
- `evaluate-run`, `compare-runs`, `promote-model` — common follow-ups.
