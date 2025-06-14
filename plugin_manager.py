#!/usr/bin/env python3
"""
Plugin Manager - Dynamic tool discovery and loading system

Automatically discovers and loads MCP tools from the tools/ directory.
Provides error isolation and hot-reloading capabilities.
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


class PluginManager:
    """
    Manages dynamic loading and discovery of MCP tool plugins.
    
    Features:
    - Auto-discovery from tools/ directory
    - Error isolation (failed plugins don't crash server)  
    - Plugin validation and metadata extraction
    - Hot-reloading support (future enhancement)
    """
    
    def __init__(self, tools_directory: str = "tools"):
        self.tools_directory = Path(tools_directory)
        self.loaded_tools: Dict[str, BaseTool] = {}
        self.failed_plugins: List[str] = []
        
    async def discover_and_load_tools(self) -> Dict[str, BaseTool]:
        """
        Discover and load all valid tool plugins.
        
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
        
        python_files = list(self.tools_directory.glob("*.py"))
        python_files = [f for f in python_files if f.name != "__init__.py"]
        
        logging.info(f"📦 Found {len(python_files)} potential plugin files")
        
        for plugin_file in python_files:
            try:
                await self._load_plugin_file(plugin_file)
            except Exception as e:
                logging.error(f"❌ Failed to load plugin {plugin_file.name}: {e}")
                self.failed_plugins.append(plugin_file.name)
        
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
            
            # Find all BaseTool subclasses in the module
            tool_classes = self._find_tool_classes(module)
            
            # Instantiate and register tools
            for tool_class in tool_classes:
                tool_instance = tool_class()
                
                # Validate tool
                self._validate_tool(tool_instance)
                
                # Register tool
                self.loaded_tools[tool_instance.name] = tool_instance
                logging.info(f"  ✓ Loaded tool: {tool_instance.name}")
                
        except Exception as e:
            logging.error(f"  ❌ Error loading {plugin_file.name}: {e}")
            raise
    
    def _find_tool_classes(self, module: Any) -> List[Type[BaseTool]]:
        """Find all BaseTool subclasses in a module"""
        tool_classes = []
        
        for name in dir(module):
            obj = getattr(module, name)
            
            # Check if it's a class that inherits from BaseTool
            if (isinstance(obj, type) and 
                issubclass(obj, BaseTool) and 
                obj is not BaseTool):
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
            logging.info(f"⚡ Executing tool: {tool_name}")
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
        return {
            "name": tool.name,
            "description": tool.description,
            "schema": tool.input_schema,
            "class": tool.__class__.__name__,
            "module": tool.__class__.__module__
        }


# Testing and validation
async def test_plugin_manager():
    """Test plugin manager with debug output"""
    manager = PluginManager()
    tools = await manager.discover_and_load_tools()
    
    print(f"🔧 Discovered tools: {list(tools.keys())}")
    
    for name, tool in tools.items():
        print(f"\n📋 Tool: {name}")
        print(f"   Description: {tool.description}")
        print(f"   Schema: {tool.input_schema}")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_plugin_manager())
