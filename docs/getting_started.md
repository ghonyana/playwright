# Getting Started

Welcome to the Python Test Automation Starter Framework! This guide will help you set up your development environment and run your first tests in under 10 minutes.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Environment Configuration](#environment-configuration)
4. [Running Your First Tests](#running-your-first-tests)
5. [Understanding Test Output](#understanding-test-output)
6. [Next Steps](#next-steps)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

### Required Software

**Python 3.9 or Later** (Python 3.11 or 3.12 Recommended)

- **Why 3.9+?** Playwright 1.55.0 requires Python 3.9 minimum, and pytest 8.4.2 dropped Python 3.8 support.
- **Why 3.11 or 3.12?** Significant performance improvements, enhanced error messages, and better async support.

Check your Python version:
```bash
python --version
# or
python3 --version
```

If you need to install Python:
- **macOS**: `brew install python@3.11`
- **Ubuntu/Debian**: `sudo apt install python3.11 python3.11-venv`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

**Git Version Control**

```bash
git --version
```

If not installed:
- **macOS**: `brew install git`
- **Ubuntu/Debian**: `sudo apt install git`
- **Windows**: Download from [git-scm.com](https://git-scm.com/downloads)

### Operating System Compatibility

This framework is tested and supported on:
- ✅ **Linux** (Ubuntu 20.04+, Debian 11+)
- ✅ **macOS** (11.0+)
- ✅ **Windows** (10+, Windows 11)

### Hardware Recommendations

- **RAM**: 4GB minimum (8GB+ recommended for parallel test execution)
- **Disk Space**: 2GB for Python dependencies and browser binaries
- **CPU**: Multi-core processor recommended for parallel execution

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/playwright-test-automation.git
cd playwright-test-automation
```

### Step 2: Create a Virtual Environment

**Why use a virtual environment?** Isolates project dependencies from system Python packages, preventing conflicts.

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

You should see `(venv)` prefix in your terminal prompt indicating the virtual environment is active.

### Step 3: Install Python Dependencies

Install all development dependencies (includes testing tools, linters, and formatters):

```bash
pip install --upgrade pip
pip install -r requirements-dev.txt
```

This installs:
- `pytest` (test framework)
- `playwright` (browser automation)
- `pytest-bdd` (Gherkin/BDD support)
- `httpx` (API testing)
- `allure-pytest` (reporting)
- `ruff`, `mypy` (code quality tools)
- And more...

**Expected output:**
```
Successfully installed pytest-8.4.2 playwright-1.55.0 ...
```

### Step 4: Install Playwright Browsers

Playwright requires browser binaries (Chromium, Firefox, WebKit). Install Chromium for local development:

```bash
python -m playwright install chromium
```

**For all browsers (optional):**
```bash
python -m playwright install chromium firefox webkit
```

**Expected output:**
```
Downloading Chromium 123.0.6312.4 ...
Chromium 123.0.6312.4 downloaded to ...
```

### Step 5: Verify Installation

Run verification commands to confirm successful setup:

**Check pytest:**
```bash
pytest --version
```
Expected: `pytest 8.4.2`

**Check Playwright:**
```bash
python -m playwright --version
```
Expected: `Version 1.55.0`

**Check installed packages:**
```bash
pip list | grep -E '(pytest|playwright|httpx|allure)'
```

Expected output should include:
```
allure-pytest      2.15.0
httpx              0.28.1
playwright         1.55.0
pytest             8.4.2
pytest-bdd         8.1.0
pytest-playwright  0.6.2
```

---

## Environment Configuration

### Step 1: Create Environment File

Copy the example environment configuration:

```bash
cp .env.example .env
```

### Step 2: Configure Essential Variables

Edit `.env` file with your settings:

```bash
# Application Under Test URLs
BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:3000/api

# Browser Configuration
HEADLESS=false
BROWSER=chromium

# MCP Server Configuration (for deterministic testing)
FASTAPI_MCP_URL=http://localhost:8000
FASTAPI_MCP_TOKEN=your_dev_token_here

# LLM Configuration (optional, for test generation)
LLM_PROVIDER=ollama
LLM_MODEL=llama2
LLM_API_KEY=

# Parallel Execution
PYTEST_WORKERS=auto
```

### Key Configuration Variables

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `BASE_URL` | Web application URL for UI tests | `http://localhost:3000` | Yes |
| `API_BASE_URL` | REST API endpoint base URL | `http://localhost:3000/api` | Yes |
| `HEADLESS` | Run browsers in headless mode | `false` (local), `true` (CI) | No |
| `BROWSER` | Browser to use (chromium, firefox, webkit) | `chromium` | No |
| `FASTAPI_MCP_URL` | MCP server for test data management | `http://localhost:8000` | Yes |
| `FASTAPI_MCP_TOKEN` | Authentication token for MCP server | - | Yes |
| `LLM_PROVIDER` | LLM provider (ollama, openai) | `ollama` | No |
| `LLM_MODEL` | LLM model name | `llama2` | No |

### Local vs. CI Configuration

**Local Development:**
- `HEADLESS=false` - See browser interactions during test execution
- `BROWSER=chromium` - Fast, compatible browser for development
- Both MCP servers (FastAPI + Playwright) available

**CI/CD Environment:**
- `HEADLESS=true` - Required for GitHub Actions runners
- `BROWSER=chromium` - Fastest browser for automated execution
- Only FastAPI MCP server runs by default

### Verify Configuration

Test that environment variables are loaded correctly:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('BASE_URL:', os.getenv('BASE_URL'))"
```

Expected output:
```
BASE_URL: http://localhost:3000
```

---

## Running Your First Tests

### Prerequisites: Start MCP Server (Optional for First Run)

If you want full integration with test data management, start the FastAPI MCP server:

```bash
# In a separate terminal
cd mcp_servers/fastapi_mcp
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Wait for:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Note:** Some example tests can run without MCP server for initial verification.

### Run All Tests

Execute the complete test suite:

```bash
pytest
```

**Expected output:**
```
========================================= test session starts ==========================================
platform linux -- Python 3.11.7, pytest-8.4.2, pluggy-1.5.0
rootdir: /path/to/playwright-test-automation
plugins: playwright-0.6.2, bdd-8.1.0, xdist-3.6.1, allure-pytest-2.15.0
collected 15 items

tests/ui/test_login_ui.py ..                                                                    [ 13%]
tests/ui/test_navigation_ui.py .                                                                [ 20%]
tests/api/test_users_api.py ...                                                                 [ 40%]
tests/api/test_auth_api.py ..                                                                   [ 53%]
tests/features/authentication.feature::test_successful_login PASSED                             [ 60%]
tests/features/user_management.feature::test_create_user PASSED                                 [ 73%]

========================================== 15 passed in 12.45s =========================================
```

### Run Specific Test Types

**UI Tests Only:**
```bash
pytest tests/ui/
```

**API Tests Only:**
```bash
pytest tests/api/
```

**BDD Feature Tests:**
```bash
pytest tests/features/
```

**Single Test File:**
```bash
pytest tests/ui/test_login_ui.py
```

**Single Test Function:**
```bash
pytest tests/ui/test_login_ui.py::test_successful_login
```

### Useful pytest Flags

**Verbose Output** (shows each test name):
```bash
pytest -v
```

**Very Verbose** (shows full test paths and detailed output):
```bash
pytest -vv
```

**Run Tests by Keyword** (matches test/file names):
```bash
pytest -k "login"
```

**Run Tests by Marker** (custom tags):
```bash
pytest -m smoke
```

**Stop on First Failure:**
```bash
pytest -x
```

**Show Local Variables on Failure:**
```bash
pytest -l
```

**Headed Mode** (see browser during UI tests):
```bash
pytest --headed
```

### Parallel Execution

Run tests in parallel for faster execution:

```bash
pytest -n auto
```

This automatically detects CPU cores and distributes tests across workers.

**Specify number of workers:**
```bash
pytest -n 4
```

---

## Understanding Test Output

### Console Output

**Successful Test:**
```
tests/ui/test_login_ui.py::test_successful_login PASSED [100%]
```

**Failed Test:**
```
tests/ui/test_login_ui.py::test_invalid_credentials FAILED [100%]

================================== FAILURES ===================================
____________________________ test_invalid_credentials _________________________

    def test_invalid_credentials(login_page):
        login_page.navigate()
        login_page.login("invalid@example.com", "wrongpassword")
>       assert login_page.has_error_message()
E       AssertionError: assert False

tests/ui/test_login_ui.py:15: AssertionError
```

### Allure Reports

Allure provides rich HTML reports with test history, screenshots, and detailed logs.

**Generate Allure Report:**
```bash
# Run tests with Allure
pytest --alluredir=allure-results

# Generate and open HTML report
allure serve allure-results
```

**Expected output:**
```
Generating report to temp directory...
Report successfully generated to /tmp/12345678-allure-report
Starting web server...
Server started at http://localhost:45678/
```

Your default browser will open with the Allure report showing:
- Test execution summary
- Pass/fail rates
- Test duration trends
- Screenshots on failures
- Browser traces
- Request/response details (API tests)

**Alternative: Generate Static HTML:**
```bash
allure generate allure-results -o allure-report --clean
open allure-report/index.html
```

### Playwright Traces

View detailed execution traces for debugging failures:

```bash
# Traces are captured automatically on failure
playwright show-trace test-results/*/trace.zip
```

This opens Playwright Trace Viewer showing:
- Step-by-step execution
- Network requests
- Console logs
- Screenshots at each action
- Timing information

---

## Next Steps

Congratulations! You've successfully set up the test automation framework and run your first tests. Here's what to explore next:

### Learn the Architecture

**Read:** [docs/architecture.md](architecture.md)

Understand the five-layer framework structure:
- Test Runner Layer (pytest)
- Test Asset Layer (Page Objects, API Clients)
- Supporting MCP Services Layer
- Optional LLM Service Layer
- CI/CD Orchestration Layer

### Write Your First Test

**Read:** [docs/writing_tests.md](writing_tests.md)

Learn how to:
- Author business-readable Gherkin scenarios
- Implement step definitions
- Write API tests with httpx
- Use MCP tools for test data management
- Follow best practices for maintainable tests

### Master Page Objects

**Read:** [docs/page_objects.md](page_objects.md)

Explore:
- Page Object Pattern implementation
- Stable locator strategies (ARIA roles, test IDs)
- BasePage class and reusable components
- Integration with step definitions

### Understand MCP Servers

**Read:** [docs/mcp_servers.md](mcp_servers.md)

Discover:
- FastAPI MCP server for deterministic test data
- Tools: `seed_user`, `build_payload`, `reset_env`, `query_state`
- Playwright MCP server for LLM-driven exploration
- Authentication and error handling

### Leverage LLM-Assisted Testing

**Read:** [docs/llm_integration.md](llm_integration.md)

Learn to:
- Generate test scenarios with local Ollama or hosted OpenAI
- Explore applications with LLM-controlled browsers
- Convert explorations to Gherkin features
- Implement human review workflows

### Configure CI/CD

**Read:** [docs/ci_cd.md](ci_cd.md)

Set up:
- GitHub Actions test execution workflow
- FastAPI MCP server lifecycle in CI
- Allure report generation and publishing
- Matrix strategy for parallel execution

### Troubleshoot Issues

**Read:** [docs/troubleshooting.md](troubleshooting.md)

Find solutions for:
- Installation and setup problems
- Test execution failures
- Browser automation issues
- MCP server connectivity
- CI/CD pipeline failures

---

## Troubleshooting

### Common Setup Issues

#### Issue: Python Version Mismatch

**Symptom:**
```
Error: This version of Playwright requires Python 3.9 or later
```

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.11 (recommended)
# macOS
brew install python@3.11

# Ubuntu
sudo apt install python3.11 python3.11-venv

# Create virtual environment with specific version
python3.11 -m venv venv
source venv/bin/activate
```

#### Issue: Playwright Browser Installation Fails

**Symptom:**
```
Error: Failed to install browsers
```

**Solution:**

**On Linux:**
```bash
# Install system dependencies first
sudo apt-get update
sudo apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2

# Then install browsers
python -m playwright install chromium --with-deps
```

**On macOS/Windows:**
```bash
# Install with dependencies
python -m playwright install chromium --with-deps
```

#### Issue: .env File Not Loading

**Symptom:**
```
KeyError: 'BASE_URL'
```

**Solution:**
```bash
# Verify .env file exists
ls -la .env

# Create from template if missing
cp .env.example .env

# Edit with your values
nano .env  # or your preferred editor

# Verify loading
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('BASE_URL'))"
```

#### Issue: pip install Fails with Dependency Conflicts

**Symptom:**
```
ERROR: Cannot install requirements due to conflicting dependencies
```

**Solution:**
```bash
# Upgrade pip
pip install --upgrade pip

# Install with no-cache
pip install --no-cache-dir -r requirements-dev.txt

# Or create fresh virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

#### Issue: Tests Fail to Collect

**Symptom:**
```
collected 0 items
```

**Solution:**
```bash
# Check test discovery
pytest --collect-only -v

# Verify __init__.py exists in test directories
ls tests/__init__.py
ls tests/ui/__init__.py

# Run from project root
cd /path/to/playwright-test-automation
pytest
```

### Getting Help

If you encounter issues not covered here:

1. **Check Full Documentation:**
   - [Troubleshooting Guide](troubleshooting.md) - Comprehensive issue solutions
   - [Architecture](architecture.md) - System design and components
   - [Writing Tests](writing_tests.md) - Test authoring patterns

2. **Review Example Tests:**
   - `tests/ui/` - UI test examples
   - `tests/api/` - API test examples
   - `tests/features/` - BDD scenario examples

3. **External Resources:**
   - [Playwright Python Documentation](https://playwright.dev/python/)
   - [pytest Documentation](https://docs.pytest.org/)
   - [pytest-bdd Documentation](https://pytest-bdd.readthedocs.io/)

4. **Community Support:**
   - GitHub Issues: [your-repo/issues](https://github.com/your-org/playwright-test-automation/issues)
   - Playwright Discord: [discord.gg/playwright](https://discord.gg/playwright)

---

## Quick Reference

### Essential Commands

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run in parallel
pytest -n auto

# Run specific tests
pytest tests/ui/test_login_ui.py
pytest -k "login"
pytest -m smoke

# Generate Allure report
pytest --alluredir=allure-results
allure serve allure-results

# Run in headed mode (see browser)
pytest --headed

# Run with debugger on failure
pytest --pdb
```

### Project Structure Quick View

```
playwright-test-automation/
├── tests/
│   ├── features/           # Gherkin .feature files
│   ├── step_definitions/   # BDD step implementations
│   ├── pages/              # Page Object classes
│   ├── api_clients/        # Typed API clients
│   ├── ui/                 # UI-specific tests
│   ├── api/                # API-specific tests
│   └── conftest.py         # Shared pytest fixtures
├── mcp_servers/
│   ├── fastapi_mcp/        # Test data management server
│   └── playwright_mcp/     # LLM exploration server
├── llm/                    # LLM integration components
├── docs/                   # Project documentation
├── .env                    # Environment configuration
├── pytest.ini              # pytest configuration
├── requirements.txt        # Production dependencies
└── requirements-dev.txt    # Development dependencies
```

### Environment Variables Quick Reference

```bash
# Application URLs
BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:3000/api

# Browser
HEADLESS=false
BROWSER=chromium

# MCP Servers
FASTAPI_MCP_URL=http://localhost:8000
FASTAPI_MCP_TOKEN=your_token

# LLM (optional)
LLM_PROVIDER=ollama
LLM_MODEL=llama2
```

---

**You're all set!** Start writing tests and exploring the framework capabilities. Happy testing! 🚀
