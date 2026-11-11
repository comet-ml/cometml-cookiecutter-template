"""Load the Production version of the registered model and predict on the test split.

This is the consumer side of the registry: the deploy workflow (.github/workflows/deploy-model.yml)
and a serving job both start from the same two calls, `find_versions(status=...)` and `download`.
"""
from __future__ import annotations

import argparse

import comet_ml
import numpy as np

from {{ cookiecutter.module_name }} import config, train


def resolve_version(api: comet_ml.API, workspace: str, status: str, version: str | None) -> str:
    if version:
        return version
    versions = api.get_model(workspace, train.MODEL_NAME).find_versions(status=status)
    if not versions:
        raise SystemExit(f"no {train.MODEL_NAME} version has status {status!r}; promote one first")
    return versions[0]


def load(workspace: str, version: str):
    """Fetch one registry version and return something `train`-compatible `predict` can use."""
{%- if cookiecutter.framework == "sklearn" %}
    from comet_ml.integration.sklearn import load_model

    return load_model(f"registry://{workspace}/{train.MODEL_NAME}:{version}")
{%- elif cookiecutter.framework == "pytorch" %}
    from comet_ml.integration.pytorch import load_model

    return load_model(f"registry://{workspace}/{train.MODEL_NAME}:{version}", map_location="cpu")
{%- else %}
    target = config.MODELS_DIR / "registry" / version
    model = comet_ml.API().get_model(workspace, train.MODEL_NAME)
    model.download(version, output_folder=str(target))
{%- if cookiecutter.framework == "xgboost" %}
    import xgboost as xgb

    model = xgb.XGBClassifier()
    model.load_model(str(next(target.rglob("*.json"))))
    return model
{%- elif cookiecutter.framework == "tensorflow" %}
    import tensorflow as tf

    return tf.keras.models.load_model(str(next(target.rglob("*.keras"))))
{%- else %}
    with np.load(next(target.rglob("*.npz"))) as weights:
        return {key: weights[key] for key in weights.files}
{%- endif %}
{%- endif %}


def predict(model, X: np.ndarray) -> np.ndarray:
{%- if cookiecutter.framework == "pytorch" %}
    import torch

    with torch.no_grad():
        return model(torch.from_numpy(X)).argmax(1).numpy()
{%- elif cookiecutter.framework == "tensorflow" %}
    return model.predict(X, verbose=0).argmax(1)
{%- elif cookiecutter.framework == "none" %}
    return train.predict(model, X)
{%- else %}
    return model.predict(X)
{%- endif %}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", default="Production", help="registry status to deploy from")
    parser.add_argument("--version", help="explicit registry version (overrides --status)")
    parser.add_argument("--rows", type=int, default=5)
    args = parser.parse_args(argv)

    api = comet_ml.API()
    workspace = config.COMET_WORKSPACE or api.get_default_workspace()
    version = resolve_version(api, workspace, args.status, args.version)
    model = load(workspace, version)

    data = train.load_data()
    y_pred = predict(model, data.X_val[: args.rows])
    print(f"{train.MODEL_NAME} {version} ({args.status})")
    for truth, pred in zip(data.y_val[: args.rows], y_pred, strict=True):
        print(f"  expected={train.LABELS[truth]:<11} predicted={train.LABELS[pred]}")


if __name__ == "__main__":
    main()
