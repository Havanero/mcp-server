#!/usr/bin/env python3
"""
SSE MCP Server Launcher
Launch Server-Sent Events MCP server for streaming operations
"""
import asyncio
import logging
import sys

from sse_transport import SSEMCPServer
from plugin_manager import PluginManager


async def main():
    """Start SSE MCP server"""
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,  # Changed to DEBUG for more info
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    # Create plugin manager and server
    plugin_manager = PluginManager("tools")
    server = SSEMCPServer(plugin_manager, host="localhost", port=8081)
    
    print("🌊 Starting SSE MCP Server")
    print("📡 URL: http://localhost:8081")
    print("🔗 Streaming endpoints:")
    print("   • GET /stream/tools/{name}?arg1=val1&arg2=val2")
    print("   • GET /stream/llm?prompt=hello&model=gpt-4")
    print("   • GET /stream/mcp?method=tools/list")
    print("📋 Documentation: http://localhost:8081/")
    print("👋 Press Ctrl+C to stop")
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n👋 Server shutdown requested")


if __name__ == "__main__":
    asyncio.run(main())
