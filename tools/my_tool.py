import sys

sys.path.append("..")

from base_tool import BaseTool, ToolResult
from tool_decorators import MethodToolRegistry, mcp_tool, tool, tool_method


@tool("tell_me_a_joke", "Tell jokes")
async def tell_joke(joke: str) -> dict:
    """Generate jokes for ppl
    Args:
        joke:  Joke string
    """

    return {"jokes": "who is there"}
