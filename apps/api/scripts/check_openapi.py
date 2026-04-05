"""Validate generated OpenAPI contract is up to date."""

from __future__ import annotations

import json
from pathlib import Path

from legions_api.main import app


def main() -> None:
    """Fail when shared OpenAPI snapshot diverges from current backend schemas."""

    openapi_path = Path(__file__).resolve().parents[3] / "packages" / "shared-schema" / "openapi.json"
    if not openapi_path.exists():
        raise SystemExit(f"missing contract snapshot: {openapi_path}")

    expected = app.openapi()
    actual = json.loads(openapi_path.read_text(encoding="utf-8"))
    if expected != actual:
        raise SystemExit("OpenAPI snapshot is outdated. Run: PYTHONPATH=apps/api/src python apps/api/scripts/export_openapi.py")


if __name__ == "__main__":
    main()
