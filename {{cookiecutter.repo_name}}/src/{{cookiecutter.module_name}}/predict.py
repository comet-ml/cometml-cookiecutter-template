"""Load a registered model version (Production by default) and predict on the test split.

The consumer side of the registry: the deploy workflow (.github/workflows/deploy-model.yml) and a
serving job start from the same calls, `find_versions(status=...)`, `download` and `load_from_dir`.
Models are saved with their feature scaling, so they run on raw features.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import comet_ml
import numpy as np

from {{ cookiecutter.module_name }} import config, train


def resolve_version(api: comet_ml.API, workspace: str, status: str, version: str | None) -> str:
    if version:
        return version
    if train.MODEL_NAME not in api.get_registry_model_names(workspace):
        raise SystemExit(f"{train.MODEL_NAME} is not registered in {workspace}; run make train")
    versions = api.get_model(workspace, train.MODEL_NAME).find_versions(status=status)
    if not versions:
        raise SystemExit(f"no {train.MODEL_NAME} version has status {status!r}; promote one first")
    return versions[0]


def download(api: comet_ml.API, workspace: str, version: str) -> Path:
    target = config.MODELS_DIR / "registry" / version
    api.get_model(workspace, train.MODEL_NAME).download(version, output_folder=str(target))
    return target


def load_from_dir(model_dir: Path):
    """Inverse of train.save_model; also works on a registry download (searches subfolders)."""
    path = next(Path(model_dir).rglob(train.MODEL_FILE))
{%- if cookiecutter.framework == "sklearn" %}
    import joblib

    return joblib.load(path)
{%- elif cookiecutter.framework == "xgboost" %}
    import xgboost as xgb

    model = xgb.XGBClassifier()
    model.load_model(str(path))
    return model
{%- elif cookiecutter.framework == "pytorch" %}
    import torch

    state = torch.load(path, map_location="cpu")
    model = train.build_model(hidden_size=state["1.weight"].shape[0])
    model.load_state_dict(state)
    return model.eval()
{%- elif cookiecutter.framework == "tensorflow" %}
    import tensorflow as tf

    return tf.keras.models.load_model(str(path))
{%- else %}
    with np.load(path) as weights:
        return {key: weights[key] for key in weights.files}
{%- endif %}


def predict(model, X: np.ndarray) -> np.ndarray:
{%- if cookiecutter.framework == "pytorch" %}
    return train._predict(model, X)
{%- elif cookiecutter.framework == "tensorflow" %}
    return train._predict(model, X)
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
    model = load_from_dir(download(api, workspace, version))

    data = train.load_data()
    y_pred = predict(model, data.X_val[: args.rows])
    print(f"{train.MODEL_NAME} {version} ({args.status})")
    for truth, pred in zip(data.y_val[: args.rows], y_pred, strict=True):
        print(f"  expected={train.LABELS[truth]:<11} predicted={train.LABELS[pred]}")


if __name__ == "__main__":
    main()
