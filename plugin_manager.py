#!/usr/bin/env python3
"""
Enhanced Plugin Manager - Supports both traditional and decorator-based tools

Automatically discovers and loads MCP tools from multiple sources:
- Traditional BaseTool subclasses  
- @tool function decorators
- @mcp_tool class decorators
- @tool_method method decorators
"""
import os
import sys
import importlib
import importlib.util
import logging
from typing import Dict, List, Type, Any
from pathlib import Path
from functools import lru_cache

from base_tool import BaseTool, ToolError
from tool_decorators import get_decorator_tools, register_tools_from_module


class PluginManager:
    """
    Enhanced plugin manager supporting multiple tool creation patterns.
    
    Features:
    - Traditional BaseTool subclass discovery
    - Decorator-based tool auto-registration
    - Error isolation and validation
    - Hot-reloading support (future)
    - Unified tool registry
    """
    
    def __init__(self, tools_directory: str = "tools"):
        self.tools_directory = Path(tools_directory)
        self.loaded_tools: Dict[str, BaseTool] = {}
        self.failed_plugins: List[str] = []
        
    async def discover_and_load_tools(self) -> Dict[str, BaseTool]:
        """
        Discover and load all tools from multiple sources.
        
        Sources:
        1. Traditional BaseTool subclasses in plugin files
        2. @tool decorated functions
        3. @mcp_tool decorated classes  
        4. @tool_method decorated methods
        
        Returns:
            Dictionary mapping tool names to tool instances
        """
        logging.info(f"🔍 Discovering tools in {self.tools_directory}")
        
        if not self.tools_directory.exists():
            logging.warning(f"Tools directory {self.tools_directory} not found")
            return {}
        
        # Ensure tools directory is in Python path
        tools_path = str(self.tools_directory.absolute())
        if tools_path not in sys.path:
            sys.path.insert(0, str(self.tools_directory.parent))
        
        # Clear decorator registry to start fresh
        from tool_decorators import clear_decorator_registry
        clear_decorator_registry()
        
        # Load all Python files in tools directory
        python_files = list(self.tools_directory.glob("*.py"))
        python_files = [f for f in python_files if f.name != "__init__.py"]
        
        logging.info(f"📦 Found {len(python_files)} potential plugin files")
        
        # Load each plugin file
        for plugin_file in python_files:
            try:
                await self._load_plugin_file(plugin_file)
            except Exception as e:
                logging.error(f"❌ Failed to load plugin {plugin_file.name}: {e}")
                self.failed_plugins.append(plugin_file.name)
        
        # Add decorator-based tools to our registry
        await self._load_decorator_tools()
        
        logging.info(f"✅ Successfully loaded {len(self.loaded_tools)} tools")
        if self.failed_plugins:
            logging.warning(f"⚠️  Failed to load {len(self.failed_plugins)} plugins: {self.failed_plugins}")
        
        return self.loaded_tools
    
    async def _load_plugin_file(self, plugin_file: Path) -> None:
        """Load tools from a single plugin file"""
        module_name = f"tools.{plugin_file.stem}"
        
        try:
            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            if not spec or not spec.loader:
                raise ImportError(f"Could not load spec for {plugin_file}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Auto-register any decorator tools found in this module
            register_tools_from_module(module, auto_register=True)
            
            # Find traditional BaseTool subclasses in the module
            tool_classes = self._find_tool_classes(module)
            
            # Instantiate and register traditional tools
            for tool_class in tool_classes:
                tool_instance = tool_class()
                
                # Validate tool
                self._validate_tool(tool_instance)
                
                # Register tool (check for conflicts)
                if tool_instance.name in self.loaded_tools:
                    logging.warning(f"⚠️  Tool name conflict: {tool_instance.name} (skipping duplicate)")
                    continue
                
                self.loaded_tools[tool_instance.name] = tool_instance
                logging.info(f"  ✓ Loaded traditional tool: {tool_instance.name}")
                
        except Exception as e:
            logging.error(f"  ❌ Error loading {plugin_file.name}: {e}")
            raise
    
    async def _load_decorator_tools(self) -> None:
        """Load tools from decorator registry"""
        decorator_tools = get_decorator_tools()
        
        for name, tool in decorator_tools.items():
            # Validate decorator tool
            try:
                self._validate_tool(tool)
                
                # Check for conflicts with traditional tools
                if name in self.loaded_tools:
                    logging.warning(f"⚠️  Tool name conflict: {name} (decorator vs traditional)")
                    continue
                
                self.loaded_tools[name] = tool
                logging.info(f"  ✓ Loaded decorator tool: {name}")
                
            except Exception as e:
                logging.error(f"  ❌ Invalid decorator tool {name}: {e}")
                self.failed_plugins.append(f"decorator:{name}")
    
    def _find_tool_classes(self, module: Any) -> List[Type[BaseTool]]:
        """Find all BaseTool subclasses in a module"""
        tool_classes = []
        
        for name in dir(module):
            obj = getattr(module, name)
            
            # Check if it's a class that inherits from BaseTool
            if (isinstance(obj, type) and 
                issubclass(obj, BaseTool) and 
                obj is not BaseTool):
                
                # Skip classes that were created by @mcp_tool decorator
                # (they'll be handled by decorator registry)
                if not hasattr(obj, '_decorator_created'):
                    tool_classes.append(obj)
        
        return tool_classes
    
    def _validate_tool(self, tool: BaseTool) -> None:
        """Validate that a tool is properly configured"""
        if not tool.name:
            raise ValueError(f"Tool {tool.__class__.__name__} missing name attribute")
        
        if not tool.description:
            raise ValueError(f"Tool {tool.name} missing description attribute")
        
        # Validate that execute method exists and is async
        if not hasattr(tool, 'execute'):
            raise ValueError(f"Tool {tool.name} missing execute method")
        
        import asyncio
        if not asyncio.iscoroutinefunction(tool.execute):
            raise ValueError(f"Tool {tool.name} execute method must be async")
        
        # Validate schema generation doesn't crash
        try:
            schema = tool.input_schema
            if not isinstance(schema, dict):
                raise ValueError(f"Tool {tool.name} schema must be a dictionary")
        except Exception as e:
            raise ValueError(f"Tool {tool.name} schema generation failed: {e}")
    
    @lru_cache(maxsize=1)
    def get_tool_registry(self) -> Dict[str, Dict[str, Any]]:
        """Get tool registry for MCP tools/list response"""
        return {
            name: {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for name, tool in self.loaded_tools.items()
        }
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with given arguments"""
        if tool_name not in self.loaded_tools:
            raise ToolError(f"Tool not found: {tool_name}", code=-32601)
        
        tool = self.loaded_tools[tool_name]
        
        try:
            logging.info(f"⚡ Executing tool: {tool_name} (type: {type(tool).__name__})")
            result = await tool.execute(**arguments)
            
            if not hasattr(result, 'to_dict'):
                raise ToolError(f"Tool {tool_name} returned invalid result type")
                
            return result.to_dict()
            
        except TypeError as e:
            # Handle argument validation errors
            raise ToolError(f"Invalid arguments for {tool_name}: {e}", code=-32602)
        except Exception as e:
            logging.error(f"❌ Tool execution failed: {e}")
            raise ToolError(f"Tool execution error: {str(e)}", code=-32603)
    
    def list_tools(self) -> List[str]:
        """Get list of loaded tool names"""
        return list(self.loaded_tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed info about a specific tool"""
        if tool_name not in self.loaded_tools:
            return {}
        
        tool = self.loaded_tools[tool_name]
        tool_type = "decorator" if hasattr(tool, '_func') else "traditional"
        
        return {
            "name": tool.name,
            "description": tool.description,
            "schema": tool.input_schema,
            "class": tool.__class__.__name__,
            "module": tool.__class__.__module__,
            "type": tool_type
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detailed plugin manager statistics"""
        traditional_tools = [name for name, tool in self.loaded_tools.items() 
                           if not hasattr(tool, '_func')]
        decorator_tools = [name for name, tool in self.loaded_tools.items() 
                         if hasattr(tool, '_func')]
        
        return {
            "total_tools": len(self.loaded_tools),
            "traditional_tools": len(traditional_tools),
            "decorator_tools": len(decorator_tools),
            "failed_plugins": len(self.failed_plugins),
            "tools_by_type": {
                "traditional": traditional_tools,
                "decorator": decorator_tools
            },
            "failed": self.failed_plugins
        }


# Enhanced testing
async def test_enhanced_plugin_manager():
    """Test the enhanced plugin manager"""
    manager = PluginManager()
    tools = await manager.discover_and_load_tools()
    
    print(f"🔧 Discovered tools: {list(tools.keys())}")
    
    # Show statistics
    stats = manager.get_stats()
    print(f"\n📊 Plugin Manager Stats:")
    print(f"  Total tools: {stats['total_tools']}")
    print(f"  Traditional tools: {stats['traditional_tools']}")
    print(f"  Decorator tools: {stats['decorator_tools']}")
    print(f"  Failed plugins: {stats['failed_plugins']}")
    
    # Show tool details
    print(f"\n📋 Tool Details:")
    for name, tool in tools.items():
        info = manager.get_tool_info(name)
        print(f"  • {name} ({info['type']}): {tool.description}")
    
    # Test a few tools
    print(f"\n⚡ Testing tools:")
    
    try:
        if "current_time" in tools:
            result = await manager.execute_tool("current_time", {"format": "readable"})
            print(f"  current_time: {result}")
        
        if "fibonacci" in tools:
            result = await manager.execute_tool("fibonacci", {"n": 8})
            print(f"  fibonacci: {result}")
            
        if "file_ops" in tools:
            result = await manager.execute_tool("file_ops", {
                "operation": "write", 
                "path": "test_decorator.txt", 
                "content": "Decorator tools work!"
            })
            print(f"  file_ops: {result}")
            
    except Exception as e:
        print(f"  Error testing tools: {e}")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_enhanced_plugin_manager())
