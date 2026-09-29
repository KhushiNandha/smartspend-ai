"""
Unit tests for SmartSpend AI transaction parsers and fallback engine.
"""

import pytest
import io
import pandas as pd
from datetime import datetime, timedelta
from core.fallback import extract_transactions_rule_based, guess_category
from core.parser import parse_text_input, parse_csv_or_excel

def test_single_line_english_parsing():
    text = "Spent 450 on Zomato yesterday"
    result = extract_transactions_rule_based(text)
    
    assert not result["needs_clarification"]
    txns = result["transactions"]
    assert len(txns) == 1
    txn = txns[0]
    assert txn["amount"] == 450.0
    assert txn["category"] == "Food & Dining"
    assert txn["type"] == "expense"
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    assert txn["date"] == yesterday

def test_hinglish_parsing():
    text = "Aaj chai pe 20 rupay gaye"
    result = extract_transactions_rule_based(text)
    
    assert not result["needs_clarification"]
    txns = result["transactions"]
    assert len(txns) == 1
    txn = txns[0]
    assert txn["amount"] == 20.0
    assert txn["category"] == "Food & Dining"
    assert txn["type"] == "expense"
    assert txn["date"] == datetime.today().strftime("%Y-%m-%d")

def test_multi_line_paragraph_parsing():
    text = """
    Spent 1200 on Amazon shopping
    Paid 22000 rent to landlord
    Received 85000 salary from TechCorp
    """
    result = extract_transactions_rule_based(text)
    assert not result["needs_clarification"]
    txns = result["transactions"]
    assert len(txns) == 3
    
    amounts = [t["amount"] for t in txns]
    assert 1200.0 in amounts
    assert 22000.0 in amounts
    assert 85000.0 in amounts

    types = {t["amount"]: t["type"] for t in txns}
    assert types[85000.0] == "income"
    assert types[22000.0] == "expense"

def test_ambiguity_needs_clarification():
    text = "Had a great dinner with friends last night"
    result = extract_transactions_rule_based(text)
    assert result["needs_clarification"] is True
    assert len(result["clarification_question"]) > 0

def test_category_guessing():
    assert guess_category("Blinkit grocery order") == "Groceries"
    assert guess_category("HDFC car loan EMI") == "EMI & Loans"
    assert guess_category("Uber ride to airport") == "Travel & Commute"
    assert guess_category("Apollo Pharmacy medicines") == "Healthcare"
    assert guess_category("Airtel fiber broadband bill") == "Bills & Utilities"
    assert guess_category("Monthly SIP in Index Fund") == "Investment"

def test_csv_parser():
    csv_content = """Date,Description,Amount
2026-09-01,TechCorp Salary,85000
2026-09-05,Apartment Rent,22000
2026-09-10,DMart Grocery,4500
"""
    df, msg = parse_csv_or_excel(csv_content.encode("utf-8"), "test.csv")
    assert df is not None
    assert len(df) == 3
    assert "Salary" in df["category"].values
    assert "Rent" in df["category"].values
