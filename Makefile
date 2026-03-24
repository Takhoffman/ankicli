.PHONY: lint build test-fast test-unit test-smoke test-fixture-integration test-e2e test-distribution test-all test-backup-real test-matrix real-backend-setup ankiconnect-backend-setup

PROOF_REPORT ?= /tmp/ankicli-proof-report.json
MATRIX_AUDIT_ARGS ?= --proof-report $(PROOF_REPORT)

lint:
	UV_CACHE_DIR=.uv-cache uv run ruff check .

build:
	UV_CACHE_DIR=.uv-cache uv build

test-fast:
	PYTEST_PLUGINS=ankicli.pytest_plugin UV_CACHE_DIR=.uv-cache uv run pytest -c pyproject.toml -m "unit or smoke" --proof-report $(PROOF_REPORT)

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

test-backup-real:
	UV_CACHE_DIR=.uv-cache uv run pytest -m backend_python_anki_backup_real

test-matrix:
	PYTEST_PLUGINS=ankicli.pytest_plugin UV_CACHE_DIR=.uv-cache uv run pytest -c pyproject.toml -m "unit or smoke" --proof-report $(PROOF_REPORT)
	UV_CACHE_DIR=.uv-cache uv run python scripts/audit_quality_matrix.py $(MATRIX_AUDIT_ARGS)

real-backend-setup:
	UV_CACHE_DIR=.uv-cache uv run python scripts/prepare_real_backend.py

ankiconnect-backend-setup:
	UV_CACHE_DIR=.uv-cache uv run python scripts/prepare_ankiconnect_backend.py
