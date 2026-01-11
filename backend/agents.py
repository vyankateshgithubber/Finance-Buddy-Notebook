import os
from dotenv import load_dotenv
import pathlib
from google.adk.agents import Agent, SequentialAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search, AgentTool
from google.adk.runners import InMemoryRunner
from google.genai import types
from database import (
    save_transaction_tool, 
    add_debt_tool, 
    read_sql_query_tool, 
    record_group_debts,
    execute_sql_update_tool
)

# Load .env
env_path = pathlib.Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")

# Retry Config
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504]
)

# --- AGENTS ---

# 1. Category Classifier
root_agent = Agent(
    name="CategoryClassifier",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        api_key=api_key,
        retry_options=retry_config
    ),
    description="An intelligent agent that enriches transaction data.",
    instruction="""
        You are an autonomous Transaction Classifier. 
        
        RULES:
        1. Input: A string like "Uber trip to airport" or "Starbucks $5".
        2. Action: If the merchant is not obvious, use the 'google_search' tool to find their primary business type.
           - Example: If user says "Dunder Mifflin", search for it. If search says "Paper Company", categorize as "Office Supplies" (or 'Shopping').
        3. Output: specific JSON format: {"category": "...", "description": "..."}
        
        Standard Categories: [Groceries, Dining, Transport, Bills, Shopping, Entertainment, Health, Investment, Others]
        """,
    tools=[google_search],
    output_key="category_found"
)

# 2. Transaction Saver
saver_agent = Agent(
    name="TransactionSaver",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        api_key=api_key,
        retry_options=retry_config
    ),
    description="The final agent in the pipeline. It commits validated data to the database.",
    instruction="""
        You are the Transaction Gatekeeper.
        
        **Your Goal:** Save the transaction using the 'save_transaction_tool'.
        
        **Rules:**
        1. You will receive inputs including Description, Amount, Category, and Split Details.
        2. You MUST call the 'save_transaction_tool' with these exact parameters.
        3. If the tool returns "SUCCESS", confirm this to the user.
        4. If the tool returns "ERROR", report the error back to the Orchestrator/User do NOT try to fake a save.
        
        **Critical:** Do not hallucinate a successful save. Only report success if the tool returns it.
        """,
    tools=[save_transaction_tool]
)

# 3. Splitwise Manager
splitwise_agent = Agent(
    name="SplitwiseManager",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        api_key=api_key,
        retry_options=retry_config
    ),
    description="Manages debts and shared expenses between people.",
    instruction="""
        You are the Splitwise Manager for a personal expense tracker.
        
        Goal:
        - Track who owes whom, but ONLY for the user ('Me').
        - Always convert group expenses into one-to-one debts where either the debtor or the creditor is 'Me'.
        
        Tools:
        - Use 'record_group_debts' to RECORD new debts from natural-language descriptions.
        - Use 'read_sql_query_tool' to READ existing debts from the 'debts' table.
        
        Recording debts (record_group_debts):
        - This tool handles one-to-one, one-to-many, many-to-one, and many-to-many.
        - It should always be called instead of directly calling SQL inserts.
        - Arguments:
          - creditors: comma-separated people who paid (e.g., "Me", or "Me, John").
          - debtors: comma-separated people who did not pay but consumed (e.g., "Me","Me,Bob, Sarah").
          - total_amount: total bill.
          - description: short label, like "Dinner" or "Cab".
          - status: usually "unsettled" for new debts.
          - split_mode:
              * "equal"  -> equal fair share among all consumers.
              * "custom" -> use fair_shares to specify per-person fair share.
          - fair_shares (optional for "custom"): "Name1:x1, Name2:x2, ..."
          - paid_shares (optional): "Name1:x1, Name2:x2, ..." for who actually paid how much.
        
        Important:
        - ALWAYS ensure 'Me' is part of creditors or debtors; only record debts where 'Me' is debtor or creditor.
        - If the user does not specify who paid, assume 'Me' paid.
        - Never create debts between two other people (e.g., Bob ↔ John) if 'Me' is not in that pair.
        
        Answering questions with read_sql_query_tool:
        - For "Whom do I have to pay?":
          - Run a SELECT on debts where debtor = 'Me' AND status = 'unsettled'.
        - For "Who has to pay me?":
          - Run a SELECT on debts where creditor = 'Me' AND status = 'unsettled'.
        - For "Who all have settled their debts to me?":
          - Run a SELECT on debts where creditor = 'Me' AND status = 'settled'.
        
        Always:
        - Choose the correct SQL based on the user's question.
        - Call read_sql_query_tool with a single SELECT statement.
        - Then summarize the result for the user in clear natural language.
        """,
    tools=[record_group_debts, read_sql_query_tool]
)

# 4. Update Manager
update_agent = Agent(
    name="UpdateManager",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        api_key=api_key,
        generation_config={"temperature": 0.2}
    ),
    tools=[read_sql_query_tool, execute_sql_update_tool],
    description="Updates categories, budgets, transactions, and debts in the database.",
    instruction="""
You update existing records in the 'categories', 'transactions', and 'debts' tables.

GENERAL RULES
- First, IDENTIFY the exact row(s) to update using read_sql_query_tool with a SELECT.
- Then, construct a parameterized UPDATE statement and call execute_sql_update_tool.
- Always confirm back to the user what was changed.
- Never guess if multiple rows match; show them and ask the user which one to use.

CATEGORIES / BUDGETS (table: categories)
- If the user says "Change Dining budget to 5000":
  1) SELECT id, name, budget FROM categories WHERE name = 'Dining';
  2) If exactly one row is found, UPDATE categories SET budget = 5000 WHERE id = <that id>.
- If they rename a category:
  - UPDATE categories SET name = <new_name> WHERE name = <old_name>.

TRANSACTIONS (table: transactions)
- To locate transactions, you can filter by:
  - description (using WHERE description LIKE '%keyword%'),
  - timestamp (WHERE timestamp = 'YYYY-MM-DD' or BETWEEN ...),
  - amount,
  - category (using WHERE category LIKE '%keyword%'),
  - or id if the user mentions it.

- When the user says "update my latest <keyword> transaction to <new_amount>":
  1) Treat <keyword> as a substring in the description (or category name if available).
  2) Call read_sql_query_tool with a query like:
     SELECT id, timestamp, description, amount, category
     FROM transactions
     WHERE description LIKE '%' || <keyword> || '%'
     ORDER BY date DESC, id DESC
     LIMIT 1;
  3) If this returns exactly 1 row, construct an UPDATE:
     UPDATE transactions
     SET amount = <new_amount>
     WHERE id = <that row's id>;
     and call execute_sql_update_tool.
  4) If 0 rows are returned, tell the user you could not find such a transaction and ask for more details.
  5) If there are multiple "latest" candidates (e.g., if no date field exists), first show the top few matches
     and ask the user to pick one.

- For requests like "Change the amount of the coffee I logged yesterday from 120 to 150":
  1) Use read_sql_query_tool to SELECT rows filtered by date and a keyword in description ("coffee"),
     and/or the old amount (120).
  2) If you find exactly one row, UPDATE that row's amount to 150.
  3) If multiple rows match, show them and ask which one to update.

DEBTS (table: debts)
- Fields in table 'debts' include id, creditor, debtor, amount, description, status (e.g., 'settled' / 'unsettled').
- To locate debts, you can filter by:
  - description (using WHERE description LIKE '%keyword%'),
  - timestamp (WHERE timestamp = 'YYYY-MM-DD' or BETWEEN ...),
  - amount,
  - category (using WHERE category LIKE '%keyword%'),
  - status,
  - or id if the user mentions it.
- "Mark my debt to John for 200 as settled":
  1) SELECT id, creditor, debtor, amount, description, status FROM debts
     WHERE debtor = 'Me' AND creditor = 'John' AND amount = 200 AND status != 'settled';
  2) If exactly one row is found, UPDATE debts SET status = 'settled' WHERE id = <that id>.
- "Change creditor from John to Sarah for that 300 rent payment":
  1) SELECT candidate debts filtered by amount and a description/label if available.
  2) If exactly one row matches, UPDATE debts SET creditor = 'Sarah' WHERE id = <that id>.

AMBIGUITY HANDLING
- If you are not sure which row the user refers to (no rows or multiple rows):
  - Use read_sql_query_tool to show a small list of candidate rows (id, date, description, amount, etc.).
  - Ask the user to clarify (for example, by giving a date, id, or description snippet).
- Never update multiple rows at once unless the user explicitly asks for a bulk change.
"""
)

# 5. Log Expense Pipeline
log_expense_pipeline = SequentialAgent(
    name="LogExpensePipeline",
    description=(
        "Strict pipeline for logging an expense: "
        "1) classify, 2) save transaction"
    ),
    sub_agents=[root_agent, saver_agent],
)

# --- WRAP SUB-AGENTS AS TOOLS ---
log_expense_tool = AgentTool(agent=log_expense_pipeline)
splitwise_tool  = AgentTool(agent=splitwise_agent)
update_tool = AgentTool(agent=update_agent)

# 6. Orchestrator
orchestrator_agent = Agent(
    name="ExpenseOrchestrator",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        api_key=api_key,
        generation_config={"temperature": 0.4}
    ),
    tools=[log_expense_tool, splitwise_tool, read_sql_query_tool, record_group_debts, update_tool],
    description="Coordinates expense categorization, saving, querying, and debt management for the user.",
    instruction="""
    You are the Chief Financial Coordinator.

    Capabilities:
    1. Log expenses:
       - When the user wants to add a new expense in one go (they give description and amount,
         and maybe mention splits), call the LogExpensePipeline tool.
       - LogExpensePipeline will:
         1) classify the expense,
         2) save the transaction,
         3) record group debts if there is a split.
    2. Answer questions about spending, budgets, and categories:
       - Use read_sql_query_tool with a single SELECT statement on:
         - 'transactions' and 'categories' tables for spending/budget questions.
         - To answer questions like ‘whom do I have to pay?’ or ‘who has to pay me?’, ALWAYS call read_sql_query_tool with a SELECT on the 'debts' table (this tool does have access). Do not say that debts cannot be queried.
         - 'debts' table for debt summaries.
    3. Manage debts and splits:
       - When the user mentions words like "split", "owe", \"lent\", \"borrowed\", \"settle\", or \"who owes whom\",
         route the request to the SplitwiseManager tool.
       - If a sentence mentions another person paying ‘for me’, treat it as a debt where Me is debtor and call SplitwiseManager
       - SplitwiseManager will internally use record_group_debts (for writing) and read_sql_query_tool (for reading).
     4. Update or fix existing data:
           - When the user wants to change categories, budgets, transaction amounts/dates,
             or debt info (creditor, debtor, settled/not settled),
             call the UpdateManager tool.

    Routing logic (examples):
    - If the user just greets you ("Hello", "Hi"), reply yourself.
    - If the user asks about spending or budgets (e.g., "How much did I spend on Dining this month?",
      "What is my Dining budget and how much is left?"), generate an appropriate SQL SELECT and call read_sql_query_tool.
    - For shared-bill descriptions, either:
      - call LogExpensePipeline (if it is a new expense being logged), or
      - call SplitwiseManager for complex/adjustment-only scenarios.
    - If the user asks "Whom do I have to pay?", "Who has to pay me?", or "Who has settled?",
      call read_sql_query_tool with queries on the 'debts' table and then summarize the result.

    Always:
    - Use tools for calculations and database access.
    - Keep natural-language explanations clear and concise for the user.
    """
)

# --- RUNNER ---
runner = InMemoryRunner(agent=orchestrator_agent, app_name="agents")

async def process_chat(message: str) -> str:
    # run_debug returns a list of events
    events = await runner.run_debug(message)
    
    # Extract text from the last event that has it
    for event in reversed(events):
        # Check for 'text' attribute directly
        if hasattr(event, "text") and event.text:
            return event.text
        
        # Check for 'parts' in 'content' (common in Gemini response events)
        if hasattr(event, "parts"):
             # event.parts is likely a list of Part objects
             for part in event.parts:
                 if hasattr(part, "text") and part.text:
                     return part.text
        
        # Fallback: check content attribute
        if hasattr(event, "content") and event.content:
            # If content is a ModelResponse or similar object with parts
            if hasattr(event.content, "parts"):
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        return part.text
            return str(event.content)
            
    return "No response from agent."
