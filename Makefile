.PHONY: lint build test-fast test-unit test-smoke test-fixture-integration test-e2e test-distribution test-all real-backend-setup ankiconnect-backend-setup

lint:
	UV_CACHE_DIR=.uv-cache uv run ruff check .

build:
	UV_CACHE_DIR=.uv-cache uv build

test-fast:
	UV_CACHE_DIR=.uv-cache uv run pytest -m "unit or smoke"

test-unit:
	UV_CACHE_DIR=.uv-cache uv run pytest -m unit

test-smoke:
	UV_CACHE_DIR=.uv-cache uv run pytest -m smoke

test-fixture-integration:
	UV_CACHE_DIR=.uv-cache uv run pytest tests/integration/test_python_anki_backend.py

test-e2e:
	UV_CACHE_DIR=.uv-cache uv run pytest tests/e2e/test_cli_e2e.py

test-distribution:
	UV_CACHE_DIR=.uv-cache uv build
	UV_CACHE_DIR=.uv-cache uv run pytest -m distribution

test-all:
	UV_CACHE_DIR=.uv-cache uv run pytest

real-backend-setup:
	UV_CACHE_DIR=.uv-cache uv run python scripts/prepare_real_backend.py

ankiconnect-backend-setup:
	UV_CACHE_DIR=.uv-cache uv run python scripts/prepare_ankiconnect_backend.py
