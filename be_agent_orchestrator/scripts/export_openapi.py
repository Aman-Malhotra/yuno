"""Dump the live OpenAPI schema to ``docs/openapi.json`` (and .yaml if PyYAML).

Run via ``make openapi``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running as `python scripts/export_openapi.py` from project root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.main import app  # noqa: E402


def main() -> None:
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)

    schema = app.openapi()

    json_path = docs_dir / "openapi.json"
    json_path.write_text(json.dumps(schema, indent=2, sort_keys=False) + "\n")
    print(f"wrote {json_path.relative_to(docs_dir.parent)}")

    try:
        import yaml  # type: ignore[import-not-found]

        yaml_path = docs_dir / "openapi.yaml"
        yaml_path.write_text(yaml.safe_dump(schema, sort_keys=False))
        print(f"wrote {yaml_path.relative_to(docs_dir.parent)}")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
