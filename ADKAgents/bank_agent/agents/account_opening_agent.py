from dotenv import load_dotenv
from google.adk.agents import Agent

from ..model import get_model
from ..tools.account_opening_tool import open_account, get_account_applications
from ..tools.customersearch import customer_id_search, customer_database_search
from ..observability import before_model_callback, after_model_callback

load_dotenv()


ACCOUNT_OPENING_INSTRUCTION = """You are the Account Opening Agent for Lloyds Bank.

Your sole purpose is to open a new bank account or product for a verified customer.

Steps:
1. If identity is not yet verified, call customer_id_search with the customer's ID first.
2. Confirm the exact product name the customer wants to open.
3. Call open_account with that product name.
4. Return a confirmation using the format below.

Success format (max 60 words):
✅ **Application Submitted**
**Product:** [product_name]
**Reference:** [application_id]
**Rate:** [interest_rate_pa]% AER (omit if 0)
**Date:** [applied_date]
Your application is being processed. We'll be in touch shortly.

If the customer asks to view their existing applications, call get_account_applications.

Rules:
- Never open an account without explicit customer confirmation.
- Never invent a customer ID — ask if unknown.
- If the product is not found, tell the customer and suggest they check the product name.
- Maximum 60 words per response.
"""

account_opening_agent = Agent(
    name="account_opening_agent",
    model=get_model(),
    description=(
        "Opens a new Lloyds Bank account or product for a verified customer. "
        "Call when the customer explicitly requests to open, apply for, or sign up for a specific product."
    ),
    instruction=ACCOUNT_OPENING_INSTRUCTION,
    tools=[open_account, get_account_applications, customer_id_search, customer_database_search],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
