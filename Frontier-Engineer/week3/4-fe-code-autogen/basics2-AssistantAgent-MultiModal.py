import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import MultiModalMessage
from autogen_agentchat.ui import Console
from autogen_core import Image
from autogen_ext.models.openai import OpenAIChatCompletionClient

import os
from dotenv import load_dotenv

load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env_rag")

api_key = os.getenv("OPENAI_API_KEY")
# print(api_key)

os.environ["OPENAI_API_KEY"] = api_key


async def main1():
    model_client = OpenAIChatCompletionClient( model="gpt-4o" )
    assistant = AssistantAgent( name="MultiModalAssistant", model_client=model_client )
    image = Image.from_file("img.png")
    multimodal_message = MultiModalMessage(
        content=["what do you see in this image", image], source="user"
    )
    await Console(assistant.run_stream(task=multimodal_message))
    await model_client.close()


asyncio.run( main1() )
