"""Configuration: loads .env and exposes Comet credentials.

Import COMET_* values from here rather than reading os.environ directly so that
secrets stay scoped to one module and tests can monkeypatch in one place.

Full Comet SDK configuration reference (timeouts, retries, batching, log levels):
https://www.comet.com/docs/v2/guides/experiment-management/configure-sdk/
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

COMET_API_KEY: str | None = os.environ.get("COMET_API_KEY")
COMET_WORKSPACE: str | None = os.environ.get("COMET_WORKSPACE")
COMET_PROJECT_NAME: str = os.environ.get("COMET_PROJECT_NAME", "{{ cookiecutter.repo_name }}")
# Comet backend URL — read by the SDK automatically when set in the environment.
# Override for single-tenant / on-prem deployments. Default points at public SaaS.
COMET_URL_OVERRIDE: str = os.environ.get(
    "COMET_URL_OVERRIDE", "{{ cookiecutter.comet_url_override }}"
)
