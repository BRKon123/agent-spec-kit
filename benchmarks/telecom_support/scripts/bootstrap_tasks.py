#!/usr/bin/env python3
"""One-shot generator: writes seeds/task_Txx.json and tasks/manual/test_Txx.py (explicit scenarios)."""

from __future__ import annotations

import json
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
SEEDS = BENCH / "seeds"
MANUAL = BENCH / "tasks" / "manual"

LLM_MODEL = "openai:gpt-5-nano"


def base_seed(tid: str, n: int, **meta) -> dict:
    cid = f"CUST-{n:03d}"
    lid = f"LINE-{n:04d}"
    m = {
        "task_id": tid,
        "customer_id": cid,
        "line_id": lid,
        "verification_token": f"1990-{n:02d}-15",
        "postcode": "E1 6AN",
        "credit_eligible": False,
        "duplicate_charge": False,
        "short_outage": False,
        "credit_amount": 15.0,
        "network_outage_active": False,
        "roaming_issue": False,
        "fault_domain": "unknown",
        "plan_change_billing_error": False,
    }
    m.update(meta)
    lid2 = m.pop("line_id_2", None)
    line = {
        "line_id": lid,
        "customer_id": cid,
        "phone_number": f"+4477009{n:05d}",
        "plan_id": "PLAN-STD",
        "sim_status": "active",
        "roaming_enabled": 1 if m.get("roaming_enabled_flag", True) else 0,
        "data_enabled": 1 if m.get("data_enabled_flag", True) else 0,
    }
    lines = [line]
    if lid2:
        lines.append(
            {
                "line_id": lid2,
                "customer_id": cid,
                "phone_number": f"+4477009{n:05d}2",
                "plan_id": "PLAN-STD",
                "sim_status": "active",
                "roaming_enabled": 1,
                "data_enabled": 1,
            }
        )
        m["line_id_2"] = lid2
    seed = {
        "meta": m,
        "customers": [
            {
                "customer_id": cid,
                "name": f"Customer {n}",
                "dob_check_token": m["verification_token"],
                "account_status": "active",
            }
        ],
        "plans": [
            {
                "plan_id": "PLAN-STD",
                "plan_type": "standard",
                "data_allowance_mb": 15000,
                "roaming_rules_json": json.dumps({"eu": m.get("plan_eu_roaming", True), "us": False}),
                "price": 22.0,
            }
        ],
        "lines": lines,
        "devices": [
            {
                "device_id": f"DEV-{n:03d}",
                "line_id": lid,
                "model": "iPhone 15",
                "os": "iOS 17",
                "sim_type": m.get("sim_type", "esim"),
                "settings_json": json.dumps({"airplane_mode": False}),
            }
        ],
        "network_outages": [],
        "network_events": [],
        "billing_events": [],
    }
    if m.get("network_outage_active"):
        seed["network_outages"] = [
            {
                "postcode": m["postcode"],
                "service_type": "mobile",
                "status": "active",
                "started_at": "2026-05-10T08:00:00+00:00",
                "affected_services_json": '["data","voice"]',
            }
        ]
    if m.get("duplicate_charge"):
        seed["billing_events"] = [
            {
                "customer_id": cid,
                "event_type": "duplicate_charge",
                "amount": 9.99,
                "detail": "duplicate plan fee",
                "occurred_at": "2026-05-01T00:00:00+00:00",
            }
        ]
    if m.get("credit_eligible"):
        seed["billing_events"] = [
            {
                "customer_id": cid,
                "event_type": "outage_compensation",
                "amount": 0,
                "detail": "long outage verified",
                "occurred_at": "2026-05-01T00:00:00+00:00",
            }
        ]
    if m.get("existing_ticket_id"):
        seed["tickets"] = [
            {
                "ticket_id": m["existing_ticket_id"],
                "customer_id": cid,
                "line_id": lid,
                "reason": "existing open issue",
                "priority": "medium",
                "status": "open",
                "created_at": "2026-05-12T10:00:00+00:00",
            }
        ]
    return seed


def write_seed(tid: str, n: int, **meta) -> None:
    path = SEEDS / f"task_{tid}.json"
    path.write_text(json.dumps(base_seed(tid, n, **meta), indent=2) + "\n", encoding="utf-8")


def scenario_header(tid: str, oracle: str, func: str) -> str:
    return f'''
@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=2,
    tags=("telecom", "task:{tid}", "oracle:{oracle}", "reference"),
    timeout_s=420.0,
)
async def {func}(s, store):
'''


def write_test_file(tid: str, body: str) -> None:
    header = f'''"""Task {tid} scenarios (explicit scripted messages and checks)."""

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
    path = MANUAL / f"test_{tid}.py"
    path.write_text(header + body, encoding="utf-8")


# Per-task seed meta (n = task number 1-50)
SEED_META: dict[str, dict] = {}
for i in range(1, 51):
    tid = f"T{i:02d}"
    SEED_META[tid] = {}

SEED_META["T01"] = {"data_enabled_flag": False}
SEED_META["T02"] = {"network_outage_active": True, "data_enabled_flag": False}
SEED_META["T03"] = {}
SEED_META["T04"] = {}
SEED_META["T05"] = {"fault_domain": "network"}
SEED_META["T06"] = {}
SEED_META["T07"] = {}
SEED_META["T08"] = {}
SEED_META["T09"] = {}
SEED_META["T10"] = {"fault_domain": "device"}
SEED_META["T11"] = {"roaming_enabled_flag": False, "roaming_issue": True}
SEED_META["T12"] = {"plan_eu_roaming": False, "roaming_issue": True}
SEED_META["T13"] = {"roaming_issue": True, "fault_domain": "roaming"}
SEED_META["T14"] = {"short_outage": True}
SEED_META["T15"] = {"roaming_issue": True}
SEED_META["T16"] = {"duplicate_charge": True, "credit_amount": 9.99}
SEED_META["T17"] = {"short_outage": True}
SEED_META["T18"] = {"credit_eligible": True, "credit_amount": 20.0, "network_outage_active": True}
SEED_META["T19"] = {"plan_change_billing_error": True}
SEED_META["T20"] = {}
SEED_META["T21"] = {"credit_eligible": True, "credit_amount": 10.0}
SEED_META["T22"] = {"short_outage": True}
SEED_META["T23"] = {"duplicate_charge": True}
SEED_META["T24"] = {"short_outage": True}
SEED_META["T25"] = {}
SEED_META["T26"] = {}
SEED_META["T27"] = {"fault_domain": "sim", "sim_type": "esim"}
SEED_META["T28"] = {"sim_type": "physical"}
SEED_META["T29"] = {"line_id_2": "LINE-0029B"}
SEED_META["T30"] = {"address_unverified": True}
SEED_META["T31"] = {"sim_type": "esim"}
SEED_META["T32"] = {"line_id_2": "LINE-0032B"}
SEED_META["T33"] = {"fault_domain": "sim"}
SEED_META["T34"] = {}
SEED_META["T35"] = {"existing_ticket_id": "TCK-EXIST-01"}
SEED_META["T36"] = {"network_outage_active": True}
SEED_META["T37"] = {}
SEED_META["T38"] = {}
SEED_META["T39"] = {"existing_ticket_id": "TCK-EXIST-01"}
SEED_META["T40"] = {}
SEED_META["T41"] = {"duplicate_charge": True}
SEED_META["T42"] = {}
SEED_META["T43"] = {"line_id_2": "LINE-0043B"}
SEED_META["T44"] = {}
SEED_META["T45"] = {}
SEED_META["T46"] = {"line_id_2": "LINE-0046B"}
SEED_META["T47"] = {"duplicate_charge": True}
SEED_META["T48"] = {}
SEED_META["T49"] = {}
SEED_META["T50"] = {}


def gen_simple_task(tid: str, n: int, messages: list[str], trace_block: str, state: str, output: str) -> str:
    msgs = ""
    for i, msg in enumerate(messages):
        if i == 0:
            msgs += f'    s.user_message("""{msg}""")\n'
        else:
            msgs += f'    s.user_message("""{msg}""")\n'
    full = ""
    trace = f"    {trace_block}\n" if trace_block else ""
    state_l = f"    {state}\n" if state else ""
    output_l = f"    {output}\n" if output else ""

    def block(oracle: str, func: str, parts: str) -> str:
        return scenario_header(tid, oracle, func) + f'    (\n{msgs}{parts}    )\n'

    return (
        block("F", f"test_{tid.lower()}_full", trace + state_l + output_l)
        + block("T", f"test_{tid.lower()}_trace", trace)
        + block("S", f"test_{tid.lower()}_state", state_l if state_l else "    pass  # no state checks\n")
        + block("O", f"test_{tid.lower()}_output", output_l if output_l else "    pass  # no output checks\n")
    )


def main() -> None:
    SEEDS.mkdir(parents=True, exist_ok=True)
    MANUAL.mkdir(parents=True, exist_ok=True)

    for i in range(1, 51):
        tid = f"T{i:02d}"
        write_seed(tid, i, **SEED_META.get(tid, {}))

    # T01
    m = '"My mobile data stopped working. Customer {cid}, DOB {tok}, line {lid}."'
    auth_trace = '''.assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("get_line_status", args={"line_id": meta["line_id"]}),
            ],
            ordered=True,
            allow_extras=True,
        )'''
    write_test_file(
        "T01",
        gen_simple_task(
            "T01",
            1,
            [
                "My mobile data is not working. "
                "Authenticate with customer id CUST-001, verification 1990-01-15, then check line LINE-0001."
            ],
            auth_trace.replace("meta", "store.seed_meta"),
            ".assert_that(o.assert_no_mutations)",
            '.assert_output(m.contains("data"))',
        ),
    )

    print("Bootstrap: seeds written for T01-T50; customize test_T02-T50 scenario bodies next.")
    print("Run: python benchmarks/telecom_support/scripts/bootstrap_tasks.py")


if __name__ == "__main__":
    main()
