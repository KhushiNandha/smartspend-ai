"""
SmartSpend AI - Landing Page View.
Hero section, 3 feature value propositions, 'Try Demo Account' and 'Start Fresh' onboarding.
"""

import streamlit as st
from core.database import seed_demo_data, clear_session_data

def render_landing():
    # Hero Section
    st.markdown("""
    <div class="hero-container">
        <div style="font-size: 3rem; margin-bottom: 8px;">✨💳📈</div>
        <div class="hero-title">SmartSpend AI</div>
        <div class="hero-tagline">
            Intelligent Personal Finance Insights Assistant powered by Generative AI. 
            Effortlessly track expenses in English or Hinglish, monitor real-time 50/30/20 budget allocations, 
            detect anomalous spending with Z-score models, and forecast quarterly finances.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # CTA Buttons
    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    with col_c2:
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🚀 Try Demo Account", type="primary", use_container_width=True, help="Instantly load 6 months of realistic INR financial records"):
                count = seed_demo_data(session_id=st.session_state["session_id"], force=True)
                st.session_state["current_page"] = "Dashboard"
                st.session_state["demo_loaded"] = True
                st.toast(f"✅ Loaded {count} realistic INR transactions across 6 months!", icon="🎉")
                st.rerun()

        with btn_col2:
            if st.button("🌱 Start Fresh", type="secondary", use_container_width=True, help="Clear database and start with an empty session"):
                clear_session_data(session_id=st.session_state["session_id"])
                st.session_state["current_page"] = "Dashboard"
                st.session_state["demo_loaded"] = False
                st.toast("Clean account initialized. Add your first transaction or import a statement!", icon="✨")
                st.rerun()

    st.markdown("<div style='height: 30px;'></div>", unsafe_allow_html=True)

    # 3 Feature Cards
    f1, f2, f3 = st.columns(3)
    
    with f1:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">💬</div>
            <div class="feature-title">Multilingual Smart NLP</div>
            <div class="feature-desc">
                Log expenses in plain English or natural Hinglish. Single-line or entire paragraphs are parsed into structured transactions instantly.
            </div>
            <div style="margin-top: 14px; font-size: 0.8rem; color: #10B981; font-weight: 600;">
                Try: "Aaj chai pe 20 rupay gaye"
            </div>
        </div>
        """, unsafe_allow_html=True)

    with f2:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Visual Analytics & 50/30/20</div>
            <div class="feature-desc">
                Interactive Plotly charts, category doughnuts, weekday spending heatmaps, and automatic Needs vs Wants vs Savings tracking.
            </div>
            <div style="margin-top: 14px; font-size: 0.8rem; color: #38BDF8; font-weight: 600;">
                Real-time INR Formatting (₹)
            </div>
        </div>
        """, unsafe_allow_html=True)

    with f3:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🧠</div>
            <div class="feature-title">AI Health Audit & Forecasting</div>
            <div class="feature-desc">
                0-100 Financial Health score gauge, statistical Z-score anomaly detector for impulse purchases, and 3-month linear regression expense forecasting.
            </div>
            <div style="margin-top: 14px; font-size: 0.8rem; color: #F59E0B; font-weight: 600;">
                Zero-setup offline fallback mode
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Reviewer Quick Guide Callout
    with st.expander("📌 Quick Reviewer & Evaluator Guide (Smartbridge Internship)", expanded=True):
        st.markdown("""
        - **Instant Evaluation:** Click **"Try Demo Account"** above to immediately populate all 6 months of realistic INR data (Salary, EMIs, Rent, Blinkit, Zomato, SIPs, and deliberate anomalies).
        - **Zero Setup Required:** Works right out of the box! If no Google Gemini API key is configured, the application **automatically uses the offline rule-based financial engine**, ensuring 100% uptime with zero empty screens or errors.
        - **Optional Gemini API Key:** You can optionally provide your own Gemini API Key in the sidebar expander to unlock live Generative AI extraction and conversational chat.
        - **Executive PDF Report:** Head to the **Reports** view to download a monthly PDF statement generated via `fpdf2`.
        """)
