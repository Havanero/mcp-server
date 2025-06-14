# 🚀 Advanced MCP Server - Multi-Transport Plugin System

A sophisticated **Model Context Protocol (MCP)** server with multiple transport layers, dynamic plugin discovery, and decorator-based tool creation.

## ✨ Features

- 🔧 **3 Transport Options**: Stdio, WebSocket, HTTP
- 🎯 **Decorator Tools**: `@tool`, `@mcp_tool`, `@tool_method` 
- 📦 **Auto Plugin Discovery**: Drop files in `tools/`, they work
- ⚡ **Type-Driven Schemas**: JSON schemas from Python type hints
- 🌐 **Multi-Client Support**: WebSocket & HTTP support multiple clients
- 📋 **Built-in Web UI**: Test tools from your browser
- 🛡️ **Error Isolation**: Plugin failures don't crash server

## 🎯 Quick Start

### 1. Check Setup
```bash
cd /home/cubanguy/Projects/ai-framework/mcp-server/file-dir-projects/mcp-server
python3 check_setup.py
```

### 2. Install Dependencies (if needed)
```bash
pip install -r requirements.txt
```

### 3. Choose Your Transport

#### 📡 Stdio (Development)
```bash
python3 server_v2.py
python3 ../mcp-client/cli.py python3 server_v2.py
```

#### 🌐 WebSocket (Production)
```bash
python3 server_websocket.py
python3 websocket_client.py
```

#### 🔗 HTTP (REST API)
```bash
python3 server_http.py
# Then visit: http://localhost:8080/client
```

## 🔧 Creating Tools

### Function Tool (Simplest)
```python
# tools/my_tools.py
from tool_decorators import tool

@tool("greet", "Greet someone with style")
async def greet(name: str, style: str = "friendly") -> str:
    return f"Hello {name}! 😊" if style == "friendly" else f"Greetings, {name}."
```

### Class Tool (Complex Logic)
```python
from tool_decorators import mcp_tool

@mcp_tool("calculator", "Advanced calculations")
class Calculator:
    async def execute(self, operation: str, a: float, b: float) -> ToolResult:
        result = ToolResult()
        if operation == "add":
            result.add_text(f"{a} + {b} = {a + b}")
        return result
```

### Method Tools (Multiple Tools)
```python
from tool_decorators import tool_method, MethodToolRegistry

class MathTools:
    @tool_method("fibonacci", "Calculate Fibonacci number")
    async def fib(self, n: int) -> ToolResult:
        # Implementation...
        
    @tool_method("prime_check", "Check if number is prime")
    async def is_prime(self, number: int) -> ToolResult:
        # Implementation...

# Auto-register
MethodToolRegistry.register_class_methods(MathTools())
```

**That's it!** Tools appear automatically, no configuration needed.

## 📊 Current Tools

Your server includes these example tools:

### Traditional Tools
- **`file_ops`** - Safe file operations (read/write/list)
- **`system_info`** - System metrics (disk/memory/CPU)

### Decorator Tools  
- **`opensearch`** - Search regulations documents
- **`db_health`** - Database connection health
- **`current_time`** - Get current timestamp
- **`greet`** - Greet with different styles
- **`fibonacci`** - Calculate Fibonacci numbers
- **`flip_coin`** - Virtual coin flip
- **`word_stats`** - Analyze text statistics

## 🌐 Transport Comparison

| Feature | Stdio | WebSocket | HTTP |
|---------|-------|-----------|------|
| **Clients** | Single | Multiple | Multiple |
| **Real-time** | ✅ | ✅ | ❌ |
| **Web Browsers** | ❌ | ✅ | ✅ |
| **REST API** | ❌ | ❌ | ✅ |
| **Setup** | Simple | Medium | Simple |
| **Best For** | Development | Production | Integrations |

## 🧪 Test Examples

### Stdio
```bash
mcp> list
mcp> call greet {"name": "Developer", "style": "enthusiastic"}
mcp> call fibonacci {"n": 10}
mcp> call opensearch {"query": "GDPR compliance"}
```

### WebSocket
```bash
python3 websocket_client.py
# Interactive WebSocket client with real-time communication
```

### HTTP REST
```bash
# List tools
curl http://localhost:8080/tools

# Call tool
curl -X POST http://localhost:8080/tools/greet \
     -H "Content-Type: application/json" \
     -d '{"name": "API User", "style": "formal"}'

# Web interface
open http://localhost:8080/client
```

## 📚 Documentation

- **[TRANSPORTS.md](TRANSPORTS.md)** - Complete transport guide
- **[DECORATORS.md](DECORATORS.md)** - Tool decorator patterns
- **[README_plugins.md](README_plugins.md)** - Plugin system details

## 🎉 What Makes This Special

### 1. **Zero Configuration Tools**
Drop a Python file in `tools/` → tool appears automatically

### 2. **Multiple Decorator Patterns**
Choose the right pattern for your use case:
- `@tool` for simple functions
- `@mcp_tool` for complex classes
- `@tool_method` for multiple related tools

### 3. **Transport Flexibility**
Same tools work across all transports - choose based on your needs

### 4. **Type Safety**
JSON schemas auto-generated from Python type hints

### 5. **Production Ready**
- Multi-client support
- Error isolation
- Real-time communication
- Web browser compatibility

## 🚀 Next Steps

1. **Test the system**: `python3 test_transports.py`
2. **Add your tools**: Create files in `tools/` directory
3. **Choose transport**: Stdio for dev, WebSocket for prod, HTTP for APIs
4. **Integrate with LLM**: Ready for intelligent agent integration

## 🔧 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Server Core                      │
├─────────────────────────────────────────────────────────┤
│                  Plugin Manager                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │ Traditional │ │  @tool      │ │  @tool_method   │   │
│  │ BaseTool    │ │ Functions   │ │  Classes        │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                Transport Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │   Stdio     │ │ WebSocket   │ │      HTTP       │   │
│  │ (Dev/CLI)   │ │ (Production)│ │   (REST API)    │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

This gives you a **complete, production-ready MCP server** with the flexibility to grow from simple CLI tools to sophisticated web applications! 🎉
