# Python Test Automation Starter Framework

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![pytest](https://img.shields.io/badge/testing-pytest-green)](https://pytest.org/)
[![Playwright](https://img.shields.io/badge/automation-Playwright-45ba4b)](https://playwright.dev/)

An enterprise-ready Python test automation framework combining modern testing practices with LLM-assisted development capabilities. This framework provides a unified solution for UI testing (Playwright), API testing (httpx), and Behavior-Driven Development (Gherkin/pytest-bdd) with deterministic test execution through Model Context Protocol (MCP) integration.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage Examples](#usage-examples)
- [Development Workflow](#development-workflow)
- [CI/CD Integration](#cicd-integration)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [License](#license)

---

## 🎯 Overview

This test automation framework is designed for teams that need:

- **Business-Readable Test Scenarios**: Write tests in Gherkin that stakeholders can understand
- **Stable, Maintainable UI Tests**: Page Object Pattern with ARIA-based locators (no brittle CSS selectors)
- **Deterministic Test Execution**: MCP servers provide reliable test data seeding and state management
- **LLM-Assisted Test Generation**: AI helps discover edge cases and generate test scenarios
- **Production-Ready CI/CD**: GitHub Actions workflows with parallel execution and Allure reporting
- **Type-Safe API Testing**: httpx with Pydantic validation for robust API test coverage

### Core Philosophy

> **"Tests execute inside pytest (fast, reliable), while we run two MCP options alongside"**

- pytest + Playwright remains the primary test runner (not replaced by agents)
- MCP servers run as supporting services for data management and exploration
- LLM is a helper for discovery and generation, not the test execution engine

---

## ✨ Key Features

### 🧪 Unified pytest-Based Framework
- **pytest-bdd**: Native Gherkin support with Given/When/Then scenarios
- **Playwright**: Modern browser automation for UI testing (Chromium, Firefox, WebKit)
- **httpx**: Async/sync HTTP client for API testing with full async support
- **Parallel Execution**: pytest-xdist for concurrent test runs

### 📐 Page Object Pattern
- High-level, business-readable interaction methods
- Stable locators prioritizing ARIA roles, accessible names, and test-ids
- Avoids brittle CSS class names and complex XPath expressions
- Reusable component objects for common UI elements

### 🔌 MCP Server Integration

#### FastAPI MCP Server (Production/CI)
Provides deterministic test data management:
- `seed_user`: Create test users with specific roles and attributes
- `build_payload`: Generate valid request bodies for API testing
- `reset_env`: Clear test data and reset environment state
- `query_state`: Inspect current test environment for debugging

#### Playwright MCP Server (Development/Exploration)
Enables LLM-driven test discovery:
- `navigate`, `click`, `type`: LLM controls browser for exploration
- `screenshot`, `get_page_structure`: Capture application state
- `generate_gherkin`: Convert exploration sessions to Gherkin scenarios

### 🤖 LLM-Assisted Test Authoring
- **Local LLMs**: Ollama integration for cost-free development
- **Hosted LLMs**: OpenAI-compatible API support (OpenAI, Azure, Anthropic)
- **Scenario Generation**: AI drafts business-readable Gherkin from exploration
- **Edge Case Discovery**: LLM suggests test variations and boundary conditions
- **Human-in-the-Loop**: All generated scenarios require review before commit

### 📊 Allure Reporting
- Rich HTML test reports with history tracking
- Automatic screenshot and trace attachment on failures
- GitHub Pages integration for public report hosting
- Test execution metrics and trend analysis

### 🚀 Enterprise CI/CD
- GitHub Actions workflows with matrix testing
- Parallel execution across Python versions and browsers
- Isolated browser contexts (new context per test)
- Automated report generation and publishing

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions CI/CD                     │
│  (Matrix: Python 3.11/3.12 × Chromium/Firefox/WebKit)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   pytest Test Runner                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  pytest-bdd  │  │  Playwright  │  │    httpx     │      │
│  │   (Gherkin)  │  │  (UI Tests)  │  │ (API Tests)  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │               │
│         ▼                  ▼                  ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Step Definitions│ │ Page Objects │  │ API Clients  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                             ▼
          ┌──────────────────────────────────────┐
          │         MCP Client Helper            │
          └──────────┬─────────────┬─────────────┘
                     │             │
         ┌───────────▼──┐    ┌─────▼──────────┐
         │  FastAPI MCP │    │ Playwright MCP │
         │   Server     │    │    Server      │
         │  (Prod/CI)   │    │  (Dev Only)    │
         └──────┬───────┘    └────────┬───────┘
                │                     │
                ▼                     ▼
         ┌─────────────┐       ┌──────────┐
         │  Test Data  │       │   LLM    │
         │  Database   │       │ (Ollama/ │
         │  + State    │       │ OpenAI)  │
         └─────────────┘       └──────────┘
                                     │
                                     ▼
                              ┌──────────────┐
                              │  Generated   │
                              │  .feature    │
                              │   Files      │
                              └──────────────┘
```

### Component Interaction Flow

1. **Test Execution**: pytest discovers Gherkin features and Python tests
2. **Data Setup**: Tests call MCP client to seed users and build payloads
3. **UI Testing**: Step definitions use Page Objects with stable locators
4. **API Testing**: Typed API clients make httpx requests with MCP-generated payloads
5. **Exploration** (Dev): LLM controls browser via Playwright MCP server
6. **Generation** (Dev): LLM converts exploration to Gherkin scenarios for review
7. **Reporting**: Allure captures results and generates HTML reports

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (Python 3.11 or 3.12 recommended)
- **Git** for version control
- **Node.js** (optional, for Allure CLI)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd <repository-name>

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install Playwright browsers
python -m playwright install chromium

# Install pre-commit hooks
pre-commit install
```

### Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
# Minimum required variables:
BASE_URL=http://localhost:3000          # Web application URL
API_BASE_URL=http://localhost:3000/api  # API endpoint URL
HEADLESS=true                            # Run browsers headlessly
```

### Run Your First Test

```bash
# Run all BDD feature tests
pytest tests/features/authentication.feature

# Run with Allure reporting
pytest --alluredir=allure-results
allure serve allure-results
```

---

## 📁 Project Structure

```
.
├── README.md                          # This file
├── .gitignore                         # Git ignore patterns
├── .env.example                       # Environment variable template
├── pyproject.toml                     # Modern Python project config
├── requirements.txt                   # Pinned production dependencies
├── requirements-dev.txt               # Development dependencies
├── pytest.ini                         # pytest configuration
├── .python-version                    # Python version (3.9+)
├── LICENSE                            # MIT License
│
├── .github/
│   └── workflows/
│       ├── test.yml                   # Main test execution pipeline
│       ├── allure-report.yml          # Report generation and publishing
│       └── lint.yml                   # Code quality checks
│
├── tests/
│   ├── conftest.py                    # Shared pytest fixtures
│   │
│   ├── features/                      # Gherkin feature files
│   │   ├── authentication.feature
│   │   ├── user_management.feature
│   │   └── api_operations.feature
│   │
│   ├── step_definitions/              # pytest-bdd step implementations
│   │   ├── auth_steps.py
│   │   ├── user_steps.py
│   │   ├── api_steps.py
│   │   └── common_steps.py
│   │
│   ├── pages/                         # Page Object Pattern
│   │   ├── base_page.py
│   │   ├── login_page.py
│   │   ├── dashboard_page.py
│   │   └── components/
│   │       ├── navigation.py
│   │       └── modal.py
│   │
│   ├── api_clients/                   # Typed API clients
│   │   ├── base_client.py
│   │   ├── auth_client.py
│   │   ├── users_client.py
│   │   └── models/
│   │       ├── auth_models.py
│   │       └── user_models.py
│   │
│   ├── helpers/                       # Test utilities
│   │   ├── mcp_client.py
│   │   ├── allure_utils.py
│   │   ├── data_generators.py
│   │   ├── assertions.py
│   │   └── wait_conditions.py
│   │
│   ├── ui/                            # UI-specific tests
│   │   ├── test_login_ui.py
│   │   └── test_navigation_ui.py
│   │
│   ├── api/                           # API-specific tests
│   │   ├── test_users_api.py
│   │   └── test_auth_api.py
│   │
│   └── integration/                   # Integration tests
│       └── test_end_to_end.py
│
├── mcp_servers/
│   ├── fastapi_mcp/                   # FastAPI MCP Server (Prod/CI)
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── routers/
│   │   ├── services/
│   │   ├── database/
│   │   └── auth/
│   │
│   ├── playwright_mcp/                # Playwright MCP Server (Dev)
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── tools/
│   │   ├── session/
│   │   └── gherkin/
│   │
│   └── scripts/                       # Server startup scripts
│       ├── start_fastapi_mcp.sh
│       ├── start_fastapi_mcp.bat
│       ├── start_playwright_mcp.sh
│       └── start_playwright_mcp.bat
│
├── llm/                               # LLM integration
│   ├── client.py
│   ├── providers/
│   │   ├── ollama.py
│   │   └── openai.py
│   ├── prompts/
│   │   ├── gherkin_generation.py
│   │   └── edge_case_suggestions.py
│   └── workflows/
│       ├── scenario_generator.py
│       └── review_pipeline.py
│
└── docs/                              # Comprehensive documentation
    ├── getting_started.md
    ├── architecture.md
    ├── writing_tests.md
    ├── page_objects.md
    ├── mcp_servers.md
    ├── llm_integration.md
    ├── ci_cd.md
    └── troubleshooting.md
```

---

## 💻 Installation

### System Requirements

- **Python**: 3.9 or higher (3.11/3.12 recommended for best performance)
- **OS**: Linux, macOS, or Windows
- **RAM**: 4GB minimum (8GB recommended for parallel execution)
- **Disk Space**: 2GB for dependencies and browser binaries

### Step 1: Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
# Install all development dependencies
pip install -r requirements-dev.txt

# Or install production dependencies only
pip install -r requirements.txt
```

### Step 3: Install Playwright Browsers

```bash
# Install Chromium only (recommended for CI)
python -m playwright install chromium

# Or install all browsers (Chromium, Firefox, WebKit)
python -m playwright install

# With system dependencies (Linux)
python -m playwright install --with-deps chromium
```

### Step 4: Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

```env
# Application URLs
BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:3000/api

# Browser Configuration
HEADLESS=true

# MCP Server Configuration (Production/CI)
FASTAPI_MCP_URL=http://localhost:8000
FASTAPI_MCP_TOKEN=your_secure_token_here

# MCP Server Configuration (Development Only)
PLAYWRIGHT_MCP_URL=http://localhost:8001

# LLM Configuration (Optional)
LLM_PROVIDER=ollama  # or 'openai'
LLM_MODEL=llama2     # or 'gpt-4'
LLM_API_KEY=         # Required for OpenAI-compatible APIs
```

### Step 5: Verify Installation

```bash
# Run pytest version check
pytest --version

# Run Playwright version check
playwright --version

# Run a simple test to verify setup
pytest tests/ui/test_login_ui.py --headed
```

---

## 📖 Usage Examples

### Running Tests

#### Run All Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with detailed output
pytest -vv
```

#### Run BDD Feature Tests

```bash
# Run all feature files
pytest tests/features/

# Run specific feature
pytest tests/features/authentication.feature

# Run specific scenario by name
pytest tests/features/authentication.feature -k "valid credentials"
```

#### Run UI Tests

```bash
# Run all UI tests
pytest tests/ui/

# Run specific UI test
pytest tests/ui/test_login_ui.py

# Run in headed mode (see browser)
pytest tests/ui/ --headed

# Run with specific browser
pytest tests/ui/ --browser firefox
```

#### Run API Tests

```bash
# Run all API tests
pytest tests/api/

# Run specific API test suite
pytest tests/api/test_users_api.py
```

### Parallel Execution

```bash
# Run tests in parallel (auto-detect CPU cores)
pytest -n auto

# Run with specific number of workers
pytest -n 4

# Parallel execution with load distribution
pytest -n auto --dist loadscope
```

### Allure Reporting

```bash
# Generate Allure results
pytest --alluredir=allure-results

# Serve Allure report (opens browser)
allure serve allure-results

# Generate static HTML report
allure generate allure-results -o allure-report --clean

# Open generated report
allure open allure-report
```

### Using MCP Servers

#### Start FastAPI MCP Server

```bash
# Linux/macOS
./mcp_servers/scripts/start_fastapi_mcp.sh

# Windows
mcp_servers\scripts\start_fastapi_mcp.bat

# Or manually
cd mcp_servers/fastapi_mcp
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Start Playwright MCP Server (Development)

```bash
# Linux/macOS
./mcp_servers/scripts/start_playwright_mcp.sh

# Windows
mcp_servers\scripts\start_playwright_mcp.bat
```

#### Use MCP Client in Tests

```python
# tests/test_example.py
def test_with_seeded_user(mcp_client):
    # Seed a test user via MCP
    user = mcp_client.seed_user(
        role="admin",
        email="admin@example.com"
    )
    
    # Build API payload via MCP
    payload = mcp_client.build_payload(
        "create_project",
        {"owner_id": user["id"]}
    )
    
    # Use in API test
    response = api_client.post("/projects", json=payload)
    assert response.status_code == 201
```

### Debugging Tests

```bash
# Run with pytest debugger
pytest --pdb

# Run with trace collection (Playwright)
pytest --tracing on

# Run specific test with screenshot on failure
pytest tests/ui/test_login_ui.py --screenshot on

# Keep browser open on failure
pytest tests/ui/ --headed --slowmo 1000
```

---

## 🔧 Development Workflow

### 1. Write Gherkin Scenarios

Create business-readable scenarios in `tests/features/`:

```gherkin
# tests/features/user_management.feature
Feature: User Management
  As an administrator
  I want to manage user accounts
  So that I can control system access

  Scenario: Create new user with admin role
    Given the admin is authenticated
    When the admin creates a user with role "admin"
    Then the user should be created successfully
    And the user should have admin privileges
```

### 2. Implement Step Definitions

Map Gherkin steps to Python functions in `tests/step_definitions/`:

```python
# tests/step_definitions/user_steps.py
from pytest_bdd import given, when, then, parsers
from tests.pages.admin_page import AdminPage

@given("the admin is authenticated")
def admin_authenticated(admin_page: AdminPage, mcp_client):
    admin = mcp_client.seed_user(role="admin")
    admin_page.login(admin["email"], admin["password"])

@when(parsers.parse('the admin creates a user with role "{role}"'))
def create_user(admin_page: AdminPage, mcp_client, role):
    payload = mcp_client.build_payload("create_user", {"role": role})
    admin_page.create_user(payload)

@then("the user should be created successfully")
def verify_user_created(admin_page: AdminPage):
    assert admin_page.get_success_message() == "User created"
```

### 3. Create Page Objects

Implement UI interactions with stable locators in `tests/pages/`:

```python
# tests/pages/admin_page.py
from tests.pages.base_page import BasePage
from playwright.sync_api import Page

class AdminPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        
    def create_user(self, user_data: dict):
        # Use ARIA roles and labels (stable selectors)
        self.page.get_by_role("button", name="Create User").click()
        self.page.get_by_label("Email").fill(user_data["email"])
        self.page.get_by_label("Role").select_option(user_data["role"])
        self.page.get_by_role("button", name="Save").click()
    
    def get_success_message(self) -> str:
        # Use test-id for dynamic content
        return self.page.get_by_test_id("success-message").text_content()
```

### 4. Run Tests Locally

```bash
# Run your new feature
pytest tests/features/user_management.feature -v

# Run with Allure reporting
pytest tests/features/user_management.feature --alluredir=allure-results
allure serve allure-results
```

### 5. Code Quality Checks

```bash
# Run linter
ruff check .

# Run type checker
mypy tests/

# Format code
ruff format .

# Run all pre-commit hooks
pre-commit run --all-files
```

### 6. LLM-Assisted Scenario Generation (Optional)

```bash
# Start Playwright MCP server
./mcp_servers/scripts/start_playwright_mcp.sh

# Run scenario generation workflow
python llm/workflows/scenario_generator.py \
  --url http://localhost:3000 \
  --objective "Test user profile editing"

# Review generated scenarios
cat tests/features/generated_user_profile.feature

# Edit and commit approved scenarios
git add tests/features/generated_user_profile.feature
git commit -m "Add user profile editing scenarios"
```

---

## 🔄 CI/CD Integration

### GitHub Actions Workflows

The framework includes three main workflows:

#### 1. Test Execution (`.github/workflows/test.yml`)

Runs on every push and pull request:

```yaml
- Starts FastAPI MCP server as a service
- Installs dependencies and Playwright browsers
- Executes pytest with matrix strategy:
  - Python versions: 3.11, 3.12
  - Browsers: chromium, firefox, webkit
- Runs tests in parallel with pytest-xdist
- Uploads test results and Allure artifacts
- Publishes Allure reports to GitHub Pages
```

#### 2. Allure Report Publishing (`.github/workflows/allure-report.yml`)

Generates and publishes HTML reports:

```yaml
- Downloads Allure results from test workflow
- Generates Allure HTML report with history
- Publishes to GitHub Pages
- Sends notification with report URL
```

#### 3. Lint and Type Checking (`.github/workflows/lint.yml`)

Enforces code quality:

```yaml
- Runs ruff for linting and formatting checks
- Executes mypy for static type checking
- Validates import sorting
- Checks for common issues
```

### Environment Variables for CI

Configure these secrets in GitHub repository settings:

```
BASE_URL              # Application URL for testing
API_BASE_URL          # API endpoint URL
FASTAPI_MCP_URL       # MCP server endpoint
FASTAPI_MCP_TOKEN     # MCP authentication token
TEST_DB_URL           # Test database connection string (optional)
ALLURE_DEPLOY_KEY     # SSH key for GitHub Pages deployment
```

### Matrix Testing Strategy

Tests run across multiple configurations:

| Python Version | Browsers | Parallel Workers |
|----------------|----------|------------------|
| 3.11 | chromium | 4 |
| 3.11 | firefox | 4 |
| 3.11 | webkit | 4 |
| 3.12 | chromium | 4 |
| 3.12 | firefox | 4 |
| 3.12 | webkit | 4 |

### Viewing Test Reports

After workflow completion:

1. **GitHub Pages**: Access reports at `https://<username>.github.io/<repository>/`
2. **Artifacts**: Download from workflow run page
3. **Logs**: View detailed execution logs in Actions tab

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

### Getting Started

1. **Fork the repository** and clone your fork
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Install development dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   pre-commit install
   ```

### Development Guidelines

#### Code Style
- Follow PEP 8 style guide
- Use type hints for all functions
- Maximum line length: 100 characters
- Use ruff for formatting: `ruff format .`

#### Test Writing
- **Gherkin**: Keep scenarios business-readable and high-level
- **Step Definitions**: Delegate to Page Objects, avoid direct Playwright calls
- **Page Objects**: Use stable selectors (ARIA roles > test-ids > CSS)
- **API Tests**: Use typed models and MCP-generated payloads
- **Isolation**: Each test must be independent and parallel-safe

#### Best Practices
- **No Hardcoded Data**: Use MCP tools for test data seeding
- **No Brittle Selectors**: Prefer `get_by_role()` and `get_by_label()`
- **Deterministic Tests**: Reset state before each test with `mcp_client.reset_env()`
- **Meaningful Names**: Use descriptive variable and function names
- **Documentation**: Add docstrings for public APIs

### Testing Your Changes

```bash
# Run affected tests
pytest tests/features/ -v

# Run linting
ruff check .

# Run type checking
mypy tests/

# Run all quality checks
pre-commit run --all-files
```

### Submitting Pull Requests

1. **Ensure all tests pass** locally
2. **Update documentation** if adding new features
3. **Add tests** for new functionality
4. **Write clear commit messages**:
   ```
   feat: Add user role management scenarios
   
   - Implement Gherkin scenarios for role assignment
   - Create RoleManagementPage page object
   - Add step definitions with MCP integration
   ```
5. **Push to your fork** and create a pull request
6. **Wait for CI checks** to pass
7. **Address review feedback** promptly

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] New features have test coverage
- [ ] Documentation is updated
- [ ] Code follows style guidelines
- [ ] Commit messages are clear
- [ ] No merge conflicts with main
- [ ] Pre-commit hooks pass

---

## 📚 Documentation

Comprehensive guides are available in the `docs/` directory:

- **[Getting Started](docs/getting_started.md)**: Detailed setup and first test walkthrough
- **[Architecture](docs/architecture.md)**: System design and component interactions
- **[Writing Tests](docs/writing_tests.md)**: Best practices for test authoring
- **[Page Objects](docs/page_objects.md)**: Page Object Pattern implementation guide
- **[MCP Servers](docs/mcp_servers.md)**: MCP server setup and tool usage
- **[LLM Integration](docs/llm_integration.md)**: LLM-assisted test generation workflow
- **[CI/CD](docs/ci_cd.md)**: GitHub Actions configuration and deployment
- **[Troubleshooting](docs/troubleshooting.md)**: Common issues and solutions

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with these excellent open-source projects:

- [pytest](https://pytest.org/) - Testing framework
- [Playwright](https://playwright.dev/) - Browser automation
- [pytest-bdd](https://pytest-bdd.readthedocs.io/) - Gherkin/BDD support
- [FastAPI](https://fastapi.tiangolo.com/) - Modern API framework
- [httpx](https://www.python-httpx.org/) - HTTP client library
- [Allure](https://docs.qameta.io/allure/) - Test reporting
- [Pydantic](https://docs.pydantic.dev/) - Data validation

---

## 📞 Support

- **Issues**: Report bugs via [GitHub Issues](../../issues)
- **Discussions**: Ask questions in [GitHub Discussions](../../discussions)
- **Documentation**: Check [docs/](docs/) for detailed guides

---

**Happy Testing! 🎉**
