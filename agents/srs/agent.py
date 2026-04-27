
import os
import json
from datetime import datetime, timezone
from core.llm import call_llm, load_skill
from core.memory import VectorMemory
from core.logger import get_logger
from core.output_export import export_agent_output

logger = get_logger("srs")
memory = VectorMemory()

_SKILL = load_skill("agents/srs/SKILLS.md")

_DUAL_OUTPUT_INSTRUCTIONS = (
    "\n\n---\n\n"
    "## OUTPUT FORMAT (HARD RULE)\n\n"
    "Your response MUST contain exactly two sections separated by the markers below:\n\n"
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
)


def _split_dual_output(raw: str) -> tuple[str, dict | None]:
    """Split LLM response into (markdown, sidecar_dict).

    Falls back gracefully: if markers are missing, treats the whole response
    as markdown and tries best-effort JSON extraction.
    """
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
    user = f"Graph:\n{state['graph']}\n\nLessons:\n{lessons}"

    system = _SKILL + _DUAL_OUTPUT_INSTRUCTIONS.replace(
        "ISO 8601 UTC timestamp",
        datetime.now(timezone.utc).isoformat(),
    )

    raw = call_llm(user, system=system)
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
        logger.warning(f"Sidecar not written — JSON parse failed. SRS markdown still saved.")

    return {**state, "srs": srs_markdown, "srs_path": srs_path, "srs_sidecar_path": sidecar_path}
