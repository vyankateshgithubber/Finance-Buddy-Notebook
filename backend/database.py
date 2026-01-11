import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

DB_FILE = "expense.db"

# Environment for DB (Supabase REST)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

DB_ENGINE: Optional[str] = "supabase"


class Transaction(BaseModel):
    id: int
    timestamp: str
    description: str
    amount: float
    category: str
    split_details: Optional[str] = None


class Category(BaseModel):
    id: int
    name: str
    budget: float


class Debt(BaseModel):
    id: int
    debtor: str
    creditor: str
    amount: float
    description: str
    timestamp: str
    status: str


# --- Supabase REST helpers ---
def _supabase_headers() -> Dict[str, str]:
    if not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_KEY not set")
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def supabase_get(table: str, params: str = "select=*") -> list:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL not set")
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    r = requests.get(url, headers=_supabase_headers())
    r.raise_for_status()
    return r.json()


def supabase_insert(table: str, record) -> list:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL not set")
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    r = requests.post(url, headers={**_supabase_headers(), "Prefer": "return=representation"}, data=json.dumps(record))
    r.raise_for_status()
    return r.json()


def supabase_update(table: str, filters: str, record: dict) -> list:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL not set")
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filters}"
    r = requests.patch(url, headers={**_supabase_headers(), "Prefer": "return=representation"}, data=json.dumps(record))
    r.raise_for_status()
    return r.json()


# --- Connection selection ---
def get_db_connection():
    """Supabase REST only: no direct DB connection.

    This function exists for compatibility but will raise if called.
    Use the Supabase REST helpers instead.
    """
    raise RuntimeError("Supabase REST only - no DB connection available. Use Supabase helpers.")


# --- Initialization ---
def init_db():
    # Supabase-only initialization: ensure category exist
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set for Supabase-only mode.")

    try:
        cats = supabase_get("category", "select=id")
        if not cats:
            defaults = [{"name": n, "budget": b} for (n, b) in [
                ("Dining", 200), ("Groceries", 300), ("Transport", 100),
                ("Entertainment", 150), ("Shopping", 200), ("Bills", 500), ("Others", 100)
            ]]
            supabase_insert("category", defaults)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Supabase tables: {e}")


# --- Tools from Notebook ---
def read_sql_query_tool(query: str) -> str:
    try:
        if not query.strip().upper().startswith("SELECT"):
            return "ERROR: Only SELECT queries are allowed."

        # Supabase simple SELECT support
        if DB_ENGINE == "supabase":
            q = query.strip()
            lower = q.lower()
            import re
            m = re.search(r"from\s+([a-zA-Z_][a-zA-Z0-9_]*)", lower)
            if not m:
                return "ERROR: Unsupported SELECT for Supabase"
            table = m.group(1)
            # simple where -> convert
            wm = re.search(r"where\s+(.+)$", lower)
            params = "select=*"
            if wm:
                clause = wm.group(1).strip()
                # support patterns like "id = 123" or "debtor = 'Me'"
                eq = re.search(r"([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*('?)([^'\s]+)\2", clause)
                if eq:
                    col, _, val = eq.groups()
                    params = f"select=*&{col}=eq.{val}"
            try:
                rows = supabase_get(table, params)
                return str(rows if rows else "No results found.")
            except Exception as e:
                return f"ERROR: Supabase query failed. {e}"

        # Supabase-only: translate simple SELECTs to REST
        try:
            rows = supabase_get(table, params)
            return str(rows if rows else "No results found.")
        except Exception as e:
            return f"ERROR: Supabase query failed. {e}"
    except Exception as e:
        return f"ERROR: Query failed. {str(e)}"


def execute_sql_update_tool(query: str, params: dict = {}) -> dict:
    # Supabase-only update helper.
    # Expects `params` to contain: {"table": "<table>", "filters": "<filters>", "record": {...}}
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"rows_affected": 0, "error": "Supabase not configured."}

    table = params.get("table")
    filters = params.get("filters")
    record = params.get("record")
    if not table or not filters or not isinstance(record, dict):
        return {"rows_affected": 0, "error": "Invalid params. Provide 'table', 'filters', and 'record' in params."}

    try:
        res = supabase_update(table, filters, record)
        # supabase returns updated rows when Prefer=return=representation; count them if list
        count = len(res) if isinstance(res, list) else 0
        return {"rows_affected": count}
    except Exception as e:
        return {"rows_affected": 0, "error": str(e)}


def save_transaction_tool(description: str, amount: float, category: str, split_details: str = "None") -> str:
    if amount <= 0:
        return "ERROR: Amount must be positive."
    if not category or category == "Unknown":
        return "ERROR: Category is missing. Please categorize before saving."

    try:
        # Supabase-only flow
        if not SUPABASE_URL or not SUPABASE_KEY:
            return "ERROR: Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."

        try:
            cats = supabase_get("category", f"select=budget,name&name=eq.{category}")
            if cats:
                budget = float(cats[0].get("budget", 0))
                spent_rows = supabase_get("transaction", f"select=sum(amount)&category=eq.{category}")
                spent = float(spent_rows[0].get("sum", 0)) if spent_rows and isinstance(spent_rows, list) and spent_rows[0].get("sum") is not None else 0
                if spent + float(amount) > budget:
                    budget_msg = f" WARNING: You have exceeded your {category} budget of ${budget}!"
        except Exception:
            pass

        rec = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": description,
            "amount": float(amount),
            "category": category,
            "split_details": split_details,
        }
        try:
            created = supabase_insert("transaction", rec)
            trans_id = created[0].get("id") if created and isinstance(created, list) else None
            return f"SUCCESS: Transaction #{trans_id or ''} saved. {description} - ${amount} ({category}).{budget_msg}"
        except Exception as e:
            return f"ERROR: Failed to save transaction to Supabase. {e}"
        conn.close()
        return f"SUCCESS: Transaction #{trans_id} saved. {description} - ${amount} ({category}).{budget_msg}"

    except Exception as e:
        return f"ERROR: Failed to save transaction. {str(e)}"


def add_debt_tool(debtor: str, creditor: str, amount: float,
                  description: str, status: str) -> str:
    if amount <= 0:
        return "ERROR: Amount must be positive."

    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not SUPABASE_URL or not SUPABASE_KEY:
            return "ERROR: Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY."

        drec = {
            "debtor": debtor.strip(),
            "creditor": creditor.strip(),
            "amount": float(amount),
            "description": description,
            "status": status,
            "timestamp": now,
        }
        try:
            supabase_insert("debt", drec)
            return f"SUCCESS: Recorded that {debtor} owes {creditor} {amount} for {description} ({status})."
        except Exception as e:
            return f"ERROR: Failed to record debt to Supabase. {e}"

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
    """
    High-level tool: expand group expense into one-to-one debts involving Me.

    Args:
        creditors: Comma-separated people who paid (e.g., "Me" or "Me, John").
        debtors: Comma-separated people who did not pay but consumed
                 (e.g., "John, Sarah, Bob" or "Sarah, Bob, Rafael").
        total_amount: Total bill.
        description: What the expense was for.
        status: "unsettled" or "settled".
        split_mode:
            - "equal": equal fair share among all consumers (creditors + debtors).
            - "custom": use fair_shares string.
        fair_shares:
            - For "custom": per-person FAIR share, e.g.
              "Me:205, John:50, Bob:100, Rafael:70, Sarah:75".
        paid_shares:
            - Optional: who actually paid how much, e.g.
              "Me:300, John:200". If omitted:
              - in "equal" mode, assume equal payment among creditors;
              - in "custom" mode, assume each person paid exactly their fair share.
    
    Behavior:
        - Computes net = paid - fair_share for each participant.
        - Builds debts ONLY where ME_NAME is debtor or creditor.
        - Uses add_debt_tool() to insert each edge.
    """
    ME_NAME = "Me"
    
    # 1) Parse lists and normalize "me" -> "Me"
    def normalize_name(n):
        return ME_NAME if n.lower() == "me" else n

    creditor_list = [normalize_name(c.strip()) for c in creditors.split(",") if c.strip()]
    debtor_list = [normalize_name(d.strip()) for d in debtors.split(",") if d.strip()]
    
    # Default to Me as creditor if none specified (common in "split bill" context)
    if not creditor_list:
        creditor_list = [ME_NAME]

    participants = sorted(set(creditor_list + debtor_list))

    if ME_NAME not in participants:
        return "INFO: Me is not part of this transaction; nothing recorded."

    # 2) FAIR SHARE for each participant
    fair = {}

    if split_mode.lower() == "equal":
        per_person = float(total_amount) / len(participants)
        for p in participants:
            fair[p] = per_person
    elif split_mode.lower() == "custom":
        if not fair_shares:
            return "ERROR: fair_shares is required for split_mode='custom'."
        # fair_shares like "Me:205, John:50, Bob:100, Rafael:70, Sarah:75"
        parts = [x.strip() for x in fair_shares.split(",") if x.strip()]
        for part in parts:
            name, val = [x.strip() for x in part.split(":", 1)]
            fair[name] = float(val)
        for p in participants:
            if p not in fair:
                return f"ERROR: No fair share specified for '{p}' in fair_shares."
    else:
        return "ERROR: split_mode must be 'equal' or 'custom'."

    # 3) PAID AMOUNTS
    paid = defaultdict(float)

    if paid_shares:
        # paid_shares like "Me:300, John:200"
        parts = [x.strip() for x in paid_shares.split(",") if x.strip()]
        for part in parts:
            name, val = [x.strip() for x in part.split(":", 1)]
            paid[name] = float(val)
    else:
        if split_mode.lower() == "equal":
            # assume equal payment among creditors
            per_creditor_paid = float(total_amount) / len(creditor_list)
            for c in creditor_list:
                paid[c] = per_creditor_paid
        else:
            # custom mode, assume each pays exactly their fair share
            for p in participants:
                paid[p] = fair.get(p, 0.0)

    # 4) NET position for each participant
    net = {}
    for p in participants:
        net[p] = paid[p] - fair.get(p, 0.0)

    net_me = net.get(ME_NAME, 0.0)
    if abs(net_me) < 1e-6:
        return "INFO: Me is already settled; no debts recorded."

    calls_made = 0

    # Case A: Me is creditor (others owe Me)
    if net_me > 0:
        total_owing = sum(-net[p] for p in participants if net[p] < 0)
        if total_owing <= 0:
            return "INFO: No one owes Me after balancing."

        for p in participants:
            if p == ME_NAME:
                continue
            if net[p] < 0:
                # proportional share of what they owe to Me
                share_to_me = net_me * (-net[p] / total_owing)
                if share_to_me > 0.01:
                    add_debt_tool(
                        debtor=p,
                        creditor=ME_NAME,
                        amount=round(share_to_me, 2),
                        description=description,
                        status=status
                    )
                    calls_made += 1

    # Case B: Me is debtor (I owe others)
    else:
        total_credit = sum(net[p] for p in participants if net[p] > 0)
        if total_credit <= 0:
            return "INFO: Me owes no one after balancing."

        for p in participants:
            if p == ME_NAME:
                continue
            if net[p] > 0:
                share_from_me = (-net_me) * (net[p] / total_credit)
                if share_from_me > 0.01:
                    add_debt_tool(
                        debtor=ME_NAME,
                        creditor=p,
                        amount=round(share_from_me, 2),
                        description=description,
                        status=status
                    )
                    calls_made += 1

    return f"SUCCESS: Recorded {calls_made} debt edges involving Me for '{description}'."

# --- Helper functions for API ---

def get_all_transactions() -> List[Dict]:
    try:
        rows = supabase_get('transaction', 'select=*&order=id.desc')
        return rows
    except Exception:
        return []

def get_category_totals() -> List[Dict]:
    try:
        rows = supabase_get('transaction', 'select=category,sum(amount)::numeric as total&group=category')
        return rows
    except Exception:
        return []

def get_dashboard_stats() -> Dict[str, float]:
    try:
        # 1. Total Spent (All time for now, ideally current month)
        # For simplicity, let's just sum all transactions.
        # To do current month: add filter on timestamp
        spent_rows = supabase_get('transaction', 'select=sum(amount)')
        total_spent = float(spent_rows[0].get('sum', 0)) if spent_rows and spent_rows[0].get('sum') is not None else 0.0
        
        # 2. Total Budget
        budget_rows = supabase_get('category', 'select=sum(budget)')
        total_budget = float(budget_rows[0].get('sum', 0)) if budget_rows and budget_rows[0].get('sum') is not None else 0.0
        
        # 3. Active Debts (Money owed TO Me)
        # creditor = 'Me' AND status = 'unsettled'
        debt_rows = supabase_get('debt', 'select=sum(amount)&creditor=eq.Me&status=eq.unsettled')
        active_debts = float(debt_rows[0].get('sum', 0)) if debt_rows and debt_rows[0].get('sum') is not None else 0.0
        
        return {
            "total_spent": total_spent,
            "budget": total_budget,
            "remaining": total_budget - total_spent,
            "active_debts": active_debts
        }
    except Exception as e:
        # In case of error, return zeros
        return {
            "total_spent": 0.0,
            "budget": 0.0,
            "remaining": 0.0,
            "active_debts": 0.0
        }
