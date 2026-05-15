"""Nested tool-oracle example: ordering, children, conditional args, LLM rubrics.

Requires ``OPENAI_API_KEY`` and the LangChain stack (project ``dependency-groups`` dev).

Run from repo root::

    OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_nested_tool_oracle/

Expected-failure demos (counterexamples)::

    uv run agent-spec-kit run examples/langchain_nested_tool_oracle/ --tags expected-failure

Unordered parallel sibling tools::

    uv run agent-spec-kit run examples/langchain_nested_tool_oracle/ --tags parallel-unordered
"""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "nested-tool-oracle", "smoke"),
    timeout_s=180.0,
)
async def test_incident_triage_oracle(s):
    """Ordered root trace, nested children, conditional args, LLM rubrics on tool results."""
    (
        s.user_message(
            "Triage incident INC-2026-0142: high-severity latency on edge and core. "
            "Run the full coordinator policy (open, parallel forensics + heartbeat), "
            "then summarize."
        )
        .assert_tool_calls(
            [
                m.tool_call(
                    "open_incident",
                    args=m.object(
                        {
                            "ticket": m.object(
                                {
                                    "id": m.regex(r"INC-\d{4}-\d+"),
                                    "severity": m.one_of("high", "medium"),
                                    "pager_group": m.optional(m.string(min_len=1)),
                                    "components": m.list(
                                        ["edge", "core"],
                                        mode="unordered",
                                        allow_extras=False,
                                    ),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("pager_group").when(m.field("severity") == "high"),
                                    m.forbid("pager_group").when(m.field("severity") == "medium"),
                                ],
                            )
                        },
                        extra="forbid",
                    ),
                ),
                m.tool_call(
                    "run_forensics_specialist",
                    args={"query": m.contains("latency")},
                    children=[
                        m.tool_call(
                            "pull_logs",
                            args=m.object(
                                {"window_minutes": m.number(min=15, max=15, int_only=True)},
                                extra="forbid",
                            ),
                        ),
                        m.tool_call(
                            "score_anomaly",
                            args=m.object(
                                {
                                    "source": m.one_of("logs", "synthetic"),
                                    "anomaly_score": m.number(min=0, max=1),
                                    "window_minutes": m.optional(
                                        m.number(min=5, max=60, int_only=True)
                                    ),
                                    "override_reason": m.optional(m.string(min_len=1)),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("window_minutes").when(m.field("source") == "logs"),
                                    m.forbid("override_reason").when(m.field("source") == "logs"),
                                ],
                            ).where(
                                lambda o: o["anomaly_score"] >= 0.5,
                                "anomaly_score must be at least 0.5 for escalation",
                            ),
                            result=m.llm_criteria(
                                criteria=[
                                    "mentions a numeric anomaly score or risk band",
                                    "does not state root cause as certain fact",
                                ],
                                threshold=2,
                                model="openai:gpt-5-nano",
                            ),
                        ),
                    ],
                    result=m.llm_criteria(
                        criteria=[
                            "summarizes log window or minutes analyzed",
                            "includes a recommended next step",
                        ],
                        threshold=2,
                        model="openai:gpt-5-nano",
                    ),
                ),
                m.tool_call("heartbeat_ping"),
            ],
            ordered=True,
            allow_extras=True,
        )
        .assert_output(m.contains("heartbeat"))
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "nested-tool-oracle", "parallel-unordered"),
    timeout_s=180.0,
)
async def test_incident_parallel_siblings_unordered(s):
    """Turn 1 opens incident; turn 2 asserts parallel siblings with order-free matching."""
    (
        s.user_message(
            "Open incident INC-2026-0142 only: high severity, pager_group net-oncall, "
            'components ["edge", "core"]. Do not run forensics yet.'
        )
        .assert_tool_calls(
            [
                m.tool_call(
                    "open_incident",
                    args=m.object(
                        {
                            "ticket": m.object(
                                {
                                    "id": m.regex(r"INC-\d{4}-\d+"),
                                    "severity": m.one_of("high", "medium"),
                                    "pager_group": m.optional(m.string(min_len=1)),
                                    "components": m.list(
                                        ["edge", "core"],
                                        mode="unordered",
                                        allow_extras=False,
                                    ),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("pager_group").when(m.field("severity") == "high"),
                                    m.forbid("pager_group").when(m.field("severity") == "medium"),
                                ],
                            )
                        },
                        extra="forbid",
                    ),
                ),
            ],
            ordered=True,
            allow_extras=False,
        )
        .user_message(
            "Now call run_forensics_specialist with a query mentioning latency AND "
            "heartbeat_ping in the same step. Brief reply only."
        )
        .assert_tool_calls(
            [
                m.tool_call("run_forensics_specialist"),
                m.tool_call("heartbeat_ping"),
            ],
            ordered=False,
            allow_extras=True,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent_failure_mode",
    repeats=1,
    tags=("langchain", "example", "nested-tool-oracle", "expected-failure"),
    timeout_s=180.0,
)
async def test_incident_wrong_nested_order(s):
    """Specialist calls score_anomaly before pull_logs; oracle expects policy order."""
    (
        s.user_message(
            "Open INC-2026-0142 high with pager net-oncall and components edge/core. "
            "Delegate forensics with query about latency, but instruct the specialist to call "
            "score_anomaly BEFORE pull_logs with source=logs, window_minutes=15, "
            "anomaly_score=0.72. "
            "Also heartbeat_ping in parallel with forensics."
        )
        .assert_tool_calls(
            [
                m.tool_call(
                    "open_incident",
                    args=m.object(
                        {
                            "ticket": m.object(
                                {
                                    "id": m.regex(r"INC-\d{4}-\d+"),
                                    "severity": m.one_of("high", "medium"),
                                    "pager_group": m.optional(m.string(min_len=1)),
                                    "components": m.list(
                                        ["edge", "core"],
                                        mode="unordered",
                                        allow_extras=False,
                                    ),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("pager_group").when(m.field("severity") == "high"),
                                    m.forbid("pager_group").when(m.field("severity") == "medium"),
                                ],
                            )
                        },
                        extra="forbid",
                    ),
                ),
                m.tool_call(
                    "run_forensics_specialist",
                    children=[
                        m.tool_call(
                            "pull_logs",
                            args=m.object(
                                {"window_minutes": m.number(min=15, max=15, int_only=True)},
                                extra="forbid",
                            ),
                        ),
                        m.tool_call(
                            "score_anomaly",
                            args=m.object(
                                {
                                    "source": m.one_of("logs", "synthetic"),
                                    "anomaly_score": m.number(min=0, max=1),
                                    "window_minutes": m.optional(
                                        m.number(min=5, max=60, int_only=True)
                                    ),
                                    "override_reason": m.optional(m.string(min_len=1)),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("window_minutes").when(m.field("source") == "logs"),
                                    m.forbid("override_reason").when(m.field("source") == "logs"),
                                ],
                            ).where(
                                lambda o: o["anomaly_score"] >= 0.5,
                                "anomaly_score must be at least 0.5 for escalation",
                            ),
                        ),
                    ],
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent_failure_mode",
    repeats=1,
    tags=("langchain", "example", "nested-tool-oracle", "expected-failure"),
    timeout_s=180.0,
)
async def test_incident_missing_pager_on_high(s):
    """High severity without pager_group violates conditional require rule on ticket args."""
    (
        s.user_message(
            "Open incident with ticket "
            '{"id":"INC-2026-0142","severity":"high","components":["edge","core"]} '
            "and do NOT include pager_group. Then stop."
        )
        .assert_tool_calls(
            [
                m.tool_call(
                    "open_incident",
                    args=m.object(
                        {
                            "ticket": m.object(
                                {
                                    "id": m.regex(r"INC-\d{4}-\d+"),
                                    "severity": m.one_of("high", "medium"),
                                    "pager_group": m.optional(m.string(min_len=1)),
                                    "components": m.list(
                                        ["edge", "core"],
                                        mode="unordered",
                                        allow_extras=False,
                                    ),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("pager_group").when(m.field("severity") == "high"),
                                    m.forbid("pager_group").when(m.field("severity") == "medium"),
                                ],
                            )
                        },
                        extra="forbid",
                    ),
                ),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent_failure_mode",
    repeats=1,
    tags=("langchain", "example", "nested-tool-oracle", "expected-failure"),
    timeout_s=180.0,
)
async def test_incident_logs_without_window(s):
    """source=logs without window_minutes violates conditional require on score_anomaly args."""
    (
        s.user_message(
            "Open INC-2026-0142 high with pager net-oncall, components edge/core. "
            "Run forensics (latency query) telling the specialist: call pull_logs with 15, "
            "then score_anomaly with source=logs and anomaly_score=0.72 only "
            "(omit window_minutes)."
        )
        .assert_tool_calls(
            [
                m.tool_call(
                    "open_incident",
                    args=m.object(
                        {
                            "ticket": m.object(
                                {
                                    "id": m.regex(r"INC-\d{4}-\d+"),
                                    "severity": m.one_of("high", "medium"),
                                    "pager_group": m.optional(m.string(min_len=1)),
                                    "components": m.list(
                                        ["edge", "core"],
                                        mode="unordered",
                                        allow_extras=False,
                                    ),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("pager_group").when(m.field("severity") == "high"),
                                    m.forbid("pager_group").when(m.field("severity") == "medium"),
                                ],
                            )
                        },
                        extra="forbid",
                    ),
                ),
                m.tool_call(
                    "run_forensics_specialist",
                    children=[
                        m.tool_call(
                            "pull_logs",
                            args=m.object(
                                {"window_minutes": m.number(min=15, max=15, int_only=True)},
                                extra="forbid",
                            ),
                        ),
                        m.tool_call(
                            "score_anomaly",
                            args=m.object(
                                {
                                    "source": m.one_of("logs", "synthetic"),
                                    "anomaly_score": m.number(min=0, max=1),
                                    "window_minutes": m.optional(
                                        m.number(min=5, max=60, int_only=True)
                                    ),
                                    "override_reason": m.optional(m.string(min_len=1)),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("window_minutes").when(m.field("source") == "logs"),
                                    m.forbid("override_reason").when(m.field("source") == "logs"),
                                ],
                            ).where(
                                lambda o: o["anomaly_score"] >= 0.5,
                                "anomaly_score must be at least 0.5 for escalation",
                            ),
                        ),
                    ],
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )
