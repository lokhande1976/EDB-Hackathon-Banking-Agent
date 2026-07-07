"""Tools that generate CI/CD, Docker, and documentation files."""

from __future__ import annotations


def generate_github_actions(project_name: str, java_version: str = "17") -> dict:
    """Generate .github/workflows/ci.yml — full CI pipeline with caching and Allure.

    Args:
        project_name: Project name for display labels.
        java_version: Java version string.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""name: {project_name} — Playwright CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    # Nightly regression run at 02:00 UTC
    - cron: '0 2 * * *'
  workflow_dispatch:
    inputs:
      browser:
        description: 'Browser (chromium / firefox / webkit)'
        required: false
        default: 'chromium'
      headless:
        description: 'Run headless?'
        required: false
        default: 'true'
      environment:
        description: 'Target environment (qa / staging / prod)'
        required: false
        default: 'qa'

env:
  JAVA_VERSION: '{java_version}'
  BROWSER: ${{{{ github.event.inputs.browser || 'chromium' }}}}
  HEADLESS: ${{{{ github.event.inputs.headless || 'true' }}}}
  TEST_ENV: ${{{{ github.event.inputs.environment || 'qa' }}}}

jobs:
  test:
    name: Run Playwright Tests
    runs-on: ubuntu-latest
    timeout-minutes: 60

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Java ${{{{ env.JAVA_VERSION }}}}
        uses: actions/setup-java@v4
        with:
          java-version: ${{{{ env.JAVA_VERSION }}}}
          distribution: 'temurin'
          cache: 'maven'

      - name: Cache Maven dependencies
        uses: actions/cache@v4
        with:
          path: ~/.m2/repository
          key: ${{{{ runner.os }}}}-maven-${{{{ hashFiles('**/pom.xml') }}}}
          restore-keys: |
            ${{{{ runner.os }}}}-maven-

      - name: Install Playwright browsers
        run: mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="install --with-deps ${{{{ env.BROWSER }}}}"

      - name: Run tests
        run: |
          mvn test \\
            -Dbrowser=${{{{ env.BROWSER }}}} \\
            -Dheadless=${{{{ env.HEADLESS }}}} \\
            -Denv=${{{{ env.TEST_ENV }}}} \\
            -Dsurefire.useFile=false
        env:
          BASE_URL: ${{{{ secrets.BASE_URL }}}}

      - name: Upload Allure results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: allure-results-${{{{ github.run_number }}}}
          path: target/allure-results/
          retention-days: 30

      - name: Upload screenshots (on failure)
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: screenshots-${{{{ github.run_number }}}}
          path: target/screenshots/
          retention-days: 7

      - name: Upload test logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: logs-${{{{ github.run_number }}}}
          path: target/logs/
          retention-days: 7

  allure-report:
    name: Publish Allure Report
    needs: test
    if: always()
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Download Allure results
        uses: actions/download-artifact@v4
        with:
          name: allure-results-${{{{ github.run_number }}}}
          path: allure-results/

      - name: Generate Allure report
        uses: simple-elf/allure-report-action@v1.7
        with:
          allure_results: allure-results
          allure_report: allure-report
          gh_pages: gh-pages
          allure_history: allure-history
          keep_reports: 20

      - name: Deploy Allure report to GitHub Pages
        if: github.ref == 'refs/heads/main'
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{{{ secrets.GITHUB_TOKEN }}}}
          publish_branch: gh-pages
          publish_dir: allure-history
"""
    return {
        "filename": ".github/workflows/ci.yml",
        "content": content.strip(),
    }


def generate_dockerfile(project_name: str, java_version: str = "17") -> dict:
    """Generate a multi-stage Dockerfile for running tests in containers.

    Args:
        project_name: Project name for image labels.
        java_version: Java version.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM maven:3.9.6-eclipse-temurin-{java_version} AS build

LABEL org.opencontainers.image.title="{project_name} Automation"
LABEL org.opencontainers.image.description="Playwright Java test runner"

WORKDIR /app
COPY pom.xml .
# Download dependencies first (cached layer)
RUN mvn dependency:go-offline -q

COPY src ./src
COPY testng.xml .

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM mcr.microsoft.com/playwright/java:{java_version}-noble AS runtime

WORKDIR /app
COPY --from=build /app /app
COPY --from=build /root/.m2 /root/.m2

# Environment defaults (override at docker run / docker-compose)
ENV HEADLESS=true \\
    BROWSER=chromium \\
    TEST_ENV=qa \\
    BASE_URL=""

# Install Playwright browsers
RUN mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI \\
    -D exec.args="install --with-deps chromium firefox webkit"

# Run tests; results written to /app/target/allure-results
CMD ["mvn", "test", "-Dheadless=true"]
"""
    return {"filename": "Dockerfile", "content": content.strip()}


def generate_docker_compose(project_name: str, app_url: str = "") -> dict:
    """Generate docker-compose.yml with test runner and Allure server services.

    Args:
        project_name: Project name (used for service/container names).
        app_url: Application URL to inject as an environment variable.

    Returns:
        dict with 'filename' and 'content'.
    """
    safe_name = project_name.lower().replace(" ", "-")
    content = f"""version: '3.9'

services:
  # ── Test Runner ─────────────────────────────────────────────────────────────
  test-runner:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: {safe_name}-runner
    environment:
      - BASE_URL={app_url}
      - BROWSER=${{BROWSER:-chromium}}
      - HEADLESS=${{HEADLESS:-true}}
      - TEST_ENV=${{TEST_ENV:-qa}}
    volumes:
      - ./target/allure-results:/app/target/allure-results
      - ./target/screenshots:/app/target/screenshots
      - ./target/logs:/app/target/logs
    networks:
      - test-net

  # ── Allure Report Server ────────────────────────────────────────────────────
  allure:
    image: frankescobar/allure-docker-service:latest
    container_name: {safe_name}-allure
    environment:
      CHECK_RESULTS_EVERY_SECONDS: 5
      KEEP_HISTORY: 20
    ports:
      - "5050:5050"   # Allure UI
      - "5252:5252"   # Allure API
    volumes:
      - ./target/allure-results:/app/allure-results
      - ./target/allure-reports:/app/default-reports
    depends_on:
      - test-runner
    networks:
      - test-net

networks:
  test-net:
    driver: bridge

# ── Usage ──────────────────────────────────────────────────────────────────────
# Run tests:
#   docker-compose up test-runner
#
# View Allure report:
#   docker-compose up allure
#   Open: http://localhost:5050/allure-docker-service/projects/default/reports/latest/index.html
#
# Run specific browser:
#   BROWSER=firefox docker-compose up test-runner
"""
    return {"filename": "docker-compose.yml", "content": content.strip()}


def generate_readme(
    project_name: str,
    group_id: str,
    artifact_id: str,
    app_url: str,
    author: str = "Your Name",
) -> dict:
    """Generate a comprehensive README.md.

    Args:
        project_name: Human-readable project name.
        group_id: Maven group id.
        artifact_id: Maven artifact id.
        app_url: Application URL under test.
        author: Author name.

    Returns:
        dict with 'filename' and 'content'.
    """
    content = f"""# {project_name} — Playwright Automation Framework

> End-to-end test automation framework built with **Java 17**, **Playwright**, **TestNG**, and **Allure Reports**.
> Generated by the [ADK Automation Framework Generator](https://github.com) 🤖

[![CI](https://github.com/your-org/{artifact_id}/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/{artifact_id}/actions/workflows/ci.yml)
[![Allure Report](https://img.shields.io/badge/Allure-Report-brightgreen)](https://your-org.github.io/{artifact_id}/)
[![Java](https://img.shields.io/badge/Java-17-blue)](https://adoptium.net/)
[![Playwright](https://img.shields.io/badge/Playwright-1.44.0-green)](https://playwright.dev/java/)

---

## Technology Stack

| Layer        | Technology                        |
|--------------|-----------------------------------|
| Language     | Java 17                           |
| Test Runner  | TestNG 7.10.0                     |
| Browser      | Playwright Java 1.44.0            |
| Reporting    | Allure 2.27.0                     |
| Build        | Maven 3.9+                        |
| Logging      | Log4j2 2.23.1                     |
| Test Data    | Apache POI (Excel) + Jackson (JSON)|
| CI/CD        | GitHub Actions                    |
| Containers   | Docker + Docker Compose           |

---

## Prerequisites

| Tool             | Version  | Install                                      |
|------------------|----------|----------------------------------------------|
| Java JDK         | 17+      | https://adoptium.net/                        |
| Apache Maven     | 3.9+     | https://maven.apache.org/download.cgi        |
| Git              | any      | https://git-scm.com/                         |
| Docker (optional)| 24+      | https://www.docker.com/products/docker-desktop |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-org/{artifact_id}.git
cd {artifact_id}
mvn dependency:resolve
```

### 2. Install Playwright browsers

```bash
mvn exec:java -e -D exec.mainClass=com.microsoft.playwright.CLI -D exec.args="install --with-deps chromium"
```

### 3. Configure

Edit `src/main/resources/config.properties`:

```properties
base.url={app_url}
browser=chromium
headless=true
```

Or pass values at runtime:

```bash
mvn test -Dbase.url={app_url} -Dbrowser=firefox -Dheadless=false
```

### 4. Run tests

```bash
# All tests (headless)
mvn test

# Specific browser, headed
mvn test -Dbrowser=firefox -Dheadless=false

# Specific test class
mvn test -Dtest=LoginTest

# Generate and open Allure report
mvn allure:serve
```

---

## Running with Docker

```bash
# Build and run tests
docker-compose up test-runner

# Start Allure report server
docker-compose up allure
# → http://localhost:5050

# Run with a specific browser
BROWSER=firefox docker-compose up test-runner
```

---

## Project Structure

```
{artifact_id}/
├── pom.xml                         Maven build descriptor
├── testng.xml                      TestNG suite configuration
├── Dockerfile                      Docker image for test execution
├── docker-compose.yml              Orchestrates runner + Allure server
├── .github/workflows/ci.yml        GitHub Actions CI pipeline
└── src/
    ├── main/java/{group_id.replace('.', '/')}/
    │   ├── pages/
    │   │   ├── BasePage.java       Common Playwright actions
    │   │   └── *Page.java          Page Object classes
    │   ├── utils/
    │   │   ├── ConfigReader.java   Property + env-var config
    │   │   ├── WaitHelper.java     Explicit wait utilities
    │   │   ├── ScreenshotUtil.java Screenshot + Allure attach
    │   │   └── ExcelReader.java    Apache POI data reader
    │   └── constants/
    │       └── FrameworkConstants.java
    ├── main/resources/
    │   ├── config.properties       Framework configuration
    │   └── log4j2.xml              Logging configuration
    └── test/java/{group_id.replace('.', '/')}/
        ├── base/BaseTest.java      Browser lifecycle + setup
        └── tests/*Test.java        Test classes
```

---

## Writing Tests

### 1. Create a Page Object

```java
public class DashboardPage extends BasePage {{
    private static final String WELCOME_MSG = "[data-testid='welcome']";

    public DashboardPage(Page page) {{ super(page); }}

    @Step("Get welcome message")
    public String getWelcomeMessage() {{ return getText(WELCOME_MSG); }}
}}
```

### 2. Write a Test

```java
public class DashboardTest extends BaseTest {{
    private DashboardPage dashboard;

    @BeforeMethod
    public void init() {{ dashboard = new DashboardPage(page); }}

    @Test(description = "Verify welcome message")
    public void verifyWelcomeMessage() {{
        dashboard.open();
        assertThat(dashboard.getWelcomeMessage()).contains("Welcome");
    }}
}}
```

### 3. Add to testng.xml

```xml
<class name="{group_id}.tests.DashboardTest"/>
```

---

## Configuration Reference

| Property           | Default      | Description                   |
|--------------------|--------------|-------------------------------|
| `base.url`         | —            | Application URL under test    |
| `browser`          | `chromium`   | `chromium`, `firefox`, `webkit`|
| `headless`         | `true`       | Run headless                  |
| `default.timeout`  | `30000`      | Element wait timeout (ms)     |
| `viewport.width`   | `1920`       | Browser viewport width        |
| `viewport.height`  | `1080`       | Browser viewport height       |
| `slow.mo`          | `0`          | Slow-motion delay (ms)        |
| `record.video`     | `false`      | Record test videos            |

---

## CI/CD

The GitHub Actions pipeline in `.github/workflows/ci.yml`:

- Triggers on push, PR, and nightly schedule
- Caches Maven dependencies for fast builds
- Installs Playwright browsers
- Runs tests in parallel (4 threads by default)
- Uploads Allure results as artifacts
- Publishes the Allure report to GitHub Pages on `main` merges

### Required GitHub Secrets

| Secret     | Description               |
|------------|---------------------------|
| `BASE_URL` | Application URL under test|

---

## Allure Report

```bash
# After running tests:
mvn allure:serve          # Generates and opens report in browser
mvn allure:report         # Generates report to target/site/allure-maven-plugin/
```

---

## Author

**{author}**
- LinkedIn: https://www.linkedin.com/in/your-profile
- GitHub: https://github.com/your-org/{artifact_id}

---

*Generated by the ADK Automation Framework Generator — [Get it here](https://github.com)*
"""
    return {"filename": "README.md", "content": content.strip()}
