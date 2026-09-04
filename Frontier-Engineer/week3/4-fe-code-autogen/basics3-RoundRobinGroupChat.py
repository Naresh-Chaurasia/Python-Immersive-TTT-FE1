import asyncio
import os

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

import os
from dotenv import load_dotenv

load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env_rag")

api_key = os.getenv("OPENAI_API_KEY")
# print(api_key)

os.environ["OPENAI_API_KEY"] = api_key

async def main():
    #create first assitant agent
    model_client = OpenAIChatCompletionClient( model="gpt-4o" )
    agent1 = AssistantAgent( name="MathTeacher", model_client=model_client,
                             system_message="You are a math teacher,Explain concepts clearly and ask follow-up "
                                            "questions" )

    agent2 = AssistantAgent( name="Student", model_client=model_client,
                             system_message="You are a curious student. Ask questions and show your thinking process" )

    team = RoundRobinGroupChat( participants=[agent1, agent2],
                                termination_condition=MaxMessageTermination( max_messages=6 ) )

    await Console( team.run_stream( task="Let's discuss what is multiplication and how it works" ) )
    await model_client.close()


asyncio.run( main() )
