# Optimizer and offline reference

Loaded on demand by `/run-sweep`. Docs: <https://www.comet.com/docs/v2/guides/optimizer/quickstart/>.

## comet_ml.Optimizer

```python
config = {
    "algorithm": "bayes",                      # or "grid", "random"
    "spec": {"metric": "val_accuracy", "objective": "maximize", "maxCombo": 8},
    "parameters": {
        "learning_rate": {"type": "float", "min": 0.001, "max": 0.3, "scalingType": "loguniform"},
        "epochs": {"type": "integer", "min": 5, "max": 50},
        # "hidden_size": {"type": "discrete", "values": [8, 16, 32]},
    },
}
optimizer = comet_ml.Optimizer(config)
for experiment in optimizer.get_experiments(project_name=..., auto_metric_logging=False):
    params = {k: experiment.get_parameter(k) for k in config["parameters"]}
    ...                                       # train, log the spec metric, experiment.end()
optimizer.id                                  # resume later with Optimizer(optimizer.id)
```

- `get_experiments(**kwargs)` forwards its arguments to the experiment constructor, so
  `ExperimentConfig` fields work there.
- Each trial is an ordinary experiment: tags, names and the MCP tools all apply. `sweep.py` tags trials
  `sweep` and names them with `config.experiment_name("<model>-sweep")`.
- Parallel trials: run `make sweep` on several machines with `Optimizer(<id>)`; the server hands out
  distinct parameter sets.
- `comet optimize` (CLI) wraps the same thing for scripts that read parameters from the environment.

## Offline mode

`COMET_START_ONLINE=false` makes `comet_ml.start()` return an `OfflineExperiment` that writes
`.cometml-runs/<key>.zip`; `comet upload <zip>` sends it later. Offline experiments cannot log or fetch
Artifacts, cannot register models, and the Optimizer needs the backend, so sweeps are online-only.
