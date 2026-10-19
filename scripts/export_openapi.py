"""Write the API's OpenAPI spec to a file, without starting a server.

The frontend generates its TypeScript types from this file:
    uv run python -m scripts.export_openapi web/openapi.json
"""

import json
import sys
from pathlib import Path

from main import app


def main(path: str) -> None:
    Path(path).write_text(json.dumps(app.openapi(), indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "web/openapi.json")
