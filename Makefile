PYTHON ?= python

.PHONY: install test lint fmt

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check atlas cli tests

fmt:
	$(PYTHON) -m ruff format atlas cli tests
