# MCP Server with Plugin System

## Architecture

```
mcp-server/
├── server_v2.py          # Enhanced server with plugin system
├── plugin_manager.py     # Auto-discovery and loading
├── base_tool.py          # Tool foundation with type-driven schemas  
├── transport.py          # Stdio transport (unchanged)
└── tools/                # Plugin directory
    ├── file_operations.py # File I/O operations
    └── system_info.py     # System metrics
```

## Key Features

### 🔌 Auto-Discovery
- Drop `.py` files in `tools/` directory
- Server automatically loads all `BaseTool` subclasses
- Zero configuration needed

### 🏗️ Type-Driven Schemas
```python
class MyTool(BaseTool):
    name = "my_tool"
    description = "Example tool"
    
    async def execute(self, text: str, count: int = 1) -> ToolResult:
        # Schema auto-generated from type hints!
        result = ToolResult()
        result.add_text(f"Got: {text} x{count}")
        return result
```

### ⚡ Async-First Design
- All tools use `async def execute()`
- Non-blocking I/O with `asyncio`
- Proper error isolation

### 🛡️ Error Handling
- Plugin failures don't crash server
- Proper MCP error codes
- Security validation (file paths, etc.)

## Quick Start

### 1. Test the Plugin System
```bash
# Test with client
python3 test_plugins.py

# Or use CLI
python3 ../mcp-client/cli.py python3 server_v2.py
```

### 2. Add a New Tool

Create `tools/my_tool.py`:
```python
from base_tool import BaseTool, ToolResult

class WeatherTool(BaseTool):
    name = "weather"
    description = "Get weather for a location"
    
    async def execute(self, location: str) -> ToolResult:
        # Your implementation here
        result = ToolResult()
        result.add_text(f"Weather in {location}: Sunny ☀️")
        return result
```

**That's it!** The server will auto-discover and load it.

## Available Tools

### 📄 file_ops
- **Operations**: read, write, list
- **Security**: Sandboxed to workspace directory
- **Usage**: `call file_ops {"operation": "write", "path": "test.txt", "content": "Hello!"}`

### 🖥️ system_info  
- **Info Types**: overview, disk, memory, cpu, processes
- **Cross-platform**: Works on Linux, macOS, Windows
- **Usage**: `call system_info {"info_type": "overview"}`

## CLI Examples

```bash
mcp> list
🔧 Available Tools (2):
  1. file_ops - Read, write, and list files with security validation
  2. system_info - Get system information, disk usage, memory, and process details

mcp> call file_ops {"operation": "write", "path": "hello.txt", "content": "Hello World!"}
⚡ Calling file_ops...
✅ Result:
  📄 ✅ File written: hello.txt

mcp> call system_info {"info_type": "disk"}
⚡ Calling system_info...
✅ Result:
  📄 💾 Disk Usage: .
  📄 📊 Total: 500.00 GB
  📄 📈 Used: 250.00 GB (50.0%)
```

## Next Steps

Ready to add:
- **LLM Integration** - Intelligent agent that uses these tools
- **More Tools** - Database, web scraping, API calls
- **Remote Transport** - TCP/HTTP instead of just stdio
