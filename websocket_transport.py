#!/usr/bin/env python3
"""
WebSocket Transport - Enhanced MCP transport for web and remote connectivity

Provides WebSocket-based transport for MCP with multi-client support.
Perfect for web applications, remote connections, and production deployments.
"""
import asyncio
import json
import logging
import websockets
from typing import Dict, Set, Optional, Callable, Awaitable, Any
from dataclasses import dataclass
import uuid

from transport import MCPRequest, MCPResponse


@dataclass 
class WebSocketClient:
    """Represents a connected WebSocket client"""
    id: str
    websocket: websockets.WebSocketServerProtocol
    initialized: bool = False
    client_info: Optional[Dict[str, Any]] = None


class WebSocketTransport:
    """
    WebSocket-based MCP transport supporting multiple concurrent clients.
    
    Features:
    - Multiple simultaneous client connections
    - Real-time bidirectional communication  
    - Web browser compatibility
    - Remote connection support
    - Connection lifecycle management
    - Error isolation per client
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, WebSocketClient] = {}
        self.request_handler: Optional[Callable[[MCPRequest], Awaitable[MCPResponse]]] = None
        self.server = None
        
    def set_request_handler(self, handler: Callable[[MCPRequest], Awaitable[MCPResponse]]):
        """Set the request handler function"""
        self.request_handler = handler
    
    async def start_server(self) -> None:
        """Start the WebSocket server"""
        if not self.request_handler:
            raise ValueError("Request handler must be set before starting server")
        
        logging.info(f"🚀 Starting WebSocket MCP server on {self.host}:{self.port}")
        
        self.server = await websockets.serve(
            self._handle_client_connection,
            self.host,
            self.port,
            ping_interval=30,  # Keep connections alive
            ping_timeout=10
        )
        
        logging.info(f"✅ WebSocket server listening on ws://{self.host}:{self.port}")
        
        # Keep server running
        await self.server.wait_closed()
    
    async def _handle_client_connection(self, websocket):
        """Handle a new client connection"""
        client_id = str(uuid.uuid4())
        client = WebSocketClient(id=client_id, websocket=websocket)
        self.clients[client_id] = client
        
        remote_addr = websocket.remote_address
        logging.info(f"🔌 New client connected: {client_id} from {remote_addr}")
        
        try:
            await self._client_message_loop(client)
        except websockets.exceptions.ConnectionClosed:
            logging.info(f"👋 Client disconnected: {client_id}")
        except Exception as e:
            logging.error(f"❌ Client {client_id} error: {e}")
        finally:
            # Clean up client
            if client_id in self.clients:
                del self.clients[client_id]
                logging.info(f"🧹 Cleaned up client: {client_id}")
    
    async def _client_message_loop(self, client: WebSocketClient):
        """Handle messages from a specific client"""
        async for message in client.websocket:
            try:
                # Parse JSON-RPC message
                if isinstance(message, str):
                    data = json.loads(message)
                else:
                    data = json.loads(message.decode('utf-8'))
                
                # Create MCP request
                request = MCPRequest(
                    id=data.get("id"),
                    method=data.get("method"),
                    params=data.get("params", {})
                )
                
                # Log request
                logging.debug(f"📨 Client {client.id}: {request.method}")
                
                # Track initialization
                if request.method == "initialize":
                    client.client_info = request.params.get("clientInfo", {})
                elif request.method == "initialized":
                    client.initialized = True
                
                # Handle request
                response = await self.request_handler(request)
                
                # Send response (if not notification)
                if response.id is not None:
                    await self._send_response(client, response)
                    
            except json.JSONDecodeError as e:
                logging.error(f"❌ Invalid JSON from client {client.id}: {e}")
                await self._send_error(client, None, -32700, "Parse error")
            except Exception as e:
                logging.error(f"❌ Message handling error for client {client.id}: {e}")
                await self._send_error(client, None, -32603, f"Internal error: {str(e)}")
    
    async def _send_response(self, client: WebSocketClient, response: MCPResponse):
        """Send response to client"""
        try:
            response_data = {
                "jsonrpc": "2.0",
                "id": response.id
            }
            
            if response.result is not None:
                response_data["result"] = response.result
            elif response.error is not None:
                response_data["error"] = response.error
            
            message = json.dumps(response_data)
            await client.websocket.send(message)
            
        except Exception as e:
            logging.error(f"❌ Failed to send response to client {client.id}: {e}")
    
    async def _send_error(self, client: WebSocketClient, request_id: Any, code: int, message: str):
        """Send error response to client"""
        try:
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": code,
                    "message": message
                }
            }
            
            await client.websocket.send(json.dumps(error_response))
            
        except Exception as e:
            logging.error(f"❌ Failed to send error to client {client.id}: {e}")
    
    async def broadcast_notification(self, method: str, params: Dict[str, Any]):
        """Send notification to all connected clients"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        message = json.dumps(notification)
        disconnected_clients = []
        
        for client_id, client in self.clients.items():
            if client.initialized:  # Only send to initialized clients
                try:
                    await client.websocket.send(message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.append(client_id)
                except Exception as e:
                    logging.error(f"❌ Failed to send notification to client {client_id}: {e}")
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            if client_id in self.clients:
                del self.clients[client_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            "server_url": f"ws://{self.host}:{self.port}",
            "connected_clients": len(self.clients),
            "initialized_clients": len([c for c in self.clients.values() if c.initialized]),
            "client_details": [
                {
                    "id": client.id,
                    "initialized": client.initialized,
                    "client_info": client.client_info,
                    "remote_address": str(client.websocket.remote_address)
                }
                for client in self.clients.values()
            ]
        }
    
    async def shutdown(self):
        """Gracefully shutdown the server"""
        if self.server:
            logging.info("🛑 Shutting down WebSocket server...")
            self.server.close()
            await self.server.wait_closed()
            
            # Close all client connections
            for client in self.clients.values():
                await client.websocket.close()
            
            self.clients.clear()
            logging.info("✅ WebSocket server shutdown complete")


# WebSocket-enabled MCP Server
class WebSocketMCPServer:
    """MCP Server with WebSocket transport"""
    
    def __init__(self, plugin_manager, host: str = "localhost", port: int = 8765):
        self.plugin_manager = plugin_manager
        self.transport = WebSocketTransport(host, port)
        self.transport.set_request_handler(self._handle_request)
        self.name = "mcp-websocket-server"
        self.version = "2.0.0"
    
    async def start(self):
        """Start the WebSocket MCP server"""
        # Load plugins
        tools = await self.plugin_manager.discover_and_load_tools()
        logging.info(f"🔧 Loaded {len(tools)} tools: {list(tools.keys())}")
        
        # Start WebSocket server
        await self.transport.start_server()
    
    async def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP requests (same logic as stdio server)"""
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
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
                "description": f"WebSocket MCP server with {len(self.plugin_manager.loaded_tools)} tools"
            }
        }
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_initialized(self, request: MCPRequest) -> MCPResponse:
        """Handle initialized notification"""
        logging.info("✅ Client initialization complete")
        return MCPResponse(id=None)  # Notification, no response
    
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
        server = WebSocketMCPServer(plugin_manager, host="localhost", port=8765)
        
        try:
            await server.start()
        except KeyboardInterrupt:
            logging.info("👋 Server shutdown requested")
            await server.transport.shutdown()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())
