"""Load the cleaned data into PostgreSQL and run the SQL files in ``sql/``."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

TABLE = "diwali_sales"
SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
LOCAL_DATA_DIR = Path(__file__).resolve().parent.parent / ".pgdata"

DDL = f"""
DROP TABLE IF EXISTS {TABLE};
CREATE TABLE {TABLE} (
    sale_id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id          INTEGER      NOT NULL,
    cust_name        VARCHAR(100) NOT NULL,
    product_id       VARCHAR(20)  NOT NULL,
    gender           CHAR(1)      NOT NULL CHECK (gender IN ('F', 'M')),
    age_group        VARCHAR(10)  NOT NULL,
    age              SMALLINT     NOT NULL CHECK (age > 0),
    marital_status   SMALLINT     NOT NULL CHECK (marital_status IN (0, 1)),
    state            VARCHAR(50)  NOT NULL,
    zone             VARCHAR(20)  NOT NULL,
    occupation       VARCHAR(50)  NOT NULL,
    product_category VARCHAR(50)  NOT NULL,
    orders           SMALLINT     NOT NULL CHECK (orders > 0),
    amount           NUMERIC(12,2) NOT NULL CHECK (amount >= 0)
);
CREATE INDEX idx_{TABLE}_state ON {TABLE} (state);
CREATE INDEX idx_{TABLE}_zone ON {TABLE} (zone);
CREATE INDEX idx_{TABLE}_category ON {TABLE} (product_category);
CREATE INDEX idx_{TABLE}_product ON {TABLE} (product_id);
CREATE INDEX idx_{TABLE}_age_group ON {TABLE} (age_group);
"""


def normalise_url(url: str) -> str:
    """Make a plain postgresql:// URL use the psycopg 3 driver."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def get_engine(url: str | None = None) -> Engine:
    url = url or os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("no database URL: pass one or set DATABASE_URL (see .env.example)")
    return create_engine(normalise_url(url))


def start_local_server(data_dir=LOCAL_DATA_DIR) -> str:
    """Start a bundled PostgreSQL (pgserver) and return its connection URL."""
    try:
        import pgserver
    except ImportError as exc:
        raise RuntimeError(
            "pgserver is not installed: pip install -r requirements-local.txt"
        ) from exc
    server = pgserver.get_server(Path(data_dir), cleanup_mode="stop")
    return server.get_uri()


def load_dataframe(df: pd.DataFrame, engine: Engine) -> int:
    """Recreate the table and insert df. Returns the number of rows stored."""
    with engine.begin() as conn:
        for statement in DDL.split(";"):
            if statement.strip():
                conn.execute(text(statement))
        df.to_sql(TABLE, conn, if_exists="append", index=False, method="multi", chunksize=1000)
        return conn.execute(text(f"SELECT COUNT(*) FROM {TABLE}")).scalar_one()


def sql_files() -> list[Path]:
    return sorted(SQL_DIR.glob("*.sql"))


def run_sql_file(engine: Engine, path) -> pd.DataFrame:
    query = Path(path).read_text()
    with engine.connect() as conn:
        result = pd.read_sql(text(query), conn)
    for col in result.columns:
        if result[col].dtype == object and len(result):
            try:
                result[col] = pd.to_numeric(result[col])
            except (ValueError, TypeError):
                pass
    return result
