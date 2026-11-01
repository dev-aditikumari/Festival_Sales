import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from festival_sales import db
from festival_sales.cleaning import COLUMNS, RAW_TO_CLEAN, load_clean

ROOT = Path(__file__).resolve().parent.parent
REAL_CSV = ROOT / "data" / "Diwali Sales Data.csv"

# same order as cleaning.COLUMNS
TINY_ROWS = [
    (1, "A", "P1", "F", "26-35", 28, 0, "Maharashtra", "Western", "IT Sector", "Auto", 1, 100),
    (2, "B", "P1", "M", "26-35", 30, 1, "Maharashtra", "Western", "IT Sector", "Food", 2, 300),
    (3, "C", "P2", "F", "18-25", 20, 0, "Kerala", "Southern", "Govt", "Food", 3, 200),
    (4, "D", "P3", "M", "0-17", 15, 0, "Kerala", "Southern", "Govt", "Auto", 1, 400),
    (5, "E", "P2", "F", "26-35", 33, 1, "Delhi", "Northern", "Media", "Food", 2, 100),
    (6, "F", "P1", "F", "36-45", 40, 1, "Delhi", "Northern", "IT Sector", "Auto", 4, 800),
]


@pytest.fixture
def tiny_clean():
    df = pd.DataFrame(TINY_ROWS, columns=COLUMNS)
    df = df.astype({c: "int64" for c in ["user_id", "age", "marital_status", "orders"]})
    df["amount"] = df["amount"].astype("float64")
    return df


@pytest.fixture
def tiny_raw(tiny_clean):
    """The tiny data in the raw file layout, including the two empty columns."""
    raw = tiny_clean.rename(columns={v: k for k, v in RAW_TO_CLEAN.items()})
    raw["Status"] = np.nan
    raw["unnamed1"] = np.nan
    return raw


@pytest.fixture
def tiny_csv(tiny_raw, tmp_path):
    path = tmp_path / "tiny.csv"
    tiny_raw.to_csv(path, index=False, encoding="latin-1")
    return path


@pytest.fixture(scope="session")
def real_clean():
    df, report = load_clean(REAL_CSV)
    return df, report


@pytest.fixture(scope="session")
def engine(tmp_path_factory):
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            url = db.start_local_server(tmp_path_factory.mktemp("pgdata"))
        except Exception as exc:
            pytest.skip(f"no PostgreSQL available (set DATABASE_URL or install pgserver): {exc}")
    eng = db.get_engine(url)
    yield eng
    eng.dispose()


_loaded = {"name": None}


def _ensure(engine, name, df):
    if _loaded["name"] != name:
        db.load_dataframe(df, engine)
        _loaded["name"] = name


@pytest.fixture
def db_full(engine, real_clean):
    _ensure(engine, "full", real_clean[0])
    return engine


@pytest.fixture
def db_tiny(engine, tiny_clean):
    _ensure(engine, "tiny", tiny_clean)
    return engine


@pytest.fixture
def db_scratch(engine):
    """Engine for a test that loads its own data; the next fixture user reloads."""
    _loaded["name"] = None
    return engine
