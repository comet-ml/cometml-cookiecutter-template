"""Argument parsing for the registry CLI and the sweep definition (no network)."""
import importlib.util
import sys
from pathlib import Path

from {{ cookiecutter.module_name }} import sweep, train


def _registry_mutate():
    path = Path(__file__).resolve().parents[1] / "scripts" / "registry_mutate.py"
    spec = importlib.util.spec_from_file_location("registry_mutate", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["registry_mutate"] = module
    spec.loader.exec_module(module)
    return module


def test_registry_list_accepts_status_filter():
    args = _registry_mutate().build_parser().parse_args(
        ["list", "--model", "iris-classifier", "--status", "Production"]
    )
    assert args.status == "Production"
    assert args.func.__name__ == "cmd_list"


def test_registry_set_status_requires_version():
    parser = _registry_mutate().build_parser()
    try:
        parser.parse_args(["set-status", "--model", "m", "--status", "QA"])
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError("missing --version must be rejected")


def test_sweep_space_only_uses_known_params():
    assert sweep.OPTIMIZER_CONFIG["spec"]["metric"] == "val_accuracy"
    assert set(sweep.OPTIMIZER_CONFIG["parameters"]) <= set(train.DEFAULT_PARAMS)
