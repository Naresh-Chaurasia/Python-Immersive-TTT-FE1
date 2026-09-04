import logging
import os

from mcp.server.fastmcp import FastMCP

# Configure logging so that the flow of method calls can be traced.
# Logs are written both to the console and to a log file so that
# the flow can be reviewed after the MCP server has stopped running.
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "resource_prompt_server.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("Creating FastMCP server instance: promptandresource-mcp-demo")
mcp = FastMCP("promptandresource-mcp-demo")

@mcp.resource("docs://aboutme")
def bharath_bio() -> str:
    logger.info("Entering method: bharath_bio()")
    result = (
        "Bharath Thippireddy is a popular Udemy tech instructor and software architect "
        "with 20+ years of experience in India and the USA. He teaches Java, Python, GenAI, "
        "LangChain, and GitHub Copilot, and builds AI apps (RAG, agents). He runs Neyah Digital Solutions, and works on "
        "ed‑tech and gov-tech ideas in India. He’s also a certified yoga teacher ,actor and an active "
        "content creator on YouTube and LinkedIn."
    )
    logger.info("Exiting method: bharath_bio()")
    return result

@mcp.prompt("question")
def ask_about_bharath(question: str, context: str) -> str:
    logger.info("Entering method: ask_about_bharath(question=%r)", question)
    result = (
        "System: You are a helpful assistant. Answer strictly using the provided context."
        f"Context:{context}"
        f"User question: {question}"
        "Answer:"
    )
    logger.info("Exiting method: ask_about_bharath()")
    return result

if __name__ == "__main__":
    logger.info("Entering method: __main__")
    logger.info("__main__: starting MCP server with transport=streamable-http")
    mcp.run(transport="streamable-http")
    logger.info("Exiting method: __main__")