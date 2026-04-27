import os
import asyncio
from core.llm import call_llm_with_mcp, load_skill
from core.logger import get_logger
from core.output_export import export_agent_output

logger = get_logger("refine")

_SKILL = load_skill("agents/refine/SKILLS.md")

def run(state):
    srs_path = state.get("srs_path", "workspace/current_srs.md")

    if not os.path.exists(srs_path) and "srs" in state:
        os.makedirs(os.path.dirname(srs_path), exist_ok=True)
        with open(srs_path, "w", encoding="utf-8") as f:
            f.write(state["srs"])

    user = f"SRS File Path: {srs_path}\n\nFeedback:\n{state['qa']}\n\nPlease use the provided tools to fix the document based on the feedback."

    mcp_server_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "core", "mcp_server.py"))

    logger.info("Starting Refine Agent with MCP Client...")
    result_summary = asyncio.run(call_llm_with_mcp(user, server_script=mcp_server_script, system=_SKILL))
    logger.info(f"Refinement Summary:\n{result_summary}")

    with open(srs_path, "r", encoding="utf-8") as f:
        new_srs = f.read()

    export_agent_output(
        "refine",
        output={
            "summary": result_summary,
            "srs_path": srs_path,
            "srs_length_chars": len(new_srs),
        },
        metadata={
            "iteration": state.get("iterations", 0),
            "previous_score": state.get("score"),
            "previous_issue_type": state.get("issue_type"),
        },
    )

    return {**state, "srs": new_srs, "srs_path": srs_path}
