.PHONY: test lint types build check benchmark

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

