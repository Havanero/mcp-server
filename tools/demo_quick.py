#!/usr/bin/env python3
"""
Demo Tool - Created in seconds with decorators!
"""
import sys
sys.path.append('..')
from base_tool import ToolResult
from tool_decorators import tool, tool_method


@tool("greet", "Greet someone with style")
async def greet_user(name: str, style: str = "friendly") -> str:
    """Greet a user with different styles"""
    styles = {
        "friendly": f"Hello there, {name}! 😊",
        "formal": f"Good day, {name}.",
        "casual": f"Hey {name}! What's up?",
        "enthusiastic": f"WOW! Hi {name}!!! 🎉"
    }
    return styles.get(style, f"Hi {name}!")


class QuickTools:
    @tool_method("flip_coin", "Flip a virtual coin")
    async def flip_coin(self) -> ToolResult:
        import random
        result = ToolResult()
        outcome = "Heads" if random.choice([True, False]) else "Tails"
        result.add_text(f"🪙 Coin flip: {outcome}")
        return result
    
    @tool_method("dice_roll", "Roll dice")
    async def roll_dice(self, sides: int = 6, count: int = 1) -> ToolResult:
        import random
        result = ToolResult()
        rolls = [random.randint(1, sides) for _ in range(count)]
        result.add_text(f"🎲 Rolled {count}d{sides}: {rolls}")
        result.add_text(f"Total: {sum(rolls)}")
        return result

# Auto-register method tools
from tool_decorators import MethodToolRegistry
MethodToolRegistry.register_class_methods(QuickTools())
