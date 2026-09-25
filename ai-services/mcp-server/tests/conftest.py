import os
import sys

MCP_SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if MCP_SERVER_DIR not in sys.path:
    sys.path.insert(0, MCP_SERVER_DIR)
