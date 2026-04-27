
import os
import json
from datetime import datetime, timezone
from core.llm import call_llm, load_skill
from core.memory import VectorMemory
from core.logger import get_logger

logger = get_logger("srs")
memory = VectorMemory()

_SKILL = load_skill("agents/srs/SKILLS.md")

_SIDECAR_SYSTEM = (
    "You are a strict structured-data extractor. Given a Software Requirements "
    "Specification (SRS) markdown document, extract every functional requirement "
    "(REQ-F-NNN) into a JSON object conforming exactly to this schema:\n\n"
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
    "}\n\n"
    "Rules:\n"
    "  - All 6 fields (who, what, why, when, how_options, edge_cases) are arrays "
    "of strings — never null, never absent.\n"
    "  - 'when' MUST contain exactly 3 entries prefixed Trigger:, Preconditions:, "
    "Schedule:.\n"
    "  - 'how_options' MUST contain >=1 entry; if multiple, exactly one MUST be "
    "marked (CHOSEN).\n"
    "  - 'edge_cases' contains one entry per applicable category from "
    "{Race, Time, Boundary, Stale, Network, Permission, i18n, Empty, Volume, "
    "Adversarial}, prefixed by the category name.\n"
    "  - Output ONLY raw JSON. No markdown fences. No prose. The first character "
    "must be '{' and the last must be '}'.\n"
)


def _emit_sidecar(srs_markdown: str, sidecar_path: str) -> None:
    user = (
        "Extract all REQ-F entries from this SRS into the JSON schema. "
        f"Set generated_at to {datetime.now(timezone.utc).isoformat()}.\n\n"
        f"SRS document:\n{srs_markdown}"
    )
    raw = call_llm(user, system=_SIDECAR_SYSTEM)
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.error("Sidecar emission: could not locate JSON object in LLM output.")
        return
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as e:
        logger.error(f"Sidecar emission: JSON parse failed: {e}")
        return
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    req_count = len(data.get("requirements", []))
    logger.info(f"Sidecar written to {sidecar_path} with {req_count} requirement(s).")


def run(state):
    lessons = memory.search(state["graph"])
    user = f"Graph:\n{state['graph']}\n\nLessons:\n{lessons}"
    srs = call_llm(user, system=_SKILL)

    srs_path = "workspace/current_srs.md"
    sidecar_path = "workspace/current_srs.json"
    os.makedirs(os.path.dirname(srs_path), exist_ok=True)
    with open(srs_path, "w", encoding="utf-8") as f:
        f.write(srs)

    _emit_sidecar(srs, sidecar_path)

    return {**state, "srs": srs, "srs_path": srs_path, "srs_sidecar_path": sidecar_path}
