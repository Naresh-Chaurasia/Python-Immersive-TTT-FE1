import os
from langchain_openai import ChatOpenAI
import streamlit as st
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

import os
from dotenv import load_dotenv

load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CO_API_KEY = os.getenv("CO_API_KEY")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(CO_API_KEY)

llm=ChatOpenAI(model="gpt-4o", api_key=OPENAI_API_KEY)


title_prompt = PromptTemplate(
    input_variables=["topic"],
    template="""You are an experienced speech writer.
    You need to craft an impactful title for a speech 
    on the following topic: {topic}
    Answer exactly with one title.	
    """
)

speech_prompt = PromptTemplate(
    input_variables=["title"],
    template="""You need to write a powerful speech of 350 words
     for the following title: {title}
    """
)

# """
# topic
#   ↓
# title_prompt
#   ↓
# LLM
#   ↓
# StrOutputParser
#   ↓
# "Generated Title"          ← first_chain output
#   ↓
# speech_prompt
#   ↓
# LLM
#   ↓
# AIMessage                   ← final_chain output

# ---


# generated_title = first_chain.invoke({"topic": topic})

# second_chain.invoke({
#     "title": generated_title
# })

# """

# first_chain = title_prompt | llm | StrOutputParser() 
# output = first_chain.invoke({"topic": "The Future of Artificial Intelligence"})

# print("Generated Title:", output)


# This does two things - st.write(title) - displays the title in Streamlit.
# then title returns the title to be used in the next chain. The [1] at the end is to return the second element of the tuple, which is the title itself.
first_chain = title_prompt | llm | StrOutputParser() | (lambda title: (st.write(title),title)[1])
second_chain = speech_prompt | llm
final_chain = first_chain | second_chain

st.title("Speech Generator")

topic = st.text_input("Enter the topic:")

if topic:
    response = final_chain.invoke({"topic":topic})
    st.write(response.content)