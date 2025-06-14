#!/usr/bin/env python3
"""
WebSocket MCP Server Launcher
"""
import asyncio
import logging
import sys

from websocket_transport import WebSocketMCPServer
from plugin_manager import PluginManager


async def main():
    """Start WebSocket MCP server"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    # Create plugin manager and server
    plugin_manager = PluginManager("tools")
    server = WebSocketMCPServer(plugin_manager, host="localhost", port=8765)
    
    print("🚀 Starting WebSocket MCP Server")
    print("🔗 URL: ws://localhost:8765")
    print("👋 Press Ctrl+C to stop")
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n👋 Server shutdown requested")
        await server.transport.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
