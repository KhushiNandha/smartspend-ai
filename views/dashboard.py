"""
SmartSpend AI - Interactive Dashboard View.
KPI scorecards, category doughnut, monthly income vs expense bars,
daily spending trend with 7-day moving average, weekday heatmap, top expenses,
and budget warning alerts.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from core.database import get_transactions_df, get_budgets, seed_demo_data
from core.analytics import (
    calculate_kpis, get_category_breakdown, get_monthly_summary,
    get_daily_spending_trend, get_weekday_spending, format_inr,
    check_budget_alerts
)
from core.charts import (
    plot_category_doughnut, plot_monthly_income_expense_bars,
    plot_daily_spending_trend, plot_weekday_spending_bar
)

def render_dashboard():
    session_id = st.session_state.get("session_id", "demo_user")
    
    # Header & Quick Actions
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.title("📊 Financial Dashboard")
        st.caption("Real-time financial analytics, spending breakdowns, and budget compliance.")
    with header_col2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    # Load All Transactions for Filtering
    all_df = get_transactions_df(session_id)

    # Empty State Handler
    if all_df.empty:
        st.info("ℹ️ Your account has no transactions yet. Choose an option to get started:")
        emp_col1, emp_col2 = st.columns(2)
        with emp_col1:
            if st.button("🚀 Load 6-Month Demo Data", type="primary", use_container_width=True):
                seed_demo_data(session_id, force=True)
                st.session_state["demo_loaded"] = True
                st.rerun()
        with emp_col2:
            if st.button("💬 Log First Expense via Chat", use_container_width=True):
                st.session_state["current_page"] = "Chat Assistant"
                st.rerun()
        return

    # Filters Toolbar
    with st.container():
        f_col1, f_col2, f_col3 = st.columns([2, 2, 2])
        
        with f_col1:
            time_filter = st.selectbox(
                "📅 Date Range",
                ["Last 6 Months (Full)", "Last 90 Days", "Last 30 Days", "All Time", "Custom Range"]
            )
            
        with f_col2:
            categories_list = ["All"] + sorted(all_df["category"].dropna().unique().tolist())
            selected_cat = st.selectbox("🏷️ Filter Category", categories_list)

        with f_col3:
            custom_start, custom_end = None, None
            if time_filter == "Custom Range":
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    custom_start = st.date_input("Start", value=datetime.today() - timedelta(days=90))
                with c_d2:
                    custom_end = st.date_input("End", value=datetime.today())

    # Apply Date Filtering
    today = datetime.today()
    if time_filter == "Last 30 Days":
        start_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        df = all_df[all_df["date"] >= start_date]
    elif time_filter == "Last 90 Days":
        start_date = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        df = all_df[all_df["date"] >= start_date]
    elif time_filter == "Last 6 Months (Full)":
        start_date = (today - timedelta(days=180)).strftime("%Y-%m-%d")
        df = all_df[all_df["date"] >= start_date]
    elif time_filter == "Custom Range" and custom_start and custom_end:
        df = all_df[(all_df["date"] >= str(custom_start)) & (all_df["date"] <= str(custom_end))]
    else:
        df = all_df

    if selected_cat != "All":
        df = df[df["category"] == selected_cat]

    if df.empty:
        st.warning(f"No transactions found for category '{selected_cat}' within the selected date range.")
        return

    # 1. Budget Alerts Check
    budgets = get_budgets(session_id)
    alerts = check_budget_alerts(all_df, budgets)
    if alerts:
        with st.container():
            for alert in alerts:
                if alert["level"] == "exceeded":
                    st.error(alert["message"])
                else:
                    st.warning(alert["message"])

    # 2. KPI Scorecards
    kpis = calculate_kpis(df)
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
    
    with kpi_col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Income</div>
            <div class="metric-value" style="color: #10B981;">{format_inr(kpis['total_income'])}</div>
            <div class="metric-delta delta-positive">MoM: {kpis['mom_income_change_pct']:+0.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Expenses</div>
            <div class="metric-value" style="color: #EF4444;">{format_inr(kpis['total_expense'])}</div>
            <div class="metric-delta {'delta-negative' if kpis['mom_expense_change_pct'] > 0 else 'delta-positive'}">MoM: {kpis['mom_expense_change_pct']:+0.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Net Savings</div>
            <div class="metric-value" style="color: #38BDF8;">{format_inr(kpis['net_savings'])}</div>
            <div class="metric-delta {'delta-positive' if kpis['net_savings'] >= 0 else 'delta-negative'}">{'Surplus' if kpis['net_savings'] >= 0 else 'Deficit'}</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Savings Rate</div>
            <div class="metric-value" style="color: #A855F7;">{kpis['savings_rate']}%</div>
            <div class="metric-delta {'delta-positive' if kpis['savings_rate'] >= 20 else 'delta-neutral'}">Target: > 20%</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_col5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Active Records</div>
            <div class="metric-value" style="color: #F59E0B;">{len(df):,}</div>
            <div class="metric-delta delta-neutral">Transactions</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # 3. Main Visualizations Row
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        cat_df = get_category_breakdown(df, "expense")
        fig_doughnut = plot_category_doughnut(cat_df)
        st.plotly_chart(fig_doughnut, use_container_width=True)

    with chart_col2:
        monthly_df = get_monthly_summary(all_df)
        fig_bars = plot_monthly_income_expense_bars(monthly_df)
        st.plotly_chart(fig_bars, use_container_width=True)

    # 4. Secondary Visualizations Row
    trend_col1, trend_col2 = st.columns([3, 2])
    
    with trend_col1:
        daily_df = get_daily_spending_trend(df)
        fig_trend = plot_daily_spending_trend(daily_df)
        st.plotly_chart(fig_trend, use_container_width=True)

    with trend_col2:
        weekday_df = get_weekday_spending(df)
        fig_weekday = plot_weekday_spending_bar(weekday_df)
        st.plotly_chart(fig_weekday, use_container_width=True)

    # 5. Top 5 Expenses & Recent Transactions
    t_col1, t_col2 = st.columns(2)
    
    with t_col1:
        st.subheader("🔥 Top 5 Largest Expenses")
        top_exp = df[df["type"] == "expense"].sort_values("amount", ascending=False).head(5)
        if not top_exp.empty:
            display_top = top_exp[["date", "description", "category", "amount"]].copy()
            display_top["date"] = display_top["date"].dt.strftime("%d %b %Y")
            display_top["amount"] = display_top["amount"].apply(format_inr)
            display_top.columns = ["Date", "Description", "Category", "Amount"]
            st.dataframe(display_top, use_container_width=True, hide_index=True)
        else:
            st.write("No expense records found.")

    with t_col2:
        st.subheader("⏱️ Recent 5 Transactions")
        recent = df.sort_values("date", ascending=False).head(5)
        if not recent.empty:
            display_recent = recent[["date", "description", "type", "amount"]].copy()
            display_recent["date"] = display_recent["date"].dt.strftime("%d %b %Y")
            display_recent["amount"] = display_recent["amount"].apply(format_inr)
            display_recent.columns = ["Date", "Description", "Type", "Amount"]
            st.dataframe(display_recent, use_container_width=True, hide_index=True)
        else:
            st.write("No transaction records found.")
