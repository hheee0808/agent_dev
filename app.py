import os
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()
st.set_page_config(page_title="agent-dev", page_icon="")
st.title("agent-dev")
st.caption("Framework-free multi-agent orchestrator · Phase 0")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if query := st.chat_input("질문 입력"):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)
    with st.chat_message("assistant"):
        with st.spinner("Gemini..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query,
            )
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})
