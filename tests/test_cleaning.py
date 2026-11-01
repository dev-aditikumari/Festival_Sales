import numpy as np
import pandas as pd
import pytest

from festival_sales import cleaning
from festival_sales.cleaning import COLUMNS, clean, normalise_text, read_raw


def test_clean_tiny_data_is_unchanged(tiny_raw, tiny_clean):
    df, report = clean(tiny_raw)
    pd.testing.assert_frame_equal(df, tiny_clean)
    assert report.rows_in == 6 and report.rows_out == 6 and report.rows_dropped == 0


def test_columns_renamed_and_empty_columns_dropped(tiny_raw):
    df, report = clean(tiny_raw)
    assert list(df.columns) == COLUMNS
    assert report.dropped_columns == ["Status", "unnamed1"]


def test_non_empty_unknown_column_is_dropped_and_reported(tiny_raw):
    tiny_raw["Notes"] = "x"
    df, report = clean(tiny_raw)
    assert "Notes" not in df.columns
    assert "Notes" in report.dropped_columns


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Andhra\xa0Pradesh", "Andhra Pradesh"),
        ("Andhra�Pradesh", "Andhra Pradesh"),
        ("  Uttar   Pradesh ", "Uttar Pradesh"),
        ("Kerala", "Kerala"),
    ],
)
def test_normalise_text(value, expected):
    assert normalise_text(value) == expected


def test_normalise_text_passes_missing_through():
    assert pd.isna(normalise_text(np.nan))


def test_state_name_fixed_and_counted(tiny_raw):
    tiny_raw.loc[0, "State"] = "Andhra\xa0Pradesh"
    tiny_raw.loc[1, "State"] = "Andhra\xa0Pradesh"
    df, report = clean(tiny_raw)
    assert (df["state"] == "Andhra Pradesh").sum() == 2
    assert report.text_cells_changed == 2


def test_missing_amount_row_dropped_and_reported(tiny_raw):
    tiny_raw.loc[2, "Amount"] = np.nan
    df, report = clean(tiny_raw)
    assert len(df) == 5
    assert 3 not in df["user_id"].tolist()
    assert report.dropped_missing == {"amount": 1}
    assert report.rows_dropped == 1


def test_missing_text_value_dropped(tiny_raw):
    tiny_raw.loc[0, "State"] = np.nan
    df, report = clean(tiny_raw)
    assert len(df) == 5
    assert report.dropped_missing == {"state": 1}


@pytest.mark.parametrize(
    "column, bad_value",
    [("Orders", 0), ("Orders", -2), ("Amount", -5), ("Gender", "X"), ("Orders", "abc")],
)
def test_invalid_rows_dropped(tiny_raw, column, bad_value):
    tiny_raw[column] = tiny_raw[column].astype(object)
    tiny_raw.loc[0, column] = bad_value
    df, report = clean(tiny_raw)
    assert len(df) == 5
    assert report.dropped_invalid == 1


def test_gender_uppercased(tiny_raw):
    tiny_raw.loc[0, "Gender"] = "f"
    df, _ = clean(tiny_raw)
    assert df.loc[0, "gender"] == "F"


def test_integer_columns_become_integers_and_amount_stays_decimal(tiny_raw):
    df, _ = clean(tiny_raw)
    for col in cleaning.INT_COLUMNS:
        assert df[col].dtype == np.int64
    assert df["amount"].dtype == np.float64


def test_decimal_amount_keeps_cents(tiny_raw):
    tiny_raw.loc[0, "Amount"] = 123.456
    df, _ = clean(tiny_raw)
    assert df.loc[0, "amount"] == 123.46
    tiny_raw.loc[0, "Amount"] = 123.45
    df, _ = clean(tiny_raw)
    assert df.loc[0, "amount"] == 123.45


def test_duplicates_are_counted_but_kept(tiny_raw):
    doubled = pd.concat([tiny_raw, tiny_raw.iloc[[0]]], ignore_index=True)
    df, report = clean(doubled)
    assert len(df) == 7
    assert report.duplicate_rows == 1


def test_missing_required_column_raises(tiny_raw):
    with pytest.raises(ValueError, match="missing required columns.*amount"):
        clean(tiny_raw.drop(columns=["Amount"]))


def test_empty_frame_gives_empty_result(tiny_raw):
    df, report = clean(tiny_raw.iloc[0:0])
    assert df.empty and report.rows_out == 0


def test_empty_file_raises(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("")
    with pytest.raises(ValueError, match="empty"):
        read_raw(path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_raw(tmp_path / "nope.csv")


def test_header_only_file_gives_no_rows(tiny_raw, tmp_path):
    path = tmp_path / "header.csv"
    tiny_raw.iloc[0:0].to_csv(path, index=False)
    df, report = cleaning.load_clean(path)
    assert df.empty and report.rows_in == 0


def test_read_raw_handles_non_utf8_bytes(tmp_path, tiny_raw):
    tiny_raw.loc[0, "State"] = "Andhra\xa0Pradesh"
    path = tmp_path / "latin.csv"
    tiny_raw.to_csv(path, index=False, encoding="latin-1")
    df, _ = cleaning.load_clean(path)
    assert df.loc[0, "state"] == "Andhra Pradesh"


def test_report_summary_mentions_counts(tiny_raw):
    tiny_raw.loc[0, "Amount"] = np.nan
    _, report = clean(tiny_raw)
    text = report.summary()
    assert "rows dropped:            1" in text


def test_real_data_cleaning_counts(real_clean):
    df, report = real_clean
    assert report.rows_in == 11251
    assert report.rows_out == 11239
    assert report.dropped_missing == {"amount": 12}
    assert report.dropped_columns == ["Status", "unnamed1"]
    assert (df["amount"] % 1 != 0).sum() == 5
    assert df["amount"].sum().round(2) == 106249132.43
    assert "Andhra Pradesh" in set(df["state"])
    assert not df["state"].str.contains("\xa0|�|\\?", regex=True).any()
    assert df["state"].nunique() == 16
