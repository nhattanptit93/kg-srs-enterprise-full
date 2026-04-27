import os
import json
from core.llm import call_llm, load_skill
from core.logger import get_logger
from core.output_export import export_agent_output
from core.kg_client import (
    load_graph,
    get_orphan_entities,
    validate_trigger_coverage,
    scan_srs_for_state_drift,
)

logger = get_logger("verify")

_SKILL = load_skill("agents/verification/SKILLS.md")


def _run_deterministic_checks(srs_content: str) -> dict:
    """Pure-Python checks that don't need LLM. These are ground truth — feed
    their results into the LLM scorer prompt so the LLM doesn't have to
    re-derive them (and can't hallucinate them away).
    """
    graph = load_graph()
    if graph is None:
        logger.warning("Graph JSON not loaded; skipping deterministic checks.")
        return {"available": False}

    orphans = get_orphan_entities(graph)
    dangling_triggers = validate_trigger_coverage(graph)
    state_drifts = scan_srs_for_state_drift(srs_content, graph)

    return {
        "available": True,
        "orphan_entities": orphans,
        "dangling_triggers": dangling_triggers,
        "state_drifts": state_drifts,
        "summary": {
            "orphan_count": len(orphans),
            "dangling_trigger_count": len(dangling_triggers),
            "state_drift_count": len(state_drifts),
        },
    }


def run(state):
    srs_content = state.get("srs", "")
    if state.get("srs_path") and os.path.exists(state["srs_path"]):
        with open(state["srs_path"], "r", encoding="utf-8") as f:
            srs_content = f.read()

    det = _run_deterministic_checks(srs_content)
    det_block = ""
    if det.get("available"):
        det_block = (
            "\n\n## DETERMINISTIC CHECKS (ground truth — do not re-derive)\n"
            + json.dumps(det, ensure_ascii=False, indent=2)
            + "\n\nFactor these findings into your score and include each in your "
            "issues list with high severity if non-empty."
        )

    qa_raw = call_llm(
        {"cached": f"SRS:\n{srs_content}", "suffix": det_block},
        system=_SKILL,
    )

    score = 7
    issue = "CONSISTENCY"
    parsed_qa = None

    try:
        # Strip potential markdown formatting or prefix prose
        start_idx = qa_raw.find("{")
        end_idx = qa_raw.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = qa_raw[start_idx:end_idx + 1]
            parsed_qa = json.loads(json_str)
            score = int(parsed_qa.get("score", 7))
            issue = parsed_qa.get("issue_type", "CONSISTENCY")
        else:
            logger.warning("Could not find JSON block in LLM response.")
    except Exception as e:
        logger.error(f"Failed to parse verification JSON: {e}")

    iterations = state.get("iterations", 0) + 1

    output_payload = parsed_qa if parsed_qa is not None else {"raw": qa_raw}
    if det.get("available"):
        output_payload = {
            **(output_payload if isinstance(output_payload, dict) else {"raw": qa_raw}),
            "deterministic_checks": det,
        }

    export_agent_output(
        "verify",
        output=output_payload,
        metadata={
            "iteration": iterations,
            "score": score,
            "issue_type": issue,
            "parse_ok": parsed_qa is not None,
            "det_orphan_count": det.get("summary", {}).get("orphan_count"),
            "det_dangling_trigger_count": det.get("summary", {}).get("dangling_trigger_count"),
            "det_state_drift_count": det.get("summary", {}).get("state_drift_count"),
        },
    )

    return {**state, "qa": qa_raw, "score": score, "issue_type": issue, "iterations": iterations}
