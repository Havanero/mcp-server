#!/usr/bin/env python3
"""
Test all transport options for MCP server
"""
import asyncio
import sys
import os

# Add client path
client_path = os.path.abspath('../mcp-client')
sys.path.insert(0, client_path)

from websocket_client import WebSocketMCPClient
import aiohttp


async def test_stdio_transport():
    """Test stdio transport (original)"""
    print("🧪 Testing Stdio Transport")
    print("-" * 40)
    
    import transport as client_transport
    import protocol as client_protocol
    
    server_command = ["python3", "server_v2.py"]
    transport = client_transport.StdioTransport(server_command)
    client = client_protocol.MCPClient(transport)
    
    try:
        success = await client.initialize()
        if success:
            print(f"✅ Stdio: {len(client.tools)} tools available")
            
            # Test a tool
            if any(t.name == "current_time" for t in client.tools):
                result = await client.call_tool("current_time", {"format": "readable"})
                print(f"   Tool result: {result.get('content', [{}])[0].get('text', '')}")
        else:
            print("❌ Stdio connection failed")
    finally:
        await client.close()


async def test_websocket_transport():
    """Test WebSocket transport"""
    print("\n🧪 Testing WebSocket Transport")
    print("-" * 40)
    
    # Start WebSocket server in background
    server_task = None
    try:
        # Import and start WebSocket server
        from websocket_transport import WebSocketMCPServer
        from plugin_manager import PluginManager
        
        plugin_manager = PluginManager("tools")
        server = WebSocketMCPServer(plugin_manager, host="localhost", port=8765)
        
        # Start server in background
        server_task = asyncio.create_task(server.start())
        
        # Give server time to start
        await asyncio.sleep(2)
        
        # Connect client
        client = WebSocketMCPClient("ws://localhost:8765")
        
        connected = await client.connect()
        if connected:
            print(f"✅ WebSocket: {len(client.tools)} tools available")
            
            # Test a tool
            if any(t['name'] == "greet" for t in client.tools):
                result = await client.call_tool("greet", {"name": "WebSocket", "style": "enthusiastic"})
                content = result.get('content', [])
                if content:
                    print(f"   Tool result: {content[0].get('text', '')}")
        else:
            print("❌ WebSocket connection failed")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")
    finally:
        if server_task:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


async def test_http_transport():
    """Test HTTP transport"""
    print("\n🧪 Testing HTTP Transport")
    print("-" * 40)
    
    # Start HTTP server in background
    server_task = None
    try:
        from http_transport import HTTPMCPServer
        from plugin_manager import PluginManager
        
        plugin_manager = PluginManager("tools")
        server = HTTPMCPServer(plugin_manager, host="localhost", port=8080)
        
        # Start server in background
        server_task = asyncio.create_task(server.start())
        
        # Give server time to start
        await asyncio.sleep(2)
        
        # Test HTTP endpoints
        async with aiohttp.ClientSession() as session:
            # Test tools list
            async with session.get("http://localhost:8080/tools") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ HTTP: {len(data['tools'])} tools available")
                else:
                    print(f"❌ HTTP tools list failed: {resp.status}")
                    return
            
            # Test tool call
            tool_data = {"name": "HTTP Test", "style": "friendly"}
            async with session.post("http://localhost:8080/tools/greet", json=tool_data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get('result', {}).get('content', [])
                    if content:
                        print(f"   Tool result: {content[0].get('text', '')}")
                else:
                    print(f"❌ HTTP tool call failed: {resp.status}")
            
            # Test health endpoint
            async with session.get("http://localhost:8080/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print(f"   Health: {health['status']}")
        
    except Exception as e:
        print(f"❌ HTTP test error: {e}")
    finally:
        if server_task:
            server_task.cancel()
            try:
                await server_task
            except asyncio.CancelledError:
                pass


async def run_transport_comparison():
    """Run comparison of all transport options"""
    print("🚀 MCP Transport Comparison Test")
    print("=" * 50)
    
    await test_stdio_transport()
    await test_websocket_transport() 
    await test_http_transport()
    
    print("\n📊 Transport Summary:")
    print("=" * 50)
    print("📡 Stdio:     Local only, single client, fastest")
    print("🌐 WebSocket: Multi-client, real-time, bidirectional")
    print("🔗 HTTP:      REST-style, web-friendly, stateless")
    print("\n🏆 Recommendation: WebSocket for production, Stdio for development")


if __name__ == "__main__":
    asyncio.run(run_transport_comparison())
