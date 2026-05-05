#!/usr/bin/env python3
"""Export OpenAPI schema from FastAPI app to JSON file."""

import json
import sys
from pathlib import Path

# Add server to path
server_path = Path(__file__).parent
src_path = server_path.parent
sys.path.insert(0, str(src_path))

from api.main import app

def main():
    """Generate OpenAPI JSON schema."""
    openapi_schema = app.openapi()
    
    output_path = server_path / "openapi.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, sort_keys=True, ensure_ascii=False)
    
    print(f"OpenAPI schema exported to {output_path}")

if __name__ == "__main__":
    main()