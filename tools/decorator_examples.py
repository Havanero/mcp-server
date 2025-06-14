#!/usr/bin/env python3
"""
Decorator Example Tools - Showcasing all decorator patterns

This demonstrates how to use the new decorator patterns to create tools with minimal boilerplate.
"""
import asyncio
import sys
import datetime
import random
from typing import Optional

sys.path.append('..')
from base_tool import ToolResult
from tool_decorators import tool, mcp_tool, tool_method, MethodToolRegistry


# Pattern 1: Function-based tools with @tool decorator
@tool("current_time", "Get the current date and time")
async def get_current_time(timezone: str = "UTC", format: str = "iso") -> str:
    """Get current time in specified timezone and format"""
    now = datetime.datetime.now()
    
    if format == "iso":
        return f"Current time: {now.isoformat()}"
    elif format == "readable": 
        return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}"
    else:
        return f"Current time: {now}"


@tool("random_number", "Generate a random number in a range")
async def generate_random(min_val: int = 1, max_val: int = 100) -> str:
    """Generate random number between min and max values"""
    number = random.randint(min_val, max_val)
    return f"Random number between {min_val} and {max_val}: {number}"


@tool("reverse_text", "Reverse any text string")
async def reverse_text(text: str) -> ToolResult:
    """Reverse the given text"""
    result = ToolResult()
    reversed_text = text[::-1]
    result.add_text(f"Original: {text}")
    result.add_text(f"Reversed: {reversed_text}")
    return result


# Pattern 2: Class-based tool with @mcp_tool decorator
@mcp_tool("string_utils", "String manipulation utilities")
class StringUtilsTool:
    """String manipulation tool using class decorator"""
    
    async def execute(self, operation: str, text: str, **kwargs) -> ToolResult:
        """
        Perform string operations.
        
        Args:
            operation: Operation type ('upper', 'lower', 'title', 'count', 'replace')
            text: Text to operate on
            **kwargs: Additional parameters for specific operations
        """
        result = ToolResult()
        
        if operation == "upper":
            result.add_text(f"Uppercase: {text.upper()}")
        elif operation == "lower":
            result.add_text(f"Lowercase: {text.lower()}")
        elif operation == "title":
            result.add_text(f"Title Case: {text.title()}")
        elif operation == "count":
            target = kwargs.get("target", " ")
            count = text.count(target)
            result.add_text(f"Count of '{target}' in text: {count}")
        elif operation == "replace":
            old = kwargs.get("old", "")
            new = kwargs.get("new", "")
            replaced = text.replace(old, new)
            result.add_text(f"Replaced '{old}' with '{new}': {replaced}")
        else:
            result.add_text(f"Unknown operation: {operation}")
            result.add_text("Available: upper, lower, title, count, replace")
        
        return result


# Pattern 3: Multiple tools in one class with @tool_method
class MathUtilities:
    """Collection of math utility tools using method decorators"""
    
    @tool_method("add_numbers", "Add multiple numbers together")
    async def add_numbers(self, numbers: str) -> ToolResult:
        """Add numbers from comma-separated string"""
        try:
            num_list = [float(x.strip()) for x in numbers.split(',')]
            total = sum(num_list)
            
            result = ToolResult()
            result.add_text(f"Numbers: {', '.join(map(str, num_list))}")
            result.add_text(f"Sum: {total}")
            return result
            
        except ValueError:
            result = ToolResult()
            result.add_text("Error: Please provide comma-separated numbers")
            return result
    
    @tool_method("fibonacci", "Calculate Fibonacci number at position n")
    async def fibonacci(self, n: int) -> ToolResult:
        """Calculate nth Fibonacci number"""
        if n < 0:
            result = ToolResult()
            result.add_text("Error: n must be non-negative")
            return result
        
        def fib(x):
            if x <= 1:
                return x
            return fib(x-1) + fib(x-2)
        
        # Limit to reasonable values to avoid long computation
        if n > 40:
            result = ToolResult()
            result.add_text(f"Error: n too large (max 40), got {n}")
            return result
        
        fib_value = fib(n)
        result = ToolResult()
        result.add_text(f"Fibonacci({n}) = {fib_value}")
        return result
    
    @tool_method("prime_check", "Check if a number is prime")
    async def is_prime(self, number: int) -> ToolResult:
        """Check if a number is prime"""
        def check_prime(n):
            if n < 2:
                return False
            for i in range(2, int(n ** 0.5) + 1):
                if n % i == 0:
                    return False
            return True
        
        is_prime_result = check_prime(number)
        result = ToolResult()
        result.add_text(f"{number} is {'prime' if is_prime_result else 'not prime'}")
        
        if not is_prime_result and number > 1:
            # Find factors
            factors = []
            for i in range(2, number):
                if number % i == 0:
                    factors.append(i)
                    if len(factors) >= 3:  # Limit output
                        factors.append("...")
                        break
            if factors:
                result.add_text(f"Factors: {', '.join(map(str, factors))}")
        
        return result


class TextAnalyzer:
    """Text analysis tools"""
    
    @tool_method("word_stats", "Analyze word statistics in text")
    async def analyze_text(self, text: str) -> ToolResult:
        """Analyze text statistics"""
        words = text.split()
        characters = len(text)
        chars_no_spaces = len(text.replace(' ', ''))
        sentences = len([s for s in text.split('.') if s.strip()])
        
        result = ToolResult()
        result.add_text(f"📊 Text Analysis:")
        result.add_text(f"  Words: {len(words)}")
        result.add_text(f"  Characters: {characters}")
        result.add_text(f"  Characters (no spaces): {chars_no_spaces}")
        result.add_text(f"  Sentences: {sentences}")
        
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)
            result.add_text(f"  Average word length: {avg_word_length:.2f}")
        
        return result
    
    @tool_method("extract_emails", "Extract email addresses from text")
    async def extract_emails(self, text: str) -> ToolResult:
        """Extract email addresses using simple pattern matching"""
        import re
        
        # Simple email regex pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        result = ToolResult()
        if emails:
            result.add_text(f"📧 Found {len(emails)} email(s):")
            for email in emails:
                result.add_text(f"  • {email}")
        else:
            result.add_text("📧 No email addresses found")
        
        return result


# Register all method-based tools
MethodToolRegistry.register_class_methods(MathUtilities())
MethodToolRegistry.register_class_methods(TextAnalyzer())


# Test function to demonstrate all tools
async def test_decorator_tools():
    """Test all decorator-based tools"""
    from tool_decorators import get_decorator_tools
    
    print("🧪 Testing Decorator Tools")
    tools = get_decorator_tools()
    print(f"📦 Found {len(tools)} decorator tools")
    
    for name, tool in tools.items():
        print(f"\n🔧 Tool: {name}")
        print(f"   Description: {tool.description}")
        print(f"   Schema: {tool.input_schema}")
    
    print("\n⚡ Testing function tools:")
    
    # Test function tools
    try:
        time_tool = tools["current_time"]
        time_result = await time_tool.execute(format="readable")
        print(f"Time: {time_result.to_dict()}")
        
        random_tool = tools["random_number"] 
        random_result = await random_tool.execute(min_val=1, max_val=10)
        print(f"Random: {random_result.to_dict()}")
        
    except Exception as e:
        print(f"Error testing function tools: {e}")
    
    print("\n⚡ Testing method tools:")
    
    # Test method tools
    try:
        if "fibonacci" in tools:
            fib_tool = tools["fibonacci"]
            fib_result = await fib_tool.execute(n=10)
            print(f"Fibonacci: {fib_result.to_dict()}")
        
        if "word_stats" in tools:
            stats_tool = tools["word_stats"]
            stats_result = await stats_tool.execute(text="Hello world! This is a test.")
            print(f"Stats: {stats_result.to_dict()}")
            
    except Exception as e:
        print(f"Error testing method tools: {e}")


if __name__ == "__main__":
    asyncio.run(test_decorator_tools())
