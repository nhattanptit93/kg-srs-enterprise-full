
import os
import json
import asyncio
from datetime import datetime, timezone

from core.llm import call_llm, call_llm_with_mcp, load_skill
from core.memory import VectorMemory
from core.logger import get_logger
from core.kg_client import load_graph, list_entities_summary

logger = get_logger("srs")
memory = VectorMemory()

_SKILL = load_skill("agents/srs/SKILLS.md")

_KG_MCP_SERVER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "core", "kg_server.py")
)

_DUAL_OUTPUT_INSTRUCTIONS = (
    "\n\n---\n\n"
    "## OUTPUT FORMAT (HARD RULE)\n\n"
    "Your final response (after any tool use) MUST contain exactly two sections "
    "separated by the markers below:\n\n"
    "<<<SRS_MARKDOWN>>>\n"
    "<the full SRS markdown document here, no fences around the whole thing>\n"
    "<<<SRS_SIDECAR_JSON>>>\n"
    "<a single raw JSON object — no fences, no prose — conforming exactly to:\n"
    "{\n"
    '  "document_id": "string",\n'
    '  "version": "string",\n'
    '  "generated_at": "ISO 8601 UTC timestamp",\n'
    '  "requirements": [\n'
    "    {\n"
    '      "id": "REQ-F-NNN",\n'
    '      "title": "string",\n'
    '      "priority": "Essential | Conditional | Optional",\n'
    '      "who": ["actor strings"],\n'
    '      "what": ["statement strings"],\n'
    '      "why": ["rationale strings"],\n'
    '      "when": ["Trigger: ...", "Preconditions: ...", "Schedule: ..."],\n'
    '      "how_options": ["Option A (CHOSEN): ... — Trade-off: ...", "Option B: ..."],\n'
    '      "edge_cases": ["Race: ...", "Boundary: ...", "Failure-network: ..."]\n'
    "    }\n"
    "  ]\n"
    "}>\n\n"
    "Sidecar rules:\n"
    "  - All 6 fields (who/what/why/when/how_options/edge_cases) are arrays of strings — never null, never absent.\n"
    "  - 'when' MUST contain exactly 3 entries prefixed Trigger:, Preconditions:, Schedule:.\n"
    "  - 'how_options' MUST contain >=1 entry; if multiple, exactly one MUST be marked (CHOSEN).\n"
    "  - 'edge_cases' contains one entry per applicable category from {Race, Time, Boundary, Stale, Network, Permission, i18n, Empty, Volume, Adversarial}, prefixed by category name.\n"
    "  - Sidecar must cover every REQ-F-NNN that appears in the SRS markdown above.\n"
    "  - The sidecar JSON object must start with '{' and end with '}'. Nothing after it.\n"
    "\n## KG QUERY GUIDANCE\n"
    "You have MCP tools to query the knowledge graph instead of being given the full JSON inline. "
    "Use them as needed:\n"
    "  - ``list_entities`` / ``list_entities(type='actor')`` — discover what's in the graph\n"
    "  - ``get_entity(entity_id)`` — fetch full schema + state_machine when writing §6 or AC\n"
    "  - ``list_relationships(from_entity=…)`` — confirm cardinality and inverse names\n"
    "  - ``list_events(actor=…)`` — find triggers for §3 REQ-F\n"
    "  - ``find_state_drift(entity_id, claimed_state)`` — sanity check before writing a state name\n"
    "Quote ``state_machine.states`` and field names verbatim from the entity record.\n"
)


def _split_dual_output(raw: str) -> tuple[str, dict | None]:
    md_marker = "<<<SRS_MARKDOWN>>>"
    json_marker = "<<<SRS_SIDECAR_JSON>>>"

    if md_marker in raw and json_marker in raw:
        after_md = raw.split(md_marker, 1)[1]
        markdown_part, json_part = after_md.split(json_marker, 1)
        markdown = markdown_part.strip()
    else:
        logger.warning("Dual-output markers missing — falling back to whole-response-as-markdown.")
        markdown = raw.strip()
        json_part = raw

    start = json_part.find("{")
    end = json_part.rfind("}")
    sidecar: dict | None = None
    if start != -1 and end != -1 and end > start:
        try:
            sidecar = json.loads(json_part[start : end + 1])
        except json.JSONDecodeError as e:
            logger.error(f"Sidecar JSON parse failed: {e}")

    return markdown, sidecar


def run(state):
    lessons = memory.search(state["graph"])

    # Seed the LLM with a lightweight entity index. Full entity records are
    # fetched on demand via ``get_entity`` MCP tool. This keeps the user
    # message ~1-2K tokens instead of dumping the entire graph (~5-10K).
    graph_obj = load_graph()
    if graph_obj is not None:
        index = list_entities_summary(graph_obj)
        index_text = json.dumps(index, ensure_ascii=False, indent=2)
        rel_count = len(graph_obj.get("relationships", []))
        event_count = len(graph_obj.get("events", []))
        index_summary = (
            f"Knowledge graph index ({len(index)} entities, {rel_count} relationships, "
            f"{event_count} events). Use MCP tools to fetch entity details when needed.\n\n"
            f"Entity index:\n{index_text}"
        )
        cached = index_summary + f"\n\nLessons:\n{lessons}"
    else:
        # Fallback: graph file missing — fall back to embedded raw JSON behaviour.
        logger.warning(
            "Graph JSON file not found — falling back to inline raw graph in user prompt."
        )
        cached = f"Graph (raw JSON):\n{state['graph']}\n\nLessons:\n{lessons}"

    suffix = (
        "\n\nNow produce the dual-output (SRS markdown + sidecar JSON). "
        "Query the KG MCP tools as you write each section."
    )

    system = _SKILL + _DUAL_OUTPUT_INSTRUCTIONS.replace(
        "ISO 8601 UTC timestamp",
        datetime.now(timezone.utc).isoformat(),
    )

    if graph_obj is not None:
        raw = asyncio.run(
            call_llm_with_mcp(
                {"cached": cached, "suffix": suffix},
                server_script=_KG_MCP_SERVER,
                system=system,
                max_turns=40,
            )
        )
    else:
        raw = call_llm({"cached": cached, "suffix": suffix}, system=system)

    srs_markdown, sidecar = _split_dual_output(raw)

    srs_path = "workspace/current_srs.md"
    sidecar_path = "workspace/current_srs.json"
    os.makedirs(os.path.dirname(srs_path), exist_ok=True)
    with open(srs_path, "w", encoding="utf-8") as f:
        f.write(srs_markdown)

    if sidecar is not None:
        with open(sidecar_path, "w", encoding="utf-8") as f:
            json.dump(sidecar, f, ensure_ascii=False, indent=2)
        req_count = len(sidecar.get("requirements", []))
        logger.info(f"Sidecar written to {sidecar_path} with {req_count} requirement(s).")
    else:
        logger.warning("Sidecar not written — JSON parse failed. SRS markdown still saved.")

    return {**state, "srs": srs_markdown, "srs_path": srs_path, "srs_sidecar_path": sidecar_path}
