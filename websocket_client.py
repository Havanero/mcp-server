#!/usr/bin/env python3
"""
WebSocket MCP Client - Connect to WebSocket MCP servers

Provides WebSocket client for connecting to WebSocket-based MCP servers.
"""
import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Any
import uuid


class WebSocketMCPClient:
    """
    WebSocket client for MCP servers.
    
    Features:
    - Real-time bidirectional communication
    - Automatic reconnection (optional)
    - Tool discovery and execution
    - Event handling for notifications
    """
    
    def __init__(self, url: str):
        self.url = url
        self.websocket = None
        self.server_info = None
        self.tools = []
        self.initialized = False
        self._pending_requests = {}
        self._request_id_counter = 0
    
    async def connect(self) -> bool:
        """Connect to WebSocket MCP server"""
        try:
            logging.info(f"🔌 Connecting to WebSocket MCP server: {self.url}")
            self.websocket = await websockets.connect(self.url)
            
            # Start message handler task
            asyncio.create_task(self._message_handler())
            
            # Initialize MCP connection
            success = await self._initialize()
            if success:
                await self._mark_initialized()
                await self._list_tools()
            
            return success
            
        except Exception as e:
            logging.error(f"❌ Failed to connect: {e}")
            return False
    
    async def _message_handler(self):
        """Handle incoming messages from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                
                # Handle responses to our requests
                if "id" in data and data["id"] in self._pending_requests:
                    future = self._pending_requests.pop(data["id"])
                    if not future.cancelled():
                        future.set_result(data)
                
                # Handle server notifications
                elif "method" in data:
                    await self._handle_notification(data)
                    
        except websockets.exceptions.ConnectionClosed:
            logging.info("📡 WebSocket connection closed")
        except Exception as e:
            logging.error(f"❌ Message handler error: {e}")
    
    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send request and wait for response"""
        request_id = self._get_next_request_id()
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        
        if params:
            request["params"] = params
        
        # Create future for response
        future = asyncio.Future()
        self._pending_requests[request_id] = future
        
        # Send request
        await self.websocket.send(json.dumps(request))
        
        # Wait for response
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise Exception(f"Request {method} timed out")
    
    async def _initialize(self) -> bool:
        """Initialize MCP connection"""
        try:
            response = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "websocket-mcp-client",
                    "version": "1.0.0"
                }
            })
            
            if "result" in response:
                self.server_info = response["result"]
                logging.info(f"✅ Connected to: {self.server_info.get('serverInfo', {}).get('name', 'Unknown')}")
                return True
            else:
                logging.error(f"❌ Initialize failed: {response.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Initialize error: {e}")
            return False
    
    async def _mark_initialized(self):
        """Send initialized notification"""
        try:
            # Send as notification (no response expected)
            notification = {
                "jsonrpc": "2.0",
                "method": "initialized"
            }
            await self.websocket.send(json.dumps(notification))
            self.initialized = True
            
        except Exception as e:
            logging.error(f"❌ Failed to send initialized: {e}")
    
    async def _list_tools(self):
        """Get list of available tools"""
        try:
            response = await self._send_request("tools/list")
            
            if "result" in response:
                self.tools = response["result"].get("tools", [])
                logging.info(f"🔧 Discovered {len(self.tools)} tools: {[t['name'] for t in self.tools]}")
            else:
                logging.error(f"❌ Failed to list tools: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logging.error(f"❌ List tools error: {e}")
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool by name"""
        if not self.initialized:
            raise Exception("Client not initialized")
        
        try:
            response = await self._send_request("tools/call", {
                "name": name,
                "arguments": arguments or {}
            })
            
            if "result" in response:
                return response["result"]
            else:
                error = response.get("error", {})
                raise Exception(f"Tool call failed: {error.get('message', 'Unknown error')}")
                
        except Exception as e:
            logging.error(f"❌ Tool call error: {e}")
            raise
    
    async def _handle_notification(self, data: Dict[str, Any]):
        """Handle server notifications"""
        method = data.get("method")
        params = data.get("params", {})
        
        logging.info(f"📢 Server notification: {method}")
        # Add custom notification handlers here
    
    def _get_next_request_id(self) -> int:
        """Get next request ID"""
        self._request_id_counter += 1
        return self._request_id_counter
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.websocket:
            await self.websocket.close()
            logging.info("👋 Disconnected from WebSocket server")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools"""
        return self.tools
    
    def get_server_info(self) -> Optional[Dict[str, Any]]:
        """Get server information"""
        return self.server_info


# Interactive WebSocket CLI
async def websocket_cli():
    """Interactive CLI for WebSocket MCP client"""
    print("🌐 WebSocket MCP Client")
    print("=" * 50)
    
    # Connect to server
    url = input("Enter WebSocket URL (default: ws://localhost:8765): ").strip()
    if not url:
        url = "ws://localhost:8765"
    
    client = WebSocketMCPClient(url)
    
    try:
        connected = await client.connect()
        if not connected:
            print("❌ Failed to connect to server")
            return
        
        print(f"\n✅ Connected to server!")
        print(f"Server: {client.server_info}")
        print(f"Available tools: {[t['name'] for t in client.tools]}")
        
        print(f"\n📋 Commands:")
        print(f"  list          - List available tools")
        print(f"  call <tool>   - Call a tool interactively")
        print(f"  exit          - Exit client")
        
        # Interactive loop
        while True:
            try:
                command = input(f"\nws-mcp> ").strip()
                
                if command == "exit":
                    break
                elif command == "list":
                    print(f"\n🔧 Available Tools ({len(client.tools)}):")
                    for tool in client.tools:
                        print(f"  • {tool['name']}: {tool['description']}")
                elif command.startswith("call "):
                    tool_name = command[5:].strip()
                    await _interactive_tool_call(client, tool_name)
                else:
                    print(f"Unknown command: {command}")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
    finally:
        await client.disconnect()


async def _interactive_tool_call(client: WebSocketMCPClient, tool_name: str):
    """Interactively call a tool"""
    # Find tool
    tool = next((t for t in client.tools if t['name'] == tool_name), None)
    if not tool:
        print(f"❌ Tool not found: {tool_name}")
        return
    
    print(f"\n🔧 Calling tool: {tool_name}")
    print(f"Description: {tool['description']}")
    
    # Get tool parameters
    schema = tool.get('inputSchema', {})
    properties = schema.get('properties', {})
    required = schema.get('required', [])
    
    arguments = {}
    
    if properties:
        print(f"\nParameters:")
        for param_name, param_info in properties.items():
            param_type = param_info.get('type', 'string')
            is_required = param_name in required
            
            prompt = f"  {param_name} ({param_type})"
            if is_required:
                prompt += " [required]"
            prompt += ": "
            
            value = input(prompt).strip()
            
            if value:
                # Simple type conversion
                if param_type == 'integer':
                    try:
                        arguments[param_name] = int(value)
                    except ValueError:
                        print(f"    ⚠️  Invalid integer, using string")
                        arguments[param_name] = value
                elif param_type == 'number':
                    try:
                        arguments[param_name] = float(value)
                    except ValueError:
                        print(f"    ⚠️  Invalid number, using string")
                        arguments[param_name] = value
                elif param_type == 'boolean':
                    arguments[param_name] = value.lower() in ['true', 'yes', '1', 'on']
                else:
                    arguments[param_name] = value
    
    try:
        print(f"\n⚡ Executing {tool_name}...")
        result = await client.call_tool(tool_name, arguments)
        
        print(f"\n✅ Result:")
        content = result.get('content', [])
        for item in content:
            print(f"  📄 {item.get('text', str(item))}")
            
    except Exception as e:
        print(f"❌ Tool execution failed: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(websocket_cli())
