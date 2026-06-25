from dotenv import load_dotenv
from google.adk.agents import Agent

from ..model import get_model
from ..tools.bigquery_tool import run_bigquery_query
from ..tools.financial_analysis_tools import get_spending_analysis, get_savings_opportunity
from ..observability import before_model_callback, after_model_callback

load_dotenv()


TRANSACTION_ANALYSIS_INSTRUCTION = """You are the Transaction Analysis Agent for a retail bank.

Steps: get_spending_analysis → get_savings_opportunity. No further queries needed.

Return ONLY these numbers, nothing else:
- Monthly income · Total spend · Surplus (£ and % of income)
- Top 3 spending categories with £ amounts
- Savings rate: X% (flag if <10%)
- Cash buffer: X months of expenses
- One opportunity (max 10 words, e.g. "£800 idle in current account earning 0%")

Rules:
- Maximum 60 words in your response.
- Numbers and bullets only. No prose paragraphs.
- No product names. No recommendations.
"""

transaction_analysis_agent = Agent(
    name="transaction_analysis_agent",
    model=get_model(),
    description=(
        "Analyses transaction history to derive spending patterns, behavioural trends, "
        "financial signals, and savings opportunities. Call after customer profile is established."
    ),
    instruction=TRANSACTION_ANALYSIS_INSTRUCTION,
    tools=[get_spending_analysis, get_savings_opportunity, run_bigquery_query],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
