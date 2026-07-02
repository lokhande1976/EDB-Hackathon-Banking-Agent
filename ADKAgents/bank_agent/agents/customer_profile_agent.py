from dotenv import load_dotenv
from google.adk.agents import Agent

from ..model import get_model
from ..tools.customersearch import customer_id_search, customer_database_search
from ..tools.bigquery_tool import run_bigquery_query
from ..observability import before_model_callback, after_model_callback

load_dotenv()


CUSTOMER_PROFILE_INSTRUCTION = """You are the Customer Profile Agent for a retail bank.

Steps: customer_id_search → customer_database_search. Use run_bigquery_query only if data is missing.

Return ONLY these facts, nothing else:
- Name · Age · Life stage · Occupation · Income band
- Accounts: for each → type, balance, interest rate (or "None" if no bank accounts)
- Total wealth: sum of ALL bank account balances + ALL FD principals + ALL investment current values (never report £0 if the customer has FDs or investments)
- Any idle current account cash (>£500 with no savings account)
- Product gaps: missing ISA / savings account / current account / etc.

Rules:
- Maximum 60 words in your response.
- No preamble, no sign-off, no section headers.
- Pure facts only. No recommendations.
- If customer not found, say: "Customer ID not found. Please check and retry."
"""

customer_profile_agent = Agent(
    name="customer_profile_agent",
    model=get_model(),
    description=(
        "Verifies customer identity, retrieves their full profile, and derives their "
        "life stage and current financial position. Call this first for any customer interaction."
    ),
    instruction=CUSTOMER_PROFILE_INSTRUCTION,
    tools=[customer_id_search, customer_database_search, run_bigquery_query],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
