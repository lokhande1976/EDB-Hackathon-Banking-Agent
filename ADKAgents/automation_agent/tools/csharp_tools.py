"""Tools that generate C# + Playwright / Selenium automation project files."""

from __future__ import annotations


def generate_csharp_csproj(
    project_name: str,
    artifact_id: str,
    framework: str = "playwright",
) -> dict:
    """Generate a .NET .csproj file for C# automation."""
    framework_pkg = (
        '<PackageReference Include="Microsoft.Playwright.NUnit" Version="1.44.0" />'
        if framework == "playwright"
        else """<PackageReference Include="Selenium.WebDriver" Version="4.21.0" />
    <PackageReference Include="Selenium.Support" Version="4.21.0" />
    <PackageReference Include="WebDriverManager" Version="2.17.4" />
    <PackageReference Include="NUnit.Selenium.PageObjectModel" Version="1.0.0" />"""
    )
    content = f"""<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <LangVersion>12</LangVersion>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <IsPackable>false</IsPackable>
    <IsTestProject>true</IsTestProject>
    <AssemblyName>{artifact_id}</AssemblyName>
    <RootNamespace>{project_name.replace(" ", "").replace("-", "")}.Automation</RootNamespace>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="NUnit" Version="4.1.0" />
    <PackageReference Include="NUnit3TestAdapter" Version="4.5.0" />
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.9.0" />
    {framework_pkg}
    <PackageReference Include="Allure.NUnit" Version="2.12.1" />
    <PackageReference Include="Allure.Net.Commons" Version="2.12.1" />
    <PackageReference Include="Bogus" Version="35.6.0" />
    <PackageReference Include="DotNetEnv" Version="3.1.0" />
    <PackageReference Include="ClosedXML" Version="0.102.2" />
    <PackageReference Include="Microsoft.Extensions.Configuration" Version="8.0.0" />
    <PackageReference Include="Microsoft.Extensions.Configuration.Json" Version="8.0.0" />
    <PackageReference Include="Serilog" Version="4.0.0" />
    <PackageReference Include="Serilog.Sinks.Console" Version="6.0.0" />
    <PackageReference Include="Serilog.Sinks.File" Version="6.0.0" />
  </ItemGroup>

  <ItemGroup>
    <None Update="appsettings.json">
      <CopyToOutputDirectory>Always</CopyToOutputDirectory>
    </None>
  </ItemGroup>

</Project>
"""
    return {"filename": f"{artifact_id}.csproj", "content": content.strip()}


def generate_csharp_appsettings(app_url: str, browser: str = "chromium") -> dict:
    """Generate appsettings.json."""
    content = f"""{{
  "Application": {{
    "BaseUrl": "{app_url}",
    "Environment": "qa"
  }},
  "Browser": {{
    "Name": "{browser}",
    "Headless": true,
    "SlowMo": 0,
    "Timeout": 30000,
    "ViewportWidth": 1920,
    "ViewportHeight": 1080
  }},
  "Allure": {{
    "ResultsDirectory": "allure-results"
  }}
}}
"""
    return {"filename": "appsettings.json", "content": content.strip()}


def generate_csharp_base_page(namespace: str, framework: str = "playwright") -> dict:
    """Generate Pages/BasePage.cs."""
    if framework == "playwright":
        content = f"""using Microsoft.Playwright;
using Allure.Net.Commons;
using Serilog;

namespace {namespace}.Pages;

/// <summary>
/// BasePage — parent for all Page Object classes.
/// Wraps Playwright IPage with common actions and Allure step logging.
/// </summary>
public abstract class BasePage
{{
    protected readonly IPage Page;

    protected BasePage(IPage page)
    {{
        Page = page;
    }}

    // ── Navigation ─────────────────────────────────────────────────────────────

    public async Task NavigateAsync(string url)
    {{
        Log.Information("Navigating to: {{Url}}", url);
        await Page.GotoAsync(url);
        await Page.WaitForLoadStateAsync();
    }}

    public string GetUrl() => Page.Url;
    public async Task<string> GetTitleAsync() => await Page.TitleAsync();

    // ── Click ──────────────────────────────────────────────────────────────────

    public async Task ClickAsync(string selector)
    {{
        Log.Debug("Clicking: {{Selector}}", selector);
        await Page.WaitForSelectorAsync(selector);
        await Page.ClickAsync(selector);
    }}

    public async Task DoubleClickAsync(string selector) =>
        await Page.DblClickAsync(selector);

    // ── Input ──────────────────────────────────────────────────────────────────

    public async Task FillAsync(string selector, string value)
    {{
        Log.Debug("Filling {{Selector}} with value", selector);
        await Page.Locator(selector).ClearAsync();
        await Page.FillAsync(selector, value);
    }}

    public async Task SelectOptionAsync(string selector, string value) =>
        await Page.SelectOptionAsync(selector, value);

    public async Task CheckAsync(string selector) =>
        await Page.CheckAsync(selector);

    public async Task UploadFileAsync(string selector, string filePath) =>
        await Page.SetInputFilesAsync(selector, filePath);

    // ── Read ───────────────────────────────────────────────────────────────────

    public async Task<string> GetTextAsync(string selector) =>
        await Page.TextContentAsync(selector) ?? string.Empty;

    public async Task<string> GetInputValueAsync(string selector) =>
        await Page.InputValueAsync(selector);

    public async Task<string?> GetAttributeAsync(string selector, string attribute) =>
        await Page.GetAttributeAsync(selector, attribute);

    // ── Visibility ─────────────────────────────────────────────────────────────

    public async Task<bool> IsVisibleAsync(string selector) =>
        await Page.IsVisibleAsync(selector);

    public async Task<bool> IsEnabledAsync(string selector) =>
        await Page.IsEnabledAsync(selector);

    // ── Waits ──────────────────────────────────────────────────────────────────

    public async Task WaitForVisibleAsync(string selector, float? timeout = null) =>
        await Page.WaitForSelectorAsync(selector, new() {{ State = WaitForSelectorState.Visible, Timeout = timeout }});

    public async Task WaitForUrlAsync(string urlPattern) =>
        await Page.WaitForURLAsync(urlPattern);

    public async Task WaitForPageLoadAsync() =>
        await Page.WaitForLoadStateAsync(LoadState.NetworkIdle);

    // ── Screenshot ─────────────────────────────────────────────────────────────

    public async Task<byte[]> TakeScreenshotAsync(string name)
    {{
        var bytes = await Page.ScreenshotAsync(new() {{ FullPage = true }});
        AllureApi.AddAttachment(name, "image/png", bytes, ".png");
        return bytes;
    }}
}}
"""
    else:
        content = f"""using OpenQA.Selenium;
using OpenQA.Selenium.Support.UI;
using Allure.Net.Commons;

namespace {namespace}.Pages;

/// <summary>BasePage — parent for all Page Object classes (Selenium).</summary>
public abstract class BasePage
{{
    protected readonly IWebDriver Driver;
    protected readonly WebDriverWait Wait;

    protected BasePage(IWebDriver driver, int timeoutSeconds = 30)
    {{
        Driver = driver;
        Wait   = new WebDriverWait(driver, TimeSpan.FromSeconds(timeoutSeconds));
    }}

    public void Navigate(string url) => Driver.Navigate().GoToUrl(url);
    public string GetUrl()           => Driver.Url;
    public string GetTitle()         => Driver.Title;

    protected IWebElement Find(By locator)           => Wait.Until(d => d.FindElement(locator));
    protected IWebElement FindVisible(By locator)     => Wait.Until(ExpectedConditions.ElementIsVisible(locator));
    protected IWebElement FindClickable(By locator)   => Wait.Until(ExpectedConditions.ElementToBeClickable(locator));

    public void Click(By locator)                    => FindClickable(locator).Click();
    public void Fill(By locator, string value)       {{ Find(locator).Clear(); Find(locator).SendKeys(value); }}
    public string GetText(By locator)                => FindVisible(locator).Text;
    public bool IsVisible(By locator)                => Driver.FindElements(locator).Count > 0 && Driver.FindElement(locator).Displayed;

    public byte[] TakeScreenshot(string name)
    {{
        var bytes = ((ITakesScreenshot)Driver).GetScreenshot().AsByteArray;
        AllureApi.AddAttachment(name, "image/png", bytes, ".png");
        return bytes;
    }}
}}
"""
    return {"filename": "Pages/BasePage.cs", "content": content.strip()}


def generate_csharp_base_test(namespace: str, framework: str = "playwright") -> dict:
    """Generate Tests/BaseTest.cs."""
    if framework == "playwright":
        content = f"""using Microsoft.Playwright;
using Microsoft.Playwright.NUnit;
using Microsoft.Extensions.Configuration;
using NUnit.Framework;
using Serilog;

namespace {namespace}.Tests;

/// <summary>
/// BaseTest — all test classes inherit from this.
/// Manages Playwright browser/context/page lifecycle.
/// </summary>
[TestFixture]
public class BaseTest : PageTest
{{
    protected IConfiguration Config {{ get; private set; }} = null!;

    [OneTimeSetUp]
    public void GlobalSetUp()
    {{
        Log.Logger = new LoggerConfiguration()
            .WriteTo.Console()
            .WriteTo.File("test-results/logs/automation.log", rollingInterval: RollingInterval.Day)
            .CreateLogger();

        Config = new ConfigurationBuilder()
            .SetBasePath(AppContext.BaseDirectory)
            .AddJsonFile("appsettings.json", optional: false)
            .AddEnvironmentVariables()
            .Build();
    }}

    public override BrowserNewContextOptions ContextOptions()
    {{
        return new BrowserNewContextOptions
        {{
            ViewportSize = new ViewportSize
            {{
                Width  = Config.GetValue<int>("Browser:ViewportWidth",  1920),
                Height = Config.GetValue<int>("Browser:ViewportHeight", 1080),
            }},
            BaseURL             = Config["Application:BaseUrl"],
            RecordVideoDir      = Environment.GetEnvironmentVariable("RECORD_VIDEO") == "true"
                                  ? "test-results/videos" : null,
            IgnoreHTTPSErrors   = true,
        }};
    }}

    [TearDown]
    public async Task OnTestTearDown()
    {{
        if (TestContext.CurrentContext.Result.Outcome.Status == NUnit.Framework.Interfaces.TestStatus.Failed)
        {{
            await Page.ScreenshotAsync(new() {{ FullPage = true, Path = $"test-results/screenshots/{{TestContext.CurrentContext.Test.Name}}.png" }});
        }}
    }}

    [OneTimeTearDown]
    public void GlobalTearDown() => Log.CloseAndFlush();
}}
"""
    else:
        content = f"""using OpenQA.Selenium;
using OpenQA.Selenium.Chrome;
using OpenQA.Selenium.Firefox;
using WebDriverManager;
using WebDriverManager.DriverConfigs.Impl;
using NUnit.Framework;
using Serilog;

namespace {namespace}.Tests;

[TestFixture]
public class BaseTest
{{
    protected IWebDriver Driver {{ get; private set; }} = null!;

    [SetUp]
    public void SetUp()
    {{
        var browser  = Environment.GetEnvironmentVariable("BROWSER") ?? "chrome";
        var headless = Environment.GetEnvironmentVariable("HEADLESS") != "false";

        Driver = browser.ToLower() switch
        {{
            "firefox" => CreateFirefox(headless),
            _         => CreateChrome(headless),
        }};
        Driver.Manage().Timeouts().ImplicitWait = TimeSpan.FromSeconds(10);
        Driver.Manage().Window.Maximize();
        Driver.Navigate().GoToUrl(Environment.GetEnvironmentVariable("BASE_URL") ?? "");
    }}

    [TearDown]
    public void TearDown()
    {{
        if (TestContext.CurrentContext.Result.Outcome.Status == NUnit.Framework.Interfaces.TestStatus.Failed)
        {{
            var ss = ((ITakesScreenshot)Driver).GetScreenshot();
            ss.SaveAsFile($"test-results/screenshots/{{TestContext.CurrentContext.Test.Name}}.png");
        }}
        Driver?.Quit();
    }}

    private static IWebDriver CreateChrome(bool headless)
    {{
        new DriverManager().SetUpDriver(new ChromeConfig());
        var opts = new ChromeOptions();
        if (headless) opts.AddArgument("--headless=new");
        opts.AddArguments("--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080");
        return new ChromeDriver(opts);
    }}

    private static IWebDriver CreateFirefox(bool headless)
    {{
        new DriverManager().SetUpDriver(new FirefoxConfig());
        var opts = new FirefoxOptions();
        if (headless) opts.AddArgument("--headless");
        return new FirefoxDriver(opts);
    }}
}}
"""
    return {"filename": "Tests/BaseTest.cs", "content": content.strip()}


def generate_csharp_page_object(
    page_name: str,
    namespace: str,
    url: str,
    elements_description: str,
    framework: str = "playwright",
) -> dict:
    """Generate a C# Page Object class."""
    class_name = "".join(w.capitalize() for w in page_name.split()) + "Page"
    using = "using Microsoft.Playwright;" if framework == "playwright" else "using OpenQA.Selenium;"
    content = f"""{using}

namespace {namespace}.Pages;

/// <summary>
/// {class_name} — Page Object for: {url}
/// Elements: {elements_description}
/// </summary>
public class {class_name}({("IPage page" if framework == "playwright" else "IWebDriver driver")}) : BasePage({("page" if framework == "playwright" else "driver")})
{{
    private const string Url = "{url}";

    // ── Selectors ─────────────────────────────────────────────────────────────
    // TODO: replace with your actual selectors
    // private const string SubmitButton = "[data-testid='submit']";
    // private const string ErrorMessage = "[data-testid='error']";

    public async Task OpenAsync()
    {{
        await NavigateAsync(Url);
    }}

    public async Task<bool> IsLoadedAsync() =>
        GetUrl().Contains(Url);

    // ── Actions ────────────────────────────────────────────────────────────────
    // public async Task ClickSubmitAsync() => await ClickAsync(SubmitButton);
}}
"""
    return {"filename": f"Pages/{class_name}.cs", "content": content.strip()}


def generate_csharp_test(
    test_name: str,
    page_name: str,
    namespace: str,
    test_scenarios: str,
    framework: str = "playwright",
) -> dict:
    """Generate a C# NUnit test class."""
    class_name = "".join(w.capitalize() for w in page_name.split()) + "Page"
    test_class = "".join(w.capitalize() for w in test_name.split()) + "Tests"
    scenarios  = [s.strip() for s in test_scenarios.split(",") if s.strip()]
    if not scenarios:
        scenarios = ["Verify page loads", "Verify positive flow", "Verify error handling"]

    methods = []
    for s in scenarios:
        method = "".join(w.capitalize() for w in s.split())
        method = "".join(c for c in method if c.isalnum())
        methods.append(f"""
    [Test]
    [Description("{s}")]
    public async Task {method}()
    {{
        // Arrange
        var page = new {class_name}(Page);

        // Act
        await page.OpenAsync();

        // Assert
        Assert.That(await page.IsLoadedAsync(), Is.True, "Page should be loaded");
    }}""")

    methods_str = "\n".join(methods)
    content = f"""using NUnit.Framework;
using Allure.Net.Commons;
using {namespace}.Pages;

namespace {namespace}.Tests;

[TestFixture]
[AllureEpic("Automation Framework Generator")]
[AllureFeature("{page_name}")]
public class {test_class} : BaseTest
{{
{methods_str}
}}
"""
    return {"filename": f"Tests/{test_class}.cs", "content": content.strip()}
