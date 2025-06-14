
import asyncio
import sys
sys.path.append('..')
from base_tool import ToolError, ToolResult
from tool_decorators import MethodToolRegistry, tool, tool_method


@tool("caleb", "talk to caleb")
async def talk_caleb(
    query: str,
) -> ToolResult:
    """
    talk to caleb about anything.

    Args:
        query: any questions you might have
    """
    result = ToolResult()
    return result
