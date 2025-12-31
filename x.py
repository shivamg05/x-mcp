import threading
import logging

from fastmcp import FastMCP
from x_mcp.http_server import run_http_server
from x_mcp.tools import register_tools

logging.basicConfig(level=logging.INFO)

mcp = FastMCP("x-mcp")
register_tools(mcp)

if __name__ == "__main__":
    threading.Thread(target=run_http_server, daemon=True).start()
    mcp.run()