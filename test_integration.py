#!/usr/bin/env python3
"""
Test the MCP server with our client
"""
import asyncio
import sys
import os

# Add client path and import from client modules
client_path = os.path.abspath('../mcp-client')
sys.path.insert(0, client_path)

# Import client modules explicitly to avoid conflicts with local transport.py
import transport as client_transport
import protocol as client_protocol


async def test_client_server():
    """Test our MCP server with our client"""
    print("🧪 Testing MCP Server with Client")

    # Start client connected to our server
    server_command = ["python3", "server.py"]
    transport = client_transport.StdioTransport(server_command)
    client = client_protocol.MCPClient(transport)

    try:
        # Initialize
        print("🔌 Connecting...")
        success = await client.initialize()

        if success:
            print(f"✅ Connected! Server: {client.server_info}")
            print(f"📦 Tools found: {[t.name for t in client.tools]}")

            # Test each tool
            for tool in client.tools:
                print(f"\n🔧 Testing tool: {tool.name}")

                if tool.name == "echo":
                    result = await client.call_tool("echo", {"text": "Hello from client!"})
                    print(f"  Result: {result}")

                elif tool.name == "calculate":
                    result = await client.call_tool("calculate", {
                        "operation": "add",
                        "a": 15,
                        "b": 27
                    })
                    print(f"  Result: {result}")

                elif tool.name == "current_time":
                    result = await client.call_tool("current_time", {})
                    print(f"  Result: {result}")

            print("\n✅ All tests passed!")
        else:
            print("❌ Connection failed")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_client_server())
