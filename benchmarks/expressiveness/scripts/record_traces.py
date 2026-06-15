#!/usr/bin/env python3
"""Record golden traces from the live reference agent (requires OPENAI_API_KEY)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[1]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from catalog import SPECIMENS
from specimens import messages as msg
from shared.run_agent import record_trace

_PROMPTS: dict[str, tuple[str, str]] = {
    "C01": ("task_T16", msg.msg_c01()),
    "C02": ("task_T09", msg.msg_c02()),
    "C03": ("task_T23", msg.msg_c03()),
    "C04": ("task_T23", msg.msg_c04()),
    "C05": ("task_T02", msg.msg_c05()),
    "C06": ("task_T49", msg.msg_c06()),
    "C07": ("task_T01", msg.msg_c07()),
    "C08": ("task_T10", msg.msg_c08()),
    "C09": ("task_T40", msg.msg_c09()),
    "C10": ("task_T06", msg.msg_c10()),
    "C11": ("task_T04", msg.msg_c11_turn1()),
}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="append", help="Check id(s) to record (default: C02-C11)")
    args = parser.parse_args()
    targets = args.check or [s.check_id for s in SPECIMENS if not s.needs_llm and s.check_id != "C12"]
    for cid in targets:
        if cid not in _PROMPTS:
            print(f"skip {cid}: no live prompt mapping")
            continue
        seed, prompt = _PROMPTS[cid]
        path = await record_trace(cid, seed, prompt)
        print(f"recorded {cid} -> {path}")


if __name__ == "__main__":
    asyncio.run(main())
