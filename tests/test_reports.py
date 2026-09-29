"""
Unit tests for PDF report compilation, CSV export, and rule-based chat advisory.
"""

import pytest
import pandas as pd
from core.report_generator import generate_pdf_report, export_transactions_csv
from core.fallback import generate_chat_response_rule_based, generate_insights_rule_based
from core.prompts import FINANCIAL_DISCLAIMER

def test_chat_rule_based_chips():
    data = [
        {"date": "2026-09-01", "type": "income", "amount": 85000.0, "category": "Salary", "description": "TechCorp"},
        {"date": "2026-09-05", "type": "expense", "amount": 22000.0, "category": "Rent", "description": "Apartment"},
        {"date": "2026-09-10", "type": "expense", "amount": 14000.0, "category": "Food & Dining", "description": "Dining & Zomato"}
    ]
    df = pd.DataFrame(data)

    # 1. Overspending
    ans1 = generate_chat_response_rule_based("Where am I overspending?", df)
    assert "Rent" in ans1 or "Food & Dining" in ans1
    assert FINANCIAL_DISCLAIMER in ans1

    # 2. Afford 60k phone
    ans2 = generate_chat_response_rule_based("Can I afford a ₹60,000 phone?", df)
    assert "60,000" in ans2 or "afford" in ans2.lower()
    assert FINANCIAL_DISCLAIMER in ans2

    # 3. Save 1 lakh
    ans3 = generate_chat_response_rule_based("How do I save ₹1 lakh in 6 months?", df)
    assert "16,667" in ans3 or "1,00,000" in ans3
    assert FINANCIAL_DISCLAIMER in ans3

    # 4. Budget plan
    ans4 = generate_chat_response_rule_based("Give me a budget plan", df)
    assert "50/30/20" in ans4
    assert FINANCIAL_DISCLAIMER in ans4

def test_pdf_report_compilation():
    data = [
        {"date": "2026-09-01", "type": "income", "amount": 88000.0, "category": "Salary", "description": "TechCorp Salary"},
        {"date": "2026-09-05", "type": "expense", "amount": 23500.0, "category": "Rent", "description": "House Rent"},
        {"date": "2026-09-12", "type": "expense", "amount": 4500.0, "category": "Groceries", "description": "DMart"}
    ]
    df = pd.DataFrame(data)
    insights = generate_insights_rule_based(df, [])
    
    pdf_bytes = generate_pdf_report(df, insights, "Last 6 Months")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000 # Valid non-empty PDF
    assert pdf_bytes.startswith(b"%PDF")

def test_csv_export():
    data = [
        {"date": "2026-09-01", "type": "income", "amount": 88000.0, "category": "Salary", "description": "TechCorp Salary"}
    ]
    df = pd.DataFrame(data)
    csv_bytes = export_transactions_csv(df)
    assert b"TechCorp Salary" in csv_bytes
    assert b"88000.0" in csv_bytes
