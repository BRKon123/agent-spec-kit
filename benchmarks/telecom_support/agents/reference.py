"""Build coordinator + specialist LangGraph agents for the telco benchmark."""

from __future__ import annotations

import json
import os
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.tools import BaseTool

from agents.prompts import (
    billing_specialist_prompt,
    fault_system_prompt,
    network_specialist_prompt,
    reference_system_prompt,
)
from agents.schemas import BillingDecision, NetworkAssessment
from store.store import TelcoStore
from store.fault_variants import maybe_auto_credit_after_billing
from store.tools import (
    make_billing_specialist_tools,
    make_coordinator_tools,
    make_network_specialist_tools,
)


def require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "TelcoSupportBench requires OPENAI_API_KEY "
            "(install dependency-groups dev and export the key)."
        )


def _structured_response_json(out: dict[str, Any], *, variant: str = "reference") -> str:
    sr = out.get("structured_response")
    if sr is not None:
        if hasattr(sr, "model_dump_json"):
            raw = sr.model_dump(mode="json")
        elif isinstance(sr, dict):
            raw = sr
        else:
            raw = None
        if raw is not None and variant == "fault_structured_output":
            raw = _mutate_structured_fault_payload(raw)
            return json.dumps(raw)
        if hasattr(sr, "model_dump_json"):
            return sr.model_dump_json()
        return json.dumps(sr) if isinstance(sr, dict) else str(sr)
    last = out["messages"][-1]
    content = getattr(last, "content", last)
    return str(content)


def _mutate_structured_fault_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Fault-only: emit JSON that may fail task matchers (never used for reference)."""
    out = dict(raw)
    if "fault_domain" in out:
        if out.get("fault_domain") != "unknown":
            out["evidence"] = []
        if out.get("severity") == "high" and out.get("recommended_action") == "create_ticket":
            out["escalation_reason"] = None
        if "user_explanation" in out:
            out["user_explanation"] = (
                f"{out['user_explanation']} The root cause is definitely confirmed."
            )
    if "eligible" in out:
        if out.get("eligible") is True:
            out["amount"] = None
        else:
            out["amount"] = 50.0
        out["user_explanation"] = (
            "We guarantee a full refund and compensation will be applied immediately."
        )
    return out


def build_graph(store: TelcoStore, *, variant: str = "reference") -> object:
    require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)

    network_specialist = create_agent(
        llm,
        tools=make_network_specialist_tools(store, variant=variant),
        response_format=NetworkAssessment,
        system_prompt=network_specialist_prompt(variant=variant),
    )
    billing_specialist = create_agent(
        llm,
        tools=make_billing_specialist_tools(store, variant=variant),
        response_format=BillingDecision,
        system_prompt=billing_specialist_prompt(
            variant=variant,
            task_id=str(store.seed_meta.get("task_id", "")),
        ),
    )

    @tool
    def run_network_diagnostics_specialist(line_id: str, complaint: str) -> str:
        """Delegate connectivity/roaming/outage diagnostics to NetworkDiagnosticsSpecialist.

        For latency spikes or ambiguous network issues, call in the same agent turn as
        authenticate_customer (do not stop after auth alone).
        """
        out = network_specialist.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"line_id={line_id.strip()}\n"
                            f"postcode={store.seed_meta.get('postcode', 'SW1A1AA')}\n"
                            f"complaint: {complaint.strip()}"
                        ),
                    }
                ]
            }
        )
        return _structured_response_json(out, variant=variant)

    @tool
    def run_billing_policy_specialist(customer_id: str, issue: str) -> str:
        """Delegate refund/compensation policy to BillingPolicySpecialist.

        Use after auth for duplicate charges, brief outages, and compensation requests.
        """
        out = billing_specialist.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"customer_id={customer_id.strip()}\n"
                            f"issue: {issue.strip()}"
                        ),
                    }
                ]
            }
        )
        raw = _structured_response_json(out, variant=variant)
        maybe_auto_credit_after_billing(store, variant, raw)
        return raw

    coordinator_tools: list[BaseTool] = [
        *make_coordinator_tools(store, variant=variant),
        run_network_diagnostics_specialist,
        run_billing_policy_specialist,
    ]
    prompt = (
        reference_system_prompt()
        if variant == "reference"
        else fault_system_prompt(variant)
    )
    return create_agent(llm, tools=coordinator_tools, system_prompt=prompt)
