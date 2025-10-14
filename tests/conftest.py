"""
Pytest configuration and shared fixtures for the test automation framework.

This module provides:
- Playwright browser and page fixtures with per-test isolation
- httpx API client fixtures with base URL configuration
- Allure reporting enhancements
- Environment configuration loading
"""

import os
from typing import Generator

import httpx
import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

# Load environment variables from .env file
load_dotenv()


# ==============================================================================
# Configuration Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def base_url() -> str:
    """
    Get the base URL for the web application.
    
    Returns:
        str: Base URL from environment or default localhost
    """
    return os.getenv("BASE_URL", "http://localhost:3000")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """
    Get the base URL for the API.
    
    Returns:
        str: API base URL from environment or default localhost
    """
    return os.getenv("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def headless() -> bool:
    """
    Determine if browser should run in headless mode.
    
    Returns:
        bool: True for headless mode, False for headed
    """
    return os.getenv("HEADLESS", "true").lower() == "true"


# ==============================================================================
# Playwright Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def browser_type_launch_args(headless: bool) -> dict:
    """
    Configure browser launch arguments.
    
    Args:
        headless: Whether to run browser in headless mode
        
    Returns:
        dict: Browser launch arguments
    """
    return {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
        ],
    }


@pytest.fixture(scope="session")
def browser_context_args() -> dict:
    """
    Configure browser context arguments for enhanced stability.
    
    Returns:
        dict: Browser context arguments
    """
    return {
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
        "java_script_enabled": True,
    }


@pytest.fixture(scope="function")
def context(
    browser: Browser,
    browser_context_args: dict,
) -> Generator[BrowserContext, None, None]:
    """
    Create a new browser context for each test (ensures isolation).
    
    This fixture provides a fresh browser context per test, which is critical
    for parallel execution and test isolation.
    
    Args:
        browser: Playwright browser instance
        browser_context_args: Context configuration
        
    Yields:
        BrowserContext: Isolated browser context for the test
    """
    context = browser.new_context(**browser_context_args)
    
    # Enable tracing for debugging
    if os.getenv("CAPTURE_TRACE", "true").lower() == "true":
        context.tracing.start(screenshots=True, snapshots=True, sources=True)
    
    yield context
    
    # Save trace on test failure
    if os.getenv("CAPTURE_TRACE", "true").lower() == "true":
        context.tracing.stop(path="test-results/trace.zip")
    
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """
    Create a new page within the browser context.
    
    Args:
        context: Browser context for this test
        
    Yields:
        Page: Fresh page for the test
    """
    page = context.new_page()
    
    # Set default timeouts from environment
    navigation_timeout = int(os.getenv("NAVIGATION_TIMEOUT", "30000"))
    page.set_default_navigation_timeout(navigation_timeout)
    page.set_default_timeout(int(os.getenv("REQUEST_TIMEOUT", "30000")))
    
    yield page
    
    # Cleanup
    page.close()


# ==============================================================================
# API Client Fixtures
# ==============================================================================


@pytest.fixture(scope="function")
def api_client(api_base_url: str) -> Generator[httpx.Client, None, None]:
    """
    Create an httpx client for API testing.
    
    Args:
        api_base_url: Base URL for API requests
        
    Yields:
        httpx.Client: HTTP client configured for API testing
    """
    timeout = httpx.Timeout(float(os.getenv("REQUEST_TIMEOUT", "30000")) / 1000)
    
    with httpx.Client(
        base_url=api_base_url,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        yield client


@pytest.fixture(scope="function")
async def async_api_client(api_base_url: str):
    """
    Create an async httpx client for API testing.
    
    Args:
        api_base_url: Base URL for API requests
        
    Yields:
        httpx.AsyncClient: Async HTTP client configured for API testing
    """
    timeout = httpx.Timeout(float(os.getenv("REQUEST_TIMEOUT", "30000")) / 1000)
    
    async with httpx.AsyncClient(
        base_url=api_base_url,
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        yield client


# ==============================================================================
# API Client Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def admin_token() -> str:
    """
    Get admin authentication token for API tests.
    
    Returns:
        str: Admin bearer token from environment or test default
    """
    return os.getenv("ADMIN_TOKEN", "test-admin-token-placeholder")


@pytest.fixture(scope="function")
def auth_api(api_base_url: str):
    """
    Authentication API client fixture for login, logout, and token management.
    
    Per Agent Action Plan Section 0.4.1: Provides typed API client for authentication
    endpoints with Pydantic model validation and Allure reporting integration.
    
    Args:
        api_base_url: Base URL for the API from environment
    
    Returns:
        AuthAPIClient: Configured authentication API client instance
    """
    from tests.api_clients.auth_client import AuthAPIClient
    return AuthAPIClient(base_url=api_base_url)


@pytest.fixture(scope="function")
def users_api(api_base_url: str, admin_token: str):
    """
    User management API client fixture with admin authentication.
    
    Args:
        api_base_url: Base URL for the API from environment
        admin_token: Admin bearer token for authentication
    
    Returns:
        UsersAPIClient: Configured users API client instance
    """
    from tests.api_clients.users_client import UsersAPIClient
    return UsersAPIClient(base_url=api_base_url, auth_token=admin_token)


@pytest.fixture(scope="function")
def mcp_client() -> "MCPClient":
    """
    MCP (Model Context Protocol) client fixture for deterministic test data generation.
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    
    Returns:
        MCPClient: Configured MCP client for test data operations
    """
    from tests.helpers.mcp_client import MCPClient
    
    mcp_base_url = os.getenv("FASTAPI_MCP_URL", "http://localhost:8000")
    mcp_token = os.getenv("FASTAPI_MCP_TOKEN", "test-mcp-token")
    
    return MCPClient(base_url=mcp_base_url, token=mcp_token)


# ==============================================================================
# Pytest Hooks for Enhanced Reporting
# ==============================================================================


def pytest_configure(config):
    """
    Configure pytest with custom markers and settings.
    
    Args:
        config: Pytest configuration object
    """
    # Add custom markers (defined in pytest.ini)
    config.addinivalue_line(
        "markers", "ui: UI tests using Playwright"
    )
    config.addinivalue_line(
        "markers", "api: API tests using httpx"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "smoke: Smoke tests for critical paths"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer to execute"
    )


def pytest_runtest_makereport(item, call):
    """
    Hook to capture test failures and attach screenshots.
    
    Args:
        item: Test item
        call: Test call phase
    """
    if call.when == "call" and call.excinfo is not None:
        # Test failed, try to capture screenshot
        if hasattr(item, "funcargs") and "page" in item.funcargs:
            page = item.funcargs["page"]
            if os.getenv("CAPTURE_SCREENSHOT_ON_FAILURE", "true").lower() == "true":
                screenshot_path = f"test-results/{item.nodeid.replace('::', '_')}_failure.png"
                os.makedirs("test-results", exist_ok=True)
                try:
                    page.screenshot(path=screenshot_path)
                except Exception:
                    # Ignore screenshot failures
                    pass
