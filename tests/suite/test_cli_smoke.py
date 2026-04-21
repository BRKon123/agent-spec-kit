"""CLI smoke tests (subprocess)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _env() -> dict[str, str]:
    env = dict(os.environ)
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    return env


def test_cli_list_discovers_scenario(tmp_path: Path) -> None:
    (tmp_path / "fixtures.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek
from agent_spec_kit.run import TurnResult

@ek.fixture
async def agent():
    class A:
        async def run_turn(self, user_message: str) -> TurnResult:
            return TurnResult(output="ok", events=())
    return A()
""",
        encoding="utf-8",
    )
    (tmp_path / "test_smoke.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek

@ek.scenario(agent_fixture="agent", tags=("smoke",))
async def test_smoke(s):
    s.user_message("hi")
    await s.materialise()
""",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, "-m", "agent_spec_kit.cli", "run", str(tmp_path), "--list"],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "test_smoke" in out
    assert "smoke" in out


def test_cli_run_passes(tmp_path: Path) -> None:
    (tmp_path / "fixtures.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek
from agent_spec_kit.run import TurnResult

@ek.fixture
async def agent():
    class A:
        async def run_turn(self, user_message: str) -> TurnResult:
            return TurnResult(output="ok", events=())
    return A()
""",
        encoding="utf-8",
    )
    (tmp_path / "test_run.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek

@ek.scenario(agent_fixture="agent", repeats=1, tags=())
async def test_run(s):
    s.user_message("hi")
    await s.materialise()
""",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, "-m", "agent_spec_kit.cli", "run", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "test_run" in r.stdout
    assert "1 passed" in r.stdout


def test_cli_tags_filter(tmp_path: Path) -> None:
    (tmp_path / "fixtures.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek
from agent_spec_kit.run import TurnResult

@ek.fixture
async def agent():
    class A:
        async def run_turn(self, user_message: str) -> TurnResult:
            return TurnResult(output="ok", events=())
    return A()
""",
        encoding="utf-8",
    )
    (tmp_path / "test_tags.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek

@ek.scenario(agent_fixture="agent", tags=("onlyme",))
async def tagged(s):
    pass

@ek.scenario(agent_fixture="agent", tags=("other",))
async def other(s):
    pass
""",
        encoding="utf-8",
    )
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent_spec_kit.cli",
            "run",
            str(tmp_path),
            "--list",
            "--tags",
            "onlyme",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    assert r.returncode == 0, r.stderr
    assert "tagged" in r.stdout
    assert "other" not in r.stdout


def test_cli_parallel_workers(tmp_path: Path) -> None:
    (tmp_path / "fixtures.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek
from agent_spec_kit.run import TurnResult

@ek.fixture
async def agent():
    class A:
        async def run_turn(self, user_message: str) -> TurnResult:
            return TurnResult(output="ok", events=())
    return A()
""",
        encoding="utf-8",
    )
    (tmp_path / "test_parallel.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek

@ek.scenario(agent_fixture="agent", repeats=1, tags=())
async def test_one(s):
    pass

@ek.scenario(agent_fixture="agent", repeats=1, tags=())
async def test_two(s):
    pass
""",
        encoding="utf-8",
    )
    r = subprocess.run(
        [sys.executable, "-m", "agent_spec_kit.cli", "run", str(tmp_path), "-n", "2"],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
    )
    assert r.returncode == 0, r.stderr + r.stdout
    assert "test_one" in r.stdout
    assert "test_two" in r.stdout
    assert "2 passed" in r.stdout
