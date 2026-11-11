"""Argument parsing for the registry CLI and the sweep definition (no network)."""
import pytest

from {{ cookiecutter.module_name }} import registry, sweep, train


def test_registry_list_accepts_status_filter():
    args = registry.build_parser().parse_args(
        ["list", "--model", "iris-classifier", "--status", "Production"]
    )
    assert args.status == "Production"
    assert args.func is registry.cmd_list


def test_registry_set_status_requires_version():
    with pytest.raises(SystemExit) as exc:
        registry.build_parser().parse_args(["set-status", "--model", "m", "--status", "QA"])
    assert exc.value.code == 2


def test_sweep_space_only_uses_known_params():
    assert sweep.OPTIMIZER_CONFIG["spec"]["metric"] == "val_accuracy"
    assert set(sweep.OPTIMIZER_CONFIG["parameters"]) <= set(train.DEFAULT_PARAMS)
