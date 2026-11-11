.PHONY: help install format lint test data train sweep predict clean

MODULE := {{ cookiecutter.module_name }}

help:
	@echo "Available targets:"
	@echo "  install  uv sync (runtime + dev deps)"
	@echo "  format   ruff format src tests scripts"
	@echo "  lint     ruff check src tests scripts"
	@echo "  test     pytest (credential-free)"
	@echo "  data     build data/processed/iris-*.csv and log the dataset Artifact"
	@echo "  train    run one experiment; registers a version when thresholds.yaml passes"
	@echo "  sweep    run a Comet Optimizer sweep over train()"
	@echo "  predict  load the Production registry version and predict on test rows"
	@echo "  clean    remove caches and build artifacts"

install:
	uv sync

format:
	uv run ruff format src tests scripts

lint:
	uv run ruff check src tests scripts

test:
	uv run pytest

data data/processed/iris-train.csv:
	uv run python -m $(MODULE).dataset

train: data/processed/iris-train.csv
	uv run python -m $(MODULE).train

sweep: data/processed/iris-train.csv
	uv run python -m $(MODULE).sweep

predict: data/processed/iris-train.csv
	uv run python -m $(MODULE).predict

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
