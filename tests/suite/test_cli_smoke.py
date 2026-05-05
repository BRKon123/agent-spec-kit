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


def _run_cli(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "agent_spec_kit.cli", *args],
        capture_output=True,
        text=True,
        check=False,
        env=_env(),
        cwd=cwd,
    )


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
    r = _run_cli(["run", str(tmp_path), "--list"], cwd=tmp_path)
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
    r = _run_cli(["run", str(tmp_path)], cwd=tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "PASS test_run [1/1]" in r.stdout
    assert "progress: test_run [1/1]: repeat started" in r.stderr
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
    r = _run_cli(["run", str(tmp_path), "--list", "--tags", "onlyme"], cwd=tmp_path)
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
    r = _run_cli(["run", str(tmp_path), "-n", "2"], cwd=tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    assert r.stdout.count("PASS ") >= 2
    assert "PASS test_one [1/1]" in r.stdout or "PASS test_two [1/1]" in r.stdout
    assert "progress:" in r.stderr
    assert "test_one" in r.stdout
    assert "test_two" in r.stdout
    assert "2 passed" in r.stdout


def test_cli_run_metadata_validation(tmp_path: Path) -> None:
    r = _run_cli(["run", str(tmp_path), "--metadata", "bad"], cwd=tmp_path)
    assert r.returncode == 2
    assert "expected key=value" in r.stderr


def test_cli_runs_and_show(tmp_path: Path) -> None:
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

@ek.scenario(agent_fixture="agent", repeats=1, tags=("telecom",))
async def test_run(s):
    s.user_message("hello")
    await s.materialise()
""",
        encoding="utf-8",
    )
    run = _run_cli(
        [
            "run",
            str(tmp_path),
            "--experiment",
            "telecom-agent",
            "--metadata",
            "model_family=gpt",
            "--metadata",
            "prompt_version=v3",
            "--notes",
            "tracking notes",
        ],
        cwd=tmp_path,
    )
    assert run.returncode == 0, run.stderr + run.stdout

    runs = _run_cli(["runs"], cwd=tmp_path)
    assert runs.returncode == 0
    assert "telecom-agent" in runs.stdout
    assert "scenarios" in runs.stdout
    run_id = runs.stdout.split()[0]

    show = _run_cli(["show", run_id], cwd=tmp_path)
    assert show.returncode == 0
    assert f"Run: {run_id}" in show.stdout
    assert "Experiment: telecom-agent" in show.stdout
    assert "Notes: tracking notes" in show.stdout


def test_cli_progress_non_generative_includes_param_labels(tmp_path: Path) -> None:
    (tmp_path / "fixtures.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek
from agent_spec_kit.run import TurnResult

@ek.fixture
@ek.parametrize("model", (ek.case("a", id="m_a"), ek.case("b", id="m_b")))
async def agent(model: str):
    class A:
        async def run_turn(self, user_message: str) -> TurnResult:
            return TurnResult(output=f"{model}:{user_message}", events=())
    return A()
""",
        encoding="utf-8",
    )
    (tmp_path / "test_param_progress.py").write_text(
        """
from __future__ import annotations
import agent_spec_kit as ek

@ek.scenario(agent_fixture="agent", repeats=1, tags=())
async def test_param_progress(s):
    s.user_message("hello")
    await s.materialise()
""",
        encoding="utf-8",
    )
    r = _run_cli(["run", str(tmp_path)], cwd=tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    assert "progress: test_param_progress (model=m_a) [1/1]: repeat started" in r.stderr
    assert "progress: test_param_progress (model=m_b) [1/1]: repeat started" in r.stderr
