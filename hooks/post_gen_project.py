"""Post-generation hook.

Responsibilities:
- Drop the framework-specific train.py and append matching deps to pyproject.toml.
- Drop the chosen LICENSE (or delete it for Proprietary / None).
- Run `git init`.
- Print next-steps banner.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

FRAMEWORK = "{{ cookiecutter.framework }}"
LICENSE = "{{ cookiecutter.open_source_license }}"
MODULE_NAME = "{{ cookiecutter.module_name }}"
REPO_NAME = "{{ cookiecutter.repo_name }}"
AUTHOR_NAME = "{{ cookiecutter.author_name }}"

ROOT = Path.cwd()
TRAIN_PATH = ROOT / "src" / MODULE_NAME / "train.py"
PYPROJECT_PATH = ROOT / "pyproject.toml"
LICENSE_PATH = ROOT / "LICENSE"


# --- Framework-specific train.py ----------------------------------------------

_MODULE_PLACEHOLDER = "__MODULE_NAME__"

SKLEARN_TRAIN = '''"""Example experiment: sklearn LogisticRegression on iris, full Comet MLOps lifecycle."""
from pathlib import Path

import comet_ml
import joblib
import pandas as pd
from comet_ml import Artifact
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from __MODULE_NAME__ import config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_NAME = "iris-classifier"
DATASET_NAME = "iris-dataset"


def main() -> None:
    experiment = comet_ml.Experiment(
        api_key=config.COMET_API_KEY,
        workspace=config.COMET_WORKSPACE,
        project_name=config.COMET_PROJECT_NAME,
    )
    try:
        # --- 1. Code + tags -------------------------------------------------
        experiment.log_code(folder=str(PROJECT_ROOT / "src"))
        experiment.add_tags(["example", "framework=sklearn", "model=logreg"])

        # --- 2. Load + persist dataset, log as a versioned Artifact ---------
        X, y = load_iris(return_X_y=True, as_frame=True)
        df = pd.concat([X, y.rename("target")], axis=1)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
        train_path = DATA_DIR / "iris-train.csv"
        test_path = DATA_DIR / "iris-test.csv"
        train_df.to_csv(train_path, index=False)
        test_df.to_csv(test_path, index=False)

        dataset_artifact = Artifact(name=DATASET_NAME, artifact_type="dataset")
        dataset_artifact.add(str(train_path))
        dataset_artifact.add(str(test_path))
        experiment.log_artifact(dataset_artifact)
        experiment.log_dataset_hash(df)

        # --- 3. Train + log metrics ----------------------------------------
        params = {"max_iter": 200, "solver": "lbfgs", "random_state": 42}
        experiment.log_parameters(params)

        X_train, y_train = train_df.drop(columns=["target"]), train_df["target"]
        X_test, y_test = test_df.drop(columns=["target"]), test_df["target"]

        model = LogisticRegression(**params).fit(X_train, y_train)
        experiment.log_metric("train_accuracy", model.score(X_train, y_train))
        experiment.log_metric("test_accuracy", model.score(X_test, y_test))

        # --- 4. Save model file + log to experiment ------------------------
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / f"{MODEL_NAME}.pkl"
        joblib.dump(model, model_path)
        experiment.log_model(name=MODEL_NAME, file_or_folder=str(model_path))

        # --- 5. Register to Model Registry (promote to staging) -------------
        # Comment out if you only want to log models inside experiments.
        experiment.register_model(
            model_name=MODEL_NAME,
            tags=["staging"],
            description="Baseline sklearn LogisticRegression trained on iris-dataset.",
        )
    finally:
        experiment.end()


if __name__ == "__main__":
    main()
'''

XGBOOST_TRAIN = '''"""Example experiment: xgboost classifier on iris, full Comet MLOps lifecycle."""
from pathlib import Path

import comet_ml
import pandas as pd
import xgboost as xgb
from comet_ml import Artifact
from sklearn.datasets import load_iris
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from __MODULE_NAME__ import config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_NAME = "iris-xgb-classifier"
DATASET_NAME = "iris-dataset"


def main() -> None:
    experiment = comet_ml.Experiment(
        api_key=config.COMET_API_KEY,
        workspace=config.COMET_WORKSPACE,
        project_name=config.COMET_PROJECT_NAME,
    )
    try:
        # --- 1. Code + tags -------------------------------------------------
        experiment.log_code(folder=str(PROJECT_ROOT / "src"))
        experiment.add_tags(["example", "framework=xgboost", "model=xgbclassifier"])

        # --- 2. Load + persist dataset, log as a versioned Artifact ---------
        X, y = load_iris(return_X_y=True, as_frame=True)
        df = pd.concat([X, y.rename("target")], axis=1)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
        train_path = DATA_DIR / "iris-train.csv"
        test_path = DATA_DIR / "iris-test.csv"
        train_df.to_csv(train_path, index=False)
        test_df.to_csv(test_path, index=False)

        dataset_artifact = Artifact(name=DATASET_NAME, artifact_type="dataset")
        dataset_artifact.add(str(train_path))
        dataset_artifact.add(str(test_path))
        experiment.log_artifact(dataset_artifact)
        experiment.log_dataset_hash(df)

        # --- 3. Train + log metrics ----------------------------------------
        params = {
            "n_estimators": 50,
            "max_depth": 3,
            "learning_rate": 0.1,
            "objective": "multi:softprob",
            "num_class": 3,
            "random_state": 42,
        }
        experiment.log_parameters(params)

        X_train, y_train = train_df.drop(columns=["target"]), train_df["target"]
        X_test, y_test = test_df.drop(columns=["target"]), test_df["target"]

        model = xgb.XGBClassifier(**params).fit(X_train, y_train)
        experiment.log_metric("train_accuracy", accuracy_score(y_train, model.predict(X_train)))
        experiment.log_metric("test_accuracy", accuracy_score(y_test, model.predict(X_test)))

        # --- 4. Save model file + log to experiment ------------------------
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / f"{MODEL_NAME}.json"
        model.save_model(str(model_path))
        experiment.log_model(name=MODEL_NAME, file_or_folder=str(model_path))

        # --- 5. Register to Model Registry (promote to staging) -------------
        experiment.register_model(
            model_name=MODEL_NAME,
            tags=["staging"],
            description="Baseline XGBClassifier trained on iris-dataset.",
        )
    finally:
        experiment.end()


if __name__ == "__main__":
    main()
'''

PYTORCH_TRAIN = '''"""Example experiment: tiny torch model + one training step, full Comet MLOps lifecycle."""
from pathlib import Path

import comet_ml
import torch
from torch import nn

from __MODULE_NAME__ import config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_NAME = "tiny-torch-net"


class TinyNet(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(nn.Linear(10, 16), nn.ReLU(), nn.Linear(16, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def main() -> None:
    experiment = comet_ml.Experiment(
        api_key=config.COMET_API_KEY,
        workspace=config.COMET_WORKSPACE,
        project_name=config.COMET_PROJECT_NAME,
    )
    try:
        experiment.log_code(folder=str(PROJECT_ROOT / "src"))
        experiment.add_tags(["example", "framework=pytorch"])

        torch.manual_seed(42)
        model = TinyNet()
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        loss_fn = nn.MSELoss()

        experiment.log_parameters({"lr": 0.01, "optimizer": "SGD", "loss": "MSE"})

        x = torch.randn(32, 10)
        y = torch.randn(32, 1)

        optimizer.zero_grad()
        pred = model(x)
        loss = loss_fn(pred, y)
        loss.backward()
        optimizer.step()
        experiment.log_metric("loss", loss.item(), step=0)

        # --- Save + log model ---------------------------------------------
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / f"{MODEL_NAME}.pt"
        torch.save(model.state_dict(), model_path)
        experiment.log_model(name=MODEL_NAME, file_or_folder=str(model_path))

        # --- Register to Model Registry -----------------------------------
        experiment.register_model(
            model_name=MODEL_NAME,
            tags=["staging"],
            description="Tiny 2-layer MLP, single training step on synthetic data.",
        )
    finally:
        experiment.end()


if __name__ == "__main__":
    main()
'''

TENSORFLOW_TRAIN = '''"""Example experiment: tiny tf.keras model + one train_on_batch, full Comet MLOps lifecycle."""
from pathlib import Path

import comet_ml
import numpy as np
import tensorflow as tf

from __MODULE_NAME__ import config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_NAME = "tiny-keras-net"


def main() -> None:
    experiment = comet_ml.Experiment(
        api_key=config.COMET_API_KEY,
        workspace=config.COMET_WORKSPACE,
        project_name=config.COMET_PROJECT_NAME,
    )
    try:
        experiment.log_code(folder=str(PROJECT_ROOT / "src"))
        experiment.add_tags(["example", "framework=tensorflow"])

        tf.random.set_seed(42)
        model = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(10,)),
                tf.keras.layers.Dense(16, activation="relu"),
                tf.keras.layers.Dense(1),
            ]
        )
        model.compile(optimizer=tf.keras.optimizers.SGD(learning_rate=0.01), loss="mse")

        experiment.log_parameters({"lr": 0.01, "optimizer": "SGD", "loss": "mse"})

        x = np.random.randn(32, 10).astype("float32")
        y = np.random.randn(32, 1).astype("float32")

        loss = model.train_on_batch(x, y)
        experiment.log_metric("loss", float(loss), step=0)

        # --- Save + log model ---------------------------------------------
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / f"{MODEL_NAME}.keras"
        model.save(str(model_path))
        experiment.log_model(name=MODEL_NAME, file_or_folder=str(model_path))

        # --- Register to Model Registry -----------------------------------
        experiment.register_model(
            model_name=MODEL_NAME,
            tags=["staging"],
            description="Tiny 2-layer Keras MLP, single train_on_batch on synthetic data.",
        )
    finally:
        experiment.end()


if __name__ == "__main__":
    main()
'''

NONE_TRAIN = '''"""Example experiment: mock training loop with full Comet MLOps lifecycle (no ML framework)."""
import json
import random
from pathlib import Path

import comet_ml
from comet_ml import Artifact

from __MODULE_NAME__ import config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
MODEL_NAME = "mock-model"
DATASET_NAME = "mock-dataset"


def main() -> None:
    experiment = comet_ml.Experiment(
        api_key=config.COMET_API_KEY,
        workspace=config.COMET_WORKSPACE,
        project_name=config.COMET_PROJECT_NAME,
    )
    try:
        experiment.log_code(folder=str(PROJECT_ROOT / "src"))
        experiment.add_tags(["example", "framework=none"])

        # --- Stub dataset, logged as Artifact ------------------------------
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        dataset_path = DATA_DIR / "mock-dataset.json"
        dataset_path.write_text(json.dumps({"size": 1000, "schema": ["x", "y"]}))
        artifact = Artifact(name=DATASET_NAME, artifact_type="dataset")
        artifact.add(str(dataset_path))
        experiment.log_artifact(artifact)

        # --- Mock training loop --------------------------------------------
        params = {"lr": 0.01, "epochs": 10, "batch_size": 32}
        experiment.log_parameters(params)

        for epoch in range(params["epochs"]):
            experiment.log_metric("loss", random.random(), step=epoch)
            experiment.log_metric("accuracy", random.uniform(0.5, 1.0), step=epoch)

        # --- Save + log a stub model file ---------------------------------
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / f"{MODEL_NAME}.json"
        model_path.write_text(json.dumps({"weights": [0.1, 0.2, 0.3]}))
        experiment.log_model(name=MODEL_NAME, file_or_folder=str(model_path))

        # --- Register to Model Registry -----------------------------------
        experiment.register_model(
            model_name=MODEL_NAME,
            tags=["staging"],
            description="Stub model from the no-framework example.",
        )
    finally:
        experiment.end()


if __name__ == "__main__":
    main()
'''

TRAIN_TEMPLATES = {
    "sklearn": SKLEARN_TRAIN,
    "xgboost": XGBOOST_TRAIN,
    "pytorch": PYTORCH_TRAIN,
    "tensorflow": TENSORFLOW_TRAIN,
    "none": NONE_TRAIN,
}

FRAMEWORK_DEPS = {
    "sklearn": ["scikit-learn>=1.4.0", "pandas>=2.0.0", "joblib>=1.3.0"],
    "xgboost": ["xgboost>=2.0.0", "scikit-learn>=1.4.0", "pandas>=2.0.0"],
    "pytorch": ["torch>=2.0.0"],
    "tensorflow": ["tensorflow>=2.15.0"],
    "none": [],
}


def write_train() -> None:
    """Write the framework-specific train.py with the module name substituted in."""
    content = TRAIN_TEMPLATES[FRAMEWORK].replace(_MODULE_PLACEHOLDER, MODULE_NAME)
    TRAIN_PATH.write_text(content)


_DEP_ANCHOR_RE = re.compile(r'^(?P<indent>[ \t]+)"python-dotenv[^"]*",[ \t]*\r?\n', re.MULTILINE)


def append_deps() -> None:
    """Insert framework deps into pyproject.toml right after the python-dotenv anchor.

    Uses a regex tolerant of indentation, version-pin variations, and CRLF line endings.
    Inserts after the first match only so a stray comment mentioning python-dotenv
    elsewhere in the file cannot duplicate the deps.
    """
    deps = FRAMEWORK_DEPS[FRAMEWORK]
    if not deps:
        return
    text = PYPROJECT_PATH.read_text().replace("\r\n", "\n")
    match = _DEP_ANCHOR_RE.search(text)
    if not match:
        print(
            f"WARNING: could not find python-dotenv dependency anchor in pyproject.toml; "
            f"add these manually under [project].dependencies: {deps}",
            file=sys.stderr,
        )
        return
    indent = match.group("indent")
    insertion = "".join(f'{indent}"{d}",\n' for d in deps)
    end = match.end()
    PYPROJECT_PATH.write_text(text[:end] + insertion + text[end:])


# --- License ------------------------------------------------------------------

MIT_LICENSE = """MIT License

Copyright (c) 2026 {author}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

APACHE_LICENSE = """                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

Copyright 2026 {author}

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

For the full text of the Apache License 2.0, see:
    https://www.apache.org/licenses/LICENSE-2.0.txt
"""


def write_license() -> None:
    if LICENSE == "MIT":
        LICENSE_PATH.write_text(MIT_LICENSE.format(author=AUTHOR_NAME))
    elif LICENSE == "Apache-2.0":
        LICENSE_PATH.write_text(APACHE_LICENSE.format(author=AUTHOR_NAME))
    else:
        # Proprietary or None: remove the placeholder LICENSE file.
        if LICENSE_PATH.exists():
            LICENSE_PATH.unlink()


# --- Git init -----------------------------------------------------------------


def git_init() -> None:
    try:
        subprocess.run(["git", "init", "--quiet"], check=True)
        subprocess.run(["git", "add", "."], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"WARNING: git init failed ({exc}). Skipping.", file=sys.stderr)


# --- Next steps banner --------------------------------------------------------


def banner() -> None:
    msg = dedent(
        f"""
        ============================================================
        Project '{REPO_NAME}' generated.

        Next steps:
            cd {REPO_NAME}
            uv sync
            cp .env.example .env       # fill in COMET_API_KEY / COMET_WORKSPACE
            make train                 # run the example experiment

        See AGENT.md for an agentic-tool briefing and .claude/ for
        Claude Code rules and skills.
        ============================================================
        """
    ).strip()
    print(msg)


def main() -> None:
    write_train()
    append_deps()
    write_license()
    git_init()
    banner()


if __name__ == "__main__":
    main()
