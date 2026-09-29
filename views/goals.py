"""
SmartSpend AI - Financial Goals Tracker.
Set savings targets, track progress, compute monthly required savings,
and view automated AI feasibility commentary.
"""

import streamlit as st
from datetime import datetime
from core.database import get_goals, add_goal, update_goal, delete_goal, get_transactions_df
from core.analytics import calculate_kpis, format_inr
from core.prompts import FINANCIAL_DISCLAIMER

def render_goals():
    session_id = st.session_state.get("session_id", "demo_user")
    goals = get_goals(session_id)
    df = get_transactions_df(session_id)
    kpis = calculate_kpis(df)
    monthly_surplus = max(0.0, kpis["net_savings"] / 6.0) if kpis["net_savings"] > 0 else 0.0

    st.title("🎯 Savings & Financial Goals")
    st.caption("Plan life milestones, track target deadlines, and calculate required monthly contributions.")

    # Top KPI Banner
    g_kpi1, g_kpi2, g_kpi3 = st.columns(3)
    total_target = sum(g["target_amount"] for g in goals)
    total_saved = sum(g["current_amount"] for g in goals)
    overall_progress = round((total_saved / total_target * 100), 1) if total_target > 0 else 0.0

    with g_kpi1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Goals Target</div>
            <div class="metric-value" style="color: #38BDF8;">{format_inr(total_target)}</div>
            <div class="metric-delta delta-neutral">{len(goals)} Active Goals</div>
        </div>
        """, unsafe_allow_html=True)

    with g_kpi2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Accumulated</div>
            <div class="metric-value" style="color: #10B981;">{format_inr(total_saved)}</div>
            <div class="metric-delta delta-positive">{overall_progress}% Achieved</div>
        </div>
        """, unsafe_allow_html=True)

    with g_kpi3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Est. Monthly Surplus</div>
            <div class="metric-value" style="color: #A855F7;">{format_inr(monthly_surplus)}</div>
            <div class="metric-delta delta-neutral">Available for allocation</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # Goal Creation Form (Expander)
    with st.expander("➕ Create a New Savings Goal", expanded=False):
        with st.form("create_goal_form", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                title = st.text_input("Goal Title", placeholder="e.g., Emergency Reserve, New Car, Goa Vacation")
                target_amount = st.number_input("Target Amount (₹)", min_value=1000.0, step=5000.0, value=50000.0)
                category = st.selectbox("Category", ["Safety & Emergency", "Travel & Lifestyle", "Gadgets & Tech", "Vehicle", "Home & Family", "Education"])
            with f_col2:
                current_amount = st.number_input("Currently Saved (₹)", min_value=0.0, step=1000.0, value=5000.0)
                target_date = st.date_input("Target Completion Date")
                notes = st.text_input("Notes / Strategy", placeholder="Optional purpose details")

            submit_goal = st.form_submit_button("Create Savings Goal", type="primary", use_container_width=True)
            if submit_goal:
                if not title.strip():
                    st.error("Please provide a title for your goal.")
                else:
                    add_goal(session_id, title.strip(), target_amount, current_amount, str(target_date), category)
                    st.success(f"Goal '{title}' created successfully!")
                    st.rerun()

    # Active Goals List
    st.subheader("Your Savings Goals")
    if not goals:
        st.info("No active savings goals found. Create your first goal using the form above!")
        return

    today = datetime.today().date()

    for g in goals:
        target = float(g["target_amount"])
        current = float(g["current_amount"])
        pct = min(100.0, round((current / target * 100), 1)) if target > 0 else 0.0
        remaining = max(0.0, target - current)

        try:
            target_dt = datetime.strptime(g["target_date"], "%Y-%m-%d").date()
            days_left = (target_dt - today).days
            months_left = max(1, round(days_left / 30.0))
        except Exception:
            days_left = 180
            months_left = 6

        req_monthly = remaining / months_left if months_left > 0 else remaining
        is_feasible = monthly_surplus >= req_monthly

        with st.container():
            st.markdown(f"""
            <div class="insight-card" style="margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <div>
                        <span style="font-size: 1.15rem; font-weight: 700; color: #F8FAFC;">{g['title']}</span>
                        <span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38BDF8; margin-left: 8px;">{g.get('category', 'Savings')}</span>
                    </div>
                    <div style="text-align: right;">
                        <span style="font-size: 1.1rem; font-weight: 700; color: #10B981;">{format_inr(current)}</span>
                        <span style="color: #94A3B8; font-size: 0.9rem;"> / {format_inr(target)}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Streamlit progress bar
            st.progress(pct / 100.0)

            # Details & Metrics
            m_col1, m_col2, m_col3, m_col4 = st.columns([2, 2, 2, 2])
            with m_col1:
                st.caption(f"**Target Date:** {g['target_date']} ({days_left} days left)")
            with m_col2:
                st.caption(f"**Remaining:** {format_inr(remaining)}")
            with m_col3:
                st.caption(f"**Required:** {format_inr(req_monthly)} / month")
            with m_col4:
                if is_feasible:
                    st.markdown("<span style='color: #10B981; font-weight: 600; font-size: 0.85rem;'>✅ Achievable with surplus</span>", unsafe_allow_html=True)
                else:
                    st.markdown("<span style='color: #F59E0B; font-weight: 600; font-size: 0.85rem;'>⚠️ Requires extra savings</span>", unsafe_allow_html=True)

            # Quick Update / Delete
            with st.expander("⚙️ Manage Goal", expanded=False):
                u_col1, u_col2 = st.columns([3, 1])
                with u_col1:
                    new_curr = st.number_input(f"Update Saved Amount for '{g['title']}' (₹)", value=current, step=1000.0, key=f"curr_{g['id']}")
                    if st.button("Update Amount", key=f"btn_up_{g['id']}"):
                        update_goal(g["id"], session_id, new_curr)
                        st.success("Goal progress updated!")
                        st.rerun()
                with u_col2:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Delete", key=f"btn_del_{g['id']}", type="secondary"):
                        delete_goal(g["id"], session_id)
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="disclaimer-box">
        ⚖️ {FINANCIAL_DISCLAIMER}
    </div>
    """, unsafe_allow_html=True)
