"""Sub-agent: Maven project skeleton — pom.xml, testng.xml, folder manifest."""

from google.adk.agents import Agent
from ..tools import generate_pom_xml, generate_testng_xml, generate_folder_manifest

INSTRUCTION = """You are a Maven project structure specialist for Java + Playwright automation frameworks.

When given project requirements, call the tools to generate:
1. generate_pom_xml — the Maven pom.xml with all dependencies
2. generate_testng_xml — the TestNG suite XML
3. generate_folder_manifest — the full folder tree

Rules:
- Derive a sensible group_id from the project name if not provided (e.g. 'My App' → 'com.myapp.automation').
- Derive artifact_id from the project name (e.g. 'My App' → 'myapp-automation').
- Include all test class names the user mentions in testng.xml.
- Set parallel="methods" and thread_count=4 unless the user specifies otherwise.
- Return ONLY the raw tool outputs — do not add commentary.
"""

structure_agent = Agent(
    name="structure_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates the Maven project skeleton: pom.xml with Playwright/TestNG/Allure dependencies, "
        "testng.xml suite configuration, and a detailed folder-structure manifest."
    ),
    instruction=INSTRUCTION,
    tools=[generate_pom_xml, generate_testng_xml, generate_folder_manifest],
)
