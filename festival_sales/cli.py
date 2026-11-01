"""Command line entry point: python -m festival_sales {report,load-db,sql}."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import charts, db, report
from .cleaning import load_clean

DEFAULT_CSV = "data/Diwali Sales Data.csv"


def _add_csv(parser):
    parser.add_argument("--csv", default=DEFAULT_CSV, help="path to the raw CSV")


def _add_db(parser):
    parser.add_argument("--database-url", help="PostgreSQL URL (default: DATABASE_URL)")
    parser.add_argument(
        "--local", action="store_true", help="start a bundled PostgreSQL (needs pgserver)"
    )


def _engine(args):
    url = db.start_local_server() if args.local else args.database_url
    return db.get_engine(url)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="festival_sales", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser("report", help="clean the data, print findings, save charts")
    _add_csv(rep)
    rep.add_argument("--charts-dir", default="docs/charts")
    rep.add_argument("--markdown", help="also write the findings to this Markdown file")

    load = sub.add_parser("load-db", help="clean the data and load it into PostgreSQL")
    _add_csv(load)
    _add_db(load)

    sql = sub.add_parser("sql", help="run one of the files in sql/ and print the result")
    sql.add_argument("file", help="path to a .sql file")
    _add_csv(sql)
    _add_db(sql)
    sql.add_argument("--load", action="store_true", help="load the CSV first")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "report":
            df, rep = load_clean(args.csv)
            print(rep.summary())
            findings = report.compute_findings(df)
            text = report.render_markdown(findings, rows_dropped=rep.rows_dropped)
            print()
            print(text)
            paths = charts.save_all(df, args.charts_dir)
            print(f"saved {len(paths)} charts to {args.charts_dir}")
            if args.markdown:
                Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
                Path(args.markdown).write_text(text)
        elif args.command == "load-db":
            df, rep = load_clean(args.csv)
            print(rep.summary())
            count = db.load_dataframe(df, _engine(args))
            print(f"loaded {count} rows into table {db.TABLE}")
        elif args.command == "sql":
            engine = _engine(args)
            if args.load:
                df, _ = load_clean(args.csv)
                db.load_dataframe(df, engine)
            print(db.run_sql_file(engine, args.file).to_string(index=False))
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
