.PHONY: setup demo test lint test-demo test-production clean

VENV ?= artifacts/.venv
VENV_PY := $(VENV)/bin/python
PYTHONPATH := src

setup:
	mkdir -p artifacts
	python3 -m venv $(VENV)
	$(VENV_PY) -c "import sys; print(sys.version)"

demo: setup
	PYTHONPATH=$(PYTHONPATH) $(VENV_PY) -m portfolio_proof validate
	PYTHONPATH=$(PYTHONPATH) $(VENV_PY) -m portfolio_proof report --out artifacts/report.md

test: setup
	PYTHONPATH=$(PYTHONPATH) $(VENV_PY) -m unittest discover -s tests -v

lint: setup
	PYTHONPATH=$(PYTHONPATH) $(VENV_PY) -m compileall -q src tests
	PYTHONPATH=$(PYTHONPATH) $(VENV_PY) -m portfolio_proof lint

test-demo: setup
	TEST_MODE=demo python3 tests/run_tests.py

test-production: setup
	TEST_MODE=production PRODUCTION_TESTS_CONFIRM=1 python3 tests/run_tests.py

clean:
	rm -rf artifacts $(VENV)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
