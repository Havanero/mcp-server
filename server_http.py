#!/usr/bin/env python3
"""
HTTP MCP Server Launcher
"""
import asyncio
import logging
import sys

from http_transport import HTTPMCPServer
from plugin_manager import PluginManager


async def main():
    """Start HTTP MCP server"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    
    # Create plugin manager and server
    plugin_manager = PluginManager("tools")
    server = HTTPMCPServer(plugin_manager, host="localhost", port=8080)
    
    print("🚀 Starting HTTP MCP Server")
    print("🔗 Base URL: http://localhost:8080")
    print("📋 API Docs: http://localhost:8080/")
    print("🌐 Web Client: http://localhost:8080/client")
    print("👋 Press Ctrl+C to stop")
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n👋 Server shutdown requested")


if __name__ == "__main__":
    asyncio.run(main())
