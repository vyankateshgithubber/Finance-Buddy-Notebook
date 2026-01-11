import requests
import sqlite3
import time

API_URL = "http://127.0.0.1:8000/chat"

def send_message(message):
    print(f"\nUser: {message}")
    try:
        response = requests.post(API_URL, json={"message": message})
        if response.status_code == 200:
            print(f"Bot: {response.json()['response']}")
            return response.json()['response']
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def verify_db(query):
    print(f"DB Check ({query}):")
    try:
        conn = sqlite3.connect("expense.db")
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        print(rows)
        conn.close()
        return rows
    except Exception as e:
        print(f"DB Error: {e}")
        return []

def main():
    print("--- Starting Verification ---")
    
    # 1. Add Expense
    print("\n--- Test 1: Add Expense ---")
    send_message("I spent 250/- on Lunch at Subway")
    time.sleep(2)
    verify_db("SELECT * FROM transactions ORDER BY id DESC LIMIT 1")

    # 2. Split Expense
    print("\n--- Test 2: Split Expense ---")
    send_message("I paid 300/- for dinner for Me, John and Sarah split equally")
    time.sleep(2)
    verify_db("SELECT * FROM debts ORDER BY id DESC LIMIT 3")

    # 3. Insights
    print("\n--- Test 3: Insights ---")
    send_message("How much did I spend on Dining?")
    
    # 4. Update Transaction
    print("\n--- Test 4: Update Transaction ---")
    # First, get the last transaction ID to be specific, or just rely on description
    send_message("Update my latest Subway transaction to 30")
    time.sleep(2)
    verify_db("SELECT * FROM transactions WHERE description LIKE '%Subway%' ORDER BY id DESC LIMIT 1")

if __name__ == "__main__":
    main()
