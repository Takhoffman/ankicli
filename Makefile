.PHONY: lint build test-fast test-unit test-smoke test-fixture-integration test-e2e test-distribution test-all

lint:
	uv run ruff check .

build:
	uv build

test-fast:
	uv run pytest -m "unit or smoke"

test-unit:
	uv run pytest -m unit

test-smoke:
	uv run pytest -m smoke

test-fixture-integration:
	uv run pytest tests/integration/test_python_anki_backend.py

test-e2e:
	uv run pytest tests/e2e/test_cli_e2e.py

test-distribution:
	uv build
	uv run pytest -m distribution

test-all:
	uv run pytest
