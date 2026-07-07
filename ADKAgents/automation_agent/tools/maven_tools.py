"""Tools that generate Maven project skeleton files."""

from __future__ import annotations


def generate_pom_xml(
    project_name: str,
    group_id: str,
    artifact_id: str,
    version: str = "1.0-SNAPSHOT",
) -> dict:
    """Generate a production-ready Maven pom.xml with Playwright Java, TestNG, and Allure.

    Args:
        project_name: Human-readable project name.
        group_id: Maven group id (e.g. com.acme).
        artifact_id: Maven artifact id (e.g. acme-automation).
        version: Project version string.

    Returns:
        dict with keys 'filename' and 'content'.
    """
    package_name = group_id.replace("-", "").replace("_", "")
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>{group_id}</groupId>
    <artifactId>{artifact_id}</artifactId>
    <version>{version}</version>
    <packaging>jar</packaging>

    <name>{project_name} - Playwright Automation Framework</name>
    <description>End-to-end automation framework using Playwright Java + TestNG + Allure</description>

    <properties>
        <java.version>17</java.version>
        <maven.compiler.source>17</maven.compiler.source>
        <maven.compiler.target>17</maven.compiler.target>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>

        <!-- Dependency Versions -->
        <playwright.version>1.44.0</playwright.version>
        <testng.version>7.10.0</testng.version>
        <allure.version>2.27.0</allure.version>
        <log4j.version>2.23.1</log4j.version>
        <jackson.version>2.17.1</jackson.version>
        <poi.version>5.2.5</poi.version>
        <lombok.version>1.18.32</lombok.version>
        <assertj.version>3.26.0</assertj.version>
        <faker.version>1.0.2</faker.version>
        <aspectj.version>1.9.22</aspectj.version>
    </properties>

    <dependencies>
        <!-- Playwright Java -->
        <dependency>
            <groupId>com.microsoft.playwright</groupId>
            <artifactId>playwright</artifactId>
            <version>${{playwright.version}}</version>
        </dependency>

        <!-- TestNG -->
        <dependency>
            <groupId>org.testng</groupId>
            <artifactId>testng</artifactId>
            <version>${{testng.version}}</version>
        </dependency>

        <!-- Allure TestNG -->
        <dependency>
            <groupId>io.qameta.allure</groupId>
            <artifactId>allure-testng</artifactId>
            <version>${{allure.version}}</version>
        </dependency>

        <!-- Allure Attachments -->
        <dependency>
            <groupId>io.qameta.allure</groupId>
            <artifactId>allure-attachments</artifactId>
            <version>${{allure.version}}</version>
        </dependency>

        <!-- Log4j2 -->
        <dependency>
            <groupId>org.apache.logging.log4j</groupId>
            <artifactId>log4j-api</artifactId>
            <version>${{log4j.version}}</version>
        </dependency>
        <dependency>
            <groupId>org.apache.logging.log4j</groupId>
            <artifactId>log4j-core</artifactId>
            <version>${{log4j.version}}</version>
        </dependency>
        <dependency>
            <groupId>org.apache.logging.log4j</groupId>
            <artifactId>log4j-slf4j2-impl</artifactId>
            <version>${{log4j.version}}</version>
        </dependency>

        <!-- Jackson (JSON data) -->
        <dependency>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
            <version>${{jackson.version}}</version>
        </dependency>

        <!-- Apache POI (Excel data) -->
        <dependency>
            <groupId>org.apache.poi</groupId>
            <artifactId>poi-ooxml</artifactId>
            <version>${{poi.version}}</version>
        </dependency>

        <!-- Lombok -->
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <version>${{lombok.version}}</version>
            <scope>provided</scope>
        </dependency>

        <!-- AssertJ -->
        <dependency>
            <groupId>org.assertj</groupId>
            <artifactId>assertj-core</artifactId>
            <version>${{assertj.version}}</version>
        </dependency>

        <!-- Java Faker (test data) -->
        <dependency>
            <groupId>com.github.javafaker</groupId>
            <artifactId>javafaker</artifactId>
            <version>${{faker.version}}</version>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <!-- Maven Compiler -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.13.0</version>
                <configuration>
                    <source>17</source>
                    <target>17</target>
                    <annotationProcessorPaths>
                        <path>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                            <version>${{lombok.version}}</version>
                        </path>
                    </annotationProcessorPaths>
                </configuration>
            </plugin>

            <!-- Maven Surefire (TestNG runner) -->
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-surefire-plugin</artifactId>
                <version>3.2.5</version>
                <configuration>
                    <suiteXmlFiles>
                        <suiteXmlFile>testng.xml</suiteXmlFile>
                    </suiteXmlFiles>
                    <argLine>
                        -javaagent:"${{settings.localRepository}}/org/aspectj/aspectjweaver/${{aspectj.version}}/aspectjweaver-${{aspectj.version}}.jar"
                        --add-opens java.base/java.lang=ALL-UNNAMED
                    </argLine>
                    <systemPropertyVariables>
                        <allure.results.directory>${{project.build.directory}}/allure-results</allure.results.directory>
                    </systemPropertyVariables>
                </configuration>
                <dependencies>
                    <dependency>
                        <groupId>org.aspectj</groupId>
                        <artifactId>aspectjweaver</artifactId>
                        <version>${{aspectj.version}}</version>
                    </dependency>
                </dependencies>
            </plugin>

            <!-- Allure Maven Plugin -->
            <plugin>
                <groupId>io.qameta.allure</groupId>
                <artifactId>allure-maven</artifactId>
                <version>2.12.0</version>
                <configuration>
                    <reportVersion>${{allure.version}}</reportVersion>
                    <resultsDirectory>${{project.build.directory}}/allure-results</resultsDirectory>
                </configuration>
            </plugin>
        </plugins>
    </build>

    <reporting>
        <plugins>
            <plugin>
                <groupId>io.qameta.allure</groupId>
                <artifactId>allure-maven</artifactId>
                <version>2.12.0</version>
            </plugin>
        </plugins>
    </reporting>
</project>
"""
    return {"filename": "pom.xml", "content": content.strip()}


def generate_testng_xml(
    suite_name: str,
    test_classes: list[str],
    package_name: str,
    parallel: str = "methods",
    thread_count: int = 4,
) -> dict:
    """Generate a TestNG suite XML file.

    Args:
        suite_name: Name for the test suite.
        test_classes: List of fully-qualified test class names.
        package_name: Base package for the tests.
        parallel: Parallelism mode — 'methods', 'classes', 'tests', or 'none'.
        thread_count: Number of parallel threads.

    Returns:
        dict with keys 'filename' and 'content'.
    """
    classes_xml = "\n".join(
        f'            <class name="{pkg}.tests.{cls}"/>'
        for cls in test_classes
        for pkg in [package_name]
    )

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE suite SYSTEM "http://testng.org/testng-1.0.dtd">
<suite name="{suite_name}" verbose="1" parallel="{parallel}" thread-count="{thread_count}">

    <listeners>
        <listener class-name="io.qameta.allure.testng.AllureTestNg"/>
    </listeners>

    <test name="{suite_name} Tests">
        <classes>
{classes_xml}
        </classes>
    </test>

</suite>
"""
    return {"filename": "testng.xml", "content": content.strip()}


def generate_folder_manifest(project_name: str, package_path: str) -> dict:
    """Return a textual listing of the full Maven project folder structure.

    Args:
        project_name: Root folder name for the project.
        package_path: Java package path (e.g. com/acme/automation).

    Returns:
        dict with 'filename' (README section) and 'content' (folder tree string).
    """
    tree = f"""
{project_name}/
├── pom.xml
├── testng.xml
├── Dockerfile
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── {package_path}/
│   │   │       ├── pages/
│   │   │       │   ├── BasePage.java
│   │   │       │   └── [YourPage].java
│   │   │       ├── utils/
│   │   │       │   ├── ConfigReader.java
│   │   │       │   ├── WaitHelper.java
│   │   │       │   ├── ScreenshotUtil.java
│   │   │       │   └── ExcelReader.java
│   │   │       └── constants/
│   │   │           └── FrameworkConstants.java
│   │   └── resources/
│   │       ├── config.properties
│   │       └── log4j2.xml
│   └── test/
│       ├── java/
│       │   └── {package_path}/
│       │       ├── base/
│       │       │   └── BaseTest.java
│       │       └── tests/
│       │           └── [YourTest].java
│       └── resources/
│           ├── testdata/
│           │   └── testdata.xlsx
│           └── allure.properties
└── README.md
""".strip()

    return {"filename": "folder_structure.txt", "content": tree}
