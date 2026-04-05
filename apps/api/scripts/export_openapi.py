"""Export backend OpenAPI contract for shared-schema consumers."""

from __future__ import annotations

import json
from pathlib import Path

from legions_api.main import app


def main() -> None:
    """Write OpenAPI document to packages/shared-schema/openapi.json."""

    output_path = Path(__file__).resolve().parents[3] / "packages" / "shared-schema" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
