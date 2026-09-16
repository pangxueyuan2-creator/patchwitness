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
	python scripts/release_check.py
