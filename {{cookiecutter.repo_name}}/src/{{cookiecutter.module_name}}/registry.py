"""Model Registry helpers shared by train.py, predict.py and scripts/registry_mutate.py.

The CLI takes every input as a separate argv entry so user-supplied model names, versions,
statuses and tags never pass through shell or Python interpolation.

Examples:
    python scripts/registry_mutate.py list --model iris-classifier [--status Production]
    python scripts/registry_mutate.py list-models
    python scripts/registry_mutate.py allowed-statuses
    python scripts/registry_mutate.py set-status --model iris-classifier --version 1.2.0 \\
        --status QA
    python scripts/registry_mutate.py add-tag --model iris-classifier --version 1.2.0 --tag canary
    python scripts/registry_mutate.py remove-tag --model iris-classifier --version 1.2.0 \\
        --tag canary

API reference: https://www.comet.com/docs/v2/api-and-sdk/python-sdk/reference/Model/
"""
from __future__ import annotations

import argparse
import json
import sys

import comet_ml

from {{ cookiecutter.module_name }} import config


def workspace(api: comet_ml.API) -> str:
    """`COMET_WORKSPACE` from .env, else the API key's default workspace."""
    ws = config.COMET_WORKSPACE or api.get_default_workspace()
    if not ws:
        sys.exit("Could not determine the workspace. Set COMET_WORKSPACE in your .env.")
    return ws


def model_or_none(api: comet_ml.API, ws: str, model_name: str):
    """The `Model` handle, or None when nothing is registered under that name."""
    if model_name not in api.get_registry_model_names(ws):
        return None
    return api.get_model(ws, model_name)


def _model(args: argparse.Namespace):
    api = comet_ml.API()
    model = model_or_none(api, workspace(api), args.model)
    if model is None:
        sys.exit(f"Model '{args.model}' not found; list with: registry_mutate.py list-models")
    return model


def cmd_list(args: argparse.Namespace) -> None:
    """Versions of a model with status, tags and source experiment."""
    model = _model(args)
    rows = []
    for version in model.find_versions(status=args.status):
        try:
            details = model.get_details(version=version)
        except Exception as exc:  # one broken version must not hide the others
            rows.append({"version": version, "status": f"<error: {exc}>", "tags": []})
            continue
        rows.append(
            {
                "version": version,
                "status": details.get("status") or "None",
                "tags": details.get("tags") or [],
                "experimentKey": details.get("experimentKey"),
            }
        )
    print(json.dumps(rows, indent=2))


def cmd_list_models(args: argparse.Namespace) -> None:
    api = comet_ml.API()
    print(json.dumps(api.get_registry_model_names(workspace(api)), indent=2))


def cmd_allowed_statuses(args: argparse.Namespace) -> None:
    api = comet_ml.API()
    print(json.dumps(api.model_registry_allowed_status_values(workspace(api)), indent=2))


def cmd_set_status(args: argparse.Namespace) -> None:
    _model(args).set_status(version=args.version, status=args.status)
    print(f"OK: {args.model} {args.version} status -> {args.status}")


def cmd_add_tag(args: argparse.Namespace) -> None:
    _model(args).add_tag(version=args.version, tag=args.tag)
    print(f"OK: {args.model} {args.version} +tag '{args.tag}'")


def cmd_remove_tag(args: argparse.Namespace) -> None:
    _model(args).delete_tag(version=args.version, tag=args.tag)
    print(f"OK: {args.model} {args.version} -tag '{args.tag}'")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    model_args = argparse.ArgumentParser(add_help=False)
    model_args.add_argument("--model", required=True)
    version_args = argparse.ArgumentParser(add_help=False, parents=[model_args])
    version_args.add_argument("--version", required=True)

    p = sub.add_parser("list", parents=[model_args], help="List versions of a model")
    p.add_argument("--status", help="only versions with this status")
    p.set_defaults(func=cmd_list)
    sub.add_parser("list-models", help="List registered models").set_defaults(func=cmd_list_models)
    sub.add_parser("allowed-statuses", help="Show allowed status values").set_defaults(
        func=cmd_allowed_statuses
    )
    p = sub.add_parser("set-status", parents=[version_args], help="Set status on a version")
    p.add_argument("--status", required=True)
    p.set_defaults(func=cmd_set_status)
    p = sub.add_parser("add-tag", parents=[version_args], help="Add a tag to a version")
    p.add_argument("--tag", required=True)
    p.set_defaults(func=cmd_add_tag)
    p = sub.add_parser("remove-tag", parents=[version_args], help="Remove a tag from a version")
    p.add_argument("--tag", required=True)
    p.set_defaults(func=cmd_remove_tag)
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
