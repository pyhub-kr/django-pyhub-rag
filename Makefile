.PHONY: test clean build publish

test:
	uv pip install -e ".[test,postgres,sqlite]"
	uv run pytest $(filter-out $@,$(MAKECMDGOALS))

format:
	uv pip install -e ".[dev]"
	uv run black ./src ./tests
	uv run isort ./src ./tests
	uv run ruff check ./src ./tests --fix
	uv run djlint ./src ./tests --reformat

lint:
	uv pip install -e ".[dev]"
	uv run black ./src ./tests --check
	uv run isort ./src ./tests --check
	uv run ruff check ./src ./tests
	uv run djlint ./src ./tests --check

clean:
	rm -rf dist/
	rm -rf build/
	rm -rf src/*.egg-info

build: clean
	uv pip install -e ".[build]"
	uv run -m build --wheel

publish: build
	uv run -m twine upload dist/*
