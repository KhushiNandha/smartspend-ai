"""
SmartSpend AI - Database persistence layer using SQLite.
Supports session isolation, auto-seeding with realistic INR demo data,
transactions, savings goals, and category budgets.
"""

import os
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "smartspend.db")
DEMO_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "demo_data.csv")

def get_connection() -> sqlite3.Connection:
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if tables do not exist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'demo_user',
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                amount REAL NOT NULL,
                payment_mode TEXT DEFAULT 'UPI',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'demo_user',
                title TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL NOT NULL DEFAULT 0.0,
                target_date TEXT NOT NULL,
                category TEXT DEFAULT 'Savings',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Budgets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL DEFAULT 'demo_user',
                category TEXT NOT NULL,
                monthly_limit REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id, category)
            )
        """)
        
        conn.commit()

def seed_demo_data(session_id: str = "demo_user", force: bool = False) -> int:
    """
    Seeds the database with 6 months of realistic INR data from demo_data.csv.
    If force is False, only seeds if the session has 0 transactions.
    """
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if not force:
            cursor.execute("SELECT COUNT(*) FROM transactions WHERE session_id = ?", (session_id,))
            count = cursor.fetchone()[0]
            if count > 0:
                return count

        # If force, clear existing for this session
        if force:
            cursor.execute("DELETE FROM transactions WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM goals WHERE session_id = ?", (session_id,))
            cursor.execute("DELETE FROM budgets WHERE session_id = ?", (session_id,))
            conn.commit()

        # Load CSV
        if not os.path.exists(DEMO_CSV_PATH):
            return 0
            
        df = pd.read_csv(DEMO_CSV_PATH)
        records = df.to_dict(orient="records")
        
        for r in records:
            cursor.execute("""
                INSERT INTO transactions (session_id, date, description, category, type, amount, payment_mode, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                r.get("date"),
                r.get("description"),
                r.get("category"),
                r.get("type", "expense"),
                float(r.get("amount", 0.0)),
                r.get("payment_mode", "UPI"),
                r.get("notes", "")
            ))
            
        # Seed default goals
        default_goals = [
            ("Emergency Fund (6 Months)", 150000.0, 95000.0, "2026-12-31", "Safety"),
            ("New iPhone / Laptop Upgrade", 65000.0, 32000.0, "2026-11-15", "Tech"),
            ("Bali Vacation Trip", 80000.0, 45000.0, "2027-02-28", "Travel")
        ]
        for title, target, current, target_date, cat in default_goals:
            cursor.execute("""
                INSERT INTO goals (session_id, title, target_amount, current_amount, target_date, category)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, title, target, current, target_date, cat))
            
        # Seed default category budgets
        default_budgets = [
            ("Food & Dining", 15000.0),
            ("Shopping", 10000.0),
            ("Groceries", 12000.0),
            ("Travel & Commute", 8000.0),
            ("Bills & Utilities", 6000.0),
            ("Entertainment", 4000.0)
        ]
        for cat, limit in default_budgets:
            cursor.execute("""
                INSERT OR REPLACE INTO budgets (session_id, category, monthly_limit)
                VALUES (?, ?, ?)
            """, (session_id, cat, limit))

        conn.commit()
        return len(records)

def clear_session_data(session_id: str = "demo_user"):
    """Resets transactions, goals, and budgets for a specific session."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM goals WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM budgets WHERE session_id = ?", (session_id,))
        conn.commit()

def add_transaction(session_id: str, date: str, description: str, category: str, 
                    type_: str, amount: float, payment_mode: str = "UPI", notes: str = "") -> int:
    """Adds a single transaction and returns its ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (session_id, date, description, category, type, amount, payment_mode, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, date, description, category, type_, float(amount), payment_mode, notes))
        conn.commit()
        return cursor.lastrowid

def add_transactions_batch(session_id: str, transactions: List[Dict[str, Any]]) -> int:
    """Adds multiple transactions in a single transaction block."""
    if not transactions:
        return 0
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        count = 0
        for t in transactions:
            cursor.execute("""
                INSERT INTO transactions (session_id, date, description, category, type, amount, payment_mode, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                t.get("date", datetime.today().strftime("%Y-%m-%d")),
                t.get("description", "Unknown Expense"),
                t.get("category", "Other"),
                t.get("type", "expense"),
                float(t.get("amount", 0.0)),
                t.get("payment_mode", "UPI"),
                t.get("notes", "")
            ))
            count += 1
        conn.commit()
        return count

def delete_transaction(transaction_id: int, session_id: str) -> bool:
    """Deletes a transaction by ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ? AND session_id = ?", (transaction_id, session_id))
        conn.commit()
        return cursor.rowcount > 0

def get_transactions_df(session_id: str, start_date: Optional[str] = None, 
                        end_date: Optional[str] = None, category: Optional[str] = None) -> pd.DataFrame:
    """Returns transactions as a Pandas DataFrame with optional filters."""
    init_db()
    with get_connection() as conn:
        query = "SELECT id, date, description, category, type, amount, payment_mode, notes FROM transactions WHERE session_id = ?"
        params: List[Any] = [session_id]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if category and category != "All":
            query += " AND category = ?"
            params.append(category)
            
        query += " ORDER BY date DESC, id DESC"
        
        df = pd.read_sql_query(query, conn, params=params)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df

def get_goals(session_id: str) -> List[Dict[str, Any]]:
    """Retrieves all savings goals for a session."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, target_amount, current_amount, target_date, category, notes 
            FROM goals WHERE session_id = ? ORDER BY target_date ASC
        """, (session_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def add_goal(session_id: str, title: str, target_amount: float, 
             current_amount: float, target_date: str, category: str = "Savings") -> int:
    """Adds a new savings goal."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO goals (session_id, title, target_amount, current_amount, target_date, category)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, title, float(target_amount), float(current_amount), target_date, category))
        conn.commit()
        return cursor.lastrowid

def update_goal(goal_id: int, session_id: str, current_amount: float) -> bool:
    """Updates current saved amount for a goal."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE goals SET current_amount = ? WHERE id = ? AND session_id = ?
        """, (float(current_amount), goal_id, session_id))
        conn.commit()
        return cursor.rowcount > 0

def delete_goal(goal_id: int, session_id: str) -> bool:
    """Deletes a savings goal."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM goals WHERE id = ? AND session_id = ?", (goal_id, session_id))
        conn.commit()
        return cursor.rowcount > 0

def get_budgets(session_id: str) -> Dict[str, float]:
    """Retrieves category budgets as a dictionary of {category: monthly_limit}."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT category, monthly_limit FROM budgets WHERE session_id = ?", (session_id,))
        rows = cursor.fetchall()
        return {r["category"]: float(r["monthly_limit"]) for r in rows}

def set_budget(session_id: str, category: str, monthly_limit: float):
    """Sets or updates the monthly budget limit for a category."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO budgets (session_id, category, monthly_limit)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit
        """, (session_id, category, float(monthly_limit)))
        conn.commit()
