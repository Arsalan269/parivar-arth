"""
Chat Assistant Page for Parivar Arth.
Provides an interactive AI chat interface querying live app calculations,
status metrics, what-if simulations, and offline FAQ knowledge.
"""

import os
import sys
import streamlit as st

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.security import touch_session, get_current_user_id
from chatbot.agent import ParivarChatbotAgent
from app.styles import apply_theme, render_header, render_footer, PRIMARY_TEAL, ACCENT_SAFFRON, TEXT_NAVY


def show_chat_assistant_page():
    st.set_page_config(page_title="Parivar AI Assistant - Parivar Arth", page_icon="🤖", layout="centered")
    apply_theme()
    touch_session()

    user_id = get_current_user_id()
    if not user_id:
        st.warning("Please sign in to chat with your household financial assistant.")
        st.stop()

    render_header(
        title="Parivar AI Assistant",
        subtitle="Ask questions about your financial projections, shortfall risks & inflation",
        icon="🤖"
    )

    # Privacy Note Banner
    st.markdown(
        f"""
        <div style="background-color: #F8FAFC; border-left: 4px solid {PRIMARY_TEAL}; padding: 10px 14px; border-radius: 6px; font-size: 0.85rem; color: #475569; margin-bottom: 1rem;">
            <strong>Privacy Guarantee:</strong> Your individual transaction items are never sent to external AI servers. 
            All numbers are queried directly from your local session calculations.
        </div>
        """,
        unsafe_allow_html=True
    )

    # Initialize agent in session state
    if "chatbot_agent" not in st.session_state:
        st.session_state["chatbot_agent"] = ParivarChatbotAgent()

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = [
            {
                "role": "assistant",
                "content": (
                    "Namaste! I am your **Parivar Arth Financial Assistant**. "
                    "I can explain your household's risk status, calculate future compounded costs, "
                    "or simulate what-if scenarios. How can I help you today?"
                )
            }
        ]

    agent: ParivarChatbotAgent = st.session_state["chatbot_agent"]

    # Quick Suggestion Buttons
    st.markdown("##### 💡 Suggested Questions:")
    col_q1, col_q2 = st.columns(2)
    with col_q1:
        if st.button("📊 What is my financial health status?", use_container_width=True):
            st.session_state["pending_query"] = "What is my financial health status?"
        if st.button("⚡ What happens if RBI hikes repo rate?", use_container_width=True):
            st.session_state["pending_query"] = "What happens if the repo rate increases?"
    with col_q2:
        if st.button("🔮 Will my family face a shortfall in 12 months?", use_container_width=True):
            st.session_state["pending_query"] = "Will my family face a shortfall in 12 months?"
        if st.button("🏺 What is a sinking fund?", use_container_width=True):
            st.session_state["pending_query"] = "What is a sinking fund?"

    # Render previous messages
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle pending query from suggestion buttons or chat input
    user_prompt = st.session_state.pop("pending_query", None) or st.chat_input("Ask a question about your family finances...")

    if user_prompt:
        # Display user message
        st.session_state["chat_history"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Generate response using agent
        with st.spinner("Analyzing your household plan..."):
            reply = agent.process_message(user_id=user_id, user_message=user_prompt)

        st.session_state["chat_history"].append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.markdown(reply)

    render_footer()


if __name__ == "__main__":
    show_chat_assistant_page()
