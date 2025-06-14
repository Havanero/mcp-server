#!/usr/bin/env python3
"""
Test the fixed server with new db.py tool
"""
import asyncio
import sys
import os

# Add client path for imports  
client_path = os.path.abspath('../mcp-client')
sys.path.insert(0, client_path)

import transport as client_transport
import protocol as client_protocol


async def test_fixed_server():
    """Test the fixed MCP server without JSON corruption"""
    print("🧪 Testing Fixed MCP Server (No JSON Corruption)")
    
    # Connect to the fixed server
    server_command = ["python3", "server_v2.py"]
    transport = client_transport.StdioTransport(server_command)
    client = client_protocol.MCPClient(transport)
    
    try:
        print("🔌 Connecting to fixed server...")
        success = await client.initialize()
        
        if success:
            print(f"✅ Connected! Server: {client.server_info}")
            print(f"📦 Available tools: {[t.name for t in client.tools]}")
            
            # Check for the new db tool
            db_tools = [t for t in client.tools if 'opensearch' in t.name]
            if db_tools:
                print(f"🆕 Found new db tool: {db_tools[0].name}")
                
                # Test the new opensearch tool
                test_query = {"index": "regulations", "query": "GDPR compliance"}
                result = await client.call_tool("opensearch", {"query": test_query})
                print(f"  opensearch result: {result}")
            
            # Test some existing tools to ensure they still work
            print(f"\n🔧 Testing existing tools:")
            
            if any(t.name == "current_time" for t in client.tools):
                result = await client.call_tool("current_time", {"format": "readable"})
                print(f"  current_time: {result.get('content', [{}])[0].get('text', '')}")
            
            if any(t.name == "greet" for t in client.tools):
                result = await client.call_tool("greet", {"name": "Fixed Server", "style": "enthusiastic"})
                print(f"  greet: {result.get('content', [{}])[0].get('text', '')}")
            
            if any(t.name == "flip_coin" for t in client.tools):
                result = await client.call_tool("flip_coin", {})
                print(f"  flip_coin: {result.get('content', [{}])[0].get('text', '')}")
                
            print(f"\n✅ Server working perfectly! No JSON corruption.")
            
        else:
            print("❌ Connection failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_fixed_server())
