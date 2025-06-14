#!/bin/bash
# Quick test script for decorator tools

echo "🎯 MCP Decorator Tools Quick Test"
echo "=================================="
echo ""

echo "🧪 Testing all decorator patterns..."
echo "1. Function decorators (@tool)"
echo "2. Class decorators (@mcp_tool)"  
echo "3. Method decorators (@tool_method)"
echo "4. Traditional BaseTool classes"
echo ""

echo "🚀 Starting enhanced server with decorator support..."
echo ""

# Test with CLI
python3 ../mcp-client/cli.py python3 server_v2.py
