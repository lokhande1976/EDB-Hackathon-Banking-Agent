from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .model import get_model
from .observability import (
    after_model_callback,
    before_model_callback,
    setup_observability,
)
from .prompt import AGENT_INSTRUCTION
from .agents import (
    customer_profile_agent,
    transaction_analysis_agent,
    product_recommendation_agent,
    financial_wellbeing_agent,
)

load_dotenv()


# Initialise OpenTelemetry exporters and the metrics store.
setup_observability()

root_agent = Agent(
    name="banking_orchestrator",
    model=get_model(),
    description=(
        "Multi-agent retail banking assistant. Orchestrates customer profiling, "
        "transaction analysis, product recommendations, and financial wellbeing "
        "assessments to deliver end-to-end personalised banking experiences."
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        AgentTool(agent=customer_profile_agent),
        AgentTool(agent=transaction_analysis_agent),
        AgentTool(agent=product_recommendation_agent),
        AgentTool(agent=financial_wellbeing_agent),
    ],
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
