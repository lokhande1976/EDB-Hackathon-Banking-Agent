"""Tools that generate utility/helper Java classes and resource files."""

from __future__ import annotations


def generate_config_reader(package_name: str) -> dict:
    """Generate ConfigReader.java — reads config.properties with env-var override.

    Args:
        package_name: Root Java package.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""package {package_name}.utils;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

/**
 * ConfigReader — loads config.properties from the classpath.
 * Environment variables override property file values (CI-friendly).
 */
public final class ConfigReader {{

    private static final Logger log = LogManager.getLogger(ConfigReader.class);
    private static final Properties props = new Properties();

    static {{
        String env = System.getProperty("env", System.getenv().getOrDefault("TEST_ENV", "config"));
        String file = env.equals("config") ? "config.properties" : env + ".config.properties";
        try (InputStream is = ConfigReader.class.getClassLoader().getResourceAsStream(file)) {{
            if (is != null) {{
                props.load(is);
                log.info("Loaded config from: {{}}", file);
            }} else {{
                log.warn("Config file not found: {{}}, using defaults", file);
            }}
        }} catch (IOException e) {{
            log.error("Failed to load config: {{}}", e.getMessage());
        }}
    }}

    private ConfigReader() {{}}

    /**
     * Return a property value. Environment variables take precedence.
     */
    public static String get(String key) {{
        String envKey = key.toUpperCase().replace(".", "_");
        String envVal = System.getenv(envKey);
        if (envVal != null && !envVal.isBlank()) return envVal;
        String sysProp = System.getProperty(key);
        if (sysProp != null && !sysProp.isBlank()) return sysProp;
        return props.getProperty(key, "");
    }}

    public static String get(String key, String defaultValue) {{
        String val = get(key);
        return val.isBlank() ? defaultValue : val;
    }}

    public static int getInt(String key, int defaultValue) {{
        try {{
            return Integer.parseInt(get(key));
        }} catch (NumberFormatException e) {{
            return defaultValue;
        }}
    }}

    public static boolean getBoolean(String key, boolean defaultValue) {{
        String val = get(key);
        return val.isBlank() ? defaultValue : Boolean.parseBoolean(val);
    }}
}}
"""
    return {
        "filename": f"src/main/java/{package_name.replace('.', '/')}/utils/ConfigReader.java",
        "content": content.strip(),
    }


def generate_wait_helper(package_name: str) -> dict:
    """Generate WaitHelper.java — explicit Playwright wait utilities.

    Args:
        package_name: Root Java package.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""package {package_name}.utils;

import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.WaitForSelectorState;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import {package_name}.constants.FrameworkConstants;

/**
 * WaitHelper — centralised explicit-wait utilities for Playwright.
 */
public final class WaitHelper {{

    private static final Logger log = LogManager.getLogger(WaitHelper.class);

    private WaitHelper() {{}}

    public static void waitForVisible(Page page, String selector) {{
        log.debug("Waiting for visible: {{}}", selector);
        page.waitForSelector(selector, new Page.WaitForSelectorOptions()
                .setState(WaitForSelectorState.VISIBLE)
                .setTimeout(FrameworkConstants.DEFAULT_TIMEOUT));
    }}

    public static void waitForHidden(Page page, String selector) {{
        page.waitForSelector(selector, new Page.WaitForSelectorOptions()
                .setState(WaitForSelectorState.HIDDEN)
                .setTimeout(FrameworkConstants.DEFAULT_TIMEOUT));
    }}

    public static void waitForEnabled(Page page, String selector) {{
        Locator loc = page.locator(selector);
        loc.waitFor(new Locator.WaitForOptions()
                .setState(com.microsoft.playwright.options.WaitForSelectorState.VISIBLE)
                .setTimeout(FrameworkConstants.DEFAULT_TIMEOUT));
    }}

    public static void waitForText(Page page, String selector, String text) {{
        page.waitForFunction(
                "([sel, txt]) => document.querySelector(sel)?.textContent?.includes(txt)",
                new Object[]{{selector, text}});
    }}

    public static void waitForUrlContains(Page page, String partial) {{
        page.waitForURL("**" + partial + "**");
    }}

    public static void hardWait(int milliseconds) {{
        try {{
            log.warn("Hard wait: {{}}ms — prefer explicit waits", milliseconds);
            Thread.sleep(milliseconds);
        }} catch (InterruptedException e) {{
            Thread.currentThread().interrupt();
        }}
    }}

    public static void waitForNetworkIdle(Page page) {{
        page.waitForLoadState(com.microsoft.playwright.options.LoadState.NETWORKIDLE);
    }}
}}
"""
    return {
        "filename": f"src/main/java/{package_name.replace('.', '/')}/utils/WaitHelper.java",
        "content": content.strip(),
    }


def generate_screenshot_util(package_name: str) -> dict:
    """Generate ScreenshotUtil.java — full-page and element screenshots with Allure attachment.

    Args:
        package_name: Root Java package.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""package {package_name}.utils;

import com.microsoft.playwright.Page;
import io.qameta.allure.Allure;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * ScreenshotUtil — captures screenshots and attaches them to Allure reports.
 */
public final class ScreenshotUtil {{

    private static final Logger log = LogManager.getLogger(ScreenshotUtil.class);
    private static final String SCREENSHOT_DIR = "target/screenshots/";
    private static final DateTimeFormatter FMT  = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS");

    private ScreenshotUtil() {{}}

    /**
     * Capture a full-page screenshot, save to disk, and attach to Allure.
     *
     * @param page Playwright page instance.
     * @param name Descriptive name for the screenshot.
     * @return Screenshot bytes (null on failure).
     */
    public static byte[] capture(Page page, String name) {{
        if (page == null) return null;
        try {{
            String timestamp = LocalDateTime.now().format(FMT);
            String filename  = sanitize(name) + "_" + timestamp + ".png";
            Path dir         = Paths.get(SCREENSHOT_DIR);
            Files.createDirectories(dir);
            Path file = dir.resolve(filename);

            byte[] bytes = page.screenshot(new Page.ScreenshotOptions().setFullPage(true));
            Files.write(file, bytes);

            Allure.addAttachment(name, "image/png", new ByteArrayInputStream(bytes), ".png");
            log.info("Screenshot saved: {{}}", file);
            return bytes;
        }} catch (IOException e) {{
            log.error("Screenshot failed for '{{}}': {{}}", name, e.getMessage());
            return null;
        }}
    }}

    private static String sanitize(String name) {{
        return name.replaceAll("[^a-zA-Z0-9_\\-]", "_").replaceAll("_+", "_");
    }}
}}
"""
    return {
        "filename": f"src/main/java/{package_name.replace('.', '/')}/utils/ScreenshotUtil.java",
        "content": content.strip(),
    }


def generate_excel_reader(package_name: str) -> dict:
    """Generate ExcelReader.java — reads test data from .xlsx files using Apache POI.

    Args:
        package_name: Root Java package.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""package {package_name}.utils;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * ExcelReader — reads test data from .xlsx files using Apache POI.
 * First row is treated as header; subsequent rows become Map entries.
 */
public final class ExcelReader {{

    private static final Logger log = LogManager.getLogger(ExcelReader.class);

    private ExcelReader() {{}}

    /**
     * Read all rows from a sheet as a list of maps (column header → cell value).
     *
     * @param filePath  Absolute or classpath-relative path to the .xlsx file.
     * @param sheetName Name of the sheet to read.
     * @return List of row maps; empty list on error.
     */
    public static List<Map<String, String>> readSheet(String filePath, String sheetName) {{
        List<Map<String, String>> data = new ArrayList<>();
        try (FileInputStream fis = new FileInputStream(filePath);
             Workbook wb = new XSSFWorkbook(fis)) {{

            Sheet sheet = wb.getSheet(sheetName);
            if (sheet == null) {{
                log.warn("Sheet '{{}}' not found in: {{}}", sheetName, filePath);
                return data;
            }}

            Row header = sheet.getRow(0);
            if (header == null) return data;

            for (int r = 1; r <= sheet.getLastRowNum(); r++) {{
                Row row = sheet.getRow(r);
                if (row == null) continue;
                Map<String, String> rowMap = new LinkedHashMap<>();
                for (int c = 0; c < header.getLastCellNum(); c++) {{
                    String key = getCellValue(header.getCell(c));
                    String val = getCellValue(row.getCell(c));
                    rowMap.put(key, val);
                }}
                data.add(rowMap);
            }}
            log.info("Read {{}} rows from sheet '{{}}' in {{}}", data.size(), sheetName, filePath);
        }} catch (IOException e) {{
            log.error("Failed to read Excel file '{{}}': {{}}", filePath, e.getMessage());
        }}
        return data;
    }}

    private static String getCellValue(Cell cell) {{
        if (cell == null) return "";
        DataFormatter formatter = new DataFormatter();
        return formatter.formatCellValue(cell).trim();
    }}
}}
"""
    return {
        "filename": f"src/main/java/{package_name.replace('.', '/')}/utils/ExcelReader.java",
        "content": content.strip(),
    }


def generate_config_properties(
    app_url: str,
    browser: str = "chromium",
    environment: str = "qa",
) -> dict:
    """Generate config.properties resource file.

    Args:
        app_url: Application base URL.
        browser: Browser name.
        environment: Environment label.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""# ─────────────────────────────────────────────
# Automation Framework Configuration
# Environment: {environment.upper()}
# Override any value via environment variable:
#   BASE_URL, BROWSER, HEADLESS, etc.
# ─────────────────────────────────────────────

# Application
base.url={app_url}
environment={environment}

# Browser
browser={browser}
headless=true
viewport.width=1920
viewport.height=1080
slow.mo=0

# Timeouts (milliseconds)
default.timeout=30000
short.timeout=5000
long.timeout=60000

# Allure
allure.results.dir=target/allure-results

# Video recording (set to true to record test videos)
record.video=false

# Retry
max.retry.count=1
"""
    return {"filename": "src/main/resources/config.properties", "content": content.strip()}


def generate_log4j2_config() -> dict:
    """Generate log4j2.xml for structured console + rolling-file logging.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = """<?xml version="1.0" encoding="UTF-8"?>
<Configuration status="WARN" monitorInterval="30">
    <Properties>
        <Property name="LOG_PATTERN">%d{yyyy-MM-dd HH:mm:ss.SSS} [%t] %-5level %logger{36} - %msg%n</Property>
        <Property name="LOG_DIR">target/logs</Property>
    </Properties>

    <Appenders>
        <!-- Console -->
        <Console name="Console" target="SYSTEM_OUT">
            <PatternLayout pattern="${LOG_PATTERN}"/>
        </Console>

        <!-- Rolling file — one file per day, 30-day retention -->
        <RollingFile name="RollingFile"
                     fileName="${LOG_DIR}/automation.log"
                     filePattern="${LOG_DIR}/automation-%d{yyyy-MM-dd}-%i.log.gz">
            <PatternLayout pattern="${LOG_PATTERN}"/>
            <Policies>
                <TimeBasedTriggeringPolicy/>
                <SizeBasedTriggeringPolicy size="10MB"/>
            </Policies>
            <DefaultRolloverStrategy max="30"/>
        </RollingFile>
    </Appenders>

    <Loggers>
        <!-- Suppress noisy third-party loggers -->
        <Logger name="com.microsoft.playwright" level="WARN" additivity="false">
            <AppenderRef ref="Console"/>
        </Logger>
        <Logger name="org.apache.poi" level="WARN" additivity="false">
            <AppenderRef ref="Console"/>
        </Logger>

        <Root level="INFO">
            <AppenderRef ref="Console"/>
            <AppenderRef ref="RollingFile"/>
        </Root>
    </Loggers>
</Configuration>
"""
    return {"filename": "src/main/resources/log4j2.xml", "content": content.strip()}


def generate_allure_properties(results_dir: str = "target/allure-results") -> dict:
    """Generate allure.properties for the Allure TestNG listener.

    Args:
        results_dir: Directory where Allure writes results.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""allure.results.directory={results_dir}
allure.link.issue.pattern=https://jira.yourdomain.com/browse/{{}}
allure.link.tms.pattern=https://testrail.yourdomain.com/index.php?/cases/view/{{}}
"""
    return {
        "filename": "src/test/resources/allure.properties",
        "content": content.strip(),
    }
