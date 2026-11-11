"""Hyperparameter sweep with comet_ml.Optimizer over train.train().

Every trial is a normal Comet experiment in the same project, tagged `sweep`, so the project
view, the parallel coordinates chart and /compare-runs all work on the results. The sweep
never registers models: pick the best trial, then `make train ARGS="--learning-rate ..."`.

Docs: https://www.comet.com/docs/v2/guides/optimizer/quickstart/
"""
from __future__ import annotations

import argparse

import comet_ml

from {{ cookiecutter.module_name }} import config, dataset, train

OPTIMIZER_CONFIG = {
    "algorithm": "bayes",
    "spec": {"metric": "val_accuracy", "objective": "maximize", "maxCombo": 8},
    "parameters": {
        "learning_rate": {"type": "float", "min": 0.001, "max": 0.3, "scalingType": "loguniform"},
        "epochs": {"type": "integer", "min": 5, "max": train.DEFAULT_PARAMS["epochs"]},
    },
}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--max-combo", type=int, default=OPTIMIZER_CONFIG["spec"]["maxCombo"])
    args = parser.parse_args(argv)

    spec = {**OPTIMIZER_CONFIG["spec"], "maxCombo": args.max_combo}
    optimizer_config = {**OPTIMIZER_CONFIG, "spec": spec}
    optimizer = comet_ml.Optimizer(optimizer_config)
    data = train.load_data()
    best: tuple[float, str] | None = None

    for experiment in optimizer.get_experiments(
        project_name=config.COMET_PROJECT_NAME, auto_metric_logging=False
    ):
        experiment.set_name(config.experiment_name(f"{train.MODEL_NAME}-sweep"))
        experiment.add_tags(["sweep", f"sweep={optimizer.id}", "framework={{ cookiecutter.framework }}"])
        tuned = {k: experiment.get_parameter(k) for k in OPTIMIZER_CONFIG["parameters"]}
        params = {**train.DEFAULT_PARAMS, **tuned}
        try:
            dataset.record_lineage(experiment)
            _, metrics = train.train(experiment, params, data)
        finally:
            experiment.end()
        if best is None or metrics["val_accuracy"] > best[0]:
            best = (metrics["val_accuracy"], experiment.get_key())

    if best:
        print(f"best val_accuracy={best[0]:.3f} experiment={best[1]}")
        print(f"sweep id: {optimizer.id}")


if __name__ == "__main__":
    main()
