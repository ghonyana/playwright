# Python Test Automation Framework with Playwright

A comprehensive, enterprise-ready Python test automation framework combining modern testing practices with LLM-assisted development capabilities.

## 🎯 Overview

This framework provides a unified testing solution that seamlessly integrates:

- **UI Testing** with Playwright for browser automation
- **API Testing** with httpx for REST API validation
- **BDD Testing** with pytest-bdd for business-readable scenarios
- **MCP Integration** for deterministic test data management
- **LLM-Assisted** test generation and exploration
- **Allure Reporting** for beautiful test reports
- **CI/CD Ready** with GitHub Actions integration

## ✨ Key Features

- 🎭 **Playwright Integration**: Modern browser automation with stable selectors (ARIA roles, test-ids)
- 🥒 **BDD Support**: Write tests in Gherkin for business-readable scenarios
- 🔌 **MCP Servers**: FastAPI and Playwright MCP servers for test data and exploration
- 🤖 **LLM Integration**: Optional AI-assisted test generation (Ollama/OpenAI)
- 📊 **Allure Reports**: Professional HTML reports with screenshots and traces
- 🚀 **Parallel Execution**: Run tests in parallel with pytest-xdist
- 🔒 **Test Isolation**: Each test gets a fresh browser context
- 🎨 **Page Object Pattern**: Maintainable UI test architecture
- 📦 **Typed API Clients**: Type-safe API testing with Pydantic models
- ⚡ **Fast & Reliable**: Modern tools and best practices

## 📋 Prerequisites

- **Python 3.9+** (Python 3.11 or 3.12 recommended)
- **Git** for version control
- **Node.js 16+** (for Playwright browser drivers)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd playwright-test-automation
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate on Linux/Mac
source venv/bin/activate

# Activate on Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install -r requirements-dev.txt

# Install Playwright browsers
python -m playwright install chromium --with-deps
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Set BASE_URL, API_BASE_URL, etc.
```

### 5. Run Tests

```bash
# Run all tests
pytest

# Run with parallel execution
pytest -n auto

# Run specific markers
pytest -m ui      # UI tests only
pytest -m api     # API tests only
pytest -m smoke   # Smoke tests only

# Generate Allure report
pytest --alluredir=allure-results
allure serve allure-results
```

## 📁 Project Structure

```
playwright-test-automation/
├── tests/                          # Test suite
│   ├── conftest.py                 # Pytest fixtures and configuration
│   ├── features/                   # BDD Gherkin feature files
│   ├── step_definitions/           # BDD step implementations
│   ├── pages/                      # Page Object Models
│   ├── api_clients/                # API client wrappers
│   ├── helpers/                    # Test utilities
│   ├── ui/                         # UI-specific tests
│   ├── api/                        # API-specific tests
│   └── integration/                # Integration tests
├── mcp_servers/                    # MCP server implementations
│   ├── fastapi_mcp/                # FastAPI MCP for test data
│   └── playwright_mcp/             # Playwright MCP for exploration
├── llm/                            # LLM integration
│   ├── providers/                  # Ollama, OpenAI providers
│   ├── prompts/                    # LLM prompt templates
│   └── workflows/                  # Test generation workflows
├── docs/                           # Documentation
├── .github/                        # GitHub Actions workflows
├── pyproject.toml                  # Project configuration
├── requirements.txt                # Production dependencies
├── requirements-dev.txt            # Development dependencies
├── pytest.ini                      # Pytest configuration
├── .env.example                    # Environment template
└── README.md                       # This file
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```bash
# Application URLs
BASE_URL=http://localhost:3000          # Web UI base URL
API_BASE_URL=http://localhost:8000      # REST API base URL

# Browser Settings
HEADLESS=true                            # Run browsers headlessly
BROWSER=chromium                         # chromium, firefox, webkit

# Test Execution
PARALLEL_WORKERS=auto                    # Number of parallel workers
TEST_TIMEOUT=30000                       # Default timeout in ms

# MCP Servers (optional)
FASTAPI_MCP_URL=http://localhost:8001
PLAYWRIGHT_MCP_URL=http://localhost:8002

# LLM Integration (optional)
LLM_PROVIDER=ollama                      # ollama, openai, azure
LLM_MODEL=llama3.2
LLM_API_KEY=                             # Required for OpenAI/Azure

# Reporting
ALLURE_RESULTS_DIR=allure-results
CAPTURE_SCREENSHOT_ON_FAILURE=true
CAPTURE_TRACE=true
```

## 📖 Usage Examples

### Writing UI Tests (Page Object Pattern)

```python
# tests/pages/login_page.py
class LoginPage:
    def __init__(self, page):
        self.page = page
    
    def navigate(self):
        self.page.goto("/login")
    
    def login(self, email, password):
        self.page.get_by_label("Email").fill(email)
        self.page.get_by_label("Password").fill(password)
        self.page.get_by_role("button", name="Login").click()

# tests/ui/test_login.py
def test_successful_login(page, base_url):
    login_page = LoginPage(page)
    login_page.navigate()
    login_page.login("user@example.com", "password123")
    expect(page).to_have_url(f"{base_url}/dashboard")
```

### Writing API Tests

```python
# tests/api/test_users_api.py
def test_create_user(api_client):
    response = api_client.post(
        "/users",
        json={
            "email": "new@example.com",
            "name": "New User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
```

### Writing BDD Tests

```gherkin
# tests/features/authentication.feature
Feature: User Authentication
  
  Scenario: Successful login with valid credentials
    Given the user is on the login page
    When the user enters valid credentials
    And clicks the login button
    Then the user should be redirected to the dashboard
```

## 🧪 Testing Best Practices

1. **Use Stable Locators**: Prefer ARIA roles, labels, and test-ids over CSS/XPath
2. **Test Isolation**: Each test gets a fresh browser context
3. **Page Objects**: Keep UI logic in page objects, not test files
4. **Parallel-Friendly**: Design tests to run independently
5. **BDD for Behavior**: Use Gherkin for business-readable scenarios
6. **API for Setup**: Use API calls for test data setup when possible
7. **Screenshots on Failure**: Automatically captured for debugging
8. **Traces**: Enabled by default for post-mortem debugging

## 🛠️ Development Tools

### Code Quality

```bash
# Format code with ruff
ruff format .

# Lint code
ruff check .

# Type checking
mypy tests/

# Run with coverage
pytest --cov=tests --cov-report=html
```

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📊 Reporting

### Allure Reports

```bash
# Generate and view Allure report
pytest --alluredir=allure-results
allure serve allure-results
```

### HTML Reports

```bash
# Generate pytest-html report
pytest --html=report.html --self-contained-html
```

## 🤝 Contributing

1. Follow the Page Object Pattern for UI tests
2. Write business-readable Gherkin scenarios
3. Use stable locators (ARIA roles, test-ids)
4. Keep tests isolated and parallel-friendly
5. Add Allure decorators for better reporting
6. Run linters before committing

## 📚 Documentation

- [Getting Started Guide](docs/getting_started.md)
- [Architecture Overview](docs/architecture.md)
- [Writing Tests](docs/writing_tests.md)
- [Page Objects Guide](docs/page_objects.md)
- [MCP Servers](docs/mcp_servers.md)
- [LLM Integration](docs/llm_integration.md)
- [CI/CD Setup](docs/ci_cd.md)

## 🔍 Troubleshooting

### Playwright Browsers Not Installed

```bash
python -m playwright install chromium --with-deps
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Tests Timing Out

```bash
# Increase timeout in .env
TEST_TIMEOUT=60000
NAVIGATION_TIMEOUT=60000
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Playwright](https://playwright.dev/) for browser automation
- [pytest](https://pytest.org/) for the testing framework
- [pytest-bdd](https://pytest-bdd.readthedocs.io/) for BDD support
- [Allure](https://docs.qameta.io/allure/) for reporting
- [httpx](https://www.python-httpx.org/) for API testing

## 📞 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Built with ❤️ by the Blitzy Team**
