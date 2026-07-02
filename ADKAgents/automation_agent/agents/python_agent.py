"""Sub-agent: Python + Playwright or Selenium project files."""

from google.adk.agents import Agent
from ..tools import (
    generate_python_pyproject_toml, generate_python_conftest,
    generate_python_base_page, generate_python_page_object, generate_python_test,
)

INSTRUCTION = """You are a Python test automation expert for Playwright and Selenium.

When generating a Python framework, call ALL of these tools:
1. generate_python_pyproject_toml  — pyproject.toml (pytest + allure + faker + openpyxl)
2. generate_python_conftest        — conftest.py (fixtures: playwright session/context/page or selenium driver)
3. generate_python_base_page       — pages/base_page.py (30+ reusable actions)
4. generate_python_page_object     — for EACH page the user mentions
5. generate_python_test            — for EACH page object

Always pass the `framework` parameter — 'playwright' or 'selenium' — to tools that accept it.

Naming rules:
- page_name 'Login' → LoginPage class in pages/login_page.py, tests in tests/test_login.py
- If no pages specified, generate at least: HomePage and LoginPage
- Infer test_scenarios from the page name and app type

Return ONLY the raw tool outputs — do not add commentary.
"""

python_agent = Agent(
    name="python_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates Python automation framework files for Playwright or Selenium. "
        "Produces: pyproject.toml (pytest + allure + faker), conftest.py with thread-safe fixtures, "
        "BasePage with 30+ actions, Page Objects, and pytest test files with Allure annotations."
    ),
    instruction=INSTRUCTION,
    tools=[
        generate_python_pyproject_toml, generate_python_conftest,
        generate_python_base_page, generate_python_page_object, generate_python_test,
    ],
)
