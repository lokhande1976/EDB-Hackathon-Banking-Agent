"""Sub-agent: CI/CD, Docker, and README files."""

from google.adk.agents import Agent
from ..tools import generate_github_actions, generate_dockerfile, generate_docker_compose, generate_readme

INSTRUCTION = """You are a DevOps and CI/CD specialist for Java test automation.

When given project requirements, call ALL of these tools:
1. generate_github_actions  — .github/workflows/ci.yml (full pipeline: cache, install Playwright, run tests, upload Allure, deploy to GitHub Pages)
2. generate_dockerfile      — multi-stage Dockerfile
3. generate_docker_compose  — docker-compose.yml with test-runner + Allure server
4. generate_readme          — comprehensive README.md (badges, quick-start, Docker, CI/CD, config reference)

Always call all 4 tools.
Return ONLY the raw tool outputs — do not add commentary.
"""

cicd_agent = Agent(
    name="cicd_agent",
    model="gemini-2.0-flash",
    description=(
        "Generates all CI/CD and infrastructure files: GitHub Actions workflow with Allure report "
        "publishing to GitHub Pages, multi-stage Dockerfile, docker-compose.yml with Allure server, "
        "and a comprehensive README with quick-start guide and configuration reference."
    ),
    instruction=INSTRUCTION,
    tools=[generate_github_actions, generate_dockerfile, generate_docker_compose, generate_readme],
)
