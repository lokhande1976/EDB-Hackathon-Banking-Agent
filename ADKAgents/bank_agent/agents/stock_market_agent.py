from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from ..model import get_model
from ..observability import before_model_callback, after_model_callback
from ..tools.lloyds_stock_tool import get_stock_price, get_stock_price_range, get_stock_stats
from ..tools.stock_holdings_tool import get_customer_holdings, get_portfolio_wellbeing

load_dotenv()


# Dedicated search-only sub-agent — google_search cannot be mixed with function tools
# in the same agent; isolate it here so stock_market_agent stays function-tool-only.
from google.adk.tools import google_search as _google_search

_web_search_agent = Agent(
    name="stock_market_web_search",
    model=get_model(),
    description="Searches the internet for live stock prices, market news, and financial data.",
    instruction=(
        "Use google_search to answer the question. Return the key facts concisely — "
        "numbers, source, date. Maximum 80 words."
    ),
    tools=[_google_search],
)


STOCK_MARKET_INSTRUCTION = """You are the Stock Market Agent for a retail bank.

You have three sources of data:

1. LOCAL DB — historical LLOY (Lloyds Banking Group) price data 2017-2019:
   - get_stock_price(date)             → single-day OHLCV
   - get_stock_price_range(start, end) → closing prices over a range
   - get_stock_stats(period)           → aggregate stats ('all', year, 'YYYY-MM')

2. CUSTOMER HOLDINGS — personalised portfolio data:
   - get_customer_holdings(customer_id)    → full portfolio with current P&L
   - get_portfolio_wellbeing(customer_id) → diversification and net worth summary

3. INTERNET — for live prices, news, or non-LLOY stocks:
   - web_search_agent(request)  → delegates to Google Search

Routing:
- Historical LLOY (2017-2019): use local tools.
- Customer portfolio questions: use holdings tools.
- Live prices / news / other tickers: use web_search_agent.
- Prices in pence. Return numbers directly. Maximum 100 words.
"""

stock_market_agent = Agent(
    name="stock_market_agent",
    model=get_model(),
    description=(
        "Handles all stock market queries: historical LLOY price data (2017-2019), "
        "customer stock portfolio and P&L, live market prices and news via internet search. "
        "Call for any stock price, holdings, portfolio, or market question."
    ),
    instruction=STOCK_MARKET_INSTRUCTION,
    tools=[
        get_stock_price,
        get_stock_price_range,
        get_stock_stats,
        get_customer_holdings,
        get_portfolio_wellbeing,
        AgentTool(agent=_web_search_agent),
    ],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
