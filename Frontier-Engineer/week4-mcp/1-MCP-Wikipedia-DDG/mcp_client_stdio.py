import asyncio
import logging
import os

import streamlit as st

from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent

# Configure logging so that the flow of method calls can be traced.
# Logs are written both to the console and to a log file so that
# the flow can be reviewed after the Streamlit app has stopped running.
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "mcp_client_stdio.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


logger.info("Entering method: __main__ (module execution start)")

logger.info("__main__: creating MultiServerMCPClient for server 'tools' via stdio (python3 mcp_server_stdio.py)")
client = MultiServerMCPClient({
    "tools": {
        "command": "python3",
        "args": ["mcp_server_stdio.py"],
        "transport": "stdio"
    }
})

logger.info("__main__: discovering MCP tools via client.get_tools()")
tools = asyncio.run(client.get_tools())
logger.info("__main__: discovered %d MCP tool(s): %s", len(tools), [t.name for t in tools])

logger.info("__main__: creating ChatOpenAI llm instance (model=gpt-4o)")

import os
from dotenv import load_dotenv

logger.info("__main__: loading environment variables from .env file")
load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CO_API_KEY = os.getenv("CO_API_KEY")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(CO_API_KEY)


llm = ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)
logger.info("__main__: creating agent via create_agent(llm, tools)")
agent = create_agent(llm, tools)

logger.info("__main__: rendering Streamlit title")
st.title("AI Agent (MCP Version)")
task = st.text_input("Assign me a task")

if task:
    logger.info("Entering method: on_task_submitted(task=%r)", task)
    logger.info("on_task_submitted: invoking agent.ainvoke() with task")
    response = asyncio.run(agent.ainvoke({"messages": task}))
    logger.info("on_task_submitted: agent.ainvoke() returned response")
    st.write(response)
    final_output = response["messages"][-1].content
    logger.info("on_task_submitted: extracted final_output from last message")
    st.write(final_output)
    logger.info("Exiting method: on_task_submitted")

