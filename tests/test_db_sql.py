"""Run each SQL file in PostgreSQL and check it matches the pandas result."""

import pandas as pd
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from festival_sales import analysis, db

CASES = {
    "01_by_state.sql": analysis.by_state,
    "02_by_zone.sql": analysis.by_zone,
    "03_by_gender.sql": analysis.by_gender,
    "04_by_age_group.sql": analysis.by_age_group,
    "05_by_occupation.sql": analysis.by_occupation,
    "06_by_category.sql": analysis.by_category,
    "07_marital_status_by_gender.sql": analysis.marital_status_by_gender,
    "08_top_products.sql": analysis.top_products,
    "09_category_rank_within_zone.sql": analysis.category_rank_within_zone,
}


def _compare(sql_result, pandas_result):
    pd.testing.assert_frame_equal(
        sql_result.reset_index(drop=True),
        pandas_result.reset_index(drop=True),
        check_dtype=False,
        atol=0.011,
        rtol=0,
    )


def test_every_sql_file_has_a_pandas_counterpart():
    assert {p.name for p in db.sql_files()} == set(CASES)


@pytest.mark.parametrize("filename", sorted(CASES))
def test_sql_matches_pandas_on_full_data(db_full, real_clean, filename):
    sql_result = db.run_sql_file(db_full, db.SQL_DIR / filename)
    _compare(sql_result, CASES[filename](real_clean[0]))


@pytest.mark.parametrize("filename", sorted(CASES))
def test_sql_matches_pandas_on_tiny_data(db_tiny, tiny_clean, filename):
    sql_result = db.run_sql_file(db_tiny, db.SQL_DIR / filename)
    _compare(sql_result, CASES[filename](tiny_clean))


def test_sql_known_values_on_tiny_data(db_tiny):
    result = db.run_sql_file(db_tiny, db.SQL_DIR / "01_by_state.sql")
    assert result["state"].tolist() == ["Delhi", "Kerala", "Maharashtra"]
    assert result["cumulative_amount_share_pct"].tolist() == [47.37, 78.95, 100.0]


def test_load_reports_row_count_and_is_repeatable(engine, real_clean):
    df = real_clean[0]
    assert db.load_dataframe(df, engine) == len(df)
    assert db.load_dataframe(df, engine) == len(df)


def test_table_has_expected_indexes(db_full):
    with db_full.connect() as conn:
        names = {
            r[0]
            for r in conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = :t"), {"t": db.TABLE}
            )
        }
    assert {
        "idx_diwali_sales_state",
        "idx_diwali_sales_zone",
        "idx_diwali_sales_category",
        "idx_diwali_sales_product",
        "idx_diwali_sales_age_group",
    } <= names


def test_column_types(db_full):
    with db_full.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = :t"
            ),
            {"t": db.TABLE},
        ).all()
    types = dict(rows)
    assert types["amount"] == "integer"
    assert types["orders"] == "smallint"
    assert types["state"] == "character varying"


def test_database_rejects_bad_gender(db_full):
    with pytest.raises(DBAPIError):
        with db_full.begin() as conn:
            conn.execute(text(f"UPDATE {db.TABLE} SET gender = 'X' WHERE sale_id = 1"))


@pytest.mark.parametrize(
    "url, expected",
    [
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgres://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ],
)
def test_normalise_url(url, expected):
    assert db.normalise_url(url) == expected


def test_get_engine_without_url_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.get_engine()
