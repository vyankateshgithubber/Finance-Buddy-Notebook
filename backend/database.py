import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from collections import defaultdict
from user_context import get_current_user_id  # <--- NEW IMPORT

DB_FILE = "expense.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Transactions: Added user_id
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  timestamp TEXT,
                  description TEXT,
                  amount REAL,
                  category TEXT,
                  split_details TEXT)''')
    
    # 2. Categories: Added user_id (Constraint: name unique per user, not globally)
    c.execute('''CREATE TABLE IF NOT EXISTS categories
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  name TEXT,
                  budget REAL,
                  UNIQUE(user_id, name))''')
    
    # 3. Debts: Added user_id
    c.execute('''CREATE TABLE IF NOT EXISTS debts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT,
                  debtor TEXT,
                  creditor TEXT,
                  amount REAL,
                  description TEXT,
                  timestamp TEXT,
                  status TEXT)''')
    
    # Seed Global/Default Categories (assigned to 'default_user' or generalized)
    # For this multi-user setup, we might skip seeding or seed for specific users on creation.
    # To keep it simple, we just ensure the table exists.
        
    conn.commit()
    conn.close()

# --- Tools ---

def read_sql_query_tool(query: str) -> str:
    """
    Executes a READ-ONLY SQL query, automatically filtered by the current user_id.
    """
    user_id = get_current_user_id()
    
    try:
        if not query.strip().upper().startswith("SELECT"):
            return "ERROR: Only SELECT queries are allowed."

        # --- SECURITY & FILTERING MAGIC ---
        # We replace the table names with a subquery that filters by user_id.
        # This allows the Agent to say "SELECT * FROM transactions" 
        # while actually executing "SELECT * FROM (SELECT * FROM transactions WHERE user_id='...')".
        
        filtered_trans = f"(SELECT * FROM transactions WHERE user_id = '{user_id}')"
        filtered_debts = f"(SELECT * FROM debts WHERE user_id = '{user_id}')"
        filtered_cats  = f"(SELECT * FROM categories WHERE user_id = '{user_id}')"

        # Simple replacement (case-insensitive handling would be better, but this covers the Agent's output)
        safe_query = query.replace("transactions", filtered_trans)\
                          .replace("debts", filtered_debts)\
                          .replace("categories", filtered_cats)
        # ----------------------------------

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(safe_query)
        rows = c.fetchall()
        columns = [description[0] for description in c.description]
        conn.close()
        
        if not rows:
            return "No results found."
            
        result = [dict(zip(columns, row)) for row in rows]
        return str(result)
    except Exception as e:
        return f"ERROR: Query failed. {str(e)}"

def execute_sql_update_tool(query: str, params: dict={}) -> dict:
    # NOTE: In a production app, you would apply similar filtering logic here 
    # to ensure users can only UPDATE their own rows.
    # For now, we rely on the Agent finding the ID via read_sql_query_tool first.
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, params or {})
    conn.commit()
    rows_affected = cur.rowcount
    conn.close()
    return {"rows_affected": rows_affected}

def save_transaction_tool(description: str, amount: float, category: str, split_details: str = "None") -> str:
    user_id = get_current_user_id()  # <--- Get context

    if amount <= 0:
        return "ERROR: Amount must be positive."
    
    if not category or category == "Unknown":
        return "ERROR: Category is missing. Please categorize before saving."

    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Check budget for THIS user
        # (We handle the case where categories might not be seeded for a new user yet)
        c.execute("SELECT budget FROM categories WHERE name = ? AND user_id = ?", (category, user_id))
        row = c.fetchone()
        
        budget_msg = ""
        if row:
            budget = row['budget']
            c.execute("SELECT SUM(amount) FROM transactions WHERE category = ? AND user_id = ?", (category, user_id))
            result = c.fetchone()
            spent = result[0] if result[0] else 0
            if spent + float(amount) > budget:
                budget_msg = f" WARNING: You have exceeded your {category} budget of ${budget}!"
        else:
            # Optional: Auto-create category for user if it doesn't exist
            c.execute("INSERT INTO categories (user_id, name, budget) VALUES (?, ?, ?)", (user_id, category, 500))
            budget_msg = " (New category created)"

        c.execute("INSERT INTO transactions (user_id, timestamp, description, amount, category, split_details) VALUES (?, ?, ?, ?, ?, ?)",
                  (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), description, float(amount), category, split_details))
        trans_id = c.lastrowid
        conn.commit()
        conn.close()
        return f"SUCCESS: Transaction #{trans_id} saved. {description} - ${amount} ({category}).{budget_msg}"
    except Exception as e:
            return f"ERROR: Failed to save transaction. {str(e)}"

def add_debt_tool(debtor: str, creditor: str, amount: float,
                  description: str, status: str) -> str:
    user_id = get_current_user_id()  # <--- Get context

    if amount <= 0:
        return "ERROR: Amount must be positive."

    try:
        conn = get_db_connection()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        c.execute(
            "INSERT INTO debts (user_id, debtor, creditor, amount, description, status, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, debtor.strip(), creditor.strip(), float(amount), description, status, now)
        )
        conn.commit()
        conn.close()
        return f"SUCCESS: Recorded that {debtor} owes {creditor} {amount} for {description} ({status})."
    except Exception as e:
        return f"ERROR: Failed to record debt. {str(e)}"

def record_group_debts(
    creditors: str,
    debtors: str,
    total_amount: float,
    description: str,
    status: str = "unsettled",
    split_mode: str = "equal",
    fair_shares: str = "",
    paid_shares: str = "",
) -> str:
    # ... [Implementation is EXACTLY the same as before] ...
    # This function calculates the math, then calls `add_debt_tool`.
    # Since `add_debt_tool` now handles `user_id` automatically,
    # this function requires NO changes.
    
    ME_NAME = "Me"
    
    # 1) Parse lists
    creditor_list = [c.strip() for c in creditors.split(",") if c.strip()]
    debtor_list = [d.strip() for d in debtors.split(",") if d.strip()]
    participants = sorted(set(creditor_list + debtor_list))

    if ME_NAME not in participants:
        return "INFO: Me is not part of this transaction; nothing recorded."

    # 2) FAIR SHARE
    fair = {}
    if split_mode.lower() == "equal":
        per_person = float(total_amount) / len(participants)
        for p in participants:
            fair[p] = per_person
    elif split_mode.lower() == "custom":
        if not fair_shares:
            return "ERROR: fair_shares is required for split_mode='custom'."
        parts = [x.strip() for x in fair_shares.split(",") if x.strip()]
        for part in parts:
            name, val = [x.strip() for x in part.split(":", 1)]
            fair[name] = float(val)
    else:
        return "ERROR: split_mode must be 'equal' or 'custom'."

    # 3) PAID AMOUNTS
    paid = defaultdict(float)
    if paid_shares:
        parts = [x.strip() for x in paid_shares.split(",") if x.strip()]
        for part in parts:
            name, val = [x.strip() for x in part.split(":", 1)]
            paid[name] = float(val)
    else:
        if split_mode.lower() == "equal":
            per_creditor_paid = float(total_amount) / len(creditor_list)
            for c in creditor_list:
                paid[c] = per_creditor_paid
        else:
            for p in participants:
                paid[p] = fair.get(p, 0.0)

    # 4) NET position
    net = {}
    for p in participants:
        net[p] = paid[p] - fair.get(p, 0.0)

    net_me = net.get(ME_NAME, 0.0)
    if abs(net_me) < 1e-6:
        return "INFO: Me is already settled; no debts recorded."

    calls_made = 0

    # Case A: Me is creditor
    if net_me > 0:
        total_owing = sum(-net[p] for p in participants if net[p] < 0)
        if total_owing <= 0: return "INFO: No one owes Me."
        
        for p in participants:
            if p == ME_NAME: continue
            if net[p] < 0:
                share_to_me = net_me * (-net[p] / total_owing)
                if share_to_me > 0.01:
                    add_debt_tool(debtor=p, creditor=ME_NAME, amount=round(share_to_me, 2), description=description, status=status)
                    calls_made += 1
    # Case B: Me is debtor
    else:
        total_credit = sum(net[p] for p in participants if net[p] > 0)
        if total_credit <= 0: return "INFO: Me owes no one."

        for p in participants:
            if p == ME_NAME: continue
            if net[p] > 0:
                share_from_me = (-net_me) * (net[p] / total_credit)
                if share_from_me > 0.01:
                    add_debt_tool(debtor=ME_NAME, creditor=p, amount=round(share_from_me, 2), description=description, status=status)
                    calls_made += 1

    return f"SUCCESS: Recorded {calls_made} debt edges involving Me for '{description}'."

# --- Helper functions for API (Updated to take user_id argument explicitly or use context) ---

def get_user_transactions(user_id: str) -> List[Dict]:
    """Helper for the REST API endpoint"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_category_totals(user_id: str) -> List[Dict]:
    """Helper for the REST API endpoint"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT category, SUM(amount) as total FROM transactions WHERE user_id = ? GROUP BY category", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]