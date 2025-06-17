#!/usr/bin/env python3
"""
MCP-over-HTTP Server - Proper JSON-RPC 2.0 MCP Protocol via HTTP

This maintains ALL MCP benefits while using HTTP transport:
- JSON-RPC 2.0 message structure
- Standard MCP methods (initialize, tools/list, tools/call)  
- Proper protocol handshake and versioning
- MCP ecosystem compatibility

Búvár-style architecture with dependency injection and plugin system.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from aiohttp import web, web_request
from aiohttp.web import Application, Request, Response, json_response

from plugin_manager import PluginManager


class MCPOverHTTPServer:
    """
    Proper MCP server using JSON-RPC 2.0 over HTTP transport
    
    Maintains full MCP protocol compliance while using HTTP for transport.
    """
    
    def __init__(self, plugin_manager: PluginManager, host: str = "localhost", port: int = 8081):
        self.plugin_manager = plugin_manager
        self.host = host
        self.port = port
        
        # MCP protocol state
        self.protocol_version = "2024-11-05"
        self.server_info = {
            "name": "mcp-python-server", 
            "version": "1.0.0"
        }
        self.capabilities = {
            "tools": {}  # We support tools
        }
        
        # Client sessions (for multi-client support)
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        self.logger = logging.getLogger("mcp_http_server")
        
    async def start(self):
        """Start the MCP-over-HTTP server"""
        # Load tools BEFORE starting server to avoid race condition
        self.logger.info("📦 Loading tools...")
        await self.plugin_manager.discover_and_load_tools()
        tool_count = len(self.plugin_manager.loaded_tools)
        self.logger.info(f"🔧 Loaded {tool_count} tools")
        
        if tool_count == 0:
            self.logger.warning("⚠️  No tools loaded! Check tools directory")
        
        # Now start the HTTP server
        app = self._create_app()
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        self.logger.info(f"🎯 MCP-over-HTTP Server started on http://{self.host}:{self.port}")
        self.logger.info(f"📋 Protocol: JSON-RPC 2.0 (proper MCP)")
        self.logger.info(f"🔧 Tools available: {tool_count}")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Server shutting down...")
            await runner.cleanup()
    
    def _create_app(self) -> Application:
        """Create aiohttp application with MCP routes"""
        app = web.Application()
        
        # MCP JSON-RPC endpoint
        app.router.add_post("/mcp", self._handle_mcp_request)
        
        # Health check (non-MCP)
        app.router.add_get("/health", self._handle_health)
        
        # Server info (non-MCP)
        app.router.add_get("/", self._handle_info)
        
        # Tools endpoint for quick listing (non-MCP)
        app.router.add_get("/tools", self._handle_tools_list)
        
        return app
    
    async def _handle_mcp_request(self, request: Request) -> Response:
        """Handle JSON-RPC 2.0 MCP requests"""
        try:
            # Parse JSON-RPC request
            data = await request.json()
            
            # Validate JSON-RPC format
            if not self._is_valid_jsonrpc(data):
                return self._jsonrpc_error(None, -32600, "Invalid Request")
            
            method = data["method"]
            params = data.get("params", {})
            request_id = data.get("id")
            
            self.logger.debug(f"MCP Request: {method}")
            
            # Route to MCP method handlers
            if method == "initialize":
                result = await self._handle_initialize(params, request)
            elif method == "initialized":
                result = await self._handle_initialized(params, request)
            elif method == "tools/list":
                result = await self._handle_tools_list_mcp(params, request)
            elif method == "tools/call":
                result = await self._handle_tools_call(params, request)
            else:
                return self._jsonrpc_error(request_id, -32601, f"Method not found: {method}")
            
            # Return JSON-RPC response
            if request_id is not None:  # Request (not notification)
                return self._jsonrpc_success(request_id, result)
            else:  # Notification (no response)
                return Response(status=204)  # No Content
                
        except json.JSONDecodeError:
            return self._jsonrpc_error(None, -32700, "Parse error")
        except Exception as e:
            self.logger.error(f"Error handling MCP request: {e}")
            request_id = data.get("id") if 'data' in locals() else None
            return self._jsonrpc_error(request_id, -32603, f"Internal error: {str(e)}")
    
    def _is_valid_jsonrpc(self, data: Dict[str, Any]) -> bool:
        """Validate JSON-RPC 2.0 format"""
        return (
            isinstance(data, dict) and
            "method" in data and
            isinstance(data["method"], str)
        )
    
    def _jsonrpc_success(self, request_id: Any, result: Any) -> Response:
        """Create JSON-RPC success response"""
        response_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        return json_response(response_data)
    
    def _jsonrpc_error(self, request_id: Any, code: int, message: str, data: Any = None) -> Response:
        """Create JSON-RPC error response"""
        error = {"code": code, "message": message}
        if data:
            error["data"] = data
            
        response_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": error
        }
        return json_response(response_data, status=200)  # JSON-RPC errors use 200 OK
    
    def _get_session_id(self, request: Request) -> str:
        """Get or create session ID for client"""
        # Use client IP + User-Agent as session key
        client_ip = request.remote
        user_agent = request.headers.get("User-Agent", "unknown")
        session_key = f"{client_ip}_{hash(user_agent)}"
        
        if session_key not in self.sessions:
            self.sessions[session_key] = {
                "id": session_key,
                "initialized": False,
                "created_at": datetime.now(),
                "client_info": {}
            }
        
        return session_key
    
    async def _handle_initialize(self, params: Dict[str, Any], request: Request) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        session_id = self._get_session_id(request)
        session = self.sessions[session_id]
        
        # Validate protocol version
        client_version = params.get("protocolVersion")
        if not client_version:
            raise ValueError("Missing protocolVersion")
        
        # Store client info
        session["client_info"] = params.get("clientInfo", {})
        session["protocol_version"] = client_version
        
        self.logger.info(f"Client initializing: {session['client_info'].get('name', 'unknown')}")
        
        # Return server capabilities
        return {
            "protocolVersion": self.protocol_version,
            "capabilities": self.capabilities,
            "serverInfo": self.server_info
        }
    
    async def _handle_initialized(self, params: Dict[str, Any], request: Request) -> None:
        """Handle initialized notification"""
        session_id = self._get_session_id(request)
        session = self.sessions[session_id]
        session["initialized"] = True
        
        client_name = session["client_info"].get("name", "unknown")
        self.logger.info(f"Client '{client_name}' initialization complete")
        
        return None  # Notification - no result
    
    async def _handle_tools_list_mcp(self, params: Dict[str, Any], request: Request) -> Dict[str, Any]:
        """Handle MCP tools/list request"""
        session_id = self._get_session_id(request)
        session = self.sessions[session_id]
        
        if not session.get("initialized"):
            raise ValueError("Server not initialized")
        
        # Ensure tools are loaded
        if not hasattr(self.plugin_manager, 'loaded_tools') or not self.plugin_manager.loaded_tools:
            self.logger.warning("No tools loaded, attempting to reload...")
            await self.plugin_manager.discover_and_load_tools()
        
        # Get tools from plugin manager
        tools_list = []
        for tool_name, tool_instance in self.plugin_manager.loaded_tools.items():
            tool_info = {
                "name": tool_name,
                "description": tool_instance.description,
                "inputSchema": tool_instance.input_schema
            }
            tools_list.append(tool_info)
        
        self.logger.debug(f"Returning {len(tools_list)} tools to client")
        
        return {"tools": tools_list}
    
    async def _handle_tools_call(self, params: Dict[str, Any], request: Request) -> Dict[str, Any]:
        """Handle MCP tools/call request"""
        session_id = self._get_session_id(request)
        session = self.sessions[session_id]
        
        if not session.get("initialized"):
            raise ValueError("Server not initialized")
        
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise ValueError("Missing tool name")
        
        # Get tool from plugin manager
        tool_instance = self.plugin_manager.loaded_tools.get(tool_name)
        if not tool_instance:
            raise ValueError(f"Tool not found: {tool_name}")
        
        self.logger.info(f"Executing tool: {tool_name}")
        
        try:
            # Execute tool using plugin manager
            result = await self.plugin_manager.execute_tool(tool_name, arguments)
            return result
            
        except Exception as e:
            self.logger.error(f"Tool execution failed: {e}")
            raise ValueError(f"Tool execution error: {str(e)}")
    
    async def _handle_health(self, request: Request) -> Response:
        """Health check endpoint (non-MCP)"""
        return json_response({
            "status": "healthy",
            "server": self.server_info,
            "protocol": "MCP over HTTP (JSON-RPC 2.0)",
            "sessions": len(self.sessions),
            "tools": len(self.plugin_manager.loaded_tools)
        })
    
    async def _handle_info(self, request: Request) -> Response:
        """Server information endpoint (non-MCP)"""
        return json_response({
            "server": self.server_info,
            "protocol": {
                "name": "Model Context Protocol",
                "version": self.protocol_version,
                "transport": "HTTP",
                "format": "JSON-RPC 2.0"
            },
            "capabilities": self.capabilities,
            "endpoints": {
                "mcp": "/mcp",
                "health": "/health", 
                "tools": "/tools"
            },
            "tools": {
                "count": len(self.plugin_manager.loaded_tools),
                "available": list(self.plugin_manager.loaded_tools.keys())
            }
        })
    
    async def _handle_tools_list(self, request: Request) -> Response:
        """Quick tools listing (non-MCP, for debugging)"""
        tools = []
        for tool_name, tool_instance in self.plugin_manager.loaded_tools.items():
            tools.append({
                "name": tool_name,
                "description": tool_instance.description,
                "inputSchema": tool_instance.input_schema
            })
        
        return json_response({"tools": tools})


async def main():
    """Start MCP-over-HTTP server"""
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create plugin manager and server
    plugin_manager = PluginManager("tools")
    server = MCPOverHTTPServer(plugin_manager, host="localhost", port=8081)
    
    print("🎯 Starting MCP-over-HTTP Server (JSON-RPC 2.0)")
    print("=" * 60)
    print(f"📡 URL: http://localhost:8081")
    print(f"🔗 MCP Endpoint: POST http://localhost:8081/mcp")
    print(f"📋 Server Info: GET http://localhost:8081/")
    print(f"🔧 Tools List: GET http://localhost:8081/tools")
    print(f"🏥 Health Check: GET http://localhost:8081/health")
    print("=" * 60)
    print("📖 Protocol: Proper MCP with JSON-RPC 2.0 over HTTP")
    print("🎯 Benefits: Full MCP compliance + HTTP transport")
    print("👋 Press Ctrl+C to stop")
    print()
    
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
