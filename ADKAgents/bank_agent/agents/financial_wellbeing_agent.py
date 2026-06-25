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
1. calculate_financial_wellbeing_score → banking score (savings, income, cushion, debt)
2. get_portfolio_wellbeing → investment score (portfolio value, diversification)
3. get_savings_opportunity → cash flow opportunity

Combine into a single score out of 125 (100 banking + 25 investment), then normalise to /100.

Return in this exact format:

**Wellbeing Score: [X]/100 — [Rating]**
✓ [One specific positive backed by a number from banking data]
✓ [Investment positive: portfolio value or P&L figure]
⚠ [One specific area to improve with a £ or % figure]
→ Top action: [One concrete step, max 15 words]

Rules:
- Maximum 80 words total.
- Every bullet must reference an actual number from the data.
- Include the portfolio value in the score if investments are present.
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
