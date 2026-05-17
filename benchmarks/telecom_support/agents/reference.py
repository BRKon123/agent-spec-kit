"""Build coordinator + specialist LangGraph agents for the telco benchmark."""

from __future__ import annotations

import json
import os
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.tools import BaseTool

from agents.calibration_steering import (
    billing_specialist_extra,
    calibration_steering_suffix,
    network_specialist_extra,
)
from agents.prompts import (
    billing_specialist_prompt,
    fault_system_prompt,
    network_specialist_prompt,
    reference_system_prompt,
)
from agents.schemas import BillingDecision, NetworkAssessment
from store.store import TelcoStore
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


def calibration_steering_enabled() -> bool:
    """True only when TELCO_ENABLE_CALIBRATION_STEERING=1 (opt-in calibration hints)."""
    if os.environ.get("TELCO_DISABLE_CALIBRATION_STEERING", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return False
    return os.environ.get("TELCO_ENABLE_CALIBRATION_STEERING", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _structured_response_json(out: dict[str, Any]) -> str:
    sr = out.get("structured_response")
    if sr is not None:
        if hasattr(sr, "model_dump_json"):
            return sr.model_dump_json()
        return json.dumps(sr) if isinstance(sr, dict) else str(sr)
    last = out["messages"][-1]
    content = getattr(last, "content", last)
    return str(content)


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
        system_prompt=billing_specialist_prompt(variant=variant),
    )

    @tool
    def run_network_diagnostics_specialist(line_id: str, complaint: str) -> str:
        """Delegate connectivity/roaming/outage diagnostics to NetworkDiagnosticsSpecialist."""
        out = network_specialist.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"line_id={line_id.strip()}\n"
                            f"postcode={store.seed_meta.get('postcode', 'SW1A1AA')}\n"
                            f"complaint: {complaint.strip()}"
                            f"{network_specialist_extra(store) if calibration_steering_enabled() else ''}"
                        ),
                    }
                ]
            }
        )
        return _structured_response_json(out)

    @tool
    def run_billing_policy_specialist(customer_id: str, issue: str) -> str:
        """Delegate refund/compensation policy to BillingPolicySpecialist."""
        out = billing_specialist.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"customer_id={customer_id.strip()}\n"
                            f"issue: {issue.strip()}"
                            f"{billing_specialist_extra(store) if calibration_steering_enabled() else ''}"
                        ),
                    }
                ]
            }
        )
        return _structured_response_json(out)

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
    if variant == "reference" and calibration_steering_enabled():
        prompt = prompt + calibration_steering_suffix(store)
    return create_agent(llm, tools=coordinator_tools, system_prompt=prompt)
