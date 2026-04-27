
import json

from core.llm import call_llm, load_skill
from core.logger import get_logger
from core.output_export import export_agent_output

logger = get_logger("graph")

_SKILL = load_skill("agents/graph/SKILLS.md")


def _try_parse_graph(raw: str):
    """Best-effort JSON parse. Returns parsed dict or None on failure."""
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        logger.warning(f"Could not parse graph JSON for export: {e}")
        return None


def run(state):
    user = f"Use Case:\n{state['usecase']}"

    if state.get("qa") and state.get("graph"):
        logger.info("Handling LOGIC feedback loop.")
        user += f"\n\nPrevious Graph:\n{state['graph']}\n\nQA Feedback (Logic Errors to Fix):\n{state['qa']}\n\nPlease output a corrected Knowledge Graph JSON."

    g = call_llm(user, system=_SKILL)

    parsed = _try_parse_graph(g)
    output_payload = parsed if parsed is not None else {"raw": g}
    metadata = {
        "iteration": state.get("iterations", 0),
        "loop_mode": "logic_rebuild" if state.get("qa") and state.get("graph") else "initial",
        "parse_ok": parsed is not None,
    }
    if parsed is not None:
        metadata["entity_count"] = len(parsed.get("entities", []))
        metadata["relationship_count"] = len(parsed.get("relationships", []))
        metadata["event_count"] = len(parsed.get("events", []))

    export_agent_output("graph", output=output_payload, metadata=metadata)

    return {**state, "graph": g}
