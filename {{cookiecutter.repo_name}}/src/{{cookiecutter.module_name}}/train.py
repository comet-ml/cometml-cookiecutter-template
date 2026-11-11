"""Example experiment: {{ cookiecutter.framework }} classifier on iris with the full Comet lifecycle.

Shape (the same for every framework so the sweep, tests, predict.py and the skills rely on it):
    load_data(data_dir) -> Data                      # raw features; builds the CSVs if missing
    train(experiment, params, data) -> (model, metrics)
    predict(model, X) -> labels
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
import sys
from pathlib import Path
from typing import NamedTuple

import comet_ml
{%- if cookiecutter.framework == "sklearn" %}
import joblib
{%- endif %}
import numpy as np
import pandas as pd
{%- if cookiecutter.framework == "sklearn" %}
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
{%- elif cookiecutter.framework == "tensorflow" %}
import tensorflow as tf
{%- elif cookiecutter.framework == "pytorch" %}
import torch
from torch import nn
{%- elif cookiecutter.framework == "xgboost" %}
import xgboost as xgb
{%- endif %}

from {{ cookiecutter.module_name }} import config, dataset, registry

FRAMEWORK = "{{ cookiecutter.framework }}"
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


def load_data(data_dir: Path = config.DATA_DIR) -> Data:
    """Read the train/test CSVs, building them first when absent. Raw features."""
    if not all((data_dir / f).exists() for f in (dataset.TRAIN_CSV, dataset.TEST_CSV)):
        dataset.build(data_dir)
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


def save_model(model, model_dir: Path) -> Path:
    """Write the model (with its preprocessing) to `model_dir / MODEL_FILE` and return the path."""
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / MODEL_FILE
    _dump(model, path)
    return path


{%- if cookiecutter.framework == "sklearn" %}


def predict(model, X: np.ndarray) -> np.ndarray:
    return model.predict(X)


def train(experiment, params: dict, data: Data):
    """StandardScaler + SGDClassifier, one `partial_fit` pass per epoch; saved as one Pipeline."""
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
    y_pred = predict(model, data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def _dump(model, path: Path) -> None:
    joblib.dump(model, path)
{%- elif cookiecutter.framework == "xgboost" %}


def predict(model, X: np.ndarray) -> np.ndarray:
    return model.predict(X)


def train(experiment, params: dict, data: Data):
    """XGBClassifier grown `trees_per_epoch` trees per epoch via continued boosting; no scaling."""
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
            "train_accuracy": accuracy(data.y_train, predict(model, data.X_train)),
            "val_accuracy": accuracy(data.y_val, predict(model, data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    y_pred = predict(model, data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def _dump(model, path: Path) -> None:
    model.save_model(str(path))
{%- elif cookiecutter.framework == "pytorch" %}


class Standardize(nn.Module):
    """Scaling as a layer, so the stats travel inside the state_dict."""

    def __init__(self, n_features: int):
        super().__init__()
        self.register_buffer("mean", torch.zeros(n_features))
        self.register_buffer("std", torch.ones(n_features))

    def fit(self, X: torch.Tensor) -> None:
        self.mean.copy_(X.mean(0))
        self.std.copy_(X.std(0) + 1e-8)

    def forward(self, X: torch.Tensor) -> torch.Tensor:
        return (X - self.mean) / self.std


def build_model(hidden_size: int) -> nn.Sequential:
    return nn.Sequential(
        Standardize(4), nn.Linear(4, hidden_size), nn.ReLU(), nn.Linear(hidden_size, len(LABELS))
    )


def predict(model, X: np.ndarray) -> np.ndarray:
    model.eval()
    with torch.no_grad():
        return model(torch.from_numpy(np.ascontiguousarray(X))).argmax(1).numpy()


def train(experiment, params: dict, data: Data):
    """Two-layer MLP behind a Standardize layer, full-batch Adam, one step per epoch."""
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
            "train_accuracy": accuracy(data.y_train, predict(model, data.X_train)),
            "val_accuracy": accuracy(data.y_val, predict(model, data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    y_pred = predict(model, data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def _dump(model, path: Path) -> None:
    torch.save(model.state_dict(), path)  # weights + scaling buffers; predict rebuilds the module
{%- elif cookiecutter.framework == "tensorflow" %}


def predict(model, X: np.ndarray) -> np.ndarray:
    return model.predict(X, verbose=0).argmax(1)


def train(experiment, params: dict, data: Data):
    """Normalization layer + two Dense layers; one `fit(epochs=1)` per loop for uniform logging."""
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
            "train_accuracy": accuracy(data.y_train, predict(model, data.X_train)),
            "val_accuracy": accuracy(data.y_val, predict(model, data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    y_pred = predict(model, data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def _dump(model, path: Path) -> None:
    model.save(str(path))
{%- else %}


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def predict(model: dict, X: np.ndarray) -> np.ndarray:
    Xs = (X - model["mean"]) / model["std"]
    return (Xs @ model["W"] + model["b"]).argmax(axis=1)


def train(experiment, params: dict, data: Data):
    """Multinomial logistic regression in numpy; the weights dict carries the scaling stats."""
    experiment.log_parameters(params)
    rng = np.random.default_rng(params["seed"])
    n_features, n_classes = data.X_train.shape[1], len(LABELS)
    model = {
        "mean": data.X_train.mean(axis=0),
        "std": data.X_train.std(axis=0) + 1e-8,
        "W": rng.normal(scale=0.01, size=(n_features, n_classes)),
        "b": np.zeros(n_classes),
    }
    Xs = (data.X_train - model["mean"]) / model["std"]
    onehot = np.eye(n_classes)[data.y_train]
    for epoch in range(params["epochs"]):
        probs = softmax(Xs @ model["W"] + model["b"])
        grad = probs - onehot
        model["W"] -= params["learning_rate"] * Xs.T @ grad / len(onehot)
        model["b"] -= params["learning_rate"] * grad.mean(axis=0)
        metrics = {
            "train_loss": float(
                -np.log(probs[np.arange(len(onehot)), data.y_train] + 1e-12).mean()
            ),
            "train_accuracy": accuracy(data.y_train, predict(model, data.X_train)),
            "val_accuracy": accuracy(data.y_val, predict(model, data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    y_pred = predict(model, data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def _dump(model, path: Path) -> None:
    np.savez(path, **model)
{%- endif %}


_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def bump_patch(version: str | None) -> str:
    """`1.2.3` -> `1.2.4` (prerelease/build suffixes dropped); the first version is `1.0.0`."""
    match = _SEMVER_RE.match(version or "")
    if not match:
        return "1.0.0"
    major, minor, patch = match.groups()
    return f"{major}.{minor}.{int(patch) + 1}"


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
            tags=["example", f"framework={FRAMEWORK}"],
            auto_metric_logging=False,  # the loop logs train/val metrics itself
        ),
    )
    try:
        dataset_version = dataset.record_lineage(experiment)
        model, metrics = train(experiment, params, data)
        experiment.log_model(MODEL_NAME, str(save_model(model, config.MODELS_DIR / MODEL_NAME)))
    finally:
        experiment.end()

    failing = config.failing_thresholds(metrics)
    version = None
    if isinstance(experiment, comet_ml.OfflineExperiment):
        print("offline run: model logged to the archive, not registered")
    elif args.register or not failing:
        # The REST path registers synchronously and raises when the backend rejects the version.
        api = comet_ml.API()
        ws = registry.workspace(api)
        existing = registry.model_or_none(api, ws, MODEL_NAME)
        versions = existing.find_versions() if existing else []
        version = args.version or bump_patch(versions[0] if versions else None)
        rounded = {k: round(v, 4) for k, v in metrics.items()}
        api_experiment = api.get_experiment_by_key(experiment.get_key())
        if api_experiment is None:
            sys.exit(f"model logged, not registered: experiment {experiment.get_key()} not found")
        api_experiment.register_model(
            MODEL_NAME,
            version=version,
            status="Development",
            tags=["example"],
            metadata={"dataset_version": dataset_version, **rounded},
        )
    else:
        print(f"not registered: {', '.join(failing)} failed thresholds.yaml")

    print(
        f"summary: name={experiment.get_name()} dataset=iris-dataset:{dataset_version} "
        + " ".join(f"{k}={v:.4f}" for k, v in sorted(metrics.items()))
        + f" registered={version or 'none'}"
    )


if __name__ == "__main__":
    main()
