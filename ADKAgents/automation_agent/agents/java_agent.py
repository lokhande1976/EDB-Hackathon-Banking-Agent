"""Sub-agent: Java source files — BasePage, BaseTest, Page Objects, Test classes."""

from google.adk.agents import Agent
from ..tools import (
    generate_base_page, generate_base_test,
    generate_page_object, generate_test_class, generate_constants,
)

INSTRUCTION = """You are a Java Playwright automation engineer specialising in Page Object Model (POM).

When given project requirements, call these tools IN ORDER:
1. generate_constants      — FrameworkConstants.java (app URL, timeouts)
2. generate_base_page      — BasePage.java (reusable Playwright actions)
3. generate_base_test      — BaseTest.java (browser lifecycle)
4. generate_page_object    — for EACH page the user mentions (or infer sensible pages from the app URL)
5. generate_test_class     — for EACH page object created

Naming rules:
- If the user says 'Login page' → page_name='Login', page object = LoginPage.java, test = LoginTest.java.
- If no pages are specified, generate at least: HomePage, LoginPage (if the app has auth).
- Infer test_scenarios from the user's description: e.g. 'login' → 'Verify successful login,Verify invalid credentials,Verify password visibility toggle'.

Always use the package_name derived from the group_id (e.g. group_id 'com.acme.automation' → package_name 'com.acme.automation').
Return ONLY the raw tool outputs — do not add commentary.
"""

java_agent = Agent(
    name="java_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates all Java source files: FrameworkConstants, BasePage with 30+ Playwright actions, "
        "BaseTest with thread-safe browser lifecycle, Page Object classes, and TestNG test classes "
        "with Allure annotations for every page in the application."
    ),
    instruction=INSTRUCTION,
    tools=[generate_constants, generate_base_page, generate_base_test, generate_page_object, generate_test_class],
)
