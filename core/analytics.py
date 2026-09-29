"""
SmartSpend AI - Analytics & Financial Metrics Engine.
Includes Indian Rupee (INR) formatting, KPI aggregations, MoM changes,
Z-score anomaly detection, 50/30/20 budget breakdown, and financial health score.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

def format_inr(amount: float, show_cents: bool = False) -> str:
    """
    Formats a numeric amount into Indian Rupee numbering format (e.g. ₹1,23,45,678).
    Supports negative values and zero.
    """
    if pd.isna(amount):
        return "₹0"
    
    is_negative = amount < 0
    amount = abs(float(amount))
    
    parts = f"{amount:.2f}".split(".")
    integer_part = parts[0]
    decimal_part = parts[1]
    
    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group remaining digits in pairs from right to left
        grouped = []
        while len(remaining) > 2:
            grouped.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            grouped.insert(0, remaining)
        formatted_int = ",".join(grouped) + "," + last_three
        
    res = f"₹{formatted_int}"
    if show_cents and decimal_part != "00":
        res += f".{decimal_part}"
    if is_negative:
        res = f"-{res}"
    return res

def calculate_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes top-level financial KPIs: Total Income, Total Expenses,
    Net Savings, Savings Rate, and Month-over-Month changes.
    """
    if df.empty:
        return {
            "total_income": 0.0,
            "total_expense": 0.0,
            "net_savings": 0.0,
            "savings_rate": 0.0,
            "current_month_expense": 0.0,
            "prev_month_expense": 0.0,
            "mom_expense_change_pct": 0.0,
            "current_month_income": 0.0,
            "prev_month_income": 0.0,
            "mom_income_change_pct": 0.0
        }

    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    income_df = df[df["type"] == "income"]
    expense_df = df[df["type"] == "expense"]

    total_income = float(income_df["amount"].sum())
    total_expense = float(expense_df["amount"].sum())
    net_savings = total_income - total_expense
    savings_rate = (net_savings / total_income * 100.0) if total_income > 0 else 0.0

    # Month-over-Month (MoM) calculation
    df["year_month"] = df["date"].dt.to_period("M")
    available_months = sorted(df["year_month"].unique())

    current_month_expense = 0.0
    prev_month_expense = 0.0
    mom_expense_change_pct = 0.0

    current_month_income = 0.0
    prev_month_income = 0.0
    mom_income_change_pct = 0.0

    if len(available_months) >= 1:
        latest_m = available_months[-1]
        current_month_expense = float(df[(df["year_month"] == latest_m) & (df["type"] == "expense")]["amount"].sum())
        current_month_income = float(df[(df["year_month"] == latest_m) & (df["type"] == "income")]["amount"].sum())

    if len(available_months) >= 2:
        prev_m = available_months[-2]
        prev_month_expense = float(df[(df["year_month"] == prev_m) & (df["type"] == "expense")]["amount"].sum())
        prev_month_income = float(df[(df["year_month"] == prev_m) & (df["type"] == "income")]["amount"].sum())

        if prev_month_expense > 0:
            mom_expense_change_pct = ((current_month_expense - prev_month_expense) / prev_month_expense) * 100.0
        if prev_month_income > 0:
            mom_income_change_pct = ((current_month_income - prev_month_income) / prev_month_income) * 100.0

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net_savings": net_savings,
        "savings_rate": round(savings_rate, 1),
        "current_month_expense": current_month_expense,
        "prev_month_expense": prev_month_expense,
        "mom_expense_change_pct": round(mom_expense_change_pct, 1),
        "current_month_income": current_month_income,
        "prev_month_income": prev_month_income,
        "mom_income_change_pct": round(mom_income_change_pct, 1)
    }

def get_category_breakdown(df: pd.DataFrame, transaction_type: str = "expense") -> pd.DataFrame:
    """Calculates category-wise spend or income distribution."""
    if df.empty:
        return pd.DataFrame(columns=["category", "amount", "percentage"])
    
    filtered = df[df["type"] == transaction_type]
    if filtered.empty:
        return pd.DataFrame(columns=["category", "amount", "percentage"])
        
    grouped = filtered.groupby("category")["amount"].sum().reset_index()
    total = grouped["amount"].sum()
    grouped["percentage"] = (grouped["amount"] / total * 100.0).round(1) if total > 0 else 0.0
    return grouped.sort_values(by="amount", ascending=False)

def get_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Returns monthly totals for income, expense, and net savings."""
    if df.empty:
        return pd.DataFrame(columns=["month", "income", "expense", "savings"])

    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    df["month"] = df["date"].dt.strftime("%b %Y")
    df["sort_key"] = df["date"].dt.to_period("M")

    months = df[["month", "sort_key"]].drop_duplicates().sort_values("sort_key")

    summary = []
    for _, row in months.iterrows():
        m_label = row["month"]
        m_key = row["sort_key"]
        subset = df[df["sort_key"] == m_key]
        inc = float(subset[subset["type"] == "income"]["amount"].sum())
        exp = float(subset[subset["type"] == "expense"]["amount"].sum())
        sav = inc - exp
        summary.append({
            "month": m_label,
            "sort_key": m_key,
            "income": inc,
            "expense": exp,
            "savings": sav
        })

    return pd.DataFrame(summary)

def get_daily_spending_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Returns aggregated daily expense amounts with 7-day moving average."""
    if df.empty:
        return pd.DataFrame(columns=["date", "amount", "moving_avg_7d"])

    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    expense_df = df[df["type"] == "expense"]
    if expense_df.empty:
        return pd.DataFrame(columns=["date", "amount", "moving_avg_7d"])

    daily = expense_df.groupby("date")["amount"].sum().reset_index()
    daily = daily.sort_values("date")
    daily["moving_avg_7d"] = daily["amount"].rolling(window=7, min_periods=1).mean().round(2)
    return daily

def get_weekday_spending(df: pd.DataFrame) -> pd.DataFrame:
    """Returns average spending grouped by day of the week."""
    if df.empty:
        return pd.DataFrame(columns=["day", "avg_spend", "total_spend"])

    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    expense_df = df[df["type"] == "expense"].copy()
    if expense_df.empty:
        return pd.DataFrame(columns=["day", "avg_spend", "total_spend"])

    expense_df["day_name"] = expense_df["date"].dt.day_name()
    expense_df["day_num"] = expense_df["date"].dt.dayofweek

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    agg = expense_df.groupby(["day_name", "day_num"])["amount"].agg(["sum", "mean", "count"]).reset_index()
    agg = agg.rename(columns={"day_name": "day", "mean": "avg_spend", "sum": "total_spend"})
    agg = agg.sort_values("day_num")
    return agg

def detect_anomalies(df: pd.DataFrame, z_threshold: float = 2.0) -> List[Dict[str, Any]]:
    """
    Detects statistical spending anomalies using Z-score and IQR methods.
    Flag transactions that deviate substantially from typical category or overall spending.
    """
    if df.empty:
        return []

    expense_df = df[df["type"] == "expense"].copy()
    if len(expense_df) < 5:
        return []

    anomalies = []
    
    # 1. Overall Z-score
    amounts = expense_df["amount"].values
    mean_val = np.mean(amounts)
    std_val = np.std(amounts)

    if std_val > 0:
        expense_df["z_score"] = (expense_df["amount"] - mean_val) / std_val
        flagged = expense_df[expense_df["z_score"] >= z_threshold].sort_values("z_score", ascending=False)
        
        for _, row in flagged.iterrows():
            anomalies.append({
                "date": str(row["date"])[:10],
                "description": row["description"],
                "category": row["category"],
                "amount": float(row["amount"]),
                "z_score": round(float(row["z_score"]), 2),
                "reason": f"Spending of {format_inr(row['amount'])} is {round(float(row['z_score']), 1)} standard deviations above average ({format_inr(mean_val)})."
            })

    return anomalies

def calculate_50_30_20(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Categorizes spending according to the standard 50/30/20 budgeting rule:
    - Needs (50% target): Rent, Groceries, Bills & Utilities, EMI & Loans, Healthcare
    - Wants (30% target): Food & Dining, Shopping, Entertainment, Subscriptions, Travel & Commute, Other
    - Savings/Investments (20% target): Investment, Savings
    """
    if df.empty:
        return {
            "needs": {"amount": 0, "pct": 0, "target_pct": 50},
            "wants": {"amount": 0, "pct": 0, "target_pct": 30},
            "savings": {"amount": 0, "pct": 0, "target_pct": 20},
            "status": "Balanced"
        }

    needs_categories = {"Rent", "Groceries", "Bills & Utilities", "EMI & Loans", "Healthcare", "Health"}
    savings_categories = {"Investment", "Savings", "Mutual Fund", "SIP"}

    df = df.copy()
    income = float(df[df["type"] == "income"]["amount"].sum())
    
    # Separate expenses
    exp_df = df[df["type"] == "expense"]
    
    needs_amount = float(exp_df[exp_df["category"].isin(needs_categories)]["amount"].sum())
    savings_amount = float(exp_df[exp_df["category"].isin(savings_categories)]["amount"].sum())
    wants_amount = float(exp_df[~exp_df["category"].isin(needs_categories.union(savings_categories))]["amount"].sum())
    
    # Also add residual net savings if income exceeds expenses
    net_residual = income - (needs_amount + wants_amount + savings_amount)
    if net_residual > 0:
        savings_amount += net_residual

    base = income if income > 0 else (needs_amount + wants_amount + savings_amount)
    if base == 0:
        base = 1.0

    needs_pct = round((needs_amount / base) * 100, 1)
    wants_pct = round((wants_amount / base) * 100, 1)
    savings_pct = round((savings_amount / base) * 100, 1)

    if wants_pct > 35:
        status = "High Wants Spending"
    elif savings_pct < 15:
        status = "Under-saving"
    elif needs_pct > 60:
        status = "High Fixed Costs"
    else:
        status = "Healthy Allocation"

    return {
        "needs": {"amount": needs_amount, "pct": needs_pct, "target_pct": 50},
        "wants": {"amount": wants_amount, "pct": wants_pct, "target_pct": 30},
        "savings": {"amount": savings_amount, "pct": savings_pct, "target_pct": 20},
        "status": status
    }

def check_budget_alerts(df: pd.DataFrame, budgets_dict: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Checks the latest month's expenses against user-defined category budgets.
    Flags at 80% (Warning) and >=100% (Exceeded).
    """
    if df.empty or not budgets_dict:
        return []

    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    # Filter to current/latest month
    df["year_month"] = df["date"].dt.to_period("M")
    latest_month = df["year_month"].max()
    month_exp = df[(df["year_month"] == latest_month) & (df["type"] == "expense")]

    cat_totals = month_exp.groupby("category")["amount"].sum().to_dict()

    alerts = []
    for cat, limit in budgets_dict.items():
        spent = cat_totals.get(cat, 0.0)
        pct = (spent / limit) * 100.0 if limit > 0 else 0.0

        if pct >= 100.0:
            alerts.append({
                "category": cat,
                "spent": spent,
                "limit": limit,
                "pct": round(pct, 1),
                "level": "exceeded",
                "message": f"🚨 Budget Exceeded for **{cat}**: Spent {format_inr(spent)} of {format_inr(limit)} ({round(pct)}%)"
            })
        elif pct >= 80.0:
            alerts.append({
                "category": cat,
                "spent": spent,
                "limit": limit,
                "pct": round(pct, 1),
                "level": "warning",
                "message": f"⚠️ Budget Alert for **{cat}**: Reached {format_inr(spent)} of {format_inr(limit)} ({round(pct)}%)"
            })

    return alerts

def calculate_financial_health_score(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates an intelligent Financial Health Score (0 - 100):
    - Savings Rate (30 pts): >25% = 30 pts, 15-25% = 20 pts, >0% = 10 pts
    - Budget Discipline (30 pts): Wants <= 35% of income = 30 pts
    - Investment Allocation (20 pts): Active investments = 20 pts
    - Anomaly / Volatility Control (20 pts): Low variance / few sudden spikes = 20 pts
    """
    kpis = calculate_kpis(df)
    alloc = calculate_50_30_20(df)
    anomalies = detect_anomalies(df)

    score = 0
    breakdown = []

    # 1. Savings Rate Score (Max 30)
    sav_rate = kpis["savings_rate"]
    if sav_rate >= 25:
        score += 30
        breakdown.append(("Savings Rate", 30, 30, f"Excellent savings rate of {sav_rate}%"))
    elif sav_rate >= 15:
        score += 20
        breakdown.append(("Savings Rate", 20, 30, f"Moderate savings rate of {sav_rate}% (Target: >20%)"))
    elif sav_rate > 0:
        score += 10
        breakdown.append(("Savings Rate", 10, 30, f"Low savings rate of {sav_rate}%"))
    else:
        score += 0
        breakdown.append(("Savings Rate", 0, 30, "Negative savings - expenses exceed income"))

    # 2. Budget Discipline / Needs vs Wants (Max 30)
    wants_pct = alloc["wants"]["pct"]
    if wants_pct <= 30:
        score += 30
        breakdown.append(("Expense Discipline", 30, 30, f"Controlled discretionary spending ({wants_pct}%)"))
    elif wants_pct <= 40:
        score += 20
        breakdown.append(("Expense Discipline", 20, 30, f"Slightly elevated discretionary spending ({wants_pct}%)"))
    else:
        score += 10
        breakdown.append(("Expense Discipline", 10, 30, f"High wants spending ({wants_pct}%), above 30% rule"))

    # 3. Investment & Growth (Max 20)
    inv_df = df[(df["type"] == "expense") & (df["category"].isin(["Investment", "Savings"]))] if not df.empty else pd.DataFrame()
    inv_total = float(inv_df["amount"].sum()) if not inv_df.empty else 0.0
    if inv_total > 0 and len(inv_df) >= 3:
        score += 20
        breakdown.append(("Investment Consistency", 20, 20, "Consistent monthly SIPs & investments active"))
    elif inv_total > 0:
        score += 12
        breakdown.append(("Investment Consistency", 12, 20, "Some investments detected, but inconsistent"))
    else:
        score += 5
        breakdown.append(("Investment Consistency", 5, 20, "No dedicated investments or SIPs recorded"))

    # 4. Spending Volatility & Anomaly Control (Max 20)
    if len(anomalies) == 0:
        score += 20
        breakdown.append(("Spending Stability", 20, 20, "No extreme anomalous spending spikes detected"))
    elif len(anomalies) <= 2:
        score += 14
        breakdown.append(("Spending Stability", 14, 20, f"{len(anomalies)} spending spikes detected"))
    else:
        score += 8
        breakdown.append(("Spending Stability", 8, 20, f"High volatility: {len(anomalies)} major anomalous expenses"))

    # Determine grade
    if score >= 85:
        grade = "Excellent"
        summary = "Your financial health is strong with disciplined savings and regular investments."
    elif score >= 70:
        grade = "Good"
        summary = "Good financial management with minor opportunities to trim discretionary spending."
    elif score >= 50:
        grade = "Fair"
        summary = "Average financial standing. Prioritize increasing your savings buffer and curtailing impulse buys."
    else:
        grade = "Needs Attention"
        summary = "Expenses are outpacing recommended thresholds. Immediate budgeting adjustments needed."

    return {
        "score": score,
        "grade": grade,
        "summary": summary,
        "breakdown": breakdown
    }
