"""Configuration: loads .env, exposes Comet settings, naming and promotion thresholds.

Import COMET_* values from here rather than reading os.environ directly so that
secrets stay scoped to one module and tests can monkeypatch in one place.

Full Comet SDK configuration reference (timeouts, retries, batching, log levels):
https://www.comet.com/docs/v2/guides/experiment-management/configure-sdk/
"""
from __future__ import annotations

import operator
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
THRESHOLDS_PATH = PROJECT_ROOT / "thresholds.yaml"

COMET_API_KEY: str | None = os.environ.get("COMET_API_KEY")
COMET_WORKSPACE: str | None = os.environ.get("COMET_WORKSPACE")
COMET_PROJECT_NAME: str = os.environ.get("COMET_PROJECT_NAME", "{{ cookiecutter.repo_name }}")
# Comet backend URL. The SDK reads it from the environment; override for single-tenant / on-prem.
COMET_URL_OVERRIDE: str = os.environ.get(
    "COMET_URL_OVERRIDE", "{{ cookiecutter.comet_url_override }}"
)


def experiment_name(model_name: str) -> str:
    """`{project}-{model}-{YYYYMMDD}-{HHmm}` in UTC: unique across archived runs and sortable."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")  # noqa: UP017 (py3.10 support)
    return f"{COMET_PROJECT_NAME}-{model_name}-{stamp}"


_OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt, "==": operator.eq}
_THRESHOLD_RE = re.compile(r"^\s*(>=|<=|==|>|<)\s*(-?\d+(?:\.\d+)?)\s*$")


def thresholds(path: Path = THRESHOLDS_PATH) -> dict[str, str]:
    """Metric -> condition string (e.g. `">=0.9"`) from thresholds.yaml; empty if absent."""
    if not path.exists():
        return {}
    return {k: str(v) for k, v in (yaml.safe_load(path.read_text()) or {}).items()}


def threshold_passes(metric: str, value: float, path: Path = THRESHOLDS_PATH) -> bool:
    """True when `value` satisfies the metric's condition, or when none is defined for it."""
    condition = thresholds(path).get(metric)
    if condition is None:
        return True
    match = _THRESHOLD_RE.match(condition)
    if not match:
        raise ValueError(f"thresholds.yaml: cannot parse {metric}: {condition!r}")
    op, bound = match.groups()
    return _OPS[op](value, float(bound))
