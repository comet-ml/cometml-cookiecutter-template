"""Credential-free tests: naming, thresholds, dataset build and the training loop."""
import re

import {{ cookiecutter.module_name }}
from {{ cookiecutter.module_name }} import config, dataset, predict, train


class StubExperiment:
    """Records what training logs without talking to Comet."""

    def __init__(self):
        self.metrics: dict[str, list[float]] = {}
        self.params: dict = {}
        self.calls: list[str] = []

    def log_metric(self, name, value, step=None, epoch=None):
        self.metrics.setdefault(name, []).append(float(value))

    def log_metrics(self, values, step=None, epoch=None):
        for name, value in values.items():
            self.log_metric(name, value, step=step, epoch=epoch)

    def log_parameters(self, params):
        self.params.update(params)

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.calls.append(name)


def test_package_imports():
    assert {{ cookiecutter.module_name }}.__version__


def test_experiment_name_follows_convention():
    name = config.experiment_name("iris-classifier")
    assert re.fullmatch(r"[\w-]+-\d{8}-\d{4}", name), name
    assert name.startswith(f"{config.COMET_PROJECT_NAME}-iris-classifier-")


def test_failing_thresholds_checks_every_listed_metric(tmp_path):
    path = tmp_path / "thresholds.yaml"
    path.write_text('val_accuracy: ">=0.9"\ntrain_loss: "<=0.5"\n')
    passing = {"val_accuracy": 0.95, "train_loss": 0.2}
    assert config.failing_thresholds(passing, path=path) == []
    failing = config.failing_thresholds({"val_accuracy": 0.95, "train_loss": 0.9}, path=path)
    assert failing == ["train_loss"]
    missing = {"val_accuracy": 0.95}
    assert config.failing_thresholds(missing, path=path) == ["train_loss"]
    assert config.failing_thresholds({"anything": 1.0}, path=tmp_path / "absent.yaml") == []


def test_bump_patch():
    assert train.bump_patch("1.2.3") == "1.2.4"
    assert train.bump_patch("1.0.0-rc.1") == "1.0.1"
    assert train.bump_patch(None) == "1.0.0"


def test_dataset_build_writes_train_and_test_csv(tmp_path):
    train_csv, test_csv = dataset.build(tmp_path)
    assert train_csv.exists() and test_csv.exists()
    assert train_csv.read_text().splitlines()[0].endswith("target")


def test_train_logs_per_epoch_and_returns_val_accuracy(tmp_path):
    data = train.load_data(tmp_path)  # builds the CSVs on first use
    experiment = StubExperiment()

    model, metrics = train.train(experiment, train.DEFAULT_PARAMS, data)

    assert model is not None
    assert 0.0 <= metrics["val_accuracy"] <= 1.0
    assert experiment.params == train.DEFAULT_PARAMS
    assert len(experiment.metrics["val_accuracy"]) == train.DEFAULT_PARAMS["epochs"]
    assert "log_confusion_matrix" in experiment.calls


def test_saved_model_round_trips_with_its_preprocessing(tmp_path):
    data = train.load_data(tmp_path)
    model, metrics = train.train(StubExperiment(), train.DEFAULT_PARAMS, data)

    train.save_model(model, tmp_path / "model")
    loaded = predict.load_from_dir(tmp_path / "model")

    y_pred = train.predict(loaded, data.X_val)
    assert train.accuracy(data.y_val, y_pred) == metrics["val_accuracy"]
