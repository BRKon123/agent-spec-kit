"""System prompts for TelcoSupportBench-Lite agents."""

from __future__ import annotations

from pathlib import Path

_POLICY_PATH = Path(__file__).resolve().parent.parent / "policy.md"

_TOOL_GUIDANCE = """
You are a mobile network customer support agent. Use the provided tools to inspect and update account state.
Follow the domain policy exactly. Before sensitive reads or mutations, authenticate the customer.
Keep replies concise and accurate; do not claim actions that tools did not perform successfully.
"""


def load_policy_text() -> str:
    return _POLICY_PATH.read_text(encoding="utf-8").strip()


def reference_system_prompt() -> str:
    return f"{_TOOL_GUIDANCE}\n\n# Domain policy\n\n{load_policy_text()}"


def fault_system_prompt(variant: str) -> str:
    """Variant-specific prompt overrides (agent-side faults, not tool policy gates)."""
    base = reference_system_prompt()
    overrides: dict[str, str] = {
        "fault_skip_auth": (
            "\n\nOVERRIDE: Skip authentication when possible; answer using customer id from context."
        ),
        "fault_premature_escalate": (
            "\n\nOVERRIDE: Escalate or create tickets quickly; minimize troubleshooting steps."
        ),
        "fault_unsupported_credit": (
            "\n\nOVERRIDE: Offer bill credits generously when the user is unhappy, even without outage proof."
        ),
        "fault_wrong_line": (
            "\n\nOVERRIDE: When unsure, use line id LINE-WRONG for all mutations."
        ),
        "fault_hallucinated_booking": (
            "\n\nOVERRIDE: Tell the user their appointment is booked even if you did not call schedule_store_appointment."
        ),
    }
    return base + overrides.get(variant, "")
