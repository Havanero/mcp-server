#!/usr/bin/env python3
"""
MCP Server - Transport Layer

Server-side stdio transport for MCP protocol communication.
Handles incoming requests and outgoing responses via stdin/stdout.
"""
import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional


@dataclass
class MCPRequest:
    """Incoming MCP request"""
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPRequest":
        return cls(
            method=data["method"],
            params=data.get("params", {}),
            id=data.get("id")
        )


@dataclass
class MCPResponse:
    """Outgoing MCP response"""
    id: Optional[str]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        response = {"id": self.id}
        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result or {}
        return response


class StdioServerTransport:
    """Server-side stdio transport for MCP communication"""

    def __init__(self):
        self.running = False
        self.request_handler: Optional[Callable[[MCPRequest], Awaitable[MCPResponse]]] = None

    def set_request_handler(self, handler: Callable[[MCPRequest], Awaitable[MCPResponse]]) -> None:
        """Set the async request handler function"""
        self.request_handler = handler

    async def start(self) -> None:
        """Start the server and process incoming requests"""
        self.running = True
        logging.info("MCP Server started on stdio")

        try:
            async for line in self._read_stdin():
                if not self.running:
                    break

                await self._process_line(line)

        except KeyboardInterrupt:
            logging.info("Server interrupted")
        finally:
            self.running = False

    async def _read_stdin(self):
        """Async generator for reading stdin lines"""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while self.running:
            try:
                line = await reader.readline()
                if not line:  # EOF
                    break
                yield line.decode().strip()
            except Exception as e:
                logging.error(f"Error reading stdin: {e}")
                break

    async def _process_line(self, line: str) -> None:
        """Process a single JSON-RPC line"""
        if not line.strip():
            return

        try:
            data = json.loads(line)
            request = MCPRequest.from_dict(data)

            logging.debug(f"Processing request: {request.method}")

            if self.request_handler:
                response = await self.request_handler(request)
                await self._send_response(response)
            else:
                # Send error if no handler
                error_response = MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": "Method not found"}
                )
                await self._send_response(error_response)

        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON received: {line} - {e}")
            error_response = MCPResponse(
                id=None,
                error={"code": -32700, "message": "Parse error"}
            )
            await self._send_response(error_response)
        except Exception as e:
            logging.error(f"Error processing request: {e}")
            error_response = MCPResponse(
                id=data.get("id") if 'data' in locals() else None,
                error={"code": -32603, "message": "Internal error"}
            )
            await self._send_response(error_response)

    async def _send_response(self, response: MCPResponse) -> None:
        """Send response to stdout"""
        json_response = json.dumps(response.to_dict())
        print(json_response)
        sys.stdout.flush()
        logging.debug(f"Sent response: {json_response}")

    async def send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send notification (no response expected)"""
        notification = {"method": method, "params": params}
        json_notification = json.dumps(notification)
        print(json_notification)
        sys.stdout.flush()
        logging.debug(f"Sent notification: {json_notification}")

    def stop(self) -> None:
        """Stop the server"""
        self.running = False


# Simple test for the transport
async def test_transport():
    """Test the server transport with echo handler"""

    async def echo_handler(request: MCPRequest) -> MCPResponse:
        """Simple echo request handler"""
        return MCPResponse(
            id=request.id,
            result={
                "echo": {
                    "method": request.method,
                    "params": request.params
                }
            }
        )

    transport = StdioServerTransport()
    transport.set_request_handler(echo_handler)

    logging.info("Echo server starting - send JSON-RPC messages")
    await transport.start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(test_transport())
