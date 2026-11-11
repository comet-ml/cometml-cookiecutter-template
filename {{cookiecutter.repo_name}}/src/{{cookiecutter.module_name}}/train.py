"""Example experiment: {{ cookiecutter.framework }} classifier on iris with the full Comet lifecycle.

Shape (the same for every framework so the sweep, tests and skills can rely on it):
    load_data(data_dir) -> Data                      # raw features from the CSVs of `make data`
    train(experiment, params, data) -> (model, metrics)
    save_model(model, dir) -> Path                   # everything predict.load_from_dir needs
    main(argv)                                        # start experiment, train, log model, register

Feature scaling is part of the saved model, so a registry version is deployable on raw features.
`make train` logs per-epoch metrics, a confusion matrix and the model, then registers a new version
only when every metric in thresholds.yaml passes (or `--register` is given), and ends with one
`summary:` line that /run-training reads.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import comet_ml
import numpy as np
import pandas as pd

from {{ cookiecutter.module_name }} import config, dataset

MODEL_NAME = "iris-classifier"
LABELS = ["setosa", "versicolor", "virginica"]
{%- if cookiecutter.framework == "sklearn" %}
MODEL_FILE = "model.pkl"
DEFAULT_PARAMS = {"epochs": 20, "alpha": 0.001, "learning_rate": 0.1, "random_state": 42}
{%- elif cookiecutter.framework == "xgboost" %}
MODEL_FILE = "model.json"
DEFAULT_PARAMS = {"epochs": 10, "trees_per_epoch": 5, "max_depth": 3, "learning_rate": 0.3}
{%- elif cookiecutter.framework == "pytorch" %}
MODEL_FILE = "model.pt"
DEFAULT_PARAMS = {"epochs": 50, "hidden_size": 16, "learning_rate": 0.05, "seed": 42}
{%- elif cookiecutter.framework == "tensorflow" %}
MODEL_FILE = "model.keras"
DEFAULT_PARAMS = {"epochs": 50, "hidden_size": 16, "learning_rate": 0.05, "seed": 42}
{%- else %}
MODEL_FILE = "model.npz"
DEFAULT_PARAMS = {"epochs": 200, "learning_rate": 0.1, "seed": 42}
{%- endif %}


class Data(NamedTuple):
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray


def load_data(data_dir=config.DATA_DIR) -> Data:
    """Read the train/test CSVs written by `make data`. Raw features; models scale internally."""
    train_df = pd.read_csv(data_dir / dataset.TRAIN_CSV)
    test_df = pd.read_csv(data_dir / dataset.TEST_CSV)
    return Data(
        train_df.drop(columns=["target"]).to_numpy(dtype=np.float32),
        train_df["target"].to_numpy(dtype=np.int64),
        test_df.drop(columns=["target"]).to_numpy(dtype=np.float32),
        test_df["target"].to_numpy(dtype=np.int64),
    )


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float((y_true == y_pred).mean())


def _finish(experiment, model, data: Data, metrics: dict, predict_fn) -> tuple:
    y_pred = predict_fn(model, data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


{%- if cookiecutter.framework == "sklearn" %}


def train(experiment, params: dict, data: Data):
    """StandardScaler + SGDClassifier, one `partial_fit` pass per epoch; saved as one Pipeline."""
    from sklearn.linear_model import SGDClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    experiment.log_parameters(params)
    scaler = StandardScaler().fit(data.X_train)
    clf = SGDClassifier(
        loss="log_loss",
        alpha=params["alpha"],
        learning_rate="constant",
        eta0=params["learning_rate"],
        random_state=params["random_state"],
    )
    model = Pipeline([("scale", scaler), ("clf", clf)])
    X_train, X_val = scaler.transform(data.X_train), scaler.transform(data.X_val)
    classes = np.unique(data.y_train)
    for epoch in range(params["epochs"]):
        clf.partial_fit(X_train, data.y_train, classes=classes)
        metrics = {
            "train_accuracy": accuracy(data.y_train, clf.predict(X_train)),
            "val_accuracy": accuracy(data.y_val, clf.predict(X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    return _finish(experiment, model, data, metrics, lambda m, X: m.predict(X))


def save_model(model, model_dir: Path) -> Path:
    import joblib

    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / MODEL_FILE
    joblib.dump(model, path)
    return path
{%- elif cookiecutter.framework == "xgboost" %}


def train(experiment, params: dict, data: Data):
    """XGBClassifier grown `trees_per_epoch` trees per epoch via continued boosting; no scaling."""
    import xgboost as xgb

    experiment.log_parameters(params)
    model = None
    for epoch in range(params["epochs"]):
        booster = xgb.XGBClassifier(
            n_estimators=params["trees_per_epoch"],
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            objective="multi:softprob",
            num_class=len(LABELS),
        )
        previous = model.get_booster() if model is not None else None
        booster.fit(data.X_train, data.y_train, xgb_model=previous)
        model = booster
        metrics = {
            "train_accuracy": accuracy(data.y_train, model.predict(data.X_train)),
            "val_accuracy": accuracy(data.y_val, model.predict(data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    return _finish(experiment, model, data, metrics, lambda m, X: m.predict(X))


def save_model(model, model_dir: Path) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / MODEL_FILE
    model.save_model(str(path))
    return path
{%- elif cookiecutter.framework == "pytorch" %}


def standardize_cls():
    """Scaling as a module with buffers, so the stats travel inside the state_dict."""
    import torch
    from torch import nn

    class Standardize(nn.Module):
        def __init__(self, n_features: int):
            super().__init__()
            self.register_buffer("mean", torch.zeros(n_features))
            self.register_buffer("std", torch.ones(n_features))

        def fit(self, X: torch.Tensor) -> None:
            self.mean.copy_(X.mean(0))
            self.std.copy_(X.std(0) + 1e-8)

        def forward(self, X: torch.Tensor) -> torch.Tensor:
            return (X - self.mean) / self.std

    return Standardize


def build_model(hidden_size: int):
    """Standardize -> Linear -> ReLU -> Linear."""
    from torch import nn

    standardize = standardize_cls()
    return nn.Sequential(
        standardize(4), nn.Linear(4, hidden_size), nn.ReLU(), nn.Linear(hidden_size, len(LABELS))
    )


def _predict(model, X: np.ndarray) -> np.ndarray:
    import torch

    model.eval()
    with torch.no_grad():
        return model(torch.from_numpy(np.ascontiguousarray(X))).argmax(1).numpy()


def train(experiment, params: dict, data: Data):
    """Two-layer MLP with a standardization front layer, full-batch Adam, one step per epoch."""
    import torch
    from torch import nn

    experiment.log_parameters(params)
    torch.manual_seed(params["seed"])
    model = build_model(params["hidden_size"])
    X_train, y_train = torch.from_numpy(data.X_train.copy()), torch.from_numpy(data.y_train)
    model[0].fit(X_train)
    optimizer = torch.optim.Adam(model.parameters(), lr=params["learning_rate"])
    loss_fn = nn.CrossEntropyLoss()
    for epoch in range(params["epochs"]):
        model.train()
        optimizer.zero_grad()
        loss = loss_fn(model(X_train), y_train)
        loss.backward()
        optimizer.step()
        metrics = {
            "train_loss": loss.item(),
            "train_accuracy": accuracy(data.y_train, _predict(model, data.X_train)),
            "val_accuracy": accuracy(data.y_val, _predict(model, data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    return _finish(experiment, model, data, metrics, _predict)


def save_model(model, model_dir: Path) -> Path:
    """state_dict only (weights + scaling buffers); predict rebuilds the module from its shapes."""
    import torch

    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / MODEL_FILE
    torch.save(model.state_dict(), path)
    return path
{%- elif cookiecutter.framework == "tensorflow" %}


def _predict(model, X: np.ndarray) -> np.ndarray:
    return model.predict(X, verbose=0).argmax(1)


def train(experiment, params: dict, data: Data):
    """Normalization layer + two Dense layers; one `fit(epochs=1)` per loop for uniform logging."""
    import tensorflow as tf

    experiment.log_parameters(params)
    tf.random.set_seed(params["seed"])
    norm = tf.keras.layers.Normalization(axis=-1)
    norm.adapt(data.X_train)
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(4,)),
            norm,
            tf.keras.layers.Dense(params["hidden_size"], activation="relu"),
            tf.keras.layers.Dense(len(LABELS), activation="softmax"),
        ]
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(params["learning_rate"]),
        loss="sparse_categorical_crossentropy",
    )
    for epoch in range(params["epochs"]):
        history = model.fit(data.X_train, data.y_train, epochs=1, verbose=0)
        metrics = {
            "train_loss": float(history.history["loss"][0]),
            "train_accuracy": accuracy(data.y_train, _predict(model, data.X_train)),
            "val_accuracy": accuracy(data.y_val, _predict(model, data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    return _finish(experiment, model, data, metrics, _predict)


def save_model(model, model_dir: Path) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / MODEL_FILE
    model.save(str(path))
    return path
{%- else %}


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def predict(weights: dict, X: np.ndarray) -> np.ndarray:
    Xs = (X - weights["mean"]) / weights["std"]
    return (Xs @ weights["W"] + weights["b"]).argmax(axis=1)


def train(experiment, params: dict, data: Data):
    """Multinomial logistic regression in numpy; the weights dict carries the scaling stats."""
    experiment.log_parameters(params)
    rng = np.random.default_rng(params["seed"])
    n_features, n_classes = data.X_train.shape[1], len(LABELS)
    weights = {
        "mean": data.X_train.mean(axis=0),
        "std": data.X_train.std(axis=0) + 1e-8,
        "W": rng.normal(scale=0.01, size=(n_features, n_classes)),
        "b": np.zeros(n_classes),
    }
    Xs = (data.X_train - weights["mean"]) / weights["std"]
    onehot = np.eye(n_classes)[data.y_train]
    for epoch in range(params["epochs"]):
        probs = softmax(Xs @ weights["W"] + weights["b"])
        grad = probs - onehot
        weights["W"] -= params["learning_rate"] * Xs.T @ grad / len(onehot)
        weights["b"] -= params["learning_rate"] * grad.mean(axis=0)
        metrics = {
            "train_loss": float(
                -np.log(probs[np.arange(len(onehot)), data.y_train] + 1e-12).mean()
            ),
            "train_accuracy": accuracy(data.y_train, predict(weights, data.X_train)),
            "val_accuracy": accuracy(data.y_val, predict(weights, data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    return _finish(experiment, weights, data, metrics, predict)


def save_model(model, model_dir: Path) -> Path:
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / MODEL_FILE
    np.savez(path, **model)
    return path
{%- endif %}


_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def bump_patch(version: str | None) -> str:
    """`1.2.3` -> `1.2.4` (prerelease/build suffixes dropped); the first version is `1.0.0`."""
    match = _SEMVER_RE.match(version or "")
    if not match:
        return "1.0.0"
    major, minor, patch = match.groups()
    return f"{major}.{minor}.{int(patch) + 1}"


def next_version(api: comet_ml.API, workspace: str) -> str:
    """Next patch after the latest registered version; `1.0.0` when the model is not registered."""
    if MODEL_NAME not in api.get_registry_model_names(workspace):
        return "1.0.0"
    versions = api.get_model(workspace, MODEL_NAME).find_versions()
    return bump_patch(versions[0] if versions else None)


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--register", action="store_true", help="register even if thresholds fail")
    parser.add_argument("--version", help="registry version to create (default: bump latest patch)")
    for key, value in DEFAULT_PARAMS.items():
        parser.add_argument(f"--{key.replace('_', '-')}", type=type(value), default=value)
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    params = {key: getattr(args, key) for key in DEFAULT_PARAMS}
    data = load_data()

    experiment = comet_ml.start(
        project_name=config.COMET_PROJECT_NAME,
        experiment_config=comet_ml.ExperimentConfig(
            name=config.experiment_name(MODEL_NAME),
            tags=["example", "framework={{ cookiecutter.framework }}"],
            auto_metric_logging=False,  # the loop logs train/val metrics itself
        ),
    )
    name = experiment.get_name()
    offline = isinstance(experiment, comet_ml.OfflineExperiment)
    version = workspace = None
    try:
        dataset_version = dataset.record_lineage(experiment)
        model, metrics = train(experiment, params, data)
        experiment.log_model(MODEL_NAME, str(save_model(model, config.MODELS_DIR / MODEL_NAME)))

        failing = config.gate_passes(metrics)
        if offline:
            print("offline run: model logged to the archive, not registered")
        elif args.register or not failing:
            api = comet_ml.API()
            workspace = config.COMET_WORKSPACE or api.get_default_workspace()
            version = args.version or next_version(api, workspace)
            experiment.register_model(
                MODEL_NAME,
                version=version,
                status="Development",
                tags=["example"],
                metadata={
                    "dataset_version": dataset_version,
                    "git_sha": git_sha(),
                    **{k: round(metrics[k], 4) for k in config.thresholds() if k in metrics},
                },
            )
        else:
            print(f"not registered: {', '.join(failing)} failed thresholds.yaml")
    finally:
        experiment.end()  # registration is sent here; a rejected one is only logged by the SDK

    registered = "none"
    if version:
        model_api = comet_ml.API().get_model(workspace, MODEL_NAME)
        known = model_api.find_versions(version_prefix=version)
        registered = version if version in known else "FAILED"
    print(
        f"summary: name={name} dataset=iris-dataset:{dataset_version} "
        + " ".join(f"{k}={v:.4f}" for k, v in sorted(metrics.items()))
        + f" registered={registered}"
    )
    if registered == "FAILED":
        sys.exit(f"registration of {MODEL_NAME} {version} was rejected; see the COMET ERROR above")


if __name__ == "__main__":
    main()
