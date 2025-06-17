#!/usr/bin/env python3
"""
MCP HTTP Transport - Proper JSON-RPC 2.0 MCP Client

Maintains full MCP protocol compliance while using HTTP transport.
This is a proper MCP client that speaks JSON-RPC 2.0 over HTTP.
"""
import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import aiohttp


class MCPHTTPClient:
    """
    Proper MCP client using JSON-RPC 2.0 over HTTP transport
    
    Maintains full MCP protocol compliance:
    - JSON-RPC 2.0 message structure
    - Standard MCP methods (initialize, tools/list, tools/call)
    - Proper protocol handshake and versioning
    """
    
    def __init__(self, base_url: str = "http://localhost:8081", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.mcp_endpoint = f"{self.base_url}/mcp"
        self.timeout = timeout
        
        # MCP protocol state
        self.protocol_version = "2024-11-05"
        self.client_info = {
            "name": "mcp-python-client",
            "version": "1.0.0"
        }
        self.initialized = False
        self.server_capabilities = {}
        self.server_info = {}
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger("mcp_http_client")
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Connect to MCP server and perform handshake"""
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        try:
            # MCP handshake: initialize
            await self._initialize()
            
            # MCP handshake: send initialized notification
            await self._send_initialized()
            
            self.logger.info("🎯 MCP client connected and initialized")
            
        except Exception as e:
            await self.disconnect()
            raise ConnectionError(f"Failed to connect to MCP server: {e}")
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.session:
            await self.session.close()
            self.session = None
        self.initialized = False
        self.logger.info("👋 MCP client disconnected")
    
    async def _send_jsonrpc_request(self, method: str, params: Dict[str, Any] = None, request_id: str = None) -> Any:
        """Send JSON-RPC 2.0 request to MCP server"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        # Create JSON-RPC request
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        
        # Add ID for requests (not notifications)
        if request_id is not None:
            request_data["id"] = request_id
        
        self.logger.debug(f"Sending MCP request: {method}")
        
        try:
            async with self.session.post(self.mcp_endpoint, json=request_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise ConnectionError(f"HTTP {response.status}: {error_text}")
                
                response_data = await response.json()
                
                # Handle JSON-RPC response
                if "error" in response_data:
                    error = response_data["error"]
                    raise RuntimeError(f"MCP Error [{error['code']}]: {error['message']}")
                
                return response_data.get("result")
                
        except aiohttp.ClientError as e:
            raise ConnectionError(f"HTTP request failed: {e}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")
    
    async def _send_jsonrpc_notification(self, method: str, params: Dict[str, Any] = None):
        """Send JSON-RPC 2.0 notification (no response expected)"""
        await self._send_jsonrpc_request(method, params, request_id=None)
    
    async def _initialize(self):
        """Send MCP initialize request"""
        params = {
            "protocolVersion": self.protocol_version,
            "clientInfo": self.client_info,
            "capabilities": {}  # Client capabilities
        }
        
        result = await self._send_jsonrpc_request("initialize", params, str(uuid.uuid4()))
        
        # Store server info
        self.server_capabilities = result.get("capabilities", {})
        self.server_info = result.get("serverInfo", {})
        
        server_version = result.get("protocolVersion")
        if server_version != self.protocol_version:
            self.logger.warning(f"Protocol version mismatch: client={self.protocol_version}, server={server_version}")
        
        self.logger.info(f"Server: {self.server_info.get('name', 'unknown')} v{self.server_info.get('version', 'unknown')}")
    
    async def _send_initialized(self):
        """Send initialized notification"""
        await self._send_jsonrpc_notification("initialized", {})
        self.initialized = True
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools using MCP tools/list method"""
        if not self.initialized:
            raise RuntimeError("Client not initialized")
        
        result = await self._send_jsonrpc_request("tools/list", {}, str(uuid.uuid4()))
        return result.get("tools", [])
    
    async def call_tool(self, name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call a tool using MCP tools/call method"""
        if not self.initialized:
            raise RuntimeError("Client not initialized")
        
        params = {
            "name": name,
            "arguments": arguments or {}
        }
        
        result = await self._send_jsonrpc_request("tools/call", params, str(uuid.uuid4()))
        return result
    
    async def get_health(self) -> Dict[str, Any]:
        """Get server health (non-MCP endpoint)"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        async with self.session.get(f"{self.base_url}/health") as response:
            if response.status == 200:
                return await response.json()
            else:
                raise ConnectionError(f"Health check failed: HTTP {response.status}")
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information (non-MCP endpoint)"""
        if not self.session:
            raise RuntimeError("Not connected to server")
        
        async with self.session.get(f"{self.base_url}/") as response:
            if response.status == 200:
                return await response.json()
            else:
                raise ConnectionError(f"Server info failed: HTTP {response.status}")


# Test the MCP HTTP client
async def test_mcp_client():
    """Test the MCP HTTP client"""
    logging.basicConfig(level=logging.DEBUG)
    
    print("🧪 Testing MCP HTTP Client")
    print("=" * 40)
    
    async with MCPHTTPClient() as client:
        # Test server health
        health = await client.get_health()
        print(f"✅ Server health: {health['status']}")
        
        # Test server info
        info = await client.get_server_info()
        print(f"✅ Server: {info['server']['name']} v{info['server']['version']}")
        print(f"✅ Protocol: {info['protocol']['name']} {info['protocol']['version']}")
        
        # Test tools listing
        tools = await client.get_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   • {tool['name']}: {tool['description']}")
        
        # Test tool execution
        if tools:
            first_tool = tools[0]
            tool_name = first_tool["name"]
            
            try:
                print(f"\\n🔧 Testing tool: {tool_name}")
                
                # Try calling with empty arguments first
                result = await client.call_tool(tool_name, {})
                print(f"✅ Tool result: {result}")
                
            except Exception as e:
                print(f"⚠️  Tool call failed: {e}")
                
                # Try with some basic arguments if it failed
                if tool_name == "echo":
                    try:
                        result = await client.call_tool(tool_name, {"text": "Hello MCP!"})
                        print(f"✅ Tool result with args: {result}")
                    except Exception as e2:
                        print(f"❌ Tool still failed: {e2}")
    
    print("\\n🎯 MCP client test completed!")


if __name__ == "__main__":
    asyncio.run(test_mcp_client())
