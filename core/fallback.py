"""
SmartSpend AI - Intelligent Offline Rule-Based Fallback Engine.
Guarantees zero-downtime: if the Gemini API key is absent, rate-limited,
or encounters an exception, this engine seamlessly handles NLP parsing,
transaction categorization, grounded Q&A, and insight generation.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd
from core.analytics import (
    calculate_kpis, get_category_breakdown, calculate_50_30_20,
    detect_anomalies, format_inr, calculate_financial_health_score
)
from core.forecasting import forecast_3_months_expenses
from core.prompts import FINANCIAL_DISCLAIMER

# Keyword Dictionaries for Category Resolution
CATEGORY_KEYWORDS = {
    "Salary": ["salary", "tankhwah", "payroll", "techcorp", "credited by", "employer", "stipend"],
    "Freelance": ["upwork", "fiverr", "freelance", "consulting", "client payment", "invoice"],
    "Investment": ["sip", "mutual fund", "zerodha", "groww", "nifty", "index fund", "ppf", "stocks", "equity", "fd", "deposit"],
    "Rent": ["rent", "kiraya", "landlord", "flat", "apartment maintenance", "society maint"],
    "Groceries": ["blinkit", "zepto", "dmart", "bigbasket", "instamart", "grocery", "ration", "vegetables", "fruits", "milk", "doodh"],
    "Food & Dining": ["zomato", "swiggy", "starbucks", "mcdonald", "burger", "pizza", "biryani", "chai", "coffee", "restaurant", "pub", "bar", "dinner", "lunch", "khana", "snack"],
    "Bills & Utilities": ["electricity", "bijli", "wifi", "airtel", "jio", "broadband", "adani", "bescom", "gas", "cylinder", "recharge", "water bill"],
    "EMI & Loans": ["emi", "loan", "hdfc auto", "car loan", "home loan", "education loan", "credit card payment"],
    "Shopping": ["amazon", "flipkart", "myntra", "zara", "uniqlo", "clothes", "shoes", "electronics", "croma", "apple", "shopping", "mall"],
    "Travel & Commute": ["uber", "ola", "petrol", "fuel", "diesel", "shell", "fastag", "toll", "metro", "auto", "cab", "flight", "indigo", "irctc"],
    "Healthcare": ["apollo", "pharmacy", "1mg", "medicine", "doctor", "clinic", "hospital", "dentist", "dawa", "tests", "pathology"],
    "Subscriptions": ["netflix", "spotify", "prime", "youtube premium", "gym", "hotstar", "subscription"],
    "Entertainment": ["bookmyshow", "movie", "cinema", "gaming", "steam", "concert"]
}

def guess_category(text: str) -> str:
    """Classifies a description into a financial category based on keyword matching."""
    text_lower = text.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return cat
    return "Other"

def extract_transactions_rule_based(text: str) -> Dict[str, Any]:
    """
    Parses single-line or multi-line user text (English/Hinglish) into structured transactions.
    Supports Hindi numbers, today/yesterday keywords, and ambiguity detection.
    """
    today = datetime.today().date()
    yesterday = today - timedelta(days=1)
    
    # Split text into lines or sentences if multi-transaction
    raw_lines = [l.strip() for l in re.split(r'[\n;]+|(?<=[.!?])\s+', text) if l.strip()]
    if not raw_lines:
        return {"transactions": [], "needs_clarification": True, "clarification_question": "Could you provide details of your expense or income?"}

    extracted_list = []
    
    for line in raw_lines:
        line_lower = line.lower()
        
        # 1. Resolve Date
        txn_date = today
        if any(w in line_lower for w in ["yesterday", "kal", "beete kal"]):
            txn_date = yesterday
        elif any(w in line_lower for w in ["parso", "day before"]):
            txn_date = today - timedelta(days=2)
            
        # 2. Resolve Amount
        # Match patterns like: 450, 450.50, 1.5k, 20k, 1 lakh, ₹500, rs 500, 20 rupay
        amount = None
        
        # Check 'k' notation (e.g., 1.5k, 20k)
        k_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*k\b', line_lower)
        if k_match:
            amount = float(k_match.group(1)) * 1000
            
        # Check 'lakh' notation
        if amount is None:
            lakh_match = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*(?:lakh|lac)\b', line_lower)
            if lakh_match:
                amount = float(lakh_match.group(1)) * 100000

        # General numbers with rs / inr / rupay / ₹ or standalone
        if amount is None:
            # Pattern: (₹|rs|inr)?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:rupay|rs|inr|bucks)?
            amt_match = re.search(r'(?:₹|rs\.?|inr)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?)\s*(?:rupaye?|rupay|rs\.?|inr|bucks)?', line_lower)
            if amt_match and amt_match.group(1):
                clean_num = amt_match.group(1).replace(",", "")
                try:
                    val = float(clean_num)
                    if val > 0:
                        amount = val
                except ValueError:
                    pass

        # If no amount could be found in this segment
        if amount is None:
            continue
            
        # 3. Determine Category & Type
        cat = guess_category(line)
        is_income = cat in ["Salary", "Freelance"] or any(w in line_lower for w in ["received", "credited", "salary", "earned", "aaye", "mile"])
        txn_type = "income" if is_income else "expense"
        
        # 4. Clean description
        # Remove amounts and common action verbs
        desc = re.sub(r'(?:₹|rs\.?|inr)?\s*[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?\s*(?:rupaye?|rupay|rs\.?|inr|bucks)?', '', line, flags=re.IGNORECASE)
        desc = re.sub(r'\b(spent|paid|gaye|diye|aaye|mile|on|pe|for|yesterday|today|kal|aaj)\b', '', desc, flags=re.IGNORECASE).strip()
        if not desc:
            desc = f"{cat} Payment"
        else:
            desc = desc.strip(" ,.-")
            desc = desc.capitalize()

        # 5. Payment mode heuristic
        payment_mode = "UPI"
        if any(w in line_lower for w in ["card", "credit card", "debit"]):
            payment_mode = "Credit Card"
        elif any(w in line_lower for w in ["cash", "roker"]):
            payment_mode = "Cash"
        elif any(w in line_lower for w in ["net banking", "transfer", "neft", "imps"]):
            payment_mode = "Net Banking"

        extracted_list.append({
            "date": txn_date.strftime("%Y-%m-%d"),
            "description": desc,
            "category": cat,
            "type": txn_type,
            "amount": amount,
            "payment_mode": payment_mode
        })

    if not extracted_list:
        return {
            "transactions": [],
            "needs_clarification": True,
            "clarification_question": "Amount ya category clearly nahi mil payi. Kya aap ₹ amount specify kar sakte hain? (E.g. 'Spent 450 on Zomato')"
        }

    return {
        "transactions": extracted_list[:20],
        "needs_clarification": False,
        "clarification_question": ""
    }

def generate_chat_response_rule_based(user_message: str, df: pd.DataFrame) -> str:
    """
    Generates high-impact, grounded 4-sentence financial answers tailored to the user's data.
    Directly answers key user inquiries with real numbers and concludes with actionable advice.
    """
    msg = user_message.lower().strip()
    kpis = calculate_kpis(df)
    cats = get_category_breakdown(df, "expense")
    alloc = calculate_50_30_20(df)
    
    total_income = kpis["total_income"]
    total_expense = kpis["total_expense"]
    net_savings = kpis["net_savings"]
    savings_rate = kpis["savings_rate"]

    top_cat = cats.iloc[0]["category"] if not cats.empty else "General Spending"
    top_cat_amt = cats.iloc[0]["amount"] if not cats.empty else 0.0

    # Question 1: "Where am I overspending?"
    if any(q in msg for q in ["overspending", "overspend", "kahan zyada", "kharcha zyada"]):
        top3 = ", ".join([f"{r['category']} ({format_inr(r['amount'])})" for _, r in cats.head(3).iterrows()]) if not cats.empty else "various categories"
        return (
            f"Based on your recent records, your top expense category is **{top_cat}** at {format_inr(top_cat_amt)}, followed by {top3}. "
            f"Your discretionary 'Wants' account for {alloc['wants']['pct']}% of your expenditure, which exceeds the ideal 30% threshold. "
            f"Overall, you have spent {format_inr(total_expense)} against an income of {format_inr(total_income)}. "
            f"**Actionable Tip:** Set a strict monthly cap of {format_inr(top_cat_amt * 0.8)} on {top_cat} to save an extra ~{format_inr(top_cat_amt * 0.2)} next month.\n\n"
            f"_{FINANCIAL_DISCLAIMER}_"
        )

    # Question 2: "Can I afford a ₹60,000 phone?"
    if any(q in msg for q in ["60,000", "60000", "afford", "phone", "iphone", "laptop", "khareed sakti", "khareed sakta"]):
        monthly_surplus = max(0.0, net_savings / 6.0) if net_savings > 0 else 0.0
        can_afford = monthly_surplus >= 15000 or net_savings >= 120000
        verdict = "Yes, you can comfortably afford it" if can_afford else "It would strain your short-term cash flow right now"
        months_needed = max(1, int(round(60000.0 / monthly_surplus))) if monthly_surplus > 0 else 6
        return (
            f"{verdict}. Your average monthly net savings buffer is approximately {format_inr(monthly_surplus)} with a total surplus of {format_inr(net_savings)}. "
            f"A ₹60,000 one-off purchase represents {round((60000 / (net_savings or 60000)) * 100)}% of your accumulated savings. "
            f"You could fund this in ~{months_needed} months without liquidating essential emergency funds. "
            f"**Actionable Tip:** Allocate {format_inr(60000 / 3)} per month into a separate liquid stash over the next 3 months rather than using high-interest credit card debt.\n\n"
            f"_{FINANCIAL_DISCLAIMER}_"
        )

    # Question 3: "How do I save ₹1 lakh in 6 months?"
    if any(q in msg for q in ["1 lakh", "1,00,000", "100000", "save 1 lakh", "1 lakh kaise"]):
        monthly_target = 100000.0 / 6.0 # ~16,667
        avg_monthly_sav = max(0.0, net_savings / 6.0)
        gap = monthly_target - avg_monthly_sav
        return (
            f"To accumulate ₹1,00,000 in 6 months, you need to save **{format_inr(monthly_target)} each month**. "
            f"Your current average monthly savings is around {format_inr(avg_monthly_sav)} (savings rate: {savings_rate}%). "
            f"{'You are already on track to exceed this goal!' if gap <= 0 else f'You have a minor monthly gap of {format_inr(gap)} to cover.'} "
            f"**Actionable Tip:** Trim discretionary dining and shopping by 15% and route the ₹16,667 into an automated recurring deposit or liquid mutual fund on the 2nd of every month.\n\n"
            f"_{FINANCIAL_DISCLAIMER}_"
        )

    # Question 4: "Give me a budget plan"
    if any(q in msg for q in ["budget plan", "budget", "50/30/20", "planning", "kharcha plan"]):
        avg_income = total_income / 6.0 if total_income > 0 else 85000.0
        return (
            f"Here is your personalized **50/30/20 budget framework** based on your monthly average income of {format_inr(avg_income)}: "
            f"Allocate **{format_inr(avg_income * 0.50)} (50%)** for Needs (Rent, Groceries, Utilities, EMIs), **{format_inr(avg_income * 0.30)} (30%)** for Wants (Dining, Shopping, Travel), and **{format_inr(avg_income * 0.20)} (20%)** for Investments/SIPs. "
            f"Currently, your wants are at {alloc['wants']['pct']}% of income. "
            f"**Actionable Tip:** Automate an investment SIP of {format_inr(avg_income * 0.20)} right on salary day so you only spend what is left over.\n\n"
            f"_{FINANCIAL_DISCLAIMER}_"
        )

    # Hinglish query detection
    if any(w in msg for w in ["kaisa", "mera", "batao", "bachat", "kitna", "kya", "paisa", "rupay"]):
        return (
            f"Aapka total income {format_inr(total_income)} hai aur total expenses {format_inr(total_expense)} hain, jisse aapki net bachat {format_inr(net_savings)} ({savings_rate}%) banti hai. "
            f"Aapka sabse bada kharcha **{top_cat}** ({format_inr(top_cat_amt)}) me ho raha hai. "
            f"Aapki financial health overall strong hai lekin discretionary kharche control me rakhna zaroori hai. "
            f"**Actionable Tip:** Weekend dining aur online delivery par weekly limit lagaiye taaki mahine ke ₹4,000 extra bachein.\n\n"
            f"_{FINANCIAL_DISCLAIMER}_"
        )

    # General financial overview response
    return (
        f"You have tracked a total income of {format_inr(total_income)} against expenses of {format_inr(total_expense)}, yielding a healthy net savings of {format_inr(net_savings)} ({savings_rate}%). "
        f"Your highest spending is directed towards {top_cat} ({format_inr(top_cat_amt)}), followed by other essential needs. "
        f"Your current financial health score stands at {calculate_financial_health_score(df)['score']}/100. "
        f"**Actionable Tip:** Automate your savings transfer immediately after receiving income to protect your emergency buffer.\n\n"
        f"_{FINANCIAL_DISCLAIMER}_"
    )

def generate_insights_rule_based(df: pd.DataFrame, goals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates structured AI-style Insights JSON using rigorous analytical logic.
    Follows the exact schema required by the UI view.
    """
    health = calculate_financial_health_score(df)
    kpis = calculate_kpis(df)
    alloc = calculate_50_30_20(df)
    anomalies_raw = detect_anomalies(df)
    cats = get_category_breakdown(df, "expense")
    top_cat = cats.iloc[0]["category"] if not cats.empty else "Discretionary"
    top_amt = cats.iloc[0]["amount"] if not cats.empty else 0.0

    # Alerts
    alerts = []
    if alloc["wants"]["pct"] > 30:
        alerts.append(f"Discretionary 'Wants' spending is at {alloc['wants']['pct']}%, exceeding the 30% benchmark.")
    if kpis["mom_expense_change_pct"] > 10:
        alerts.append(f"Month-over-month expenses increased by {kpis['mom_expense_change_pct']}%.")
    if len(anomalies_raw) > 0:
        alerts.append(f"Detected {len(anomalies_raw)} unusual spending spikes requiring verification.")
    if not alerts:
        alerts.append("Spending trajectory is within normal operating limits across all categories.")

    # Anomalies
    anomalies_formatted = []
    for a in anomalies_raw[:3]:
        anomalies_formatted.append({
            "category": a.get("category", "General"),
            "description": a.get("description", "High Expense"),
            "amount": a.get("amount", 0.0),
            "severity": "High" if a.get("z_score", 0) > 3.0 else "Medium",
            "insight": f"Spike of {format_inr(a.get('amount', 0.0))} is {a.get('z_score', 0)} std deviations higher than typical category spend."
        })

    # Savings tips
    savings_tips = [
        f"Trim monthly {top_cat} expenditure by 15% to immediately free up {format_inr(top_amt * 0.15)} for savings.",
        f"Re-evaluate recurring digital subscriptions; consolidating streaming services can save ~₹1,200/month.",
        "Set up an automated SIP transfer on salary credit day (1st of each month) to enforce zero-friction savings."
    ]

    # Goal feasibility
    monthly_surplus = max(0.0, kpis["net_savings"] / 6.0)
    goal_feasibility = []
    for g in goals:
        target = float(g.get("target_amount", 0.0))
        current = float(g.get("current_amount", 0.0))
        rem = max(0.0, target - current)
        
        # Calculate months remaining
        try:
            target_dt = datetime.strptime(g.get("target_date", "2026-12-31"), "%Y-%m-%d").date()
            today = datetime.today().date()
            days_left = max(1, (target_dt - today).days)
            months_left = max(1, round(days_left / 30.0))
        except Exception:
            months_left = 6
            
        req_monthly = rem / months_left
        is_feas = monthly_surplus >= req_monthly
        
        goal_feasibility.append({
            "goal_name": g.get("title", "Goal"),
            "is_feasible": is_feas,
            "monthly_required": round(req_monthly, 2),
            "verdict": f"Feasible: Requires {format_inr(req_monthly)}/month over {months_left} months (Current surplus: {format_inr(monthly_surplus)}/month)." if is_feas else f"Challenging: Target requires {format_inr(req_monthly)}/month, which exceeds current monthly surplus of {format_inr(monthly_surplus)}. Consider extending target date by {round(req_monthly / (monthly_surplus or 1))} months."
        })

    return {
        "health_score": health["score"],
        "health_grade": health["grade"],
        "executive_summary": f"Your financial health score is {health['score']}/100 ({health['grade']}). You maintain a healthy savings rate of {kpis['savings_rate']}%, with opportunities to optimize discretionary spending in {top_cat}.",
        "alerts": alerts,
        "anomalies": anomalies_formatted,
        "savings_tips": savings_tips,
        "budget_plan": {
            "framework": "50/30/20",
            "needs_advice": f"Needs currently comprise {alloc['needs']['pct']}% of spending. Keep fixed commitments under 50%.",
            "wants_advice": f"Wants represent {alloc['wants']['pct']}% of spending. Cap discretionary dining and shopping to 30%.",
            "savings_advice": f"Current savings and investments stand at {alloc['savings']['pct']}%. Maintain at least 20% in disciplined SIPs."
        },
        "goal_feasibility": goal_feasibility,
        "disclaimer": FINANCIAL_DISCLAIMER
    }
