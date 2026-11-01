# Festival Sales Analytics

Analysis of a Diwali festival sales dataset (11,251 rows) written two ways: pandas functions in a
small tested Python package, and PostgreSQL queries over the same data. The test suite loads the
cleaned data into PostgreSQL, runs every SQL file and checks that the results equal the pandas
results. The original exploratory notebook is kept in `notebooks/`.

## Stack

Python, pandas, matplotlib, SQLAlchemy with psycopg 3, PostgreSQL 16, pytest, ruff, GitHub Actions.
For local runs without installing PostgreSQL, the optional `pgserver` package bundles a server.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r requirements-local.txt   # optional: bundled PostgreSQL for local runs
```

## Commands

```bash
python -m festival_sales report --markdown docs/findings.md   # clean, print findings, save charts
python -m festival_sales load-db --local                      # load into a bundled PostgreSQL (.pgdata/)
python -m festival_sales sql sql/01_by_state.sql --local      # run a query file
DATABASE_URL=postgresql://user:pass@host/db python -m festival_sales load-db   # your own server
ruff check . && ruff format --check .
pytest
```

`make test`, `make lint`, `make report` and `make load-db-local` wrap the same commands. See
`.env.example` for the `DATABASE_URL` format.

## Structure

```
data/Diwali Sales Data.csv     original dataset
notebooks/                     original notebook (only the CSV path was changed)
festival_sales/
  cleaning.py                  load and clean, with a report of what changed
  analysis.py                  pure pandas summaries
  charts.py                    matplotlib PNGs
  report.py                    findings and Markdown rendering
  db.py                        PostgreSQL schema, loader, SQL runner
  cli.py                       report / load-db / sql commands
sql/                           the same questions as PostgreSQL queries (01 to 09)
tests/                         pytest suite
docs/findings.md, docs/charts/ generated results
.github/workflows/ci.yml       lint, tests on 3.10 to 3.12 with a PostgreSQL service, actionlint
```

## Data and cleaning rules

Columns: User_ID, Cust_name, Product_ID, Gender, Age Group, Age, Marital_Status (0 or 1), State,
Zone, Occupation, Product_Category, Orders, Amount, plus two empty columns. Rules (also in the
docstring of `festival_sales/cleaning.py`), with what they did here:

- Column names become snake_case. A missing expected column raises an error.
- Columns outside the schema are dropped: `Status` and `unnamed1` are completely empty.
- Text columns: non-breaking spaces and replacement characters become a normal space. The file is
  not UTF-8 and the state "Andhra Pradesh" contains a byte 0xA0, which many viewers show as
  `Andhra?Pradesh`. 813 text cells changed.
- Rows with a missing value are dropped: 12 rows, all with no Amount.
- Rows with orders <= 0, negative amounts or an unknown gender are dropped: 0 rows.
- Numeric columns are cast to integers.
- Exact duplicate rows are counted but kept: 8 rows. There is no order id, so a repeat cannot be
  told apart from a second identical purchase.

Result: 11,251 rows read, 11,239 kept. Every run prints this report.

## SQL

Each file in `sql/` has a comment saying what it does and which pandas function it mirrors.

| File | Question | Features |
|---|---|---|
| 01 to 06 | sales, orders, share and running share by state, zone, gender, age group, occupation, category | CTE, GROUP BY, SUM() OVER, RANK() |
| 07 | marital status by gender | two grouping keys, window functions |
| 08 | top 10 products by orders | aggregate in RANK, LIMIT |
| 09 | rank of each category inside each zone | RANK() PARTITION BY, CTE |

The table `diwali_sales` has typed columns, CHECK constraints, an identity primary key and indexes
on state, zone, category, product and age group (see `festival_sales/db.py`).

## Findings

Full tables are in [docs/findings.md](docs/findings.md). Amounts are in the file's own units (no
currency is given). Total: 106,249,129 over 27,981 orders.

- Uttar Pradesh is the top state by amount (19,374,968, 18.24%) and by orders (4,807), followed by
  Maharashtra and Karnataka. The top three states are 44.55% of the total.
- The Central zone is the largest (39.15%), then Southern (25.04%).
- Women account for 69.96% of the amount (74,335,853 vs 31,913,276 for men).
- The 26-35 age group spends the most (40.11%).
- Food is the top category by amount (33,933,883, 31.94%), ahead of Clothing & Apparel (15.52%),
  Electronics & Gadgets (14.72%) and Footwear & Shoes (14.66%). By orders the order is Clothing &
  Apparel (6,634), Food (6,110), Electronics & Gadgets (5,226).
- IT Sector (13.89%), Healthcare (12.27%) and Aviation (11.86%) are the top occupations.
- By marital status and gender, unmarried women are the largest segment (41.21%), ahead of married
  women (28.75%). The notebook's conclusion names married women; the numbers here do not show that.

![Sales by state](docs/charts/sales_by_state.png)
![Sales by zone](docs/charts/sales_by_zone.png)
![Age group and gender](docs/charts/age_group_gender.png)
![Sales by category](docs/charts/sales_by_category.png)
![Sales by occupation](docs/charts/sales_by_occupation.png)
![Marital status and gender](docs/charts/marital_gender.png)

## Testing

`pytest` runs unit tests for every cleaning rule and analysis function on a six-row fixture with
hand-computed answers, tests for bad input (missing columns, empty or missing file, invalid values),
CLI tests, and database tests. The database tests run each SQL file on both the fixture and the full
dataset and compare with pandas. They use `DATABASE_URL` if set, otherwise a bundled server from
`pgserver`; without either they are skipped.

Locally: 86 tests passed, with PostgreSQL 16.2 started by `pgserver`. CI runs the same tests against
a `postgres:16` service container on Python 3.10, 3.11 and 3.12, and lints the workflow with
actionlint. The CI workflow has been validated with actionlint locally but has not been run on
GitHub.

## Limitations

- One season, no dates and no order id, so there are no trends, repeat-purchase or cohort analyses.
- Findings describe correlation within this data only. For example, women having a larger share of
  the amount does not say whether they bought for themselves or for others.
- The share of amount is rounded to two decimals; SQL and pandas are compared with a 0.011
  tolerance on those columns and exactly on all counts and sums.
- Zone is taken from the file as given and not checked against official definitions.
- Age and age group are taken as given; they were not checked against each other.
- The loader recreates the table on every run, which is simple but not incremental.
