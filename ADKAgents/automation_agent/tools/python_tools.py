"""Tools that generate Python automation project files — Playwright, Selenium, pytest."""

from __future__ import annotations


def generate_python_pyproject_toml(
    project_name: str,
    artifact_id: str,
    framework: str = "playwright",
) -> dict:
    """Generate pyproject.toml for Python automation project."""
    framework_dep = (
        'playwright = "^1.44.0"' if framework == "playwright"
        else 'selenium = "^4.21.0"\nwebdriver-manager = "^4.0.1"'
    )
    content = f"""[project]
name = "{artifact_id}"
version = "1.0.0"
description = "{project_name} — Python {framework.capitalize()} Automation Framework"
requires-python = ">=3.10"

dependencies = [
    {framework_dep},
    "pytest>=8.2.0",
    "pytest-html>=4.1.1",
    "allure-pytest>=2.13.5",
    "python-dotenv>=1.0.1",
    "faker>=25.8.0",
    "openpyxl>=3.1.4",
    "requests>=2.32.3",
    "assertpy>=1.1",
    "pydantic>=2.7.4",
]

[project.optional-dependencies]
dev = [
    "black>=24.4.2",
    "ruff>=0.4.10",
    "mypy>=1.10.0",
    "pytest-xdist>=3.5.0",
    "pytest-rerunfailures>=14.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short --strict-markers --alluredir=allure-results --clean-alluredir"
markers = [
    "smoke: Smoke tests",
    "regression: Regression tests",
    "sanity: Sanity tests",
    "slow: Tests that take > 30s",
]

[tool.black]
line-length = 100
target-version = ["py310", "py311", "py312"]

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N"]
"""
    return {"filename": "pyproject.toml", "content": content.strip()}


def generate_python_conftest(
    package_name: str,
    app_url: str,
    framework: str = "playwright",
) -> dict:
    """Generate conftest.py — pytest fixtures for Playwright or Selenium."""
    if framework == "playwright":
        content = f"""import pytest
from playwright.sync_api import Playwright, Browser, BrowserContext, Page, sync_playwright
from dotenv import load_dotenv
import os

load_dotenv()


# ── Playwright session fixtures ───────────────────────────────────────────────

@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as pw:
        yield pw


@pytest.fixture(scope="session")
def browser(playwright_instance: Playwright):
    browser_name = os.getenv("BROWSER", "chromium").lower()
    headless     = os.getenv("HEADLESS", "true").lower() == "true"
    slow_mo      = int(os.getenv("SLOW_MO", "0"))

    launch = dict(headless=headless, slow_mo=slow_mo)

    browsers = {{
        "chromium": playwright_instance.chromium,
        "firefox":  playwright_instance.firefox,
        "webkit":   playwright_instance.webkit,
    }}
    b = browsers.get(browser_name, playwright_instance.chromium).launch(**launch)
    yield b
    b.close()


@pytest.fixture
def context(browser: Browser):
    ctx = browser.new_context(
        base_url=os.getenv("BASE_URL", "{app_url}"),
        viewport={{"width": 1920, "height": 1080}},
        record_video_dir="test-results/videos" if os.getenv("RECORD_VIDEO") == "true" else None,
    )
    ctx.set_default_timeout(int(os.getenv("DEFAULT_TIMEOUT", "30000")))
    yield ctx
    ctx.close()


@pytest.fixture
def page(context: BrowserContext):
    p = context.new_page()
    yield p
    p.close()


# ── Hooks ─────────────────────────────────────────────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()

    if report.when == "call" and report.failed:
        # Attach screenshot to Allure on failure
        if hasattr(item, "funcargs") and "page" in item.funcargs:
            import allure
            page: Page = item.funcargs["page"]
            try:
                screenshot = page.screenshot(full_page=True)
                allure.attach(screenshot, name="Failure Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
"""
    else:  # selenium
        content = f"""import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from dotenv import load_dotenv
import os
import allure

load_dotenv()


@pytest.fixture
def driver():
    browser_name = os.getenv("BROWSER", "chrome").lower()
    headless     = os.getenv("HEADLESS", "true").lower() == "true"

    if browser_name == "firefox":
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        d = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
    else:
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        d = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    d.get(os.getenv("BASE_URL", "{app_url}"))
    d.maximize_window()
    d.implicitly_wait(int(os.getenv("IMPLICIT_WAIT", "10")))
    yield d
    d.quit()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()
    if report.when == "call" and report.failed:
        if hasattr(item, "funcargs") and "driver" in item.funcargs:
            driver = item.funcargs["driver"]
            try:
                screenshot = driver.get_screenshot_as_png()
                allure.attach(screenshot, name="Failure Screenshot", attachment_type=allure.attachment_type.PNG)
            except Exception:
                pass
"""
    return {"filename": "conftest.py", "content": content.strip()}


def generate_python_base_page(
    package_name: str,
    framework: str = "playwright",
) -> dict:
    """Generate pages/base_page.py."""
    if framework == "playwright":
        content = f"""\"\"\"BasePage — parent for all Page Object classes (Playwright).\"\"\"
from __future__ import annotations

import os
from playwright.sync_api import Page, Locator, expect


class BasePage:
    \"\"\"Wraps Playwright Page with common reusable actions.\"\"\"

    def __init__(self, page: Page) -> None:
        self.page = page

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate(self, url: str) -> None:
        self.page.goto(url)
        self.page.wait_for_load_state("networkidle")

    def reload(self) -> None:
        self.page.reload()
        self.page.wait_for_load_state()

    def get_url(self) -> str:
        return self.page.url

    def get_title(self) -> str:
        return self.page.title()

    # ── Locators ──────────────────────────────────────────────────────────────

    def locator(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def get_by_test_id(self, test_id: str) -> Locator:
        return self.page.get_by_test_id(test_id)

    def get_by_role(self, role: str, **kwargs) -> Locator:
        return self.page.get_by_role(role, **kwargs)

    def get_by_label(self, label: str) -> Locator:
        return self.page.get_by_label(label)

    def get_by_placeholder(self, placeholder: str) -> Locator:
        return self.page.get_by_placeholder(placeholder)

    def get_by_text(self, text: str) -> Locator:
        return self.page.get_by_text(text)

    # ── Actions ────────────────────────────────────────────────────────────────

    def click(self, selector: str) -> None:
        self.locator(selector).click()

    def fill(self, selector: str, value: str) -> None:
        self.locator(selector).clear()
        self.locator(selector).fill(value)

    def select_option(self, selector: str, value: str) -> None:
        self.locator(selector).select_option(value)

    def check(self, selector: str) -> None:
        self.locator(selector).check()

    def upload_file(self, selector: str, file_path: str) -> None:
        self.locator(selector).set_input_files(file_path)

    def press_key(self, key: str) -> None:
        self.page.keyboard.press(key)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_text(self, selector: str) -> str:
        return self.locator(selector).text_content() or ""

    def get_input_value(self, selector: str) -> str:
        return self.locator(selector).input_value()

    def get_attribute(self, selector: str, attribute: str) -> str | None:
        return self.locator(selector).get_attribute(attribute)

    # ── Visibility ─────────────────────────────────────────────────────────────

    def is_visible(self, selector: str) -> bool:
        return self.locator(selector).is_visible()

    def is_enabled(self, selector: str) -> bool:
        return self.locator(selector).is_enabled()

    # ── Waits ──────────────────────────────────────────────────────────────────

    def wait_for_visible(self, selector: str, timeout: float = 30_000) -> None:
        self.locator(selector).wait_for(state="visible", timeout=timeout)

    def wait_for_hidden(self, selector: str, timeout: float = 30_000) -> None:
        self.locator(selector).wait_for(state="hidden", timeout=timeout)

    def wait_for_url(self, url_pattern: str) -> None:
        self.page.wait_for_url(url_pattern)

    def wait_for_page_load(self) -> None:
        self.page.wait_for_load_state("networkidle")

    # ── Assertions ─────────────────────────────────────────────────────────────

    def assert_visible(self, selector: str) -> None:
        expect(self.locator(selector)).to_be_visible()

    def assert_text(self, selector: str, text: str) -> None:
        expect(self.locator(selector)).to_have_text(text)

    def assert_url(self, url: str) -> None:
        expect(self.page).to_have_url(url)

    # ── Screenshot ─────────────────────────────────────────────────────────────

    def screenshot(self, name: str) -> bytes:
        return self.page.screenshot(full_page=True)
"""
    else:  # selenium
        content = """\"\"\"BasePage — parent for all Page Object classes (Selenium).\"\"\"
from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import os


DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "30"))


class BasePage:
    \"\"\"Wraps Selenium WebDriver with common reusable actions.\"\"\"

    def __init__(self, driver: WebDriver) -> None:
        self.driver  = driver
        self.wait    = WebDriverWait(driver, DEFAULT_TIMEOUT)
        self.actions = ActionChains(driver)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def navigate(self, url: str) -> None:
        self.driver.get(url)

    def get_url(self) -> str:
        return self.driver.current_url

    def get_title(self) -> str:
        return self.driver.title

    def reload(self) -> None:
        self.driver.refresh()

    # ── Find ──────────────────────────────────────────────────────────────────

    def find(self, by: str, value: str) -> WebElement:
        return self.wait.until(EC.presence_of_element_located((by, value)))

    def find_visible(self, by: str, value: str) -> WebElement:
        return self.wait.until(EC.visibility_of_element_located((by, value)))

    def find_clickable(self, by: str, value: str) -> WebElement:
        return self.wait.until(EC.element_to_be_clickable((by, value)))

    def find_all(self, by: str, value: str) -> list[WebElement]:
        self.wait.until(EC.presence_of_all_elements_located((by, value)))
        return self.driver.find_elements(by, value)

    # ── Actions ────────────────────────────────────────────────────────────────

    def click(self, by: str, value: str) -> None:
        self.find_clickable(by, value).click()

    def fill(self, by: str, value: str, text: str) -> None:
        el = self.find_visible(by, value)
        el.clear()
        el.send_keys(text)

    def select_by_value(self, by: str, value: str, option: str) -> None:
        Select(self.find(by, value)).select_by_value(option)

    def select_by_visible_text(self, by: str, value: str, text: str) -> None:
        Select(self.find(by, value)).select_by_visible_text(text)

    def hover(self, by: str, value: str) -> None:
        self.actions.move_to_element(self.find(by, value)).perform()

    def upload_file(self, by: str, value: str, path: str) -> None:
        self.find(by, value).send_keys(path)

    def scroll_to(self, by: str, value: str) -> None:
        el = self.find(by, value)
        self.driver.execute_script("arguments[0].scrollIntoView(true);", el)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_text(self, by: str, value: str) -> str:
        return self.find_visible(by, value).text

    def get_attribute(self, by: str, value: str, attr: str) -> str:
        return self.find(by, value).get_attribute(attr) or ""

    # ── Assertions ─────────────────────────────────────────────────────────────

    def assert_url_contains(self, partial: str) -> None:
        self.wait.until(EC.url_contains(partial))

    def assert_title_contains(self, text: str) -> None:
        self.wait.until(EC.title_contains(text))

    def is_visible(self, by: str, value: str) -> bool:
        try:
            return self.find(by, value).is_displayed()
        except Exception:
            return False

    # ── Screenshot ─────────────────────────────────────────────────────────────

    def screenshot(self, name: str) -> bytes:
        return self.driver.get_screenshot_as_png()
"""
    return {"filename": "pages/base_page.py", "content": content.strip()}


def generate_python_page_object(
    page_name: str,
    url: str,
    elements_description: str,
    framework: str = "playwright",
) -> dict:
    """Generate a Python Page Object class."""
    class_name = "".join(w.capitalize() for w in page_name.split()) + "Page"
    file_name  = page_name.lower().replace(" ", "_") + "_page"
    import_base = "from playwright.sync_api import Page" if framework == "playwright" else "from selenium.webdriver.common.by import By"
    parent_init = "def __init__(self, page: Page) -> None:\n        super().__init__(page)" if framework == "playwright" else "def __init__(self, driver) -> None:\n        super().__init__(driver)"

    content = f"""\"\"\"
{class_name} — Page Object for: {url}
Elements: {elements_description}
\"\"\"
from __future__ import annotations
{import_base}
from pages.base_page import BasePage


class {class_name}(BasePage):
    URL = "{url}"

    # ── Selectors ─────────────────────────────────────────────────────────────
    # TODO: replace with your actual selectors
    # SUBMIT_BUTTON = "[data-testid='submit']"
    # ERROR_MESSAGE = "[data-testid='error']"

    {parent_init}

    def open(self) -> "{class_name}":
        self.navigate(self.URL)
        return self

    def is_loaded(self) -> bool:
        return self.URL in self.get_url()

    # ── Actions ────────────────────────────────────────────────────────────────
    # def click_submit(self) -> None:
    #     self.click(self.SUBMIT_BUTTON)
"""
    return {
        "filename": f"pages/{file_name}.py",
        "content": content.strip(),
    }


def generate_python_test(
    test_name: str,
    page_name: str,
    test_scenarios: str,
    framework: str = "playwright",
) -> dict:
    """Generate a pytest test file."""
    class_name = "".join(w.capitalize() for w in page_name.split()) + "Page"
    page_file  = page_name.lower().replace(" ", "_") + "_page"
    file_name  = test_name.lower().replace(" ", "_")
    scenarios  = [s.strip() for s in test_scenarios.split(",") if s.strip()]
    if not scenarios:
        scenarios = ["verify page loads", "verify positive flow", "verify error handling"]

    fixture = "page" if framework == "playwright" else "driver"

    test_funcs = []
    for s in scenarios:
        func_name = s.lower().replace(" ", "_").replace("-", "_")
        func_name = "".join(c if c.isalnum() or c == "_" else "_" for c in func_name).strip("_")
        test_funcs.append(f"""
def test_{func_name}({fixture}):
    \"\"\"Scenario: {s}\"\"\"
    po = {class_name}({fixture})
    po.open()
    # TODO: implement assertions for — {s}
    assert po.is_loaded()""")

    funcs_str = "\n".join(test_funcs)
    content = f"""\"\"\"
Tests for {test_name}.
Scenarios: {test_scenarios}
\"\"\"
import allure
import pytest
from pages.{page_file} import {class_name}


@allure.epic("Automation Framework Generator")
@allure.feature("{page_name}")
class Test{class_name.replace('Page', '')}:
{funcs_str}
"""
    return {
        "filename": f"tests/test_{file_name}.py",
        "content": content.strip(),
    }
