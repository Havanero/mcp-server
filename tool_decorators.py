#!/usr/bin/env python3
"""
Tool Decorators - Enhanced decorator patterns for effortless tool creation

Provides multiple decorator patterns to make tool implementation as simple as possible:
- @tool - Turn async functions into tools
- @mcp_tool - Class decorator for tool classes  
- @tool_method - Multiple tools within one class
- Auto-registration system for zero-config tool discovery
"""
import inspect
import logging
from typing import Any, Dict, Callable, Optional, get_type_hints, Union
from functools import wraps, lru_cache
from dataclasses import dataclass

from base_tool import BaseTool, ToolResult, ToolError


# Global tool registry for decorator-based tools
_DECORATOR_TOOL_REGISTRY: Dict[str, BaseTool] = {}


def get_decorator_tools() -> Dict[str, BaseTool]:
    """Get all tools registered via decorators"""
    return _DECORATOR_TOOL_REGISTRY.copy()


class DecoratorTool(BaseTool):
    """Tool wrapper for function-based tools"""
    
    def __init__(self, func: Callable, name: str, description: str):
        self._func = func
        self._name = name
        self._description = description
        
        # Generate schema from function signature
        self._schema = self._generate_function_schema(func)
    
    @property
    def name(self) -> str:
        return self._name
    
    @property  
    def description(self) -> str:
        return self._description
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return self._schema
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the wrapped function"""
        try:
            # Call the original function
            result = await self._func(**kwargs)
            
            # Handle different return types
            if isinstance(result, ToolResult):
                return result
            elif isinstance(result, str):
                # String result -> text content
                tool_result = ToolResult()
                tool_result.add_text(result)
                return tool_result
            elif isinstance(result, dict):
                # Dict result -> JSON content
                tool_result = ToolResult()
                tool_result.add_json(result)
                return tool_result
            else:
                # Any other result -> convert to string
                tool_result = ToolResult()
                tool_result.add_text(str(result))
                return tool_result
                
        except Exception as e:
            raise ToolError(f"Function tool '{self.name}' failed: {str(e)}")
    
    def _generate_function_schema(self, func: Callable) -> Dict[str, Any]:
        """Generate schema from function signature with proper parameter extraction"""
        sig = inspect.signature(func)
        type_hints = get_type_hints(func)
        
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter for bound methods
            if param_name == "self":
                continue
                
            param_type = type_hints.get(param_name, str)
            json_type = self._python_type_to_json_type(param_type)
            
            # ONLY extract from docstring - no fallbacks or additions
            description = self._extract_param_description(func, param_name)
            if description:
                json_type["description"] = description
            # If no docstring description, leave description empty
            
            properties[param_name] = json_type
            
            # Required if no default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        schema = {
            "type": "object", 
            "properties": properties,
            "additionalProperties": False,  # MCP compliance - strict schema
            "strict": True  # Enable strict mode for better validation
        }
        
        if required:
            schema["required"] = required
            
        return schema
    
    @staticmethod
    def _python_type_to_json_type(python_type: type) -> Dict[str, Any]:
        """Convert Python type to JSON schema type with enhanced handling"""
        from typing import get_origin, get_args
        
        origin = get_origin(python_type)
        
        # Handle Optional/Union types
        if origin is Union:
            args = get_args(python_type)
            if len(args) == 2 and type(None) in args:
                non_none_type = next(arg for arg in args if arg is not type(None))
                return DecoratorTool._python_type_to_json_type(non_none_type)
        
        # Enhanced type mapping with proper dict handling
        type_mapping = {
            str: {"type": "string"},
            int: {"type": "integer"},
            float: {"type": "number"}, 
            bool: {"type": "boolean"},
            list: {"type": "array"},
            dict: {"type": "object"},  # Ensure dict maps to object
            type(None): {"type": "null"}
        }
        
        base_type = origin or python_type
        result = type_mapping.get(base_type, {"type": "string"})
        
        # Extra safety for dict types
        if python_type == dict or base_type == dict or str(python_type) == "<class 'dict'>":
            result = {"type": "object"}
        
        return result
    
    def _extract_param_description(self, func: Callable, param_name: str) -> str:
        """Extract parameter description from function docstring"""
        if not func.__doc__:
            return ""
        
        lines = func.__doc__.split('\n')
        in_args_section = False
        description_lines = []
        current_param = None
        
        for line in lines:
            line_stripped = line.strip()
            
            if line_stripped.startswith('Args:'):
                in_args_section = True
                continue
            
            if in_args_section:
                # Check if this is the start of a new parameter
                if line_stripped and ':' in line_stripped and not line_stripped.startswith(' '):
                    # If we were collecting for our target param, we're done
                    if current_param == param_name and description_lines:
                        break
                    
                    # Check if this is our target parameter
                    if line_stripped.startswith(param_name + ':'):
                        current_param = param_name
                        desc = line_stripped.split(':', 1)[1].strip()
                        if desc:
                            description_lines = [desc]
                        else:
                            description_lines = []
                    else:
                        current_param = line_stripped.split(':')[0].strip()
                        description_lines = []
                
                # If we're collecting for our parameter, add continuation lines
                elif current_param == param_name and line_stripped:
                    # Check if this is a new section (Returns:, etc.)
                    if line_stripped.endswith(':') and not line_stripped.startswith(' '):
                        break
                    description_lines.append(line_stripped)
                
                # Stop if we hit another section
                elif line_stripped and not line_stripped.startswith(' ') and line_stripped.endswith(':'):
                    break
        
        if current_param == param_name and description_lines:
            return ' '.join(description_lines)
        
        return ""
    

# 1. Function Decorator - @tool
def tool(name: str, description: str, auto_register: bool = True):
    """
    Decorator to turn async functions into MCP tools.
    
    Usage:
        @tool("weather", "Get weather for a city")
        async def get_weather(city: str, units: str = "metric") -> str:
            return f"Weather in {city}: Sunny 🌞"
    """
    def decorator(func: Callable) -> Callable:
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Tool function '{name}' must be async")
        
        # Create tool wrapper
        tool_instance = DecoratorTool(func, name, description)
        
        # Auto-register if requested
        if auto_register:
            _DECORATOR_TOOL_REGISTRY[name] = tool_instance
            logging.info(f"🔧 Auto-registered tool: {name}")
        
        # Store tool metadata on function
        func._mcp_tool = tool_instance
        func._mcp_name = name
        func._mcp_description = description
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# 2. Class Decorator - @mcp_tool  
def mcp_tool(name: str, description: str, auto_register: bool = True):
    """
    Class decorator to simplify tool class creation.
    
    Usage:
        @mcp_tool("calculator", "Basic math operations")
        class Calculator(BaseTool):  # Must inherit from BaseTool
            async def execute(self, operation: str, a: float, b: float) -> ToolResult:
                ...
    """
    def decorator(cls):
        # Add name and description as class attributes
        cls.name = name
        cls.description = description
        cls._mcp_tool_decorated = True  # Mark as decorator tool
        
        # Ensure it inherits from BaseTool
        if not issubclass(cls, BaseTool):
            raise ValueError(
                f"Class {cls.__name__} must inherit from BaseTool when using @mcp_tool decorator.\n"
                f"Change 'class {cls.__name__}:' to 'class {cls.__name__}(BaseTool):'"
            )
        
        # Auto-register if requested
        if auto_register:
            instance = cls()
            _DECORATOR_TOOL_REGISTRY[name] = instance
            logging.info(f"🔧 Auto-registered class tool: {name}")
        
        return cls
    
    return decorator


# 3. Method Decorator - @tool_method
def tool_method(name: str, description: str):
    """
    Decorator for methods within a class to create multiple tools.
    
    Usage:
        class MathTools:
            @tool_method("add", "Add two numbers")
            async def add(self, a: float, b: float) -> ToolResult:
                ...
            
            @tool_method("multiply", "Multiply two numbers") 
            async def multiply(self, a: float, b: float) -> ToolResult:
                ...
    """
    def decorator(method: Callable) -> Callable:
        if not inspect.iscoroutinefunction(method):
            raise ValueError(f"Tool method '{name}' must be async")
        
        # Store metadata on method
        method._mcp_tool_name = name
        method._mcp_tool_description = description
        
        return method
    
    return decorator


class MethodToolRegistry:
    """Registry for managing method-based tools"""
    
    @classmethod
    def register_class_methods(cls, instance_or_class, auto_register: bool = True) -> Dict[str, BaseTool]:
        """Extract and register tool methods from a class instance"""
        tools = {}
        
        # Get all methods marked with @tool_method
        for attr_name in dir(instance_or_class):
            method = getattr(instance_or_class, attr_name)
            
            if hasattr(method, '_mcp_tool_name'):
                tool_name = method._mcp_tool_name
                tool_description = method._mcp_tool_description
                
                # Create a tool wrapper for the method
                if inspect.isclass(instance_or_class):
                    # If class passed, instantiate it
                    instance = instance_or_class()
                    bound_method = getattr(instance, attr_name)
                else:
                    # Already an instance
                    bound_method = method
                
                tool_instance = DecoratorTool(bound_method, tool_name, tool_description)
                tools[tool_name] = tool_instance
                
                # Auto-register
                if auto_register:
                    _DECORATOR_TOOL_REGISTRY[tool_name] = tool_instance
                    logging.info(f"🔧 Auto-registered method tool: {tool_name}")
        
        return tools


# 4. Auto-registration function  
def register_tools_from_module(module_or_globals: Union[Any, dict], auto_register: bool = True):
    """
    Scan a module or globals() for decorated functions and register them.
    
    Usage:
        # At end of your tool module:
        register_tools_from_module(globals())
    """
    if isinstance(module_or_globals, dict):
        namespace = module_or_globals
    else:
        namespace = vars(module_or_globals)
    
    registered = 0
    
    for name, obj in namespace.items():
        # Check for function tools
        if hasattr(obj, '_mcp_tool') and auto_register:
            tool = obj._mcp_tool
            if tool.name not in _DECORATOR_TOOL_REGISTRY:
                _DECORATOR_TOOL_REGISTRY[tool.name] = tool
                registered += 1
        
        # Check for class tools with method tools
        if inspect.isclass(obj):
            method_tools = MethodToolRegistry.register_class_methods(obj, auto_register)
            registered += len(method_tools)
    
    if registered > 0:
        logging.info(f"🔧 Auto-registered {registered} tools from module")


# Utility functions
def list_decorator_tools() -> Dict[str, str]:
    """List all tools registered via decorators"""
    return {name: tool.description for name, tool in _DECORATOR_TOOL_REGISTRY.items()}


def clear_decorator_registry():
    """Clear the decorator tool registry (useful for testing and development)"""
    global _DECORATOR_TOOL_REGISTRY
    _DECORATOR_TOOL_REGISTRY.clear()
    logging.info("🔄 Cleared decorator tool registry")


# Example usage patterns
if __name__ == "__main__":
    # Example 1: Function-based tool
    @tool("greet", "Greet someone with a message")
    async def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}! 👋"
    
    # Example 2: Class-based tool
    @mcp_tool("math", "Basic math operations")
    class MathTool(BaseTool):
        async def execute(self, operation: str, a: float, b: float) -> ToolResult:
            operations = {
                "add": lambda x, y: x + y,
                "subtract": lambda x, y: x - y,
                "multiply": lambda x, y: x * y,
                "divide": lambda x, y: x / y if y != 0 else float('inf')
            }
            
            result = operations.get(operation, lambda x, y: 0)(a, b)
            
            tool_result = ToolResult()
            tool_result.add_text(f"{a} {operation} {b} = {result}")
            return tool_result
    
    # Example 3: Method-based tools
    class UtilityTools:
        @tool_method("reverse", "Reverse a string")
        async def reverse_string(self, text: str) -> ToolResult:
            result = ToolResult()
            result.add_text(text[::-1])
            return result
        
        @tool_method("count_words", "Count words in text")
        async def count_words(self, text: str) -> ToolResult:
            word_count = len(text.split())
            result = ToolResult()
            result.add_text(f"Word count: {word_count}")
            return result
    
    # Register method tools
    MethodToolRegistry.register_class_methods(UtilityTools())
    
    print("📋 Registered tools:")
    for name, description in list_decorator_tools().items():
        print(f"  • {name}: {description}")
