"""Tools that generate TypeScript + Playwright project files."""

from __future__ import annotations


def generate_ts_playwright_package_json(
    project_name: str,
    artifact_id: str,
) -> dict:
    """Generate package.json for TypeScript + Playwright project."""
    content = f"""{{
  "name": "{artifact_id}",
  "version": "1.0.0",
  "description": "{project_name} — Playwright TypeScript Automation Framework",
  "scripts": {{
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "test:report": "playwright show-report",
    "test:chromium": "playwright test --project=chromium",
    "test:firefox": "playwright test --project=firefox",
    "test:webkit": "playwright test --project=webkit",
    "test:mobile": "playwright test --project='Mobile Chrome'",
    "lint": "eslint . --ext .ts",
    "lint:fix": "eslint . --ext .ts --fix",
    "allure:generate": "allure generate allure-results --clean -o allure-report",
    "allure:open": "allure open allure-report"
  }},
  "devDependencies": {{
    "@playwright/test": "^1.44.0",
    "@types/node": "^20.14.0",
    "typescript": "^5.4.5",
    "eslint": "^9.5.0",
    "@typescript-eslint/eslint-plugin": "^7.13.0",
    "@typescript-eslint/parser": "^7.13.0",
    "allure-playwright": "^3.0.0",
    "dotenv": "^16.4.5",
    "@faker-js/faker": "^8.4.1",
    "xlsx": "^0.18.5"
  }}
}}
"""
    return {"filename": "package.json", "content": content.strip()}


def generate_ts_playwright_config(
    project_name: str,
    app_url: str,
    browser: str = "chromium",
) -> dict:
    """Generate playwright.config.ts."""
    content = f"""import {{ defineConfig, devices }} from '@playwright/test';
import * as dotenv from 'dotenv';

dotenv.config();

/**
 * Playwright configuration for {project_name}.
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({{
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 4 : undefined,
  timeout: 30_000,
  expect: {{
    timeout: 10_000,
  }},

  reporter: [
    ['list'],
    ['html', {{ open: 'never', outputFolder: 'playwright-report' }}],
    ['allure-playwright', {{ detail: true, outputFolder: 'allure-results' }}],
    ['junit', {{ outputFile: 'test-results/results.xml' }}],
  ],

  use: {{
    baseURL: process.env.BASE_URL || '{app_url}',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  }},

  projects: [
    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
    {{
      name: 'firefox',
      use: {{ ...devices['Desktop Firefox'] }},
    }},
    {{
      name: 'webkit',
      use: {{ ...devices['Desktop Safari'] }},
    }},
    {{
      name: 'Mobile Chrome',
      use: {{ ...devices['Pixel 5'] }},
    }},
    {{
      name: 'Mobile Safari',
      use: {{ ...devices['iPhone 12'] }},
    }},
  ],

  outputDir: 'test-results/',
}});
"""
    return {"filename": "playwright.config.ts", "content": content.strip()}


def generate_ts_playwright_tsconfig() -> dict:
    """Generate tsconfig.json."""
    content = """{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM"],
    "module": "commonjs",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "outDir": "./dist",
    "rootDir": "./",
    "baseUrl": ".",
    "paths": {
      "@pages/*": ["pages/*"],
      "@utils/*": ["utils/*"],
      "@fixtures/*": ["fixtures/*"]
    }
  },
  "include": ["**/*.ts"],
  "exclude": ["node_modules", "dist"]
}
"""
    return {"filename": "tsconfig.json", "content": content.strip()}


def generate_ts_playwright_base_page(package_name: str) -> dict:
    """Generate pages/BasePage.ts."""
    content = """import { Page, Locator, expect } from '@playwright/test';

/**
 * BasePage — parent for all Page Object classes.
 * Wraps Playwright Page with common actions and assertions.
 */
export abstract class BasePage {
  protected readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  // ── Navigation ─────────────────────────────────────────────────────────────

  async navigate(url: string): Promise<void> {
    await this.page.goto(url);
    await this.waitForPageLoad();
  }

  async reload(): Promise<void> {
    await this.page.reload();
    await this.waitForPageLoad();
  }

  getUrl(): string {
    return this.page.url();
  }

  async getTitle(): Promise<string> {
    return await this.page.title();
  }

  // ── Locators ──────────────────────────────────────────────────────────────

  protected locator(selector: string): Locator {
    return this.page.locator(selector);
  }

  protected getByTestId(testId: string): Locator {
    return this.page.getByTestId(testId);
  }

  protected getByRole(role: Parameters<Page['getByRole']>[0], options?: Parameters<Page['getByRole']>[1]): Locator {
    return this.page.getByRole(role, options);
  }

  protected getByLabel(label: string): Locator {
    return this.page.getByLabel(label);
  }

  protected getByPlaceholder(placeholder: string): Locator {
    return this.page.getByPlaceholder(placeholder);
  }

  protected getByText(text: string): Locator {
    return this.page.getByText(text);
  }

  // ── Actions ────────────────────────────────────────────────────────────────

  async click(selector: string): Promise<void> {
    await this.locator(selector).click();
  }

  async fill(selector: string, value: string): Promise<void> {
    await this.locator(selector).clear();
    await this.locator(selector).fill(value);
  }

  async type(selector: string, value: string): Promise<void> {
    await this.locator(selector).pressSequentially(value, { delay: 50 });
  }

  async selectOption(selector: string, value: string): Promise<void> {
    await this.locator(selector).selectOption(value);
  }

  async check(selector: string): Promise<void> {
    await this.locator(selector).check();
  }

  async uncheck(selector: string): Promise<void> {
    await this.locator(selector).uncheck();
  }

  async hover(selector: string): Promise<void> {
    await this.locator(selector).hover();
  }

  async pressKey(key: string): Promise<void> {
    await this.page.keyboard.press(key);
  }

  async uploadFile(selector: string, filePath: string): Promise<void> {
    await this.locator(selector).setInputFiles(filePath);
  }

  async dragAndDrop(source: string, target: string): Promise<void> {
    await this.locator(source).dragTo(this.locator(target));
  }

  // ── Read ──────────────────────────────────────────────────────────────────

  async getText(selector: string): Promise<string> {
    return await this.locator(selector).textContent() ?? '';
  }

  async getInputValue(selector: string): Promise<string> {
    return await this.locator(selector).inputValue();
  }

  async getAttribute(selector: string, attribute: string): Promise<string | null> {
    return await this.locator(selector).getAttribute(attribute);
  }

  async getAllTexts(selector: string): Promise<string[]> {
    return await this.locator(selector).allTextContents();
  }

  // ── Visibility ─────────────────────────────────────────────────────────────

  async isVisible(selector: string): Promise<boolean> {
    return await this.locator(selector).isVisible();
  }

  async isEnabled(selector: string): Promise<boolean> {
    return await this.locator(selector).isEnabled();
  }

  async isChecked(selector: string): Promise<boolean> {
    return await this.locator(selector).isChecked();
  }

  // ── Waits ──────────────────────────────────────────────────────────────────

  async waitForVisible(selector: string, timeout?: number): Promise<void> {
    await this.locator(selector).waitFor({ state: 'visible', timeout });
  }

  async waitForHidden(selector: string, timeout?: number): Promise<void> {
    await this.locator(selector).waitFor({ state: 'hidden', timeout });
  }

  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  async waitForUrl(urlPattern: string | RegExp): Promise<void> {
    await this.page.waitForURL(urlPattern);
  }

  // ── Assertions ─────────────────────────────────────────────────────────────

  async assertVisible(selector: string): Promise<void> {
    await expect(this.locator(selector)).toBeVisible();
  }

  async assertText(selector: string, text: string): Promise<void> {
    await expect(this.locator(selector)).toHaveText(text);
  }

  async assertContainsText(selector: string, text: string): Promise<void> {
    await expect(this.locator(selector)).toContainText(text);
  }

  async assertUrl(url: string | RegExp): Promise<void> {
    await expect(this.page).toHaveURL(url);
  }

  async assertTitle(title: string | RegExp): Promise<void> {
    await expect(this.page).toHaveTitle(title);
  }

  // ── Screenshot ─────────────────────────────────────────────────────────────

  async screenshot(name: string): Promise<Buffer> {
    return await this.page.screenshot({ path: `test-results/screenshots/${name}.png`, fullPage: true });
  }

  // ── Scroll ─────────────────────────────────────────────────────────────────

  async scrollToElement(selector: string): Promise<void> {
    await this.locator(selector).scrollIntoViewIfNeeded();
  }
}
"""
    return {"filename": "pages/BasePage.ts", "content": content.strip()}


def generate_ts_playwright_fixtures(package_name: str) -> dict:
    """Generate fixtures/fixtures.ts — shared Playwright test fixtures."""
    content = """import { test as base } from '@playwright/test';

/**
 * Extend Playwright's base `test` with page-object fixtures.
 * Import `test` from this file instead of '@playwright/test' in all test files.
 *
 * Usage:
 *   import { test, expect } from '../fixtures/fixtures';
 *   test('my test', async ({ loginPage }) => { ... });
 */

// Add your page objects here:
// import { LoginPage } from '../pages/LoginPage';

type Fixtures = {
  // loginPage: LoginPage;
};

export const test = base.extend<Fixtures>({
  // loginPage: async ({ page }, use) => {
  //   await use(new LoginPage(page));
  // },
});

export { expect } from '@playwright/test';
"""
    return {"filename": "fixtures/fixtures.ts", "content": content.strip()}


def generate_ts_playwright_page_object(
    page_name: str,
    url: str,
    elements_description: str,
) -> dict:
    """Generate a TypeScript Page Object class."""
    class_name = page_name.strip().replace(" ", "") + "Page"
    content = f"""import {{ Page, Locator, expect }} from '@playwright/test';
import {{ BasePage }} from './BasePage';

/**
 * {class_name} — Page Object for: {url}
 *
 * Elements:
 * {elements_description}
 */
export class {class_name} extends BasePage {{
  // ── Locators ───────────────────────────────────────────────────────────────
  // Prefer data-testid > ARIA role > CSS. Never XPath unless unavoidable.

  // readonly usernameInput: Locator = this.page.getByTestId('username');
  // readonly passwordInput: Locator = this.page.getByTestId('password');
  // readonly submitButton:  Locator = this.page.getByRole('button', {{ name: 'Sign in' }});
  // readonly errorMessage:  Locator = this.page.getByTestId('error-message');

  constructor(page: Page) {{
    super(page);
  }}

  // ── Navigation ─────────────────────────────────────────────────────────────

  async open(): Promise<{class_name}> {{
    await this.navigate('{url}');
    return this;
  }}

  async isLoaded(): Promise<boolean> {{
    // TODO: update with a reliable indicator
    return this.getUrl().includes('{url}');
  }}

  // ── Actions ────────────────────────────────────────────────────────────────
  // One method per meaningful user action. Return `this` for chainability.

  // async enterUsername(username: string): Promise<{class_name}> {{
  //   await this.fill('input[name="username"]', username);
  //   return this;
  // }}

  // async clickSubmit(): Promise<void> {{
  //   await this.submitButton.click();
  //   await this.waitForPageLoad();
  // }}

  // ── Assertions ─────────────────────────────────────────────────────────────

  // async expectErrorMessage(message: string): Promise<void> {{
  //   await expect(this.errorMessage).toContainText(message);
  // }}
}}
"""
    return {
        "filename": f"pages/{class_name}.ts",
        "content": content.strip(),
    }


def generate_ts_playwright_test(
    test_name: str,
    page_name: str,
    test_scenarios: str,
) -> dict:
    """Generate a Playwright TypeScript test file."""
    class_name = page_name.strip().replace(" ", "") + "Page"
    file_name = test_name.lower().replace(" ", "-")
    scenarios = [s.strip() for s in test_scenarios.split(",") if s.strip()]
    if not scenarios:
        scenarios = ["verify page loads", "verify positive flow", "verify negative flow"]

    test_blocks = []
    for s in scenarios:
        test_blocks.append(f"""
  test('{s}', async ({{ page }}) => {{
    const {page_name.lower()}Page = new {class_name}(page);
    await {page_name.lower()}Page.open();

    // TODO: implement test for — {s}
    await {page_name.lower()}Page.assertUrl(/{page_name.lower()}/);
  }});""")

    tests_str = "\n".join(test_blocks)

    content = f"""import {{ test, expect }} from '@playwright/test';
import {{ {class_name} }} from '../pages/{class_name}';

/**
 * {test_name} test suite.
 * Scenarios: {test_scenarios}
 */
test.describe('{test_name}', () => {{
  test.beforeEach(async ({{ page }}) => {{
    // Common setup — e.g. navigate to the page or authenticate
  }});
{tests_str}
}});
"""
    return {
        "filename": f"tests/{file_name}.spec.ts",
        "content": content.strip(),
    }


def generate_ts_playwright_env() -> dict:
    """Generate .env.example for TypeScript Playwright."""
    content = """# Copy this file to .env and fill in your values.
# .env is gitignored — never commit real credentials.

BASE_URL=https://your-app.example.com
TEST_USER_EMAIL=testuser@example.com
TEST_USER_PASSWORD=YourSecurePassword123!
HEADLESS=true
BROWSER=chromium
"""
    return {"filename": ".env.example", "content": content.strip()}


def generate_ts_playwright_utils() -> dict:
    """Generate utils/helpers.ts — shared test utilities."""
    content = """import * as fs from 'fs';
import * as path from 'path';
import * as XLSX from 'xlsx';
import { faker } from '@faker-js/faker';

// ── Faker helpers ────────────────────────────────────────────────────────────

export const generateUser = () => ({
  firstName: faker.person.firstName(),
  lastName:  faker.person.lastName(),
  email:     faker.internet.email(),
  phone:     faker.phone.number(),
  password:  faker.internet.password({ length: 12, memorable: false }),
});

// ── Excel reader ─────────────────────────────────────────────────────────────

export function readExcelSheet(filePath: string, sheetName: string): Record<string, string>[] {
  const workbook = XLSX.readFile(filePath);
  const sheet = workbook.Sheets[sheetName];
  if (!sheet) throw new Error(`Sheet "${sheetName}" not found in ${filePath}`);
  return XLSX.utils.sheet_to_json<Record<string, string>>(sheet);
}

// ── Config helpers ───────────────────────────────────────────────────────────

export function getEnv(key: string, defaultValue?: string): string {
  const value = process.env[key] ?? defaultValue;
  if (value === undefined) throw new Error(`Missing required env var: ${key}`);
  return value;
}

// ── Retry ────────────────────────────────────────────────────────────────────

export async function retry<T>(
  fn: () => Promise<T>,
  attempts = 3,
  delayMs = 1000,
): Promise<T> {
  let lastError: Error | undefined;
  for (let i = 0; i < attempts; i++) {
    try {
      return await fn();
    } catch (err) {
      lastError = err as Error;
      if (i < attempts - 1) await new Promise(r => setTimeout(r, delayMs));
    }
  }
  throw lastError;
}

// ── Screenshot naming ────────────────────────────────────────────────────────

export function screenshotName(testTitle: string): string {
  return testTitle.replace(/[^a-zA-Z0-9]/g, '_').replace(/_+/g, '_') + '_' + Date.now();
}
"""
    return {"filename": "utils/helpers.ts", "content": content.strip()}
