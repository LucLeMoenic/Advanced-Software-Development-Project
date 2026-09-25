"""Shared Release 1 MCP server.

Runs natively on the host (not a Docker Compose service, per the Release 1
brief) and exposes every feature's tools over streamable HTTP on one port.
Backends reach it at ``MCP_SERVER_URL`` (default ``http://localhost:5400``),
or ``http://host.docker.internal:5400`` from inside a container.

Run directly: ``python server.py``
"""

import os

from mcp.server.mcpserver import MCPServer

from tools import register_all

HOST = os.environ.get("MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_PORT", "5400"))

mcp = MCPServer("asd-shared-mcp-server")

register_all(mcp)

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=HOST, port=PORT)
