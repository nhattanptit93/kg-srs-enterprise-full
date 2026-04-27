
from langgraph.graph import StateGraph
from core.state import AgentState
from agents.interview.agent import run as interview
from agents.structuring.agent import run as struct
from agents.graph.agent import run as graph
from agents.srs.agent import run as srs
from agents.verification.agent import run as verify
from agents.refine.agent import run as refine
from agents.diagram.agent import run as diagram
from agents.memorize.agent import run as memorize

from core.config import SCORE_THRESHOLD, MAX_ITERATIONS
from core.logger import get_logger

logger = get_logger("workflow")
def route(state):
    if state["score"] >= SCORE_THRESHOLD:
        return "diagram"
    if state.get("iterations", 0) >= MAX_ITERATIONS:
        logger.info(f"Hit MAX_ITERATIONS={MAX_ITERATIONS}, forcing end.")
        return "diagram"
    if state["issue_type"] == "LOGIC":
        return "graph"
    if state["issue_type"] == "MISSING":
        return "interview"
    return "refine"

def build_app():
    g = StateGraph(AgentState)
    g.add_node("interview", interview)
    g.add_node("struct", struct)
    g.add_node("graph", graph)
    g.add_node("srs", srs)
    g.add_node("verify", verify)
    g.add_node("refine", refine)
    g.add_node("diagram", diagram)
    g.add_node("memorize", memorize)

    g.set_entry_point("interview")
    g.add_edge("interview","struct")
    g.add_edge("struct","graph")
    g.add_edge("graph","srs")
    g.add_edge("srs","verify")

    g.add_conditional_edges("verify", route,{
        "graph":"graph",
        "interview":"interview",
        "refine":"refine",
        "diagram":"diagram"
    })

    g.add_edge("diagram", "memorize")
    g.add_edge("memorize", "__end__")

    g.add_edge("refine", "verify")
    return g.compile()
