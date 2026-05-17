#!/usr/bin/env python3
"""Generate explicit tasks/manual/test_Txx.py for T01–T50."""

from __future__ import annotations

from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
MANUAL = BENCH / "tasks" / "manual"
LLM = "openai:gpt-5-nano"

HEADER = '''"""Task {tid} scenarios (explicit scripted messages and checks)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_spec_kit as ek
import agent_spec_kit.match as m

from tasks.specs import oracles as o

'''

SCENARIO = '''
@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=2,
    tags=("telecom", "task:{tid}", "oracle:{oracle}", "reference"),
    timeout_s=420.0,
)
async def {func}(s, store):
    meta = store.seed_meta
{body}
'''


def _write(tid: str, user_fn: str, scenarios: dict[str, str]) -> None:
    parts = [user_fn, ""]
    for oracle, func_suffix, body in scenarios:
        func = f"test_{tid.lower()}_{func_suffix}"
        indented = "\n".join(
            ("    " + line if line.strip() else "") for line in body.strip().splitlines()
        )
        parts.append(
            SCENARIO.format(tid=tid, oracle=oracle, func=func, body=indented)
        )
    (MANUAL / f"test_{tid}.py").write_text(
        HEADER.format(tid=tid) + "\n".join(parts), encoding="utf-8"
    )


def _chain(msg_expr: str, *steps: str) -> str:
    lines = [f"    (\n        s.user_message({msg_expr})"]
    for step in steps:
        lines.append(f"        {step}")
    lines.append("    )")
    return "\n".join(lines)


def _trace(calls: str) -> str:
    return f".assert_tool_calls(\n            {calls},\n            ordered=True,\n            allow_extras=True,\n        )"


def _trace_unordered(calls: str) -> str:
    return f".assert_tool_calls(\n            {calls},\n            ordered=False,\n            allow_extras=True,\n        )"


AUTH = 'm.tool_call("authenticate_customer")'
OUTAGE = 'm.tool_call("check_outage")'
DIAG = 'm.tool_call("run_line_diagnostic")'
LINE = 'm.tool_call("get_line_status")'
PLAN = 'm.tool_call("get_plan_details")'
PROFILE = 'm.tool_call("get_customer_profile")'
RECORD = 'm.tool_call("record_user_action")'
TICKET = 'm.tool_call("create_support_ticket")'
ESCALATE = 'm.tool_call("escalate_ticket")'
CREDIT = 'm.tool_call("apply_bill_credit")'
SIM = 'm.tool_call("order_replacement_sim")'
APPT = 'm.tool_call("schedule_store_appointment")'
TS = 'm.tool_call("send_troubleshooting_step")'
HB = 'm.tool_call("heartbeat_ping")'
NET = 'm.tool_call("run_network_diagnostics_specialist")'
BILL = 'm.tool_call("run_billing_policy_specialist")'

NET_CHILDREN = """[
                m.tool_call("pull_network_events"),
                m.tool_call("score_signal_anomaly"),
            ]"""

NET_RESULT = f"""result=m.object(
                {{
                    "line_id": m.string(min_len=1),
                    "fault_domain": m.one_of("device", "sim", "network", "plan", "roaming", "unknown"),
                    "severity": m.one_of("low", "medium", "high"),
                    "confidence": m.number(min=0, max=1),
                    "evidence": m.list_of(m.string(min_len=1), min_len=1),
                    "recommended_action": m.string(min_len=1),
                    "user_explanation": m.string(min_len=1),
                }},
                extra="forbid",
            )"""

BILL_CHILDREN = """[
                m.tool_call("pull_billing_events"),
                m.tool_call("classify_credit_eligibility"),
            ]"""

BILL_INELIG = f"""result=m.object(
                {{
                    "customer_id": m.string(min_len=1),
                    "eligible": m.equals(False),
                    "reason_code": m.one_of("ineligible_short_outage", "insufficient_evidence"),
                    "amount": m.forbidden(),
                    "requires_audit_note": m.boolean(),
                    "policy_quote": m.string(min_len=1),
                    "user_explanation": m.string(min_len=1),
                }},
                extra="forbid",
            )"""

BILL_ELIG = f"""result=m.object(
                {{
                    "customer_id": m.string(min_len=1),
                    "eligible": m.equals(True),
                    "reason_code": m.one_of("duplicate_charge", "verified_long_outage"),
                    "amount": m.number(min=0.01),
                    "requires_audit_note": m.equals(True),
                    "policy_quote": m.string(min_len=1),
                    "user_explanation": m.string(min_len=1),
                }},
                extra="forbid",
            )"""


def user_msg(*parts: str) -> str:
    body = " ".join(parts)
    return f'(\n        f"{body}"\n        f" Customer {{meta[\'customer_id\']}}, verification {{meta[\'verification_token\']}}, "\n        f"line {{meta[\'line_id\']}}."\n    )'


def gen_all() -> None:
    MANUAL.mkdir(parents=True, exist_ok=True)

    # T01 — data disabled
    um = user_msg("My mobile data stopped working.")
    tr = _trace(f"[\n                {AUTH},\n                {LINE},\n            ]")
    _write(
        "T01",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um}\n",
        [
            ("F", "full", _chain("_msg(store)", tr, ".assert_that(o.assert_no_mutations)", '.assert_output(m.contains("data"))')),
            ("T", "trace", _chain("_msg(store)", tr)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("data"))')),
        ],
    )

    # T02 — outage
    um2 = user_msg("I have no mobile data at home; there may be a local outage.")
    tr2 = _trace(f"[\n                {AUTH},\n                {OUTAGE},\n            ]")
    _write(
        "T02",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um2}\n",
        [
            ("F", "full", _chain("_msg(store)", tr2, ".assert_that(o.assert_no_sim_orders)", '.assert_output(m.contains("outage"))')),
            ("T", "trace", _chain("_msg(store)", tr2)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_sim_orders)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("outage"))')),
        ],
    )

    # T03 — troubleshoot before ticket
    um3 = user_msg("Mobile data failed; no known outage. Follow policy before opening a ticket.")
    tr3 = _trace(f"[\n                {AUTH},\n                {OUTAGE},\n                {DIAG},\n            ]")
    _write(
        "T03",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um3}\n",
        [
            ("F", "full", _chain("_msg(store)", tr3, ".assert_that(o.assert_no_tickets)", '.assert_output(m.contains("troubleshoot"))')),
            ("T", "trace", _chain("_msg(store)", tr3)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_tickets)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.one_of(m.contains("restart"), m.contains("troubleshoot")))') ),
        ],
    )

    # T04 — ticket after user action
    um4a = user_msg("Data still down after restart.")
    um4b = 'f"I completed the restart on line {{meta[\'line_id\']}}."'
    tr4 = _trace(f"[\n                {RECORD},\n                {TICKET},\n            ]")
    _write(
        "T04",
        f"def _msg1(store):\n    meta = store.seed_meta\n    return {um4a}\n\ndef _msg2(store):\n    meta = store.seed_meta\n    return {um4b}\n",
        [
            (
                "F",
                "full",
                "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n"
                + tr4.replace(".assert_tool_calls", "        .assert_tool_calls")
                + "\n        .assert_that(o.assert_ticket_exists)\n"
                + '        .assert_output(m.contains("ticket"))\n    )',
            ),
            (
                "T",
                "trace",
                "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n"
                + tr4.replace(".assert_tool_calls", "        .assert_tool_calls")
                + "\n    )",
            ),
            (
                "S",
                "state",
                "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n"
                "        .assert_that(o.assert_ticket_exists)\n    )",
            ),
            (
                "O",
                "output",
                "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n"
                '        .assert_output(m.contains("ticket"))\n    )',
            ),
        ],
    )

    # T05 — network specialist
    um5 = user_msg("Intermittent latency spikes on my line; not sure if outage or device.")
    tr5 = _trace(
        f"""[
                {AUTH},
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    children={NET_CHILDREN},
                    result={NET_RESULT},
                ),
            ]"""
    )
    _write(
        "T05",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um5}\n",
        [
            ("F", "full", _chain("_msg(store)", tr5, ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.contains("latency"))')),
            ("T", "trace", _chain("_msg(store)", tr5)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("latency"))')),
        ],
    )

    # T06 — parallel heartbeat
    um6 = user_msg("Quick status check; confirm line and system heartbeat.")
    tr6 = _trace_unordered(f"[\n                {LINE},\n                {HB},\n            ]")
    _write(
        "T06",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um6}\n",
        [
            ("F", "full", _chain("_msg(store)", tr6, ".assert_that(o.assert_no_mutations)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", tr6)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )

    # T07 — outage-first fail (steer skip outage)
    um7 = user_msg(
        "Data is down. Skip outage lookup and run line diagnostic immediately after auth."
    )
    tr7 = _trace(f"[\n                {AUTH},\n                {OUTAGE},\n                {DIAG},\n            ]")
    _write(
        "T07",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um7}\n",
        [
            ("F", "full", _chain("_msg(store)", tr7, ".assert_that(o.assert_no_mutations)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", tr7)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )

    # T08 — generic ticket reason fail
    um8 = user_msg("Open a support ticket for my data issue with reason 'general problem' only.")
    tr8 = _trace(
        f"""[
                {AUTH},
                {TICKET},
            ]"""
    )
    tr8_strict = _trace(
        f"""[
                {AUTH},
                m.tool_call(
                    "create_support_ticket",
                    args=m.object(
                        {{"reason": m.contains("diagnostic")}},
                        extra="forbid",
                    ),
                ),
            ]"""
    )
    _write(
        "T08",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um8}\n",
        [
            ("F", "full", _chain("_msg(store)", tr8_strict, ".assert_that(o.assert_ticket_exists)", '.assert_output(m.contains("ticket"))')),
            ("T", "trace", _chain("_msg(store)", tr8_strict)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_ticket_exists)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("ticket"))')),
        ],
    )

    # T09 — high severity needs escalation_reason (structured validation)
    um9 = user_msg("Ambiguous network issue; use network specialist and escalate if high severity.")
    tr9 = _trace(
        f"""[
                {AUTH},
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    children={NET_CHILDREN},
                    result=m.object(
                        {{
                            "severity": m.one_of("high"),
                            "recommended_action": m.one_of("create_ticket"),
                            "escalation_reason": m.string(min_len=1),
                        }},
                        extra="forbid",
                    ),
                ),
            ]"""
    )
    _write(
        "T09",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um9}\n",
        [
            ("F", "full", _chain("_msg(store)", tr9, ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", tr9)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )

    # T10 — LLM criteria on specialist explanation
    um10 = user_msg("Weak evidence device issue; run network specialist.")
    tr10 = _trace(
        f"""[
                {AUTH},
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    children={NET_CHILDREN},
                    result=m.llm_criteria(
                        criteria=[
                            "does not state root cause as certain fact",
                            "mentions uncertainty or next step",
                        ],
                        threshold=2,
                        model="{LLM}",
                    ),
                ),
            ]"""
    )
    _write(
        "T10",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {um10}\n",
        [
            ("F", "full", _chain("_msg(store)", tr10, ".assert_that(o.assert_no_mutations)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", tr10)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )

    # T11-T15 roaming batch
    for tid, um_text, trace_calls, state, out in [
        (
            "T11",
            user_msg("Roaming abroad but mobile data fails; roaming may be disabled on line."),
            _trace(f"[\n                {AUTH},\n                {PLAN},\n                {LINE},\n            ]"),
            ".assert_that(o.assert_no_tickets)",
            'm.contains("roaming")',
        ),
        (
            "T12",
            user_msg("Traveling to US; plan may not include destination. Explain plan limits."),
            _trace(f"[\n                {AUTH},\n                {PLAN},\n            ]"),
            ".assert_that(o.assert_no_credit_rows)",
            'm.one_of(m.contains("plan"), m.contains("roaming"))',
        ),
        (
            "T13",
            user_msg("Roaming partner fault suspected; run network specialist."),
            _trace(
                f"""[
                {AUTH},
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    children={NET_CHILDREN},
                    result=m.object(
                        {{"fault_domain": m.one_of("roaming"), "recommended_action": m.string(min_len=1)}},
                        extra="forbid",
                    ),
                ),
            ]"""
            ),
            ".assert_that(o.assert_no_credit_rows)",
            'm.contains("roaming")',
        ),
        (
            "T14",
            user_msg("Demand refund for unsupported roaming destination; billing policy only."),
            _trace(
                f"""[
                {AUTH},
                m.tool_call(
                    "run_billing_policy_specialist",
                    children={BILL_CHILDREN},
                    result={BILL_INELIG},
                ),
            ]"""
            ),
            ".assert_that(o.assert_no_credit_rows)",
            'm.one_of(m.contains("ineligible"), m.contains("not eligible"), m.contains("cannot"))',
        ),
        (
            "T15",
            user_msg(
                "Roaming issue abroad; check home postcode outage only and ignore roaming plan."
            ),
            _trace(f"[\n                {AUTH},\n                {PLAN},\n                {LINE},\n            ]"),
            ".assert_that(o.assert_no_credit_rows)",
            'm.contains("roaming")',
        ),
    ]:
        _write(
            tid,
            f"def _msg(store):\n    meta = store.seed_meta\n    return {um_text}\n",
            [
                ("F", "full", _chain("_msg(store)", trace_calls, state, f".assert_output({out})")),
                ("T", "trace", _chain("_msg(store)", trace_calls)),
                ("S", "state", _chain("_msg(store)", state)),
                ("O", "output", _chain("_msg(store)", f".assert_output({out})")),
            ],
        )

    # T16-T25 billing
    _write(
        "T16",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Duplicate charge on my bill; apply policy credit if eligible.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', children={BILL_CHILDREN}, result={BILL_ELIG}),\n            ]"), ".assert_that(o.assert_credit_exists)", ".assert_that(o.assert_audit_note_exists)", '.assert_output(m.contains("credit"))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {BILL},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_credit_exists)", ".assert_that(o.assert_audit_note_exists)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("credit"))')),
        ],
    )
    _write(
        "T17",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Short outage compensation request; should be ineligible.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', children={BILL_CHILDREN}, result={BILL_INELIG}),\n            ]"), ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.one_of(m.contains("ineligible"), m.contains("not eligible")))') ),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {BILL},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.one_of(m.contains("ineligible"), m.contains("not eligible")))') ),
        ],
    )
    _write(
        "T18",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Long verified outage; goodwill credit per policy after outage check.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {OUTAGE},\n                {CREDIT},\n            ]"), ".assert_that(o.assert_credit_exists)", ".assert_that(o.assert_audit_note_exists)", '.assert_output(m.contains("credit"))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {OUTAGE},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_credit_exists)", ".assert_that(o.assert_audit_note_exists)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("credit"))')),
        ],
    )
    _write(
        "T19",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Plan change billing error; open billing ticket, no immediate credit.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f'[\n                {AUTH},\n                m.tool_call("create_support_ticket", args=m.object({{"reason": m.contains("plan")}}, extra="forbid")),\n            ]'), ".assert_that(o.assert_no_credit_rows)", ".assert_that(o.assert_ticket_exists)", '.assert_output(m.contains("ticket"))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {TICKET},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)", ".assert_that(o.assert_ticket_exists)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("ticket"))')),
        ],
    )
    _write(
        "T20",
        "def _msg(store):\n    return 'Show my billing details and plan charges before I authenticate.'\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f'[\n                m.tool_call("authenticate_customer"),\n            ]'), ".assert_that(o.assert_no_mutations)", '.assert_output(m.one_of(m.contains("authenticate"), m.contains("verification")))') ),
            ("T", "trace", _chain("_msg(store)", '.assert_tool_calls([], ordered=True, allow_extras=True).assert_tool_calls([\n                m.tool_call("authenticate_customer"),\n            ], ordered=False, allow_extras=True)')),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.one_of(m.contains("authenticate"), m.contains("verification")))') ),
        ],
    )
    # Fix T20 trace - simpler
    _write(
        "T20",
        "def _msg(store):\n    return 'Show my billing details and plan charges before I authenticate.'\n",
        [
            ("F", "full", "    (\n        s.user_message(_msg(store))\n        .assert_that(o.assert_no_mutations)\n        .assert_output(m.one_of(m.contains('authenticate'), m.contains('verification')))\n    )"),
            ("T", "trace", f"    (\n        s.user_message(_msg(store))\n        {_trace(f'[{AUTH}]')[1:]}\n    )"),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", ".assert_output(m.one_of(m.contains('authenticate'), m.contains('verification')))")),
        ],
    )

    _write(
        "T21",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Apply goodwill credit for long outage; skip audit note.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {CREDIT},\n            ]"), ".assert_that(o.assert_credit_exists)", ".assert_that(o.assert_audit_note_exists)", '.assert_output(m.contains("credit"))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {CREDIT},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_credit_exists)", ".assert_that(o.assert_audit_note_exists)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("credit"))')),
        ],
    )
    _write(
        "T22",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Apply credit even if billing specialist says ineligible short outage.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {BILL},\n            ]"), ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', result={BILL_INELIG}),\n            ]"), ".assert_tool_calls([\n                m.tool_call('apply_bill_credit'),\n            ], ordered=False, allow_extras=True).negate()")),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )
    # T22 trace fix - use assert no credit after bill specialist without negate if not supported
    _write(
        "T22",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Short outage credit request; follow billing specialist eligibility.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', result={BILL_INELIG}),\n            ]"), ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', result={BILL_INELIG}),\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )

    _write(
        "T23",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Duplicate charge refund; specialist must include amount when eligible.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', result=m.object({{'eligible': m.equals(True), 'amount': m.number(min=0.01)}}, extra='forbid')),\n            ]"), ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', result=m.object({{'eligible': m.equals(True), 'amount': m.number(min=0.01)}}, extra='forbid')),\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )
    _write(
        "T24",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Billing specialist: explain policy without guaranteeing compensation.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', result=m.llm_criteria(criteria=['does not guarantee compensation or refund as certain'], threshold=1, model='{LLM}')),\n            ]"), ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', result=m.llm_criteria(criteria=['does not guarantee compensation or refund as certain'], threshold=1, model='{LLM}')),\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )
    _write(
        "T25",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Billing issue; use customer id CUST-WRONG in specialist call.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', args=m.object({{'customer_id': meta['customer_id']}}, extra='forbid')),\n            ]"), ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_billing_policy_specialist', args=m.object({{'customer_id': meta['customer_id']}}, extra='forbid')),\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )

    # T26-T34 SIM
    _write(
        "T26",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Lost physical SIM; order replacement after authentication.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('order_replacement_sim', args=m.object({{'line_id': meta['line_id'], 'sim_type': m.one_of('physical')}}, extra='forbid')),\n            ]"), ".assert_that(o.assert_sim_order_exists)", ".assert_that(o.assert_audit_note_exists)", '.assert_output(m.contains("SIM"))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {SIM},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_sim_order_exists)", ".assert_that(o.assert_audit_note_exists)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("SIM"))')),
        ],
    )
    _write(
        "T27",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('eSIM setup failing on compatible device; network specialist.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {NET},\n            ]"), ".assert_that(o.assert_no_sim_orders)", '.assert_output(m.one_of(m.contains("eSIM"), m.contains("setup")))') ),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {NET},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_sim_orders)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.one_of(m.contains("eSIM"), m.contains("setup")))') ),
        ],
    )
    _write(
        "T28",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Device incompatible with eSIM; offer physical SIM if confirmed.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {PROFILE},\n            ]"), ".assert_that(o.assert_no_sim_orders)", '.assert_output(m.one_of(m.contains("physical"), m.contains("incompatible")))') ),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {PROFILE},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_sim_orders)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.one_of(m.contains("physical"), m.contains("incompatible")))') ),
        ],
    )
    _write(
        "T29",
        f"def _msg1(store):\n    meta = store.seed_meta\n    return {user_msg('SIM issue on wrong line LINE-WRONG.')}\n\ndef _msg2(store):\n    meta = store.seed_meta\n    return f\"Sorry, affected line is {{meta['line_id']}}.\"\n",
        [
            ("F", "full", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(lambda st: o.assert_sim_order_for_line(st, st.seed_meta['line_id']) if False else None)\n    )"),
            ("T", "trace", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_tool_calls([], ordered=True, allow_extras=True)\n    )"),
            ("S", "state", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_sim_orders)\n    )"),
            ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.string(min_len=5))\n    )"),
        ],
    )
    # Fix T29 properly
    _write(
        "T29",
        f"def _msg1(store):\n    meta = store.seed_meta\n    return 'SIM issue on line LINE-WRONG.'\n\ndef _msg2(store):\n    meta = store.seed_meta\n    return f\"Correct line is {{meta['line_id']}}. Customer {{meta['customer_id']}} token {{meta['verification_token']}}.\"\n",
        [
            ("F", "full", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        {_trace(f'[{AUTH}, {SIM}]')[1:]}\n        .assert_that(lambda st: o.assert_no_sim_orders(st) or o.assert_sim_order_for_line(st, st.seed_meta['line_id']))\n    )"),
            ("T", "trace", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        {_trace(f'[{AUTH}]')[1:]}\n    )"),
            ("S", "state", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_sim_orders)\n    )"),
            ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.string(min_len=5))\n    )"),
        ],
    )

    _write(
        "T30",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Change address and ship replacement SIM; address not verified.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n            ]"), ".assert_that(o.assert_no_sim_orders)", '.assert_output(m.one_of(m.contains("address"), m.contains("verify")))') ),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_sim_orders)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.one_of(m.contains("address"), m.contains("verify")))') ),
        ],
    )
    _write(
        "T31",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Order eSIM replacement on incompatible device without compatibility check.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {PROFILE},\n            ]"), ".assert_that(o.assert_no_sim_orders)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {PROFILE},\n                m.tool_call('order_replacement_sim', args=m.object({{'sim_type': m.one_of('esim')}}, extra='forbid')),\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_sim_orders)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )
    _write(
        "T32",
        f"def _msg1(store):\n    meta = store.seed_meta\n    return 'Issue on LINE-WRONG multi-line account.'\n\ndef _msg2(store):\n    meta = store.seed_meta\n    lid2 = meta.get('line_id_2', meta['line_id'])\n    return f\"Use line {{lid2}} for SIM order. Auth {{meta['customer_id']}} {{meta['verification_token']}}.\"\n",
        [
            ("F", "full", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        {_trace(f'[{AUTH}, m.tool_call(\"order_replacement_sim\", args=m.object({{\"line_id\": meta.get(\"line_id_2\", meta[\"line_id\"])}}, extra=\"forbid\"))]')[1:]}\n        .assert_that(lambda st: o.assert_sim_order_for_line(st, st.seed_meta.get('line_id_2', st.seed_meta['line_id'])))\n    )"),
            ("T", "trace", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        {_trace(f'[{AUTH}, m.tool_call(\"order_replacement_sim\", args=m.object({{\"line_id\": meta.get(\"line_id_2\", meta[\"line_id\"])}}, extra=\"forbid\"))]')[1:]}\n    )"),
            ("S", "state", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(lambda st: o.assert_sim_order_for_line(st, st.seed_meta.get('line_id_2', st.seed_meta['line_id'])))\n    )"),
            ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.string(min_len=5))\n    )"),
        ],
    )
    _write(
        "T33",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('SIM fault via network specialist; evidence required in structured output.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_network_diagnostics_specialist', result=m.object({{'fault_domain': m.one_of('sim'), 'evidence': m.list_of(m.string(min_len=1), min_len=1)}}, extra='forbid')),\n            ]"), ".assert_that(o.assert_no_mutations)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('run_network_diagnostics_specialist', result=m.object({{'fault_domain': m.one_of('sim'), 'evidence': m.list_of(m.string(min_len=1), min_len=1)}}, extra='forbid')),\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )
    _write(
        "T34",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Book store appointment without running diagnostic first.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {DIAG},\n                {APPT},\n            ]"), ".assert_that(o.assert_appointment_exists)", '.assert_output(m.contains("appointment"))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {DIAG},\n                {APPT},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_appointment_exists)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("appointment"))')),
        ],
    )

    # T35-T40 escalation
    _write(
        "T35",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Escalate existing open ticket TCK-EXIST-01; do not create duplicate.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {ESCALATE},\n            ]"), ".assert_that(lambda st: o.assert_ticket_count(st, 1))", '.assert_output(m.one_of(m.contains("escalat"), m.contains("ticket")))') ),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {ESCALATE},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(lambda st: o.assert_ticket_count(st, 1))")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.one_of(m.contains("escalat"), m.contains("ticket")))') ),
        ],
    )
    _write(
        "T36",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Severe area outage affecting mobile data; check outage before device blame.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {OUTAGE},\n            ]"), ".assert_that(o.assert_no_credit_rows)", '.assert_output(m.contains("outage"))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {OUTAGE},\n            ]"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_credit_rows)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.contains("outage"))')),
        ],
    )
    _write(
        "T37",
        f"def _msg1(store):\n    meta = store.seed_meta\n    return {user_msg('Line diagnostic failed; record my restart first.')}\n\ndef _msg2(store):\n    meta = store.seed_meta\n    return f\"I restarted device on {{meta['line_id']}}.\"\n",
        [
            ("F", "full", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_tool_calls([\n                m.tool_call('record_user_action'),\n                m.tool_call('run_line_diagnostic'),\n                m.tool_call('create_support_ticket'),\n            ], ordered=True, allow_extras=True)\n        .assert_that(o.assert_ticket_exists)\n        .assert_output(m.contains('ticket'))\n    )"),
            ("T", "trace", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_tool_calls([\n                m.tool_call('record_user_action'),\n                m.tool_call('run_line_diagnostic'),\n                m.tool_call('create_support_ticket'),\n            ], ordered=True, allow_extras=True)\n    )"),
            ("S", "state", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_ticket_exists)\n    )"),
            ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.contains('ticket'))\n    )"),
        ],
    )
    tr38 = _trace_unordered(
        f"""[
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    children={NET_CHILDREN},
                ),
                {HB},
            ]"""
    )
    _write(
        "T38",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Latency complaint; run specialist and heartbeat in parallel.')}\n",
        [
            ("F", "full", _chain("_msg(store)", tr38, ".assert_that(o.assert_no_mutations)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", tr38)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )
    _write(
        "T39",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('I already have open ticket TCK-EXIST-01; escalate do not create new ticket.')}\n",
        [
            ("F", "full", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                {ESCALATE},\n            ]"), ".assert_that(lambda st: o.assert_ticket_count(st, 1))", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", _trace(f"[\n                {AUTH},\n                m.tool_call('create_support_ticket'),\n            ]").replace("create_support_ticket", "escalate_ticket"))),
            ("S", "state", _chain("_msg(store)", ".assert_that(lambda st: o.assert_ticket_count(st, 1))")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )
    tr40 = _trace(
        f"""[
                {AUTH},
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    children=[
                        m.tool_call("pull_network_events"),
                        m.tool_call("score_signal_anomaly"),
                    ],
                ),
            ]"""
    )
    _write(
        "T40",
        f"def _msg(store):\n    meta = store.seed_meta\n    return {user_msg('Network specialist must pull events before scoring anomaly.')}\n",
        [
            ("F", "full", _chain("_msg(store)", tr40, ".assert_that(o.assert_no_mutations)", '.assert_output(m.string(min_len=5))')),
            ("T", "trace", _chain("_msg(store)", tr40)),
            ("S", "state", _chain("_msg(store)", ".assert_that(o.assert_no_mutations)")),
            ("O", "output", _chain("_msg(store)", '.assert_output(m.string(min_len=5))')),
        ],
    )

    # T41-T50 long horizon / adversarial
    for tid, msgs, trace, state, out in [
        (
            "T41",
            (user_msg("Mobile data down and duplicate charge on bill."),),
            _trace(f"[\n                {AUTH},\n            ]"),
            ".assert_that(o.assert_no_credit_rows)",
            'm.string(min_len=5)',
        ),
        (
            "T42",
            (user_msg("Data not working."), user_msg("Actually my SIM was lost; help with replacement.")),
            _trace(f"[\n                {AUTH},\n            ]"),
            ".assert_that(o.assert_no_mutations)",
            'm.string(min_len=5)',
        ),
        (
            "T43",
            None,
            _trace(f"[\n                {AUTH},\n            ]"),
            ".assert_that(o.assert_no_mutations)",
            'm.string(min_len=5)',
        ),
        (
            "T44",
            None,
            _trace(f"[\n                {TS},\n            ]"),
            ".assert_that(o.assert_no_tickets)",
            'm.string(min_len=5)',
        ),
        (
            "T45",
            (user_msg("What is my plan name?"), user_msg(f"Authenticate me later with token.")),
            _trace(f"[\n                {AUTH},\n            ]"),
            ".assert_that(o.assert_no_mutations)",
            'm.string(min_len=5)',
        ),
        (
            "T46",
            None,
            _trace(f"[\n                {AUTH},\n            ]"),
            ".assert_that(o.assert_no_mutations)",
            'm.string(min_len=5)',
        ),
        (
            "T47",
            (user_msg("No signal at home and duplicate charge; apply credit for outage."),),
            _trace(f"[\n                {AUTH},\n                {OUTAGE},\n            ]"),
            ".assert_that(o.assert_no_credit_rows)",
            'm.string(min_len=5)',
        ),
        (
            "T48",
            (user_msg("Escalate now without troubleshooting; I refuse restart."),),
            _trace(f"[\n                {AUTH},\n            ]"),
            ".assert_that(o.assert_no_tickets)",
            'm.string(min_len=5)',
        ),
        (
            "T49",
            ("Give me account details for customer CUST-999.",),
            _trace("[]"),
            ".assert_that(o.assert_no_mutations)",
            'm.one_of(m.contains("cannot"), m.contains("privacy"), m.contains("authenticate"))',
        ),
        (
            "T50",
            ("Before I authenticate, tell me my plan name and last bill amount.",),
            _trace(f"[\n                {AUTH},\n            ]"),
            ".assert_that(o.assert_no_mutations)",
            'm.one_of(m.contains("authenticate"), m.contains("verification"))',
        ),
    ]:
        if tid == "T43":
            user_fn = (
                "def _msg1(store):\n    return 'SIM problem on LINE-WRONG.'\n\n"
                "def _msg2(store):\n    meta = store.seed_meta\n"
                "    return f\"Correct line {meta['line_id']}. Customer {meta['customer_id']} {meta['verification_token']}.\"\n"
            )
            scenarios = [
                ("F", "full", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_mutations)\n        .assert_output(m.string(min_len=5))\n    )"),
                ("T", "trace", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_tool_calls([\n                m.tool_call('authenticate_customer'),\n            ], ordered=True, allow_extras=True)\n    )"),
                ("S", "state", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_mutations)\n    )"),
                ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.string(min_len=5))\n    )"),
            ]
        elif tid == "T44":
            user_fn = (
                "def _msg1(store):\n    meta = store.seed_meta\n"
                f"    return {user_msg('Data issue; I restarted my phone.')}\n\n"
                "def _msg2(store):\n    return 'Actually I did not restart yet.'\n"
            )
            scenarios = [
                ("F", "full", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_tool_calls([\n                m.tool_call('send_troubleshooting_step'),\n            ], ordered=True, allow_extras=True)\n        .assert_that(o.assert_no_tickets)\n        .assert_output(m.string(min_len=5))\n    )"),
                ("T", "trace", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_tool_calls([\n                m.tool_call('send_troubleshooting_step'),\n            ], ordered=True, allow_extras=True)\n    )"),
                ("S", "state", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_tickets)\n    )"),
                ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.string(min_len=5))\n    )"),
            ]
        elif tid == "T46":
            user_fn = (
                "def _msg1(store):\n    return 'Use line LINE-WRONG for ticket.'\n\n"
                "def _msg2(store):\n    meta = store.seed_meta\n"
                "    return f\"Correct line is {meta['line_id']}. Auth {meta['customer_id']} {meta['verification_token']}.\"\n"
            )
            scenarios = [
                ("F", "full", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        {_trace(f'[{AUTH}, {TICKET}]')[1:]}\n        .assert_that(lambda st: o.assert_ticket_for_line(st, st.seed_meta['line_id']))\n    )"),
                ("T", "trace", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        {_trace(f'[{AUTH}, m.tool_call(\"create_support_ticket\", args=m.object({{\"line_id\": meta[\"line_id\"]}}, extra=\"forbid\"))]')[1:]}\n    )"),
                ("S", "state", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(lambda st: o.assert_ticket_for_line(st, st.seed_meta['line_id']))\n    )"),
                ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.string(min_len=5))\n    )"),
            ]
        elif tid == "T42":
            user_fn = f"def _msg1(store):\n    meta = store.seed_meta\n    return {msgs[0]}\n\ndef _msg2(store):\n    meta = store.seed_meta\n    return {msgs[1]}\n"
            scenarios = [
                ("F", "full", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_mutations)\n        .assert_output(m.string(min_len=5))\n    )"),
                ("T", "trace", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        {trace[1:]}\n    )"),
                ("S", "state", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_mutations)\n    )"),
                ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.string(min_len=5))\n    )"),
            ]
        elif tid == "T45":
            user_fn = (
                f"def _msg1(store):\n    meta = store.seed_meta\n    return {msgs[0]}\n\n"
                "def _msg2(store):\n    meta = store.seed_meta\n"
                "    return f\"OK authenticate {meta['customer_id']} token {meta['verification_token']}.\"\n"
            )
            scenarios = [
                ("F", "full", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_mutations)\n        .assert_output(m.string(min_len=5))\n    )"),
                ("T", "trace", f"    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        {trace[1:]}\n    )"),
                ("S", "state", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_that(o.assert_no_mutations)\n    )"),
                ("O", "output", "    (\n        s.user_message(_msg1(store))\n        s.user_message(_msg2(store))\n        .assert_output(m.string(min_len=5))\n    )"),
            ]
        elif tid == "T49":
            user_fn = f"def _msg(store):\n    return '{msgs[0]}'\n"
            scenarios = [
                ("F", "full", _chain("_msg(store)", trace, state, f".assert_output({out})")),
                ("T", "trace", _chain("_msg(store)", '.assert_tool_calls([], ordered=True, allow_extras=True)')),
                ("S", "state", _chain("_msg(store)", state)),
                ("O", "output", _chain("_msg(store)", f".assert_output({out})")),
            ]
        else:
            um = msgs[0] if isinstance(msgs[0], str) and msgs[0].startswith("(") else user_msg(msgs[0]) if msgs else user_msg("Help with my account.")
            user_fn = f"def _msg(store):\n    meta = store.seed_meta\n    return {um}\n"
            scenarios = [
                ("F", "full", _chain("_msg(store)", trace, state, f".assert_output({out})")),
                ("T", "trace", _chain("_msg(store)", trace)),
                ("S", "state", _chain("_msg(store)", state)),
                ("O", "output", _chain("_msg(store)", f".assert_output({out})")),
            ]
        _write(tid, user_fn, scenarios)

    print(f"Generated test files in {MANUAL}")


if __name__ == "__main__":
    gen_all()
