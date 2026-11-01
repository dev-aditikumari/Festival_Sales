import pandas as pd
import pytest

from festival_sales import analysis


def test_by_state(tiny_clean):
    result = analysis.by_state(tiny_clean)
    expected = pd.DataFrame(
        {
            "state": ["Delhi", "Kerala", "Maharashtra"],
            "transactions": [2, 2, 2],
            "orders": [6, 4, 3],
            "amount": [900, 600, 400],
            "amount_share_pct": [47.37, 31.58, 21.05],
            "cumulative_amount_share_pct": [47.37, 78.95, 100.0],
            "amount_rank": [1, 2, 3],
        }
    )
    pd.testing.assert_frame_equal(result, expected, check_dtype=False)


def test_by_zone(tiny_clean):
    result = analysis.by_zone(tiny_clean)
    assert result["zone"].tolist() == ["Northern", "Southern", "Western"]
    assert result["amount"].tolist() == [900, 600, 400]


def test_by_gender(tiny_clean):
    result = analysis.by_gender(tiny_clean).set_index("gender")
    assert result.loc["F", "amount"] == 1200
    assert result.loc["F", "orders"] == 10
    assert result.loc["F", "transactions"] == 4
    assert result.loc["M", "amount"] == 700
    assert result.loc["F", "amount_share_pct"] == pytest.approx(63.16)


def test_by_age_group(tiny_clean):
    result = analysis.by_age_group(tiny_clean)
    assert result["age_group"].tolist() == ["36-45", "26-35", "0-17", "18-25"]
    assert result["amount"].tolist() == [800, 500, 400, 200]


def test_by_occupation(tiny_clean):
    result = analysis.by_occupation(tiny_clean).set_index("occupation")
    assert result.loc["IT Sector", "amount"] == 1200
    assert result.loc["Govt", "amount"] == 600
    assert result.loc["Media", "amount"] == 100


def test_by_category(tiny_clean):
    result = analysis.by_category(tiny_clean)
    assert result["product_category"].tolist() == ["Auto", "Food"]
    assert result["amount"].tolist() == [1300, 600]
    assert result["orders"].tolist() == [6, 7]


def test_marital_status_by_gender_with_tie(tiny_clean):
    result = analysis.marital_status_by_gender(tiny_clean)
    keys = list(zip(result["marital_status"], result["gender"]))
    assert keys == [(1, "F"), (0, "M"), (0, "F"), (1, "M")]
    assert result["amount"].tolist() == [900, 400, 300, 300]
    assert result["amount_rank"].tolist() == [1, 2, 3, 3]


def test_shares_sum_to_100(tiny_clean):
    result = analysis.by_category(tiny_clean)
    assert result["amount_share_pct"].sum() == pytest.approx(100, abs=0.02)
    assert result["cumulative_amount_share_pct"].iloc[-1] == pytest.approx(100)


@pytest.mark.parametrize(
    "metric, n, expected",
    [
        ("amount", 1, ["Delhi"]),
        ("amount", 2, ["Delhi", "Kerala"]),
        ("orders", 3, ["Delhi", "Kerala", "Maharashtra"]),
        ("transactions", 2, ["Delhi", "Kerala"]),
        ("amount", 99, ["Delhi", "Kerala", "Maharashtra"]),
    ],
)
def test_top_n_states(tiny_clean, metric, n, expected):
    assert analysis.top_n(tiny_clean, "state", n, metric)["state"].tolist() == expected


def test_top_n_rejects_bad_arguments(tiny_clean):
    with pytest.raises(ValueError):
        analysis.top_n(tiny_clean, "state", 0)
    with pytest.raises(ValueError):
        analysis.top_n(tiny_clean, "state", 3, metric="profit")


def test_top_products(tiny_clean):
    result = analysis.top_products(tiny_clean, 2)
    assert result["product_id"].tolist() == ["P1", "P2"]
    assert result["orders"].tolist() == [7, 5]
    assert result["amount"].tolist() == [1200, 300]
    assert result["orders_rank"].tolist() == [1, 2]


def test_category_rank_within_zone(tiny_clean):
    result = analysis.category_rank_within_zone(tiny_clean)
    got = {(r.zone, r.product_category): (r.amount, r.rank_in_zone) for r in result.itertuples()}
    assert got[("Western", "Food")] == (300, 1)
    assert got[("Southern", "Auto")] == (400, 1)
    assert got[("Southern", "Food")] == (200, 2)
    assert got[("Northern", "Auto")] == (800, 1)


def test_overall_totals(tiny_clean):
    assert analysis.overall_totals(tiny_clean) == {
        "transactions": 6,
        "orders": 13,
        "amount": 1900,
        "customers": 6,
    }


def test_unknown_column_raises(tiny_clean):
    with pytest.raises(KeyError):
        analysis.summarize(tiny_clean, "colour")


def test_empty_frame_gives_empty_table(tiny_clean):
    result = analysis.by_state(tiny_clean.iloc[0:0])
    assert result.empty
    assert list(result.columns)[0] == "state"


def test_all_zero_amounts_do_not_divide_by_zero(tiny_clean):
    tiny_clean["amount"] = 0
    result = analysis.by_state(tiny_clean)
    assert (result["amount_share_pct"] == 0).all()


def test_input_not_modified(tiny_clean):
    before = tiny_clean.copy()
    analysis.by_state(tiny_clean)
    analysis.top_products(tiny_clean)
    pd.testing.assert_frame_equal(tiny_clean, before)
