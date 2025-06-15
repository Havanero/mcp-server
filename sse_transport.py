#!/usr/bin/env python3
"""
SSE MCP Transport - Server-Sent Events for streaming MCP responses
Implements reliable streaming for LLM integration with auto-reconnection
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Callable
from dataclasses import dataclass, field
from aiohttp import web, ClientSession
import aiohttp
from contextlib import asynccontextmanager
import uuid
import time

from transport import MCPRequest, MCPResponse


@dataclass
class SSEContext:
    """SSE streaming context with hierarchical management"""
    stream_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_info: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    message_count: int = 0
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class SSETransport:
    """
    Server-Sent Events MCP transport with streaming capabilities.
    
    Features:
    - Real-time streaming responses
    - Automatic client reconnection
    - HTTP-based (firewall-friendly)
    - Progress updates for long operations
    - LLM token streaming optimized
    """
    
    def __init__(self, host: str = "localhost", port: int = 8081):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.request_handler: Optional[Callable] = None
        self.plugin_manager = None
        self.active_streams: Dict[str, SSEContext] = {}
        self._setup_routes()
        self._setup_cors()
    
    def set_request_handler(self, handler: Callable):
        """Set MCP request handler"""
        self.request_handler = handler
    
    def set_plugin_manager(self, plugin_manager):
        """Set plugin manager for streaming tools"""
        self.plugin_manager = plugin_manager
    
    def _setup_routes(self):
        """Setup SSE and HTTP routes"""
        # SSE streaming endpoints (GET only - EventSource requirement)
        self.app.router.add_get('/stream/tools/{tool_name}', self._handle_tool_stream)
        self.app.router.add_get('/stream/llm', self._handle_llm_stream)
        self.app.router.add_get('/stream/mcp', self._handle_mcp_stream)
        
        # POST endpoints for complex arguments -> redirect to streaming
        self.app.router.add_post('/stream/tools/{tool_name}', self._handle_tool_stream_post)
        
        # Traditional HTTP endpoints (fallback)
        self.app.router.add_post('/mcp', self._handle_mcp_request)
        self.app.router.add_get('/tools', self._handle_list_tools)
        self.app.router.add_post('/tools/{tool_name}', self._handle_call_tool)
        
        # Utility endpoints
        self.app.router.add_get('/health', self._handle_health)
        self.app.router.add_get('/stats', self._handle_stats)
        self.app.router.add_get('/streams', self._handle_stream_stats)
        
        # Documentation
        self.app.router.add_get('/', self._handle_docs)
    
    def _setup_cors(self):
        """Setup CORS for browser EventSource"""
        @web.middleware
        async def cors_handler(request, handler):
            response = await handler(request)
            response.headers.update({
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Last-Event-ID',
                'Access-Control-Expose-Headers': 'X-Stream-ID'
            })
            return response
    
    async def _handle_tool_stream_post(self, request: web.Request) -> web.Response:
        """Handle POST /stream/tools/{tool_name} - Accept JSON, return stream URL"""
        tool_name = request.match_info['tool_name']
        
        try:
            # Get JSON arguments from POST body
            arguments = await request.json()
            logging.info(f"📄 POST stream request for {tool_name} with JSON: {arguments}")
            
            # Convert to query string for GET redirect
            from urllib.parse import urlencode
            query_string = urlencode(arguments)
            stream_url = f"/stream/tools/{tool_name}?{query_string}"
            
            # Return streaming instructions
            return web.json_response({
                "message": "Use EventSource with the provided URL for streaming",
                "stream_url": stream_url,
                "full_url": f"{request.scheme}://{request.host}{stream_url}",
                "tool": tool_name,
                "arguments": arguments,
                "javascript_example": f"new EventSource('{stream_url}')"
            })
            
        except Exception as e:
            logging.error(f"❌ POST stream error for {tool_name}: {e}")
            return web.json_response({
                "error": str(e),
                "tool": tool_name
            }, status=500)
        
        self.app.middlewares.append(cors_handler)
        
        # Handle preflight requests
        async def options_handler(request):
            return web.Response(headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Last-Event-ID'
            })
        
        self.app.router.add_options('/{path:.*}', options_handler)
    
    async def _create_sse_response(self, request: web.Request) -> web.StreamResponse:
        """Create SSE response with proper headers"""
        response = web.StreamResponse()
        response.headers.update({
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',  # Disable nginx buffering
        })
        
        # Handle reconnection
        last_event_id = request.headers.get('Last-Event-ID', '0')
        
        await response.prepare(request)
        return response
    
    async def _send_sse_message(self, 
                               response: web.StreamResponse, 
                               context: SSEContext,
                               event_type: str = "message",
                               data: Any = None,
                               event_id: Optional[str] = None):
        """Send SSE formatted message"""
        try:
            if event_id is None:
                event_id = str(context.message_count)
            
            message_lines = []
            message_lines.append(f"id: {event_id}")
            message_lines.append(f"event: {event_type}")
            
            if data is not None:
                json_data = json.dumps(data)
                message_lines.append(f"data: {json_data}")
            
            message_lines.append("")  # Empty line terminates message
            
            message = "\n".join(message_lines) + "\n"
            await response.write(message.encode())
            
            context.message_count += 1
            
        except Exception as e:
            logging.error(f"❌ SSE send error: {e}")
            context.active = False
    
    async def _handle_tool_stream(self, request: web.Request) -> web.StreamResponse:
        """Handle GET /stream/tools/{tool_name} - Stream tool execution"""
        tool_name = request.match_info['tool_name']
        arguments = {k: v for k, v in request.query.items()}
        
        # Convert query params to proper types (simple heuristic)
        for key, value in arguments.items():
            if value.isdigit():
                arguments[key] = int(value)
            elif value.lower() in ['true', 'false']:
                arguments[key] = value.lower() == 'true'
        
        context = SSEContext()
        self.active_streams[context.stream_id] = context
        
        response = await self._create_sse_response(request)
        response.headers['X-Stream-ID'] = context.stream_id
        
        try:
            logging.info(f"🌊 Starting tool stream: {tool_name} with args: {arguments}")
            
            # Send initial status
            await self._send_sse_message(response, context, "started", {
                "tool": tool_name,
                "arguments": arguments,
                "stream_id": context.stream_id
            })
            
            # Check if tool supports streaming
            if hasattr(self.plugin_manager, 'execute_tool_stream'):
                logging.info(f"🔄 Using streaming execution for {tool_name}")
                # Stream tool execution
                async for progress in self.plugin_manager.execute_tool_stream(tool_name, arguments):
                    if not context.active:
                        break
                    
                    await self._send_sse_message(response, context, "progress", progress)
            
            else:
                logging.info(f"🔄 Using fallback execution for {tool_name}")
                # Fallback to regular execution with progress simulation
                await self._send_sse_message(response, context, "progress", {
                    "message": f"Executing {tool_name}...", 
                    "progress": 0.3
                })
                
                # Execute the tool
                logging.info(f"⚙️ Executing tool {tool_name} with {arguments}")
                result = await self.plugin_manager.execute_tool(tool_name, arguments)
                logging.info(f"✅ Tool {tool_name} completed with result: {type(result)}")
                
                await self._send_sse_message(response, context, "result", {
                    "tool": tool_name,
                    "result": result,
                    "status": "completed"
                })
            
            # Send completion
            await self._send_sse_message(response, context, "completed", {
                "message": "Tool execution completed",
                "duration": time.time() - context.start_time
            })
            
        except Exception as e:
            logging.error(f"❌ Tool stream error for {tool_name}: {e}")
            import traceback
            traceback.print_exc()
            await self._send_sse_message(response, context, "error", {
                "error": str(e),
                "tool": tool_name,
                "traceback": traceback.format_exc()
            })
        
        finally:
            self.active_streams.pop(context.stream_id, None)
            logging.info(f"🧹 Cleaned up stream for {tool_name}")
        
        return response
    
    async def _handle_llm_stream(self, request: web.Request) -> web.StreamResponse:
        """Handle GET /stream/llm - Stream LLM responses"""
        prompt = request.query.get('prompt', '')
        model = request.query.get('model', 'default')
        
        context = SSEContext()
        self.active_streams[context.stream_id] = context
        
        response = await self._create_sse_response(request)
        response.headers['X-Stream-ID'] = context.stream_id
        
        try:
            # Send initial status
            await self._send_sse_message(response, context, "started", {
                "model": model,
                "prompt_length": len(prompt),
                "stream_id": context.stream_id
            })
            
            # Simulate LLM streaming (replace with actual LLM integration)
            tokens = prompt.split() if prompt else ["Hello", "world", "from", "streaming", "MCP"]
            
            for i, token in enumerate(tokens):
                if not context.active:
                    break
                
                await self._send_sse_message(response, context, "token", {
                    "token": token,
                    "position": i,
                    "total": len(tokens)
                })
                
                # Simulate processing delay
                await asyncio.sleep(0.1)
            
            # Send completion
            await self._send_sse_message(response, context, "completed", {
                "message": "LLM response completed",
                "token_count": len(tokens),
                "duration": time.time() - context.start_time
            })
            
        except Exception as e:
            logging.error(f"❌ LLM stream error: {e}")
            await self._send_sse_message(response, context, "error", {
                "error": str(e),
                "model": model
            })
        
        finally:
            self.active_streams.pop(context.stream_id, None)
        
        return response
    
    async def _handle_mcp_stream(self, request: web.Request) -> web.StreamResponse:
        """Handle GET /stream/mcp - Stream MCP method execution"""
        method = request.query.get('method', 'tools/list')
        
        context = SSEContext()
        self.active_streams[context.stream_id] = context
        
        response = await self._create_sse_response(request)
        
        try:
            # Parse params from query string
            params = {k: v for k, v in request.query.items() if k != 'method'}
            
            # Create MCP request
            mcp_request = MCPRequest(
                id=context.stream_id,
                method=method,
                params=params
            )
            
            await self._send_sse_message(response, context, "started", {
                "method": method,
                "params": params
            })
            
            # Execute MCP request
            if self.request_handler:
                mcp_response = await self.request_handler(mcp_request)
                
                await self._send_sse_message(response, context, "result", {
                    "method": method,
                    "result": mcp_response.result,
                    "error": mcp_response.error
                })
            
            await self._send_sse_message(response, context, "completed", {
                "message": "MCP method completed"
            })
            
        except Exception as e:
            await self._send_sse_message(response, context, "error", {
                "error": str(e),
                "method": method
            })
        
        finally:
            self.active_streams.pop(context.stream_id, None)
        
        return response
    
    # Traditional HTTP handlers (same as HTTP transport)
    async def _handle_mcp_request(self, request: web.Request) -> web.Response:
        """Handle POST /mcp - Traditional MCP JSON-RPC"""
        try:
            data = await request.json()
            mcp_request = MCPRequest(
                id=data.get("id"),
                method=data.get("method"),
                params=data.get("params", {})
            )
            
            if not self.request_handler:
                return web.json_response({
                    "jsonrpc": "2.0",
                    "id": mcp_request.id,
                    "error": {"code": -32603, "message": "No request handler"}
                }, status=500)
            
            response = await self.request_handler(mcp_request)
            
            response_data = {"jsonrpc": "2.0", "id": response.id}
            if response.result is not None:
                response_data["result"] = response.result
            elif response.error is not None:
                response_data["error"] = response.error
            
            return web.json_response(response_data)
            
        except Exception as e:
            return web.json_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }, status=500)
    
    async def _handle_list_tools(self, request: web.Request) -> web.Response:
        """Handle GET /tools"""
        try:
            if not self.plugin_manager:
                return web.json_response({"error": "Plugin manager not configured"}, status=500)
            
            tools_registry = self.plugin_manager.get_tool_registry()
            tools_list = list(tools_registry.values())
            
            # Add streaming URLs to each tool
            for tool in tools_list:
                tool["streaming_url"] = f"/stream/tools/{tool['name']}"
            
            return web.json_response({
                "tools": tools_list,
                "count": len(tools_list),
                "streaming_available": True
            })
            
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def _handle_call_tool(self, request: web.Request) -> web.Response:
        """Handle POST /tools/{tool_name}"""
        tool_name = request.match_info['tool_name']
        
        try:
            arguments = await request.json()
        except:
            arguments = {}
        
        try:
            result = await self.plugin_manager.execute_tool(tool_name, arguments)
            return web.json_response({
                "tool": tool_name,
                "result": result,
                "streaming_url": f"/stream/tools/{tool_name}"
            })
            
        except Exception as e:
            return web.json_response({
                "tool": tool_name,
                "error": str(e)
            }, status=500)
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check with streaming info"""
        return web.json_response({
            "status": "healthy",
            "server": "SSE MCP Server",
            "version": "2.0.0",
            "streaming": {
                "enabled": True,
                "active_streams": len(self.active_streams),
                "endpoints": ["/stream/tools/{name}", "/stream/llm", "/stream/mcp"]
            },
            "tools_loaded": len(self.plugin_manager.loaded_tools) if self.plugin_manager else 0
        })
    
    async def _handle_stats(self, request: web.Request) -> web.Response:
        """Server statistics"""
        return web.json_response({
            "server": {
                "name": "SSE MCP Server",
                "transport": "Server-Sent Events",
                "host": self.host,
                "port": self.port
            },
            "streaming": {
                "active_streams": len(self.active_streams),
                "total_messages": sum(ctx.message_count for ctx in self.active_streams.values())
            },
            "plugins": self.plugin_manager.get_stats() if self.plugin_manager else {}
        })
    
    async def _handle_stream_stats(self, request: web.Request) -> web.Response:
        """Active stream statistics"""
        streams_info = []
        for stream_id, context in self.active_streams.items():
            streams_info.append({
                "stream_id": stream_id,
                "duration": time.time() - context.start_time,
                "message_count": context.message_count,
                "active": context.active,
                "client_info": context.client_info
            })
        
        return web.json_response({
            "active_streams": len(self.active_streams),
            "streams": streams_info
        })
    
    async def _handle_docs(self, request: web.Request) -> web.Response:
        """API documentation with SSE examples"""
        docs_html = """
<!DOCTYPE html>
<html>
<head>
    <title>SSE MCP Server</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .method { color: #007acc; font-weight: bold; }
        .sse { color: #28a745; font-weight: bold; }
        code { background: #eee; padding: 2px 4px; border-radius: 3px; }
        pre { background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <h1>🌊 SSE MCP Server</h1>
    <p>Server-Sent Events interface for streaming MCP responses</p>
    
    <h2>📡 SSE Streaming Endpoints</h2>
    
    <div class="endpoint">
        <div class="sse">GET /stream/tools/{tool_name}</div>
        <p>Stream tool execution with real-time progress</p>
        <code>curl -N "http://localhost:8081/stream/tools/opensearch?query=GDPR&size=100"</code>
    </div>
    
    <div class="endpoint">
        <div class="sse">GET /stream/llm</div>
        <p>Stream LLM token generation</p>
        <code>curl -N "http://localhost:8081/stream/llm?prompt=Hello%20world&model=gpt-4"</code>
    </div>
    
    <div class="endpoint">
        <div class="sse">GET /stream/mcp</div>
        <p>Stream MCP method execution</p>
        <code>curl -N "http://localhost:8081/stream/mcp?method=tools/list"</code>
    </div>
    
    <h2>📋 Traditional HTTP Endpoints</h2>
    
    <div class="endpoint">
        <div class="method">GET /tools</div>
        <p>List available tools</p>
    </div>
    
    <div class="endpoint">
        <div class="method">POST /tools/{tool_name}</div>
        <p>Execute tool (non-streaming)</p>
    </div>
    
    <h2>🌐 JavaScript EventSource Example</h2>
    <pre>
const eventSource = new EventSource('/stream/tools/opensearch?query=GDPR');

eventSource.addEventListener('started', (event) => {
    const data = JSON.parse(event.data);
    console.log('Tool started:', data);
});

eventSource.addEventListener('progress', (event) => {
    const data = JSON.parse(event.data);
    console.log('Progress:', data);
});

eventSource.addEventListener('result', (event) => {
    const data = JSON.parse(event.data);
    console.log('Result:', data);
});

eventSource.addEventListener('completed', (event) => {
    eventSource.close();
    console.log('Completed');
});

eventSource.addEventListener('error', (event) => {
    console.error('Stream error');
});
    </pre>
    
    <h2>✨ Features</h2>
    <ul>
        <li>🔄 <strong>Auto-reconnection</strong> - Built into EventSource</li>
        <li>🛡️ <strong>Firewall-friendly</strong> - Standard HTTP</li>
        <li>📊 <strong>Real-time progress</strong> - For long operations</li>
        <li>🤖 <strong>LLM streaming</strong> - Token-by-token responses</li>
        <li>🔧 <strong>Tool streaming</strong> - Progressive results</li>
    </ul>
</body>
</html>
        """
        return web.Response(text=docs_html, content_type='text/html')
    
    async def start_server(self):
        """Start the SSE MCP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logging.info(f"🌊 SSE MCP Server started on http://{self.host}:{self.port}")
        logging.info(f"📡 Streaming endpoints: /stream/tools/*, /stream/llm, /stream/mcp")
        logging.info(f"📋 Documentation: http://{self.host}:{self.port}/")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logging.info("👋 SSE server shutdown requested")
        finally:
            await runner.cleanup()
    
    async def broadcast_to_streams(self, event_type: str, data: Any):
        """Broadcast message to all active streams"""
        dead_streams = []
        
        for stream_id, context in self.active_streams.items():
            if not context.active:
                dead_streams.append(stream_id)
        
        # Clean up dead streams
        for stream_id in dead_streams:
            self.active_streams.pop(stream_id, None)


# SSE-enabled MCP Server
class SSEMCPServer:
    """MCP Server with SSE transport"""
    
    def __init__(self, plugin_manager, host: str = "localhost", port: int = 8081):
        self.plugin_manager = plugin_manager
        self.transport = SSETransport(host, port)
        self.transport.set_request_handler(self._handle_request)
        self.transport.set_plugin_manager(plugin_manager)
        self.name = "mcp-sse-server"
        self.version = "2.0.0"
    
    async def start(self):
        """Start the SSE MCP server"""
        tools = await self.plugin_manager.discover_and_load_tools()
        logging.info(f"🔧 Loaded {len(tools)} tools: {list(tools.keys())}")
        await self.transport.start_server()
    
    async def _handle_request(self, request):
        """Handle MCP requests (same as other transports)"""
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
    
    async def _handle_initialize(self, request):
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"streaming": True}},
            "serverInfo": {
                "name": self.name,
                "version": self.version,
                "description": f"SSE MCP server with streaming support"
            }
        }
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_initialized(self, request):
        return MCPResponse(id=None)
    
    async def _handle_tools_list(self, request):
        tools_registry = self.plugin_manager.get_tool_registry()
        tools_list = list(tools_registry.values())
        
        # Add streaming URLs to each tool
        for tool in tools_list:
            tool["streaming_url"] = f"/stream/tools/{tool['name']}"
        
        result = {"tools": tools_list}
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_tools_call(self, request):
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        if not tool_name:
            return MCPResponse(
                id=request.id,
                error={"code": -32602, "message": "Missing tool name"}
            )
        
        try:
            result = await self.plugin_manager.execute_tool(tool_name, arguments)
            return MCPResponse(id=request.id, result=result)
        except Exception as e:
            return MCPResponse(
                id=request.id,
                error={"code": -32603, "message": str(e)}
            )


if __name__ == "__main__":
    async def main():
        from plugin_manager import PluginManager
        
        plugin_manager = PluginManager("tools")
        server = SSEMCPServer(plugin_manager, host="localhost", port=8081)
        
        await server.start()
    
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
