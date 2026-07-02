from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .prompt import ORCHESTRATOR_INSTRUCTION
from .agents import structure_agent, java_agent, utility_agent, cicd_agent

load_dotenv()

root_agent = Agent(
    name="automation_framework_generator",
    model="gemini-2.0-flash",
    description=(
        "Generates complete, production-ready Java + Playwright + Maven automation frameworks "
        "from a single natural-language prompt. Produces: Maven POM, Page Objects, BaseTest, "
        "utility classes, Allure reporting, GitHub Actions CI/CD, Docker, and README — "
        "all files ready to clone and run."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        AgentTool(agent=structure_agent),
        AgentTool(agent=java_agent),
        AgentTool(agent=utility_agent),
        AgentTool(agent=cicd_agent),
    ],
)
