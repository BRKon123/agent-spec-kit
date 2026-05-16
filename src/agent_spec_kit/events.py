"""Framework-neutral normalized agent events."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, TypeAlias

from agent_spec_kit.console_format import format_value_for_console


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
            formatted = format_value_for_console(self.result)
            if "\n" in formatted:
                indented = "\n".join(f"    {line}" for line in formatted.splitlines())
                return f"{self.tool_name}\n  result:\n{indented}"
            return f"{self.tool_name}  result={formatted}"
        return f"{self.tool_name}  (pending)"


@dataclass
class AgentTurnEvent(BaseEvent):
    """One agent response to one user message (completed turn)."""

    user_input: Any = None
    agent_output: Any = None
    error: str | None = None

    def _rich_node_label(self) -> str:
        if not self.source_path:
            prefix = "AgentTurn"
        else:
            path = ".".join(self.source_path)
            prefix = f"AgentTurn ({path})"
        s = self.agent_output
        s = s if s is not None else ""
        if not isinstance(s, str):
            s = repr(s)
        if self.error:
            t = f"{s}  [error: {self.error!r}]"
        else:
            t = s
        if len(t) > 72:
            t = t[:69] + "..."
        return f"{prefix}: {t}"


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


def collect_event_errors(
    roots: AgentEvent | Sequence[AgentEvent],
    *,
    include_tools: bool = True,
) -> tuple[str, ...]:
    """Collect non-empty ``error`` strings from an event tree (depth-first)."""

    def _walk(node: AgentEvent, out: list[str]) -> None:
        if isinstance(node, AgentTurnEvent) and node.error:
            if node.source_path:
                label = ".".join(node.source_path)
                out.append(f"{label}: {node.error}")
            else:
                out.append(node.error)
        elif include_tools and isinstance(node, ToolCallEvent) and node.error:
            name = node.tool_name or "tool"
            out.append(f"{name}: {node.error}")
        for ch in node.children:
            _walk(ch, out)

    if isinstance(roots, AgentTurnEvent | ToolCallEvent | UserTurnEvent):
        items: Sequence[AgentEvent] = (roots,)
    else:
        items = roots
    found: list[str] = []
    for root in items:
        _walk(root, found)
    return tuple(found)


def print_rich_event_trace(
    console: Any,
    roots: Sequence[BaseEvent],
    *,
    title: str = "Event trace",
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
    "collect_event_errors",
    "new_event_id",
    "print_rich_event_trace",
]
