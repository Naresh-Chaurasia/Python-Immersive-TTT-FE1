import os
from langchain_openai import ChatOpenAI
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate

import os
from dotenv import load_dotenv

load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CO_API_KEY = os.getenv("CO_API_KEY")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(CO_API_KEY)

llm=ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)

prompt_template = ChatPromptTemplate.from_messages(
[
    ("system","You are a Agile Coach.Answer any questions "
              "related to the agile process"),
    ("human", "{input}")
]
)

st.title("Agile Guide")

input = st.text_input("Enter the question:")

chain = prompt_template | llm

if input:
    response = chain.invoke({"input":input})
    st.write(response.content)