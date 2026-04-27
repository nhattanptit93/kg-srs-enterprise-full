
from typing import TypedDict, Optional, List, Dict, Any

class AgentState(TypedDict):
    input: str
    answers: Optional[str]
    usecase: Optional[str]
    graph: Optional[str]
    srs: Optional[str]
    srs_path: Optional[str]
    qa: Optional[str]
    score: Optional[int]
    issue_type: Optional[str]
    iterations: Optional[int]
    is_synthetic_answers: Optional[bool]
    diagram_paths: Optional[List[str]]
    diagram_coverage: Optional[Dict[str, Any]]
