PY ?= .venv/bin/python

.PHONY: setup lint format test report load-db-local

setup:
	python3 -m venv .venv
	$(PY) -m pip install -r requirements-dev.txt -r requirements-local.txt

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff format .

test:
	$(PY) -m pytest

report:
	$(PY) -m festival_sales report --markdown docs/findings.md

load-db-local:
	$(PY) -m festival_sales load-db --local
