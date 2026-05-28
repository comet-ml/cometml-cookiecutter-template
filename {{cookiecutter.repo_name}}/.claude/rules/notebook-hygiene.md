# Notebook Hygiene

Rules for Jupyter notebooks under `notebooks/`. Production code lives in `src/`.

## Notebooks are for exploration

- Use notebooks to explore data, sanity-check ideas, generate plots.
- **Do not** put long-lived training code, data-loading utilities, or model definitions in notebooks. Move them to `src/{{ cookiecutter.module_name }}/` as soon as you'll reuse them.
- Notebooks should import from `src/` — never the other way around.

A good notebook looks like:

```python
# Cell 1: setup
from {{ cookiecutter.module_name }} import config, dataset
import pandas as pd

# Cell 2: load via src/
df = pd.read_csv(dataset.load_processed("train.csv"))

# Cell 3: explore
df.describe()
```

A bad notebook reimplements `dataset.load_processed`, hardcodes paths, or contains a full training loop.

## Clear outputs before committing

Notebook output cells bloat git diffs, leak data, and make code review painful.

Options:

- Manually: `Cell > All Output > Clear` in Jupyter, then save.
- CLI: `jupyter nbconvert --clear-output --inplace notebooks/*.ipynb`
- Automatic: install [`nbstripout`](https://github.com/kynan/nbstripout) and configure it as a git filter (`nbstripout --install`).

## No secrets in cells

- Never write `COMET_API_KEY = "abc..."` in a cell. Use `config.COMET_API_KEY`.
- If you `print(os.environ)`, redact before committing.
- Same for AWS keys, database passwords, customer PII.

## Length

If a notebook grows past ~300 lines or you find yourself scrolling to find things, that's a signal to:

1. Extract reusable cells into `src/{{ cookiecutter.module_name }}/` modules.
2. Have the notebook import them.

## Naming

Use a number prefix so `ls notebooks/` reads chronologically:

```
notebooks/
├── 01-eda.ipynb
├── 02-feature-engineering.ipynb
└── 03-baseline-model.ipynb
```

## Logging from notebooks

You can still create Comet experiments from notebooks for exploratory runs:

```python
experiment = comet_ml.Experiment(
    api_key=config.COMET_API_KEY,
    workspace=config.COMET_WORKSPACE,
    project_name=config.COMET_PROJECT_NAME,
)
experiment.add_tag("exploration")
# ...
experiment.end()
```

Tag exploratory notebook experiments distinctly (e.g. `exploration`, `eda`) so they don't pollute the metrics dashboard alongside real training runs.
