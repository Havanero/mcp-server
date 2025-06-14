#!/bin/bash
# Quick verification that the decorator fix works

echo "🔧 MCP Decorator Fix Verification"
echo "=================================="
echo ""

echo "📋 Checking fixed files..."
if grep -q "class StringUtilsTool(BaseTool)" tools/decorator_examples.py; then
    echo "✅ decorator_examples.py - StringUtilsTool now inherits from BaseTool"
else
    echo "❌ decorator_examples.py - Fix not applied"
fi

if grep -q "must inherit from BaseTool" tool_decorators.py; then
    echo "✅ tool_decorators.py - @mcp_tool now has clear error messaging"  
else
    echo "❌ tool_decorators.py - Fix not applied"
fi

echo ""
echo "🧪 Testing server startup (should complete without errors)..."
echo "Press Ctrl+C after you see tool loading messages"
echo ""

# Test that server starts without the abstract method error
python3 server_v2.py
