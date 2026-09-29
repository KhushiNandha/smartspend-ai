"""
SmartSpend AI - AI Strategic Insights & Forecast Page.
Renders structured JSON from LLM or Rule-Based Engine as modern UI cards:
- Financial Health Score (Gauge Chart)
- 3-Month Linear Regression Forecast with confidence interval
- 50/30/20 Budget Framework Allocation
- Statistical Z-Score Anomaly Detector
- Tailored Actionable Savings Tips
- Goals Feasibility Assessment
"""

import streamlit as st
import pandas as pd
from core.database import get_transactions_df, get_goals
from core.llm_service import generate_ai_insights
from core.forecasting import forecast_3_months_expenses
from core.charts import plot_health_gauge, plot_forecast_chart
from core.analytics import format_inr
from core.prompts import FINANCIAL_DISCLAIMER

def render_insights():
    session_id = st.session_state.get("session_id", "demo_user")
    df = get_transactions_df(session_id)
    goals = get_goals(session_id)

    st.title("🧠 AI Financial Insights & Forecasting")
    st.caption("Comprehensive financial health audit, Z-score spending anomaly detection, and quarterly forecasting.")

    if df.empty:
        st.info("No transaction data available to generate insights. Please seed demo data or record expenses first.")
        return

    with st.spinner("Synthesizing AI financial audit and econometric models..."):
        insights_data = generate_ai_insights(df, goals)
        forecast_data = forecast_3_months_expenses(df)

    # 1. Top Section: Health Score Gauge & Executive Summary
    row1_c1, row1_c2 = st.columns([1, 2])
    
    with row1_c1:
        st.subheader("Financial Health Score")
        score = int(insights_data.get("health_score", 75))
        fig_gauge = plot_health_gauge(score)
        st.plotly_chart(fig_gauge, use_container_width=True)

    with row1_c2:
        st.subheader("Executive Audit Summary")
        grade = insights_data.get("health_grade", "Good")
        badge_style = "badge-ai" if score >= 75 else ("badge-fallback" if score >= 50 else "badge-alert")
        
        st.markdown(f"""
        <div style="margin-bottom: 12px;">
            <span class="badge {badge_style}">Rating: {grade} ({score}/100)</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="insight-card insight-card-info">
            <div style="font-size: 1.05rem; line-height: 1.6; color: #F1F5F9;">
                {insights_data.get("executive_summary", "")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 24px 0;'/>", unsafe_allow_html=True)

    # 2. 3-Month Linear Regression Forecast
    st.subheader("📈 3-Month Expense Forecast (Linear Regression)")
    f_chart_col, f_stats_col = st.columns([2, 1])
    
    with f_chart_col:
        fig_forecast = plot_forecast_chart(forecast_data)
        st.plotly_chart(fig_forecast, use_container_width=True)

    with f_stats_col:
        st.markdown("""
        <div class="insight-card">
            <div style="font-size: 0.85rem; color: #94A3B8; text-transform: uppercase; font-weight: 600;">Forecast Trajectory</div>
        """, unsafe_allow_html=True)
        
        trend = forecast_data.get("trend_direction", "Stable")
        proj_q = forecast_data.get("projected_quarterly_total", 0.0)
        
        st.markdown(f"**Trajectory:** {trend}")
        st.markdown(f"**Projected Q4 Expenses:** {format_inr(proj_q)}")
        
        fc_pts = forecast_data.get("forecast", [])
        if fc_pts:
            st.markdown("**Predicted Monthly Run-rate:**")
            for pt in fc_pts:
                st.markdown(f"- **{pt['month']}:** {format_inr(pt['predicted'])} _(Range: {format_inr(pt['lower_bound'])} - {format_inr(pt['upper_bound'])})_")
                
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 24px 0;'/>", unsafe_allow_html=True)

    # 3. 50/30/20 Budget Plan Breakdown
    st.subheader("⚖️ 50/30/20 Rule Budget Allocation")
    b_plan = insights_data.get("budget_plan", {})
    
    bp_c1, bp_c2, bp_c3 = st.columns(3)
    
    with bp_c1:
        st.markdown(f"""
        <div class="insight-card insight-card-info">
            <div style="font-size: 1.1rem; font-weight: 700; color: #38BDF8; margin-bottom: 6px;">🏠 Needs (50% Target)</div>
            <div style="font-size: 0.92rem; color: #CBD5E1; line-height: 1.5;">
                {b_plan.get("needs_advice", "Keep rent, EMIs, utilities, and groceries under 50% of net income.")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with bp_c2:
        st.markdown(f"""
        <div class="insight-card insight-card-warning">
            <div style="font-size: 1.1rem; font-weight: 700; color: #F59E0B; margin-bottom: 6px;">🛍️ Wants (30% Target)</div>
            <div style="font-size: 0.92rem; color: #CBD5E1; line-height: 1.5;">
                {b_plan.get("wants_advice", "Cap dining, shopping, and entertainment to 30% of net income.")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with bp_c3:
        st.markdown(f"""
        <div class="insight-card insight-card-success">
            <div style="font-size: 1.1rem; font-weight: 700; color: #10B981; margin-bottom: 6px;">💰 Savings (20% Target)</div>
            <div style="font-size: 0.92rem; color: #CBD5E1; line-height: 1.5;">
                {b_plan.get("savings_advice", "Direct at least 20% into disciplined mutual fund SIPs and emergency reserves.")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # 4. Statistical Z-Score Anomalies & Budget Alerts
    a_col1, a_col2 = st.columns(2)
    
    with a_col1:
        st.subheader("🚨 Z-Score Spending Anomalies")
        anomalies = insights_data.get("anomalies", [])
        if anomalies:
            for anom in anomalies:
                st.markdown(f"""
                <div class="insight-card insight-card-danger">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-weight: 700; color: #F87171;">{anom.get('description', 'High Expense')}</span>
                        <span class="badge badge-alert">{format_inr(anom.get('amount', 0))}</span>
                    </div>
                    <div style="font-size: 0.88rem; color: #CBD5E1;">
                        {anom.get('insight', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No statistical spending anomalies detected in recent cycles.")

    with a_col2:
        st.subheader("🔔 Budget Alerts & Leakages")
        alerts = insights_data.get("alerts", [])
        if alerts:
            for al in alerts:
                st.markdown(f"""
                <div class="insight-card insight-card-warning">
                    <div style="color: #FBBF24; font-size: 0.92rem; font-weight: 500;">
                        ⚠️ {al}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("All spending categories are operating within prescribed limits.")

    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

    # 5. Targeted Savings Tips
    st.subheader("💡 Strategic Savings Recommendations")
    tips = insights_data.get("savings_tips", [])
    if tips:
        for idx, tip in enumerate(tips):
            st.markdown(f"""
            <div class="insight-card insight-card-success">
                <div style="display: flex; gap: 12px; align-items: flex-start;">
                    <div style="font-size: 1.2rem;">💎</div>
                    <div style="font-size: 0.92rem; color: #E2E8F0; line-height: 1.5;">
                        <strong>Action Item {idx+1}:</strong> {tip}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 6. Goals Feasibility
    feasibility = insights_data.get("goal_feasibility", [])
    if feasibility:
        st.subheader("🎯 Savings Goals Feasibility Audit")
        for gf in feasibility:
            status_color = "#10B981" if gf.get("is_feasible") else "#F59E0B"
            st.markdown(f"""
            <div class="insight-card">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="font-weight: 700; color: #F8FAFC;">{gf.get('goal_name')}</span>
                    <span style="font-weight: 600; color: {status_color};">
                        {'✅ On Track' if gf.get('is_feasible') else '⚠️ Re-adjustment Suggested'}
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: #94A3B8;">
                    {gf.get('verdict')}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Footer Disclaimer
    st.markdown(f"""
    <div class="disclaimer-box">
        ⚖️ <strong>Regulatory Notice:</strong> {FINANCIAL_DISCLAIMER}
    </div>
    """, unsafe_allow_html=True)
