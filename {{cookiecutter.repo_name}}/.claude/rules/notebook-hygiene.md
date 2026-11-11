---
paths:
  - "notebooks/**"
---

# Notebook Hygiene

Rules for Jupyter notebooks under `notebooks/`. Production code lives in `src/`.

## Notebooks are for exploration

- Use notebooks to explore data, sanity-check ideas, generate plots.
- **Do not** put long-lived training code, data-loading utilities, or model definitions in notebooks.
  Move them to `src/{{ cookiecutter.module_name }}/` as soon as you'll reuse them.
- Notebooks import from `src/`, never the other way around.

```python
# Cell 1: setup
import pandas as pd
from {{ cookiecutter.module_name }} import config, dataset, train

# Cell 2: load via src/
data = train.load_data()                                      # the CSVs from `make data`
df = pd.read_csv(config.DATA_DIR / dataset.TRAIN_CSV)

# Cell 3: explore
df.describe()
```

A bad notebook re-implements `load_data`, hardcodes paths, or contains a full training loop.

## Outputs never reach git

`.pre-commit-config.yaml` runs `nbstripout` on every commit; install the hooks once per clone with
`uv run pre-commit install`. Manual fallback: `uv run jupyter nbconvert --clear-output --inplace notebooks/*.ipynb`.

## No secrets in cells

- Never write `COMET_API_KEY = "abc..."` in a cell. `comet_ml.start()` reads it from the environment.
- If you `print(os.environ)`, redact before committing. Same for cloud keys and customer data.

## Length

Past ~300 lines, or when you scroll to find things: extract reusable cells into
`src/{{ cookiecutter.module_name }}/` and import them.

## Naming

Number-prefix so `ls notebooks/` reads chronologically: `01-eda.ipynb`, `02-features.ipynb`,
`03-baseline.ipynb`.

## Logging from notebooks

```python
import comet_ml
from {{ cookiecutter.module_name }} import config

experiment = comet_ml.start(
    project_name=config.COMET_PROJECT_NAME,
    experiment_config=comet_ml.ExperimentConfig(
        name=config.experiment_name("eda"), tags=["exploration"]
    ),
)
# ... work ...
experiment.log_notebook("notebooks/01-eda.ipynb")   # snapshot the notebook itself
experiment.end()
```

`start()` returns the running experiment when the cell re-runs, so you don't create duplicates. Tag
exploratory experiments (`exploration`, `eda`) so they stay out of the training dashboards.

## Dependencies

`ipykernel` and `nbstripout` are in the `dev` dependency group (`uv sync` installs them). Commit
`uv.lock` so notebooks and CI resolve the same versions.
