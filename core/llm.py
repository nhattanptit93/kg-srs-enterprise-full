
import os
import asyncio
from typing import Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from core.logger import get_logger

logger = get_logger("llm")

MODEL = "claude-opus-4-7"
MAX_TOKENS = 16000

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            timeout=300.0
        )
    return _client


def load_skill(path: str) -> str:
    """Load a SKILLS.md file (EN-only, used as the system prompt).

    Bilingual sources are split offline by ``tools/split_skills.py`` into
    ``SKILLS.md`` (English) and ``SKILLS-vn.md`` (Vietnamese). This loader
    just reads the file as-is.
    """
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _build_user_content(user):
    """Accept either a plain string or a dict {"cached": str, "suffix": str}.

    When a dict is provided, the cached portion gets its own ``cache_control``
    breakpoint so repeated invocations within the 5-min TTL hit the cache.
    """
    if isinstance(user, str):
        return user
    cached = user.get("cached", "")
    suffix = user.get("suffix", "")
    blocks = []
    if cached:
        blocks.append({
            "type": "text",
            "text": cached,
            "cache_control": {"type": "ephemeral"},
        })
    if suffix:
        blocks.append({"type": "text", "text": suffix})
    return blocks if blocks else ""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
def call_llm(user, system: Optional[str] = None) -> str:
    """Call Claude with optional cached system + optional cached user prefix.

    ``user`` may be a string (no user-side caching) or
    ``{"cached": str, "suffix": str}`` to put a cache breakpoint after the
    cached portion.
    """
    kwargs = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": _build_user_content(user)}],
    }
    if system:
        kwargs["system"] = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    response = _get_client().messages.create(**kwargs)

    u = response.usage
    logger.info(
        f"cache_read={u.cache_read_input_tokens} "
        f"cache_write={u.cache_creation_input_tokens} "
        f"input={u.input_tokens} output={u.output_tokens}"
    )

    for block in response.content:
        if block.type == "text":
            return block.text
    return ""


async def call_llm_with_mcp(user: str, server_script: str, system: Optional[str] = None) -> str:
    server_params = StdioServerParameters(command="python", args=[server_script])
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            tools_response = await session.list_tools()
            anthropic_tools = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema
                } for t in tools_response.tools
            ]
            # Place a cache breakpoint on the last tool: every multi-turn refine
            # session re-sends the full tool array each turn, so caching it
            # eliminates redundant tool-schema input tokens after the first turn.
            if anthropic_tools:
                anthropic_tools[-1]["cache_control"] = {"type": "ephemeral"}

            messages = [{"role": "user", "content": user}]
            
            system_param = None
            if system:
                system_param = [
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ]
            
            # Retry loop is managed manually here if needed, or we rely on the internal calls
            # For simplicity, we just do the tool loop
            while True:
                kwargs = {
                    "model": MODEL,
                    "max_tokens": MAX_TOKENS,
                    "messages": messages,
                    "tools": anthropic_tools
                }
                if system_param:
                    kwargs["system"] = system_param
                    
                # We can't use @retry decorator on an async function block easily without extracting
                # Assuming the network is stable or _get_client handles it.
                response = _get_client().messages.create(**kwargs)
                
                u = response.usage
                logger.info(
                    f"[MCP Call] cache_read={u.cache_read_input_tokens} "
                    f"cache_write={u.cache_creation_input_tokens} "
                    f"input={u.input_tokens} output={u.output_tokens}"
                )
                
                messages.append({"role": "assistant", "content": response.content})
                
                if response.stop_reason == "tool_use":
                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            logger.info(f"LLM called tool: {block.name}")
                            try:
                                result = await session.call_tool(block.name, block.input)
                                result_text = result.content[0].text
                            except Exception as e:
                                result_text = f"Error executing tool: {str(e)}"
                                logger.error(result_text)
                                
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_text
                            })
                    messages.append({"role": "user", "content": tool_results})
                else:
                    for block in response.content:
                        if block.type == "text":
                            return block.text
                    return ""
