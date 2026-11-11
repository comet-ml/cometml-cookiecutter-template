"""Example experiment: {{ cookiecutter.framework }} classifier on iris with the full Comet lifecycle.

Shape (the same for every framework so the sweep, tests and skills can rely on it):
    load_data(data_dir) -> Data                      # reads the CSVs written by `make data`
    train(experiment, params, data) -> (model, metrics)
    main(argv)                                        # start experiment, train, log model, register

`make train` logs per-epoch metrics, a confusion matrix and the model, then registers a new
version only when thresholds.yaml passes (or `--register` is given).
"""
from __future__ import annotations

import argparse
import subprocess
from typing import NamedTuple

import comet_ml
import numpy as np
import pandas as pd

from {{ cookiecutter.module_name }} import config, dataset

MODEL_NAME = "iris-classifier"
LABELS = ["setosa", "versicolor", "virginica"]
{%- if cookiecutter.framework == "sklearn" %}
DEFAULT_PARAMS = {"epochs": 20, "alpha": 0.001, "learning_rate": 0.1, "random_state": 42}
{%- elif cookiecutter.framework == "xgboost" %}
DEFAULT_PARAMS = {"epochs": 10, "trees_per_epoch": 5, "max_depth": 3, "learning_rate": 0.3}
{%- elif cookiecutter.framework == "pytorch" %}
DEFAULT_PARAMS = {"epochs": 50, "hidden_size": 16, "learning_rate": 0.05, "seed": 42}
{%- elif cookiecutter.framework == "tensorflow" %}
DEFAULT_PARAMS = {"epochs": 50, "hidden_size": 16, "learning_rate": 0.05, "seed": 42}
{%- else %}
DEFAULT_PARAMS = {"epochs": 200, "learning_rate": 0.1, "seed": 42}
{%- endif %}


class Data(NamedTuple):
    X_train: np.ndarray
    y_train: np.ndarray
    X_val: np.ndarray
    y_val: np.ndarray


def load_data(data_dir=config.DATA_DIR) -> Data:
    """Read the train/test CSVs written by `make data` (features scaled to zero mean, unit var)."""
    train_df = pd.read_csv(data_dir / dataset.TRAIN_CSV)
    test_df = pd.read_csv(data_dir / dataset.TEST_CSV)
    X_train = train_df.drop(columns=["target"]).to_numpy(dtype=np.float32)
    X_val = test_df.drop(columns=["target"]).to_numpy(dtype=np.float32)
    mean, std = X_train.mean(axis=0), X_train.std(axis=0) + 1e-8
    return Data(
        (X_train - mean) / std,
        train_df["target"].to_numpy(dtype=np.int64),
        (X_val - mean) / std,
        test_df["target"].to_numpy(dtype=np.int64),
    )


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float((y_true == y_pred).mean())


{%- if cookiecutter.framework == "sklearn" %}


def train(experiment, params: dict, data: Data):
    """SGDClassifier trained with one `partial_fit` pass per epoch."""
    from sklearn.linear_model import SGDClassifier

    experiment.log_parameters(params)
    model = SGDClassifier(
        loss="log_loss",
        alpha=params["alpha"],
        learning_rate="constant",
        eta0=params["learning_rate"],
        random_state=params["random_state"],
    )
    classes = np.unique(data.y_train)
    for epoch in range(params["epochs"]):
        model.partial_fit(data.X_train, data.y_train, classes=classes)
        metrics = {
            "train_accuracy": accuracy(data.y_train, model.predict(data.X_train)),
            "val_accuracy": accuracy(data.y_val, model.predict(data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    y_pred = model.predict(data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def log_model(experiment, model) -> None:
    from comet_ml.integration.sklearn import log_model as sklearn_log_model

    sklearn_log_model(experiment, MODEL_NAME, model)
{%- elif cookiecutter.framework == "xgboost" %}


def train(experiment, params: dict, data: Data):
    """XGBClassifier grown `trees_per_epoch` trees at a time (continued boosting per epoch)."""
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
        booster.fit(data.X_train, data.y_train, xgb_model=model.get_booster() if model else None)
        model = booster
        metrics = {
            "train_accuracy": accuracy(data.y_train, model.predict(data.X_train)),
            "val_accuracy": accuracy(data.y_val, model.predict(data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    y_pred = model.predict(data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def log_model(experiment, model) -> None:
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.MODELS_DIR / f"{MODEL_NAME}.json"
    model.save_model(str(path))
    experiment.log_model(MODEL_NAME, str(path))
{%- elif cookiecutter.framework == "pytorch" %}


def build_model(hidden_size: int):
    from torch import nn

    return nn.Sequential(nn.Linear(4, hidden_size), nn.ReLU(), nn.Linear(hidden_size, len(LABELS)))


def train(experiment, params: dict, data: Data):
    """Two-layer MLP, full-batch Adam, one optimizer step per epoch."""
    import torch
    from torch import nn

    experiment.log_parameters(params)
    torch.manual_seed(params["seed"])
    model = build_model(params["hidden_size"])
    optimizer = torch.optim.Adam(model.parameters(), lr=params["learning_rate"])
    loss_fn = nn.CrossEntropyLoss()
    X_train, y_train = torch.from_numpy(data.X_train), torch.from_numpy(data.y_train)
    X_val, y_val = torch.from_numpy(data.X_val), torch.from_numpy(data.y_val)
    for epoch in range(params["epochs"]):
        model.train()
        optimizer.zero_grad()
        loss = loss_fn(model(X_train), y_train)
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            metrics = {
                "train_loss": loss.item(),
                "train_accuracy": accuracy(y_train.numpy(), model(X_train).argmax(1).numpy()),
                "val_accuracy": accuracy(y_val.numpy(), model(X_val).argmax(1).numpy()),
            }
        experiment.log_metrics(metrics, epoch=epoch)
    with torch.no_grad():
        y_pred = model(X_val).argmax(1).numpy()
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def log_model(experiment, model) -> None:
    from comet_ml.integration.pytorch import log_model as pytorch_log_model

    pytorch_log_model(experiment, model, MODEL_NAME)
{%- elif cookiecutter.framework == "tensorflow" %}


def train(experiment, params: dict, data: Data):
    """Two-layer Keras MLP; one `fit(epochs=1)` per loop so metrics are logged uniformly."""
    import tensorflow as tf

    experiment.log_parameters(params)
    tf.random.set_seed(params["seed"])
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(4,)),
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
        train_pred = model.predict(data.X_train, verbose=0).argmax(1)
        val_pred = model.predict(data.X_val, verbose=0).argmax(1)
        metrics = {
            "train_loss": float(history.history["loss"][0]),
            "train_accuracy": accuracy(data.y_train, train_pred),
            "val_accuracy": accuracy(data.y_val, val_pred),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    y_pred = model.predict(data.X_val, verbose=0).argmax(1)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return model, metrics


def log_model(experiment, model) -> None:
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.MODELS_DIR / f"{MODEL_NAME}.keras"
    model.save(str(path))
    experiment.log_model(MODEL_NAME, str(path))
{%- else %}


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def predict(weights: dict, X: np.ndarray) -> np.ndarray:
    return (X @ weights["W"] + weights["b"]).argmax(axis=1)


def train(experiment, params: dict, data: Data):
    """Multinomial logistic regression in numpy, one full-batch gradient step per epoch."""
    experiment.log_parameters(params)
    rng = np.random.default_rng(params["seed"])
    n_features, n_classes = data.X_train.shape[1], len(LABELS)
    weights = {"W": rng.normal(scale=0.01, size=(n_features, n_classes)), "b": np.zeros(n_classes)}
    onehot = np.eye(n_classes)[data.y_train]
    for epoch in range(params["epochs"]):
        probs = softmax(data.X_train @ weights["W"] + weights["b"])
        grad = probs - onehot
        weights["W"] -= params["learning_rate"] * data.X_train.T @ grad / len(onehot)
        weights["b"] -= params["learning_rate"] * grad.mean(axis=0)
        metrics = {
            "train_loss": float(
                -np.log(probs[np.arange(len(onehot)), data.y_train] + 1e-12).mean()
            ),
            "train_accuracy": accuracy(data.y_train, predict(weights, data.X_train)),
            "val_accuracy": accuracy(data.y_val, predict(weights, data.X_val)),
        }
        experiment.log_metrics(metrics, epoch=epoch)
    y_pred = predict(weights, data.X_val)
    experiment.log_confusion_matrix(y_true=data.y_val, y_predicted=y_pred, labels=LABELS)
    return weights, metrics


def log_model(experiment, model) -> None:
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.MODELS_DIR / f"{MODEL_NAME}.npz"
    np.savez(path, **model)
    experiment.log_model(MODEL_NAME, str(path))
{%- endif %}


def bump_patch(version: str | None) -> str:
    """`1.2.3` -> `1.2.4`; the first version of a model is `1.0.0`."""
    if not version:
        return "1.0.0"
    major, minor, patch = version.split(".")
    return f"{major}.{minor}.{int(patch) + 1}"


def next_version(workspace: str | None) -> str:
    """Next patch after the latest registered version (`register_model` rejects a duplicate)."""
    api = comet_ml.API()
    try:
        latest = api.get_model(workspace or api.get_default_workspace(), MODEL_NAME).find_versions()
    except Exception:  # model not registered yet
        latest = []
    return bump_patch(latest[0] if latest else None)


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
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
    try:
        offline = isinstance(experiment, comet_ml.OfflineExperiment)
        dataset_version = dataset.record_lineage(experiment)
        model, metrics = train(experiment, params, data)
        log_model(experiment, model)

        gate = "val_accuracy"
        if offline:
            print("offline run: model logged to the archive, not registered")
        elif args.register or config.threshold_passes(gate, metrics[gate]):
            version = args.version or next_version(config.COMET_WORKSPACE)
            experiment.register_model(
                MODEL_NAME,
                version=version,
                status="Development",
                tags=["example"],
                metadata={
                    "dataset_version": dataset_version,
                    gate: round(metrics[gate], 4),
                    "git_sha": git_sha(),
                },
            )
            print(f"registered {MODEL_NAME} {version} ({gate}={metrics[gate]:.3f})")
        else:
            print(f"not registered: {gate}={metrics[gate]:.3f} fails {config.thresholds()[gate]}")
    finally:
        experiment.end()


if __name__ == "__main__":
    main()
