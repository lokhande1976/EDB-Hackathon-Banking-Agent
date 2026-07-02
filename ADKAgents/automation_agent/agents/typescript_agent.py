"""Sub-agent: TypeScript + Playwright or Cypress project files."""

from google.adk.agents import Agent
from ..tools import (
    generate_ts_playwright_package_json, generate_ts_playwright_config,
    generate_ts_playwright_tsconfig, generate_ts_playwright_base_page,
    generate_ts_playwright_fixtures, generate_ts_playwright_page_object,
    generate_ts_playwright_test, generate_ts_playwright_env,
    generate_ts_playwright_utils,
    generate_cypress_package_json, generate_cypress_config,
    generate_cypress_support_commands, generate_cypress_support_e2e,
    generate_cypress_page_object, generate_cypress_test,
)

INSTRUCTION = """You are a TypeScript automation expert for Playwright and Cypress.

Based on the user's chosen framework:

FOR PLAYWRIGHT (TypeScript):
Call ALL of these tools:
1. generate_ts_playwright_package_json  — package.json
2. generate_ts_playwright_config        — playwright.config.ts (multi-browser, Allure reporter)
3. generate_ts_playwright_tsconfig      — tsconfig.json
4. generate_ts_playwright_base_page     — pages/BasePage.ts (30+ typed actions)
5. generate_ts_playwright_fixtures      — fixtures/fixtures.ts (extend base test)
6. generate_ts_playwright_env           — .env.example
7. generate_ts_playwright_utils         — utils/helpers.ts (Faker, Excel reader, retry)
8. generate_ts_playwright_page_object   — for EACH page the user mentions
9. generate_ts_playwright_test          — for EACH page object

FOR CYPRESS (TypeScript):
Call ALL of these tools:
1. generate_cypress_package_json        — package.json
2. generate_cypress_config              — cypress.config.ts (Mochawesome reporter)
3. generate_cypress_support_commands    — cypress/support/commands.ts (custom commands)
4. generate_cypress_support_e2e        — cypress/support/e2e.ts (global hooks)
5. generate_cypress_page_object         — for EACH page the user mentions
6. generate_cypress_test                — for EACH page object

Naming rules:
- page_name 'Login' → LoginPage.ts, login.spec.ts (Playwright) or login.cy.ts (Cypress)
- If no pages specified, generate at least: HomePage and LoginPage
- Infer test_scenarios from the page name and app type
- Always set package_name to the group_id without dots (e.g. 'comacme' → use as namespace label only)

Return ONLY the raw tool outputs — do not add commentary.
"""

typescript_agent = Agent(
    name="typescript_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates TypeScript automation framework files for Playwright or Cypress. "
        "Playwright: package.json, playwright.config.ts (multi-browser + Allure), tsconfig.json, "
        "BasePage.ts with 30+ typed actions, fixtures, helpers, page objects, and spec files. "
        "Cypress: package.json, cypress.config.ts, custom commands, support files, page objects, and cy.ts specs."
    ),
    instruction=INSTRUCTION,
    tools=[
        generate_ts_playwright_package_json, generate_ts_playwright_config,
        generate_ts_playwright_tsconfig, generate_ts_playwright_base_page,
        generate_ts_playwright_fixtures, generate_ts_playwright_page_object,
        generate_ts_playwright_test, generate_ts_playwright_env,
        generate_ts_playwright_utils,
        generate_cypress_package_json, generate_cypress_config,
        generate_cypress_support_commands, generate_cypress_support_e2e,
        generate_cypress_page_object, generate_cypress_test,
    ],
)
