---
paths:
  - "src/**"
  - "scripts/**"
  - "notebooks/**"
  - "tests/**"
---

# Comet EM Best Practices

Rules for working with `comet-ml` in this project, in lifecycle order: **config -> data -> training ->
model -> registry -> consume**. The runnable version of every rule is `src/{{ cookiecutter.module_name }}/`
(`dataset.py`, `train.py`, `sweep.py`, `predict.py`); when this file and that code disagree, fix the one
that is wrong rather than working around it.

## 0. Credentials and configuration

- Read `COMET_API_KEY`, `COMET_WORKSPACE`, `COMET_PROJECT_NAME`, `COMET_URL_OVERRIDE` through
  `src/{{ cookiecutter.module_name }}/config.py` (it loads `.env`). Never hardcode a key, never print one.
- `.env` is gitignored and the Read tool is denied on it in `.claude/settings.json`. Share `.env.example` instead.
- Every SDK setting is an env var (`COMET_*`), a `.comet.config` entry, or a `comet_ml.login(...)` argument.
  Env var wins. Reference: <https://www.comet.com/docs/v2/guides/experiment-management/configure-sdk/>.
  Common ones: `COMET_TIMEOUT_CLEANING` / `COMET_TIMEOUT_UPLOAD` (slow `end()`), `COMET_AUTO_LOG_*`
  (per-framework autologging), `COMET_LOGGING_FILE_LEVEL`, `COMET_START_ONLINE=false` (offline).
- Automated jobs (CI, schedulers) use a **Service Account** key, not a person's:
  <https://www.comet.com/docs/v2/guides/comet-ui/admin-dashboard/service-accounts/>.

## 1. One experiment per run, created with `comet_ml.start()`

```python
import comet_ml
from {{ cookiecutter.module_name }} import config

experiment = comet_ml.start(
    project_name=config.COMET_PROJECT_NAME,
    experiment_config=comet_ml.ExperimentConfig(
        name=config.experiment_name("iris-classifier"),
        tags=["example", "framework={{ cookiecutter.framework }}"],
    ),
)
try:
    ...
finally:
    experiment.end()
```

- `start()` reads the key, workspace and URL from the environment, honors `COMET_START_ONLINE=false`,
  can resume by `experiment_key`, and reuses the running experiment when a notebook cell re-runs.
  `comet_ml.Experiment(...)` still works but has none of that.
- `Experiment` is **not** a context manager: `try/finally: experiment.end()`.
- One run = one experiment. A sweep is many experiments (see `sweep.py`).

## 2. Naming and tags

- Names come from `config.experiment_name(model_name)`:
  `{project}-{model}-{YYYYMMDD}-{HHmm}` in UTC. Unique across archived runs, sortable, readable.
  Never append a counter: archiving an experiment frees its number and the next run collides.
- Tags carry the dimensions you filter on: `key=value` for sortable ones (`framework=pytorch`,
  `dataset=v2`), single words for stages (`baseline`, `sweep`, `exploration`). Don't pack them into the name.
- Comet logs git SHA, uncommitted patch, packages, host and CLI args on its own. Don't duplicate them.

## 3. Datasets: one Artifact, consumed by version

- `make data` writes `data/processed/iris-*.csv` and logs them as a new version of Artifact
  `iris-dataset`. Run it when the data changes, not before every training run.
- Training reads the CSVs and records lineage with `experiment.get_artifact("iris-dataset")`
  (`dataset.record_lineage`). It never re-logs the dataset. The version lands in registry metadata.
- Data that lives in S3/GCS stays there: register a remote Artifact (`artifact.add_remote(uri)`) so Comet
  stores the reference and checksum. For a cheap fingerprint without an Artifact, `experiment.log_dataset_hash(df)`.

## 4. Metrics, parameters, assets

| Kind | API | When |
|------|-----|------|
| Hyperparameters | `experiment.log_parameters(dict)` | Once, at start (`train()` does it) |
| Per-epoch metrics | `experiment.log_metrics(dict, epoch=...)` | Every epoch; `step=` for batches |
| Confusion matrix | `experiment.log_confusion_matrix(y_true=, y_predicted=, labels=)` | After eval |
| Figures / tables / text | `log_figure`, `log_table`, `log_text` | When produced |

- Autologging covers Keras `fit`, PyTorch `backward`, sklearn params, XGBoost `eval_set` curves.
  Either rely on it or log yourself under different names (`train.py` sets `auto_metric_logging=False`
  and logs `train_*` / `val_*`). Logging the same name twice at the same step overwrites silently.
- The metric that gates promotion is `val_accuracy`; `thresholds.yaml` holds the bar.

## 5. Models: log, then register, then consume

- Save the model **with its preprocessing** (`train.save_model`: sklearn `Pipeline`, a scaling layer or
  buffers, or stats in the file) and `experiment.log_model(name, path)`. A registry version must run on
  raw features; a model that needs the training-time scaler recomputed elsewhere is not deployable.
  `comet_ml.integration.<framework>.log_model` helpers exist, but note the pytorch one saves a
  state_dict, not a module. A logged model lives inside one experiment.
- Register only a run that cleared its gate, after `experiment.end()`, through the REST client:
  `api.get_experiment_by_key(key).register_model(name, version=, status=, tags=, metadata=)`. It is
  synchronous and raises when the backend rejects the version. (`experiment.register_model` is
  fire-and-forget: a rejection is only logged at `end()`.) `version` is semver and required in
  practice: it defaults to `1.0.0` and duplicates are rejected. `train.py` bumps the patch of the
  latest version; bump minor for a retrain with new hyperparameters, major for new data or architecture.
- `metadata=` carries provenance: dataset Artifact version and the final metrics. Comet already logs the
  git SHA on the experiment; the registry version links to it through `experimentKey`.
- **Status** is one value per version (`None`, `Development`, `Staging`, `QA`, `Production` by default;
  workspace-configurable, with an approval workflow). **Tags** are free-form and many. Deploy pipelines
  select by status; humans slice by tags. Comet does **not** demote the previous holder when you set a
  new one: `/promote-model` handles that explicitly.
- Status changes after registration go through `scripts/registry_mutate.py` (`/promote-model`), never
  ad-hoc `python -c`. Reading the registry (versions, status, tags) also goes through that script: the
  MCP server has no registry tools.
- Consume by status, never by local path: `api.get_model(ws, name).find_versions(status="Production")[0]`
  then `.download(version, output_folder=...)` and `predict.load_from_dir`. `predict.py` is the
  reference; the deploy workflow does the same from a status-change webhook.

## 6. Agents: the Comet MCP server

Setup, the workspace/project rule, the tool table and the SDK fallback live in `AGENTS.md` (always
loaded), section "Comet MCP server". Two things to remember here: the server reads experiments only
(no registry access; that is `scripts/registry_mutate.py`), and every query names `workspace=` and
`project_name=` from `.env`.

## 7. Offline runs

`COMET_START_ONLINE=false make train` writes `.cometml-runs/<key>.zip`; upload later with
`comet upload <zip>`. Offline experiments cannot log or fetch Artifacts and cannot register models, so
`train.py` skips both. Use it for airgapped training, not for CI (CI runs the credential-free tests).

## Anti-patterns

- Hardcoded or printed API keys; reading `.env` from the agent.
- A counter in the experiment name; a name that tries to be the tag list.
- Re-uploading the dataset Artifact on every run.
- Registering every run, or registering without `version=` after the first.
- Two versions in `Production` because the old one was never demoted.
- Loading a model from `models/*.pkl` in serving code instead of the registry.
- MCP queries without `workspace=` / `project_name=`.
- `COMET_MODE=offline` (not a setting), `comet_ml.config.set_config` (does not exist),
  `api.download_registry_model` (deprecated; use `Model.download`).

## Lifecycle checklist (paste into PR description)

- [ ] Experiment created with `comet_ml.start()` and named via `config.experiment_name`
- [ ] Dataset consumed from the `iris-dataset` Artifact, not re-uploaded
- [ ] Per-epoch `train_*` / `val_*` metrics and a confusion matrix logged
- [ ] Model logged; registered only when `thresholds.yaml` passes, with semver + metadata
- [ ] Status changes done through `/promote-model`, previous holder demoted
- [ ] `experiment.end()` in `finally`
