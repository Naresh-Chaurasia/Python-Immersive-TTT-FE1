# server.py
from mcp.server.fastmcp import FastMCP

# Create an MCP server
my_mcp = FastMCP("Demo")


# Add an addition tool
@my_mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b