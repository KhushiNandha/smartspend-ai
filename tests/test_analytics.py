"""
Unit tests for SmartSpend AI analytics, metrics, forecasting, and INR formatting.
"""

import pytest
import pandas as pd
from core.analytics import (
    format_inr, calculate_kpis, get_category_breakdown,
    detect_anomalies, calculate_50_30_20, calculate_financial_health_score
)
from core.forecasting import forecast_3_months_expenses

def test_format_inr():
    assert format_inr(0) == "₹0"
    assert format_inr(450) == "₹450"
    assert format_inr(1200) == "₹1,200"
    assert format_inr(85000) == "₹85,000"
    assert format_inr(150000) == "₹1,50,000"
    assert format_inr(10000000) == "₹1,00,00,000"
    assert format_inr(-4500) == "-₹4,500"

def test_calculate_kpis():
    data = [
        {"date": "2026-08-01", "type": "income", "amount": 80000.0},
        {"date": "2026-08-05", "type": "expense", "amount": 30000.0},
        {"date": "2026-09-01", "type": "income", "amount": 90000.0},
        {"date": "2026-09-05", "type": "expense", "amount": 35000.0}
    ]
    df = pd.DataFrame(data)
    kpis = calculate_kpis(df)
    
    assert kpis["total_income"] == 170000.0
    assert kpis["total_expense"] == 65000.0
    assert kpis["net_savings"] == 105000.0
    assert kpis["savings_rate"] > 0
    assert kpis["current_month_expense"] == 35000.0
    assert kpis["prev_month_expense"] == 30000.0

def test_category_breakdown():
    data = [
        {"type": "expense", "category": "Food & Dining", "amount": 5000.0},
        {"type": "expense", "category": "Rent", "amount": 20000.0},
        {"type": "expense", "category": "Food & Dining", "amount": 3000.0}
    ]
    df = pd.DataFrame(data)
    breakdown = get_category_breakdown(df)
    
    assert len(breakdown) == 2
    top = breakdown.iloc[0]
    assert top["category"] == "Rent"
    assert top["amount"] == 20000.0
    assert top["percentage"] == 71.4

def test_detect_anomalies_z_score():
    # 20 normal expenses and 1 massive outlier
    normal = [{"date": "2026-08-01", "description": "Normal meal", "category": "Food & Dining", "type": "expense", "amount": 400.0} for _ in range(25)]
    spike = [{"date": "2026-08-15", "description": "Luxury TV", "category": "Shopping", "type": "expense", "amount": 85000.0}]
    df = pd.DataFrame(normal + spike)
    
    anomalies = detect_anomalies(df, z_threshold=2.0)
    assert len(anomalies) >= 1
    assert anomalies[0]["amount"] == 85000.0
    assert "Luxury TV" in anomalies[0]["description"]

def test_calculate_50_30_20():
    data = [
        {"type": "income", "category": "Salary", "amount": 100000.0},
        {"type": "expense", "category": "Rent", "amount": 35000.0}, # Needs
        {"type": "expense", "category": "Groceries", "amount": 15000.0}, # Needs
        {"type": "expense", "category": "Food & Dining", "amount": 20000.0}, # Wants
        {"type": "expense", "category": "Investment", "amount": 20000.0} # Savings
    ]
    df = pd.DataFrame(data)
    alloc = calculate_50_30_20(df)
    
    assert alloc["needs"]["pct"] == 50.0
    assert alloc["wants"]["pct"] == 20.0
    assert alloc["savings"]["pct"] == 30.0

def test_forecast_3_months():
    data = [
        {"date": "2026-05-15", "type": "expense", "amount": 40000.0},
        {"date": "2026-06-15", "type": "expense", "amount": 42000.0},
        {"date": "2026-07-15", "type": "expense", "amount": 44000.0},
        {"date": "2026-08-15", "type": "expense", "amount": 46000.0}
    ]
    df = pd.DataFrame(data)
    result = forecast_3_months_expenses(df)
    
    assert len(result["forecast"]) == 3
    assert result["projected_quarterly_total"] > 0
    assert "Upward" in result["trend_direction"]
