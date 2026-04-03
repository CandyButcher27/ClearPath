"""
Startup script for the ClearPath API server.

Adds project root, DocStruct/, and backend/ to sys.path before importing
anything from those packages, so relative imports work correctly.

Usage:
    cd <project_root>
    python api/run.py

The API will be available at http://localhost:8000
"""
import sys
from pathlib import Path

# Make DocStruct and backend importable by name
_project_root = Path(__file__).parent.parent
_docstruct_dir = _project_root / "DocStruct"
_backend_dir = _project_root / "backend"

for _p in [str(_project_root), str(_docstruct_dir), str(_backend_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
