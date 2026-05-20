"""Pytest configuration for expressiveness benchmark."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parent
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

# agent_spec_kit scenarios run via `agent-spec-kit run`, not plain pytest.
collect_ignore = ["implementations/agent_spec_kit"]
