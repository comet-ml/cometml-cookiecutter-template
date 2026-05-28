"""Mutate Comet Model Registry status and/or tags safely.

Invoked by the `promote-model` skill. Takes all inputs as separate argv entries
so there is no shell/Python interpolation attack surface from user-supplied
model names, versions, statuses, or tags.

Examples:
    # List versions and their current status/tags
    python scripts/registry_mutate.py list --model iris-classifier

    # Show the workspace's allowed status values
    python scripts/registry_mutate.py allowed-statuses

    # Set status on a version (single enum)
    python scripts/registry_mutate.py set-status \\
        --model iris-classifier --version 1.2.0 --status Production

    # Add a tag
    python scripts/registry_mutate.py add-tag \\
        --model iris-classifier --version 1.2.0 --tag release-2026-05

    # Remove a tag
    python scripts/registry_mutate.py remove-tag \\
        --model iris-classifier --version 1.2.0 --tag canary

API reference: https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/API/
"""
from __future__ import annotations

import argparse
import json
import sys

from comet_ml import API

# Importing the project's config loads .env via python-dotenv.
# Falls back to environment if the project's config module is unavailable.
try:
    from {{ cookiecutter.module_name }} import config

    _WORKSPACE_HINT = config.COMET_WORKSPACE
except Exception:
    import os

    _WORKSPACE_HINT = os.environ.get("COMET_WORKSPACE")


def _api() -> API:
    return API()


def _workspace(api: API) -> str:
    """Resolve workspace: prefer .env value, fall back to API key's default workspace."""
    if _WORKSPACE_HINT:
        return _WORKSPACE_HINT
    try:
        ws = api.get_default_workspace()
    except Exception as exc:
        sys.exit(
            f"COMET_WORKSPACE is not set in .env and could not resolve default "
            f"workspace from the API key ({exc}). Set COMET_WORKSPACE in your .env."
        )
    if not ws:
        sys.exit("Could not determine workspace. Set COMET_WORKSPACE in your .env.")
    return ws


def _get_model(model_name: str):
    api = _api()
    ws = _workspace(api)
    model = api.get_model(workspace=ws, model_name=model_name)
    if model is None:
        sys.exit(
            f"Model '{model_name}' not found in workspace '{ws}'. "
            f"List with: python scripts/registry_mutate.py list-models"
        )
    return model


def cmd_list(args: argparse.Namespace) -> None:
    """List versions of a registered model with their status and tags."""
    model = _get_model(args.model)
    versions = model.find_versions()
    rows = []
    for v in versions:
        try:
            details = model.get_details(version=v)
            status = details.get("status") or "None"
            tags = details.get("tags") or []
        except Exception as exc:
            status = f"<error: {exc}>"
            tags = []
        rows.append({"version": v, "status": status, "tags": tags})
    print(json.dumps(rows, indent=2))


def cmd_list_models(args: argparse.Namespace) -> None:
    """List all registered models in the workspace."""
    api = _api()
    ws = _workspace(api)
    print(json.dumps(api.get_registry_model_names(workspace=ws), indent=2))


def cmd_allowed_statuses(args: argparse.Namespace) -> None:
    """Print the workspace's allowed status values for the registry."""
    api = _api()
    ws = _workspace(api)
    try:
        allowed = api.model_registry_allowed_status_values(workspace=ws)
    except AttributeError:
        # Method name varies across SDK versions; fall back to Comet's standard set.
        allowed = ["None", "Development", "Staging", "QA", "Production"]
        print(
            "WARNING: api.model_registry_allowed_status_values not available; "
            "printing Comet's standard defaults.",
            file=sys.stderr,
        )
    print(json.dumps(allowed, indent=2))


def cmd_set_status(args: argparse.Namespace) -> None:
    """Set the (single-value) status of a model version."""
    model = _get_model(args.model)
    model.set_status(version=args.version, status=args.status)
    print(f"OK: {args.model} {args.version} status -> {args.status}")


def cmd_add_tag(args: argparse.Namespace) -> None:
    """Add a single tag to a model version. Idempotent."""
    model = _get_model(args.model)
    model.add_tag(version=args.version, tag=args.tag)
    print(f"OK: {args.model} {args.version} +tag '{args.tag}'")


def cmd_remove_tag(args: argparse.Namespace) -> None:
    """Remove a single tag from a model version."""
    model = _get_model(args.model)
    model.delete_tag(version=args.version, tag=args.tag)
    print(f"OK: {args.model} {args.version} -tag '{args.tag}'")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List versions of a model")
    p_list.add_argument("--model", required=True)
    p_list.set_defaults(func=cmd_list)

    p_lmodels = sub.add_parser("list-models", help="List registered models")
    p_lmodels.set_defaults(func=cmd_list_models)

    p_statuses = sub.add_parser("allowed-statuses", help="Show allowed status values")
    p_statuses.set_defaults(func=cmd_allowed_statuses)

    p_status = sub.add_parser("set-status", help="Set status on a version")
    p_status.add_argument("--model", required=True)
    p_status.add_argument("--version", required=True)
    p_status.add_argument("--status", required=True)
    p_status.set_defaults(func=cmd_set_status)

    p_add = sub.add_parser("add-tag", help="Add a tag to a version")
    p_add.add_argument("--model", required=True)
    p_add.add_argument("--version", required=True)
    p_add.add_argument("--tag", required=True)
    p_add.set_defaults(func=cmd_add_tag)

    p_rm = sub.add_parser("remove-tag", help="Remove a tag from a version")
    p_rm.add_argument("--model", required=True)
    p_rm.add_argument("--version", required=True)
    p_rm.add_argument("--tag", required=True)
    p_rm.set_defaults(func=cmd_remove_tag)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
