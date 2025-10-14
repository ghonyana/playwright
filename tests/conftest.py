"""
Pytest Configuration and Shared Fixtures for Test Automation Framework

This module provides the central pytest configuration per Agent Action Plan Section 0.4.1
and user directive: "Keep tests deterministic, isolated, and parallel-friendly (new context per test)"

Core Capabilities:
------------------
1. Playwright Browser Fixtures: Session-scoped browser with function-scoped context/page
   ensuring per-test isolation for parallel execution without state leakage

2. httpx API Client Fixtures: Configured sync and async HTTP clients with
   API_BASE_URL from environment for API testing

3. MCP Client Fixture: FastAPI MCP server client for deterministic test data management
   per user directive: "Use MCP tools for data/state (don't hard-code test data)"

4. Page Object Fixtures: Pre-configured LoginPage and DashboardPage instances
   injecting Playwright page fixture for UI testing with stable ARIA locators

5. API Client Fixtures: AuthAPIClient and UsersAPIClient instances with typed
   request/response validation via Pydantic models

6. Allure Reporting Configuration: Environment metadata capture, test categorization,
   automatic screenshot on failure, and test execution diagnostics

7. pytest-bdd Configuration: Feature file base directory setup for Gherkin scenario
   discovery and step definition mapping

8. Test Isolation Hooks: Optional environment reset per test via MCP server
   configurable through RESET_ENV_PER_TEST environment variable

Environment Variables:
---------------------
BASE_URL: Web application base URL (default: http://localhost:3000)
API_BASE_URL: REST API endpoint base URL (default: http://localhost:3000/api)
HEADLESS: Browser headless mode (default: true)
FASTAPI_MCP_URL: FastAPI MCP server URL (default: http://localhost:8000)
FASTAPI_MCP_TOKEN: MCP server authentication token (required in CI)
RESET_ENV_PER_TEST: Reset environment before each test (default: false)
CAPTURE_TRACE: Enable Playwright trace collection (default: true)
NAVIGATION_TIMEOUT: Page navigation timeout in ms (default: 30000)

Integration Points:
------------------
Per Agent Action Plan Section 0.4:
- tests/helpers/mcp_client.py: MCPClient for test data management
- tests/pages/login_page.py: LoginPage for authentication UI testing
- tests/pages/dashboard_page.py: DashboardPage for main app UI testing
- tests/api_clients/auth_client.py: AuthAPIClient for authentication API testing
- tests/api_clients/users_client.py: UsersAPIClient for user management API testing
"""

import os
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Generator

import allure
import httpx
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

# Load environment variables from .env file at pytest startup
# Per Agent Action Plan Section 0.4.8: "Environment Configuration Integration"
load_dotenv()


# ==============================================================================
# pytest-bdd Configuration
# ==============================================================================

# Feature file base directory for pytest-bdd scenario discovery
# Per Agent Action Plan Section 0.4.1: "pytest Configuration Integration"
pytest_bdd_feature_base_dir = Path(__file__).parent / "features"


# ==============================================================================
# Configuration Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def base_url() -> str:
    """
    Get the base URL for the web application.
    
    Per user directive: "Base URLs via env: BASE_URL, API_BASE_URL"
    
    Returns:
        str: Base URL from BASE_URL environment variable or default localhost
    
    Example:
        export BASE_URL=https://staging.example.com
    """
    return os.getenv("BASE_URL", "http://localhost:3000")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """
    Get the base URL for the REST API.
    
    Per user directive: "Base URLs via env: BASE_URL, API_BASE_URL"
    
    Returns:
        str: API base URL from API_BASE_URL environment variable or default localhost
    
    Example:
        export API_BASE_URL=https://api.staging.example.com
    """
    return os.getenv("API_BASE_URL", "http://localhost:3000/api")


# ==============================================================================
# Playwright Browser Fixtures with Per-Test Context Isolation
# ==============================================================================
# Per user directive: "Keep tests deterministic, isolated, and parallel-friendly
# (new context per test)"
#
# Critical Architecture:
# - browser: Session-scoped (shared across all tests, expensive to create)
# - browser_context: Function-scoped (NEW CONTEXT PER TEST - prevents state leakage)
# - page: Function-scoped (new page in isolated context)
#
# This ensures parallel tests don't interfere with each other's:
# - Cookies and local storage
# - Cache and session data
# - Network request state
# - Browser permissions and preferences


@pytest.fixture(scope="session")
def browser_type_launch_args() -> dict[str, Any]:
    """
    Configure Playwright browser launch arguments.
    
    Per user directive: "HEADLESS=true" environment variable controls headless mode
    
    Returns:
        dict[str, Any]: Browser launch configuration including:
            - headless: From HEADLESS env var (default: true)
            - slow_mo: Milliseconds to slow down operations (default: 0, useful for debugging)
    
    Example:
        export HEADLESS=false  # For local debugging with visible browser
        export SLOW_MO=100     # Slow down by 100ms per action
    """
    return {
        "headless": os.getenv("HEADLESS", "true").lower() == "true",
        "slow_mo": int(os.getenv("SLOW_MO", "0")),
        "args": [
            "--disable-blink-features=AutomationControlled",  # Avoid detection
        ],
    }


@pytest.fixture(scope="session")
def browser(playwright: Playwright, browser_type_launch_args: dict[str, Any]) -> Generator[Browser, None, None]:
    """
    Create session-scoped Playwright browser instance.
    
    Session scope is optimal because browser launch is expensive (~1-2 seconds)
    and sharing the browser process across tests is safe when contexts are isolated.
    
    Per Agent Action Plan Section 0.4.1: "Session-scoped browser launch"
    
    Args:
        playwright: Playwright instance from pytest-playwright plugin
        browser_type_launch_args: Launch configuration from fixture
    
    Yields:
        Browser: Chromium browser instance (can be configured for Firefox/WebKit)
    
    Note:
        To change browser type, modify this fixture:
        browser = playwright.chromium.launch(**browser_type_launch_args)  # Current
        browser = playwright.firefox.launch(**browser_type_launch_args)   # Alternative
    """
    browser = playwright.chromium.launch(**browser_type_launch_args)
    yield browser
    browser.close()


@pytest.fixture
def browser_context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """
    Create function-scoped browser context for EACH TEST.
    
    ✓ CRITICAL: This is the KEY fixture ensuring test isolation per user directive:
    "Keep tests deterministic, isolated, and parallel-friendly (new context per test)"
    
    Function scope (NOT session/module) ensures:
    - Each test gets a fresh context with clean cookies/storage/cache
    - No state leakage between parallel test executions
    - Tests can run in any order without dependencies
    - Parallel execution with pytest-xdist works correctly
    
    Per Agent Action Plan Section 0.4.1: "Function-scoped context ensures no state leakage"
    
    Args:
        browser: Session-scoped browser instance
    
    Yields:
        BrowserContext: Isolated browser context with:
            - Clean cookies and local storage
            - Fresh cache
            - Default viewport size (1920x1080)
            - HTTPS error ignoring for local testing
            - Optional trace collection for debugging
    
    Example:
        def test_login(browser_context):
            # This context is ISOLATED from all other tests
            page = browser_context.new_page()
            # Test execution with clean state
    """
    # Create fresh context with sensible defaults
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True,  # Allow self-signed certs in test environments
        java_script_enabled=True,
    )
    
    # Enable Playwright trace collection for debugging test failures
    # Traces include screenshots, DOM snapshots, and network activity
    if os.getenv("CAPTURE_TRACE", "true").lower() == "true":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    
    yield context
    
    # Save trace to test-results/ directory for post-mortem analysis
    if os.getenv("CAPTURE_TRACE", "true").lower() == "true":
        try:
            os.makedirs("test-results", exist_ok=True)
            context.tracing.stop(path="test-results/trace.zip")
        except Exception:
            # Don't fail test if trace saving fails
            pass
    
    # Clean up context resources
    context.close()


@pytest.fixture
def page(browser_context: BrowserContext) -> Generator[Page, None, None]:
    """
    Create function-scoped page within isolated browser context.
    
    Each test receives a fresh page in a fresh context, ensuring complete isolation.
    The page is pre-configured with timeouts from environment variables.
    
    Per Agent Action Plan Section 0.4.1: "New page in isolated context"
    
    Args:
        browser_context: Function-scoped browser context from fixture
    
    Yields:
        Page: Playwright page instance with configured timeouts:
            - Navigation timeout: NAVIGATION_TIMEOUT env var (default: 30000ms)
            - Default timeout: REQUEST_TIMEOUT env var (default: 30000ms)
    
    Example:
        def test_navigation(page):
            page.goto("https://example.com")  # Uses NAVIGATION_TIMEOUT
            page.locator("button").click()    # Uses REQUEST_TIMEOUT
    """
    page = browser_context.new_page()
    
    # Configure timeouts from environment
    navigation_timeout = int(os.getenv("NAVIGATION_TIMEOUT", "30000"))
    request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30000"))
    
    page.set_default_navigation_timeout(navigation_timeout)
    page.set_default_timeout(request_timeout)
    
    yield page
    
    # Page cleanup (context.close() will also clean up, but explicit is better)
    page.close()


# ==============================================================================
# httpx HTTP Client Fixtures for API Testing
# ==============================================================================
# Per Agent Action Plan Section 0.4.1: "httpx client fixtures configured with
# BASE_URL and API_BASE_URL"


@pytest.fixture
def api_client(api_base_url: str) -> Generator[httpx.Client, None, None]:
    """
    Create synchronous httpx client for API testing.
    
    Per Agent Action Plan Section 0.4.3: "httpx client with base URLs"
    
    This fixture provides a pre-configured HTTP client with:
    - Base URL from API_BASE_URL environment variable
    - Timeout configuration from REQUEST_TIMEOUT
    - Automatic redirect following
    - Connection pooling for performance
    
    Args:
        api_base_url: API base URL from fixture (API_BASE_URL env var)
    
    Yields:
        httpx.Client: Configured HTTP client for API testing
    
    Example:
        def test_api_endpoint(api_client):
            response = api_client.get("/users")
            assert response.status_code == 200
    """
    # Convert milliseconds to seconds for httpx timeout
    timeout_seconds = float(os.getenv("REQUEST_TIMEOUT", "30000")) / 1000
    timeout = httpx.Timeout(timeout_seconds)
    
    client = httpx.Client(
        base_url=api_base_url,
        timeout=timeout,
        follow_redirects=True,
        # Connection pool limits for parallel test execution
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    
    yield client
    
    # Ensure client is closed to release connection pool resources
    client.close()


@pytest.fixture
async def async_api_client(api_base_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    Create asynchronous httpx client for async API testing.
    
    Per Agent Action Plan Section 0.4.1: "Async httpx client for async tests"
    
    This fixture provides an async HTTP client for tests using pytest-asyncio.
    Useful for testing async API endpoints or running concurrent API calls.
    
    Args:
        api_base_url: API base URL from fixture (API_BASE_URL env var)
    
    Yields:
        httpx.AsyncClient: Configured async HTTP client
    
    Example:
        @pytest.mark.asyncio
        async def test_async_api(async_api_client):
            response = await async_api_client.get("/users")
            assert response.status_code == 200
    """
    timeout_seconds = float(os.getenv("REQUEST_TIMEOUT", "30000")) / 1000
    timeout = httpx.Timeout(timeout_seconds)
    
    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=timeout,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    ) as client:
        yield client


# ==============================================================================
# MCP Client Fixture for Deterministic Test Data Management
# ==============================================================================
# Per user directive: "Use MCP tools for data/state (don't hard-code test data)"


@pytest.fixture(scope="session")
def mcp_client() -> Generator[Any, None, None]:
    """
    MCP (Model Context Protocol) client fixture for deterministic test data management.
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    Per Agent Action Plan Section 0.4.2: "MCP Client Integration Pattern"
    
    This fixture provides access to the FastAPI MCP server tools:
    - seed_user: Create test users with unique, non-conflicting emails
    - build_payload: Generate API request bodies from templates
    - reset_env: Reset test environment to known-good state
    - query_state: Inspect current test data for verification
    
    Session scope is appropriate because:
    - MCP client can be shared across all tests (stateless)
    - Expensive connection setup done once
    - Each MCP operation is independent and thread-safe
    
    Environment Variables:
        FASTAPI_MCP_URL: MCP server base URL (default: http://localhost:8000)
        FASTAPI_MCP_TOKEN: Authentication token (REQUIRED in CI)
    
    Returns:
        MCPClient: Configured MCP client instance with health check validation
    
    Raises:
        ValueError: If FASTAPI_MCP_TOKEN not set
        httpx.ConnectError: If MCP server unavailable
    
    Example:
        def test_with_seeded_user(mcp_client):
            # Create test user via MCP (not hardcoded)
            user = mcp_client.seed_user(role="customer")
            assert user['email']  # Auto-generated unique email
            
        def test_with_api_payload(mcp_client, api_client):
            # Generate request payload via MCP
            payload = mcp_client.build_payload("create_user", {"role": "admin"})
            response = api_client.post("/users", json=payload)
            assert response.status_code == 201
    """
    from tests.helpers.mcp_client import get_mcp_client
    
    # Use factory function which validates configuration and performs health check
    # Per Agent Action Plan Section 0.4.2: "Verify server availability"
    client = get_mcp_client()
    
    yield client
    
    # Clean up HTTP client connection pool
    client.close()


# ==============================================================================
# Typed API Client Fixtures
# ==============================================================================
# Per Agent Action Plan Section 0.4.3: "API Clients → httpx Client"


@pytest.fixture
def auth_api(api_base_url: str) -> Any:
    """
    Authentication API client fixture for login, logout, and token management.
    
    Per Agent Action Plan Section 0.4.3: "AuthAPIClient for auth_api pytest fixture"
    
    Provides typed API client with Pydantic model validation for:
    - login: User authentication with email/password
    - logout: Session termination
    - refresh_token: JWT token refresh
    - request_password_reset: Password recovery initiation
    - verify_token: Token validity checking
    
    All methods include:
    - Automatic Allure step annotations
    - Request/response logging
    - Type-safe validation
    - Descriptive error messages
    
    Args:
        api_base_url: API base URL from fixture (API_BASE_URL env var)
    
    Returns:
        AuthAPIClient: Configured authentication API client
    
    Example:
        def test_login_flow(auth_api, mcp_client):
            # Seed test user via MCP
            user = mcp_client.seed_user(role="customer")
            
            # Login with typed API client
            response = auth_api.login(user['email'], user['password'])
            assert response.access_token
            assert response.user_id == user['id']
    """
    from tests.api_clients.auth_client import AuthAPIClient
    
    return AuthAPIClient(base_url=api_base_url)


@pytest.fixture
def users_api(api_base_url: str) -> Any:
    """
    User management API client fixture for CRUD operations.
    
    Per Agent Action Plan Section 0.4.3: "UsersAPIClient for users_api pytest fixture"
    
    Provides typed API client with Pydantic model validation for:
    - create_user: User account creation
    - get_user: Retrieve user by ID
    - list_users: Paginated user listing with filters
    - update_user: User data modification
    - delete_user: User account removal
    - search_users: User search by query
    - activate_user/deactivate_user: Account status management
    
    All methods include:
    - Automatic Allure step annotations
    - Request/response validation
    - Type-safe parameters
    - Integration with MCP build_payload
    
    Args:
        api_base_url: API base URL from fixture (API_BASE_URL env var)
    
    Returns:
        UsersAPIClient: Configured users API client
    
    Example:
        def test_user_crud(users_api, mcp_client):
            # Generate payload via MCP
            payload = mcp_client.build_payload("create_user", {"role": "admin"})
            
            # Create user with typed client
            user = users_api.create_user(CreateUserRequest(**payload))
            assert user.id
            
            # Retrieve created user
            retrieved = users_api.get_user(user.id)
            assert retrieved.email == user.email
    """
    from tests.api_clients.users_client import UsersAPIClient
    
    # Note: Authentication handled per test via auth_api.login() or MCP seed_user token
    return UsersAPIClient(base_url=api_base_url)


# ==============================================================================
# Page Object Fixtures
# ==============================================================================
# Per Agent Action Plan Section 0.4.1: "Page object fixtures that inject browser contexts"


@pytest.fixture
def login_page(page: Page) -> Any:
    """
    LoginPage fixture with injected Playwright page instance.
    
    Per Agent Action Plan Section 0.4.2: "Step Definitions → Page Objects"
    
    Provides LoginPage instance for authentication UI testing with:
    - Stable ARIA-based locators per user directive
    - High-level business methods (navigate_to_login, login, verify_error_message)
    - Automatic Allure step annotations
    - Integration with MCP-seeded test users
    
    Args:
        page: Function-scoped Playwright page from fixture
    
    Returns:
        LoginPage: Configured login page object
    
    Example:
        def test_valid_login(login_page, mcp_client):
            user = mcp_client.seed_user(role="customer")
            login_page.navigate_to_login()
            login_page.login(user['email'], user['password'])
            login_page.verify_successful_login()
    """
    from tests.pages.login_page import LoginPage
    
    return LoginPage(page)


@pytest.fixture
def dashboard_page(page: Page) -> Any:
    """
    DashboardPage fixture with injected Playwright page instance.
    
    Per Agent Action Plan Section 0.4.2: "Step Definitions → Page Objects"
    
    Provides DashboardPage instance for main application UI testing with:
    - Stable ARIA-based locators
    - High-level navigation methods
    - User menu and logout interactions
    - Section navigation capabilities
    
    Args:
        page: Function-scoped Playwright page from fixture
    
    Returns:
        DashboardPage: Configured dashboard page object
    
    Example:
        def test_dashboard_navigation(dashboard_page):
            dashboard_page.navigate_to_dashboard()
            dashboard_page.verify_dashboard_loaded()
            welcome = dashboard_page.get_welcome_message()
            assert "Welcome" in welcome
    """
    from tests.pages.dashboard_page import DashboardPage
    
    return DashboardPage(page)


# ==============================================================================
# Allure Reporting Configuration and Environment Metadata
# ==============================================================================
# Per Agent Action Plan Section 0.4.6: "pytest → Allure Data Collection"


@pytest.fixture(scope="session", autouse=True)
def configure_allure_environment() -> None:
    """
    Configure Allure environment metadata for test reports.
    
    Per Agent Action Plan Section 0.4.1: "Allure environment configuration"
    
    This fixture automatically captures test environment information and attaches
    it to Allure reports. Useful for debugging test failures and understanding
    test execution context.
    
    Information captured:
    - BASE_URL: Web application URL
    - API_BASE_URL: REST API endpoint URL
    - Browser type and version
    - Python version
    - Headless mode setting
    - MCP server URL
    
    This fixture runs once per test session (autouse=True) to attach
    environment metadata visible in Allure report overview.
    
    Example Allure report attachment:
        BASE_URL: https://staging.example.com
        API_BASE_URL: https://api.staging.example.com
        Browser: chromium
        Headless: true
        Python: 3.11.5
        MCP Server: http://localhost:8000
    """
    # Build environment info string
    environment_info = f"""BASE_URL: {os.getenv('BASE_URL', 'http://localhost:3000')}
API_BASE_URL: {os.getenv('API_BASE_URL', 'http://localhost:3000/api')}
Browser: chromium
Headless: {os.getenv('HEADLESS', 'true')}
Python: {sys.version.split()[0]}
MCP Server: {os.getenv('FASTAPI_MCP_URL', 'http://localhost:8000')}
Capture Trace: {os.getenv('CAPTURE_TRACE', 'true')}
Navigation Timeout: {os.getenv('NAVIGATION_TIMEOUT', '30000')}ms
Request Timeout: {os.getenv('REQUEST_TIMEOUT', '30000')}ms"""
    
    # Attach to Allure report
    allure.attach(
        environment_info,
        name="Test Environment Configuration",
        attachment_type=allure.attachment_type.TEXT
    )


# ==============================================================================
# Test Isolation Hook with Optional Environment Reset
# ==============================================================================
# Per Agent Action Plan Section 0.4.1: "Test isolation ensuring deterministic execution"


@pytest.fixture(autouse=True)
def test_isolation(mcp_client: Any) -> Generator[None, None, None]:
    """
    Optional test isolation hook that resets environment before each test.
    
    Per user directive: "Keep tests deterministic, isolated, and parallel-friendly"
    Per Agent Action Plan Section 0.4.2: "Environment state reset via MCP"
    
    This fixture optionally resets the test environment to a known-good state
    before each test execution. Controlled by RESET_ENV_PER_TEST environment
    variable (default: false).
    
    When enabled (RESET_ENV_PER_TEST=true), MCP server performs:
    - Truncate test database tables
    - Reset sequences and auto-increment counters
    - Seed default/required data (system admin, configurations)
    - Clear caches and temporary storage
    
    Args:
        mcp_client: Session-scoped MCP client fixture
    
    Warning:
        Environment reset is EXPENSIVE (2-5 seconds per test). Only enable when:
        - Tests have order dependencies (bad practice, but legacy codebases)
        - Debugging mysterious state-related failures
        - Validating environment reset functionality itself
        
        For most tests, prefer:
        - Using unique test data from mcp_client.seed_user()
        - Isolated browser contexts (already provided)
        - Stateless test design
    
    Example:
        # Enable environment reset for debugging
        export RESET_ENV_PER_TEST=true
        pytest tests/
    """
    # Check if environment reset is enabled
    if os.getenv("RESET_ENV_PER_TEST", "false").lower() == "true":
        try:
            with allure.step("Reset test environment via MCP"):
                reset_result = mcp_client.reset_env()
                allure.attach(
                    f"Environment reset: {reset_result.get('status', 'unknown')}",
                    name="Environment Reset Status",
                    attachment_type=allure.attachment_type.TEXT
                )
        except Exception as e:
            # Log warning but don't fail test - environment reset is best-effort
            allure.attach(
                f"Warning: Environment reset failed: {str(e)}",
                name="Environment Reset Warning",
                attachment_type=allure.attachment_type.TEXT
            )
    
    # Yield to run the actual test
    yield
    
    # Post-test cleanup (if needed in future)
    pass


# ==============================================================================
# Pytest Hooks for Enhanced Reporting and Test Execution
# ==============================================================================


def pytest_configure(config: Any) -> None:
    """
    Configure pytest with custom markers and settings.
    
    Per Agent Action Plan Section 0.4.6: "Allure report customization hooks"
    
    This hook runs once at pytest startup to register custom markers for
    test categorization and filtering.
    
    Args:
        config: Pytest configuration object
    
    Registered Markers:
        @pytest.mark.ui: UI tests using Playwright
        @pytest.mark.api: API tests using httpx
        @pytest.mark.integration: Integration tests spanning multiple layers
        @pytest.mark.smoke: Smoke tests for critical paths (CI priority)
        @pytest.mark.slow: Tests that take >30 seconds to execute
    
    Example:
        @pytest.mark.ui
        @pytest.mark.smoke
        def test_login_flow(login_page):
            # Critical UI smoke test
            pass
        
        # Run only smoke tests:
        pytest -m smoke
        
        # Run UI tests excluding slow ones:
        pytest -m "ui and not slow"
    """
    config.addinivalue_line(
        "markers", "ui: UI tests using Playwright for web interface testing"
    )
    config.addinivalue_line(
        "markers", "api: API tests using httpx for REST API testing"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests spanning multiple system layers"
    )
    config.addinivalue_line(
        "markers", "smoke: Smoke tests for critical paths (high priority in CI)"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than 30 seconds to execute"
    )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: Any, call: Any) -> Generator[None, None, None]:
    """
    Pytest hook to capture test failures and attach diagnostic information.
    
    Per Agent Action Plan Section 0.4.6: "Allure hooks capture test metadata"
    
    This hook runs after each test phase (setup, call, teardown) and captures
    screenshots and diagnostic information on test failures.
    
    For UI tests with Playwright page fixture, automatically captures:
    - Screenshot of failure state
    - Page URL at time of failure
    - Console logs (if available)
    
    All captures are attached to Allure reports for debugging.
    
    Args:
        item: Pytest test item
        call: Test call phase information
    
    Yields:
        Test execution outcome
    """
    # Execute test and get outcome
    outcome = yield
    report = outcome.get_result()  # type: ignore[attr-defined]
    
    # Only process test failures in the "call" phase (not setup/teardown)
    if report.when == "call" and report.failed:
        # Check if test uses Playwright page fixture
        if "page" in item.funcargs:
            page = item.funcargs["page"]
            
            # Capture screenshot on failure (if enabled)
            if os.getenv("CAPTURE_SCREENSHOT_ON_FAILURE", "true").lower() == "true":
                try:
                    screenshot_bytes = page.screenshot(full_page=True)
                    allure.attach(
                        screenshot_bytes,
                        name=f"Failure Screenshot - {item.name}",
                        attachment_type=allure.attachment_type.PNG
                    )
                except Exception as e:
                    # Log failure but don't crash test reporting
                    allure.attach(
                        f"Failed to capture screenshot: {str(e)}",
                        name="Screenshot Capture Error",
                        attachment_type=allure.attachment_type.TEXT
                    )
            
            # Attach current URL
            try:
                current_url = page.url
                allure.attach(
                    current_url,
                    name="Current URL at Failure",
                    attachment_type=allure.attachment_type.TEXT
                )
            except Exception:
                pass
            
            # Attach page HTML source for debugging
            try:
                page_source = page.content()
                allure.attach(
                    page_source,
                    name="Page HTML Source at Failure",
                    attachment_type=allure.attachment_type.HTML
                )
            except Exception:
                pass
