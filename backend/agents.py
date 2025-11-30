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
        1. You will receive inputs including Description, Amount, Category, Split Details and transaction_type (either 'debit' or 'credit').
        2. If transaction_type is not provided, default to 'debit' if user is paying or lending money (losing money) in transaction. Use 'credit' when the user clearly receives money (Example : refunds, salary, friend paying you back) .
        3. You MUST call the 'save_transaction_tool' with these exact parameters.
        4. If the tool returns "SUCCESS", confirm this to the user.
        5. If the tool returns "ERROR", report the error back to the Orchestrator/User do NOT try to fake a save.      
        
        **Critical:** Do not hallucinate a successful save. Only report success if the tool returns it.
        """,
    tools=[save_transaction_tool]
)

# 3. Splitwise Manager
s# --- SPLITWISE AGENT ---
splitwise_agent = Agent(
    name="SplitwiseManager",
    model=Gemini(
        model="gemini-2.5-flash-lite",
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
        
        Work through these examples:
        
        1) Example 1: "I paid 200/- for John, Sarah and Bob and to be split equally."
           - creditors="Me"
           - debtors="John, Sarah, Bob"
           - total_amount=200
           - split_mode="equal"
           Call:
           record_group_debts(
               creditors="Me",
               debtors="John, Sarah, Bob",
               total_amount=200,
               description="Dinner",
               status="unsettled",
               split_mode="equal"
           )
        
        2) Example 2: "I paid 200 for John, Sarah and Bob where Bob owes 60, Sarah 40 and John 20."
           - You already know each person's FAIR SHARE.
           - creditors="Me"
           - debtors="John, Sarah, Bob"
           - total_amount=200
           - split_mode="custom"
           - fair_shares="Me:80, Bob:60, Sarah:40, John:20" (must sum to 200)
           - paid_shares="Me:200"
           Call:
           record_group_debts(
               creditors="Me",
               debtors="John, Sarah, Bob",
               total_amount=200,
               description="Dinner",
               status="unsettled",
               split_mode="custom",
               fair_shares="Me:80, Bob:60, Sarah:40, John:20",
               paid_shares="Me:200"
           )
        
        3) Example 3: "I and John paid 500 total for Sarah, Bob and Rafael where I and John paid 250 each, split equally for all."
           - creditors="Me, John"
           - debtors="Sarah, Bob, Rafael"
           - total_amount=500
           - split_mode="equal"
           - paid_shares="Me:250, John:250"
           Call:
           record_group_debts(
               creditors="Me, John",
               debtors="Sarah, Bob, Rafael",
               total_amount=500,
               description="Dinner",
               status="unsettled",
               split_mode="equal",
               paid_shares="Me:250, John:250"
           )
        
        4) Example 4: "I and John paid 500 for Sarah, Bob and Rafael where I and John paid 300, 200 respectively, split equally for all."
           - creditors="Me, John"
           - debtors="Sarah, Bob, Rafael"
           - total_amount=500
           - split_mode="equal"
           - paid_shares="Me:300, John:200"
           Call:
           record_group_debts(
               creditors="Me, John",
               debtors="Sarah, Bob, Rafael",
               total_amount=500,
               description="Dinner",
               status="unsettled",
               split_mode="equal",
               paid_shares="Me:300, John:200"
           )
        
        5) Example 5: "I and John paid 500 for Sarah, Bob and Rafael where I and John paid 300, 200 respectively, here Bob owes 100, Rafael owes 70, Sarah owes 75, John owes 50 and I owe 205."
           - These numbers represent each person's FAIR SHARE.
           - creditors="Me, John"
           - debtors="Sarah, Bob, Rafael"
           - total_amount=500
           - split_mode="custom"
           - fair_shares="Me:205, John:50, Bob:100, Rafael:70, Sarah:75"
           - paid_shares="Me:300, John:200"
           Call:
           record_group_debts(
               creditors="Me, John",
               debtors="Sarah, Bob, Rafael",
               total_amount=500,
               description="Dinner",
               status="unsettled",
               split_mode="custom",
               fair_shares="Me:205, John:50, Bob:100, Rafael:70, Sarah:75",
               paid_shares="Me:300, John:200"
           )

           6) Example 6: “You and John ate dinner for 300, John paid everything, split equally.”
           - These numbers represent each person's FAIR SHARE.
           - creditors="John"
           - debtors="Me"
           - total_amount=300
           - split_mode="equal"
           Call:
              record_group_debts(
                creditors="John",                 # only John paid
                debtors="Me",                     # you also consumed but didn't pay
                total_amount=300,
                description="Dinner",
                status="unsettled",
                split_mode="equal",               # equal split
                # fair_shares optional here; equal mode will compute 150/150
                paid_shares="John:300"           # John advanced the full amount
            )

            7) Example 7: “Me, John and Aisha ate for 600. John paid 400, Aisha paid 200, I paid 0, split equally for all.”
            - These numbers represent each person's FAIR SHARE.
            - creditors="John, Aisha"
            - debtors="Me"
            - total_amount=600
            - split_mode="equal"
            -paid_shares="John:400, Aisha:200"
            Call:
            record_group_debts(
                creditors="John, Aisha",
                debtors="Me",
                total_amount=600,
                description="Friends dinner",
                status="unsettled",
                split_mode="equal",
                paid_shares="John:400, Aisha:200"
            )

            8)Example 8:“Me, John and Aisha ate for 600. I paid 100, John paid 300, Aisha paid 200, split equally for all.”
            - These numbers represent each person's FAIR SHARE.
            - creditors="Me,John, Aisha"
            - debtors=""
            - total_amount=600
            - split_mode="equal"
            -paid_shares="Me:100, John:300, Aisha:200"
            Call:
            record_group_debts(
                creditors="Me, John, Aisha",
                debtors="",                       # no extra debtors; all three consumed
                total_amount=600,
                description="Equal split dinner",
                status="unsettled",
                split_mode="equal",
                paid_shares="Me:100, John:300, Aisha:200"
            )
            
        Important:
        - ALWAYS ensure 'Me' is part of creditors or debtors; only record debts where 'Me' is debtor or creditor.
        - Never create debts between two other people (e.g., Bob ↔ John) if 'Me' is not in that pair.
        
        Answering questions with read_sql_query_tool:
        - For "Whom do I have to pay?":
          - Run a SELECT on debts where debtor = 'Me' AND status = 'unsettled'.
        - For "Who has to pay me?":
          - Run a SELECT on debts where creditor = 'Me' AND status = 'unsettled'.
        - For "Who all have settled their debts to me?":
          - Run a SELECT on debts where creditor = 'Me' AND status = 'settled'.
        
        Examples of queries to pass into read_sql_query_tool(query):
        
        1) Who do I have to pay?
           SELECT debtor, creditor, amount, description, status, timestamp
           FROM debts
           WHERE debtor = 'Me' AND status = 'unsettled';
        
        2) Who has to pay me?
           SELECT debtor, creditor, amount, description, status, timestamp
           FROM debts
           WHERE creditor = 'Me' AND status = 'unsettled';
        
        3) Who all have settled their debts to me?
           SELECT debtor, creditor, amount, description, status, timestamp
           FROM debts
           WHERE creditor = 'Me' AND status = 'settled';
        
        4) What is my net position?
           SELECT
             (SELECT IFNULL(SUM(amount), 0) FROM debts WHERE creditor = 'Me') AS owed_to_me,
             (SELECT IFNULL(SUM(amount), 0) FROM debts WHERE debtor   = 'Me') AS I_owe;
        
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
        generation_config={"temperature": 0.2}
    ),
    tools=[read_sql_query_tool, execute_sql_update_tool, transaction_saver_tool],
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
     ORDER BY timestamp DESC, id DESC
     LIMIT 1;
  3) If this returns exactly 1 row, construct an UPDATE:
     UPDATE transactions
     SET amount = <new_amount>
     WHERE id = <that row's id>;
     and call execute_sql_update_tool.
  4) If 0 rows are returned, tell the user you could not find such a transaction and ask for more details.
  5) If there are multiple "latest" candidates, first show the top few matches
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
  - status,
  - or id if the user mentions it.

- "Mark my debt to John for 200 as settled":
  1) Use read_sql_query_tool:
     SELECT id, creditor, debtor, amount, description, status
     FROM debts
     WHERE debtor = 'Me'
       AND creditor = 'John'
       AND amount = 200
       AND status != 'settled';
  2) If exactly one row is found, call execute_sql_update_tool with:
     UPDATE debts
     SET status = 'settled'
     WHERE id = <that id>;
  3) Then ALWAYS call transaction_saver_tool and tell it to log a DEBIT settlement transaction for the user, for example:
     - "Log a debit transaction for settling my debt to John:
        amount 200,
        category 'Debt settlement',
        description 'Debt to John settled'."

- "Mark John's 300 debt to me as settled":
  1) Use read_sql_query_tool:
     SELECT id, creditor, debtor, amount, description, status
     FROM debts
     WHERE creditor = 'Me'
       AND debtor = 'John'
       AND amount = 300
       AND status != 'settled';
  2) If exactly one row is found, call execute_sql_update_tool with:
     UPDATE debts
     SET status = 'settled'
     WHERE id = <that id>;
  3) Then ALWAYS call transaction_saver_tool and tell it to log a CREDIT settlement transaction for the user, for example:
     - "Log a credit transaction for receiving repayment from John:
        amount 300,
        category 'Debt settlement',
        description 'Debt from John settled (received)'."

- "Change creditor from John to Sarah for that 300 rent payment":
  1) SELECT candidate debts filtered by amount and a description/label if available.
  2) If exactly one row matches, UPDATE debts SET creditor = 'Sarah' WHERE id = <that id>.
  3) Do NOT log a new transaction here unless the user explicitly says the money was actually paid.

HOW TO USE transaction_saver_tool
- transaction_saver_tool wraps the saver_agent, which knows how to INSERT into the 'transactions' table.
- Whenever you need to create a NEW transaction (for example, when a debt is marked as settled),
  you SHOULD NOT write raw INSERT SQL yourself.
- Instead, call transaction_saver_tool with a clear natural-language instruction that includes:
  - transaction_type: 'debit' when money goes out from Me, 'credit' when money comes in to Me.
  - amount: the numeric amount.
  - category: e.g., 'Debt settlement'.
  - description: a short explanation like 'Debt to John settled' or 'Debt from John settled (received)'.

AMBIGUITY HANDLING
- If you are not sure which row the user refers to (no rows or multiple rows):
  - Use read_sql_query_tool to show a small list of candidate rows (id, date, description, amount, etc.).
  - Ask the user to clarify (for example, by giving a date, id, or description snippet).
- Never update multiple rows at once unless the user explicitly asks for a bulk change.
"""
)

# 5.spend analyser agent
spend_analyser_agent = Agent(
    name="SpendAnalyser",
    model=Gemini(
        model="gemini-2.5-flash-lite", 
        generation_config={"temperature": 0.3} # Lower temp for precise SQL generation
    ),
    tools=[read_sql_query_tool], # The universal tool
    description="An AI Data Analyst capable of querying the database directly.",
    instruction=f"""
    You are an expert Data Analyst and SQL Developer.
    
    **Your Goal:** Answer the user's questions about their finances by constructing and executing SQL queries.

    **Database Schema:**
    DB_SCHEMA

    **Rules for Querying:**
    1. **Always** check the schema before writing a query.
    2. Use the `read_sql_query_tool` tool to execute your SQL.
    3. **Comparisons & Trends:**
       - If the user asks to compare periods (e.g., "compare this week vs last week"), write a query that aggregates data for both periods.
       - Use `strftime` to extract week numbers (`%W`), months (`%m`), or days.
       - Use `CASE` statements to label periods if helpful.
       - Example: `SELECT strftime('%Y-%W', timestamp) as week, SUM(amount) FROM transactions WHERE ... GROUP BY week`
       - For "daily spending": `SELECT date(timestamp) as day, SUM(amount) FROM transactions ... GROUP BY day`
    4. **Smart Category & Item Search:**
       - **CRITICAL STEP 1:** If the user mentions a category or a broad topic (like "Food", "Travel"), you **MUST FIRST** execute: `SELECT name FROM categories`
       - **Step 2:** Read the list of available categories from the tool output.
       - **Step 3:** Match the user's term to the fetched categories.
         - Example: User says "Food". You fetch categories and see 'Dining', 'Groceries'. You decide "Food" maps to both.
       - **Step 4:** Construct your final analysis query using the matched categories.
         - **Also** search the `description` column using `LIKE` for the user's original term.
         - **Combined Example:** `SELECT SUM(amount) FROM transactions WHERE category IN ('Dining', 'Groceries') OR description LIKE '%food%'`
       - If the user asks about a specific item (e.g., "ice cream") that is clearly not a category:
         - Search `description` using `LIKE`.
    5. **Date Handling:** 
       - The user message will contain "Today is YYYY-MM-DD".
       - Use this date as the anchor for 'now'. 
       - Construct queries using this specific date (e.g., `date(timestamp) >= date('2025-11-30', '-7 days')`) rather than relying on `date('now')` which might be different.
    5. **Final Answer:** 
       - Interpret the results. "You spent $X this week and $Y last week, which is a Z% increase."
       - Do not show the raw SQL to the user unless they ask for it.

    **Example Thinking Process:**
    User: "Compare spending on Food this week vs last week" (Today is 2025-11-30)
    Thought: I need to compare the last 7 days vs the 7 days before that.
    Tool Call: read_sql_query_tool("SELECT CASE WHEN date(timestamp) >= date('2025-11-30', '-7 days') THEN 'This Week' ELSE 'Last Week' END as period, SUM(amount) as total FROM transactions WHERE category = 'Food' AND date(timestamp) >= date('2025-11-30', '-14 days') GROUP BY period")
    """
)

# 6. Log Expense Pipeline
log_expense_pipeline = SequentialAgent(
    name="LogExpensePipeline",
    description=(
        "Strict pipeline for logging an expense: "
        "1) classify, 2) save transaction"
    ),
    sub_agents=[root_agent, saver_agent],
)

## --- WRAP SUB-AGENTS AS TOOLS ---
log_expense_tool = AgentTool(agent=log_expense_pipeline)
splitwise_tool  = AgentTool(agent=splitwise_agent)
update_tool = AgentTool(agent=update_agent)
spend_analyser_tool = AgentTool(agent=spend_analyser_agent)

# --- ORCHESTRATOR AGENT ---
orchestrator_agent = Agent(
    name="ExpenseOrchestrator",
    model=Gemini(
        model="gemini-2.5-flash-lite",
        generation_config={"temperature": 0.4}
    ),
    tools=[ log_expense_tool, splitwise_tool, read_sql_query_tool, record_group_debts, update_tool,spend_analyser_tool],
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
     When the user asks “How much did I spend?” or “How much money went out?”:
        -Call read_sql_query_tool with a SELECT that sums only debit transactions, 
        for example:
            SELECT COALESCE(SUM(amount), 0) AS total_spent
            FROM transactions
            WHERE transaction_type = 'debit';
        -When the user asks “How much money did I receive / get back?”:
            Call read_sql_query_tool with:
            SELECT COALESCE(SUM(amount), 0) AS total_received
            FROM transactions
            WHERE transaction_type = 'credit';
        -When the user asks for net cash flow or “overall balance of credits minus debits”:
            Call read_sql_query_tool with:
            SELECT
            COALESCE(SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END), 0)
            COALESCE(SUM(CASE WHEN transaction_type = 'debit' THEN amount ELSE 0 END), 0)
            AS net_cash_flow
            FROM transactions;
        -When the user asks ‘How much did I spend on X?’ or similar, where X may not be an exact category name:
            -Treat X as a fuzzy category label.
            -First, try to resolve X to an existing category in the categories table by calling read_sql_query_tool with a query like:
            -SELECT name
            FROM categories
            WHERE LOWER(name) LIKE '%' || LOWER('<USER_TERM>') || '%'
            OR LOWER('<USER_TERM>') LIKE '%' || LOWER(name) || '%';
            -If one or more rows are returned, pick the most semantically appropriate category name (for example, map ‘food’ to ‘Dining’ or ‘Groceries’) and then use that category in subsequent spending/budget queries.
            -If no category match is found, then fall back to searching the transactions.description field using:
                -SELECT COALESCE(SUM(amount), 0) AS total_spent
                FROM transactions
                WHERE transaction_type = 'debit'
                AND LOWER(description) LIKE '%' || LOWER('<USER_TERM>') || '%';
            -For generic terms like ‘food’, you may also combine both:            
            -First answer using the resolved category (if any).
            -If the user explicitly wants “anything where the word appears in the description”, then use the description-based query.”
         - To answer questions like ‘whom do I have to pay?’ or ‘who has to pay me?’, ALWAYS call read_sql_query_tool with a SELECT on the 'debts' table (this tool does have access). Do not say that debts cannot be queried.
         - 'debts' table for debt summaries. 
3. Manage debts and splits:
    -New shared expenses:
        -When the user describes a NEW expense that also implies a debt to other where user is debtor, such as: “Neha paid 30 for my icecream”,“Quresh paid 600 for movie tickets for me and Ayesha”
        -Then ALWAYS:
        -directly call the SplitwiseManager tool to create entries in the 'debts' table.
    -Pure debt/balance questions or updates:
        -When the user mentions words like “split”, “owe”, “lent”, “borrowed”, “settle”, or “who owes whom”
            -and if user is debtor and not spent any money then they are NOT clearly logging a new payment right now, route directly to SplitwiseManager.
            -and if user is creditor and have spent money
            -Then ALWAYS:
            -call LogExpensePipeline to create a base transaction in the 'transactions' table.
            -call the SplitwiseManager tool to create entries in the debts table with data received from prompt as request..
   - SplitwiseManager will internally use record_group_debts (for writing) and read_sql_query_tool (for reading).
 4. Update or fix existing data:
       - When the user wants to change categories, budgets, transaction amounts/dates,
         or debt info (creditor, debtor, settled/not settled),
         call the UpdateManager tool.

Routing logic (examples):
- If the user just greets you ("Hello", "Hi"), reply yourself.
- If the user asks about spending trends or budget status, call SpendAnalyser.
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
- **CRITICAL**: When calling sub-agents (like SpendAnalyser), ALWAYS include the "Today is YYYY-MM-DD" context in the request arguments if it was provided to you. This is essential for them to resolve relative dates.
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
