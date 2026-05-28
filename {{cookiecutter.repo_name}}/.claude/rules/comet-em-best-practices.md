# Comet EM Best Practices

Behavioral rules for AI assistants working with `comet-ml` in this project. Organized around the MLOps lifecycle: **config → data → training → model → registry → reuse**.

## Reference: full SDK configuration

The complete configuration surface (timeouts, retry policy, batching, log levels, telemetry, offline mode, backend URLs) is documented at:

**<https://www.comet.com/docs/v2/guides/experiment-management/configure-sdk/>**

Consult that page first when diagnosing:

- Upload/sync timeouts (`COMET_TIMEOUT_*` vars)
- Slow `experiment.end()` flushes (raise `COMET_STREAMER_*` workers)
- Connection refused / `url_override` issues
- Auto-logging behavior toggles (per-framework, e.g. `COMET_AUTO_LOG_*`)
- File-upload size limits and chunking
- Log-level / verbosity (`COMET_LOGGING_*`)

All settings can be set via env var (preferred — keep them in `.env`), via `.comet.config`, or programmatically via `comet_ml.config.set_config`. Env var wins.

## 0. Credentials — never hardcode

- Read `COMET_API_KEY`, `COMET_WORKSPACE`, `COMET_PROJECT_NAME`, `COMET_URL_OVERRIDE` from `src/{{ cookiecutter.module_name }}/config.py` (loads `.env` via `python-dotenv`).
- `.env` is gitignored. Never commit it. Never paste API keys into code, notebooks, READMEs, or chat messages.
- `COMET_URL_OVERRIDE` defaults to the public SaaS clientlib endpoint. Change only for single-tenant / on-prem deployments — see the [SDK configuration docs](https://www.comet.com/docs/v2/guides/experiment-management/configure-sdk/).
- For shared examples, refer to `.env.example`.

```python
import comet_ml
from {{ cookiecutter.module_name }} import config

experiment = comet_ml.Experiment(
    api_key=config.COMET_API_KEY,
    workspace=config.COMET_WORKSPACE,
    project_name=config.COMET_PROJECT_NAME,
)
```

## 1. One Experiment per run

- Construct `comet_ml.Experiment(...)` once at the start of a training/evaluation run.
- Always call `experiment.end()` (or use a `try/finally`) — otherwise the last batch of metrics may not flush.
- Don't share an `Experiment` across multiple training runs. Each run = one Experiment.

```python
try:
    # ... training ...
finally:
    experiment.end()
```

## 2. Log code + environment for reproducibility

At the start of every run:

```python
experiment.log_code(folder="src")                  # snapshot of src/ at run time
experiment.log_parameters(hyperparams)             # all hyperparams as a dict
experiment.set_name("baseline-iris-2026-05-28")    # optional human label
experiment.add_tags(["baseline", "framework={{ cookiecutter.framework }}"])
```

Comet automatically logs: git commit SHA, git patch (uncommitted diff), Python version, installed packages, hostname, CLI args. Don't duplicate these manually.

## 3. Log datasets

Three options, in increasing power:

### 3a. Quick fingerprint — `log_dataset_hash`

```python
experiment.log_dataset_hash(df)   # logs an MD5 of the data
```

Cheap; lets you confirm two runs used the exact same data. Doesn't preserve the data itself.

### 3b. Metadata reference — `log_dataset_info`

```python
experiment.log_dataset_info(name="iris-v1", version="1.0.0", path="data/processed/")
```

Records what dataset was used without uploading it. Use when the dataset lives in S3/GCS/HF and is identified by a path or version.

### 3c. Versioned artifact — `log_artifact` (recommended for first-class datasets)

```python
from comet_ml import Artifact

artifact = Artifact(name="iris-dataset", artifact_type="dataset")
artifact.add("data/processed/iris-train.csv")
artifact.add("data/processed/iris-test.csv")
experiment.log_artifact(artifact)
```

Artifacts are workspace-level, versioned, and **reusable across experiments**. See section 6.

## 4. Log metrics, hyperparameters, plots

| Kind | API | When |
|------|-----|------|
| Hyperparameters | `experiment.log_parameters(dict)` | Once, at start |
| Scalar metrics | `experiment.log_metric(name, value, step=...)` | Every step/epoch |
| Multiple metrics | `experiment.log_metrics(dict, step=...)` | Same — batched |
| Final metrics | `experiment.log_metric("test_accuracy", ...)` | At eval |
| Confusion matrix | `experiment.log_confusion_matrix(y_true, y_pred)` | At eval |
| Figures | `experiment.log_figure(name, matplotlib_fig)` | When generated |
| Tables | `experiment.log_table(name, dataframe)` | When generated |
| Text | `experiment.log_text(text)` | For traces, prompts, predictions |

## 5. Log + version models

After training, persist the model to disk and log it to the experiment:

```python
# 1. Save to disk (framework-specific)
import joblib
joblib.dump(model, "models/iris-classifier.pkl")

# 2. Log to the experiment
experiment.log_model(
    name="iris-classifier",
    file_or_folder="models/iris-classifier.pkl",
)
```

Logged models live **inside the experiment**. They are tied to that single run. To make them discoverable and promotable across the workspace, you need section 6.

### Framework-specific save patterns

| Framework | Save |
|-----------|------|
| sklearn | `joblib.dump(model, "models/foo.pkl")` |
| xgboost | `model.save_model("models/foo.json")` |
| pytorch | `torch.save(model.state_dict(), "models/foo.pt")` |
| tensorflow | `model.save("models/foo.keras")` |

## 6. Register models to the Model Registry

The **Model Registry** is the workspace-level catalog used by deploy/serve pipelines. Promote your logged model after the run is good enough:

```python
# Promote the model logged in step 5 to the workspace registry.
experiment.register_model(
    model_name="iris-classifier",                # registry name (workspace-unique)
    version="1.0.0",                             # optional — Comet auto-increments if omitted
    tags=["staging"],                            # ["staging"], ["production"], or custom
    public=False,
    description="Baseline LR; trained on iris-v1 dataset.",
)
```

Conventions:

- **tags** — start at `staging`. Promote to `production` only after evaluation passes a gate (separate run, separate metric thresholds). Tags are the modern Comet API for stage labels (replaces the deprecated `stages=`).
- **version** — semver. Bump minor for retrains on same data + tweaked hparams, bump major for new dataset or new architecture.
- **description** — terse, references the dataset version and any non-default training config.

To consume a registered model elsewhere:

```python
from comet_ml import API

api = API()
api.download_registry_model(
    workspace=config.COMET_WORKSPACE,
    registry_name="iris-classifier",
    version="1.0.0",
    output_path="models/",
)
```

## 7. Reuse datasets across experiments

Pull a previously logged artifact in a new run:

```python
logged_artifact = experiment.get_artifact(
    artifact_name="iris-dataset",
    workspace=config.COMET_WORKSPACE,
    version_or_alias="1.0.0",      # or "latest"
)
logged_artifact.download(path="data/external/iris/")
```

This gives you provenance (you know exactly which dataset version this run used) without re-uploading.

## 8. Tagging conventions

Tags are queryable in the Comet UI — use them to slice runs.

```python
experiment.add_tag("baseline")
experiment.add_tags(["arch=resnet50", "dataset=cifar10-v2", "lr=0.01"])
```

- `key=value` tags for sortable dimensions (lr, arch, dataset version).
- Single-word tags for stages (`baseline`, `ablation`, `final`, `production-candidate`).
- Don't pack everything into the experiment name — use tags so the UI can filter.

## 9. Hyperparameter sweeps

Use `comet_ml.Optimizer` over hand-rolled grid/random loops. It logs the sweep config server-side and streams trial results:

```python
opt_config = {
    "algorithm": "bayes",
    "spec": {"metric": "test_accuracy", "objective": "maximize"},
    "parameters": {"lr": {"type": "float", "min": 1e-4, "max": 1e-1}},
    "name": "iris-lr-sweep",
}
optimizer = comet_ml.Optimizer(opt_config)

for experiment in optimizer.get_experiments(
    project_name=config.COMET_PROJECT_NAME,
    workspace=config.COMET_WORKSPACE,
):
    lr = experiment.get_parameter("lr")
    # ... train, log_metric("test_accuracy", ...) ...
    experiment.end()
```

One `Experiment` per trial.

## 10. Offline mode

For airgapped or CI environments:

```bash
COMET_MODE=offline make train
```

Writes a `.zip` under `./.cometml-runs/` that uploads later with `comet upload <file>.zip`.

## Anti-patterns

- `experiment = comet_ml.Experiment(api_key="abc123...")` — hardcoded key. Use `config.COMET_API_KEY`.
- Logging the same metric name twice in the same step — overwrites silently.
- Forgetting `experiment.end()` — last writes lost.
- Mixing multiple training runs into one Experiment — defeats the purpose.
- Logging a model with `log_model` but never `register_model` — model is buried inside one experiment, invisible to deploy pipelines.
- Re-uploading the same dataset on every run instead of `get_artifact(...)`.
- Hardcoding model paths instead of pulling from the registry — breaks reproducibility.

## Lifecycle checklist (paste into PR description)

- [ ] `log_code`, `log_parameters`, tags set at start
- [ ] Dataset logged via `log_artifact` (or `log_dataset_info` if external)
- [ ] Metrics logged per step + final eval metric
- [ ] Model saved to `models/` and logged via `log_model`
- [ ] If run is a candidate for deployment: `register_model` with stage + description
- [ ] `experiment.end()` in a `try/finally`
