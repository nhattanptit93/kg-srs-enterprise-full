import json
import os
import re

from core.llm import call_llm
from core.memory import VectorMemory
from core.config import SCORE_THRESHOLD
from core.logger import get_logger
from core.output_export import export_agent_output

logger = get_logger("memorize")

memory = VectorMemory()


def _summarize_srs(srs_text: str, sidecar_path: str = "workspace/current_srs.json") -> str:
    """Produce a compact summary of the SRS for lesson distillation.

    Lessons are domain-level insights — they don't need every AC verbatim.
    Prefer the structured sidecar JSON (entity/req-level facts) plus the
    markdown's heading skeleton. Falls back to first-N-chars if neither
    works, to stay safe.
    """
    parts: list[str] = []

    if os.path.exists(sidecar_path):
        try:
            with open(sidecar_path, "r", encoding="utf-8") as f:
                sidecar = json.load(f)
            reqs = sidecar.get("requirements", [])
            req_lines = []
            for r in reqs:
                title = r.get("title", "")
                priority = r.get("priority", "")
                edge = r.get("edge_cases", [])
                edge_cats = ",".join(
                    e.split(":", 1)[0].strip() for e in edge if ":" in e
                )
                req_lines.append(
                    f"- {r.get('id', '?')} [{priority}] {title} | edges: {edge_cats}"
                )
            parts.append(
                f"### Sidecar summary ({len(reqs)} REQ-F):\n" + "\n".join(req_lines)
            )
        except Exception as e:
            logger.warning(f"Could not read sidecar for summary: {e}")

    if srs_text:
        headings = re.findall(r"^#{1,4}\s+.+$", srs_text, flags=re.MULTILINE)
        if headings:
            parts.append("### SRS heading skeleton:\n" + "\n".join(headings[:80]))

    if not parts:
        return srs_text[:4000]

    return "\n\n".join(parts)

SYSTEM_SUCCESS = (
    "You are a lessons-learned distiller. Given the original requirement, the "
    "final SRS, and QA feedback from a successful run (score >= 8), extract 2-3 "
    "concise, reusable lessons that would help future SRS generation on similar "
    "products. Each lesson must start with 'Domain:' followed by the product "
    "category, then 'Lesson:' with the actionable insight. Return one lesson "
    "per line, no numbering, no prose around them.\n\n"
    "Prioritize lessons in these high-value categories when present:\n"
    "  - Lifecycle state naming conventions that survived cross-section review "
    "    (e.g., 'use ready_for_pickup not ready' to prevent §3↔§6 drift).\n"
    "  - Policy/configuration entities that the domain commonly needs but is "
    "    often missed (CancellationFeePolicy, RegionPaymentPolicy, etc.).\n"
    "  - Derived-field source patterns (e.g., 'discountVnd requires Coupon entity').\n"
    "  - Self-service flows commonly required (password reset, account deletion, "
    "    data export) for compliance.\n"
    "  - AC coverage tactics that produced testable specs.\n"
    "  - Domain-typical edge cases (Race / Time / Boundary / Stale / Network / "
    "    Permission / i18n / Empty / Volume / Adversarial) that the verifier "
    "    confirmed were correctly covered. Phrase as: "
    "    'Domain X must always test edge case Y because Z.'"
)

SYSTEM_FAILURE = (
    "You are a lessons-learned distiller. Given the original requirement, the "
    "final SRS, and QA feedback from a run that hit the iteration cap without "
    "reaching quality threshold, extract 1-2 cautionary lessons about what "
    "went wrong or what to watch out for. Each lesson must start with 'Domain:' "
    "followed by product category, then 'Caution:' with the warning. Return "
    "one lesson per line, no numbering, no prose around them.\n\n"
    "Prioritize cautions in these high-impact failure modes when evident in the feedback:\n"
    "  - State name divergence between §3 functional REQ and §6 data model enums "
    "    (e.g., §3 said 'ready' but §6 said 'ready_for_pickup'). Cite the entity.\n"
    "  - Orphan derived fields (e.g., Order.discountVnd with no Coupon entity).\n"
    "  - Missing policy entities for 'configurable per region' rules.\n"
    "  - Acceptance criteria coverage gap (Essential REQ-F lacking AC).\n"
    "  - Reserved-but-empty ID gaps creating traceability noise.\n"
    "  - Edge-case coverage gaps the verifier flagged: low boundary_coverage, "
    "    failure_coverage, eh_block_coverage, or concurrency_notes_coverage. "
    "    Cite the missing category (Race / Time / Boundary / Stale / Network / "
    "    Permission / i18n / Empty / Volume / Adversarial) and the REQ-F where "
    "    it was missed.\n"
    "  - AC merging anti-pattern (one AC covering multiple failure modes)."
)



def run(state):
    score = state.get("score", 0)
    success = score >= SCORE_THRESHOLD

    srs_summary = _summarize_srs(
        state.get("srs", ""),
        sidecar_path=state.get("srs_sidecar_path", "workspace/current_srs.json"),
    )
    user = (
        f"Original requirement:\n{state.get('input', '')}\n\n"
        f"SRS summary (heading skeleton + per-REQ-F facts):\n{srs_summary}\n\n"
        f"QA feedback:\n{state.get('qa', '')}\n\n"
        f"Score: {score}"
    )
    system = SYSTEM_SUCCESS if success else SYSTEM_FAILURE

    raw = call_llm(user, system=system)
    lessons = [l.strip() for l in raw.split("\n") if l.strip()]

    for lesson in lessons:
        memory.add(lesson)

    logger.info(f"Saved {len(lessons)} lesson(s) to memory (success={success}).")

    export_agent_output(
        "memorize",
        output={
            "lessons": lessons,
            "success": success,
        },
        metadata={
            "iteration": state.get("iterations", 0),
            "score": score,
            "score_threshold": SCORE_THRESHOLD,
            "lesson_count": len(lessons),
        },
    )

    return state
