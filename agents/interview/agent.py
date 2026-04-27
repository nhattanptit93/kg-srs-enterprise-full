import sys

from core.llm import call_llm, load_skill
from core.memory import VectorMemory
from core.logger import get_logger
from core.output_export import export_agent_output

logger = get_logger("interview")

memory = VectorMemory()
_SKILL = load_skill("agents/interview/SKILLS.md")

_AUTO_SYSTEM = (
    "You are simulating a product owner being interviewed. Given the product "
    "idea and clarifying questions, provide concise, plausible answers as a "
    "single paragraph. Do not ask questions back."
)


def run(state):
    # Skip only if we have answers and this isn't a self-healing loop
    if state.get("answers") and not state.get("qa"):
        export_agent_output(
            "interview",
            output={
                "questions": None,
                "answers": state["answers"],
                "is_synthetic_answers": state.get("is_synthetic_answers", False),
            },
            metadata={
                "iteration": state.get("iterations", 0),
                "loop_mode": "skipped_preset",
            },
        )
        return state

    lessons = memory.search(state["input"])
    cached = f"Input: {state['input']}\nLessons: {lessons}"
    suffix = ""

    if state.get("qa"):
        logger.info("Handling MISSING feedback loop.")
        cached += f"\n\nPrevious Answers: {state['answers']}"
        suffix = (
            f"\n\nQA Feedback (Missing Info):\n{state['qa']}"
            "\n\nPlease ask specific follow-up questions to fill in the missing information."
        )

    q = call_llm({"cached": cached, "suffix": suffix}, system=_SKILL)
    logger.info(f"Questions:\n{q}")

    if sys.stdin.isatty():
        ans = input("Answer: ")
        is_synth = False
    else:
        logger.info("stdin is not a TTY — auto-answering via LLM.")
        ans = call_llm(
            f"Product idea: {state['input']}\n\nQuestions:\n{q}",
            system=_AUTO_SYSTEM,
        )
        logger.info(f"Auto-answer: {ans}")
        is_synth = True

    # If this is a loop, append new answers to old answers
    if state.get("qa") and state.get("answers"):
        final_answers = state["answers"] + "\n\n[FOLLOW-UP ANSWERS]\n" + ans
    else:
        final_answers = ans

    export_agent_output(
        "interview",
        output={
            "questions": q,
            "answers": final_answers,
            "is_synthetic_answers": is_synth,
        },
        metadata={
            "iteration": state.get("iterations", 0),
            "loop_mode": "missing_followup" if state.get("qa") else "initial",
            "lessons_used_count": len(lessons) if lessons else 0,
        },
    )

    return {**state, "answers": final_answers, "is_synthetic_answers": is_synth}
