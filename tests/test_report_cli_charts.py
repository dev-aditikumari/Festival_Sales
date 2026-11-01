import pytest

from festival_sales import charts, cli, report


def test_findings_on_tiny_data(tiny_clean):
    f = report.compute_findings(tiny_clean)
    assert f["top_state"] == ("Delhi", 900, 47.37)
    assert f["top_zone"][0] == "Northern"
    assert f["top_gender"][0] == "F"
    assert f["top_age_group"][0] == "36-45"
    assert f["top_category"][0] == "Auto"
    assert f["top_state_by_orders"] == ("Delhi", 6)
    assert f["top3_states_share"] == pytest.approx(100, abs=0.02)


def test_findings_reject_empty_frame(tiny_clean):
    with pytest.raises(ValueError):
        report.compute_findings(tiny_clean.iloc[0:0])


def test_markdown_contains_real_numbers(tiny_clean):
    text = report.render_markdown(report.compute_findings(tiny_clean), rows_dropped=2)
    assert "Top state by amount: Delhi with 900 (47.37% of the total)" in text
    assert "2 rows were dropped" in text
    assert "| Delhi | 6 | 900 | 47.37 |" in text


def test_charts_are_written(tiny_clean, tmp_path):
    paths = charts.save_all(tiny_clean, tmp_path / "out")
    assert len(paths) == 6
    for path in paths:
        assert path.exists() and path.stat().st_size > 1000
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_cli_report(tiny_csv, tmp_path, capsys):
    md = tmp_path / "findings.md"
    code = cli.main(
        [
            "report",
            "--csv",
            str(tiny_csv),
            "--charts-dir",
            str(tmp_path / "c"),
            "--markdown",
            str(md),
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "rows read:               6" in out
    assert md.read_text().startswith("# Findings")
    assert len(list((tmp_path / "c").glob("*.png"))) == 6


def test_cli_missing_file_returns_error(tmp_path, capsys):
    assert cli.main(["report", "--csv", str(tmp_path / "none.csv")]) == 1
    assert "error:" in capsys.readouterr().err


def test_cli_empty_file_returns_error(tmp_path, capsys):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert cli.main(["report", "--csv", str(empty)]) == 1
    assert "empty" in capsys.readouterr().err


def test_cli_missing_column_returns_error(tiny_raw, tmp_path, capsys):
    path = tmp_path / "bad.csv"
    tiny_raw.drop(columns=["State"]).to_csv(path, index=False)
    assert cli.main(["report", "--csv", str(path)]) == 1
    assert "state" in capsys.readouterr().err


def test_cli_load_db_without_url_returns_error(tiny_csv, monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert cli.main(["load-db", "--csv", str(tiny_csv)]) == 1
    assert "DATABASE_URL" in capsys.readouterr().err


def test_cli_load_db_and_sql(engine, tiny_csv, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", engine.url.render_as_string(hide_password=False))
    assert cli.main(["load-db", "--csv", str(tiny_csv)]) == 0
    assert "loaded 6 rows" in capsys.readouterr().out
    assert cli.main(["sql", "sql/01_by_state.sql"]) == 0
    assert "Delhi" in capsys.readouterr().out
