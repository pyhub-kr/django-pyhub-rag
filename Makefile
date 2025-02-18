.PHONY: test clean build publish

test:
	uv pip install -e ".[test]"
	uv run pytest tests/

format:
	uv pip install -e ".[dev]"
	uv run black .
	uv run isort .
	uv run ruff check . --fix
	uv run djlint . --reformat

lint:
	uv pip install -e ".[dev]"
	uv run black . --check
	uv run isort . --check
	uv run ruff check .
	uv run djlint . --check

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf src/*.egg-info

build: clean
	uv pip install -e ".[build]"
	uv run -m build --wheel

publish: build
	uv run -m twine upload dist/*
