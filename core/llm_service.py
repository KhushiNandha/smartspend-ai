"""
SmartSpend AI - Google Gemini LLM Service with Silent Rule-Based Fallback.
Provides cached LLM queries, timeout & retry handling, strict JSON parsing,
and automatic fallback when the API key is absent, rate-limited, or throws an error.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

from core.prompts import (
    TRANSACTION_EXTRACTION_PROMPT,
    CHAT_ASSISTANT_PROMPT,
    INSIGHTS_PROMPT,
    BATCH_CATEGORIZATION_PROMPT,
    FINANCIAL_DISCLAIMER
)
from core.fallback import (
    extract_transactions_rule_based,
    generate_chat_response_rule_based,
    generate_insights_rule_based,
    guess_category
)
from core.analytics import calculate_kpis, get_category_breakdown, format_inr, calculate_50_30_20

load_dotenv()
logger = logging.getLogger("smartspend.llm")

def get_gemini_api_key() -> Optional[str]:
    """
    Retrieves Gemini API Key in order of precedence:
    1. Streamlit Session State (User UI entry)
    2. Streamlit Secrets (Deployed cloud)
    3. OS Environment / .env file
    """
    # 1. User manual input in session state
    if "custom_gemini_key" in st.session_state and st.session_state["custom_gemini_key"]:
        return st.session_state["custom_gemini_key"].strip()

    # 2. st.secrets
    try:
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            key = st.secrets["GEMINI_API_KEY"]
            if key and key.strip():
                return key.strip()
    except Exception:
        pass

    # 3. Environment variable
    env_key = os.getenv("GEMINI_API_KEY", "")
    if env_key and env_key.strip() and env_key != "your_gemini_api_key_here":
        return env_key.strip()

    return None

def get_api_status() -> Dict[str, Any]:
    """Checks whether Gemini LLM is active or running in fallback mode."""
    api_key = get_gemini_api_key()
    if not api_key:
        return {
            "is_connected": False,
            "mode": "Rule-Based Engine (Zero-Setup Active)",
            "badge_class": "badge-fallback",
            "message": "Running on intelligent local financial rules. Add Gemini API key anytime in sidebar."
        }
    return {
        "is_connected": True,
        "mode": "Google Gemini AI (Live Connected)",
        "badge_class": "badge-ai",
        "message": "Powered by Gemini Generative AI for real-time extraction & conversational insights."
    }

def _init_gemini_model():
    """Safely initializes the Google Generative AI client."""
    api_key = get_gemini_api_key()
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # Use gemini-1.5-flash as the fast, cost-effective default model
        return genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini model: {e}")
        return None

def _clean_json_response(raw_text: str) -> str:
    """Strips markdown code fences and whitespace from LLM output."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def extract_transactions(user_input: str) -> Dict[str, Any]:
    """
    Extracts transactions from user text (English/Hinglish).
    Uses Gemini API if available, otherwise seamlessly executes rule-based extraction.
    """
    model = _init_gemini_model()
    if not model:
        return extract_transactions_rule_based(user_input)

    today_str = datetime.today().strftime("%Y-%m-%d")
    yesterday_str = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    prompt = TRANSACTION_EXTRACTION_PROMPT.format(
        current_date=today_str,
        yesterday_date=yesterday_str
    ) + f"\n\nUSER INPUT:\n{user_input}"

    for attempt in range(2):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 1024}
            )
            cleaned = _clean_json_response(response.text)
            parsed = json.loads(cleaned)

            if isinstance(parsed, dict) and parsed.get("needs_clarification"):
                return {
                    "transactions": [],
                    "needs_clarification": True,
                    "clarification_question": parsed.get("clarification_question", "Could you clarify the amount in ₹?")
                }

            if isinstance(parsed, list):
                # Validate transaction objects
                validated = []
                for item in parsed:
                    if isinstance(item, dict) and "amount" in item and "category" in item:
                        validated.append({
                            "date": str(item.get("date", today_str)),
                            "description": str(item.get("description", "Expense")),
                            "category": str(item.get("category", "Other")),
                            "type": str(item.get("type", "expense")).lower(),
                            "amount": float(item.get("amount", 0.0)),
                            "payment_mode": str(item.get("payment_mode", "UPI"))
                        })
                if validated:
                    return {
                        "transactions": validated,
                        "needs_clarification": False,
                        "clarification_question": ""
                    }
        except Exception as e:
            logger.warning(f"Gemini transaction extraction attempt {attempt+1} failed: {e}")
            time.sleep(0.5)

    # Fallback to rule-based parser on any failure
    return extract_transactions_rule_based(user_input)

def chat_response(user_message: str, df: pd.DataFrame) -> str:
    """
    Generates grounded personal finance response.
    Limits to 4 sentences, cites real user data, provides an actionable tip,
    and appends the financial disclaimer.
    """
    model = _init_gemini_model()
    if not model:
        return generate_chat_response_rule_based(user_message, df)

    # Build concise user data summary to ground the LLM
    kpis = calculate_kpis(df)
    cats = get_category_breakdown(df, "expense")
    alloc = calculate_50_30_20(df)

    top_cat_summary = ", ".join([f"{r['category']}: {format_inr(r['amount'])}" for _, r in cats.head(4).iterrows()]) if not cats.empty else "None"

    grounded_summary = (
        f"Total Income: {format_inr(kpis['total_income'])}, "
        f"Total Expenses: {format_inr(kpis['total_expense'])}, "
        f"Net Savings: {format_inr(kpis['net_savings'])} (Rate: {kpis['savings_rate']}%), "
        f"Top Expense Categories: {top_cat_summary}, "
        f"Budget Allocation: Needs {alloc['needs']['pct']}%, Wants {alloc['wants']['pct']}%, Savings {alloc['savings']['pct']}%, "
        f"MoM Spending Change: {kpis['mom_expense_change_pct']}%."
    )

    prompt = CHAT_ASSISTANT_PROMPT.format(
        user_summary=grounded_summary,
        disclaimer=FINANCIAL_DISCLAIMER
    ) + f"\n\nUSER QUESTION: {user_message}"

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "max_output_tokens": 512}
        )
        text = response.text.strip()
        # Guarantee disclaimer presence
        if FINANCIAL_DISCLAIMER not in text:
            text += f"\n\n_{FINANCIAL_DISCLAIMER}_"
        return text
    except Exception as e:
        logger.warning(f"Gemini chat failed: {e}. Switching to rule-based fallback.")
        return generate_chat_response_rule_based(user_message, df)

def generate_ai_insights(df: pd.DataFrame, goals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates comprehensive AI Insights in strict JSON.
    Falls back gracefully if LLM fails.
    """
    model = _init_gemini_model()
    if not model:
        return generate_insights_rule_based(df, goals)

    kpis = calculate_kpis(df)
    cats = get_category_breakdown(df, "expense")
    alloc = calculate_50_30_20(df)

    metrics_summary = {
        "kpis": kpis,
        "top_categories": cats.head(5).to_dict(orient="records") if not cats.empty else [],
        "budget_allocation": alloc,
        "goals": goals
    }

    prompt = INSIGHTS_PROMPT.format(
        financial_metrics=json.dumps(metrics_summary, indent=2),
        disclaimer=FINANCIAL_DISCLAIMER
    )

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 1500}
        )
        cleaned = _clean_json_response(response.text)
        data = json.loads(cleaned)
        
        # Verify required keys exist
        required_keys = ["health_score", "health_grade", "alerts", "anomalies", "savings_tips", "budget_plan"]
        if all(k in data for k in required_keys):
            data["disclaimer"] = FINANCIAL_DISCLAIMER
            return data
    except Exception as e:
        logger.warning(f"Gemini insights generation failed: {e}. Executing rule-based fallback.")

    return generate_insights_rule_based(df, goals)

def batch_categorize_descriptions(descriptions: List[str]) -> List[Dict[str, str]]:
    """
    Categorizes a list of transaction descriptions into canonical categories.
    """
    if not descriptions:
        return []

    model = _init_gemini_model()
    if not model or len(descriptions) > 50:
        # Fast rule-based for large batch or offline
        return [{"category": guess_category(d), "type": "income" if guess_category(d) in ["Salary", "Freelance"] else "expense"} for d in descriptions]

    # For smaller batches, attempt LLM categorization
    input_payload = [{"id": idx, "description": desc} for idx, desc in enumerate(descriptions[:50])]
    prompt = BATCH_CATEGORIZATION_PROMPT.format(transactions_json=json.dumps(input_payload))

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.0, "max_output_tokens": 2048}
        )
        cleaned = _clean_json_response(response.text)
        parsed = json.loads(cleaned)
        if isinstance(parsed, list) and len(parsed) == len(descriptions):
            return parsed
    except Exception as e:
        logger.warning(f"Batch categorization LLM failed: {e}. Using rule-based fallback.")

    return [{"category": guess_category(d), "type": "income" if guess_category(d) in ["Salary", "Freelance"] else "expense"} for d in descriptions]
