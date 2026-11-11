"""Validate cookiecutter inputs before generating the project."""
import re
import sys

MODULE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
REPO_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

module_name = "{{ cookiecutter.module_name }}"
repo_name = "{{ cookiecutter.repo_name }}"
framework = "{{ cookiecutter.framework }}"
python_version = "{{ cookiecutter.python_version }}"

errors = []

if not MODULE_RE.match(module_name):
    errors.append(
        f"ERROR: module_name '{module_name}' is not a valid Python identifier. "
        "Use lowercase letters, digits, and underscores; must start with a letter or underscore."
    )

if not REPO_RE.match(repo_name):
    errors.append(
        f"ERROR: repo_name '{repo_name}' is not a valid repo slug. "
        "Use lowercase letters, digits, and hyphens; must start with a letter or digit."
    )

if framework == "tensorflow" and python_version == "3.13":
    errors.append("ERROR: tensorflow has no Python 3.13 wheels yet; pick python_version 3.12 or lower.")

if errors:
    for e in errors:
        print(e, file=sys.stderr)
    sys.exit(1)
