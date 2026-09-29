"""
SmartSpend AI - Interactive Plotly Chart Generators.
Features dark-mode aesthetics, responsive layouts, Indian currency tooltips,
and consistent color palettes.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any, List
from core.analytics import format_inr

# Consistent Color Tokens
PALETTE = {
    "primary": "#10B981",    # Emerald
    "accent": "#38BDF8",     # Sky Blue
    "warning": "#F59E0B",    # Amber
    "danger": "#EF4444",     # Red
    "purple": "#8B5CF6",     # Violet
    "pink": "#EC4899",       # Pink
    "indigo": "#6366F1",     # Indigo
    "bg_dark": "#0F172A",
    "card_dark": "#1E293B",
    "text_light": "#F8FAFC",
    "text_muted": "#94A3B8",
    "grid_color": "rgba(255, 255, 255, 0.07)"
}

CATEGORY_COLORS = [
    "#10B981", "#38BDF8", "#F59E0B", "#EC4899", 
    "#8B5CF6", "#14B8A6", "#F97316", "#6366F1", "#84CC16"
]

def default_layout(title: str = "") -> dict:
    """Returns baseline Plotly layout matching the dark dashboard aesthetic."""
    return dict(
        title=dict(text=title, font=dict(family="Plus Jakarta Sans, sans-serif", size=16, color=PALETTE["text_light"])),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color=PALETTE["text_muted"]),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color=PALETTE["text_muted"])
        ),
        hoverlabel=dict(
            bgcolor=PALETTE["card_dark"],
            font_size=12,
            font_family="Plus Jakarta Sans, sans-serif",
            font_color=PALETTE["text_light"]
        )
    )

def plot_category_doughnut(df: pd.DataFrame) -> go.Figure:
    """Renders category spend breakdown as a sleek doughnut chart."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(default_layout("No Expense Data Available"))
        return fig

    custom_text = [f"{format_inr(amt)} ({pct}%)" for amt, pct in zip(df["amount"], df["percentage"])]
    
    fig = go.Figure(data=[go.Pie(
        labels=df["category"],
        values=df["amount"],
        hole=0.58,
        marker=dict(colors=CATEGORY_COLORS[:len(df)], line=dict(color=PALETTE["card_dark"], width=2)),
        textinfo="label+percent",
        customdata=custom_text,
        hovertemplate="<b>%{label}</b><br>Total: %{customdata}<extra></extra>"
    )])
    
    layout = default_layout("Spending by Category")
    layout["showlegend"] = True
    fig.update_layout(**layout)
    return fig

def plot_monthly_income_expense_bars(df: pd.DataFrame) -> go.Figure:
    """Renders grouped bar chart for monthly Income vs Expense."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(default_layout("No Monthly Data"))
        return fig

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df["month"],
        y=df["income"],
        name="Income",
        marker_color=PALETTE["primary"],
        hovertemplate="Income: ₹%{y:,.0f}<extra></extra>",
        marker_line_width=0,
        opacity=0.9
    ))

    fig.add_trace(go.Bar(
        x=df["month"],
        y=df["expense"],
        name="Expense",
        marker_color=PALETTE["danger"],
        hovertemplate="Expense: ₹%{y:,.0f}<extra></extra>",
        marker_line_width=0,
        opacity=0.9
    ))

    layout = default_layout("Monthly Income vs Expense")
    layout["barmode"] = "group"
    layout["xaxis"] = dict(showgrid=False, color=PALETTE["text_muted"])
    layout["yaxis"] = dict(
        showgrid=True, 
        gridcolor=PALETTE["grid_color"], 
        color=PALETTE["text_muted"],
        tickprefix="₹"
    )
    fig.update_layout(**layout)
    return fig

def plot_daily_spending_trend(df: pd.DataFrame) -> go.Figure:
    """Renders daily spending line chart with 7-day rolling average."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(default_layout("No Daily Trend Data"))
        return fig

    fig = go.Figure()

    # Raw daily spending
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["amount"],
        name="Daily Spend",
        mode="markers",
        marker=dict(color=PALETTE["accent"], size=5, opacity=0.6),
        hovertemplate="%{x|%d %b %Y}: ₹%{y:,.0f}<extra></extra>"
    ))

    # 7-day Moving Average
    fig.add_trace(go.Scatter(
        x=df["date"],
        y=df["moving_avg_7d"],
        name="7-Day Moving Avg",
        mode="lines",
        line=dict(color=PALETTE["primary"], width=3),
        hovertemplate="7-Day Avg: ₹%{y:,.0f}<extra></extra>"
    ))

    layout = default_layout("Daily Spending Trend & Moving Average")
    layout["xaxis"] = dict(showgrid=False, color=PALETTE["text_muted"])
    layout["yaxis"] = dict(
        showgrid=True, 
        gridcolor=PALETTE["grid_color"], 
        color=PALETTE["text_muted"],
        tickprefix="₹"
    )
    fig.update_layout(**layout)
    return fig

def plot_weekday_spending_bar(df: pd.DataFrame) -> go.Figure:
    """Renders average spend by day of week."""
    if df.empty:
        fig = go.Figure()
        fig.update_layout(default_layout("No Weekday Data"))
        return fig

    fig = go.Figure(data=[go.Bar(
        x=df["day"],
        y=df["avg_spend"],
        marker_color=[PALETTE["accent"] if d in ["Saturday", "Sunday"] else PALETTE["purple"] for d in df["day"]],
        hovertemplate="<b>%{x}</b><br>Avg Spend: ₹%{y:,.0f}<extra></extra>",
        marker_line_width=0
    )])

    layout = default_layout("Average Spending by Day of Week")
    layout["xaxis"] = dict(showgrid=False, color=PALETTE["text_muted"])
    layout["yaxis"] = dict(
        showgrid=True, 
        gridcolor=PALETTE["grid_color"], 
        color=PALETTE["text_muted"],
        tickprefix="₹"
    )
    fig.update_layout(**layout)
    return fig

def plot_health_gauge(score: int) -> go.Figure:
    """Renders circular gauge for the Financial Health Score (0-100)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'suffix': "/100", 'font': {'size': 32, 'family': "Plus Jakarta Sans", 'color': PALETTE["text_light"]}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': PALETTE["text_muted"]},
            'bar': {'color': PALETTE["primary"], 'thickness': 0.3},
            'bgcolor': "rgba(255,255,255,0.05)",
            'borderwidth': 0,
            'steps': [
                {'range': [0, 50], 'color': 'rgba(239, 68, 68, 0.25)'},
                {'range': [50, 75], 'color': 'rgba(245, 158, 11, 0.25)'},
                {'range': [75, 100], 'color': 'rgba(16, 185, 129, 0.25)'}
            ],
            'threshold': {
                'line': {'color': PALETTE["text_light"], 'width': 3},
                'thickness': 0.8,
                'value': score
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=220,
        margin=dict(l=25, r=25, t=25, b=10)
    )
    return fig

def plot_forecast_chart(forecast_data: Dict[str, Any]) -> go.Figure:
    """Renders historical expense points alongside projected 3-month forecast with confidence area."""
    fig = go.Figure()
    
    hist = forecast_data.get("historical", [])
    fc = forecast_data.get("forecast", [])
    
    if not hist and not fc:
        fig.update_layout(default_layout("No Forecast Data"))
        return fig

    # Historical curve
    if hist:
        hist_x = [h["month"] for h in hist]
        hist_y = [h["amount"] for h in hist]
        fig.add_trace(go.Scatter(
            x=hist_x,
            y=hist_y,
            name="Actual Expenses",
            mode="lines+markers",
            line=dict(color=PALETTE["accent"], width=3),
            marker=dict(size=7),
            hovertemplate="%{x}: ₹%{y:,.0f}<extra></extra>"
        ))

    # Forecast curve
    if fc:
        fc_x = [f["month"] for f in fc]
        fc_y = [f["predicted"] for f in fc]
        fc_upper = [f["upper_bound"] for f in fc]
        fc_lower = [f["lower_bound"] for f in fc]

        # Connect last historical point to first forecast point
        if hist:
            connect_x = [hist[-1]["month"]] + fc_x
            connect_y = [hist[-1]["amount"]] + fc_y
        else:
            connect_x = fc_x
            connect_y = fc_y

        # Upper bound
        fig.add_trace(go.Scatter(
            x=fc_x,
            y=fc_upper,
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            hoverinfo='skip'
        ))

        # Lower bound + fill
        fig.add_trace(go.Scatter(
            x=fc_x,
            y=fc_lower,
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(245, 158, 11, 0.15)',
            name='Confidence Range',
            hoverinfo='skip'
        ))

        # Predicted line
        fig.add_trace(go.Scatter(
            x=connect_x,
            y=connect_y,
            name="Forecast (Projected)",
            mode="lines+markers",
            line=dict(color=PALETTE["warning"], width=3, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
            hovertemplate="Forecast %{x}: ₹%{y:,.0f}<extra></extra>"
        ))

    layout = default_layout("3-Month Expense Forecast (Linear Regression)")
    layout["xaxis"] = dict(showgrid=False, color=PALETTE["text_muted"])
    layout["yaxis"] = dict(
        showgrid=True, 
        gridcolor=PALETTE["grid_color"], 
        color=PALETTE["text_muted"],
        tickprefix="₹"
    )
    fig.update_layout(**layout)
    return fig
