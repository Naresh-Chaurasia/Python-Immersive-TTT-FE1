import asyncio
import os

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

import os
from dotenv import load_dotenv

load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env_rag")

api_key = os.getenv("OPENAI_API_KEY")
# print(api_key)

os.environ["OPENAI_API_KEY"] = api_key


# | Feature               | `AssistantAgent`                             | `UserProxyAgent`               |
# | --------------------- | -------------------------------------------- | ------------------------------ |
# | Purpose               | AI agent that thinks and generates responses | Represents the human user      |
# | Uses an LLM?          | ✅ Yes                                        | ❌ No                         |
# | Needs `model_client`? | ✅ Yes                                        | ❌ No                         |
# | Generates answers?    | ✅ Yes                                        | ❌ Waits for user input       |
# | Executes tools?       | ✅ Can (if configured)                        | Usually no (unless customized)|
# | Typical role          | Expert, assistant, coder, planner            | Human participant              |


# UserProxyAgent

# waits for user input
# forwards your message to the assistant
# sends your next reply back into the conversation

# Think of it as a bridge between you and the AI agents.

# You
#  │
#  ▼
# UserProxyAgent
#  │
#  ▼
# AssistantAgent (GPT-4o)
#  │
#  ▼
# UserProxyAgent
#  │
#  ▼
# You

# ````markdown
# The participants are:

# - `Student` (`UserProxyAgent`)
# - `MathTutor` (`AssistantAgent`)

# Notice that **you are not in this list** because you're outside the AutoGen framework.

# What actually happens step by step?

# 1. You start the program.
# 2. `UserProxyAgent` displays:

#    ```text
#    Enter your response:
#    ```

# 3. You type:

#    ```text
#    can you help me solve 2*4+5?
#    ```

# 4. `UserProxyAgent` converts your input into a chat message:

#    ```text
#    Student:
#    can you help me solve 2*4+5?
#    ```

# 5. `AssistantAgent` receives the message.
# 6. `AssistantAgent` calls GPT-4o.
# 7. GPT-4o generates the response.
# 8. `AssistantAgent` sends the response back.
# 9. `UserProxyAgent` displays the response and waits for your next input.

# Conversation flow:

# ```text
# You
#  │
#  ▼
# UserProxyAgent (Student)
#  │
#  ▼
# AssistantAgent (MathTutor)
#  │
#  ▼
# GPT-4o
#  │
#  ▼
# AssistantAgent
#  │
#  ▼
# UserProxyAgent
#  │
#  ▼
# You
# ```

# Think of it like customer support:

# ```text
# You (Customer)
#       │
#       ▼
# Receptionist (UserProxyAgent)
#       │
#       ▼
# Expert (AssistantAgent)
#       │
#       ▼
# Receptionist
#       │
#       ▼
# You
# ```

# The receptionist doesn't solve your problem. They simply pass messages between you and the expert.

# Similarly, the `UserProxyAgent` does not generate AI responses. It acts as a bridge between the human user (outside the framework) and the `AssistantAgent` (inside the framework).

# In short:

# - **You** → Provide input.
# - **UserProxyAgent** → Forwards your messages and displays responses.
# - **AssistantAgent** → Calls GPT-4o and generates the AI response.
# ````



async def main():
    model_client = OpenAIChatCompletionClient( model="gpt-4o" )

    assistant = AssistantAgent( name="MathTutor", model_client=model_client,
                                system_message="You are helpful math tutor.Help the user solve math problems step by step"
                                               "When the user says 'THANKS DONE' or similar, acknowledge and say 'LESSON COMPLETE' to end session." )

    user_proxy = UserProxyAgent( name="Student" )

    team = RoundRobinGroupChat( participants=[user_proxy, assistant],
                                termination_condition=TextMentionTermination( "LESSON COMPLETE" ) )

    # can you help me solve 2*4+5?
    await Console(team.run_stream(task = "I need help with algebra problem...") )


asyncio.run( main() )


#Human - Agent-(save)  ,Agent2 (save)
