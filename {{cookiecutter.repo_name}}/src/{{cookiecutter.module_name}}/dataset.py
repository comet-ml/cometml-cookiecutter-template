"""Dataset build + Comet Artifact logging.

`make data` writes `data/processed/iris-{train,test}.csv` and, when online, logs them once as
the versioned Artifact `iris-dataset`. Training reads the CSVs and only records which Artifact
version it used, so the dataset is uploaded once per change rather than on every run.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import comet_ml
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

from {{ cookiecutter.module_name }} import config

DATASET_NAME = "iris-dataset"
TRAIN_CSV = "iris-train.csv"
TEST_CSV = "iris-test.csv"


def build(data_dir: Path = config.DATA_DIR) -> tuple[Path, Path]:
    """Write the train/test CSVs (last column `target`) and return their paths."""
    X, y = load_iris(return_X_y=True, as_frame=True)
    df = pd.concat([X, y.rename("target")], axis=1)
    train_df, test_df = train_test_split(df, test_size=0.2, random_state=42, stratify=df["target"])
    data_dir.mkdir(parents=True, exist_ok=True)
    train_path, test_path = data_dir / TRAIN_CSV, data_dir / TEST_CSV
    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)
    return train_path, test_path


def log_artifact(experiment: comet_ml.CometExperiment, paths: tuple[Path, Path]) -> None:
    """Log the CSVs as a new version of the dataset Artifact."""
    artifact = comet_ml.Artifact(name=DATASET_NAME, artifact_type="dataset")
    for path in paths:
        artifact.add(str(path))
    experiment.log_artifact(artifact)


def record_lineage(experiment: comet_ml.CometExperiment) -> str:
    """Attach the latest dataset Artifact to a training experiment; its version or "local"."""
    if isinstance(experiment, comet_ml.OfflineExperiment):
        return "local"
    try:
        return str(experiment.get_artifact(DATASET_NAME).version)
    except Exception as exc:  # artifact missing or no network: training still runs on the CSVs
        print(f"dataset lineage not recorded ({exc}); run `make data` online to create it")
        return "local"


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-artifact", action="store_true", help="only write the CSVs")
    args = parser.parse_args(argv)
    paths = build()
    print(f"wrote {paths[0]} and {paths[1]}")
    if args.no_artifact:
        return
    experiment = comet_ml.start(
        project_name=config.COMET_PROJECT_NAME,
        experiment_config=comet_ml.ExperimentConfig(
            name=config.experiment_name("dataset"), tags=["dataset"]
        ),
    )
    try:
        if isinstance(experiment, comet_ml.OfflineExperiment):
            print("offline: Artifact not logged")
        else:
            log_artifact(experiment, paths)
    finally:
        experiment.end()


if __name__ == "__main__":
    main()
