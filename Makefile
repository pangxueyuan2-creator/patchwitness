.PHONY: test lint types build check benchmark release-check

test:
	python -m pytest

lint:
	ruff check src tests

types:
	mypy src

build:
	python -m build

check: test lint types build

benchmark:
	patchwitness benchmark --files 250 --rounds 7

release-check:
	python -m pytest --cov=patchwitness --cov-report=term-missing --cov-fail-under=80
	ruff check src tests
	mypy src
	python demo/run_demo.py
	python benchmarks/change-risk/run.py
	python -m build
	twine check dist/*
	python -m venv /tmp/patchwitness-release-check
	/tmp/patchwitness-release-check/bin/pip install --disable-pip-version-check dist/*.whl
	/tmp/patchwitness-release-check/bin/patchwitness --version
