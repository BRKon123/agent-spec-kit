"""Structured specialist outputs for TelcoSupportBench (response_format models)."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class NetworkAssessment(BaseModel):
    """Structured output from NetworkDiagnosticsSpecialist."""

    line_id: str
    fault_domain: Literal["device", "sim", "network", "plan", "roaming", "unknown"]
    severity: Literal["low", "medium", "high"]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    recommended_action: Literal[
        "ask_user_step",
        "create_ticket",
        "order_replacement_sim",
        "wait_for_outage_resolution",
        "no_action",
    ]
    escalation_reason: str | None = None
    user_explanation: str

    @model_validator(mode="after")
    def _conditional_fields(self) -> NetworkAssessment:
        if self.severity == "high" and self.recommended_action == "create_ticket":
            if not (self.escalation_reason and self.escalation_reason.strip()):
                raise ValueError("escalation_reason required for high severity create_ticket")
        if self.recommended_action == "ask_user_step" and self.escalation_reason:
            raise ValueError("escalation_reason forbidden when recommended_action is ask_user_step")
        if self.fault_domain != "unknown" and not self.evidence:
            raise ValueError("evidence required when fault_domain is not unknown")
        return self


class BillingDecision(BaseModel):
    """Structured output from BillingPolicySpecialist."""

    customer_id: str
    eligible: bool
    reason_code: Literal[
        "duplicate_charge",
        "verified_long_outage",
        "plan_change_error",
        "ineligible_short_outage",
        "insufficient_evidence",
    ]
    amount: Decimal | None = None
    requires_audit_note: bool
    policy_quote: str
    user_explanation: str

    @model_validator(mode="after")
    def _conditional_fields(self) -> BillingDecision:
        if self.eligible:
            if self.amount is None or self.amount <= 0:
                raise ValueError("positive amount required when eligible")
        elif self.amount is not None:
            raise ValueError("amount forbidden when not eligible")
        if self.amount is not None and not self.requires_audit_note:
            raise ValueError("requires_audit_note must be true when amount is present")
        return self
