"""Smoke tests: package imports cleanly and config has the expected shape."""
import {{ cookiecutter.module_name }}
from {{ cookiecutter.module_name }} import config


def test_package_imports():
    assert {{ cookiecutter.module_name }}.__version__


def test_config_exposes_comet_project_name():
    assert isinstance(config.COMET_PROJECT_NAME, str)
    assert config.COMET_PROJECT_NAME
