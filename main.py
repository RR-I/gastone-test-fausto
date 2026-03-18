import os
import time
from typing import Any

import streamlit as st
from agents import Agent, Runner, FileSearchTool, ModelSettings, trace


# ============================================================
# CONFIG
# ============================================================
st.set_page_config(page_title="Gastone", page_icon="💬", layout="centered")


def get_secret(name: str, default: str = "") -> str:
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, default)


CONFIG = {
    "OPENAI_API_KEY": get_secret("OPENAI_API_KEY"),
    "VECTOR_STORE_ID": get_secret("VECTOR_STORE_ID"),
    "WORKFLOW_ID": get_secret("WORKFLOW_ID"),
    "TRACE_NAME": get_secret("TRACE_NAME", "Gastone Test Fausto"),
    "MODEL_NAME": get_secret("MODEL_NAME", "gpt-5.4"),
    "APP_USER": get_secret("APP_USER"),
    "APP_PASSWORD": get_secret("APP_PASSWORD"),
}

if CONFIG["OPENAI_API_KEY"]:
    os.environ["OPENAI_API_KEY"] = CONFIG["OPENAI_API_KEY"]


# ============================================================
# SESSION
# ============================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "history_items" not in st.session_state:
    st.session_state.history_items = []

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


# ============================================================
# LOGIN
# ============================================================
def login_view():
    st.title("🔐 Accesso Gastone")

    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Accedi")

        if submitted:
            if (
                username == CONFIG["APP_USER"]
                and password == CONFIG["APP_PASSWORD"]
            ):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Credenziali non valide")


# ============================================================
# AGENT
# ============================================================
def build_agent() -> Agent:
    file_search = FileSearchTool(
        vector_store_ids=[CONFIG["VECTOR_STORE_ID"]]
    )

    return Agent(
        name="Agent",
        instructions="""
Sei un assistente esperto nelle procedure aziendali di Ranking Road Italia.
Prima di rispondere effettua sempre una ricerca nei file.
Non inventare nulla.
""",
        model=CONFIG["MODEL_NAME"],
        tools=[file_search],
        model_settings=ModelSettings(
            reasoning={"effort": "low", "summary": "auto"},
            store=True,
        ),
    )


def run_agent(user_text: str) -> str:
    agent = build_agent()

    input_items: list[Any] = list(st.session_state.history_items)
    input_items.append(
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_text}],
        }
    )

    with trace(
        workflow_name=CONFIG["TRACE_NAME"],
        metadata={"workflow_id": CONFIG["WORKFLOW_ID"]},
    ):
        result = Runner.run_sync(agent, input_items)

    st.session_state.history_items = result.to_input_list()

    return str(result.final_output or "")


# ============================================================
# CHAT UI
# ============================================================
def typewriter_effect(text: str, placeholder):
    output = ""
    for char in text:
        output += char
        placeholder.markdown(output)
        time.sleep(0.01)


def chat_view():
    st.markdown(
                    """
                    <div style="display: flex; justify-content: center; padding: 2%;">
                        <img src="https://www.rankingroad.it/wp-content/uploads/2023/01/ranking-road-italia-logo.png" 
                        alt="Ranking Road Italia Logo" style="max-width: 35%; height: auto; padding: 20px; border-radius: 10px;">
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    st.title("Gastone")
    st.subheader("Il tuo assistente per conoscere le procedure o l'organigramma di Ranking Road Italia")

    col1, col2 = st.columns([0.9, 0.1])
    with col2:
        if st.button("🚪Esci"):
            st.session_state.authenticated = False
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("Scrivi...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("🔎 Cerco nei documenti...")

            try:
                response = run_agent(prompt)
                typewriter_effect(response, placeholder)
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                placeholder.error(str(e))


# ============================================================
# MAIN
# ============================================================
if not st.session_state.authenticated:
    login_view()
    st.stop()

chat_view()
