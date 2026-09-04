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
LOG_FILE = os.path.join(LOG_DIR, "mcp_client.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


#                     Streamable HTTP
# ┌───────────────┐  ───────────────────►  ┌─────────────────┐
# │ Streamlit App │                        │  MCP Server     │
# │               │  ◄───────────────────  │ localhost:8000  │
# │   MCP Client  │                        │                 │
# └───────┬───────┘                        │ Tools:          │
#         │                                │ - Wikipedia     │
#         │                                │ - DuckDuckGo    │
#         ▼                                └─────────────────┘
#    ┌──────────┐
#    │   LLM    │
#    │ GPT-4o   │
#    └──────────┘


logger.info("Entering method: __main__ (module execution start)")

# Create an MCP client that can connect to one or more MCP servers.
#
# "tools" is the name we give to this MCP server configuration.
# It is NOT the individual tools such as wikipedia_search or ddg_search.
logger.info("__main__: creating MultiServerMCPClient for server 'tools' at http://localhost:8000/mcp")
client = MultiServerMCPClient({
    
    "tools": {
        # URL where the MCP server is running.
        #
        # This means the MCP server is expected to be available at:
        # http://localhost:8000/mcp
        "url": "http://localhost:8000/mcp",

        # Tell the MCP client which transport protocol to use
        # when communicating with this MCP server.
        #
        # streamable_http means communication happens over HTTP
        # using MCP's Streamable HTTP transport.
        "transport": "streamable_http"
    }
})


# Ask the MCP client to discover the tools exposed by the MCP server.
#
# get_tools() communicates with:
#
#     http://localhost:8000/mcp
#
# and retrieves the tools that the MCP server makes available.
#
# Because get_tools() is asynchronous, we use asyncio.run()
# to execute the async operation.
logger.info("__main__: discovering MCP tools via client.get_tools()")
tools = asyncio.run(client.get_tools())
logger.info("__main__: discovered %d MCP tool(s): %s", len(tools), [t.name for t in tools])

import os
from dotenv import load_dotenv

logger.info("__main__: loading environment variables from .env file")
load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CO_API_KEY = os.getenv("CO_API_KEY")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(CO_API_KEY)


# Create the LLM that will act as the brain of the agent.
#
# The LLM itself does not directly know about Wikipedia or
# DuckDuckGo.
logger.info("__main__: creating ChatOpenAI llm instance (model=gpt-4o)")
llm = ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)


# Create an AI agent and give it:
#
# 1. The LLM
# 2. The MCP tools discovered above
#
# The agent can now decide when it needs to call one of
# the MCP tools.
logger.info("__main__: creating agent via create_agent(llm, tools)")
agent = create_agent(llm, tools)


# Create the Streamlit application title.
logger.info("__main__: rendering Streamlit title")
st.title("AI Agent (MCP Version)")


# Display a text box where the user can enter a task.
#
# For example:
#
#     "Search Wikipedia for Python"
#
# or:
#
#     "Search the web for the latest information about LangChain"
task = st.text_input("Assign me a task")


# Execute this block only when the user has entered a task.
if task:

    logger.info("Entering method: on_task_submitted(task=%r)", task)

    # Send the user's task to the AI agent.
    #
    # ainvoke() is asynchronous, so asyncio.run() is used
    # to execute it from this synchronous Streamlit code.
    #        User
    #          │
    #          │ enters task
    #          ▼
    #        Streamlit
    #          │
    #          │ task
    #          ▼
    #        Agent
    #          │
    #          │ consults LLM
    #          ▼
    #        LLM (GPT-4o)
    #          │
    #          │ decides tool is needed
    #          ▼
    #        MCP Client
    #          │
    #          │ tool request
    #          ▼
    #        MCP Server
    #          │
    #          │ calls wikipedia_search()
    #          ▼
    #        Wikipedia
    #          │
    #          │ result
    #          ▼
    #        MCP Server
    #          │
    #          │ tool result
    #          ▼
    #        MCP Client
    #          │
    #          ▼
    #        Agent
    #          │
    #          │ sends tool result to LLM
    #          ▼
    #        LLM
    #          │
    #          │ generates final answer
    #          ▼
    #        Agent
    #          │
    #          ▼
    #        Streamlit
    #          │
    #          ▼
    #        User



#  ## Yes — `client.get_tools()` performs real network round-trips over HTTP to your MCP server.

# Since no `session` was passed (you're using `client.get_tools()` at the top level, not a pre-opened session), `load_mcp_tools()` internally does `async with create_session(connection) as tool_session: await tool_session.initialize(); tools = await _list_all_tools(tool_session)`. That means it **opens a brand new Streamable-HTTP session, initializes the MCP protocol handshake, lists tools, then tears the session down** — all in one call. Your logs map exactly to those steps:

# | Log line | What's actually happening |
# |---|---|
# | `HTTP Request: POST .../mcp "200 OK"` | The `initialize` request — MCP handshake, negotiating protocol version/capabilities |
# | `Received session ID: 788ed64b...` | Server assigns a session ID for this Streamable-HTTP connection |
# | `Negotiated protocol version: 2025-11-25` | Client/server agree on MCP protocol version |
# | `HTTP Request: GET .../mcp "200 OK"` | Client opens the SSE/streaming GET channel for server→client messages |
# | `HTTP Request: POST .../mcp "202 Accepted"` | Client sends the `initialized` notification (fire-and-forget, hence 202) |
# | `HTTP Request: POST .../mcp "200 OK"` | The actual `tools/list` request — this is what returns `wikipedia_search`/`ddg_search` |
# | `HTTP Request: DELETE .../mcp "200 OK"` | Client closes/terminates the session cleanly since it was a one-off, ad-hoc session (not persisted) |

# So **5 real HTTP requests** happen inside that single `await client.get_tools()` call: `initialize` → `GET` (stream) → `initialized` notification → `tools/list` → `DELETE` (session teardown).

# ### Important implication for your app
# Because `MultiServerMCPClient.get_tools()` doesn't keep the session open, **every time it's called it re-does the full handshake + list + teardown** — it does NOT reuse a persistent connection. In your `mcp_client.py`, this happens once at module load (top-level, outside `if task:`), so on every Streamlit rerun (which happens on every widget interaction, including just typing in the text box) it re-executes this entire handshake again. That's expected in this simple script pattern, but worth knowing: it's a real network round-trip, not a cached/local lookup, and it happens on every script rerun, not just once per app lifetime.

# If you want, I can help you optimize this in Act mode — e.g. using `st.cache_resource` to avoid re-fetching tools on every Streamlit rerun, or keeping a persistent session for the app's lifetime.   
 
    logger.info("on_task_submitted: invoking agent.ainvoke() with task")
    response = asyncio.run(
        agent.ainvoke({
            "messages": task
        })
    )
    logger.info("on_task_submitted: agent.ainvoke() returned response")


    # Display the complete response returned by the agent.
    #
    # This may contain the entire message history, including
    # intermediate tool calls and the final response.
    logger.info("on_task_submitted: rendering full response in Streamlit")
    st.write(response)


    # Get the last message from the response.
    #
    # The last message is normally the agent's final answer
    # after it has finished using any required tools.
    final_output = response["messages"][-1].content
    logger.info("on_task_submitted: extracted final_output from last message")


    # Display only the final answer to the user.
    logger.info("on_task_submitted: rendering final_output in Streamlit")
    st.write(final_output)
    logger.info("Exiting method: on_task_submitted")

