"""
SmartSpend AI - Reports, Imports & Data Management.
Supports CSV/Excel batch upload (up to 500 rows), PDF Bank Statement extraction (pdfplumber),
manual transaction entry, CSV export, and executive PDF statement generation (fpdf2).
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import (
    get_transactions_df, add_transaction, add_transactions_batch,
    delete_transaction, get_goals
)
from core.parser import parse_csv_or_excel, parse_pdf_bank_statement
from core.report_generator import generate_pdf_report, export_transactions_csv
from core.llm_service import generate_ai_insights
from core.analytics import format_inr
from core.prompts import FINANCIAL_DISCLAIMER

CATEGORIES = [
    "Salary", "Freelance", "Investment", "Rent", "Groceries",
    "Food & Dining", "Bills & Utilities", "EMI & Loans", "Shopping",
    "Travel & Commute", "Healthcare", "Subscriptions", "Entertainment", "Other"
]

def render_reports():
    session_id = st.session_state.get("session_id", "demo_user")
    df = get_transactions_df(session_id)

    st.title("📑 Statements, Imports & Reports")
    st.caption("Import statements, manage transaction ledgers, and download certified executive PDF financial reports.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📥 Download PDF & CSV", 
        "📂 Batch File Import (CSV / PDF)", 
        "✏️ Manual Transaction Entry", 
        "📋 Complete Transaction Ledger"
    ])

    # TAB 1: DOWNLOAD PDF & CSV
    with tab1:
        st.subheader("Executive Financial Statement (PDF)")
        st.write("Generate a board-ready monthly financial report summarizing your net worth, 50/30/20 budget adherence, category distributions, and strategic AI audit findings.")

        if df.empty:
            st.warning("No transactions recorded yet. Please import data or try the demo account.")
        else:
            rep_col1, rep_col2 = st.columns([2, 1])
            with rep_col1:
                date_label = st.selectbox("Select Statement Scope", [
                    "Last 6 Months (Comprehensive)",
                    "Last 90 Days",
                    "Last 30 Days (Current Month)"
                ])

            with rep_col2:
                st.write("")
                st.write("")
                if st.button("📄 Compile Executive PDF", type="primary", use_container_width=True):
                    with st.spinner("Generating PDF statement via fpdf2..."):
                        goals = get_goals(session_id)
                        insights = generate_ai_insights(df, goals)
                        pdf_bytes = generate_pdf_report(df, insights, date_range_label=date_label)
                        
                        st.download_button(
                            label="⬇️ Download PDF Report",
                            data=pdf_bytes,
                            file_name=f"SmartSpend_Statement_{datetime.now().strftime('%Y%m%d')}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )
                        st.success("PDF Compiled successfully! Click the button above to download.")

            st.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 24px 0;'/>", unsafe_allow_html=True)
            
            st.subheader("Raw Data Export (CSV)")
            st.write("Export your complete transaction ledger as a clean, standardized CSV file.")
            
            csv_bytes = export_transactions_csv(df)
            st.download_button(
                label="⬇️ Export Complete Ledger (CSV)",
                data=csv_bytes,
                file_name=f"smartspend_transactions_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )

    # TAB 2: BATCH FILE IMPORT (CSV / EXCEL / PDF)
    with tab2:
        st.subheader("Batch File Import")
        st.write("Upload your bank statement or expense sheet. Supports CSV, Excel (`.xlsx`), or PDF statements (up to 500 rows).")

        import_type = st.radio("Select File Type", ["CSV / Excel File", "PDF Bank Statement"], horizontal=True)

        if import_type == "CSV / Excel File":
            uploaded_file = st.file_uploader("Upload CSV or Excel Statement", type=["csv", "xlsx", "xls"], key="csv_uploader")
            if uploaded_file is not None:
                file_bytes = uploaded_file.read()
                clean_df, msg = parse_csv_or_excel(file_bytes, uploaded_file.name)
                
                if clean_df is not None and not clean_df.empty:
                    st.success(f"{msg} Review the auto-categorized preview below before committing:")
                    
                    edited_import = st.data_editor(clean_df, use_container_width=True, num_rows="dynamic")
                    
                    if st.button("💾 Save All Imported Transactions", type="primary"):
                        recs = edited_import.to_dict(orient="records")
                        added = add_transactions_batch(session_id, recs)
                        st.success(f"Successfully recorded {added} transactions to your ledger!")
                        st.rerun()
                else:
                    st.error(msg)

        else: # PDF Bank Statement
            pdf_file = st.file_uploader("Upload PDF Bank Statement", type=["pdf"], key="pdf_uploader")
            if pdf_file is not None:
                with st.spinner("Extracting transactions using pdfplumber & heuristic NLP..."):
                    pdf_bytes = pdf_file.read()
                    parsed_pdf_df, msg = parse_pdf_bank_statement(pdf_bytes)

                if parsed_pdf_df is not None and not parsed_pdf_df.empty:
                    st.success(f"{msg} Review extracted transactions below:")
                    edited_pdf_import = st.data_editor(parsed_pdf_df, use_container_width=True, num_rows="dynamic")

                    if st.button("💾 Save Statement Transactions", type="primary"):
                        recs = edited_pdf_import.to_dict(orient="records")
                        added = add_transactions_batch(session_id, recs)
                        st.success(f"Successfully saved {added} transactions from PDF!")
                        st.rerun()
                else:
                    st.error(msg)

    # TAB 3: MANUAL TRANSACTION ENTRY
    with tab3:
        st.subheader("Manual Transaction Entry")
        st.write("Quickly record a single transaction with full manual control over all attributes.")

        with st.form("manual_tx_form", clear_on_submit=True):
            m_c1, m_c2 = st.columns(2)
            with m_c1:
                t_date = st.date_input("Transaction Date", value=datetime.today())
                t_desc = st.text_input("Merchant / Description", placeholder="e.g., Starbucks Coffee, DMart Supermarket")
                t_cat = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index("Food & Dining"))
            with m_c2:
                t_type = st.selectbox("Transaction Type", ["expense", "income"])
                t_amt = st.number_input("Amount (₹)", min_value=1.0, step=50.0, value=350.0)
                t_mode = st.selectbox("Payment Mode", ["UPI", "Credit Card", "Debit Card", "Net Banking", "Cash"])

            t_notes = st.text_input("Notes (Optional)", placeholder="e.g., Shared with team, monthly routine")

            if st.form_submit_button("Record Transaction", type="primary", use_container_width=True):
                if not t_desc.strip():
                    st.error("Please enter a description for the transaction.")
                else:
                    add_transaction(
                        session_id,
                        t_date.strftime("%Y-%m-%d"),
                        t_desc.strip(),
                        t_cat,
                        t_type,
                        t_amt,
                        t_mode,
                        t_notes.strip()
                    )
                    st.success(f"Recorded transaction: {format_inr(t_amt)} for {t_desc}!")
                    st.rerun()

    # TAB 4: COMPLETE TRANSACTION LEDGER
    with tab4:
        st.subheader("Transaction Ledger")
        if df.empty:
            st.info("No records in ledger.")
        else:
            search_query = st.text_input("🔍 Search Description or Category", "")
            
            view_df = df.copy()
            if search_query.strip():
                q = search_query.lower()
                view_df = view_df[
                    view_df["description"].str.lower().str.contains(q) |
                    view_df["category"].str.lower().str.contains(q)
                ]

            st.write(f"Showing {len(view_df)} transactions:")
            display_ledger = view_df[["id", "date", "description", "category", "type", "amount", "payment_mode"]].copy()
            display_ledger["date"] = display_ledger["date"].dt.strftime("%Y-%m-%d")
            
            st.dataframe(display_ledger, use_container_width=True, hide_index=True)

            # Single record deletion tool
            with st.expander("🗑️ Delete a Transaction by ID"):
                del_col1, del_col2 = st.columns([3, 1])
                with del_col1:
                    target_id = st.number_input("Transaction ID to delete", min_value=1, step=1)
                with del_col2:
                    st.write("")
                    st.write("")
                    if st.button("Delete Record", type="secondary"):
                        success = delete_transaction(int(target_id), session_id)
                        if success:
                            st.success(f"Deleted transaction #{target_id}")
                            st.rerun()
                        else:
                            st.error(f"Transaction #{target_id} not found.")

    st.markdown(f"""
    <div class="disclaimer-box">
        ⚖️ {FINANCIAL_DISCLAIMER}
    </div>
    """, unsafe_allow_html=True)
