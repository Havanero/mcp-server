#!/bin/bash
# Test MCP Server with CLI Client

echo "🚀 Starting MCP Server test with CLI client..."
echo "📍 Server location: $(pwd)/server.py"
echo "📍 Client location: ../mcp-client/cli.py"
echo ""

# Check if client exists
if [ ! -f "../mcp-client/cli.py" ]; then
    echo "❌ CLI client not found at ../mcp-client/cli.py"
    exit 1
fi

# Check if server exists
if [ ! -f "server.py" ]; then
    echo "❌ Server not found at server.py"
    exit 1
fi

echo "✅ Starting interactive MCP client connected to our server..."
echo "💡 Try these commands:"
echo "   list"
echo "   help echo"
echo "   call echo {\"text\": \"Hello Server!\"}"
echo "   call calculate {\"operation\": \"multiply\", \"a\": 6, \"b\": 7}"
echo "   call current_time {}"
echo "   exit"
echo ""

# Start the CLI client with our server
python3 ../mcp-client/cli.py python3 server.py
