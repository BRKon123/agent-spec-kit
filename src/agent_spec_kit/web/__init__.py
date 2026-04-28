"""Read-only web UI for browsing run results.

Importing this submodule requires the ``[ui]`` optional dependencies
(``fastapi``, ``uvicorn``).
"""

from __future__ import annotations

__all__ = ["create_app", "DIST_DIR"]

from agent_spec_kit.web.server import DIST_DIR, create_app
