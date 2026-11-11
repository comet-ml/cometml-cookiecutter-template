# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial project scaffold generated from [cometml-cookiecutter-template](https://github.com/comet-ml/cometml-cookiecutter-template).
- `.mcp.json` at repo root that auto-registers the [Comet MCP server](https://www.comet.com/docs/v2/api-and-sdk/mcp-server/overview/) with Claude Code.
- Comet EM lifecycle: `make data` / `train` / `sweep` / `predict`, `thresholds.yaml` gate, `scripts/registry_mutate.py`.
- Claude Code skills: `run-training`, `evaluate-run`, `compare-runs`, `debug-run`, `run-sweep`, `promote-model`, `update-changelog`.
- GitHub Actions: `ci.yml` and `deploy-model.yml` (Model Registry status webhook).
