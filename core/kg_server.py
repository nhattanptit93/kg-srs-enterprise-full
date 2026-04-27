"""KG-SRS Knowledge Graph MCP server.

Exposes the structured knowledge graph (``workspace/current_graph.json``)
to LLM agents as MCP tools. This lets downstream agents (SRS writer,
Verifier, Diagram generator) query the graph piecemeal instead of
shipping the full JSON inline every call — saving tokens and giving us
deterministic graph queries for verification.

Tools:
    list_entities(type=None, context=None)
    get_entity(entity_id)
    list_relationships(from_entity=None, to_entity=None, type=None)
    find_state_drift(entity_id, claimed_state)
    get_orphan_entities()
    list_events(actor=None)
    validate_trigger_coverage()

Run standalone for inspection:
    python core/kg_server.py
"""

from __future__ import annotations

import difflib
import json
import os
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("KG-SRS-Knowledge-Graph")

GRAPH_PATH = os.environ.get(
    "KG_GRAPH_PATH",
    os.path.join("workspace", "current_graph.json"),
)


def _load_graph() -> Optional[dict[str, Any]]:
    if not os.path.exists(GRAPH_PATH):
        return None
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _err(msg: str) -> str:
    return json.dumps({"error": msg}, ensure_ascii=False)


def _entity_summary(e: dict[str, Any]) -> dict[str, Any]:
    """Lightweight projection of an entity (no schema, no state_machine)."""
    desc = (e.get("description") or "").strip()
    return {
        "id": e.get("id"),
        "type": e.get("type"),
        "context": e.get("context"),
        "description": desc[:120],
        "field_count": len(e.get("schema", {}).get("fields", []) or []),
        "state_count": len(e.get("state_machine", {}).get("states", []) or []),
    }


@mcp.tool()
def list_entities(type: Optional[str] = None, context: Optional[str] = None) -> str:
    """List entities in the graph with a lightweight projection.

    Args:
        type: filter by entity type (``actor`` | ``domain`` | ``supporting``)
        context: filter by bounded context (e.g. ``ordering``, ``payment``)
    """
    g = _load_graph()
    if g is None:
        return _err(f"Graph not loaded at {GRAPH_PATH}")
    entities = g.get("entities", [])
    if type:
        entities = [e for e in entities if e.get("type") == type]
    if context:
        entities = [e for e in entities if e.get("context") == context]
    return json.dumps(
        [_entity_summary(e) for e in entities],
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def get_entity(entity_id: str) -> str:
    """Return the full entity record (schema, state_machine) for one entity id."""
    g = _load_graph()
    if g is None:
        return _err(f"Graph not loaded at {GRAPH_PATH}")
    for e in g.get("entities", []):
        if e.get("id") == entity_id:
            return json.dumps(e, ensure_ascii=False, indent=2)
    available = [e.get("id") for e in g.get("entities", [])]
    return _err(
        f"Entity {entity_id!r} not found. Available ({len(available)}): "
        + ", ".join(available[:30])
    )


@mcp.tool()
def list_relationships(
    from_entity: Optional[str] = None,
    to_entity: Optional[str] = None,
    type: Optional[str] = None,
) -> str:
    """List relationships, optionally filtered by source / target / type."""
    g = _load_graph()
    if g is None:
        return _err(f"Graph not loaded at {GRAPH_PATH}")
    rels = g.get("relationships", [])
    if from_entity:
        rels = [r for r in rels if r.get("from") == from_entity]
    if to_entity:
        rels = [r for r in rels if r.get("to") == to_entity]
    if type:
        rels = [r for r in rels if r.get("type") == type]
    return json.dumps(rels, ensure_ascii=False, indent=2)


@mcp.tool()
def find_state_drift(entity_id: str, claimed_state: str) -> str:
    """Check whether ``claimed_state`` exists verbatim in the entity's state_machine.states.

    Returns ``{"ok": true, ...}`` if exact match. Otherwise returns the actual state
    list and a closest-match suggestion — this is the core check for §3↔§6 SRS drift.
    """
    g = _load_graph()
    if g is None:
        return _err(f"Graph not loaded at {GRAPH_PATH}")
    for e in g.get("entities", []):
        if e.get("id") == entity_id:
            states = e.get("state_machine", {}).get("states", []) or []
            if claimed_state in states:
                return json.dumps(
                    {"ok": True, "entity": entity_id, "state": claimed_state},
                    ensure_ascii=False,
                )
            suggestion = difflib.get_close_matches(claimed_state, states, n=1, cutoff=0.5)
            return json.dumps(
                {
                    "ok": False,
                    "entity": entity_id,
                    "claimed": claimed_state,
                    "actual_states": states,
                    "suggestion": suggestion[0] if suggestion else None,
                },
                ensure_ascii=False,
            )
    return _err(f"Entity {entity_id!r} not found")


@mcp.tool()
def get_orphan_entities() -> str:
    """Return entities that participate in no relationship AND no event.

    Orphans are usually a graph-quality smell — they got declared but the
    domain logic never references them.
    """
    g = _load_graph()
    if g is None:
        return _err(f"Graph not loaded at {GRAPH_PATH}")
    used: set[str] = set()
    for r in g.get("relationships", []):
        if r.get("from"):
            used.add(r["from"])
        if r.get("to"):
            used.add(r["to"])
    for ev in g.get("events", []):
        if ev.get("actor"):
            used.add(ev["actor"])
        for eff in ev.get("effects", []) or []:
            for key in ("creates", "updates"):
                if key in eff and eff[key]:
                    used.add(eff[key])
            for link in eff.get("links", []) or []:
                # links are typically "a -> b" strings
                for part in str(link).split("->"):
                    used.add(part.strip())
    orphans = [e.get("id") for e in g.get("entities", []) if e.get("id") not in used]
    return json.dumps(orphans, ensure_ascii=False)


@mcp.tool()
def list_events(actor: Optional[str] = None) -> str:
    """List events, optionally filtered by actor entity id."""
    g = _load_graph()
    if g is None:
        return _err(f"Graph not loaded at {GRAPH_PATH}")
    events = g.get("events", [])
    if actor:
        events = [ev for ev in events if ev.get("actor") == actor]
    return json.dumps(events, ensure_ascii=False, indent=2)


@mcp.tool()
def validate_trigger_coverage() -> str:
    """Find state-machine transitions whose ``trigger`` has no matching event.

    Returns a list of ``{entity, transition}`` items. Empty list = healthy graph.
    """
    g = _load_graph()
    if g is None:
        return _err(f"Graph not loaded at {GRAPH_PATH}")
    event_names = {ev.get("name") for ev in g.get("events", []) if ev.get("name")}
    dangling = []
    for e in g.get("entities", []):
        for tr in e.get("state_machine", {}).get("transitions", []) or []:
            if tr.get("trigger") and tr["trigger"] not in event_names:
                dangling.append({"entity": e.get("id"), "transition": tr})
    return json.dumps(dangling, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
