---
name: run-training
description: Run `make train`, capture the output, and report the Comet experiment name + URL, final metrics, dataset version and whether a registry version was created. Use when the user asks to "run a training run", "train the model", or "kick off an experiment". Shell only; does not use the MCP server.
argument-hint: "[--register] [--epochs N] [--learning-rate X]"
disable-model-invocation: true
---

# Run Training

Depends on: `make train` (`src/<module>/train.py`), `make data`, `thresholds.yaml`, `.env` with
`COMET_API_KEY` / `COMET_WORKSPACE`.

Run one experiment and present a clean summary. `make train` builds the dataset CSVs if they are
missing, logs per-epoch metrics, a confusion matrix and the model, and registers a new patch version
only when `thresholds.yaml` passes (or `--register` is given).

## Pre-flight

1. A key must be available: `COMET_API_KEY` in `.env` or the shell, or `api_key` in `~/.comet.config`.
   Check without printing it: `grep -qE '^COMET_API_KEY=.+' .env 2>/dev/null || [ -n "$COMET_API_KEY" ] || grep -q api_key ~/.comet.config 2>/dev/null && echo set || echo missing`.
   If missing: tell the user to `cp .env.example .env` and fill it in; stop.
2. Training reads `.env` itself; no shell export needed (that is only for the MCP server).
3. Confirm the user wants a **new** experiment. Each run costs compute and creates a Comet experiment.

## Procedure

### 1. Run and capture the exit code in the same command

```bash
LOG=/tmp/$(basename "$PWD")-train-$(date +%s).log
make train ARGS="$ARGUMENTS" > >(tee "$LOG") 2>&1; echo "TRAIN_EXIT_CODE=$?"
```

`$?` / `$PIPESTATUS` do not survive across tool calls; the `echo` must be in the same invocation.

### 2. On non-zero exit

Print the last 30 lines of `$LOG`, name the exception, and **stop**. No retry (a retry creates a second
experiment), no editing `train.py`. For a run that reached Comet, `/debug-run <id>` reads its output.

### 3. On success, read the `summary:` line

`train.py` prints one line at the end, the only thing to parse:

```
summary: name=demo-iris-classifier-20261111-1430 dataset=iris-dataset:1.0.0 train_accuracy=0.9833 val_accuracy=0.9667 registered=1.0.3
```

- `name`: the experiment name. The URL is on the `COMET INFO: Experiment is live on comet.com <url>` line.
- `dataset`: the Artifact version used (`local` when `make data` has not run online).
- The metrics are **final** values (the Comet summary block above it prints min/max, not final).
- `registered`: the new version, or `none` (gate failed; the `not registered: ...` line says which
  metric). A registration the backend rejects raises, so the run exits non-zero before this line.

### 4. Summary

```markdown
### Training run complete

- **Experiment:** demo-iris-classifier-20261111-1430 (<URL>)
- **Final metrics:** train_accuracy=0.983, val_accuracy=0.967
- **Dataset:** iris-dataset:1.0.0
- **Registry:** iris-classifier 1.0.3 created, status Development
```

### 5. Follow-ups

- `/evaluate-run <id>` to re-check the run against `thresholds.yaml` from Comet's side.
- `/compare-runs latest=5` to put it next to recent runs.
- `/promote-model iris-classifier` to move the new version to Staging / QA / Production.

## Anti-patterns

- Don't retry on failure; don't auto-edit `train.py`.
- Don't print `COMET_API_KEY` or any `.env` value. `.claude/settings.json` denies reading `.env` for a reason.
- Don't pass `--register` on your own; the gate is the user's call.
