"""Shared fixtures for expressiveness implementations."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

_EXPR = Path(__file__).resolve().parent
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

import agent_spec_kit as ek

from shared.scripted_agent import scripted_agent
from shared.store_sim import insert_ticket

_TELECOM = Path(__file__).resolve().parent.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402


def _make_store(seed: str):
    base = Path(tempfile.mkdtemp(prefix="expr_store_"))
    telco = TelcoStore(base / "telco.sqlite")
    apply_seed(telco, seed)
    return telco, base


@ek.fixture
async def store_c11():
    telco, base = _make_store("task_T04")
    try:
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def store_c12():
    telco, base = _make_store("task_T46")
    try:
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def agent_c01():
    yield scripted_agent("C01")


@ek.fixture
async def agent_c02():
    yield scripted_agent("C02")


@ek.fixture
async def agent_c03():
    yield scripted_agent("C03")


@ek.fixture
async def agent_c04():
    yield scripted_agent("C04")


@ek.fixture
async def agent_c05():
    yield scripted_agent("C05")


@ek.fixture
async def agent_c06():
    yield scripted_agent("C06")


@ek.fixture
async def agent_c07():
    yield scripted_agent("C07")


@ek.fixture
async def agent_c08():
    yield scripted_agent("C08")


@ek.fixture
async def agent_c09():
    yield scripted_agent("C09")


@ek.fixture
async def agent_c10():
    yield scripted_agent("C10")


@ek.fixture
async def agent_c11():
    yield scripted_agent("C11")


@ek.fixture
async def agent_c12():
    yield scripted_agent("C12")
