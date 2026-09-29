"""
SmartSpend AI - Financial Report Generator.
Generates comprehensive executive monthly PDF financial statements using fpdf2
and exports clean CSV records.
"""

import io
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
from fpdf import FPDF
from core.analytics import calculate_kpis, get_category_breakdown, calculate_50_30_20
from core.prompts import FINANCIAL_DISCLAIMER

class PDFReport(FPDF):
    def header(self):
        # Header banner
        self.set_fill_color(15, 23, 42) # Slate-900
        self.rect(0, 0, 210, 32, "F")
        
        self.set_text_color(16, 185, 129) # Emerald
        self.set_font("Helvetica", "B", 18)
        self.set_xy(14, 8)
        self.cell(182, 10, "SmartSpend AI")
        
        self.set_text_color(203, 213, 225) # Slate-300
        self.set_font("Helvetica", "", 10)
        self.set_xy(14, 18)
        self.cell(182, 6, "Executive Personal Financial Statement & AI Advisory Report")
        self.set_y(36)

    def footer(self):
        self.set_y(-20)
        self.set_draw_color(226, 232, 240)
        self.line(14, self.get_y(), 196, self.get_y())
        self.ln(3)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.set_x(14)
        self.cell(182, 5, f"SmartSpend AI Confidential Report | {FINANCIAL_DISCLAIMER}", align="C")
        self.ln(4)
        self.set_x(14)
        self.cell(182, 4, f"Page {self.page_no()}", align="C")

def format_pdf_inr(amount: float) -> str:
    """Formats amount as 'INR X,XX,XXX' for safe Latin-1 PDF core font rendering."""
    amt = abs(float(amount))
    parts = f"{amt:.2f}".split(".")
    integer_part = parts[0]
    
    if len(integer_part) <= 3:
        formatted_int = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        grouped = []
        while len(remaining) > 2:
            grouped.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            grouped.insert(0, remaining)
        formatted_int = ",".join(grouped) + "," + last_three

    sign = "-" if amount < 0 else ""
    return f"{sign}INR {formatted_int}"

def sanitize_pdf_text(text: str) -> str:
    """Replaces Unicode characters like ₹ with Latin-1 equivalents for safe rendering."""
    if not text:
        return ""
    clean = str(text).replace("₹", "INR ").replace("–", "-").replace("—", "-")
    # Filter out any other characters not encodable in latin-1
    return clean.encode("latin-1", "replace").decode("latin-1")

def generate_pdf_report(df: pd.DataFrame, insights: Dict[str, Any], date_range_label: str = "Last 6 Months") -> bytes:
    """
    Generates a PDF financial report containing executive summaries,
    KPI scorecard, category breakdown tables, AI alerts, and disclaimer.
    """
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=24)
    pdf.add_page()
    
    kpis = calculate_kpis(df)
    cats = get_category_breakdown(df, "expense")
    alloc = calculate_50_30_20(df)

    # Report Meta info
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 41, 59)
    pdf.set_x(14)
    pdf.cell(182, 8, f"Statement Period: {date_range_label}")
    pdf.ln(7)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.set_x(14)
    pdf.cell(182, 5, f"Report Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')}")
    pdf.ln(8)

    # 1. KPI Scorecard Table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(14)
    pdf.cell(182, 7, "1. Executive Financial Summary")
    pdf.ln(8)

    # KPI Box Row
    col_w = 45.0
    h_box = 18
    start_x = 14

    kpi_items = [
        ("Total Income", format_pdf_inr(kpis["total_income"]), (236, 253, 245), (16, 185, 129)),
        ("Total Expenses", format_pdf_inr(kpis["total_expense"]), (254, 242, 242), (239, 68, 68)),
        ("Net Savings", format_pdf_inr(kpis["net_savings"]), (240, 249, 255), (56, 189, 248)),
        ("Savings Rate", f"{kpis['savings_rate']}%", (245, 243, 255), (139, 92, 246))
    ]

    for idx, (label, val, bg_col, text_col) in enumerate(kpi_items):
        cur_x = start_x + (idx * (col_w + 1))
        cur_y = pdf.get_y()
        
        pdf.set_fill_color(*bg_col)
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(cur_x, cur_y, col_w, h_box, "FD")
        
        pdf.set_xy(cur_x + 2, cur_y + 2)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(col_w - 4, 4, label)
        
        pdf.set_xy(cur_x + 2, cur_y + 8)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*text_col)
        pdf.cell(col_w - 4, 6, val)

    pdf.set_y(pdf.get_y() + h_box + 8)

    # 2. 50/30/20 Budget Allocation Breakdown
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(14)
    pdf.cell(182, 7, "2. Budget Allocation (50/30/20 Framework)")
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(51, 65, 85)
    
    alloc_text = (
        f"- Needs (Fixed essentials): {format_pdf_inr(alloc['needs']['amount'])} ({alloc['needs']['pct']}% vs Target: 50%)\n"
        f"- Wants (Discretionary spend): {format_pdf_inr(alloc['wants']['amount'])} ({alloc['wants']['pct']}% vs Target: 30%)\n"
        f"- Savings & Investments: {format_pdf_inr(alloc['savings']['amount'])} ({alloc['savings']['pct']}% vs Target: 20%)\n"
        f"Allocation Status: {alloc['status']}"
    )
    pdf.set_x(14)
    pdf.multi_cell(182, 5, sanitize_pdf_text(alloc_text))
    pdf.ln(6)

    # 3. Category Spending Table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(14)
    pdf.cell(182, 7, "3. Top Expense Categories")
    pdf.ln(7)
    
    # Table Header
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(30, 41, 59)
    
    pdf.set_x(14)
    pdf.cell(85, 7, "Category", border=1, align="L", fill=True, new_x="RIGHT", new_y="TOP")
    pdf.cell(52, 7, "Amount Spent", border=1, align="R", fill=True, new_x="RIGHT", new_y="TOP")
    pdf.cell(45, 7, "% of Total Expenses", border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(51, 65, 85)
    
    top_cats = cats.head(8)
    for _, row in top_cats.iterrows():
        pdf.set_x(14)
        pdf.cell(85, 6, sanitize_pdf_text(str(row["category"])), border=1, align="L", new_x="RIGHT", new_y="TOP")
        pdf.cell(52, 6, format_pdf_inr(row["amount"]), border=1, align="R", new_x="RIGHT", new_y="TOP")
        pdf.cell(45, 6, f"{row['percentage']}%", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)

    # 4. AI Strategic Insights & Savings Plan
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(14)
    score_label = f"4. AI Health Audit (Score: {insights.get('health_score', 80)}/100 - {insights.get('health_grade', 'Good')})"
    pdf.cell(182, 7, sanitize_pdf_text(score_label))
    pdf.ln(7)
    
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.set_x(14)
    pdf.multi_cell(182, 5, sanitize_pdf_text(str(insights.get("executive_summary", ""))))
    pdf.ln(4)

    # Alerts & Actionable Tips
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(180, 83, 9) # Amber dark
    pdf.set_x(14)
    pdf.cell(182, 6, "Priority Budget Alerts & Opportunities:")
    pdf.ln(6)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(51, 65, 85)
    for alert in insights.get("alerts", []):
        pdf.set_x(14)
        pdf.cell(182, 5, sanitize_pdf_text(f"  * {alert}"))
        pdf.ln(5)

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(5, 150, 105) # Green dark
    pdf.set_x(14)
    pdf.cell(182, 6, "Targeted Action Items to Boost Savings:")
    pdf.ln(6)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(51, 65, 85)
    for tip in insights.get("savings_tips", []):
        pdf.set_x(14)
        pdf.multi_cell(182, 5, sanitize_pdf_text(f"  - {tip}"))
        pdf.ln(2)

    pdf.ln(4)

    # Output to byte stream
    return bytes(pdf.output())

def export_transactions_csv(df: pd.DataFrame) -> bytes:
    """Exports transaction records into CSV bytes."""
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")
