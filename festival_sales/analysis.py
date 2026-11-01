"""Pure pandas analysis. Every function takes the cleaned frame and returns a new frame.

The summary tables share one shape so the SQL versions in ``sql/`` can be compared
with them directly: the grouping key(s), then transactions (rows), orders (sum of
Orders), amount, amount_share_pct, cumulative_amount_share_pct (running share when
sorted by amount) and amount_rank. Ties in amount are broken by the key(s) ascending.
"""

from __future__ import annotations

import pandas as pd

AGE_GROUP_ORDER = ["0-17", "18-25", "26-35", "36-45", "46-50", "51-55", "55+"]
SUMMARY_COLUMNS = [
    "transactions",
    "orders",
    "amount",
    "amount_share_pct",
    "cumulative_amount_share_pct",
    "amount_rank",
]


def summarize(df: pd.DataFrame, by) -> pd.DataFrame:
    """Sales summary grouped by one column name or a list of column names."""
    keys = [by] if isinstance(by, str) else list(by)
    for key in keys:
        if key not in df.columns:
            raise KeyError(f"column not found: {key}")
    grouped = (
        df.groupby(keys, as_index=False)
        .agg(transactions=("amount", "size"), orders=("orders", "sum"), amount=("amount", "sum"))
        .assign(amount=lambda t: t["amount"].round(2))
        .sort_values(["amount"] + keys, ascending=[False] + [True] * len(keys))
        .reset_index(drop=True)
    )
    total = grouped["amount"].sum()
    if total == 0:
        grouped["amount_share_pct"] = 0.0
        grouped["cumulative_amount_share_pct"] = 0.0
    else:
        grouped["amount_share_pct"] = (100.0 * grouped["amount"] / total).round(2)
        grouped["cumulative_amount_share_pct"] = (100.0 * grouped["amount"].cumsum() / total).round(
            2
        )
    grouped["amount_rank"] = grouped["amount"].rank(method="min", ascending=False).astype(int)
    return grouped


def by_state(df):
    return summarize(df, "state")


def by_zone(df):
    return summarize(df, "zone")


def by_gender(df):
    return summarize(df, "gender")


def by_age_group(df):
    return summarize(df, "age_group")


def by_occupation(df):
    return summarize(df, "occupation")


def by_category(df):
    return summarize(df, "product_category")


def marital_status_by_gender(df):
    return summarize(df, ["marital_status", "gender"])


def top_n(df: pd.DataFrame, by: str, n: int = 10, metric: str = "amount") -> pd.DataFrame:
    """Top n groups by a metric ('amount', 'orders' or 'transactions')."""
    if n < 1:
        raise ValueError("n must be at least 1")
    table = summarize(df, by)
    if metric not in ("amount", "orders", "transactions"):
        raise ValueError(f"unknown metric: {metric}")
    table = table.sort_values([metric, by], ascending=[False, True]).head(n)
    return table.reset_index(drop=True)


def top_products(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Top n products by total orders: product_id, orders, amount, orders_rank."""
    table = (
        df.groupby("product_id", as_index=False)
        .agg(orders=("orders", "sum"), amount=("amount", "sum"))
        .assign(amount=lambda t: t["amount"].round(2))
        .sort_values(["orders", "product_id"], ascending=[False, True])
        .reset_index(drop=True)
    )
    table["orders_rank"] = table["orders"].rank(method="min", ascending=False).astype(int)
    return table.head(n).reset_index(drop=True)


def category_rank_within_zone(df: pd.DataFrame) -> pd.DataFrame:
    """Each product category's amount and rank inside every zone."""
    table = (
        df.groupby(["zone", "product_category"], as_index=False)
        .agg(amount=("amount", "sum"))
        .assign(amount=lambda t: t["amount"].round(2))
        .sort_values(["zone", "amount", "product_category"], ascending=[True, False, True])
        .reset_index(drop=True)
    )
    table["rank_in_zone"] = (
        table.groupby("zone")["amount"].rank(method="min", ascending=False).astype(int)
    )
    return table


def overall_totals(df: pd.DataFrame) -> dict:
    return {
        "transactions": int(len(df)),
        "orders": int(df["orders"].sum()),
        "amount": round(float(df["amount"].sum()), 2),
        "customers": int(df["user_id"].nunique()),
    }
