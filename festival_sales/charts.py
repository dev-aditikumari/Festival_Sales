"""Matplotlib charts. Each function saves one PNG and returns its path."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import analysis  # noqa: E402

PRIMARY = "#2a6f97"
SECONDARY = "#e07a1f"
GREY = "#5b6770"
MARITAL_LABELS = {0: "Unmarried", 1: "Married"}


def _style(ax, title, xlabel="", ylabel=""):
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)


def _save(fig, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def _millions(series):
    return series / 1_000_000


def sales_by_state(df, path, n=10):
    table = analysis.top_n(df, "state", n)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(table["state"], _millions(table["amount"]), color=PRIMARY)
    _style(ax, f"Sales amount, top {n} states", ylabel="Amount (millions)")
    ax.tick_params(axis="x", rotation=40)
    for label in ax.get_xticklabels():
        label.set_ha("right")
    return _save(fig, path)


def sales_by_zone(df, path):
    table = analysis.by_zone(df)
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.bar(table["zone"], _millions(table["amount"]), color=PRIMARY)
    _style(ax, "Sales amount by zone", ylabel="Amount (millions)")
    return _save(fig, path)


def sales_by_age_and_gender(df, path):
    pivot = (
        df.groupby(["age_group", "gender"])["amount"]
        .sum()
        .unstack("gender")
        .reindex(analysis.AGE_GROUP_ORDER)
        .fillna(0)
    )
    fig, ax = plt.subplots(figsize=(8, 4.5))
    x = range(len(pivot))
    width = 0.4
    ax.bar([i - width / 2 for i in x], _millions(pivot["F"]), width, label="Female", color=PRIMARY)
    ax.bar([i + width / 2 for i in x], _millions(pivot["M"]), width, label="Male", color=SECONDARY)
    ax.set_xticks(list(x))
    ax.set_xticklabels(pivot.index)
    _style(ax, "Sales amount by age group and gender", "Age group", "Amount (millions)")
    ax.legend(frameon=False)
    return _save(fig, path)


def sales_by_category(df, path):
    table = analysis.by_category(df).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(table["product_category"], _millions(table["amount"]), color=PRIMARY)
    _style(ax, "Sales amount by product category", xlabel="Amount (millions)")
    ax.grid(axis="y", alpha=0)
    ax.grid(axis="x", alpha=0.25)
    return _save(fig, path)


def sales_by_occupation(df, path):
    table = analysis.by_occupation(df).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(table["occupation"], _millions(table["amount"]), color=PRIMARY)
    _style(ax, "Sales amount by occupation", xlabel="Amount (millions)")
    ax.grid(axis="y", alpha=0)
    ax.grid(axis="x", alpha=0.25)
    return _save(fig, path)


def marital_status_by_gender(df, path):
    table = analysis.marital_status_by_gender(df)
    pivot = table.pivot(index="marital_status", columns="gender", values="amount").fillna(0)
    fig, ax = plt.subplots(figsize=(6, 4.5))
    x = range(len(pivot))
    width = 0.4
    ax.bar([i - width / 2 for i in x], _millions(pivot["F"]), width, label="Female", color=PRIMARY)
    ax.bar([i + width / 2 for i in x], _millions(pivot["M"]), width, label="Male", color=SECONDARY)
    ax.set_xticks(list(x))
    ax.set_xticklabels([MARITAL_LABELS[i] for i in pivot.index])
    _style(ax, "Sales amount by marital status and gender", ylabel="Amount (millions)")
    ax.legend(frameon=False)
    return _save(fig, path)


CHARTS = {
    "sales_by_state.png": sales_by_state,
    "sales_by_zone.png": sales_by_zone,
    "age_group_gender.png": sales_by_age_and_gender,
    "sales_by_category.png": sales_by_category,
    "sales_by_occupation.png": sales_by_occupation,
    "marital_gender.png": marital_status_by_gender,
}


def save_all(df: pd.DataFrame, out_dir) -> list[Path]:
    out_dir = Path(out_dir)
    return [func(df, out_dir / name) for name, func in CHARTS.items()]
