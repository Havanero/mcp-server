#!/usr/bin/env python3
"""
Base Tool - Enhanced plugin foundation with type-driven schema generation

Provides abstract base class and utilities for creating MCP tools with minimal boilerplate.
Uses type hints to automatically generate JSON schemas.
"""
import inspect
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Union, get_args, get_origin, get_type_hints


@dataclass
class ToolResult:
    """Standardized tool execution result"""

    content: list[Dict[str, Any]] = field(default_factory=list)

    def add_text(self, text: str) -> "ToolResult":
        """Add text content"""
        self.content.append({"type": "text", "text": text})
        return self

    def add_image(self, data: str, mime_type: str = "image/png") -> "ToolResult":
        """Add image content"""
        self.content.append({"type": "image", "data": data, "mimeType": mime_type})
        return self

    def add_json(self, data: Any) -> "ToolResult":
        """Add structured JSON data"""
        import json

        self.content.append({"type": "text", "text": json.dumps(data, indent=2)})
        return self

    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP response format"""
        return {"content": self.content}


class BaseTool(ABC):
    """
    Enhanced base class for MCP tools with automatic schema generation.

    Tools only need to:
    1. Implement execute() method with typed parameters
    2. Set name and description class attributes
    3. Return ToolResult
    """

    # Override these in subclasses
    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with typed parameters"""
        pass

    @property
    @lru_cache(maxsize=1)
    def input_schema(self) -> Dict[str, Any]:
        """Auto-generate JSON schema from execute() type hints"""
        return self._generate_schema()

    def _generate_schema(self) -> Dict[str, Any]:
        """Generate JSON schema from execute method signature"""
        sig = inspect.signature(self.execute)
        type_hints = get_type_hints(self.execute)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = type_hints.get(param_name, str)
            json_type = self._python_type_to_json_type(param_type)

            properties[param_name] = json_type

            # Required if no default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        schema = {"type": "object", "properties": properties}

        if required:
            schema["required"] = required

        return schema

    @staticmethod
    def _python_type_to_json_type(python_type: type) -> Dict[str, Any]:
        """Convert Python type hints to JSON schema types"""
        origin = get_origin(python_type)

        # Handle Optional/Union types
        if origin is Union:
            args = get_args(python_type)
            if len(args) == 2 and type(None) in args:
                # Optional[T] case
                non_none_type = next(arg for arg in args if arg is not type(None))
                base_schema = BaseTool._python_type_to_json_type(non_none_type)
                base_schema["nullable"] = True
                return base_schema

        # Handle basic types
        type_mapping = {
            str: {"type": "string"},
            int: {"type": "integer"},
            float: {"type": "number"},
            bool: {"type": "boolean"},
            list: {"type": "array"},
            dict: {"type": "object"},
        }

        base_type = origin or python_type
        return type_mapping.get(base_type, {"type": "string"})

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"


class ToolError(Exception):
    """Custom exception for tool execution errors"""

    def __init__(self, message: str, code: int = -32603):
        self.message = message
        self.code = code
        super().__init__(message)


# Utility decorators for common patterns
def tool_method(name: str, description: str):
    """Decorator to mark async functions as tools"""

    def decorator(func):
        func._tool_name = name
        func._tool_description = description
        return func

    return decorator


# Example usage patterns (for documentation)
if __name__ == "__main__":
    # This shows how clean the new API is:

    class ExampleTool(BaseTool):
        name = "example"
        description = "Example tool with automatic schema generation"

        async def execute(
            self, text: str, count: int = 1, optional_flag: bool = False
        ) -> ToolResult:
            result = ToolResult()
            for i in range(count):
                result.add_text(f"{i+1}: {text}")

            if optional_flag:
                result.add_text("Optional flag was set!")

            return result

    # Print generated schema
    tool = ExampleTool()
    print(f"Tool: {tool.name}")
    print(f"Schema: {tool.input_schema}")
