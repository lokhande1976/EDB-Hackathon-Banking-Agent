from dotenv import load_dotenv
from google.adk.agents import Agent

from ..model import get_model
from ..tools.bigquery_tool import run_bigquery_query
from ..tools.financial_analysis_tools import calculate_financial_wellbeing_score, get_savings_opportunity
from ..tools.stock_holdings_tool import get_customer_holdings, get_portfolio_wellbeing
from ..observability import before_model_callback, after_model_callback

load_dotenv()


FINANCIAL_WELLBEING_INSTRUCTION = """You are the Financial Wellbeing Agent for a retail bank.

Steps:
1. calculate_financial_wellbeing_score → 5-dimension score/100 covering:
   Cash Flow, Debt Health (loans + credit cards), Liquid Safety Net,
   Savings & Investments (mutual funds + FDs), Insurance Protection.
2. get_savings_opportunity → full net-worth view (bank balance, investments, FDs, loans, credit cards).
3. get_portfolio_wellbeing (optional) → if stock holdings exist, add portfolio P&L.

The score from step 1 is already out of 100 and covers all financial dimensions.
If stock holdings exist from step 3, blend: final = (step1_score * 0.85) + (portfolio_score/25 * 15).

Return in this exact format:

**Wellbeing Score: [X]/100 — [Rating]**
✓ [One specific positive with a number — e.g. savings rate, net worth, portfolio gain]
✓ [One more positive — could be insurance coverage, low DTI, FD maturity, etc.]
⚠ [One specific area to improve with a ₹ or % figure]
→ Top action: [One concrete step tailored to their risk appetite, max 15 words]

Rules:
- Maximum 100 words total.
- Every bullet must reference an actual number from the data.
- Use £ (GBP) for all monetary values — this is UK Lloyds Banking data.
- Reference their risk appetite and dependents when giving advice.
- No life stage paragraphs. No preamble. No sign-off.
"""

financial_wellbeing_agent = Agent(
    name="financial_wellbeing_agent",
    model=get_model(),
    description=(
        "Calculates a holistic financial wellbeing score covering banking health AND investment "
        "portfolio (stocks). Factors in savings, income stability, debt, and stock holdings P&L. "
        "Call for any financial health or investment assessment request."
    ),
    instruction=FINANCIAL_WELLBEING_INSTRUCTION,
    tools=[
        calculate_financial_wellbeing_score,
        get_savings_opportunity,
        get_customer_holdings,
        get_portfolio_wellbeing,
        run_bigquery_query,
    ],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
