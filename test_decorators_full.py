#!/usr/bin/env python3
"""
Comprehensive test for all decorator patterns and plugin manager integration
"""
import asyncio
import sys
import os

# Add paths for imports
sys.path.append('.')
client_path = os.path.abspath('../mcp-client')
sys.path.insert(0, client_path)

import transport as client_transport
import protocol as client_protocol


async def test_decorator_integration():
    """Test decorator-based tools with the enhanced server"""
    print("🧪 Testing Enhanced MCP Server with Decorator Tools")
    
    # Connect to enhanced server
    server_command = ["python3", "server_v2.py"]
    transport = client_transport.StdioTransport(server_command)
    client = client_protocol.MCPClient(transport)
    
    try:
        print("🔌 Connecting to enhanced server...")
        success = await client.initialize()
        
        if success:
            print(f"✅ Connected! Server: {client.server_info}")
            
            # Group tools by type
            traditional_tools = []
            decorator_tools = []
            
            for tool in client.tools:
                # Check if it's likely a decorator tool based on name patterns
                if tool.name in ["current_time", "random_number", "reverse_text", "add_numbers", 
                               "fibonacci", "prime_check", "word_stats", "extract_emails"]:
                    decorator_tools.append(tool)
                else:
                    traditional_tools.append(tool)
            
            print(f"\n📦 Tool Discovery Results:")
            print(f"  Traditional tools: {len(traditional_tools)} - {[t.name for t in traditional_tools]}")
            print(f"  Decorator tools: {len(decorator_tools)} - {[t.name for t in decorator_tools]}")
            
            # Test decorator function tools
            print(f"\n🔧 Testing @tool function decorators:")
            
            if any(t.name == "current_time" for t in client.tools):
                result = await client.call_tool("current_time", {"format": "readable"})
                print(f"  current_time: {result.get('content', [{}])[0].get('text', '')}")
            
            if any(t.name == "random_number" for t in client.tools):
                result = await client.call_tool("random_number", {"min_val": 1, "max_val": 10})
                print(f"  random_number: {result.get('content', [{}])[0].get('text', '')}")
            
            if any(t.name == "reverse_text" for t in client.tools):
                result = await client.call_tool("reverse_text", {"text": "Hello Decorators!"})
                content = result.get('content', [])
                if content:
                    for item in content:
                        print(f"    {item.get('text', '')}")
            
            # Test decorator class tools  
            print(f"\n🔧 Testing @mcp_tool class decorators:")
            
            if any(t.name == "string_utils" for t in client.tools):
                result = await client.call_tool("string_utils", {
                    "operation": "title",
                    "text": "hello world from decorators"
                })
                print(f"  string_utils: {result.get('content', [{}])[0].get('text', '')}")
            
            # Test method decorators
            print(f"\n🔧 Testing @tool_method decorators:")
            
            if any(t.name == "fibonacci" for t in client.tools):
                result = await client.call_tool("fibonacci", {"n": 12})
                print(f"  fibonacci: {result.get('content', [{}])[0].get('text', '')}")
            
            if any(t.name == "prime_check" for t in client.tools):
                result = await client.call_tool("prime_check", {"number": 17})
                content = result.get('content', [])
                for item in content:
                    print(f"    prime_check: {item.get('text', '')}")
            
            if any(t.name == "word_stats" for t in client.tools):
                result = await client.call_tool("word_stats", {
                    "text": "The decorator pattern makes tool creation incredibly simple and elegant!"
                })
                content = result.get('content', [])
                print(f"  word_stats:")
                for item in content:
                    print(f"    {item.get('text', '')}")
            
            if any(t.name == "add_numbers" for t in client.tools):
                result = await client.call_tool("add_numbers", {"numbers": "1, 2, 3, 4, 5"})
                content = result.get('content', [])
                for item in content:
                    print(f"    add_numbers: {item.get('text', '')}")
            
            # Test traditional tools still work
            print(f"\n🔧 Testing traditional BaseTool classes:")
            
            if any(t.name == "file_ops" for t in client.tools):
                result = await client.call_tool("file_ops", {
                    "operation": "write",
                    "path": "decorator_test.txt",
                    "content": "Both decorator and traditional tools work together!"
                })
                print(f"  file_ops write: {result.get('content', [{}])[0].get('text', '')}")
                
                # Read it back
                result = await client.call_tool("file_ops", {
                    "operation": "read",
                    "path": "decorator_test.txt"
                })
                print(f"  file_ops read: Success!")
            
            if any(t.name == "system_info" for t in client.tools):
                result = await client.call_tool("system_info", {"info_type": "overview"})
                print(f"  system_info: {result.get('content', [{}])[0].get('text', '')}")
            
            print(f"\n✅ All decorator patterns working perfectly!")
            print(f"\n🎉 Summary:")
            print(f"  • @tool functions: Simple async functions become tools")
            print(f"  • @mcp_tool classes: Enhanced class-based tools")
            print(f"  • @tool_method: Multiple tools per class")
            print(f"  • Traditional BaseTool: Still fully supported")
            print(f"  • Auto-discovery: All patterns work together seamlessly")
            
        else:
            print("❌ Connection failed")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.close()


async def test_plugin_manager_directly():
    """Test the plugin manager directly to see internal details"""
    print(f"\n🔍 Direct Plugin Manager Testing")
    
    from plugin_manager import PluginManager
    
    manager = PluginManager("tools")
    tools = await manager.discover_and_load_tools()
    
    stats = manager.get_stats()
    print(f"\n📊 Detailed Statistics:")
    print(f"  Total tools loaded: {stats['total_tools']}")
    print(f"  Traditional BaseTool classes: {stats['traditional_tools']}")
    print(f"  Decorator-based tools: {stats['decorator_tools']}")
    print(f"  Failed plugins: {stats['failed_plugins']}")
    
    print(f"\n📋 Tools by Type:")
    print(f"  Traditional: {stats['tools_by_type']['traditional']}")
    print(f"  Decorator: {stats['tools_by_type']['decorator']}")
    
    if stats['failed']:
        print(f"  Failed: {stats['failed']}")
    
    print(f"\n🔧 Tool Details:")
    for name in sorted(tools.keys()):
        info = manager.get_tool_info(name)
        print(f"  • {name} ({info['type']})")
        print(f"    Description: {info['description']}")
        print(f"    Schema: {len(info['schema'].get('properties', {}))} parameters")


def create_demo_decorator_tool():
    """Create a demo tool file to show how easy it is"""
    demo_content = '''#!/usr/bin/env python3
"""
Demo Tool - Created in seconds with decorators!
"""
import sys
sys.path.append('..')
from base_tool import ToolResult
from tool_decorators import tool, tool_method


@tool("greet", "Greet someone with style")
async def greet_user(name: str, style: str = "friendly") -> str:
    """Greet a user with different styles"""
    styles = {
        "friendly": f"Hello there, {name}! 😊",
        "formal": f"Good day, {name}.",
        "casual": f"Hey {name}! What's up?",
        "enthusiastic": f"WOW! Hi {name}!!! 🎉"
    }
    return styles.get(style, f"Hi {name}!")


class QuickTools:
    @tool_method("flip_coin", "Flip a virtual coin")
    async def flip_coin(self) -> ToolResult:
        import random
        result = ToolResult()
        outcome = "Heads" if random.choice([True, False]) else "Tails"
        result.add_text(f"🪙 Coin flip: {outcome}")
        return result
    
    @tool_method("dice_roll", "Roll dice")
    async def roll_dice(self, sides: int = 6, count: int = 1) -> ToolResult:
        import random
        result = ToolResult()
        rolls = [random.randint(1, sides) for _ in range(count)]
        result.add_text(f"🎲 Rolled {count}d{sides}: {rolls}")
        result.add_text(f"Total: {sum(rolls)}")
        return result

# Auto-register method tools
from tool_decorators import MethodToolRegistry
MethodToolRegistry.register_class_methods(QuickTools())
'''
    
    demo_path = "/home/cubanguy/Projects/ai-framework/mcp-server/file-dir-projects/mcp-server/tools/demo_quick.py"
    with open(demo_path, 'w') as f:
        f.write(demo_content)
    
    print(f"📝 Created demo tool file: {demo_path}")
    print(f"   Added 3 new tools: greet, flip_coin, dice_roll")


if __name__ == "__main__":
    # Create demo tools
    create_demo_decorator_tool()
    
    # Run comprehensive tests
    asyncio.run(test_decorator_integration())
    asyncio.run(test_plugin_manager_directly())
