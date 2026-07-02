from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool

from .prompt import ORCHESTRATOR_INSTRUCTION
from .agents import (
    structure_agent, java_agent, utility_agent, cicd_agent,
    typescript_agent, python_agent, csharp_agent,
)

load_dotenv()

root_agent = Agent(
    name="automation_framework_generator",
    model="gemini-2.0-flash",
    description=(
        "Generates complete, production-ready automation frameworks from a single natural-language prompt. "
        "Supports: Java (Playwright/Selenium + Maven/Gradle + TestNG/JUnit + Allure), "
        "TypeScript/JavaScript (Playwright/Cypress/WebdriverIO + npm + Allure/Mochawesome), "
        "Python (Playwright/Selenium + pytest + Allure), "
        "C# (Playwright/Selenium + NUnit + Allure). "
        "Every generation includes Page Objects, base classes, utilities, "
        "GitHub Actions CI/CD, Docker, and a full README."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        AgentTool(agent=structure_agent),    # Java: Maven POM + testng.xml
        AgentTool(agent=java_agent),         # Java: BasePage + BaseTest + Page Objects
        AgentTool(agent=utility_agent),      # Java: utilities + configs
        AgentTool(agent=typescript_agent),   # TypeScript: Playwright + Cypress
        AgentTool(agent=python_agent),       # Python: Playwright + Selenium
        AgentTool(agent=csharp_agent),       # C#: Playwright + Selenium
        AgentTool(agent=cicd_agent),         # All: GitHub Actions + Docker + README
    ],
)
