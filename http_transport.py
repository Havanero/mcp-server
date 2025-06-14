#!/usr/bin/env python3
"""
HTTP Transport - REST-like MCP transport for simple integrations

Provides HTTP-based transport for MCP with REST-style endpoints.
Good for simple request/response patterns and web integrations.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional
from aiohttp import web, ClientSession
import aiohttp
from dataclasses import asdict

from transport import MCPRequest, MCPResponse


class HTTPTransport:
    """
    HTTP-based MCP transport with REST-style endpoints.
    
    Endpoints:
    - POST /mcp          - Send MCP JSON-RPC requests
    - GET  /tools        - List available tools
    - POST /tools/{name} - Call specific tool
    - GET  /health       - Server health check
    - GET  /stats        - Server statistics
    """
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.request_handler = None
        self.plugin_manager = None
        self._setup_routes()
        self._setup_cors()
    
    def set_request_handler(self, handler):
        """Set the MCP request handler"""
        self.request_handler = handler
    
    def set_plugin_manager(self, plugin_manager):
        """Set plugin manager for direct tool access"""
        self.plugin_manager = plugin_manager
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        # MCP JSON-RPC endpoint
        self.app.router.add_post('/mcp', self._handle_mcp_request)
        
        # REST-style tool endpoints
        self.app.router.add_get('/tools', self._handle_list_tools)
        self.app.router.add_post('/tools/{tool_name}', self._handle_call_tool)
        
        # Utility endpoints
        self.app.router.add_get('/health', self._handle_health)
        self.app.router.add_get('/stats', self._handle_stats)
        
        # Documentation endpoint
        self.app.router.add_get('/', self._handle_docs)
        
        # Static file serving for web client (optional)
        self.app.router.add_get('/client', self._handle_web_client)
    
    def _setup_cors(self):
        """Setup CORS for web browser access"""
        async def cors_handler(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        
        # Add CORS middleware
        self.app.middlewares.append(cors_handler)
        
        # Handle preflight requests
        async def options_handler(request):
            return web.Response(
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type'
                }
            )
        
        self.app.router.add_options('/{path:.*}', options_handler)
    
    async def _handle_mcp_request(self, request: web.Request) -> web.Response:
        """Handle MCP JSON-RPC requests"""
        try:
            data = await request.json()
            
            # Create MCP request
            mcp_request = MCPRequest(
                id=data.get("id"),
                method=data.get("method"),
                params=data.get("params", {})
            )
            
            # Handle via MCP handler
            if not self.request_handler:
                return web.json_response({
                    "jsonrpc": "2.0",
                    "id": mcp_request.id,
                    "error": {"code": -32603, "message": "No request handler configured"}
                }, status=500)
            
            response = await self.request_handler(mcp_request)
            
            # Convert to JSON-RPC response
            response_data = {"jsonrpc": "2.0", "id": response.id}
            
            if response.result is not None:
                response_data["result"] = response.result
            elif response.error is not None:
                response_data["error"] = response.error
            
            return web.json_response(response_data)
            
        except json.JSONDecodeError:
            return web.json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }, status=400)
        except Exception as e:
            logging.error(f"❌ MCP request error: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }, status=500)
    
    async def _handle_list_tools(self, request: web.Request) -> web.Response:
        """Handle GET /tools - List available tools"""
        try:
            if not self.plugin_manager:
                return web.json_response({"error": "Plugin manager not configured"}, status=500)
            
            tools_registry = self.plugin_manager.get_tool_registry()
            tools_list = list(tools_registry.values())
            
            return web.json_response({
                "tools": tools_list,
                "count": len(tools_list)
            })
            
        except Exception as e:
            logging.error(f"❌ List tools error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_call_tool(self, request: web.Request) -> web.Response:
        """Handle POST /tools/{tool_name} - Call specific tool"""
        try:
            tool_name = request.match_info['tool_name']
            
            # Get arguments from request body
            try:
                arguments = await request.json()
            except:
                arguments = {}
            
            if not self.plugin_manager:
                return web.json_response({"error": "Plugin manager not configured"}, status=500)
            
            # Execute tool
            result = await self.plugin_manager.execute_tool(tool_name, arguments)
            
            return web.json_response({
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
                "status": "success"
            })
            
        except Exception as e:
            logging.error(f"❌ Tool call error: {e}")
            return web.json_response({
                "tool": tool_name,
                "arguments": arguments,
                "error": str(e),
                "status": "error"
            }, status=500)
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """Handle GET /health - Health check"""
        health_data = {
            "status": "healthy",
            "server": "HTTP MCP Server",
            "version": "2.0.0",
            "timestamp": asyncio.get_event_loop().time(),
            "tools_loaded": len(self.plugin_manager.loaded_tools) if self.plugin_manager else 0
        }
        
        return web.json_response(health_data)
    
    async def _handle_stats(self, request: web.Request) -> web.Response:
        """Handle GET /stats - Server statistics"""
        try:
            stats = {
                "server": {
                    "name": "HTTP MCP Server",
                    "version": "2.0.0",
                    "transport": "HTTP",
                    "host": self.host,
                    "port": self.port
                }
            }
            
            if self.plugin_manager:
                plugin_stats = self.plugin_manager.get_stats()
                stats["plugins"] = plugin_stats
            
            return web.json_response(stats)
            
        except Exception as e:
            logging.error(f"❌ Stats error: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_docs(self, request: web.Request) -> web.Response:
        """Handle GET / - API documentation"""
        docs_html = """
<!DOCTYPE html>
<html>
<head>
    <title>HTTP MCP Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .method { color: #007acc; font-weight: bold; }
        code { background: #eee; padding: 2px 4px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>🌐 HTTP MCP Server</h1>
    <p>REST-style interface for MCP (Model Context Protocol) tools</p>
    
    <h2>📋 Available Endpoints</h2>
    
    <div class="endpoint">
        <div class="method">GET /tools</div>
        <p>List all available tools with their schemas</p>
        <code>curl http://localhost:8080/tools</code>
    </div>
    
    <div class="endpoint">
        <div class="method">POST /tools/{tool_name}</div>
        <p>Execute a specific tool with JSON arguments</p>
        <code>curl -X POST http://localhost:8080/tools/greet -H "Content-Type: application/json" -d '{"name": "World"}'</code>
    </div>
    
    <div class="endpoint">
        <div class="method">POST /mcp</div>
        <p>Send raw MCP JSON-RPC requests</p>
        <code>curl -X POST http://localhost:8080/mcp -H "Content-Type: application/json" -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}'</code>
    </div>
    
    <div class="endpoint">
        <div class="method">GET /health</div>
        <p>Server health check</p>
        <code>curl http://localhost:8080/health</code>
    </div>
    
    <div class="endpoint">
        <div class="method">GET /stats</div>
        <p>Server and plugin statistics</p>
        <code>curl http://localhost:8080/stats</code>
    </div>
    
    <h2>🔧 Example Usage</h2>
    <pre>
# List tools
curl http://localhost:8080/tools

# Call a tool
curl -X POST http://localhost:8080/tools/current_time \\
     -H "Content-Type: application/json" \\
     -d '{"format": "readable"}'

# Call with complex arguments  
curl -X POST http://localhost:8080/tools/opensearch \\
     -H "Content-Type: application/json" \\
     -d '{"query": "GDPR compliance", "size": 5}'
    </pre>
</body>
</html>
        """
        
        return web.Response(text=docs_html, content_type='text/html')
    
    async def _handle_web_client(self, request: web.Request) -> web.Response:
        """Handle GET /client - Simple web client interface"""
        client_html = """
<!DOCTYPE html>
<html>
<head>
    <title>MCP Web Client</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .tool { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        button { background: #007acc; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        button:hover { background: #005999; }
        input, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
        .result { background: #f9f9f9; padding: 10px; margin: 10px 0; border-radius: 4px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>🌐 MCP Web Client</h1>
    <div id="tools"></div>
    
    <script>
        async function loadTools() {
            const response = await fetch('/tools');
            const data = await response.json();
            
            const toolsDiv = document.getElementById('tools');
            toolsDiv.innerHTML = '';
            
            data.tools.forEach(tool => {
                const toolDiv = document.createElement('div');
                toolDiv.className = 'tool';
                
                const properties = tool.inputSchema?.properties || {};
                const required = tool.inputSchema?.required || [];
                
                let inputsHtml = '';
                Object.entries(properties).forEach(([name, schema]) => {
                    const isRequired = required.includes(name);
                    inputsHtml += `
                        <label>${name} (${schema.type})${isRequired ? ' *' : ''}:</label>
                        <input type="text" id="${tool.name}_${name}" placeholder="${schema.description || ''}">
                    `;
                });
                
                toolDiv.innerHTML = `
                    <h3>🔧 ${tool.name}</h3>
                    <p>${tool.description}</p>
                    ${inputsHtml}
                    <button onclick="callTool('${tool.name}')">Execute</button>
                    <div id="${tool.name}_result" class="result" style="display: none;"></div>
                `;
                
                toolsDiv.appendChild(toolDiv);
            });
        }
        
        async function callTool(toolName) {
            const properties = await getToolProperties(toolName);
            const arguments = {};
            
            Object.keys(properties).forEach(name => {
                const input = document.getElementById(`${toolName}_${name}`);
                if (input && input.value) {
                    arguments[name] = input.value;
                }
            });
            
            try {
                const response = await fetch(`/tools/${toolName}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(arguments)
                });
                
                const result = await response.json();
                const resultDiv = document.getElementById(`${toolName}_result`);
                resultDiv.style.display = 'block';
                resultDiv.textContent = JSON.stringify(result, null, 2);
                
            } catch (error) {
                const resultDiv = document.getElementById(`${toolName}_result`);
                resultDiv.style.display = 'block';
                resultDiv.textContent = `Error: ${error.message}`;
            }
        }
        
        async function getToolProperties(toolName) {
            const response = await fetch('/tools');
            const data = await response.json();
            const tool = data.tools.find(t => t.name === toolName);
            return tool?.inputSchema?.properties || {};
        }
        
        // Load tools on page load
        loadTools();
    </script>
</body>
</html>
        """
        
        return web.Response(text=client_html, content_type='text/html')
    
    async def start_server(self):
        """Start the HTTP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logging.info(f"🚀 HTTP MCP Server started on http://{self.host}:{self.port}")
        logging.info(f"📋 API Documentation: http://{self.host}:{self.port}/")
        logging.info(f"🌐 Web Client: http://{self.host}:{self.port}/client")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logging.info("👋 HTTP server shutdown requested")
        finally:
            await runner.cleanup()


# HTTP MCP Server
class HTTPMCPServer:
    """MCP Server with HTTP transport"""
    
    def __init__(self, plugin_manager, host: str = "localhost", port: int = 8080):
        self.plugin_manager = plugin_manager
        self.transport = HTTPTransport(host, port)
        self.transport.set_request_handler(self._handle_request)
        self.transport.set_plugin_manager(plugin_manager)
        self.name = "mcp-http-server"
        self.version = "2.0.0"
    
    async def start(self):
        """Start the HTTP MCP server"""
        # Load plugins
        tools = await self.plugin_manager.discover_and_load_tools()
        logging.info(f"🔧 Loaded {len(tools)} tools: {list(tools.keys())}")
        
        # Start HTTP server
        await self.transport.start_server()
    
    async def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP requests (same as WebSocket server)"""
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
        """Handle initialize request"""
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": self.name,
                "version": self.version,
                "description": f"HTTP MCP server with {len(self.plugin_manager.loaded_tools)} tools"
            }
        }
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_initialized(self, request: MCPRequest) -> MCPResponse:
        """Handle initialized notification"""
        return MCPResponse(id=None)
    
    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/list request"""
        tools_registry = self.plugin_manager.get_tool_registry()
        tools_list = list(tools_registry.values())
        result = {"tools": tools_list}
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/call request"""
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        if not tool_name:
            return MCPResponse(
                id=request.id,
                error={"code": -32602, "message": "Missing tool name"}
            )
        
        try:
            from plugin_manager import ToolError
            result = await self.plugin_manager.execute_tool(tool_name, arguments)
            return MCPResponse(id=request.id, result=result)
        except ToolError as e:
            return MCPResponse(
                id=request.id,
                error={"code": e.code, "message": e.message}
            )
        except Exception as e:
            logging.error(f"❌ Tool execution error: {e}")
            return MCPResponse(
                id=request.id,
                error={"code": -32603, "message": f"Tool error: {str(e)}"}
            )


# Example usage
if __name__ == "__main__":
    async def main():
        from plugin_manager import PluginManager
        
        plugin_manager = PluginManager("tools")
        server = HTTPMCPServer(plugin_manager, host="localhost", port=8080)
        
        await server.start()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())
