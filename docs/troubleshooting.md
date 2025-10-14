# Troubleshooting Guide

This guide provides solutions to common issues you may encounter when working with the test automation framework. Use this as a self-service reference to resolve problems quickly without external support.

## Table of Contents

1. [Installation and Setup Issues](#1-installation-and-setup-issues)
2. [Test Execution Problems](#2-test-execution-problems)
3. [Playwright Browser Automation Issues](#3-playwright-browser-automation-issues)
4. [MCP Server Connectivity Problems](#4-mcp-server-connectivity-problems)
5. [API Testing Issues](#5-api-testing-issues)
6. [Allure Reporting Problems](#6-allure-reporting-problems)
7. [CI/CD and GitHub Actions Failures](#7-cicd-and-github-actions-failures)
8. [Performance and Timeout Issues](#8-performance-and-timeout-issues)
9. [Environment Configuration Problems](#9-environment-configuration-problems)
10. [Debugging Techniques and Tools](#10-debugging-techniques-and-tools)

---

## 1. Installation and Setup Issues

### Problem: Python Version Mismatch

**Error Message:**
```
Error: This version of Playwright requires Python 3.9 or later
```

**Solution:**
```bash
# Check current Python version
python --version

# Install Python 3.11 (recommended)
# macOS
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv

# Windows - Download from python.org

# Create virtual environment with specific version
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify version in virtual environment
python --version
```

### Problem: pip install fails with dependency conflicts

**Error Message:**
```
ERROR: Cannot install requirements due to conflicting dependencies
```

**Solution:**
```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install with no-cache to avoid stale packages
pip install --no-cache-dir -r requirements-dev.txt

# If still failing, create fresh virtual environment
deactivate  # Exit current venv
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

### Problem: Playwright browser installation fails

**Error Message:**
```
Error: Failed to install browsers
playwright install: command not found
```

**Solution:**
```bash
# Install system dependencies first (Ubuntu/Debian)
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
    libasound2 \
    libxshmfence1

# Install browsers with dependencies
python -m playwright install chromium --with-deps

# For CI/CD environments, install all browsers
python -m playwright install --with-deps

# Verify installation
python -m playwright install --help
```

### Problem: .env file not loading

**Error Message:**
```
KeyError: 'BASE_URL'
```

**Solution:**
```bash
# Create .env file from template
cp .env.example .env

# Edit with your specific values
nano .env  # or vim, code, etc.

# Verify environment variables are loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('BASE_URL'))"

# Check .env file location (should be in project root)
ls -la .env

# Ensure .env is not in .gitignore (but don't commit sensitive values)
cat .gitignore | grep -v "^#" | grep ".env"
```

### Problem: Pre-commit hooks installation fails

**Error Message:**
```
[ERROR] Cowardly refusing to install hooks with `core.hooksPath` set.
```

**Solution:**
```bash
# Unset core.hooksPath if set
git config --unset core.hooksPath

# Install pre-commit hooks
pre-commit install

# Run hooks manually to test
pre-commit run --all-files

# Skip problematic hooks temporarily
SKIP=mypy pre-commit run --all-files
```

---

## 2. Test Execution Problems

### Problem: No tests collected

**Error Message:**
```
collected 0 items
```

**Solution:**
```bash
# Check pytest discovery settings
cat pytest.ini

# Run with verbose discovery to see what pytest finds
pytest --collect-only -v

# Verify test files match naming convention
# Test files must be named test_*.py or *_test.py
ls tests/test_*.py
ls tests/*_test.py

# Check feature files exist for BDD tests
ls tests/features/*.feature

# Verify Python path includes project root
export PYTHONPATH=$PWD:$PYTHONPATH
pytest --collect-only -v

# Run pytest as module to ensure imports work
python -m pytest tests/ --collect-only -v
```

### Problem: Import errors in tests

**Error Message:**
```
ImportError: cannot import name 'LoginPage' from 'tests.pages'
ModuleNotFoundError: No module named 'tests'
```

**Solution:**
```bash
# Ensure __init__.py exists in all test directories
touch tests/__init__.py
touch tests/pages/__init__.py
touch tests/api_clients/__init__.py
touch tests/step_definitions/__init__.py
touch tests/helpers/__init__.py

# Verify directory structure
tree tests/ -I '__pycache__'

# Add project root to PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH

# Or run pytest as module (recommended)
python -m pytest tests/

# Check imports in Python REPL
python
>>> from tests.pages.login_page import LoginPage
>>> exit()
```

### Problem: Fixtures not found

**Error Message:**
```
fixture 'login_page' not found
available fixtures: ...
```

**Solution:**
```python
# Check conftest.py has the fixture defined
# tests/conftest.py should contain:
import pytest
from tests.pages.login_page import LoginPage

@pytest.fixture
def login_page(page):
    return LoginPage(page)

# Verify conftest.py location
# Should be in tests/ directory or parent directory of test file
ls tests/conftest.py

# List all available fixtures
pytest --fixtures

# Check for fixture scope issues
# Ensure fixture scope matches usage
@pytest.fixture(scope="function")  # Creates new instance per test
def login_page(page):
    return LoginPage(page)
```

### Problem: pytest-bdd step definitions not found

**Error Message:**
```
StepDefinitionNotFoundError: Step definition is not found: Given the user is on the login page
```

**Solution:**
```bash
# Verify step_definitions directory structure
ls tests/step_definitions/

# Check pytest.ini has correct BDD configuration
cat pytest.ini | grep bdd

# Ensure step definitions are imported in conftest.py
# tests/conftest.py
pytest_plugins = [
    'pytest_bdd',
]

# Re-run with verbose output
pytest --gherkin-terminal-reporter -vv tests/features/

# Verify step definition syntax matches feature file
# Feature file: Given the user is on the login page
# Step definition: @given("the user is on the login page")
```

---

## 3. Playwright Browser Automation Issues

### Problem: Element not found

**Error Message:**
```
TimeoutError: Timeout 30000ms exceeded.
=========================== logs ===========================
waiting for selector "button.login-btn"
============================================================
```

**Solution:**
```python
# Use stable locators (ARIA roles) instead of CSS selectors
# ❌ Bad - brittle CSS selector
page.locator('.btn-primary').click()

# ✅ Good - stable ARIA role
page.get_by_role('button', name='Sign In').click()

# Use other stable locator strategies
page.get_by_label('Email').fill('user@example.com')  # Label text
page.get_by_placeholder('Enter your email').fill('user@example.com')  # Placeholder
page.get_by_test_id('login-button').click()  # data-testid attribute
page.get_by_text('Welcome back').wait_for()  # Text content

# Add explicit waits
page.wait_for_selector('role=button[name="Sign In"]', state='visible')

# Increase timeout for slow-loading elements
page.get_by_role('button').click(timeout=60000)

# Wait for network to be idle
page.wait_for_load_state('networkidle')
```

### Problem: Tests fail in headless mode but pass in headed

**Error Message:**
```
Test passes with HEADLESS=false but fails with HEADLESS=true
```

**Solution:**
```python
# Add explicit wait for page load
page.wait_for_load_state('networkidle')

# Wait for specific element that indicates page is ready
page.wait_for_selector('role=heading[name="Dashboard"]', state='visible')

# Check for timing issues with slow_mo for debugging
# conftest.py
@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    return {
        **browser_type_launch_args,
        "headless": True,
        "slow_mo": 100,  # Slow down by 100ms per action for debugging
    }

# Add viewport size (headless uses different default size)
context = browser.new_context(
    viewport={'width': 1920, 'height': 1080}
)

# Check for animations that may cause issues
# Disable animations for testing
context = browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    reduced_motion='reduce'
)
```

### Problem: Screenshot not captured on failure

**Error Message:**
```
No screenshot in Allure report for failed test
```

**Solution:**
```python
# Ensure pytest-playwright is installed
pip install pytest-playwright

# Check pytest.ini configuration
# pytest.ini
[pytest]
playwright_capture_screenshots = on-failure
playwright_capture_trace = retain-on-failure

# Or manually capture in conftest.py
# tests/conftest.py
import pytest
import allure
from playwright.sync_api import Page

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call" and report.failed:
        # Get page from fixture
        page = item.funcargs.get('page')
        if page:
            screenshot = page.screenshot()
            allure.attach(
                screenshot,
                name='failure_screenshot',
                attachment_type=allure.attachment_type.PNG
            )
```

### Problem: Browser not closing after test

**Error Message:**
```
Multiple browser instances running, consuming memory
Too many open files
```

**Solution:**
```python
# Use function-scoped fixtures for proper cleanup
# tests/conftest.py
import pytest

@pytest.fixture(scope="function")
def browser_context(browser):
    context = browser.new_context()
    yield context
    context.close()

@pytest.fixture(scope="function")
def page(browser_context):
    page = browser_context.new_page()
    yield page
    page.close()

# Verify fixture scope in tests
pytest --setup-show tests/ui/test_login_ui.py

# Clean up manually if needed
# tests/conftest.py
def pytest_sessionfinish(session, exitstatus):
    """Clean up after all tests"""
    import psutil
    import os
    
    # Kill any remaining browser processes
    current_process = psutil.Process(os.getpid())
    children = current_process.children(recursive=True)
    for child in children:
        if 'chrome' in child.name().lower() or 'firefox' in child.name().lower():
            child.kill()
```

### Problem: Flaky tests due to race conditions

**Error Message:**
```
Test sometimes passes, sometimes fails with element not found
```

**Solution:**
```python
# Use auto-waiting built into Playwright locators
# Playwright automatically waits for element to be actionable
page.get_by_role('button', name='Submit').click()  # Auto-waits

# For custom conditions, use expect assertions
from playwright.sync_api import expect

expect(page.get_by_text('Success')).to_be_visible()
expect(page.get_by_role('button')).to_be_enabled()

# Wait for API responses before assertions
with page.expect_response('**/api/users') as response_info:
    page.get_by_role('button', name='Load Users').click()
response = response_info.value
assert response.status == 200

# Use network idle for dynamic content
page.goto('/dashboard')
page.wait_for_load_state('networkidle')

# Retry logic for flaky operations
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def click_element(page, selector):
    page.get_by_role('button', name=selector).click()
```

---

## 4. MCP Server Connectivity Problems

### Problem: Connection refused to MCP server

**Error Message:**
```
requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionRefusedError(61, 'Connection refused'))
Failed to connect to http://localhost:8000
```

**Solution:**
```bash
# Check if MCP server is running
curl http://localhost:8000/health

# If not running, start the FastAPI MCP server
cd mcp_servers/fastapi_mcp
uvicorn main:app --host 0.0.0.0 --port 8000

# Or use the startup script
bash scripts/start_fastapi_mcp.sh

# Check if port is already in use
lsof -i :8000
# Or on Windows: netstat -ano | findstr :8000

# Kill process if port is occupied
kill -9 <PID>

# Verify FASTAPI_MCP_URL in .env
cat .env | grep FASTAPI_MCP_URL
# Should be: FASTAPI_MCP_URL=http://localhost:8000

# Test connectivity
python -c "import httpx; print(httpx.get('http://localhost:8000/health').json())"
```

### Problem: Authentication failed

**Error Message:**
```
401 Unauthorized: Invalid or missing token
403 Forbidden: Access denied
```

**Solution:**
```bash
# Check token configuration in .env
cat .env | grep FASTAPI_MCP_TOKEN

# Verify token matches server configuration
# mcp_servers/fastapi_mcp/config.py
cat mcp_servers/fastapi_mcp/config.py | grep MCP_TOKEN

# Test authentication with curl
curl -H "Authorization: Bearer your_token_here" \
     http://localhost:8000/tools/seed_user

# Update token in .env if mismatch
echo "FASTAPI_MCP_TOKEN=new_token_here" >> .env

# Restart MCP server after token change
# Kill existing process and restart
```

### Problem: MCP tool returns 500 Internal Server Error

**Error Message:**
```
500 Internal Server Error when calling seed_user
{"detail": "Internal server error"}
```

**Solution:**
```bash
# Check MCP server logs with debug level
cd mcp_servers/fastapi_mcp
uvicorn main:app --log-level debug --reload

# Check server console output for stack traces

# Verify database connection (if MCP uses database)
echo $DATABASE_URL
# Test database connectivity
python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()"

# Test tool with correct parameters
curl -X POST http://localhost:8000/tools/seed_user \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"role": "admin", "email": "test@example.com"}'

# Check tool parameter requirements
# mcp_servers/fastapi_mcp/models.py
cat mcp_servers/fastapi_mcp/models.py

# Enable detailed error responses in development
# mcp_servers/fastapi_mcp/main.py
# Set debug=True in FastAPI app
```

### Problem: MCP server slow to respond

**Error Message:**
```
httpx.ReadTimeout: timed out after 10.0 seconds
```

**Solution:**
```python
# Increase timeout in MCP client
# tests/helpers/mcp_client.py
class MCPClient:
    def __init__(self, base_url, token):
        self.client = httpx.Client(
            base_url=base_url,
            timeout=httpx.Timeout(60.0, connect=10.0),  # Increased from 10s
            headers={"Authorization": f"Bearer {token}"}
        )

# Check MCP server performance
# Monitor server logs for slow queries or operations

# Use async operations for better performance
# Replace synchronous httpx.Client with httpx.AsyncClient

# Optimize MCP server database queries
# Add indexes, use connection pooling
```

---

## 5. API Testing Issues

### Problem: httpx connection timeout

**Error Message:**
```
httpx.ConnectTimeout: timed out
httpx.TimeoutException: Connection timeout
```

**Solution:**
```python
# Increase timeout in API client
# tests/api_clients/base_client.py
import httpx

client = httpx.Client(
    base_url=API_BASE_URL,
    timeout=httpx.Timeout(
        30.0,      # Total timeout
        connect=10.0,  # Connection timeout
        read=20.0,     # Read timeout
        write=10.0     # Write timeout
    )
)

# Check API is reachable
import httpx
try:
    response = httpx.get(f'{API_BASE_URL}/health', timeout=5.0)
    print(f"API Status: {response.status_code}")
except Exception as e:
    print(f"API unreachable: {e}")

# Verify API_BASE_URL in .env
echo $API_BASE_URL

# Test API with curl
curl -v $API_BASE_URL/health
```

### Problem: JSON decode error

**Error Message:**
```
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
simplejson.errors.JSONDecodeError: Expecting value
```

**Solution:**
```python
# Check response content type
response = client.get('/api/users')
print(f"Content-Type: {response.headers.get('content-type')}")

# Print raw response for debugging
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Body: {response.text}")

# Handle non-JSON responses gracefully
if response.headers.get('content-type', '').startswith('application/json'):
    data = response.json()
else:
    print(f'Unexpected content type: {response.headers.get("content-type")}')
    print(f'Response body: {response.text}')

# Check for empty response
if not response.text:
    print("Empty response body")
else:
    data = response.json()

# Verify API endpoint returns JSON
curl -H "Accept: application/json" $API_BASE_URL/api/users
```

### Problem: Pydantic validation error

**Error Message:**
```
pydantic.ValidationError: 1 validation error for UserResponse
  field required (type=value_error.missing)
```

**Solution:**
```python
# Print actual response to see structure
response = client.get('/api/users/1')
print(f"Response: {response.json()}")

# Update Pydantic model to match actual API response
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    created_at: Optional[datetime] = None  # Make optional if not always present
    updated_at: Optional[datetime] = None
    
    class Config:
        # Allow extra fields without validation
        extra = "allow"

# Use .parse_obj() with error handling
try:
    user = UserResponse.parse_obj(response.json())
except pydantic.ValidationError as e:
    print(f"Validation errors: {e}")
    print(f"Actual data: {response.json()}")

# Or validate loosely during development
class UserResponse(BaseModel):
    class Config:
        extra = "ignore"  # Ignore extra fields
```

### Problem: API authentication fails

**Error Message:**
```
401 Unauthorized
403 Forbidden
```

**Solution:**
```python
# Ensure authentication token is included
# tests/api_clients/base_client.py
class BaseAPIClient:
    def __init__(self, base_url: str, token: str = None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        self.client = httpx.Client(
            base_url=base_url,
            headers=headers,
            timeout=30.0
        )

# Get token from MCP server or login endpoint
def test_with_auth(mcp_client, users_api):
    # Use MCP to create user with token
    user = mcp_client.seed_user(role="admin", email="test@example.com")
    token = user["token"]
    
    # Create authenticated client
    authenticated_api = UsersAPIClient(
        base_url=API_BASE_URL,
        token=token
    )
    
    response = authenticated_api.get_current_user()
    assert response.status_code == 200

# Debug authentication headers
print(f"Headers: {client.headers}")
```

---

## 6. Allure Reporting Problems

### Problem: Allure command not found

**Error Message:**
```
bash: allure: command not found
zsh: command not found: allure
```

**Solution:**
```bash
# Install Allure command-line tool

# macOS
brew install allure

# Linux (download binary)
wget https://github.com/allure-framework/allure2/releases/download/2.15.0/allure-2.15.0.tgz
tar -zxvf allure-2.15.0.tgz
sudo mv allure-2.15.0 /opt/allure
echo 'export PATH=$PATH:/opt/allure/bin' >> ~/.bashrc
source ~/.bashrc

# Windows (using Scoop)
scoop install allure

# Verify installation
allure --version

# Generate report
allure serve allure-results
```

### Problem: Allure results directory empty

**Error Message:**
```
There are no results directories in the 'allure-results' folder
```

**Solution:**
```bash
# Run pytest with alluredir flag
pytest --alluredir=allure-results tests/

# Check pytest.ini configuration
cat pytest.ini | grep alluredir

# Verify directory exists and has content
ls -la allure-results/
# Should contain .json files

# Check allure-pytest plugin is installed
pip list | grep allure
# Should show: allure-pytest    2.15.0

# Re-install if missing
pip install allure-pytest

# Run with verbose output
pytest --alluredir=allure-results -v tests/
```

### Problem: Screenshots not appearing in Allure report

**Error Message:**
```
Test failures don't show screenshots in Allure report
```

**Solution:**
```python
# Ensure pytest-playwright captures screenshots
# pytest.ini
[pytest]
playwright_capture_screenshots = on-failure
playwright_capture_trace = retain-on-failure

# Or capture manually in conftest.py
import allure
from allure_commons.types import AttachmentType

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    
    if report.when == "call" and report.failed:
        page = item.funcargs.get('page')
        if page:
            # Capture screenshot
            screenshot_bytes = page.screenshot()
            allure.attach(
                screenshot_bytes,
                name='failure_screenshot',
                attachment_type=AttachmentType.PNG
            )

# Manually attach in test
def test_login(page):
    try:
        page.goto('/login')
        page.get_by_role('button', name='Sign In').click()
    except Exception as e:
        allure.attach(
            page.screenshot(),
            name='login_failure',
            attachment_type=AttachmentType.PNG
        )
        raise
```

### Problem: Allure report shows no test history

**Error Message:**
```
Trend chart is empty, no historical data
```

**Solution:**
```bash
# Generate report with history
allure generate allure-results -o allure-report --clean

# Keep history from previous runs
# Copy history folder before generating new report
cp -r allure-report/history allure-results/history
allure generate allure-results -o allure-report --clean

# In CI/CD, persist allure-results between runs
# GitHub Actions example:
# - name: Get Allure history
#   uses: actions/checkout@v3
#   with:
#     ref: gh-pages
#     path: gh-pages
# 
# - name: Copy history
#   run: |
#     mkdir -p allure-results/history
#     cp -r gh-pages/allure-report/history/* allure-results/history/ || true
```

---

## 7. CI/CD and GitHub Actions Failures

### Problem: GitHub Actions workflow fails to start MCP server

**Error Message:**
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
Health check failed
```

**Solution:**
```yaml
# .github/workflows/test.yml
# Add proper health check wait loop
- name: Start MCP Server
  run: |
    cd mcp_servers/fastapi_mcp
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 > mcp_server.log 2>&1 &
    echo $! > mcp_server.pid

- name: Wait for MCP health check
  run: |
    for i in {1..30}; do
      if curl -f http://localhost:8000/health; then
        echo "MCP server is ready"
        exit 0
      fi
      echo "Waiting for MCP server... ($i/30)"
      sleep 2
    done
    echo "MCP server failed to start"
    cat mcp_servers/fastapi_mcp/mcp_server.log
    exit 1

- name: Run Tests
  run: |
    export FASTAPI_MCP_URL=http://localhost:8000
    pytest tests/
```

### Problem: Tests pass locally but fail in CI

**Error Message:**
```
Tests succeed on local machine but fail in GitHub Actions
Different behavior in CI environment
```

**Solution:**
```yaml
# Add debug step to compare environments
- name: Debug Environment
  run: |
    echo "Python version: $(python --version)"
    echo "Pip version: $(pip --version)"
    echo "BASE_URL: $BASE_URL"
    echo "HEADLESS: $HEADLESS"
    echo "Working directory: $(pwd)"
    pip list
    env | sort

# Ensure consistent environment
env:
  HEADLESS: true
  BASE_URL: ${{ secrets.BASE_URL }}
  API_BASE_URL: ${{ secrets.API_BASE_URL }}
  PYTHONUNBUFFERED: 1

# Use Playwright Docker image for consistency
jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: mcr.microsoft.com/playwright/python:v1.55.0
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest tests/

# Or install browsers explicitly
- name: Install Playwright browsers
  run: python -m playwright install chromium --with-deps
```

### Problem: Allure report not published to GitHub Pages

**Error Message:**
```
Allure report generation succeeds but not visible on GitHub Pages
404 on GitHub Pages URL
```

**Solution:**
```yaml
# Enable GitHub Pages in repository settings
# Go to: Settings → Pages → Source: gh-pages branch

# Ensure workflow has correct permissions
permissions:
  contents: write  # Required for gh-pages deployment
  pages: write
  id-token: write

# Fix publish step
- name: Generate Allure Report
  run: |
    allure generate allure-results -o allure-report --clean

- name: Publish to GitHub Pages
  uses: peaceiris/actions-gh-pages@v3
  if: always()  # Publish even if tests fail
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./allure-report
    keep_files: true  # Keep previous reports
    destination_dir: allure-report-${{ github.run_number }}

# Add index page for easier navigation
- name: Create index page
  run: |
    echo '<html><body><h1>Test Reports</h1>' > allure-report/index.html
    echo '<ul>' >> allure-report/index.html
    ls -d allure-report-* | sed 's#.*#<li><a href="&">& </a></li>#' >> allure-report/index.html
    echo '</ul></body></html>' >> allure-report/index.html
```

### Problem: CI workflow times out

**Error Message:**
```
The job was canceled because it exceeded the maximum execution time of 360 minutes
Job timed out
```

**Solution:**
```yaml
# Set reasonable timeout
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30  # Fail fast if tests hang

# Add test timeout
- name: Run Tests
  run: pytest --timeout=300 tests/

# Run tests in parallel
- name: Run Tests in Parallel
  run: pytest -n auto tests/

# Split tests into multiple jobs
jobs:
  test-ui:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/ui/
  
  test-api:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/api/
  
  test-integration:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/integration/
```

### Problem: Secrets not available in workflow

**Error Message:**
```
Warning: Unexpected input(s) 'secrets', valid inputs are [...]
Environment variable is empty
```

**Solution:**
```yaml
# Add secrets in repository settings
# Go to: Settings → Secrets and variables → Actions → New repository secret

# Reference secrets correctly
env:
  BASE_URL: ${{ secrets.BASE_URL }}
  API_BASE_URL: ${{ secrets.API_BASE_URL }}
  FASTAPI_MCP_TOKEN: ${{ secrets.FASTAPI_MCP_TOKEN }}

# For pull requests from forks, use environment variables
# Forks cannot access secrets for security reasons
- name: Set environment for forks
  if: github.event.pull_request.head.repo.fork
  run: |
    echo "BASE_URL=http://localhost:3000" >> $GITHUB_ENV
    echo "API_BASE_URL=http://localhost:8080" >> $GITHUB_ENV

# Or use default values
env:
  BASE_URL: ${{ secrets.BASE_URL || 'http://localhost:3000' }}
```

---

## 8. Performance and Timeout Issues

### Problem: Tests timeout in CI

**Error Message:**
```
=========================== test session starts ============================
pytest-timeout: test timed out after 300 seconds
FAILED tests/ui/test_dashboard.py::test_load_dashboard - Test exceeded timeout
```

**Solution:**
```bash
# Increase pytest timeout globally
# pytest.ini
[pytest]
timeout = 600

# Or per test
@pytest.mark.timeout(600)
def test_slow_operation():
    pass

# Optimize slow tests
# Use API for test data setup instead of UI
def test_dashboard_with_data(api_client, mcp_client):
    # ✅ Fast: Use API to create test data
    user = mcp_client.seed_user(role="admin")
    api_client.create_records(count=10)
    
    # Then test UI
    page.goto('/dashboard')
    expect(page.get_by_text('10 records')).to_be_visible()

# Run tests in parallel
pytest -n auto tests/

# Identify slow tests
pytest --durations=10
pytest --durations=0  # Show all test durations
```

### Problem: Parallel execution causes failures

**Error Message:**
```
Tests pass when run serially (-n 1) but fail with -n auto
Database locked errors
Resource conflicts
```

**Solution:**
```python
# Ensure tests use isolated browser contexts
# tests/conftest.py
@pytest.fixture(scope="function")
def browser_context(browser):
    context = browser.new_context()
    yield context
    context.close()

# Reset environment before each test
@pytest.fixture(autouse=True)
def reset_test_environment(mcp_client):
    """Reset environment before each test"""
    mcp_client.reset_env()
    yield
    # Cleanup after test if needed

# Use unique test data per test
import uuid

def test_create_user():
    email = f"user_{uuid.uuid4()}@example.com"
    # Use unique email to avoid conflicts

# Configure pytest-xdist for proper isolation
# pytest.ini
[pytest]
addopts = -n auto --dist loadscope  # Group tests by file

# Avoid shared mutable state
# ❌ Bad: Global variable
CURRENT_USER = None

# ✅ Good: Fixture that creates new instances
@pytest.fixture
def current_user(mcp_client):
    return mcp_client.seed_user()
```

### Problem: Memory leaks during test execution

**Error Message:**
```
MemoryError: Unable to allocate memory
Process killed (OOM - Out of Memory)
```

**Solution:**
```python
# Ensure proper cleanup of browser contexts
# tests/conftest.py
@pytest.fixture
def browser_context(browser):
    context = browser.new_context()
    yield context
    context.close()  # Critical: Close context after each test

# Limit number of parallel workers
pytest -n 4 tests/  # Instead of -n auto

# Close pages explicitly
@pytest.fixture
def page(browser_context):
    page = browser_context.new_page()
    yield page
    page.close()

# Monitor memory usage
import psutil
import os

def test_example():
    process = psutil.Process(os.getpid())
    print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# Clean up after session
def pytest_sessionfinish(session, exitstatus):
    """Force cleanup after all tests"""
    import gc
    gc.collect()
```

### Problem: Browser operations are slow

**Error Message:**
```
Tests take too long to complete
Browser actions are slow
```

**Solution:**
```python
# Use faster browser
# Chromium is generally fastest
# pytest.ini
[pytest]
browser = chromium

# Disable animations and transitions
context = browser.new_context(
    viewport={'width': 1920, 'height': 1080},
    reduced_motion='reduce'
)

# Use API for data setup, UI for verification only
def test_user_dashboard(api_client, page):
    # ✅ Fast: Create users via API
    for i in range(100):
        api_client.create_user(email=f"user{i}@example.com")
    
    # ❌ Slow: Would create users via UI
    # for i in range(100):
    #     page.goto('/users/new')
    #     page.fill('[name=email]', f'user{i}@example.com')
    #     page.click('button[type=submit]')
    
    # UI only for final verification
    page.goto('/users')
    expect(page.get_by_text('100 users')).to_be_visible()

# Skip non-critical waits
page.goto('/dashboard', wait_until='domcontentloaded')  # Faster than 'networkidle'
```

---

## 9. Environment Configuration Problems

### Problem: Environment variables not loaded

**Error Message:**
```
KeyError: 'BASE_URL'
os.environ['BASE_URL'] raises KeyError
```

**Solution:**
```python
# Load .env file explicitly at the top of conftest.py
# tests/conftest.py
from dotenv import load_dotenv
import os

# Load .env from project root
load_dotenv()

# Use defaults for missing variables
BASE_URL = os.getenv('BASE_URL', 'http://localhost:3000')
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8080')

# Check .env file location
# Should be in project root, not in tests/ directory
ls -la .env

# Verify environment variables are loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('BASE_URL'))"

# Debug: Print all environment variables
python -c "import os; print('\\n'.join(f'{k}={v}' for k, v in os.environ.items()))"
```

### Problem: Different behavior between environments

**Error Message:**
```
Tests pass on local machine but fail in CI
Tests pass in development but fail in staging
```

**Solution:**
```bash
# Create environment-specific .env files
.env.local
.env.ci
.env.staging
.env.production

# Load based on environment
# tests/conftest.py
import os
from dotenv import load_dotenv

env = os.getenv('TEST_ENV', 'local')
load_dotenv(f'.env.{env}')

# Run with specific environment
TEST_ENV=ci pytest tests/

# Document environment differences
# Create .env.example with all variables
cp .env .env.example
# Replace sensitive values with placeholders
sed -i 's/=.*/=REPLACE_ME/' .env.example

# Use environment variable validation
# tests/conftest.py
required_vars = ['BASE_URL', 'API_BASE_URL', 'FASTAPI_MCP_URL']
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise ValueError(f"Missing required environment variables: {missing}")
```

### Problem: Conflicting environment variables

**Error Message:**
```
Unexpected behavior due to environment variable conflicts
Wrong URL being used
```

**Solution:**
```bash
# Check for conflicting environment variables
env | grep -i url

# Unset conflicting variables
unset SOME_CONFLICTING_VAR

# Use unique variable names
# ❌ Bad: Generic names
URL=http://example.com
TOKEN=abc123

# ✅ Good: Specific names
BASE_URL=http://example.com
FASTAPI_MCP_TOKEN=abc123

# Namespace variables by component
# UI Testing
UI_BASE_URL=http://localhost:3000
# API Testing
API_BASE_URL=http://localhost:8080
# MCP Servers
FASTAPI_MCP_URL=http://localhost:8000
FASTAPI_MCP_TOKEN=secret_token
```

---

## 10. Debugging Techniques and Tools

### Enable Verbose Logging

```bash
# pytest verbose output (show test names)
pytest -v tests/

# pytest very verbose (show test docstrings)
pytest -vv tests/

# Show print statements (disable output capture)
pytest -s tests/

# Show local variables on failure
pytest -l tests/

# Playwright debug logs
DEBUG=pw:api pytest tests/

# Full Playwright debug (all channels)
DEBUG=pw:* pytest tests/

# Python logging debug level
pytest --log-cli-level=DEBUG tests/
```

### Interactive Debugging with pdb

```python
# Drop into Python debugger on failure
pytest --pdb tests/

# Drop into debugger on first failure, then exit
pytest -x --pdb tests/

# Add breakpoint in test code
def test_login(login_page):
    login_page.navigate()
    breakpoint()  # Python 3.7+ built-in debugger
    login_page.fill_email('user@example.com')

# Or use pdb.set_trace() for older Python
import pdb
pdb.set_trace()

# Useful pdb commands:
# n - next line
# s - step into function
# c - continue execution
# p variable_name - print variable
# l - show code context
# w - show stack trace
# q - quit debugger
```

### Playwright Debugging Tools

```bash
# Run with Playwright Inspector (headed mode with step-through)
PWDEBUG=1 pytest tests/ui/test_login_ui.py

# Slow down execution to see what's happening
pytest --headed --slowmo 1000 tests/

# Keep browser open after test
pytest --headed --browser chromium tests/ --browser-channel chromium

# Generate code from browser actions (Playwright Codegen)
playwright codegen https://example.com

# Record trace for debugging
pytest --tracing on tests/

# View recorded trace
playwright show-trace trace.zip

# Screenshot on every action (debug mode)
# tests/conftest.py
@pytest.fixture
def page(context):
    page = context.new_page()
    page.on("framenavigated", lambda: page.screenshot(path=f"screenshots/{time.time()}.png"))
    yield page
    page.close()
```

### Test Coverage Analysis

```bash
# Run with coverage
pytest --cov=tests --cov-report=html tests/

# Open HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Show coverage in terminal
pytest --cov=tests --cov-report=term-missing tests/

# Generate coverage badge
coverage-badge -o coverage.svg

# Check coverage percentage
pytest --cov=tests --cov-fail-under=80 tests/
```

### Profiling Test Performance

```bash
# Show 10 slowest tests
pytest --durations=10 tests/

# Show all test durations
pytest --durations=0 tests/

# Profile with py-spy (install: pip install py-spy)
py-spy record -o profile.svg -- pytest tests/

# Profile specific test
py-spy record -o profile.svg -- pytest tests/ui/test_slow.py

# Use pytest-benchmark for performance testing
@pytest.mark.benchmark
def test_performance(benchmark):
    result = benchmark(my_function)
```

### Debugging Feature Files and Step Definitions

```bash
# Show which steps are found/missing
pytest --gherkin-terminal-reporter -vv tests/features/

# Show step definition locations
pytest --gherkin-terminal-reporter --collect-only tests/features/

# Debug step definition matching
# Add print statements in step definitions
@given("the user is on the login page")
def go_to_login_page(page):
    print(f"Executing step: go_to_login_page")  # Debug output
    page.goto('/login')

# Run specific scenario
pytest -k "user can login successfully" tests/features/

# Run specific feature file
pytest tests/features/authentication.feature
```

### Network Debugging

```python
# Monitor network requests
def test_with_network_monitoring(page):
    # Log all requests
    page.on("request", lambda request: print(f">> {request.method} {request.url}"))
    
    # Log all responses
    page.on("response", lambda response: print(f"<< {response.status} {response.url}"))
    
    page.goto('/dashboard')

# Wait for specific network request
with page.expect_request("**/api/users") as request_info:
    page.get_by_role('button', name='Load Users').click()
request = request_info.value
print(f"Request headers: {request.headers}")

# Wait for response
with page.expect_response("**/api/users") as response_info:
    page.get_by_role('button', name='Load Users').click()
response = response_info.value
print(f"Response: {response.json()}")

# Mock API responses for testing
def test_with_mocked_api(page):
    # Route API calls to mock handler
    def handle_route(route):
        route.fulfill(
            status=200,
            body='{"users": [{"id": 1, "name": "Test User"}]}'
        )
    
    page.route("**/api/users", handle_route)
    page.goto('/dashboard')
```

### Debugging MCP Server Issues

```bash
# Run MCP server with debug logging
cd mcp_servers/fastapi_mcp
uvicorn main:app --reload --log-level debug

# Test MCP endpoints with curl
curl -X POST http://localhost:8000/tools/seed_user \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{"role": "admin", "email": "test@example.com"}' \
  -v  # Verbose output

# Monitor MCP server logs in real-time
tail -f mcp_server.log

# Debug Python MCP client
# tests/helpers/mcp_client.py
class MCPClient:
    def seed_user(self, role, email):
        print(f"Calling seed_user: role={role}, email={email}")
        response = self.client.post("/tools/seed_user", json={"role": role, "email": email})
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        return response.json()
```

### Debugging CI/CD Issues

```yaml
# Add debug steps in GitHub Actions
- name: Debug Info
  run: |
    echo "Runner OS: $RUNNER_OS"
    echo "Python version: $(python --version)"
    echo "Working directory: $(pwd)"
    ls -la
    env | sort
    pip list

# SSH into GitHub Actions runner (using tmate)
- name: Setup tmate session
  if: ${{ failure() }}
  uses: mxschmitt/action-tmate@v3
  timeout-minutes: 30

# Save artifacts for debugging
- name: Upload test artifacts
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: |
      allure-results/
      test-results/
      screenshots/
      traces/
      *.log
```

### General Debugging Workflow

1. **Reproduce Locally**: Try to reproduce the issue on your local machine
2. **Simplify**: Create minimal test case that demonstrates the problem
3. **Add Logging**: Add print statements or logging to understand execution flow
4. **Use Debugger**: Set breakpoints and step through code
5. **Check Documentation**: Review docs for correct usage
6. **Search Issues**: Look for similar issues in GitHub/StackOverflow
7. **Isolate**: Run test in isolation to rule out interaction with other tests
8. **Compare Environments**: Check for differences between working and failing environments

---

## Getting Additional Help

If you've tried the troubleshooting steps above and still need assistance:

### Internal Resources

- **Getting Started Guide**: [docs/getting_started.md](getting_started.md) - Setup and installation instructions
- **Architecture Overview**: [docs/architecture.md](architecture.md) - System design and components
- **Writing Tests Guide**: [docs/writing_tests.md](writing_tests.md) - Test authoring best practices
- **MCP Servers Documentation**: [docs/mcp_servers.md](mcp_servers.md) - MCP server configuration and usage
- **CI/CD Documentation**: [docs/ci_cd.md](ci_cd.md) - GitHub Actions pipeline details

### External Documentation

- **Playwright Python**: https://playwright.dev/python/
  - API reference, guides, and best practices
- **pytest Documentation**: https://docs.pytest.org/
  - Test framework features and plugins
- **pytest-bdd**: https://pytest-bdd.readthedocs.io/
  - BDD/Gherkin integration for pytest
- **FastAPI**: https://fastapi.tiangolo.com/
  - MCP server framework documentation
- **Allure Report**: https://docs.qameta.io/allure/
  - Reporting framework documentation

### Community Support

- **GitHub Issues**: Search or create issues in the project repository
- **Playwright Discord**: https://aka.ms/playwright/discord
- **pytest Discord**: https://discord.com/invite/pytest-dev

### Creating a Good Bug Report

When reporting issues, include:

1. **Environment Information**:
   ```bash
   python --version
   pip list
   echo $BASE_URL
   cat pytest.ini
   ```

2. **Minimal Reproduction**:
   - Simplest test case that demonstrates the problem
   - Steps to reproduce
   - Expected vs actual behavior

3. **Logs and Screenshots**:
   - Error messages (full stack traces)
   - pytest output with `-vv` flag
   - Screenshots or videos of the issue
   - Playwright traces if UI-related

4. **What You've Tried**:
   - List troubleshooting steps already attempted
   - Any workarounds discovered

---

**Last Updated**: 2024
**Framework Version**: 1.0.0
**Maintained By**: Test Automation Team
