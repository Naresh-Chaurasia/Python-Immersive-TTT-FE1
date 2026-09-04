import os
from langchain_openai import ChatOpenAI
import streamlit as st
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser,JsonOutputParser

import os
from dotenv import load_dotenv

load_dotenv("/Users/nareshchaurasia/nc/PYTHON-ARCHITECT/Python-Immersive-AI-MAC/.env", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CO_API_KEY = os.getenv("CO_API_KEY")
# ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(CO_API_KEY)

title_prompt = PromptTemplate(
    input_variables=["topic"],
    template="""You are an experienced speech writer.
    You need to craft an impactful title for a speech 
    on the following topic: {topic}
    Answer exactly with one title.	
    """
)

speech_prompt = PromptTemplate(
    input_variables=["title", "emotion"],
    template="""You need to write a powerful {emotion} speech of 350 words
     for the following title: {title}   
    """
)

first_chain = title_prompt | llm | StrOutputParser() | (lambda title: (st.write(title),title)[1])
second_chain = speech_prompt | llm
final_chain = first_chain | (lambda title:{"title": title,"emotion": emotion}) | second_chain

st.title("Speech Generator")

topic = st.text_input("Enter the topic:")
emotion = st.text_input("Enter the emotion:")

if topic and emotion:
    response = final_chain.invoke({"topic":topic})
    st.write(response.content)

