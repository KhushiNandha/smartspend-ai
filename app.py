"""
SmartSpend AI - Intelligent Personal Finance Insights Assistant.
Streamlit Main Application Entrypoint.
Tech Stack: Python 3.10+, Streamlit, SQLite, Pandas, Plotly, pdfplumber, fpdf2, Google Gemini API.
"""

import os
import streamlit as st

# Configure wide layout and page metadata
st.set_page_config(
    page_title="SmartSpend AI - Personal Finance Assistant",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load and inject custom CSS
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Import core modules and views
from core.database import init_db, seed_demo_data, clear_session_data
from core.llm_service import get_api_status
from views.landing import render_landing
from views.dashboard import render_dashboard
from views.chat import render_chat
from views.insights import render_insights
from views.goals import render_goals
from views.reports import render_reports

# Initialize database schema
init_db()

# Session State Initialization
if "session_id" not in st.session_state:
    st.session_state["session_id"] = "demo_user"

# Requirement 6: Auto-seed the database on first run (handles Streamlit Cloud disk resets)
if "db_initialized" not in st.session_state:
    # Seeds only if transaction table is empty for this session
    seed_demo_data(session_id=st.session_state["session_id"], force=False)
    st.session_state["db_initialized"] = True

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Landing Page"

# ----------------- SIDEBAR NAVIGATION -----------------
with st.sidebar:
    # Brand Header
    st.markdown("""
    <div class="sidebar-brand">
        <div style="font-size: 2.2rem;">💎</div>
        <div class="brand-text">
            <h2>SmartSpend AI</h2>
            <span>FINANCIAL COPILOT</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Navigation Menu
    pages = [
        "🏠 Landing Page",
        "📊 Dashboard",
        "💬 Chat Assistant",
        "🧠 AI Insights & Forecast",
        "🎯 Goals Tracker",
        "📑 Reports & Imports"
    ]

    # Map current_page to index
    clean_current = st.session_state["current_page"]
    matched_idx = 0
    for idx, p in enumerate(pages):
        if clean_current in p:
            matched_idx = idx
            break

    selected_nav = st.radio("Navigation", pages, index=matched_idx, label_visibility="collapsed")
    st.session_state["current_page"] = selected_nav.split(" ", 1)[1]

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 18px 0;'/>", unsafe_allow_html=True)

    # API Connection Status Badge & Fallback Info
    status = get_api_status()
    st.markdown(f"""
    <div style="margin-bottom: 12px;">
        <span class="badge {status['badge_class']}">{status['mode']}</span>
    </div>
    """, unsafe_allow_html=True)
    st.caption(status["message"])

    # Optional Gemini API Key Override Expander for Reviewer
    with st.expander("🔑 Configure Gemini API Key", expanded=False):
        st.write("Optional: Provide a personal Gemini API Key from Google AI Studio. If left blank, the built-in intelligent rule-based engine runs seamlessly.")
        custom_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=st.session_state.get("custom_gemini_key", ""),
            placeholder="AIzaSy...",
            key="custom_gemini_key_input"
        )
        if st.button("Apply API Key", use_container_width=True):
            st.session_state["custom_gemini_key"] = custom_key
            st.success("API key updated!")
            st.rerun()

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 18px 0;'/>", unsafe_allow_html=True)

    # Quick Demo Reset Actions
    st.markdown("**⚡ Quick Actions**")
    btn_r1, btn_r2 = st.columns(2)
    with btn_r1:
        if st.button("🔄 Reset Demo", use_container_width=True, help="Reload fresh 6-month demo dataset"):
            seed_demo_data(st.session_state["session_id"], force=True)
            st.toast("Reloaded 6-month demo transactions!", icon="🔄")
            st.rerun()
    with btn_r2:
        if st.button("🧹 Clear All", use_container_width=True, help="Clear all records for a clean slate"):
            clear_session_data(st.session_state["session_id"])
            st.toast("All ledger records cleared!", icon="🧹")
            st.rerun()

    # About & Tech Stack Expander
    with st.expander("ℹ️ About & Tech Stack"):
        st.markdown("""
        **Project:** SmartSpend AI  
        **Domain:** Generative AI / FinTech  
        **Evaluation:** Smartbridge Internship  
        
        **Architecture:**
        - **UI:** Streamlit (Custom Theme & CSS)
        - **Database:** SQLite (Auto-seeding, Zero Setup)
        - **Visualizations:** Plotly Interactive
        - **AI Engine:** Google Gemini API (`google-generativeai`)
        - **Fallback:** Offline Financial Heuristics & RegEx
        - **Documents:** `fpdf2` & `pdfplumber`
        """)

# ----------------- VIEW ROUTING -----------------
current = st.session_state["current_page"]

if current == "Landing Page":
    render_landing()
elif current == "Dashboard":
    render_dashboard()
elif current == "Chat Assistant":
    render_chat()
elif current == "AI Insights & Forecast":
    render_insights()
elif current == "Goals Tracker":
    render_goals()
elif current == "Reports & Imports":
    render_reports()
else:
    render_dashboard()
