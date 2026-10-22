"""Shared Release 1 MCP server.

Runs natively on the host (not a Docker Compose service, per the Release 1
brief) and exposes every feature's tools over streamable HTTP on one port.
Backends reach it at ``MCP_SERVER_URL`` (default ``http://localhost:5400``),
or ``http://host.docker.internal:5400`` from inside a container.

Run directly: ``python server.py``
"""

import os
import re

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from tools import register_all

HOST = os.environ.get("MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_PORT", "5400"))

HOST_PATTERN = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?(:(\*|[0-9]{1,5}))?$")


def allowed_hosts():
    """Host header values the server accepts (DNS-rebinding protection).

    The native defaults are the loopback names and host.docker.internal. When the server runs in a container
    (the cloud AI profile) the backends reach it by its service name, so MCP_ALLOWED_HOSTS adds exact entries such
    as ``mcp-server:*``. A bare ``*`` or any other wildcard is rejected, so the protection cannot be switched off by accident.
    """
    hosts = ["127.0.0.1:*", "localhost:*", "host.docker.internal:*", f"{HOST}:*"]
    for entry in os.environ.get("MCP_ALLOWED_HOSTS", "").split(","):
        entry = entry.strip()
        if not entry:
            continue
        if not HOST_PATTERN.fullmatch(entry):
            raise ValueError(f"MCP_ALLOWED_HOSTS entry {entry!r} is not a host name with an optional port or :*")
        if entry not in hosts:
            hosts.append(entry)
    return hosts


mcp = MCPServer("asd-shared-mcp-server")

register_all(mcp)

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http", host=HOST, port=PORT,
        max_request_body_size=8192, max_sessions=64, session_idle_timeout=30,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts(),
            allowed_origins=["http://127.0.0.1:*", "http://localhost:*"],
        ),
    )
