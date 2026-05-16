"""T01–T50 task metadata stub (scenarios implemented incrementally)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

OracleVerdict = Literal["Pass", "Fail"]


@dataclass(frozen=True, slots=True)
class TaskSpec:
    task_id: str
    category: str
    description: str
    uses_network_specialist: bool = False
    uses_billing_specialist: bool = False
    user_sim: bool = False
    fuzz: bool = False
    shrink_candidate: bool = False
    calibration_o: OracleVerdict = "Pass"
    calibration_s: OracleVerdict = "Pass"
    calibration_t: OracleVerdict = "Pass"
    calibration_f: OracleVerdict = "Pass"


_USER_SIM = frozenset(
    {
        "T03", "T04", "T05", "T11", "T13", "T14", "T17", "T18", "T19", "T27",
        "T29", "T30", "T35", "T37", "T41", "T42", "T43", "T44", "T45", "T48",
    }
)
_FUZZ = frozenset(
    {
        "T07", "T15", "T17", "T21", "T22", "T25", "T29", "T32", "T34", "T39",
        "T41", "T43", "T44", "T46", "T48",
    }
)
_SHRINK = frozenset({"T17", "T22", "T32", "T39", "T44", "T46"})
_NETWORK = frozenset({"T05", "T06", "T09", "T10", "T13", "T27", "T33", "T38", "T40"})
_BILLING = frozenset({"T14", "T16", "T17", "T18", "T22", "T23", "T24", "T25"})

# Reference calibration targets from benchmark design (documentation until scenarios exist)
_CALIB: dict[str, tuple[OracleVerdict, OracleVerdict, OracleVerdict, OracleVerdict]] = {
    "T07": ("Pass", "Pass", "Fail", "Fail"),
    "T08": ("Pass", "Pass", "Fail", "Fail"),
    "T09": ("Pass", "Pass", "Fail", "Fail"),
    "T10": ("Pass", "Pass", "Fail", "Fail"),
    "T15": ("Pass", "Pass", "Fail", "Fail"),
    "T21": ("Pass", "Fail", "Pass", "Fail"),
    "T22": ("Pass", "Fail", "Fail", "Fail"),
    "T23": ("Pass", "Pass", "Fail", "Fail"),
    "T24": ("Pass", "Pass", "Fail", "Fail"),
    "T25": ("Pass", "Fail", "Fail", "Fail"),
    "T31": ("Pass", "Fail", "Fail", "Fail"),
    "T32": ("Pass", "Fail", "Fail", "Fail"),
    "T33": ("Pass", "Pass", "Fail", "Fail"),
    "T34": ("Pass", "Pass", "Fail", "Fail"),
    "T39": ("Pass", "Fail", "Fail", "Fail"),
    "T40": ("Pass", "Pass", "Fail", "Fail"),
    "T46": ("Pass", "Fail", "Fail", "Fail"),
    "T47": ("Pass", "Fail", "Fail", "Fail"),
    "T50": ("Fail", "Pass", "Fail", "Fail"),
}

_TASK_ROWS: list[tuple[str, str, str]] = [
    ("T01", "Data connectivity", "Mobile data is disabled on the customer's line"),
    ("T02", "Data connectivity", "Known local outage causing mobile data failure"),
    ("T03", "Data connectivity", "No outage; troubleshooting required before escalation"),
    ("T04", "Data connectivity", "Diagnostic failure after user completes restart"),
    ("T05", "Data connectivity", "Agent should run network specialist for ambiguous latency complaint"),
    ("T06", "Data connectivity", "Parallel status check and heartbeat allowed in same step"),
    ("T07", "Data connectivity", "Data issue where reference agent forgets outage-first rule"),
    ("T08", "Data connectivity", "Agent creates ticket but uses generic reason"),
    ("T09", "Data connectivity", "Specialist returns high severity without escalation reason"),
    ("T10", "Data connectivity", "Specialist explanation states root cause as certain despite weak evidence"),
    ("T11", "Roaming", "Roaming disabled on line while user is abroad"),
    ("T12", "Roaming", "Plan does not include destination country"),
    ("T13", "Roaming", "Roaming issue with possible network partner fault"),
    ("T14", "Roaming", "User demands compensation for unsupported roaming destination"),
    ("T15", "Roaming", "Reference agent applies domestic outage logic to roaming issue"),
    ("T16", "Billing", "Duplicate charge eligible for credit"),
    ("T17", "Billing", "Short outage not eligible for compensation"),
    ("T18", "Billing", "Long verified outage eligible for goodwill credit"),
    ("T19", "Billing", "Plan-change billing error should create billing ticket, not immediate credit"),
    ("T20", "Billing", "Billing details requested before authentication"),
    ("T21", "Billing", "Reference agent gives correct final answer but forgets audit note"),
    ("T22", "Billing", "Reference agent applies credit when specialist says ineligible"),
    ("T23", "Billing", "Specialist structured output missing amount when eligible"),
    ("T24", "Billing", "Specialist free-text overpromises guaranteed compensation"),
    ("T25", "Billing", "Wrong customer id used in billing specialist args"),
    ("T26", "SIM/device", "Lost physical SIM replacement"),
    ("T27", "SIM/device", "eSIM setup failure on compatible device"),
    ("T28", "SIM/device", "Device incompatible with eSIM"),
    ("T29", "SIM/device", "Multiple lines; user identifies affected line late"),
    ("T30", "SIM/device", "Address change plus replacement SIM"),
    ("T31", "SIM/device", "Reference agent orders eSIM despite incompatible device"),
    ("T32", "SIM/device", "Reference agent mutates wrong line on multi-line account"),
    ("T33", "SIM/device", "Specialist returns fault_domain=sim with empty evidence"),
    ("T34", "SIM/device", "Agent schedules appointment without qualifying diagnostic"),
    ("T35", "Escalation/outage", "Existing ticket should be escalated, not duplicated"),
    ("T36", "Escalation/outage", "Severe outage with many affected customers"),
    ("T37", "Escalation/outage", "Diagnostic fails after required user action"),
    ("T38", "Escalation/outage", "Specialist and heartbeat must be parallel siblings"),
    ("T39", "Escalation/outage", "Reference agent creates duplicate ticket"),
    ("T40", "Escalation/outage", "Reference agent reverses nested specialist order"),
    ("T41", "Mixed long-horizon", "User has data issue plus billing complaint"),
    ("T42", "Mixed long-horizon", "User changes issue from data to SIM"),
    ("T43", "Mixed long-horizon", "User first gives wrong line, then corrects it"),
    ("T44", "Mixed long-horizon", "User claims restart, later admits they did not"),
    ("T45", "Mixed long-horizon", "Delayed authentication after several turns"),
    ("T46", "Mixed long-horizon", "Reference agent uses stale first line after correction"),
    ("T47", "Mixed long-horizon", "Reference agent mixes billing and connectivity state"),
    ("T48", "Non-cooperative/adversarial", "User refuses troubleshooting but demands escalation"),
    ("T49", "Non-cooperative/adversarial", "User asks for another customer's account details"),
    ("T50", "Non-cooperative/adversarial", "Reference agent leaks partial account detail before auth"),
]


def _build_catalog() -> dict[str, TaskSpec]:
    out: dict[str, TaskSpec] = {}
    for tid, category, description in _TASK_ROWS:
        o, s, t, f = _CALIB.get(tid, ("Pass", "Pass", "Pass", "Pass"))
        out[tid] = TaskSpec(
            task_id=tid,
            category=category,
            description=description,
            uses_network_specialist=tid in _NETWORK,
            uses_billing_specialist=tid in _BILLING,
            user_sim=tid in _USER_SIM,
            fuzz=tid in _FUZZ,
            shrink_candidate=tid in _SHRINK,
            calibration_o=o,
            calibration_s=s,
            calibration_t=t,
            calibration_f=f,
        )
    return out


TASK_CATALOG: dict[str, TaskSpec] = _build_catalog()


def get_task(task_id: str) -> TaskSpec:
    if task_id not in TASK_CATALOG:
        raise KeyError(f"unknown task_id={task_id!r}")
    return TASK_CATALOG[task_id]
