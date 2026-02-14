#!/usr/bin/env python3
"""Script to extract OpenAPI specification from Django Ninja API.

Extracts the OpenAPI spec without needing a running server instance.
"""

import json
import os
import sys
from pathlib import Path

import django

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
repo_root = project_root.parent.parent
# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_showcase.settings")
django.setup()

from api.main import api


def extract_openapi_spec() -> bool:
    """Extract OpenAPI specification from Django Ninja API."""
    try:
        # Get the OpenAPI schema
        openapi_schema = api.get_openapi_schema()

        # Convert to JSON string with proper formatting
        openapi_json = json.dumps(openapi_schema, indent=2, ensure_ascii=False)

        # Write to file
        output_file = repo_root / "src" / "web-ui" / "backend-openapi.json"
        output_file.write_text(openapi_json, encoding="utf-8")

    except Exception:  # noqa: BLE001
        return False
    else:
        return True


if __name__ == "__main__":
    success = extract_openapi_spec()
    sys.exit(0 if success else 1)
