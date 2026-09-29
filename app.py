import asyncio
import os

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="agent-dev", page_icon="", layout="wide")

tab_chat, tab_digest, tab_ingest, tab_eval = st.tabs(["Chat", "Digest", "Ingest", "Eval"])

# ── Chat ──────────────────────────────────────────────────────
with tab_chat:
    st.title("agent-dev")
    st.caption("Framework-free multi-agent orchestrator · 5 agents")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("meta"):
                st.caption(msg["meta"])

    if query := st.chat_input("질문 입력 (RAG, 리서치, 큐레이션, CI 분석 등)"):
        st.session_state.messages.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                try:
                    r = httpx.post(f"{API_BASE}/chat", json={"message": query}, timeout=120)
                    data = r.json()
                    answer = data.get("output", "")
                    agent = data.get("agent", "")
                    usage = data.get("usage", {})
                    elapsed = data.get("elapsed_s", 0)
                    meta = f"agent: {agent} | {usage.get('model', '')} | ${usage.get('cost_usd', 0):.6f} | {elapsed:.1f}s"
                except Exception as e:
                    answer = f"API 오류: {e}"
                    meta = ""

            st.markdown(answer)
            if meta:
                st.caption(meta)
            st.session_state.messages.append({"role": "assistant", "content": answer, "meta": meta})

# ── Digest ────────────────────────────────────────────────────
with tab_digest:
    st.header("Web Curation Digest")
    if st.button("Run Curation Now"):
        with st.spinner("Fetching & ranking articles..."):
            try:
                r = httpx.post(f"{API_BASE}/curator/run", timeout=120)
                data = r.json()
                if data.get("error"):
                    st.error(data["error"])
                else:
                    st.success(f"Ranked {data.get('articles_count', 0)} articles | Slack sent: {data.get('slack_sent')}")
            except Exception as e:
                st.error(f"API 오류: {e}")

# ── Ingest ────────────────────────────────────────────────────
with tab_ingest:
    st.header("Document Ingest")
    uploaded = st.file_uploader("Upload document (txt, md, pdf, docx)", type=["txt", "md", "pdf", "docx"])
    if uploaded and st.button("Ingest"):
        with st.spinner("Chunking & embedding..."):
            try:
                r = httpx.post(
                    f"{API_BASE}/ingest",
                    files={"file": (uploaded.name, uploaded.getvalue())},
                    timeout=120,
                )
                data = r.json()
                st.success(f"Ingested {data.get('file', '')} → {data.get('chunks', 0)} chunks")
            except Exception as e:
                st.error(f"Ingest 오류: {e}")

# ── Eval ──────────────────────────────────────────────────────
with tab_eval:
    st.header("Eval Dashboard")
    st.info("Run `python -m evals.run` to execute evaluations. Results appear in Langfuse dashboard.")

    try:
        r = httpx.get(f"{API_BASE}/health", timeout=5)
        data = r.json()
        st.metric("Status", data.get("status", "unknown"))
        agents = data.get("agents", [])
        cols = st.columns(len(agents))
        for col, agent in zip(cols, agents):
            col.metric("Agent", agent)
    except Exception:
        st.warning("API server not running")
