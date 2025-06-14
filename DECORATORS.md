# Tool Decorators - Effortless MCP Tool Creation

## 🎯 Three Ways to Create Tools

### 1. Function Decorator - `@tool`
**Perfect for simple, stateless operations**

```python
from tool_decorators import tool

@tool("weather", "Get weather for a city")
async def get_weather(city: str, units: str = "metric") -> str:
    return f"Weather in {city}: Sunny 🌞 ({units})"

@tool("calculate", "Basic math operations")  
async def calculate(operation: str, a: float, b: float) -> ToolResult:
    result = ToolResult()
    if operation == "add":
        result.add_text(f"{a} + {b} = {a + b}")
    return result
```

**Benefits:**
- ✅ Zero boilerplate 
- ✅ Auto-schema from type hints
- ✅ Return `str`, `dict`, or `ToolResult`
- ✅ Auto-registration

### 2. Class Decorator - `@mcp_tool`
**For tools with complex logic or state**

```python
from tool_decorators import mcp_tool

@mcp_tool("string_utils", "String manipulation tools")
class StringUtils:
    async def execute(self, operation: str, text: str, **kwargs) -> ToolResult:
        result = ToolResult()
        if operation == "reverse":
            result.add_text(text[::-1])
        elif operation == "count":
            target = kwargs.get("target", " ")
            result.add_text(f"'{target}' appears {text.count(target)} times")
        return result
```

**Benefits:**
- ✅ Class-based organization
- ✅ Shared state and methods
- ✅ Complex parameter handling
- ✅ Auto-registration

### 3. Method Decorator - `@tool_method`
**Multiple related tools in one class**

```python
from tool_decorators import tool_method, MethodToolRegistry

class MathTools:
    @tool_method("add", "Add numbers")
    async def add(self, a: float, b: float) -> ToolResult:
        result = ToolResult()
        result.add_text(f"{a} + {b} = {a + b}")
        return result
    
    @tool_method("fibonacci", "Calculate Fibonacci number")
    async def fibonacci(self, n: int) -> ToolResult:
        # Implementation here...
        return result

# Register all methods as separate tools
MethodToolRegistry.register_class_methods(MathTools())
```

**Benefits:**
- ✅ Logical grouping
- ✅ Each method becomes a separate tool
- ✅ Shared utilities and state
- ✅ Clean organization

## 🚀 Usage Patterns

### Drop-in Tool Creation
1. Create file in `tools/` directory
2. Add decorated functions/classes  
3. Server auto-discovers everything!

```python
# tools/my_awesome_tools.py
from tool_decorators import tool

@tool("joke", "Tell a random joke")
async def tell_joke(category: str = "general") -> str:
    jokes = {"general": "Why don't scientists trust atoms? Because they make up everything!"}
    return jokes.get(category, "I'm out of jokes! 😅")
```

**That's it!** The tool is immediately available.

### Mixed Approaches
You can use all patterns in the same file:

```python
# Function tool
@tool("quick_time", "Get current time") 
async def get_time() -> str:
    return datetime.now().isoformat()

# Class tool
@mcp_tool("formatter", "Text formatting")
class TextFormatter:
    async def execute(self, text: str, style: str) -> ToolResult:
        # Implementation...

# Method tools
class Utilities:
    @tool_method("hash", "Hash text")
    async def hash_text(self, text: str) -> ToolResult:
        # Implementation...
    
    @tool_method("encode", "Encode text")
    async def encode_text(self, text: str, encoding: str = "base64") -> ToolResult:
        # Implementation...

# Register method tools
MethodToolRegistry.register_class_methods(Utilities())
```

## 🔧 Schema Auto-Generation

All decorators automatically generate JSON schemas from type hints:

```python
@tool("example", "Example with auto-schema")
async def example(
    required_text: str,           # Required string
    optional_count: int = 5,      # Optional integer with default
    flag: bool = False,           # Optional boolean
    numbers: list = None          # Optional array
) -> ToolResult:
    # Schema automatically generated!
    pass
```

Generated schema:
```json
{
  "type": "object",
  "properties": {
    "required_text": {"type": "string"},
    "optional_count": {"type": "integer"},
    "flag": {"type": "boolean"},
    "numbers": {"type": "array", "nullable": true}
  },
  "required": ["required_text"]
}
```

## 🎯 Return Value Flexibility

Decorator tools support multiple return types:

```python
@tool("flexible", "Flexible return types")
async def flexible_tool(format: str) -> Union[str, dict, ToolResult]:
    if format == "string":
        return "Simple string response"
    elif format == "json":
        return {"status": "success", "data": [1, 2, 3]}
    else:
        result = ToolResult()
        result.add_text("Formatted response")
        result.add_json({"extra": "data"})
        return result
```

## 🚀 Quick Test

```bash
# Test decorator tools
python3 test_decorators_full.py

# Or use CLI
python3 ../mcp-client/cli.py python3 server_v2.py
```

## 📊 Comparison

| Pattern | Boilerplate | Use Case | Auto-Schema | Auto-Register |
|---------|-------------|----------|-------------|---------------|
| `@tool` | **Minimal** | Simple functions | ✅ | ✅ |
| `@mcp_tool` | **Low** | Complex logic | ✅ | ✅ |
| `@tool_method` | **Medium** | Related tools | ✅ | ✅ |
| `BaseTool` | **High** | Full control | ✅ | Manual |

## 🎉 Benefits

- **Zero Configuration** - Drop files in `tools/`, tools appear
- **Type Safety** - Schemas generated from Python types
- **Minimal Boilerplate** - Focus on logic, not plumbing
- **Flexible** - Mix and match patterns as needed
- **Compatible** - Works alongside traditional `BaseTool` classes
- **Performance** - `@lru_cache` optimizations built-in
