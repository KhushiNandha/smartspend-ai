"""
SmartSpend AI - Multi-Format Input Parsers.
Handles Natural Language text (English/Hinglish), CSV/Excel batch upload (max 500 rows),
and PDF Bank Statement extraction using pdfplumber.
"""

import io
import re
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
import pdfplumber

from core.llm_service import extract_transactions, batch_categorize_descriptions
from core.fallback import guess_category

CANONICAL_COLUMNS = ["date", "description", "category", "type", "amount", "payment_mode", "notes"]

def parse_text_input(user_input: str) -> Dict[str, Any]:
    """
    Parses conversational or multi-line user input into structured transactions.
    Supports English & Hinglish, handles ambiguity and clarification requests.
    """
    if not user_input or not user_input.strip():
        return {
            "transactions": [],
            "needs_clarification": True,
            "clarification_question": "Please enter a transaction, e.g., 'Spent 450 on Zomato yesterday' or 'Chai pe 20 rupay'."
        }
    return extract_transactions(user_input)

def parse_csv_or_excel(file_bytes: bytes, filename: str) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Parses an uploaded CSV or Excel file, normalizes columns,
    auto-categorizes rows, and validates the data (up to 500 rows).
    """
    try:
        if filename.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(file_bytes))
        elif filename.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            return None, "Unsupported file format. Please upload a CSV or Excel file."

        if df.empty:
            return None, "The uploaded file is empty."

        # Cap at 500 rows as required
        if len(df) > 500:
            df = df.iloc[:500]

        # Normalize column names: lowercase and stripped
        col_map = {col: str(col).strip().lower() for col in df.columns}
        df = df.rename(columns=col_map)

        # Match Date Column
        date_col = next((c for c in df.columns if any(k in c for k in ["date", "txn_date", "transaction date", "time", "posting date"])), None)
        # Match Description Column
        desc_col = next((c for c in df.columns if any(k in c for k in ["desc", "narration", "particulars", "remarks", "details", "merchant"])), None)
        # Match Amount Column
        amt_col = next((c for c in df.columns if any(k in c for k in ["amount", "amt", "value", "inr"])), None)
        # Check debit / credit columns if amount not singular
        debit_col = next((c for c in df.columns if any(k in c for k in ["debit", "withdrawal", "dr"])), None)
        credit_col = next((c for c in df.columns if any(k in c for k in ["credit", "deposit", "cr"])), None)

        if not desc_col:
            return None, "Could not identify a 'Description' or 'Particulars' column in the uploaded file."

        output_rows = []
        descriptions_to_categorize = []

        for idx, row in df.iterrows():
            # Date
            raw_date = row.get(date_col) if date_col else None
            try:
                if pd.notna(raw_date):
                    parsed_date = pd.to_datetime(raw_date, errors="coerce")
                    date_val = parsed_date.strftime("%Y-%m-%d") if pd.notna(parsed_date) else datetime.today().strftime("%Y-%m-%d")
                else:
                    date_val = datetime.today().strftime("%Y-%m-%d")
            except Exception:
                date_val = datetime.today().strftime("%Y-%m-%d")

            # Description
            raw_desc = str(row.get(desc_col, f"Transaction {idx+1}")).strip()
            if not raw_desc or raw_desc == "nan":
                raw_desc = f"Transaction #{idx+1}"

            # Amount & Type
            txn_type = "expense"
            amount_val = 0.0

            if amt_col and pd.notna(row.get(amt_col)):
                try:
                    raw_val = float(str(row[amt_col]).replace(",", "").replace("₹", "").strip())
                    if raw_val < 0:
                        txn_type = "expense"
                        amount_val = abs(raw_val)
                    else:
                        amount_val = raw_val
                except ValueError:
                    amount_val = 0.0
            elif debit_col and pd.notna(row.get(debit_col)) and float(str(row.get(debit_col, 0)).replace(",", "") or 0) > 0:
                txn_type = "expense"
                amount_val = abs(float(str(row[debit_col]).replace(",", "")))
            elif credit_col and pd.notna(row.get(credit_col)) and float(str(row.get(credit_col, 0)).replace(",", "") or 0) > 0:
                txn_type = "income"
                amount_val = abs(float(str(row[credit_col]).replace(",", "")))

            # Check if category is already provided in file
            existing_cat_col = next((c for c in df.columns if "category" in c), None)
            category_val = str(row[existing_cat_col]).strip() if existing_cat_col and pd.notna(row.get(existing_cat_col)) else None

            output_rows.append({
                "date": date_val,
                "description": raw_desc,
                "category": category_val,
                "type": txn_type,
                "amount": amount_val,
                "payment_mode": "Imported",
                "notes": f"Imported from {filename}"
            })
            descriptions_to_categorize.append(raw_desc)

        # Auto-categorize missing categories in batch
        uncat_indices = [i for i, r in enumerate(output_rows) if not r["category"]]
        if uncat_indices:
            uncat_descs = [output_rows[i]["description"] for i in uncat_indices]
            categorized_results = batch_categorize_descriptions(uncat_descs)
            for i, cat_res in zip(uncat_indices, categorized_results):
                output_rows[i]["category"] = cat_res.get("category", "Other")
                if cat_res.get("type"):
                    output_rows[i]["type"] = cat_res["type"]

        clean_df = pd.DataFrame(output_rows)
        return clean_df, f"Successfully parsed {len(clean_df)} transactions."
    except Exception as e:
        return None, f"Failed to process file: {str(e)}"

def parse_pdf_bank_statement(file_bytes: bytes) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Parses bank statement text and tables from a PDF using pdfplumber.
    Identifies transaction lines via regex and categorizes them.
    """
    try:
        extracted_text = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages[:10]: # Read up to 10 pages
                text = page.extract_text()
                if text:
                    extracted_text.append(text)

        full_text = "\n".join(extracted_text)
        if not full_text.strip():
            return None, "No readable text found in PDF. Make sure it is not a scanned image."

        lines = full_text.split("\n")
        parsed_rows = []

        # Regex pattern for date + description + amount
        # E.g. 15/08/2026 ZOMATO RESTAURANT 450.00
        # E.g. 2026-08-15 SALARY CREDIT 85000.00
        date_pattern = r'(\d{1,4}[-/.]\d{1,2}[-/.]\d{2,4})'
        amt_pattern = r'([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{2})?)'

        for line in lines:
            line_str = line.strip()
            date_match = re.search(date_pattern, line_str)
            if not date_match:
                continue

            raw_date_str = date_match.group(1)
            # Find numbers that look like amounts
            num_matches = list(re.finditer(amt_pattern, line_str))
            if not num_matches:
                continue

            # Pick the last matched amount on the line
            last_amt_match = num_matches[-1]
            raw_amt_str = last_amt_match.group(1).replace(",", "")
            try:
                amt = float(raw_amt_str)
                if amt <= 0 or amt > 5000000: # Filter out dates or phone numbers
                    continue
            except ValueError:
                continue

            # Description is what's between date and amount
            start_pos = date_match.end()
            end_pos = last_amt_match.start()
            raw_desc = line_str[start_pos:end_pos].strip(" -|:")
            if len(raw_desc) < 3:
                raw_desc = "Bank Transaction"

            # Parse date safely
            try:
                parsed_dt = pd.to_datetime(raw_date_str, dayfirst=True, errors="coerce")
                formatted_date = parsed_dt.strftime("%Y-%m-%d") if pd.notna(parsed_dt) else datetime.today().strftime("%Y-%m-%d")
            except Exception:
                formatted_date = datetime.today().strftime("%Y-%m-%d")

            cat = guess_category(raw_desc)
            is_income = cat in ["Salary", "Freelance"] or any(k in line_str.lower() for k in ["cr", "credit", "deposit", "salary"])

            parsed_rows.append({
                "date": formatted_date,
                "description": raw_desc[:60],
                "category": cat,
                "type": "income" if is_income else "expense",
                "amount": amt,
                "payment_mode": "Net Banking",
                "notes": "Extracted from PDF Statement"
            })

        if not parsed_rows:
            return None, "Could not automatically identify standard transaction rows in the PDF. Please try CSV upload or text entry."

        # Cap at 500 rows
        result_df = pd.DataFrame(parsed_rows[:500])
        return result_df, f"Successfully extracted {len(result_df)} transactions from statement."
    except Exception as e:
        return None, f"PDF extraction error: {str(e)}"
