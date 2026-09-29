"""
SmartSpend AI - Linear Regression Expense Forecasting.
Predicts next 3 months of expenses based on historical monthly spending patterns.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List

def forecast_3_months_expenses(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Fits an Ordinary Least Squares (OLS) linear regression model on monthly expense totals
    and forecasts spending for the upcoming 3 months with confidence bounds.
    """
    if df.empty:
        return {
            "historical": [],
            "forecast": [],
            "trend_direction": "Neutral",
            "monthly_slope": 0.0,
            "projected_quarterly_total": 0.0,
            "status": "Insufficient data"
        }

    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    exp_df = df[df["type"] == "expense"].copy()
    if exp_df.empty:
        return {
            "historical": [],
            "forecast": [],
            "trend_direction": "Neutral",
            "monthly_slope": 0.0,
            "projected_quarterly_total": 0.0,
            "status": "No expense data"
        }

    # Aggregate by month
    exp_df["year_month"] = exp_df["date"].dt.to_period("M")
    monthly = exp_df.groupby("year_month")["amount"].sum().reset_index()
    monthly = monthly.sort_values("year_month")

    historical_points = []
    for _, row in monthly.iterrows():
        p = row["year_month"]
        historical_points.append({
            "month": p.strftime("%b %Y"),
            "period": str(p),
            "amount": round(float(row["amount"]), 2)
        })

    n = len(monthly)
    if n == 0:
        return {"historical": [], "forecast": [], "trend_direction": "Neutral", "monthly_slope": 0.0, "projected_quarterly_total": 0.0, "status": "No data"}

    # If only 1 month of data, repeat with modest projection
    if n == 1:
        base_amt = float(monthly["amount"].iloc[0])
        last_period = monthly["year_month"].iloc[0]
        forecast_points = []
        for i in range(1, 4):
            next_p = last_period + i
            forecast_points.append({
                "month": next_p.strftime("%b %Y"),
                "period": str(next_p),
                "predicted": round(base_amt, 2),
                "lower_bound": round(base_amt * 0.9, 2),
                "upper_bound": round(base_amt * 1.1, 2)
            })
        return {
            "historical": historical_points,
            "forecast": forecast_points,
            "trend_direction": "Stable (Baseline projection)",
            "monthly_slope": 0.0,
            "projected_quarterly_total": round(base_amt * 3, 2),
            "status": "Single-month baseline"
        }

    # Linear Regression: X = 0, 1, ..., n-1; Y = monthly expense
    X = np.arange(n)
    Y = monthly["amount"].values.astype(float)

    # Slope (m) and intercept (c)
    slope, intercept = np.polyfit(X, Y, deg=1)

    # Residual standard deviation for confidence intervals
    fitted_vals = slope * X + intercept
    residuals = Y - fitted_vals
    residual_std = np.std(residuals) if len(residuals) > 1 else (np.mean(Y) * 0.08)
    margin = max(residual_std * 1.2, np.mean(Y) * 0.05)

    last_p = monthly["year_month"].iloc[-1]
    forecast_points = []
    projected_total = 0.0

    for step in range(1, 4):
        future_x = (n - 1) + step
        pred_val = max(100.0, slope * future_x + intercept)
        next_period = last_p + step
        lower = max(0.0, pred_val - margin)
        upper = pred_val + margin

        forecast_points.append({
            "month": next_period.strftime("%b %Y"),
            "period": str(next_period),
            "predicted": round(pred_val, 2),
            "lower_bound": round(lower, 2),
            "upper_bound": round(upper, 2)
        })
        projected_total += pred_val

    if slope > 1000:
        trend = f"Upward trend (spending rising by ~₹{int(slope):,}/month)"
    elif slope < -1000:
        trend = f"Downward trend (spending reducing by ~₹{int(abs(slope)):,}/month)"
    else:
        trend = "Stable / Steady spending trajectory"

    return {
        "historical": historical_points,
        "forecast": forecast_points,
        "trend_direction": trend,
        "monthly_slope": round(float(slope), 2),
        "projected_quarterly_total": round(projected_total, 2),
        "status": "Success"
    }
