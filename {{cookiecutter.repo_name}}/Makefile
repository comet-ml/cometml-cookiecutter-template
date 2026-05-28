.PHONY: help install install-dev format lint test train clean

help:
	@echo "Available targets:"
	@echo "  install      uv sync (runtime deps only)"
	@echo "  install-dev  uv sync --all-extras (includes ruff + pytest)"
	@echo "  format       ruff format src tests"
	@echo "  lint         ruff check src tests"
	@echo "  test         pytest"
	@echo "  train        run the example experiment (src/{{ cookiecutter.module_name }}/train.py)"
	@echo "  clean        remove caches and build artifacts"

install:
	uv sync

install-dev:
	uv sync --all-extras

format:
	uv run ruff format src tests

lint:
	uv run ruff check src tests

test:
	uv run pytest

train:
	uv run python -m {{ cookiecutter.module_name }}.train

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info
