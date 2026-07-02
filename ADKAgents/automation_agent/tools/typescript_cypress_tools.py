"""Tools that generate TypeScript + Cypress project files."""

from __future__ import annotations


def generate_cypress_package_json(project_name: str, artifact_id: str) -> dict:
    """Generate package.json for TypeScript + Cypress."""
    content = f"""{{
  "name": "{artifact_id}",
  "version": "1.0.0",
  "description": "{project_name} — Cypress TypeScript Automation Framework",
  "scripts": {{
    "cy:open": "cypress open",
    "cy:run": "cypress run",
    "cy:run:chrome": "cypress run --browser chrome",
    "cy:run:firefox": "cypress run --browser firefox",
    "cy:run:edge": "cypress run --browser edge",
    "cy:run:headed": "cypress run --headed",
    "cy:run:record": "cypress run --record",
    "report:merge": "mochawesome-merge cypress/reports/*.json > cypress/reports/merged-report.json",
    "report:generate": "marge cypress/reports/merged-report.json --reportDir cypress/reports/html",
    "lint": "eslint . --ext .ts,.tsx"
  }},
  "devDependencies": {{
    "cypress": "^13.12.0",
    "typescript": "^5.4.5",
    "@types/node": "^20.14.0",
    "@cypress/xpath": "^2.0.3",
    "cypress-allure-plugin": "^2.40.2",
    "cypress-mochawesome-reporter": "^3.8.2",
    "mochawesome": "^7.1.3",
    "mochawesome-merge": "^4.3.0",
    "mochawesome-report-generator": "^6.2.0",
    "@faker-js/faker": "^8.4.1",
    "eslint": "^9.5.0",
    "@typescript-eslint/eslint-plugin": "^7.13.0",
    "@typescript-eslint/parser": "^7.13.0",
    "dotenv": "^16.4.5"
  }}
}}
"""
    return {"filename": "package.json", "content": content.strip()}


def generate_cypress_config(project_name: str, app_url: str) -> dict:
    """Generate cypress.config.ts."""
    content = f"""import {{ defineConfig }} from 'cypress';
import * as dotenv from 'dotenv';

dotenv.config();

/**
 * Cypress configuration for {project_name}.
 */
export default defineConfig({{
  e2e: {{
    baseUrl: process.env.BASE_URL || '{app_url}',
    specPattern: 'cypress/e2e/**/*.cy.{{js,jsx,ts,tsx}}',
    supportFile: 'cypress/support/e2e.ts',
    fixturesFolder: 'cypress/fixtures',
    downloadsFolder: 'cypress/downloads',
    screenshotsFolder: 'cypress/screenshots',
    videosFolder: 'cypress/videos',

    // Retry failed tests
    retries: {{
      runMode: 2,
      openMode: 0,
    }},

    // Timeouts
    defaultCommandTimeout: 10_000,
    requestTimeout: 15_000,
    responseTimeout: 30_000,
    pageLoadTimeout: 30_000,

    // Viewport
    viewportWidth: 1920,
    viewportHeight: 1080,

    // Video
    video: true,
    videoCompression: 32,

    // Reporter
    reporter: 'cypress-mochawesome-reporter',
    reporterOptions: {{
      charts: true,
      reportPageTitle: '{project_name} Test Report',
      embeddedScreenshots: true,
      inlineAssets: true,
      saveAllAttempts: false,
    }},

    setupNodeEvents(on, config) {{
      require('cypress-mochawesome-reporter/plugin')(on);
      // require('@cypress/xpath/plugin')(on, config); // Enable XPath support
      return config;
    }},

    env: {{
      // Pass environment variables here or via cypress.env.json (gitignored)
      environment: process.env.TEST_ENV || 'qa',
    }},
  }},
}});
"""
    return {"filename": "cypress.config.ts", "content": content.strip()}


def generate_cypress_support_commands() -> dict:
    """Generate cypress/support/commands.ts — custom Cypress commands."""
    content = """/// <reference types="cypress" />

/**
 * Custom Cypress commands.
 * Add commands here and declare their types in cypress/support/index.d.ts.
 */

// ── Login command ────────────────────────────────────────────────────────────
Cypress.Commands.add('login', (email: string, password: string) => {
  cy.session([email, password], () => {
    cy.visit('/login');
    cy.get('[data-testid="email"]').type(email);
    cy.get('[data-testid="password"]').type(password);
    cy.get('[data-testid="submit"]').click();
    cy.url().should('not.include', '/login');
  });
});

// ── API login (faster than UI) ───────────────────────────────────────────────
Cypress.Commands.add('loginViaApi', (email: string, password: string) => {
  cy.request({
    method: 'POST',
    url: '/api/auth/login',
    body: { email, password },
  }).then((response) => {
    window.localStorage.setItem('authToken', response.body.token);
  });
});

// ── Drag and drop ────────────────────────────────────────────────────────────
Cypress.Commands.add('dragTo', { prevSubject: 'element' }, (subject, targetSelector) => {
  cy.wrap(subject).trigger('mousedown', { button: 0 });
  cy.get(targetSelector).trigger('mousemove').trigger('mouseup', { force: true });
});

// ── Wait for API ─────────────────────────────────────────────────────────────
Cypress.Commands.add('waitForApi', (alias: string) => {
  cy.intercept('GET', `**/api/**`).as(alias);
  cy.wait(`@${alias}`);
});

// ── Type declarations ────────────────────────────────────────────────────────
declare global {
  namespace Cypress {
    interface Chainable {
      login(email: string, password: string): Chainable<void>;
      loginViaApi(email: string, password: string): Chainable<void>;
      dragTo(targetSelector: string): Chainable<void>;
      waitForApi(alias: string): Chainable<void>;
    }
  }
}
"""
    return {"filename": "cypress/support/commands.ts", "content": content.strip()}


def generate_cypress_support_e2e() -> dict:
    """Generate cypress/support/e2e.ts — global setup."""
    content = """// Import commands
import './commands';

// Import reporter plugin
import 'cypress-mochawesome-reporter/register';

// ── Global hooks ──────────────────────────────────────────────────────────────

beforeEach(function () {
  // Log test name to Cypress output
  cy.log(`Starting: ${this.currentTest?.title}`);
});

afterEach(function () {
  // Take screenshot on failure (Cypress does this automatically, but you can add extras)
  if (this.currentTest?.state === 'failed') {
    const name = this.currentTest.title.replace(/[^a-zA-Z0-9]/g, '_');
    cy.screenshot(name, { capture: 'fullPage' });
  }
});

// ── Uncaught exception handling ───────────────────────────────────────────────
// Uncomment to ignore specific app errors that don't affect test outcome:
// Cypress.on('uncaught:exception', (err) => {
//   if (err.message.includes('ResizeObserver loop')) return false;
//   return true;
// });
"""
    return {"filename": "cypress/support/e2e.ts", "content": content.strip()}


def generate_cypress_page_object(page_name: str, url: str, elements_description: str) -> dict:
    """Generate a Cypress Page Object class (TypeScript)."""
    class_name = page_name.strip().replace(" ", "") + "Page"
    content = f"""/**
 * {class_name} — Page Object for: {url}
 *
 * Elements:
 * {elements_description}
 */
export class {class_name} {{
  // ── Selectors ─────────────────────────────────────────────────────────────
  // Use data-testid attributes for stability. Avoid brittle XPath.

  private readonly url = '{url}';
  // private readonly usernameInput = '[data-testid="username"]';
  // private readonly passwordInput = '[data-testid="password"]';
  // private readonly submitButton  = '[data-testid="submit"]';
  // private readonly errorMessage  = '[data-testid="error-msg"]';

  // ── Navigation ─────────────────────────────────────────────────────────────

  open(): this {{
    cy.visit(this.url);
    return this;
  }}

  // ── Actions ────────────────────────────────────────────────────────────────

  // enterUsername(username: string): this {{
  //   cy.get(this.usernameInput).clear().type(username);
  //   return this;
  // }}

  // clickSubmit(): this {{
  //   cy.get(this.submitButton).click();
  //   return this;
  // }}

  // ── Assertions ─────────────────────────────────────────────────────────────

  // expectErrorMessage(text: string): this {{
  //   cy.get(this.errorMessage).should('contain.text', text);
  //   return this;
  // }}

  isLoaded(): this {{
    cy.url().should('include', '{url}');
    return this;
  }}
}}
"""
    return {
        "filename": f"cypress/pages/{class_name}.ts",
        "content": content.strip(),
    }


def generate_cypress_test(test_name: str, page_name: str, test_scenarios: str) -> dict:
    """Generate a Cypress spec file."""
    class_name = page_name.strip().replace(" ", "") + "Page"
    file_name = test_name.lower().replace(" ", "-")
    scenarios = [s.strip() for s in test_scenarios.split(",") if s.strip()]
    if not scenarios:
        scenarios = ["verify page loads", "verify positive flow", "verify error handling"]

    it_blocks = []
    for s in scenarios:
        it_blocks.append(f"""
    it('{s}', () => {{
      // TODO: implement — {s}
      {page_name.lower()}Page.isLoaded();
    }});""")

    tests_str = "\n".join(it_blocks)
    content = f"""import {{ {class_name} }} from '../pages/{class_name}';

/**
 * {test_name} — Cypress test suite.
 * Scenarios: {test_scenarios}
 */
describe('{test_name}', () => {{
  const {page_name.lower()}Page = new {class_name}();

  beforeEach(() => {{
    {page_name.lower()}Page.open();
  }});
{tests_str}
}});
"""
    return {
        "filename": f"cypress/e2e/{file_name}.cy.ts",
        "content": content.strip(),
    }
