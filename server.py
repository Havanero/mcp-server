#!/usr/bin/env python3
"""
MCP Server - Protocol Router

Handles MCP protocol methods: initialize, tools/list, tools/call
Provides plugin-based tool registration and execution framework.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from functools import lru_cache
from abc import ABC, abstractmethod

from transport import StdioServerTransport, MCPRequest, MCPResponse


@dataclass
class ToolDefinition:
    """Tool metadata and execution handler"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]


class MCPTool(ABC):
    """Abstract base for MCP tool plugins"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass
    
    @property
    @abstractmethod 
    def description(self) -> str:
        """Tool description"""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON schema for tool input"""
        pass
    
    @abstractmethod
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments"""
        pass


class MCPServer:
    """Main MCP server with protocol handling and tool management"""
    
    def __init__(self, name: str = "mcp-python-server", version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.tools: Dict[str, ToolDefinition] = {}
        self.transport = StdioServerTransport()
        self.initialized = False
        
        # Set up transport handler
        self.transport.set_request_handler(self._handle_request)
    
    def register_tool(self, tool: MCPTool) -> None:
        """Register a tool plugin"""
        definition = ToolDefinition(
            name=tool.name,
            description=tool.description,
            input_schema=tool.input_schema,
            handler=tool.execute
        )
        self.tools[tool.name] = definition
        logging.info(f"Registered tool: {tool.name}")
    
    def register_function_tool(
        self, 
        name: str, 
        description: str, 
        input_schema: Dict[str, Any],
        handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> None:
        """Register a function-based tool (simpler than class-based)"""
        definition = ToolDefinition(name, description, input_schema, handler)
        self.tools[name] = definition
        logging.info(f"Registered function tool: {name}")
    
    async def start(self) -> None:
        """Start the MCP server"""
        logging.info(f"Starting MCP server: {self.name} v{self.version}")
        logging.info(f"Registered tools: {list(self.tools.keys())}")
        await self.transport.start()
    
    async def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """Route MCP requests to appropriate handlers"""
        try:
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "initialized":
                return await self._handle_initialized(request)
            elif request.method == "tools/list":
                return await self._handle_tools_list(request)
            elif request.method == "tools/call":
                return await self._handle_tools_call(request)
            else:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Method not found: {request.method}"}
                )
        except Exception as e:
            logging.error(f"Error handling {request.method}: {e}")
            return MCPResponse(
                id=request.id,
                error={"code": -32603, "message": f"Internal error: {str(e)}"}
            )
    
    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP initialize request"""
        logging.info("Client initializing...")
        
        # Validate protocol version
        client_version = request.params.get("protocolVersion")
        if not client_version:
            return MCPResponse(
                id=request.id,
                error={"code": -32602, "message": "Missing protocolVersion"}
            )
        
        # Return server capabilities
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}  # We support tools
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }
        
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_initialized(self, request: MCPRequest) -> MCPResponse:
        """Handle initialized notification"""
        self.initialized = True
        logging.info("Client initialization complete")
        # Initialized is a notification, no response needed
        return MCPResponse(id=None)  # Will be ignored by transport
    
    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/list request"""
        if not self.initialized:
            return MCPResponse(
                id=request.id,
                error={"code": -32002, "message": "Server not initialized"}
            )
        
        tools_list = [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self.tools.values()
        ]
        
        result = {"tools": tools_list}
        logging.debug(f"Returning {len(tools_list)} tools")
        
        return MCPResponse(id=request.id, result=result)
    
    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle tools/call request"""
        if not self.initialized:
            return MCPResponse(
                id=request.id,
                error={"code": -32002, "message": "Server not initialized"}
            )
        
        tool_name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        
        if not tool_name:
            return MCPResponse(
                id=request.id,
                error={"code": -32602, "message": "Missing tool name"}
            )
        
        tool = self.tools.get(tool_name)
        if not tool:
            return MCPResponse(
                id=request.id,
                error={"code": -32601, "message": f"Tool not found: {tool_name}"}
            )
        
        try:
            logging.info(f"Executing tool: {tool_name}")
            result = await tool.handler(arguments)
            return MCPResponse(id=request.id, result=result)
            
        except Exception as e:
            logging.error(f"Tool execution failed: {e}")
            return MCPResponse(
                id=request.id,
                error={"code": -32603, "message": f"Tool execution error: {str(e)}"}
            )


# Example tool implementations
class EchoTool(MCPTool):
    """Simple echo tool for testing"""
    
    @property
    def name(self) -> str:
        return "echo"
    
    @property
    def description(self) -> str:
        return "Echo back the input text"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text to echo back"
                }
            },
            "required": ["text"]
        }
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        text = args.get("text", "")
        return {
            "content": [{
                "type": "text",
                "text": f"Echo: {text}"
            }]
        }


class MathTool(MCPTool):
    """Math operations tool"""
    
    @property
    def name(self) -> str:
        return "calculate"
    
    @property
    def description(self) -> str:
        return "Perform basic math operations"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "Math operation to perform"
                },
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["operation", "a", "b"]
        }
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        operation = args["operation"]
        a = args["a"]
        b = args["b"]
        
        operations = {
            "add": lambda x, y: x + y,
            "subtract": lambda x, y: x - y,
            "multiply": lambda x, y: x * y,
            "divide": lambda x, y: x / y if y != 0 else float("inf")
        }
        
        result = operations[operation](a, b)
        
        return {
            "content": [{
                "type": "text",
                "text": f"{a} {operation} {b} = {result}"
            }]
        }


# Test server with sample tools
async def test_server():
    """Test the MCP server with sample tools"""
    server = MCPServer("test-server", "1.0.0")
    
    # Register tools
    server.register_tool(EchoTool())
    server.register_tool(MathTool())
    
    # Register a simple function-based tool
    async def time_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        import datetime
        now = datetime.datetime.now().isoformat()
        return {
            "content": [{
                "type": "text",
                "text": f"Current time: {now}"
            }]
        }
    
    server.register_function_tool(
        name="current_time",
        description="Get current system time",
        input_schema={"type": "object", "properties": {}},
        handler=time_tool
    )
    
    # Start server
    await server.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_server())
