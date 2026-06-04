#!/usr/bin/env python3
"""Count lines between CHECK_START and CHECK_END markers per framework file."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[1]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.check_snippets import loc_by_framework


def main() -> None:
    totals = loc_by_framework()
    for fw, counts in sorted(totals.items()):
        print(f"[{fw}]")
        for cid in sorted(counts):
            print(f"  {cid}: {counts[cid]}")


if __name__ == "__main__":
    main()
