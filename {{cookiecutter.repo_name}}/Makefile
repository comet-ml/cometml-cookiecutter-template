.PHONY: help install format lint test data train sweep predict clean

MODULE := {{ cookiecutter.module_name }}
ARGS ?=

help:
	@echo "Available targets:"
	@echo "  install  uv sync (runtime + dev deps)"
	@echo "  format   ruff format src tests scripts"
	@echo "  lint     ruff check src tests scripts"
	@echo "  test     pytest (credential-free)"
	@echo "  data     build data/processed/iris-*.csv and log the dataset Artifact"
	@echo "  train    run one experiment; registers a version when thresholds.yaml passes"
	@echo "           (pass flags with ARGS, e.g. make train ARGS=\"--register --epochs 30\")"
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

data:
	uv run python -m $(MODULE).dataset $(ARGS)

# Prerequisite for train/sweep/predict: build the CSVs without ARGS and without Comet.
data/processed/iris-train.csv:
	uv run python -m $(MODULE).dataset --no-artifact

train: data/processed/iris-train.csv
	uv run python -m $(MODULE).train $(ARGS)

sweep: data/processed/iris-train.csv
	uv run python -m $(MODULE).sweep $(ARGS)

predict: data/processed/iris-train.csv
	uv run python -m $(MODULE).predict $(ARGS)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
