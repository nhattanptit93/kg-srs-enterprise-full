"""Sync helpers to query the knowledge graph from Python code.

For LLM agents that need *interactive* graph access (SRS writer), use the
MCP server (``core/kg_server.py``) via ``call_llm_with_mcp``.

For Python code that needs *deterministic* graph queries (Verify agent
running cross-check tooling, Diagram agent listing entities), call the
helpers below directly — they read the same ``workspace/current_graph.json``
and reuse the same logic without paying subprocess + tool-loop overhead.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

GRAPH_PATH = os.environ.get(
    "KG_GRAPH_PATH",
    os.path.join("workspace", "current_graph.json"),
)


def load_graph() -> Optional[dict[str, Any]]:
    if not os.path.exists(GRAPH_PATH):
        return None
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def list_entities_summary(graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Lightweight projection — used to seed SRS prompt without dumping full graph."""
    out = []
    for e in graph.get("entities", []):
        desc = (e.get("description") or "").strip()
        out.append(
            {
                "id": e.get("id"),
                "type": e.get("type"),
                "context": e.get("context"),
                "description": desc[:120],
                "states": e.get("state_machine", {}).get("states", []) or [],
            }
        )
    return out


def find_state_drift(
    graph: dict[str, Any],
    entity_id: str,
    claimed_state: str,
) -> dict[str, Any]:
    for e in graph.get("entities", []):
        if e.get("id") == entity_id:
            states = e.get("state_machine", {}).get("states", []) or []
            return {
                "ok": claimed_state in states,
                "entity": entity_id,
                "claimed": claimed_state,
                "actual_states": states,
            }
    return {"ok": False, "entity": entity_id, "error": "entity_not_found"}


def get_orphan_entities(graph: dict[str, Any]) -> list[str]:
    used: set[str] = set()
    for r in graph.get("relationships", []):
        if r.get("from"):
            used.add(r["from"])
        if r.get("to"):
            used.add(r["to"])
    for ev in graph.get("events", []):
        if ev.get("actor"):
            used.add(ev["actor"])
        for eff in ev.get("effects", []) or []:
            for key in ("creates", "updates"):
                if key in eff and eff[key]:
                    used.add(eff[key])
            for link in eff.get("links", []) or []:
                for part in str(link).split("->"):
                    used.add(part.strip())
    return [e.get("id") for e in graph.get("entities", []) if e.get("id") not in used]


def validate_trigger_coverage(graph: dict[str, Any]) -> list[dict[str, Any]]:
    event_names = {ev.get("name") for ev in graph.get("events", []) if ev.get("name")}
    dangling = []
    for e in graph.get("entities", []):
        for tr in e.get("state_machine", {}).get("transitions", []) or []:
            if tr.get("trigger") and tr["trigger"] not in event_names:
                dangling.append({"entity": e.get("id"), "transition": tr})
    return dangling


# Match patterns like ``order.state == 'ready'`` or ``Order.state = "ready"``
# whether or not the whole expression sits inside backticks.
_STATE_REF_RE = re.compile(
    r"\b([a-zA-Z][a-zA-Z0-9_]*)\.state\s*[=:]+\s*['\"]?([a-zA-Z][a-zA-Z0-9_]*)['\"]?",
)
# Match enum-style state lists: ``state ∈ {a, b, c}`` or ``state in {a, b}``
_STATE_ENUM_RE = re.compile(
    r"\bstate\s*(?:∈|in)\s*\{([^}\n]+)\}",
    re.IGNORECASE,
)


def scan_srs_for_state_drift(srs_markdown: str, graph: dict[str, Any]) -> list[dict[str, Any]]:
    """Heuristic scan: find state references in SRS that don't match graph states.

    Catches two common drift patterns:
        ``order.state == 'ready'`` when graph has ``ready_for_pickup``
        ``state ∈ {ready, picked, delivered}`` when graph differs

    Returns one record per drift, suitable for feeding into the verifier.
    """
    drifts: list[dict[str, Any]] = []
    entity_states = {
        (e.get("id") or "").lower(): e.get("state_machine", {}).get("states", []) or []
        for e in graph.get("entities", [])
    }

    for m in _STATE_REF_RE.finditer(srs_markdown):
        ent = m.group(1).lower()
        state = m.group(2)
        if ent in entity_states and state and state not in entity_states[ent]:
            drifts.append(
                {
                    "kind": "inline_ref",
                    "entity": ent,
                    "claimed": state,
                    "graph_states": entity_states[ent],
                }
            )

    return drifts
