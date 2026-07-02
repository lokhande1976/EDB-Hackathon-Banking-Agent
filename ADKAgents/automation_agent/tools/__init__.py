# Java tools
from .maven_tools import generate_pom_xml, generate_testng_xml, generate_folder_manifest
from .java_tools import generate_base_page, generate_base_test, generate_page_object, generate_test_class, generate_constants
from .utility_tools import (
    generate_config_reader, generate_wait_helper, generate_screenshot_util,
    generate_excel_reader, generate_config_properties, generate_log4j2_config,
    generate_allure_properties,
)

# TypeScript / JavaScript tools
from .typescript_playwright_tools import (
    generate_ts_playwright_package_json, generate_ts_playwright_config,
    generate_ts_playwright_tsconfig, generate_ts_playwright_base_page,
    generate_ts_playwright_fixtures, generate_ts_playwright_page_object,
    generate_ts_playwright_test, generate_ts_playwright_env,
    generate_ts_playwright_utils,
)
from .typescript_cypress_tools import (
    generate_cypress_package_json, generate_cypress_config,
    generate_cypress_support_commands, generate_cypress_support_e2e,
    generate_cypress_page_object, generate_cypress_test,
)

# Python tools
from .python_tools import (
    generate_python_pyproject_toml, generate_python_conftest,
    generate_python_base_page, generate_python_page_object, generate_python_test,
)

# C# tools
from .csharp_tools import (
    generate_csharp_csproj, generate_csharp_appsettings,
    generate_csharp_base_page, generate_csharp_base_test,
    generate_csharp_page_object, generate_csharp_test,
)

# CI/CD (shared)
from .cicd_tools import generate_github_actions, generate_dockerfile, generate_docker_compose, generate_readme

__all__ = [
    # Java
    "generate_pom_xml", "generate_testng_xml", "generate_folder_manifest",
    "generate_base_page", "generate_base_test", "generate_page_object",
    "generate_test_class", "generate_constants",
    "generate_config_reader", "generate_wait_helper", "generate_screenshot_util",
    "generate_excel_reader", "generate_config_properties", "generate_log4j2_config",
    "generate_allure_properties",
    # TypeScript Playwright
    "generate_ts_playwright_package_json", "generate_ts_playwright_config",
    "generate_ts_playwright_tsconfig", "generate_ts_playwright_base_page",
    "generate_ts_playwright_fixtures", "generate_ts_playwright_page_object",
    "generate_ts_playwright_test", "generate_ts_playwright_env",
    "generate_ts_playwright_utils",
    # TypeScript Cypress
    "generate_cypress_package_json", "generate_cypress_config",
    "generate_cypress_support_commands", "generate_cypress_support_e2e",
    "generate_cypress_page_object", "generate_cypress_test",
    # Python
    "generate_python_pyproject_toml", "generate_python_conftest",
    "generate_python_base_page", "generate_python_page_object", "generate_python_test",
    # C#
    "generate_csharp_csproj", "generate_csharp_appsettings",
    "generate_csharp_base_page", "generate_csharp_base_test",
    "generate_csharp_page_object", "generate_csharp_test",
    # CI/CD
    "generate_github_actions", "generate_dockerfile", "generate_docker_compose", "generate_readme",
]
