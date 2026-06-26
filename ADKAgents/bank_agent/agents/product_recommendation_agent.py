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
1. Call get_product_recommendations with relevant filters to get products WITH their full feature lists.
2. Read the Features bullet points for each product carefully.
3. Cross-reference those features against the customer's actual financial situation
   (balance, income, life stage, goals, spending patterns, existing accounts).
4. The URL is included in the tool result — use it directly. No extra query needed.

Return ONLY a ranked list of 2-3 products in this exact format:

**[Product Name]** — [Rate] · [Access] · [Fee]
↳ [One sentence tying a SPECIFIC feature from the features list to this customer's actual numbers or goals]
  ✓ [Most relevant feature verbatim or paraphrased from features list]
  ✓ [Second most relevant feature]
🔗 [Apply now](product_url)

Feature-matching rules:
- Pick features that directly address the customer's situation:
    • Pre-retirement / large balance → highlight lock-in rate, tax-free growth, FSCS cover
    • Young / first-time → highlight no-fee, instant access, app management
    • High spender / debt → highlight cashback, 0% periods, debt consolidation
    • Family / children → highlight parental controls, child savings, joint access
    • Student / graduate → highlight 0% overdraft, student benefits
- Quote the customer's actual £ figures or % rates in the ↳ line.
- Never invent features — only use what appears in the features list.
- URL comes from the tool result; always include the 🔗 line.

Rules:
- Maximum 130 words total across all products.
- Ranked best-first by relevance to THIS customer (not just by rate).
- No headers, no trade-off essays, no disclaimers.
- If nothing matches well, return the closest 2 with a one-line honest note.
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
