from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import google_search

from ..model import get_model
from ..observability import before_model_callback, after_model_callback

load_dotenv()


WEB_SEARCH_INSTRUCTION = """You are a financial internet search agent.

Use google_search to look up live information: stock prices, indices (FTSE 100, S&P 500),
interest rates, mortgage rates, economic news, company announcements, or any financial
topic not held in the local database.

Rules:
- Always search before answering. Do not guess figures.
- Quote the source name and approximate date of the information.
- Keep your response under 100 words.
- Prices/rates in GBP/% where relevant.
"""

web_search_agent = Agent(
    name="web_search_agent",
    model=get_model(),
    description=(
        "Searches the internet for live financial data and news: stock indices, current prices, "
        "interest rates, mortgage rates, economic news, or any question that needs up-to-date "
        "information not available in the local database. Call when no customer ID is provided "
        "and the question requires current market or financial data."
    ),
    instruction=WEB_SEARCH_INSTRUCTION,
    tools=[google_search],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
