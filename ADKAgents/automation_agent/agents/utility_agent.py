"""Sub-agent: Utility classes and resource files."""

from google.adk.agents import Agent
from ..tools import (
    generate_config_reader, generate_wait_helper, generate_screenshot_util,
    generate_excel_reader, generate_config_properties, generate_log4j2_config,
    generate_allure_properties,
)

INSTRUCTION = """You are a Java automation utilities specialist.

When given project requirements, call ALL of these tools:
1. generate_config_reader        — ConfigReader.java (reads config.properties + env-var overrides)
2. generate_wait_helper          — WaitHelper.java (explicit Playwright waits)
3. generate_screenshot_util      — ScreenshotUtil.java (capture + Allure attachment)
4. generate_excel_reader         — ExcelReader.java (Apache POI test data)
5. generate_config_properties    — config.properties (pass the app URL and browser)
6. generate_log4j2_config        — log4j2.xml (console + rolling file logging)
7. generate_allure_properties    — allure.properties

Always call all 7 tools — do not skip any.
Return ONLY the raw tool outputs — do not add commentary.
"""

utility_agent = Agent(
    name="utility_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates all utility/helper classes and resource files: ConfigReader, WaitHelper, "
        "ScreenshotUtil, ExcelReader, config.properties, log4j2.xml, and allure.properties."
    ),
    instruction=INSTRUCTION,
    tools=[
        generate_config_reader, generate_wait_helper, generate_screenshot_util,
        generate_excel_reader, generate_config_properties, generate_log4j2_config,
        generate_allure_properties,
    ],
)
