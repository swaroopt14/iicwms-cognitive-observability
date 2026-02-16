"""
Shared LangGraph runtime helpers for agent-level orchestration.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Iterable, List, Tuple

try:
    from langgraph.graph import StateGraph, END
except ModuleNotFoundError:
    StateGraph = None
    END = None


NodeFn = Callable[[Dict[str, Any]], Dict[str, Any]]


def is_langgraph_enabled() -> bool:
    """
    Global toggle for LangGraph-based agent execution.
    Falls back to deterministic in-process flow when unavailable.
    """
    enabled = os.getenv("ENABLE_LANGGRAPH_AGENTS", os.getenv("ENABLE_LANGGRAPH", "false"))
    return enabled.lower().strip() == "true" and StateGraph is not None and END is not None


def run_linear_graph(
    initial_state: Dict[str, Any],
    nodes: Iterable[Tuple[str, NodeFn]],
) -> Dict[str, Any]:
    """
    Execute a linear sequence of named nodes using LangGraph.
    If graph execution fails, run the same steps sequentially.
    """
    node_list = list(nodes)
    if not node_list:
        return initial_state

    if not is_langgraph_enabled():
        return _run_sequential(initial_state, node_list)

    try:
        graph = StateGraph(dict)
        for name, fn in node_list:
            graph.add_node(name, fn)
        graph.set_entry_point(node_list[0][0])
        for i in range(len(node_list) - 1):
            graph.add_edge(node_list[i][0], node_list[i + 1][0])
        graph.add_edge(node_list[-1][0], END)
        compiled = graph.compile()
        return compiled.invoke(dict(initial_state))
    except Exception:
        return _run_sequential(initial_state, node_list)


def _run_sequential(
    state: Dict[str, Any],
    nodes: List[Tuple[str, NodeFn]],
) -> Dict[str, Any]:
    current = dict(state)
    for _, fn in nodes:
        current = fn(current)
    return current
