#!/usr/bin/env python3
"""
Test the new plugin-based MCP server
"""
import asyncio
import sys
import os

# Add client path for imports  
client_path = os.path.abspath('../mcp-client')
sys.path.insert(0, client_path)

import transport as client_transport
import protocol as client_protocol


async def test_plugin_server():
    """Test the plugin-based MCP server"""
    print("🧪 Testing Plugin-Based MCP Server")
    
    # Connect to the new plugin server
    server_command = ["python3", "server_v2.py"]
    transport = client_transport.StdioTransport(server_command)
    client = client_protocol.MCPClient(transport)
    
    try:
        print("🔌 Connecting to plugin server...")
        success = await client.initialize()
        
        if success:
            print(f"✅ Connected! Server: {client.server_info}")
            print(f"📦 Auto-discovered tools: {[t.name for t in client.tools]}")
            
            # Show detailed tool info
            print("\n🔧 Tool Details:")
            for tool in client.tools:
                print(f"  • {tool.name}: {tool.description}")
            
            # Test file operations tool
            if any(t.name == "file_ops" for t in client.tools):
                print("\n📄 Testing file operations...")
                
                # Write a test file
                write_result = await client.call_tool("file_ops", {
                    "operation": "write",
                    "path": "test_plugin.txt", 
                    "content": "Hello from plugin system!"
                })
                print("  Write result:", write_result.get('content', [{}])[0].get('text', ''))
                
                # Read it back
                read_result = await client.call_tool("file_ops", {
                    "operation": "read",
                    "path": "test_plugin.txt"
                })
                print("  Read result:", read_result.get('content', [{}])[-1].get('text', ''))
                
                # List workspace
                list_result = await client.call_tool("file_ops", {
                    "operation": "list",
                    "path": "."
                })
                print("  List result:", list_result.get('content', [{}])[0].get('text', ''))
            
            # Test system info tool
            if any(t.name == "system_info" for t in client.tools):
                print("\n🖥️  Testing system info...")
                
                # Get overview
                overview_result = await client.call_tool("system_info", {
                    "info_type": "overview"
                })
                print("  Overview:", overview_result.get('content', [{}])[0].get('text', ''))
                
                # Get disk info
                disk_result = await client.call_tool("system_info", {
                    "info_type": "disk"
                })
                print("  Disk info:", disk_result.get('content', [{}])[0].get('text', ''))
            
            print("\n✅ Plugin system tests completed!")
            
        else:
            print("❌ Connection failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


async def test_plugin_manager_directly():
    """Test plugin manager independently"""
    print("\n🔍 Testing Plugin Manager Directly")
    
    # Import plugin manager
    sys.path.append('.')
    from plugin_manager import PluginManager
    
    manager = PluginManager("tools")
    tools = await manager.discover_and_load_tools()
    
    print(f"📦 Discovered tools: {list(tools.keys())}")
    
    for name, tool in tools.items():
        print(f"\n🔧 Tool: {name}")
        print(f"   Description: {tool.description}")
        print(f"   Schema: {tool.input_schema}")
        
        # Test a simple call
        if name == "system_info":
            try:
                result = await manager.execute_tool(name, {"info_type": "overview"})
                print(f"   Test result: {result}")
            except Exception as e:
                print(f"   Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_plugin_server())
    asyncio.run(test_plugin_manager_directly())
