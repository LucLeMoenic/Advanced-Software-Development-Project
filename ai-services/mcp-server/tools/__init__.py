"""Per-feature MCP tool modules.

Each feature (student-1 .. student-5) owns one module here, e.g. ``attractions.py``
for Student 3. A module exposes a single ``register(mcp: MCPServer) -> None``
function that registers its tools with ``@mcp.tool(name="<feature>.<action>")``.

``server.py`` imports every module's ``register`` function and calls it once at
startup. Keeping registration behind a function (instead of decorating at
import time with a shared decorator) means a feature module can be developed
and unit-tested without booting the whole server.
"""

from typing import Callable, List

from mcp.server.mcpserver import MCPServer

# Populated by each feature's Stage 1 branch, e.g.:
#   from . import attractions
#   REGISTRARS.append(attractions.register)
REGISTRARS: List[Callable[[MCPServer], None]] = []


def register_all(mcp: MCPServer) -> None:
    for register in REGISTRARS:
        register(mcp)
