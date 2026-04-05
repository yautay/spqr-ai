set shell := ["bash", "-cu"]

default:
    @just --list

bootstrap:
    @if [ -f apps/api/requirements-dev.txt ]; then python -m pip install -r apps/api/requirements-dev.txt; fi
    @if [ -f apps/web/package.json ]; then npm --prefix apps/web install; fi

contracts-generate:
    @if [ -f apps/api/scripts/export_openapi.py ]; then PYTHONPATH=apps/api/src python apps/api/scripts/export_openapi.py; fi

contracts-check:
    @if [ -f apps/api/scripts/check_openapi.py ]; then PYTHONPATH=apps/api/src python apps/api/scripts/check_openapi.py; fi

lint:
    @if [ -d apps/api ]; then python -m ruff check apps/api; fi
    @if [ -d apps/web ]; then npm --prefix apps/web run lint; fi

format:
    @if [ -d apps/api ]; then python -m ruff format apps/api; fi
    @if [ -d apps/web ]; then npm --prefix apps/web run format; fi

format-check:
    @if [ -d apps/api ]; then python -m ruff format --check apps/api; fi
    @if [ -d apps/web ]; then npm --prefix apps/web run format:check; fi

typecheck:
    @if [ -d apps/api ]; then python -m mypy apps/api/src; fi
    @if [ -d apps/web ]; then npm --prefix apps/web run typecheck; fi

test:
    @if [ -d apps/api ]; then python -m pytest apps/api/tests; fi
    @if [ -d apps/web ]; then npm --prefix apps/web run test:run; fi

security:
    @if [ -d apps/api/src ]; then python -m bandit -q -r apps/api/src; fi
    @if [ -f apps/api/requirements-dev.txt ]; then python -m pip_audit -r apps/api/requirements-dev.txt; fi
    @if [ -f apps/web/package.json ]; then npm --prefix apps/web audit --audit-level=high; fi

check: contracts-check lint format-check typecheck test security

run-api:
    @if [ -d apps/api/src ]; then python -m uvicorn legions_api.main:app --app-dir apps/api/src --reload; fi

run-web:
    @if [ -f apps/web/package.json ]; then npm --prefix apps/web run dev; fi
