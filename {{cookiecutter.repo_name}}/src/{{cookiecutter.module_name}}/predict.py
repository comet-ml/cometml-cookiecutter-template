"""Load a registered model version (Production by default) and predict on the test split.

The consumer side of the registry, and what the deploy workflow runs: resolve the version by
status (or verify an explicit one), `Model.download`, `load_from_dir`, `train.predict`.
Models are saved with their feature scaling, so they run on raw features.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import comet_ml
{%- if cookiecutter.framework == "sklearn" %}
import joblib
{%- elif cookiecutter.framework == "none" %}
import numpy as np
{%- elif cookiecutter.framework == "tensorflow" %}
import tensorflow as tf
{%- elif cookiecutter.framework == "pytorch" %}
import torch
{%- elif cookiecutter.framework == "xgboost" %}
import xgboost as xgb
{%- endif %}

from {{ cookiecutter.module_name }} import config, registry, train

predict = train.predict


def resolve_version(model, status: str, version: str | None) -> str:
    """The newest version with `status`, or `version` after checking it really has that status."""
    if version:
        current = model.status(version)
        if current != status:
            raise SystemExit(f"{train.MODEL_NAME} {version} has status {current!r}, not {status!r}")
        return version
    versions = model.find_versions(status=status)
    if not versions:
        raise SystemExit(f"no {train.MODEL_NAME} version has status {status!r}; promote one first")
    return versions[0]


def load_from_dir(model_dir: Path):
    """Inverse of train.save_model; a registry download has the same single-file layout."""
    path = Path(model_dir) / train.MODEL_FILE
{%- if cookiecutter.framework == "sklearn" %}
    return joblib.load(path)
{%- elif cookiecutter.framework == "xgboost" %}
    model = xgb.XGBClassifier()
    model.load_model(str(path))
    return model
{%- elif cookiecutter.framework == "pytorch" %}
    state = torch.load(path, map_location="cpu")
    model = train.build_model(hidden_size=state["1.weight"].shape[0])
    model.load_state_dict(state)
    return model.eval()
{%- elif cookiecutter.framework == "tensorflow" %}
    return tf.keras.models.load_model(str(path))
{%- else %}
    with np.load(path) as weights:
        return {key: weights[key] for key in weights.files}
{%- endif %}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--status", default="Production", help="registry status to deploy from")
    parser.add_argument("--version", help="explicit registry version; must carry --status")
    parser.add_argument("--rows", type=int, default=5)
    args = parser.parse_args(argv)

    api = comet_ml.API()
    model = registry.model_or_none(api, registry.workspace(api), train.MODEL_NAME)
    if model is None:
        raise SystemExit(f"{train.MODEL_NAME} is not registered yet; run make train first")
    version = resolve_version(model, args.status, args.version)
    target = config.MODELS_DIR / "registry" / version
    model.download(version, output_folder=str(target))

    data = train.load_data()
    y_pred = predict(load_from_dir(target), data.X_val[: args.rows])
    print(f"{train.MODEL_NAME} {version} ({args.status})")
    for truth, pred in zip(data.y_val[: args.rows], y_pred, strict=True):
        print(f"  expected={train.LABELS[truth]:<11} predicted={train.LABELS[pred]}")


if __name__ == "__main__":
    main()
