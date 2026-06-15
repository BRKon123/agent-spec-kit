#!/usr/bin/env python3
"""Extract manual-script user messages into tasks/fuzzing/seeds/TXX.json (review before commit)."""

from __future__ import annotations

import importlib
import inspect
import json
import re
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
SEEDS_DIR = BENCH / "tasks" / "fuzzing" / "seeds"

TASKS = (
    "T03",
    "T04",
    "T17",
    "T20",
    "T27",
    "T29",
    "T30",
    "T35",
    "T38",
    "T42",
    "T43",
    "T44",
    "T45",
    "T49",
)

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))


def _collect_msg_functions(mod: object) -> list[tuple[str, object]]:
    fns: list[tuple[str, object]] = []
    for name, obj in inspect.getmembers(mod, inspect.isfunction):
        if re.fullmatch(r"_msg\d*", name):
            fns.append((name, obj))
    fns.sort(key=lambda x: (len(x[0]), x[0]))
    return fns


def extract_task(task_id: str) -> dict[str, object]:
    import shutil
    import tempfile

    from store.seeds import apply_seed
    from store.store import TelcoStore

    mod = importlib.import_module(f"tasks.manual.test_{task_id}")
    base = Path(tempfile.mkdtemp(prefix="fuzz_seed_extract_"))
    try:
        store = TelcoStore(base / "telco.sqlite")
        apply_seed(store, f"task_{task_id}")
        messages: list[str] = []
        for name, fn in _collect_msg_functions(mod):
            try:
                sig = inspect.signature(fn)
                if len(sig.parameters) >= 1:
                    text = fn(store)
                else:
                    text = fn()
            except TypeError:
                text = fn(store)
            if isinstance(text, str) and text.strip():
                messages.append(text.strip())
        return {
            "task_id": task_id,
            "seed_source": "manual_script",
            "messages": messages,
            "extracted_from": f"tasks/manual/test_{task_id}.py",
        }
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main() -> int:
    SEEDS_DIR.mkdir(parents=True, exist_ok=True)
    for task_id in TASKS:
        payload = extract_task(task_id)
        out = SEEDS_DIR / f"{task_id}.json"
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out} ({len(payload['messages'])} messages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
