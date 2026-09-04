import logging
import os

import wikipedia
from duckduckgo_search import DDGS
from mcp.server.fastmcp import FastMCP

# Configure logging so that the flow of method calls can be traced.
# Logs are written both to the console and to a log file so that
# the flow can be reviewed after the server has stopped running.
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "mcp_server.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create a FastMCP server named "Tool Server".
# This server will expose functions as MCP tools.
logger.info("Creating FastMCP server instance: Tool Server")
mcp = FastMCP(name="Tool Server")


# Register the following function as an MCP tool.
# The LLM/client will be able to discover and call this tool.
@mcp.tool()
def wikipedia_search(query: str) -> str:
    """Search Wikipedia and return a short summary."""

    logger.info("Entering method: wikipedia_search(query=%r)", query)

    try:
        # Search Wikipedia using the supplied query.
        # sentences=2 limits the result to a short 2-sentence summary.
        logger.info("wikipedia_search: calling wikipedia.summary()")
        result = wikipedia.summary(query, sentences=2)
        logger.info("wikipedia_search: search succeeded")
        return result

    except Exception as e:
        # If Wikipedia search fails, return the error as a string
        # instead of crashing the MCP server.
        logger.error("wikipedia_search: error occurred - %s", str(e))
        return f"Error: {str(e)}"

    finally:
        logger.info("Exiting method: wikipedia_search")


# Register this function as another MCP tool.
# This tool performs a search using DuckDuckGo.
@mcp.tool()
def ddg_search(query: str) -> str:
    """Search DuckDuckGo and return the top 3 results."""

    logger.info("Entering method: ddg_search(query=%r)", query)

    try:
        # Create a DuckDuckGo search client.
        # 'with' ensures that the client is properly closed afterward.
        logger.info("ddg_search: opening DDGS client")
        with DDGS() as ddgs:

            # Perform a text search.
            # max_results=3 limits the search to the first 3 results.
            logger.info("ddg_search: calling ddgs.text()")
            results = ddgs.text(query, max_results=3)
            logger.info("ddg_search: search succeeded")

            # Extract the 'body' (snippet/description) from each result
            # and combine the snippets into a single string.
            return "\n".join([r["body"] for r in results])

    except Exception as e:
        # If the DuckDuckGo search fails, return the error
        # instead of stopping the MCP server.
        logger.error("ddg_search: error occurred - %s", str(e))
        return f"Error: {str(e)}"

    finally:
        logger.info("Exiting method: ddg_search")


# This condition ensures that the code below runs only when
# this Python file is executed directly.
#
# It will NOT run if this file is imported as a module.
if __name__ == "__main__":

    logger.info("Entering method: __main__")

    # Start the MCP server using the STDIO transport.
    #
    # STDIO means:
    # - The MCP client communicates with this server through
    #   standard input/output.
    # - This is commonly used when an MCP client such as
    #   Claude Desktop launches the MCP server as a local process.
    logger.info("__main__: starting MCP server with transport=streamable-http")
    mcp.run(transport="streamable-http")
    # mcp.run(transport="stdio")
    logger.info("Exiting method: __main__")