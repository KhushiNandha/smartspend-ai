"""
Unit tests for SQLite database operations and seeding in SmartSpend AI.
"""

import pytest
import os
from core.database import (
    init_db, seed_demo_data, clear_session_data, add_transaction,
    add_transactions_batch, delete_transaction, get_transactions_df,
    get_goals, add_goal, update_goal, delete_goal, get_budgets, set_budget
)

TEST_SESSION = "test_user_pytest"

def test_database_lifecycle():
    # 1. Init & Clear
    init_db()
    clear_session_data(TEST_SESSION)
    df_empty = get_transactions_df(TEST_SESSION)
    assert df_empty.empty

    # 2. Add single transaction
    t_id = add_transaction(
        session_id=TEST_SESSION,
        date="2026-09-20",
        description="Blue Tokai Coffee",
        category="Food & Dining",
        type_="expense",
        amount=380.0,
        payment_mode="UPI"
    )
    assert t_id > 0
    df = get_transactions_df(TEST_SESSION)
    assert len(df) == 1
    assert df.iloc[0]["amount"] == 380.0

    # 3. Batch add
    batch = [
        {"date": "2026-09-21", "description": "Blinkit grocery", "category": "Groceries", "type": "expense", "amount": 1250.0},
        {"date": "2026-09-22", "description": "Freelance project", "category": "Freelance", "type": "income", "amount": 15000.0}
    ]
    batch_count = add_transactions_batch(TEST_SESSION, batch)
    assert batch_count == 2
    assert len(get_transactions_df(TEST_SESSION)) == 3

    # 4. Delete single
    del_ok = delete_transaction(t_id, TEST_SESSION)
    assert del_ok is True
    assert len(get_transactions_df(TEST_SESSION)) == 2

    # 5. Goals CRUD
    g_id = add_goal(TEST_SESSION, "New Bike", 120000.0, 30000.0, "2027-01-31", "Vehicle")
    assert g_id > 0
    goals = get_goals(TEST_SESSION)
    assert len(goals) == 1
    assert goals[0]["title"] == "New Bike"

    update_goal(g_id, TEST_SESSION, 35000.0)
    goals_updated = get_goals(TEST_SESSION)
    assert goals_updated[0]["current_amount"] == 35000.0

    delete_goal(g_id, TEST_SESSION)
    assert len(get_goals(TEST_SESSION)) == 0

    # 6. Budgets
    set_budget(TEST_SESSION, "Food & Dining", 12000.0)
    budgets = get_budgets(TEST_SESSION)
    assert budgets["Food & Dining"] == 12000.0

    # 7. Demo Seeding
    seeded_count = seed_demo_data(session_id=TEST_SESSION, force=True)
    assert seeded_count > 100
    df_seeded = get_transactions_df(TEST_SESSION)
    assert len(df_seeded) == seeded_count

    # Cleanup
    clear_session_data(TEST_SESSION)
