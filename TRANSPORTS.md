# MCP Transport Options - Complete Guide

## 🚀 Transport Layer Comparison

Your MCP server now supports **3 transport layers**, each optimized for different use cases:

| Transport | Best For | Clients | Real-time | Setup | Use Case |
|-----------|----------|---------|-----------|-------|----------|
| **Stdio** | Development, CLI | Single | Yes | Simple | Local development, scripting |
| **WebSocket** | Production, Web Apps | Multiple | Yes | Medium | Real-time applications, browsers |
| **HTTP** | Integrations, REST | Multiple | No | Simple | Web APIs, simple integrations |

## 📡 1. Stdio Transport (Original)

**Perfect for:** Local development, CLI tools, single-user applications

### Start Server
```bash
python3 server_v2.py
```

### Connect Client
```bash
# Interactive CLI
python3 ../mcp-client/cli.py python3 server_v2.py

# Or programmatic
transport = StdioTransport(["python3", "server_v2.py"])
client = MCPClient(transport)
```

**Pros:**
- ✅ Fastest (no network overhead)
- ✅ Simple setup
- ✅ Perfect for development

**Cons:**
- ❌ Local only
- ❌ Single client
- ❌ Process-bound

---

## 🌐 2. WebSocket Transport (Recommended)

**Perfect for:** Production applications, web frontends, real-time tools

### Install Dependencies
```bash
pip install websockets
```

### Start Server
```bash
python3 server_websocket.py
# Server starts on ws://localhost:8765
```

### Connect Client
```bash
# Interactive WebSocket CLI
python3 websocket_client.py

# Or programmatic
client = WebSocketMCPClient("ws://localhost:8765")
await client.connect()
result = await client.call_tool("greet", {"name": "WebSocket"})
```

### Web Browser Client
```javascript
const ws = new WebSocket('ws://localhost:8765');

ws.onopen = () => {
    // Send MCP initialize request
    ws.send(JSON.stringify({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "web-client", "version": "1.0.0"}
        }
    }));
};

ws.onmessage = (event) => {
    const response = JSON.parse(event.data);
    console.log('MCP Response:', response);
};
```

**Pros:**
- ✅ Multiple clients
- ✅ Real-time bidirectional
- ✅ Web browser compatible
- ✅ Remote connections
- ✅ Persistent connections

**Cons:**
- ❌ More complex setup
- ❌ Connection management needed

---

## 🔗 3. HTTP Transport (REST-style)

**Perfect for:** Web APIs, simple integrations, REST clients

### Install Dependencies
```bash
pip install aiohttp
```

### Start Server
```bash
python3 server_http.py
# Server starts on http://localhost:8080
```

### API Endpoints

#### List Tools
```bash
curl http://localhost:8080/tools
```

#### Call Tool (REST-style)
```bash
curl -X POST http://localhost:8080/tools/greet \
     -H "Content-Type: application/json" \
     -d '{"name": "HTTP Client", "style": "friendly"}'
```

#### Send MCP JSON-RPC
```bash
curl -X POST http://localhost:8080/mcp \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 1,
       "method": "tools/call",
       "params": {
         "name": "current_time",
         "arguments": {"format": "readable"}
       }
     }'
```

#### Health Check
```bash
curl http://localhost:8080/health
```

#### Server Stats
```bash
curl http://localhost:8080/stats
```

### Web Interface
Visit **http://localhost:8080/client** for a simple web UI to test tools.

**Pros:**
- ✅ REST-style API
- ✅ Web-friendly
- ✅ Stateless
- ✅ Easy integration
- ✅ Built-in web client

**Cons:**
- ❌ Request/response only
- ❌ No real-time features
- ❌ More HTTP overhead

---

## 🎯 Which Transport Should You Use?

### For Development
```bash
# Quick testing and development
python3 server_v2.py  # Stdio
python3 ../mcp-client/cli.py python3 server_v2.py
```

### For Production Web Apps
```bash
# Real-time web applications
python3 server_websocket.py  # WebSocket
# Connect from browsers, mobile apps, etc.
```

### For REST APIs
```bash
# Simple integrations, web services
python3 server_http.py  # HTTP
# Use with curl, fetch(), REST clients
```

## 🧪 Test All Transports
```bash
# Install dependencies
pip install -r requirements.txt

# Test all three transports
python3 test_transports.py
```

## 🌟 Advanced Examples

### WebSocket with Authentication
```python
# Add auth to WebSocket server
class AuthenticatedWebSocketTransport(WebSocketTransport):
    async def _handle_client_connection(self, websocket, path):
        # Check authentication headers
        auth_header = websocket.request_headers.get('Authorization')
        if not self._validate_auth(auth_header):
            await websocket.close(code=4401, reason="Unauthorized")
            return
        
        # Continue with normal connection handling
        await super()._handle_client_connection(websocket, path)
```

### HTTP with CORS for Browser Apps
```python
# CORS is already built-in to HTTP transport
# Supports browser fetch() requests from any origin
fetch('http://localhost:8080/tools/greet', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: 'Browser', style: 'enthusiastic'})
})
.then(response => response.json())
.then(data => console.log(data));
```

### Load Balancing Multiple Servers
```python
# Start multiple servers on different ports
# Use nginx/HAProxy to load balance
# WebSocket: ws://localhost:8765, ws://localhost:8766
# HTTP: http://localhost:8080, http://localhost:8081
```

## 🔧 Production Deployment

### WebSocket with SSL
```python
import ssl
ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.load_cert_chain("server.crt", "server.key")

server = await websockets.serve(
    handler, "0.0.0.0", 443, ssl=ssl_context
)
```

### HTTP with Reverse Proxy
```nginx
# nginx.conf
location /mcp/ {
    proxy_pass http://localhost:8080/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 🎉 Summary

- **Stdio**: Fast, simple, perfect for CLI and development
- **WebSocket**: Production-ready, real-time, multi-client support
- **HTTP**: RESTful, web-friendly, easy integration

**Recommendation: Start with Stdio for development, move to WebSocket for production web apps, or HTTP for simple API integrations.**

All three transports use the same tool system and plugin architecture - just different ways to connect!
