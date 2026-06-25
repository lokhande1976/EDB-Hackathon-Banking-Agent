from dotenv import load_dotenv
from google.adk.agents import Agent

from ..model import get_model
from ..tools.bigquery_tool import run_bigquery_query
from ..tools.financial_analysis_tools import get_product_recommendations
from ..tools.productsearch import vertex_vector_search
from ..observability import before_model_callback, after_model_callback

load_dotenv()


PRODUCT_RECOMMENDATION_INSTRUCTION = """You are the Product Recommendation Agent for Lloyds Bank.

Steps:
1. get_product_recommendations with relevant filters.
2. For each recommended product, use run_bigquery_query to fetch its product_url:
   SELECT product_url FROM products WHERE product_name = '<name>'

Return ONLY a ranked list of 2-3 Lloyds Bank products in this exact format per product:
**[Product Name]** — [Rate/Key Feature] · [Access/Type] · [Fee]
↳ [One sentence: why it fits THIS customer's situation]
🔗 [Apply now](product_url)

Rules:
- Maximum 100 words total.
- Always include the 🔗 link line using the product_url from the database (lloydsbank.com).
- Ranked best-first. No headers. No trade-off essays.
- One personalised line per product referencing their actual balance or goal.
- Cover all product types: savings, current accounts, credit cards, loans, mortgages, investments, insurance.
- If nothing matches well, return the closest 2 options with a one-line honest note.
"""

product_recommendation_agent = Agent(
    name="product_recommendation_agent",
    model=get_model(),
    description=(
        "Matches and ranks banking products to a customer's stated preferences and financial "
        "profile. Provides personalised recommendations with clear reasoning. Call after "
        "transaction analysis is complete."
    ),
    instruction=PRODUCT_RECOMMENDATION_INSTRUCTION,
    tools=[get_product_recommendations, run_bigquery_query, vertex_vector_search],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
