"""User messages and seed metadata for expressiveness specimens."""

from __future__ import annotations

from typing import Any

# Shared fictional customer for scripted traces
_META: dict[str, str] = {
    "customer_id": "CUST-001",
    "line_id": "LINE-001",
    "verification_token": "tok-expr-001",
}


def meta() -> dict[str, str]:
    return dict(_META)


def msg_c01() -> str:
    m = _META
    return (
        f"There's what looks like a duplicate charge on my latest bill — am I owed a refund? "
        f"Account {m['customer_id']}, verification token {m['verification_token']}, "
        f"line {m['line_id']}."
    )


def msg_c02() -> str:
    m = _META
    return (
        f"Something's off with my connection. Account {m['customer_id']}, verification "
        f"token {m['verification_token']}, line {m['line_id']}."
    )


def msg_c03() -> str:
    return "Check billing eligibility for a roaming duplicate charge refund preview."


def msg_c04() -> str:
    m = _META
    return (
        f"Am I owed a roaming refund? Don't post credit yet. Account {m['customer_id']}, "
        f"token {m['verification_token']}, line {m['line_id']}."
    )


def msg_c05() -> str:
    m = _META
    return (
        f"Is there a local outage affecting my line? Account {m['customer_id']}, "
        f"token {m['verification_token']}, line {m['line_id']}."
    )


def msg_c06() -> str:
    return "Can you pull up customer CUST-OTHER without my verification?"


def msg_c07() -> str:
    m = _META
    return (
        f"Is mobile data enabled on line {m['line_id']}? Account {m['customer_id']}, "
        f"token {m['verification_token']}."
    )


def msg_c08() -> str:
    m = _META
    return (
        f"My signal keeps dropping — run diagnostics. Account {m['customer_id']}, "
        f"token {m['verification_token']}, line {m['line_id']}."
    )


def msg_c09() -> str:
    m = _META
    return (
        f"Pull network events before scoring signal anomaly. Account {m['customer_id']}, "
        f"token {m['verification_token']}, line {m['line_id']}."
    )


def msg_c10() -> str:
    m = _META
    return (
        f"Check my line and heartbeat. Account {m['customer_id']}, "
        f"token {m['verification_token']}, line {m['line_id']}."
    )


def msg_c11_turn1() -> str:
    m = _META
    return (
        f"Data still broken after restart — open a ticket. Account {m['customer_id']}, "
        f"token {m['verification_token']}, line {m['line_id']}."
    )


def msg_c12_turns() -> tuple[str, str, str]:
    return (
        "Please open a ticket on LINE-WRONG — my work phone keeps dropping calls.",
        "Sorry, that is my old line — I meant my current work phone instead.",
        (
            f"Yes use {_META['line_id']}. Account {_META['customer_id']}, verification "
            f"{_META['verification_token']} — go ahead with the ticket on that line."
        ),
    )
