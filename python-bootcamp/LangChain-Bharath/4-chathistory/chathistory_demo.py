import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories.in_memory import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

import os
from dotenv import load_dotenv

load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CO_API_KEY = os.getenv("CO_API_KEY")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(CO_API_KEY)

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# --------------------------------------------------
# 1. Prompt
# --------------------------------------------------

prompt_template = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an Agile Coach. "
        "Answer any questions related to the agile process."
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}")
])


# --------------------------------------------------
# 2. LLM chain
# --------------------------------------------------

chain = prompt_template | llm


# --------------------------------------------------
# 3. Chat history
# --------------------------------------------------

history_for_chain = InMemoryChatMessageHistory()


# --------------------------------------------------
# 4. Chain with message history
# --------------------------------------------------

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: history_for_chain,
    input_messages_key="input",
    history_messages_key="chat_history"
)


# --------------------------------------------------
# 5. Chat
# --------------------------------------------------

print("\nAgile Guide")

while True:

    question = input("\nEnter the question (q to quit): ")

    if question.lower() == "q":
        break

    if question:

        print("\n" + "=" * 60)
        print("1. USER INPUT")
        print("=" * 60)
        print(question)


        # ------------------------------------------
        # Show history BEFORE the request
        # ------------------------------------------

        print("\n" + "=" * 60)
        print("2. CHAT HISTORY BEFORE REQUEST")
        print("=" * 60)

        for message in history_for_chain.messages:
            print(f"{message.type}: {message.content}")


        # ------------------------------------------
        # Invoke chain
        # ------------------------------------------

        response = chain_with_history.invoke(
            {"input": question},
            {
                "configurable": {
                    "session_id": "abc123"
                }
            }
        )


        # ------------------------------------------
        # Show LLM response
        # ------------------------------------------

        print("\n" + "=" * 60)
        print("3. LLM RESPONSE")
        print("=" * 60)

        print(response.content)


        # ------------------------------------------
        # Show updated history
        # ------------------------------------------

        print("\n" + "=" * 60)
        print("4. CHAT HISTORY AFTER REQUEST")
        print("=" * 60)

        for message in history_for_chain.messages:
            print(f"{message.type}: {message.content}")