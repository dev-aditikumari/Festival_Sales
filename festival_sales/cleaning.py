"""Load and clean the Diwali sales CSV.

Cleaning rules, applied in this order:

1. Column names are converted to snake_case (``Age Group`` -> ``age_group``).
2. A ValueError is raised if any expected column is missing.
3. Columns that are not part of the schema (the empty ``Status`` and ``unnamed1``
   columns in the source file) are dropped and listed in the report.
4. In text columns, non-breaking spaces and the replacement character are turned into
   a normal space, repeated spaces are collapsed and the ends are stripped. This fixes
   ``Andhra<0xA0>Pradesh``, which shows up as ``Andhra?Pradesh`` in many viewers.
5. Rows with a missing value in any schema column are dropped (in the source this is
   12 rows with no Amount). The count per column is reported.
6. Rows with orders <= 0, a negative amount or a gender other than F/M are dropped.
7. Numeric columns other than amount are cast to integers. Amount stays a decimal
   number rounded to 2 places (5 source rows have cents).

Exact duplicate rows are counted but kept, because the source has no order id and a
repeat of the same customer, product and amount can be a genuine second purchase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

RAW_TO_CLEAN = {
    "User_ID": "user_id",
    "Cust_name": "cust_name",
    "Product_ID": "product_id",
    "Gender": "gender",
    "Age Group": "age_group",
    "Age": "age",
    "Marital_Status": "marital_status",
    "State": "state",
    "Zone": "zone",
    "Occupation": "occupation",
    "Product_Category": "product_category",
    "Orders": "orders",
    "Amount": "amount",
}
COLUMNS = list(RAW_TO_CLEAN.values())
TEXT_COLUMNS = [
    "cust_name",
    "product_id",
    "gender",
    "age_group",
    "state",
    "zone",
    "occupation",
    "product_category",
]
INT_COLUMNS = ["user_id", "age", "marital_status", "orders"]

# The file is not valid UTF-8; latin-1 reads every byte without error.
CSV_ENCODING = "latin-1"

_ODD_SPACES = re.compile(r"[ �]")
_MULTI_SPACE = re.compile(r"\s+")


@dataclass
class CleaningReport:
    rows_in: int = 0
    rows_out: int = 0
    dropped_columns: list = field(default_factory=list)
    text_cells_changed: int = 0
    dropped_missing: dict = field(default_factory=dict)
    dropped_invalid: int = 0
    duplicate_rows: int = 0

    @property
    def rows_dropped(self) -> int:
        return self.rows_in - self.rows_out

    def summary(self) -> str:
        lines = [
            f"rows read:               {self.rows_in}",
            f"rows kept:               {self.rows_out}",
            f"rows dropped:            {self.rows_dropped}",
            f"  missing values:        {sum(self.dropped_missing.values())} {self.dropped_missing}",
            f"  invalid values:        {self.dropped_invalid}",
            f"columns dropped:         {self.dropped_columns}",
            f"text cells normalised:   {self.text_cells_changed}",
            f"exact duplicate rows:    {self.duplicate_rows} (kept)",
        ]
        return "\n".join(lines)


def normalise_text(value):
    """Return value with odd spaces fixed; missing values pass through."""
    if pd.isna(value):
        return value
    text = _ODD_SPACES.sub(" ", str(value))
    return _MULTI_SPACE.sub(" ", text).strip()


def read_raw(path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    try:
        return pd.read_csv(path, encoding=CSV_ENCODING)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"CSV file is empty: {path}") from exc


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, CleaningReport]:
    """Apply the cleaning rules. Returns the cleaned frame and a report."""
    report = CleaningReport(rows_in=len(raw))
    df = raw.rename(columns=lambda c: RAW_TO_CLEAN.get(str(c).strip(), str(c).strip()))

    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    report.dropped_columns = [c for c in df.columns if c not in COLUMNS]
    df = df[COLUMNS].copy()

    for col in TEXT_COLUMNS:
        before = df[col]
        after = before.map(normalise_text)
        changed = (before != after) & before.notna()
        report.text_cells_changed += int(changed.sum())
        df[col] = after

    report.dropped_missing = {c: int(n) for c, n in df.isna().sum().items() if n > 0}
    df = df.dropna()

    df["gender"] = df["gender"].str.upper()
    for col in [*INT_COLUMNS, "amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    valid = (
        df["gender"].isin(["F", "M"])
        & df[INT_COLUMNS].notna().all(axis=1)
        & (df["orders"] > 0)
        & df["amount"].notna()
        & (df["amount"] >= 0)
    )
    report.dropped_invalid = int((~valid).sum())
    df = df[valid].astype({c: "int64" for c in INT_COLUMNS}).reset_index(drop=True)
    df["amount"] = df["amount"].astype("float64").round(2)

    report.duplicate_rows = int(df.duplicated().sum())
    report.rows_out = len(df)
    return df, report


def load_clean(path) -> tuple[pd.DataFrame, CleaningReport]:
    return clean(read_raw(path))
