"""Per-agent JSON output exporter.

Each agent calls `export_agent_output(...)` at the end of its `run()`
to persist a snapshot of its output as JSON under
`workspace/<agent_name>/<agent_name>.json`. The file is overwritten
each invocation (no versioning).
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from core.logger import get_logger

logger = get_logger("output_export")

WORKSPACE_ROOT = "workspace"


def export_agent_output(
    agent_name: str,
    output: Any,
    metadata: Optional[dict] = None,
) -> str:
    """Write {agent, timestamp, output, metadata} as JSON.

    Returns the absolute path written. On failure, logs and returns "".
    """
    folder = os.path.join(WORKSPACE_ROOT, agent_name)
    os.makedirs(folder, exist_ok=True)
    path = os.path.abspath(os.path.join(folder, f"{agent_name}.json"))

    payload = {
        "agent": agent_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "output": output,
        "metadata": metadata or {},
    }

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"Exported {agent_name} output to {path}")
        return path
    except Exception as e:
        logger.error(f"Failed to export {agent_name} output: {e}")
        return ""
