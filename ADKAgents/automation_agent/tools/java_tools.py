"""Tools that generate Java source files — BasePage, BaseTest, Page Objects, Test classes."""

from __future__ import annotations


def generate_base_page(package_name: str) -> dict:
    """Generate BasePage.java with reusable Playwright actions.

    Args:
        package_name: Root Java package (e.g. com.acme.automation).

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""package {package_name}.pages;

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.WaitForSelectorState;
import io.qameta.allure.Step;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import {package_name}.utils.ScreenshotUtil;
import {package_name}.utils.WaitHelper;

import java.nio.file.Paths;

/**
 * BasePage — parent for all Page Object classes.
 * Wraps Playwright Page with common actions, logging, and Allure steps.
 */
public abstract class BasePage {{

    protected final Page page;
    protected final Logger log = LogManager.getLogger(getClass());

    protected BasePage(Page page) {{
        this.page = page;
    }}

    // ── Navigation ──────────────────────────────────────────────────────────

    @Step("Navigate to {{url}}")
    public void navigateTo(String url) {{
        log.info("Navigating to: {{}}", url);
        page.navigate(url);
        page.waitForLoadState();
    }}

    @Step("Reload page")
    public void reload() {{
        page.reload();
        page.waitForLoadState();
    }}

    public String getCurrentUrl() {{
        return page.url();
    }}

    public String getPageTitle() {{
        return page.title();
    }}

    // ── Click ────────────────────────────────────────────────────────────────

    @Step("Click element: {{selector}}")
    public void click(String selector) {{
        log.debug("Clicking: {{}}", selector);
        WaitHelper.waitForVisible(page, selector);
        page.click(selector);
    }}

    @Step("Double-click element: {{selector}}")
    public void doubleClick(String selector) {{
        WaitHelper.waitForVisible(page, selector);
        page.dblclick(selector);
    }}

    @Step("Right-click element: {{selector}}")
    public void rightClick(String selector) {{
        WaitHelper.waitForVisible(page, selector);
        page.click(selector, new Page.ClickOptions().setButton(com.microsoft.playwright.options.MouseButton.RIGHT));
    }}

    // ── Input ────────────────────────────────────────────────────────────────

    @Step("Type '{{text}}' into {{selector}}")
    public void type(String selector, String text) {{
        log.debug("Typing '{{}}' into: {{}}", text, selector);
        WaitHelper.waitForVisible(page, selector);
        page.fill(selector, "");
        page.fill(selector, text);
    }}

    @Step("Clear and type '{{text}}' into {{selector}}")
    public void clearAndType(String selector, String text) {{
        WaitHelper.waitForVisible(page, selector);
        page.locator(selector).clear();
        page.fill(selector, text);
    }}

    @Step("Press key '{{key}}' on {{selector}}")
    public void pressKey(String selector, String key) {{
        page.press(selector, key);
    }}

    // ── Selects & Checkboxes ─────────────────────────────────────────────────

    @Step("Select option '{{value}}' in {{selector}}")
    public void selectByValue(String selector, String value) {{
        page.selectOption(selector, value);
    }}

    @Step("Select option by label '{{label}}' in {{selector}}")
    public void selectByLabel(String selector, String label) {{
        page.selectOption(selector, new com.microsoft.playwright.options.SelectOption().setLabel(label));
    }}

    @Step("Check checkbox: {{selector}}")
    public void check(String selector) {{
        page.check(selector);
    }}

    @Step("Uncheck checkbox: {{selector}}")
    public void uncheck(String selector) {{
        page.uncheck(selector);
    }}

    // ── Read ─────────────────────────────────────────────────────────────────

    public String getText(String selector) {{
        WaitHelper.waitForVisible(page, selector);
        return page.textContent(selector);
    }}

    public String getAttribute(String selector, String attribute) {{
        WaitHelper.waitForVisible(page, selector);
        return page.getAttribute(selector, attribute);
    }}

    public String getInputValue(String selector) {{
        return page.inputValue(selector);
    }}

    // ── Visibility ───────────────────────────────────────────────────────────

    public boolean isVisible(String selector) {{
        return page.isVisible(selector);
    }}

    public boolean isEnabled(String selector) {{
        return page.isEnabled(selector);
    }}

    public boolean isChecked(String selector) {{
        return page.isChecked(selector);
    }}

    // ── Scroll ───────────────────────────────────────────────────────────────

    @Step("Scroll to element: {{selector}}")
    public void scrollToElement(String selector) {{
        page.locator(selector).scrollIntoViewIfNeeded();
    }}

    public void scrollToTop() {{
        page.keyboard().press("Control+Home");
    }}

    public void scrollToBottom() {{
        page.keyboard().press("Control+End");
    }}

    // ── Upload / Download ────────────────────────────────────────────────────

    @Step("Upload file '{{filePath}}' via {{selector}}")
    public void uploadFile(String selector, String filePath) {{
        page.setInputFiles(selector, Paths.get(filePath));
    }}

    // ── Frame ────────────────────────────────────────────────────────────────

    public FrameLocator getFrame(String frameSelector) {{
        return page.frameLocator(frameSelector);
    }}

    // ── Alerts ───────────────────────────────────────────────────────────────

    public void acceptAlert() {{
        page.onDialog(dialog -> dialog.accept());
    }}

    public void dismissAlert() {{
        page.onDialog(dialog -> dialog.dismiss());
    }}

    // ── Screenshot ───────────────────────────────────────────────────────────

    @Step("Take screenshot: {{name}}")
    public byte[] takeScreenshot(String name) {{
        return ScreenshotUtil.capture(page, name);
    }}

    // ── Wait ─────────────────────────────────────────────────────────────────

    public void waitForVisible(String selector) {{
        WaitHelper.waitForVisible(page, selector);
    }}

    public void waitForHidden(String selector) {{
        page.waitForSelector(selector, new Page.WaitForSelectorOptions()
                .setState(WaitForSelectorState.HIDDEN));
    }}

    public void waitForUrl(String urlPattern) {{
        page.waitForURL(urlPattern);
    }}

    public void waitForPageLoad() {{
        page.waitForLoadState();
    }}
}}
"""
    return {
        "filename": f"src/main/java/{package_name.replace('.', '/')}/pages/BasePage.java",
        "content": content.strip(),
    }


def generate_base_test(package_name: str, browser: str = "chromium") -> dict:
    """Generate BaseTest.java with Playwright lifecycle management.

    Args:
        package_name: Root Java package.
        browser: Default browser — 'chromium', 'firefox', or 'webkit'.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""package {package_name}.base;

import com.microsoft.playwright.*;
import io.qameta.allure.Allure;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.testng.ITestResult;
import org.testng.annotations.*;
import {package_name}.utils.ConfigReader;
import {package_name}.utils.ScreenshotUtil;

import java.io.ByteArrayInputStream;
import java.lang.reflect.Method;

/**
 * BaseTest — all test classes extend this.
 * Manages Playwright / Browser / BrowserContext / Page lifecycle per test thread.
 */
public class BaseTest {{

    private static final Logger log = LogManager.getLogger(BaseTest.class);

    // Thread-local so parallel tests don't share browser state
    private static final ThreadLocal<Playwright> playwrightTL = new ThreadLocal<>();
    private static final ThreadLocal<Browser> browserTL     = new ThreadLocal<>();
    private static final ThreadLocal<BrowserContext> contextTL = new ThreadLocal<>();
    private static final ThreadLocal<Page> pageTL           = new ThreadLocal<>();

    protected Page page;
    protected BrowserContext context;

    // ── Suite lifecycle ──────────────────────────────────────────────────────

    @BeforeSuite(alwaysRun = true)
    public void globalSetup() {{
        log.info("=== Test Suite Starting ===");
    }}

    @AfterSuite(alwaysRun = true)
    public void globalTeardown() {{
        log.info("=== Test Suite Finished ===");
    }}

    // ── Test lifecycle ───────────────────────────────────────────────────────

    @BeforeMethod(alwaysRun = true)
    public void setUp(Method method) {{
        log.info("--- Starting test: {{}} ---", method.getName());

        Playwright playwright = Playwright.create();
        playwrightTL.set(playwright);

        String browserName = ConfigReader.get("browser", "{browser}").toLowerCase();
        boolean headless   = Boolean.parseBoolean(ConfigReader.get("headless", "true"));
        String baseUrl     = ConfigReader.get("base.url", "");

        BrowserType.LaunchOptions launchOptions = new BrowserType.LaunchOptions()
                .setHeadless(headless)
                .setSlowMo(Double.parseDouble(ConfigReader.get("slow.mo", "0")));

        Browser browser = switch (browserName) {{
            case "firefox" -> playwright.firefox().launch(launchOptions);
            case "webkit"  -> playwright.webkit().launch(launchOptions);
            default        -> playwright.chromium().launch(launchOptions);
        }};
        browserTL.set(browser);

        Browser.NewContextOptions contextOptions = new Browser.NewContextOptions()
                .setViewportSize(
                        Integer.parseInt(ConfigReader.get("viewport.width",  "1920")),
                        Integer.parseInt(ConfigReader.get("viewport.height", "1080"))
                )
                .setRecordVideoDir(
                        Boolean.parseBoolean(ConfigReader.get("record.video", "false"))
                                ? java.nio.file.Paths.get("target/videos") : null
                );

        BrowserContext ctx = browser.newContext(contextOptions);
        ctx.setDefaultTimeout(Double.parseDouble(ConfigReader.get("default.timeout", "30000")));
        contextTL.set(ctx);

        Page p = ctx.newPage();
        pageTL.set(p);

        this.context = ctx;
        this.page    = p;

        if (!baseUrl.isEmpty()) {{
            p.navigate(baseUrl);
            p.waitForLoadState();
        }}

        log.info("Browser: {{}}, Headless: {{}}, BaseURL: {{}}", browserName, headless, baseUrl);
    }}

    @AfterMethod(alwaysRun = true)
    public void tearDown(ITestResult result) {{
        String testName = result.getMethod().getMethodName();

        if (result.getStatus() == ITestResult.FAILURE) {{
            log.error("Test FAILED: {{}}", testName);
            byte[] screenshot = ScreenshotUtil.capture(pageTL.get(), testName);
            if (screenshot != null) {{
                Allure.addAttachment("Failure Screenshot", "image/png",
                        new ByteArrayInputStream(screenshot), ".png");
            }}
        }}

        Page p = pageTL.get();
        if (p != null) p.close();

        BrowserContext ctx = contextTL.get();
        if (ctx != null) ctx.close();

        Browser b = browserTL.get();
        if (b != null) b.close();

        Playwright pw = playwrightTL.get();
        if (pw != null) pw.close();

        playwrightTL.remove();
        browserTL.remove();
        contextTL.remove();
        pageTL.remove();

        log.info("--- Test {{}}: {{}} ---", testName,
                result.getStatus() == ITestResult.SUCCESS ? "PASSED" : "FAILED");
    }}
}}
"""
    return {
        "filename": f"src/test/java/{package_name.replace('.', '/')}/base/BaseTest.java",
        "content": content.strip(),
    }


def generate_page_object(
    page_name: str,
    package_name: str,
    url: str,
    elements_description: str,
) -> dict:
    """Generate a Page Object class for the given page.

    Args:
        page_name: Class name prefix (e.g. 'Login' → LoginPage.java).
        package_name: Root Java package.
        url: URL of the page (used in javadoc).
        elements_description: Natural-language description of page elements and actions.

    Returns:
        dict with 'filename' and 'content'.
    """
    class_name = page_name.strip().replace(" ", "") + "Page"
    content = f"""package {package_name}.pages;

import com.microsoft.playwright.Page;
import io.qameta.allure.Step;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * {class_name} — Page Object for: {url}
 *
 * Elements covered:
 * {elements_description}
 */
public class {class_name} extends BasePage {{

    private static final Logger log = LogManager.getLogger({class_name}.class);

    // ── Selectors ────────────────────────────────────────────────────────────
    // Use data-testid attributes where available; fall back to CSS/XPath.

    // TODO: Replace with your actual selectors. Examples:
    // private static final String USERNAME_FIELD  = "[data-testid='username']";
    // private static final String PASSWORD_FIELD  = "[data-testid='password']";
    // private static final String SUBMIT_BUTTON   = "[data-testid='submit']";
    // private static final String ERROR_MESSAGE   = ".error-message";
    // private static final String SUCCESS_BANNER  = ".success-banner";

    // ── Constructor ──────────────────────────────────────────────────────────

    public {class_name}(Page page) {{
        super(page);
    }}

    // ── Navigation ───────────────────────────────────────────────────────────

    @Step("Open {page_name} page")
    public {class_name} open() {{
        navigateTo("{url}");
        log.info("{page_name} page opened");
        return this;
    }}

    @Step("Verify {page_name} page is loaded")
    public boolean isLoaded() {{
        // TODO: update with a reliable indicator that this page is fully loaded
        // return isVisible(SUBMIT_BUTTON);
        return page.url().contains("{url}");
    }}

    // ── Page Actions ─────────────────────────────────────────────────────────
    // Add one @Step method per meaningful user action on this page.

    // Example:
    // @Step("Enter username: {{username}}")
    // public {class_name} enterUsername(String username) {{
    //     type(USERNAME_FIELD, username);
    //     return this;
    // }}

    // @Step("Click Submit button")
    // public void clickSubmit() {{
    //     click(SUBMIT_BUTTON);
    //     waitForPageLoad();
    // }}

    // ── Assertions Helpers ───────────────────────────────────────────────────

    // @Step("Get error message text")
    // public String getErrorMessage() {{
    //     return getText(ERROR_MESSAGE);
    // }}

    // @Step("Is success banner visible")
    // public boolean isSuccessBannerVisible() {{
    //     return isVisible(SUCCESS_BANNER);
    // }}
}}
"""
    return {
        "filename": f"src/main/java/{package_name.replace('.', '/')}/pages/{class_name}.java",
        "content": content.strip(),
    }


def generate_test_class(
    test_name: str,
    page_name: str,
    package_name: str,
    test_scenarios: str,
) -> dict:
    """Generate a TestNG test class for a given page.

    Args:
        test_name: Class name prefix (e.g. 'Login' → LoginTest.java).
        page_name: Corresponding Page Object name (e.g. 'Login').
        package_name: Root Java package.
        test_scenarios: Comma-separated list of scenario names to scaffold.

    Returns:
        dict with 'filename' and 'content'.
    """
    class_name  = test_name.strip().replace(" ", "") + "Test"
    page_class  = page_name.strip().replace(" ", "") + "Page"
    page_var    = page_class[0].lower() + page_class[1:]

    scenarios = [s.strip() for s in test_scenarios.split(",") if s.strip()]
    if not scenarios:
        scenarios = ["verifyPageLoads", "verifyPositiveFlow", "verifyNegativeFlow"]

    methods = []
    for scenario in scenarios:
        method_name = scenario[0].lower() + scenario[1:].replace(" ", "")
        method_name = "".join(
            c if c.isalnum() or c == "_" else "_" for c in method_name
        ).strip("_")
        methods.append(f"""
    @Test(description = "{scenario}", priority = {scenarios.index(scenario) + 1})
    @io.qameta.allure.Description("{scenario} — verify expected outcome")
    @io.qameta.allure.Severity(io.qameta.allure.SeverityLevel.CRITICAL)
    public void {method_name}() {{
        // Arrange
        {page_var}.open();

        // Act
        // TODO: perform actions here

        // Assert
        // assertThat({page_var}.isLoaded()).isTrue();
    }}""")

    methods_block = "\n".join(methods)

    content = f"""package {package_name}.tests;

import io.qameta.allure.*;
import org.assertj.core.api.Assertions;
import static org.assertj.core.api.Assertions.assertThat;
import org.testng.annotations.*;
import {package_name}.base.BaseTest;
import {package_name}.pages.{page_class};

/**
 * {class_name} — test suite for {page_name} functionality.
 *
 * Scenarios:
 * {test_scenarios}
 */
@Epic("Automation Framework Generator")
@Feature("{page_name}")
public class {class_name} extends BaseTest {{

    private {page_class} {page_var};

    @BeforeMethod(alwaysRun = true)
    public void initPages() {{
        {page_var} = new {page_class}(page);
    }}
{methods_block}
}}
"""
    return {
        "filename": f"src/test/java/{package_name.replace('.', '/')}/tests/{class_name}.java",
        "content": content.strip(),
    }


def generate_constants(package_name: str, app_url: str) -> dict:
    """Generate FrameworkConstants.java.

    Args:
        package_name: Root Java package.
        app_url: Application base URL.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""package {package_name}.constants;

/**
 * Central place for framework-wide string constants.
 * Never hard-code these values in page objects or tests.
 */
public final class FrameworkConstants {{

    private FrameworkConstants() {{}}

    public static final String BASE_URL          = "{app_url}";
    public static final String RESOURCES_PATH    = "src/test/resources/";
    public static final String TESTDATA_PATH     = RESOURCES_PATH + "testdata/";
    public static final String SCREENSHOT_PATH   = "target/screenshots/";
    public static final long   DEFAULT_TIMEOUT   = 30_000L;
    public static final long   SHORT_TIMEOUT     = 5_000L;
    public static final long   LONG_TIMEOUT      = 60_000L;
}}
"""
    return {
        "filename": f"src/main/java/{package_name.replace('.', '/')}/constants/FrameworkConstants.java",
        "content": content.strip(),
    }
