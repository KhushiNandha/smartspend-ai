"""
SmartSpend AI - Conversational Financial Assistant.
Multilingual NLP (English & Hinglish), suggested-question chips,
multi-transaction batch extraction with editable confirmation table,
and grounded financial advice.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from core.database import get_transactions_df, add_transactions_batch
from core.llm_service import chat_response, extract_transactions
from core.prompts import FINANCIAL_DISCLAIMER

SUGGESTED_CHIPS = [
    "Where am I overspending?",
    "Can I afford a ₹60,000 phone?",
    "How do I save ₹1 lakh in 6 months?",
    "Give me a budget plan"
]

def render_chat():
    session_id = st.session_state.get("session_id", "demo_user")
    df = get_transactions_df(session_id)

    st.title("💬 SmartSpend Financial Copilot")
    st.caption("Ask questions about your finances in English or Hinglish, or log single/multiple expenses naturally.")

    # 1. Clickable Prompt Chips
    st.markdown("**💡 Quick Financial Inquiries:**")
    chip_cols = st.columns(len(SUGGESTED_CHIPS))
    selected_chip = None
    
    for idx, chip in enumerate(SUGGESTED_CHIPS):
        with chip_cols[idx]:
            if st.button(chip, key=f"chip_{idx}", use_container_width=True):
                selected_chip = chip

    # Initialize Session Chat History
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {
                "role": "assistant",
                "content": f"Namaste! I am your SmartSpend AI personal finance assistant. You can ask me questions about your spending patterns, test if you can afford a purchase, or log expenses in English or Hinglish (e.g., 'Spent 450 on Zomato yesterday' or 'Chai pe 20 rupay').\n\n_{FINANCIAL_DISCLAIMER}_"
            }
        ]

    # Pending Extracted Transactions Confirmation State
    if "pending_extracted_txns" not in st.session_state:
        st.session_state["pending_extracted_txns"] = None

    # Render Active Pending Confirmation Table if exists
    if st.session_state["pending_extracted_txns"]:
        with st.container():
            st.info("📝 **Verify & Confirm Extracted Transactions:** We detected the following transaction(s). You can edit any field before saving.")
            
            pending_df = pd.DataFrame(st.session_state["pending_extracted_txns"])
            edited_df = st.data_editor(
                pending_df,
                use_container_width=True,
                num_rows="dynamic",
                key="editor_pending_txns"
            )
            
            c_save, c_cancel = st.columns([1, 4])
            with c_save:
                if st.button("💾 Save All to Account", type="primary", use_container_width=True):
                    records_to_save = edited_df.to_dict(orient="records")
                    saved_count = add_transactions_batch(session_id, records_to_save)
                    st.session_state["pending_extracted_txns"] = None
                    st.success(f"🎉 Successfully recorded {saved_count} transaction(s) to your ledger!")
                    # Add assistant confirmation to chat history
                    st.session_state["messages"].append({
                        "role": "assistant",
                        "content": f"Saved {saved_count} transaction(s) to your account. Your dashboard and budget metrics have been updated."
                    })
                    st.rerun()
            with c_cancel:
                if st.button("❌ Discard", use_container_width=True):
                    st.session_state["pending_extracted_txns"] = None
                    st.rerun()

    # Render Chat History
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Handle Input from Chip or Chat Input Box
    user_prompt = None
    if selected_chip:
        user_prompt = selected_chip
    else:
        chat_box_input = st.chat_input("Ask a question or log expenses (e.g., 'Aaj chai pe 20 rupay gaye' or 'Spent 450 on Zomato')...")
        if chat_box_input:
            user_prompt = chat_box_input

    if user_prompt:
        # Display user message
        st.session_state["messages"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Check if the prompt is an expense/transaction logging attempt
        # Heuristics: contains numbers/amount keywords + action verbs
        lower_prompt = user_prompt.lower()
        is_transaction_input = any(w in lower_prompt for w in [
            "spent", "paid", "bought", "gaye", "diye", "aaye", "mile", "kharcha", "rupay", 
            "rs", "inr", "zomato", "swiggy", "uber", "blinkit", "zepto", "salary", "credited"
        ]) and any(char.isdigit() for char in user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                if is_transaction_input:
                    extraction_result = extract_transactions(user_prompt)
                    
                    if extraction_result.get("needs_clarification"):
                        clarification = extraction_result.get("clarification_question", "Could you specify the exact amount in ₹?")
                        st.markdown(clarification)
                        st.session_state["messages"].append({"role": "assistant", "content": clarification})
                    else:
                        txns = extraction_result.get("transactions", [])
                        if txns:
                            st.session_state["pending_extracted_txns"] = txns
                            bot_reply = f"I extracted {len(txns)} transaction(s) from your input. Please review and confirm below:"
                            st.markdown(bot_reply)
                            st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
                            st.rerun()
                        else:
                            reply = chat_response(user_prompt, df)
                            st.markdown(reply)
                            st.session_state["messages"].append({"role": "assistant", "content": reply})
                else:
                    # Pure financial inquiry / advisory
                    reply = chat_response(user_prompt, df)
                    st.markdown(reply)
                    st.session_state["messages"].append({"role": "assistant", "content": reply})
