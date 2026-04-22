"""Framework-neutral normalized agent events."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, TypeAlias


def new_event_id(*, prefix: str = "") -> str:
    """Return a new opaque event id, optionally prefixed for debugging."""
    u = uuid.uuid4().hex
    return f"{prefix}{u}" if prefix else u


@dataclass
class BaseEvent:
    """Shared fields for all tracked agent events."""

    turn_index: int | None = None
    event_id: str | None = None
    source_path: tuple[str, ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list["AgentEvent"] = field(default_factory=list)

    def _rich_node_label(self) -> str:
        """One-line label for Rich tree display (override in subclasses)."""
        return type(self).__name__

    def _rich_append_children(self, parent_branch: Any) -> None:
        """Append ``children`` under ``parent_branch`` (a Rich ``Tree`` node)."""
        for ch in self.children:
            branch = parent_branch.add(ch._rich_node_label())
            ch._rich_append_children(branch)

    def to_rich_tree(self, *, title: str | None = None) -> Any:
        """
        Build a Rich ``Tree`` for this node and all descendants.

        Requires the optional ``rich`` package.
        """
        try:
            from rich.tree import Tree
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "Rich is required for to_rich_tree(); install with `pip install rich`."
            ) from e

        label = title if title is not None else self._rich_node_label()
        t = Tree(label)
        self._rich_append_children(t)
        return t


@dataclass
class ToolCallEvent(BaseEvent):
    """One tool invocation with a result or error."""

    tool_name: str = ""
    args: Any = None
    result: Any = None
    error: str | None = None

    def _rich_node_label(self) -> str:
        if self.error:
            return f"{self.tool_name}  error={self.error!r}"
        if self.result is not None:
            s = repr(self.result)
            if len(s) > 72:
                s = s[:69] + "..."
            return f"{self.tool_name}  result={s}"
        return f"{self.tool_name}  (pending)"


@dataclass
class AgentTurnEvent(BaseEvent):
    """One agent response to one user message (completed turn)."""

    user_input: Any = None
    agent_output: Any = None
    error: str | None = None

    def _rich_node_label(self) -> str:
        path = ".".join(self.source_path) if self.source_path else "root"
        return f"AgentTurn ({path})"


@dataclass
class UserTurnEvent(BaseEvent):
    """Synthetic root for failure traces: one user-side or scripted user line."""

    content: Any = None
    error: str | None = None

    def _rich_node_label(self) -> str:
        s = self.content
        s = s if s is not None else ""
        if not isinstance(s, str):
            s = repr(s)
        if self.error:
            t = f"{s}  [error: {self.error!r}]"
        else:
            t = s
        if len(t) > 72:
            t = t[:69] + "..."
        return f"UserTurn: {t}"


AgentEvent: TypeAlias = ToolCallEvent | AgentTurnEvent | UserTurnEvent


def print_rich_event_trace(
    console: Any,
    roots: Sequence[BaseEvent],
    *,
    title: str = "Event trace (till failure)",
) -> None:
    """
    Pretty-print one or more event trees (e.g. ``TurnResult.events``) using Rich.
    For mixed conversation + agent trees, use roots built from
    :func:`conversation_turns_to_event_trace` in :mod:`agent_spec_kit.failures`.

    Requires the optional ``rich`` package.
    """
    try:
        from rich.tree import Tree
    except ImportError as e:  # pragma: no cover
        raise ImportError(
            "Rich is required for print_rich_event_trace(); install with `pip install rich`."
        ) from e

    tr = Tree(title)
    for root in roots:
        branch = tr.add(root._rich_node_label())
        root._rich_append_children(branch)
    console.print(tr)


__all__ = [
    "AgentEvent",
    "AgentTurnEvent",
    "BaseEvent",
    "ToolCallEvent",
    "UserTurnEvent",
    "new_event_id",
    "print_rich_event_trace",
]
