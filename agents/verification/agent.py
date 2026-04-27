import os
import json
from core.llm import call_llm, load_skill
from core.logger import get_logger
from core.output_export import export_agent_output

logger = get_logger("verify")

_SKILL = load_skill("agents/verification/SKILLS.md")


def run(state):
    srs_content = state.get("srs", "")
    if state.get("srs_path") and os.path.exists(state["srs_path"]):
        with open(state["srs_path"], "r", encoding="utf-8") as f:
            srs_content = f.read()

    qa_raw = call_llm(f"SRS:\n{srs_content}", system=_SKILL)

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
    export_agent_output(
        "verify",
        output=output_payload,
        metadata={
            "iteration": iterations,
            "score": score,
            "issue_type": issue,
            "parse_ok": parsed_qa is not None,
        },
    )

    return {**state, "qa": qa_raw, "score": score, "issue_type": issue, "iterations": iterations}
