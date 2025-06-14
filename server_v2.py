#!/usr/bin/env python3
"""
MCP Server - Enhanced with Plugin System

Clean MCP server with dynamic tool loading via plugin manager.
No hardcoded tools - everything loaded from tools/ directory.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field

from transport import StdioServerTransport, MCPRequest, MCPResponse
from plugin_manager import PluginManager, ToolError


class MCPServer:
    """
    Enhanced MCP server with plugin-based tool management.
    
    Features:
    - Dynamic tool loading from tools/ directory
    - Zero hardcoded tools - fully plugin-driven
    - Error isolation and proper MCP error handling
    - Clean separation between server core and tools
    """
    
    def __init__(self, name: str = "mcp-plugin-server", version: str = "2.0.0", tools_dir: str = "tools"):
        self.name = name
        self.version = version
        self.transport = StdioServerTransport()
        self.plugin_manager = PluginManager(tools_dir)
        self.initialized = False
        
        # Set up transport handler
        self.transport.set_request_handler(self._handle_request)
    
    async def start(self) -> None:
        """Start the MCP server with plugin discovery"""
        logging.info(f"🚀 Starting MCP server: {self.name} v{self.version}")
        
        # Load plugins
        tools = await self.plugin_manager.discover_and_load_tools()
        logging.info(f"🔧 Loaded {len(tools)} tools: {list(tools.keys())}")
        
        if not tools:
            logging.warning("⚠️  No tools loaded! Check tools/ directory")
        
        # Start transport
        await self.transport.start()
    
    async def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """Route MCP requests to appropriate handlers"""
        try:
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "initialized":
                return await self._handle_initialized(request)
            elif request.method == "tools/list":
                return await self._handle_tools_list(request)
            elif request.method == "tools/call":
                return await self._handle_tools_call(request)
            else:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Method not found: {request.method}"}
                )
        except Exception as e:
            logging.error(f"❌ Error handling {request.method}: {e}")
            return MCPResponse(
                id=request.id,
                error={"code": -32603, "message": f"Internal error: {str(e)}"}
            )
    
    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP initialize request"""
        logging.info("🔌 Client initializing...")
        
        # Validate protocol version
        client_version = request.params.get("protocolVersion")
        if not client_version:
            return MCPResponse(
                id=request.id,
                error={"code": -32602, "message": "Missing protocolVersion"}
            )
        
        # Return server capabilities and info
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}  # We support tools
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
                "description": f"Plugin-based MCP server with {len(self.plugin_manager.loaded_tools)} tools"
            }
        }
        
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_initialized(self, request: MCPRequest) -> MCPResponse:
        """Handle initialized notification"""
        self.initialized = True
        logging.info("✅ Client initialization complete")
        # Initialized is a notification, no response needed
        return MCPResponse(id=None)  # Will be ignored by transport
    
    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/list request"""
        if not self.initialized:
            return MCPResponse(
                id=request.id,
                error={"code": -32002, "message": "Server not initialized"}
            )
        
        # Get tools from plugin manager
        tools_registry = self.plugin_manager.get_tool_registry()
        tools_list = list(tools_registry.values())
        
        result = {"tools": tools_list}
        logging.debug(f"📋 Returning {len(tools_list)} tools")
        
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/call request"""
        if not self.initialized:
            return MCPResponse(
                id=request.id,
                error={"code": -32002, "message": "Server not initialized"}
            )
        
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        if not tool_name:
            return MCPResponse(
                id=request.id,
                error={"code": -32602, "message": "Missing tool name"}
            )
        
        try:
            # Execute tool via plugin manager
            result = await self.plugin_manager.execute_tool(tool_name, arguments)
            return MCPResponse(id=request.id, result=result)
            
        except ToolError as e:
            # Tool-specific errors with proper codes
            return MCPResponse(
                id=request.id,
                error={"code": e.code, "message": e.message}
            )
        except Exception as e:
            logging.error(f"❌ Unexpected tool execution error: {e}")
            return MCPResponse(
                id=request.id,
                error={"code": -32603, "message": f"Internal tool error: {str(e)}"}
            )
    
    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics for debugging"""
        return {
            "name": self.name,
            "version": self.version,
            "initialized": self.initialized,
            "tools_loaded": len(self.plugin_manager.loaded_tools),
            "tools": list(self.plugin_manager.loaded_tools.keys()),
            "failed_plugins": self.plugin_manager.failed_plugins
        }


# Enhanced server startup
async def main():
    """Main server entry point with enhanced logging"""
    server = MCPServer()
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logging.info("👋 Server shutdown requested")
    except Exception as e:
        logging.error(f"💥 Server crashed: {e}")
        raise


if __name__ == "__main__":
    # Enhanced logging for development
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 Starting Enhanced MCP Server with Plugin System")
    print("🔧 Loading tools from tools/ directory...")
    
    asyncio.run(main())
