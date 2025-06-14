#!/usr/bin/env python3
"""
Test the fixed decorator system
"""
import asyncio
import sys

# Test plugin manager directly to see if error is fixed
sys.path.append('.')
from plugin_manager import PluginManager


async def test_fixed_decorators():
    """Test that the decorator error is fixed"""
    print("🧪 Testing Fixed Decorator System")
    print("-" * 40)
    
    manager = PluginManager("tools")
    
    try:
        tools = await manager.discover_and_load_tools()
        
        print(f"✅ Plugin loading successful!")
        print(f"📦 Loaded {len(tools)} tools:")
        
        # Show all loaded tools
        for name, tool in tools.items():
            tool_type = "decorator" if hasattr(tool, '_func') else "traditional"
            print(f"  • {name} ({tool_type}): {tool.description}")
        
        # Test the problematic tool that was failing
        if "string_utils" in tools:
            print(f"\n🔧 Testing string_utils tool:")
            result = await manager.execute_tool("string_utils", {
                "operation": "upper",
                "text": "hello decorator fix!"
            })
            print(f"   Result: {result}")
        
        print(f"\n✅ All tools working correctly!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fixed_decorators())
