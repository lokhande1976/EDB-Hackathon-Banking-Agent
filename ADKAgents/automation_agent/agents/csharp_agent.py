"""Sub-agent: C# + Playwright or Selenium project files."""

from google.adk.agents import Agent
from ..tools import (
    generate_csharp_csproj, generate_csharp_appsettings,
    generate_csharp_base_page, generate_csharp_base_test,
    generate_csharp_page_object, generate_csharp_test,
)

INSTRUCTION = """You are a C# (.NET) test automation expert for Playwright and Selenium.

When generating a C# framework, call ALL of these tools:
1. generate_csharp_csproj        — .csproj (NUnit + Playwright.NUnit or Selenium + Allure)
2. generate_csharp_appsettings   — appsettings.json (base URL, browser config)
3. generate_csharp_base_page     — Pages/BasePage.cs (30+ async actions)
4. generate_csharp_base_test     — Tests/BaseTest.cs (NUnit lifecycle + Playwright PageTest or Selenium WebDriver)
5. generate_csharp_page_object   — for EACH page the user mentions
6. generate_csharp_test          — for EACH page object

Always pass the `framework` parameter — 'playwright' or 'selenium' — to tools that accept it.
Derive the `namespace` from the project name (e.g. 'My App' → 'MyApp.Automation').

Naming rules:
- page_name 'Login' → LoginPage class in Pages/LoginPage.cs, tests in Tests/LoginTests.cs
- If no pages specified, generate at least: HomePage and LoginPage

Return ONLY the raw tool outputs — do not add commentary.
"""

csharp_agent = Agent(
    name="csharp_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates C# (.NET 8) automation framework files for Playwright or Selenium. "
        "Produces: .csproj (NUnit + Allure + Bogus), appsettings.json, BasePage.cs with async actions, "
        "BaseTest.cs with NUnit lifecycle management, Page Objects, and NUnit test classes."
    ),
    instruction=INSTRUCTION,
    tools=[
        generate_csharp_csproj, generate_csharp_appsettings,
        generate_csharp_base_page, generate_csharp_base_test,
        generate_csharp_page_object, generate_csharp_test,
    ],
)
