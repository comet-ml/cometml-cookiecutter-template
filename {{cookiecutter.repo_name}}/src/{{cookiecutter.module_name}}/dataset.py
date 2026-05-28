"""Data loading utilities.

Replace these stubs with project-specific loaders. Keep them framework-agnostic
where possible so train.py and notebooks can both reuse them.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
EXTERNAL_DIR = DATA_DIR / "external"


def load_raw(filename: str) -> Path:
    """Return the path to a file under data/raw/."""
    return RAW_DIR / filename


def load_processed(filename: str) -> Path:
    """Return the path to a file under data/processed/."""
    return PROCESSED_DIR / filename
