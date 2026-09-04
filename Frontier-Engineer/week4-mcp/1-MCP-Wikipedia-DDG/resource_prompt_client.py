import asyncio
import logging
import os

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

# Configure logging so that the flow of method calls can be traced.
# Logs are written both to the console and to a log file so that
# the flow can be reviewed after this script has finished running.
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "resource_prompt_client.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

HTTP_URL = "http://localhost:8000/mcp"

async def main():
    logger.info("Entering method: main()")

    # Connect over streamable HTTP
    logger.info("main: creating MultiServerMCPClient for server 'demo' at %s", HTTP_URL)
    client = MultiServerMCPClient({
        "demo": {"url": HTTP_URL, "transport": "streamable_http"}
    })

    # 1) Get bio from the resource
    logger.info("main: fetching resource 'docs://aboutme' from server 'demo'")
    blobs = await client.get_resources(server_name="demo",
                                       uris="docs://aboutme")
    logger.info("main: fetched %d resource blob(s)", len(blobs) if blobs else 0)

    bio_text = blobs[0].as_string() if blobs else ""
    print("Bio:", bio_text[:120], "...")

    # 2) Build prompt messages using the bio as context
    logger.info("main: requesting prompt 'question' from server 'demo'")
    messages = await client.get_prompt(server_name="demo",
                                       prompt_name="question",
                                       arguments={
                                           "question": "What subjects does Bharath Teach",
                                           "context": bio_text
                                       })
    logger.info("main: prompt messages built")

    # 3) Send to LLM
    logger.info("main: creating ChatOpenAI llm instance (model=gpt-4o-mini)")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    logger.info("main: invoking llm.ainvoke() with prompt messages")
    resp = await llm.ainvoke(messages)
    logger.info("main: llm.ainvoke() returned response")
    print("\nLLM Answer:\n", resp.content)

    logger.info("Exiting method: main()")

if __name__ == "__main__":
    logger.info("Entering method: __main__")
    asyncio.run(main())
    logger.info("Exiting method: __main__")