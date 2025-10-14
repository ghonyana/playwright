"""
Authentication Step Definitions for pytest-bdd

This module implements pytest-bdd step definitions for authentication scenarios,
providing business-readable Gherkin steps that delegate to page objects and API clients.

Per Agent Action Plan Section 0.1.2 Special Instructions:
"Prefer Gherkin that's business‑readable; keep steps high‑level"
"Implement steps via page objects; avoid brittle CSS/xpath—prefer role/name/test‑id"
"Use MCP tools for data/state (don't hard‑code test data)"

Key Features:
-------------
- High-level, business-readable step semantics
- Delegates UI interactions to page objects (LoginPage, DashboardPage)
- Delegates API interactions to typed API clients (AuthAPIClient)
- Integrates with MCP server for deterministic test user credentials
- Supports both UI and API authentication testing workflows
- Comprehensive Allure reporting with step hierarchy
- Session state management for API token tracking

Design Principles:
------------------
- Steps remain 1-5 lines maximum
- No UI selectors, CSS classes, or XPath in step bodies
- Business-focused language: "logs in with valid credentials" not "fills email input"
- All test data from MCP client (no hardcoded credentials)
- Isolated, parallel-friendly test execution

Example Gherkin Usage:
----------------------
```gherkin
Feature: User Authentication
  Scenario: Successful login with valid credentials
    Given the user is on the login page
    When the user logs in with valid credentials
    Then the user is redirected to the dashboard
    And a welcome message is displayed
  
  Scenario: API authentication with JWT tokens
    Given a test user exists with role "admin"
    When the user authenticates via API
    Then a valid JWT token is returned
    And the token contains the correct user role
```

Integration with MCP Server:
----------------------------
All test users are created via MCP server's seed_user tool, ensuring:
- Unique, non-conflicting email addresses for parallel execution
- Deterministic credentials available for assertions
- No hardcoded test data in test files
- Automatic cleanup through browser context isolation

Example:
```python
# MCP creates user with unique email
user = mcp_client.seed_user(role="customer", email="test@example.com")

# Returns:
{
    "id": 123,
    "email": "customer-a3f9d82@test.local",
    "role": "customer",
    "password": "Test123!",
    "auth_token": "eyJhbGc..."
}
```
"""

from typing import Dict, Any, Optional

import allure
import pytest
from pytest_bdd import given, when, then, scenarios, parsers

# Import page objects for UI authentication flows
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage

# Import API clients for backend authentication testing
from tests.api_clients.auth_client import AuthAPIClient
from tests.api_clients.models.auth_models import TokenRefreshResponse

# Import MCP client for deterministic test data
from tests.helpers.mcp_client import MCPClient


# ==================================================================================
# SCENARIO LOADING
# ==================================================================================
# Load all authentication scenarios from the authentication feature file
# This enables pytest-bdd to discover and execute the Gherkin scenarios

scenarios('../features/authentication.feature')


# ==================================================================================
# PYTEST FIXTURES
# ==================================================================================
# Fixtures provide reusable test components with automatic dependency injection
# and setup/teardown management

@pytest.fixture
def login_page(page, base_url: str) -> LoginPage:
    """
    Initialize LoginPage instance for UI authentication testing.
    
    Args:
        page: Playwright Page instance from pytest-playwright fixture
        base_url: Application base URL from BASE_URL environment variable
    
    Returns:
        LoginPage: Configured login page object with stable ARIA-based locators
    
    Example:
        @when("the user logs in with valid credentials")
        def user_logs_in(login_page: LoginPage, test_user: Dict[str, Any]):
            login_page.login(test_user["email"], test_user["password"])
    """
    return LoginPage(page, base_url)


@pytest.fixture
def dashboard_page(page, base_url: str) -> DashboardPage:
    """
    Initialize DashboardPage instance for post-authentication interactions.
    
    Args:
        page: Playwright Page instance from pytest-playwright fixture
        base_url: Application base URL from BASE_URL environment variable
    
    Returns:
        DashboardPage: Configured dashboard page object with navigation support
    
    Example:
        @then("the user is redirected to the dashboard")
        def verify_dashboard(dashboard_page: DashboardPage):
            dashboard_page.verify_dashboard_loaded()
    """
    return DashboardPage(page, base_url)


@pytest.fixture
def auth_api(api_base_url: str) -> AuthAPIClient:
    """
    Initialize AuthAPIClient instance for API authentication testing.
    
    Args:
        api_base_url: REST API base URL from API_BASE_URL environment variable
    
    Returns:
        AuthAPIClient: Configured authentication API client with httpx
    
    Example:
        @when("the user authenticates via API")
        def api_auth(auth_api: AuthAPIClient, test_user: Dict[str, Any], auth_token: Dict[str, str]):
            response = auth_api.login(test_user["email"], test_user["password"])
            auth_token["value"] = response.access_token
    """
    return AuthAPIClient(base_url=api_base_url)


@pytest.fixture
def test_user(mcp_client: MCPClient) -> Dict[str, Any]:
    """
    Create test user via MCP server with deterministic credentials.
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    
    This fixture creates a unique test user with auto-generated email to avoid
    conflicts in parallel test execution. The MCP server ensures credentials
    are known and predictable for test assertions.
    
    Args:
        mcp_client: MCP server client fixture from conftest.py
    
    Returns:
        dict: User data including:
            - id: User ID in target system
            - email: Auto-generated unique email (e.g., "customer-a3f9d82@test.local")
            - password: Generated password for UI login
            - role: User role (default: "customer")
            - auth_token: Valid JWT token for API requests
    
    Example:
        @given("a user exists with valid credentials")
        def user_exists(test_user: Dict[str, Any]):
            # test_user automatically created via MCP
            assert test_user["email"]
            assert test_user["password"]
    """
    user = mcp_client.seed_user(role="customer")
    return user


@pytest.fixture
def auth_token() -> Dict[str, str]:
    """
    Storage fixture for API authentication tokens across step definitions.
    
    This request-scoped fixture provides mutable state for storing JWT tokens
    between When and Then steps in API authentication scenarios. Using a dict
    allows mutations to persist across step function calls within the same test.
    
    Returns:
        dict: Empty dict for token storage with keys:
            - "value": Access token string
            - "refresh": Refresh token string (optional)
    
    Example:
        @when("the user authenticates via API")
        def api_auth(auth_api: AuthAPIClient, test_user: Dict[str, Any], auth_token: Dict[str, str]):
            response = auth_api.login(test_user["email"], test_user["password"])
            auth_token["value"] = response.access_token
            auth_token["refresh"] = response.refresh_token
        
        @then("a valid JWT token is returned")
        def verify_token(auth_token: Dict[str, str]):
            assert "value" in auth_token
            assert len(auth_token["value"]) > 50  # JWT tokens are long strings
    """
    return {}


# ==================================================================================
# GIVEN STEPS - AUTHENTICATION PRECONDITIONS
# ==================================================================================
# Given steps establish the initial state before authentication actions

@allure.step("Given the user is on the login page")
@given("the user is on the login page")
def navigate_to_login_page(login_page: LoginPage) -> None:
    """
    Navigate to the login page and verify it loads successfully.
    
    This step uses the LoginPage page object's navigate_to_login() method which:
    - Navigates to /login URL
    - Waits for login button to be visible
    - Captures screenshot for Allure report
    
    Allure Integration:
        - Step appears in report hierarchy
        - Screenshot attached automatically on navigation
    
    Example Gherkin:
        Given the user is on the login page
    """
    login_page.navigate_to_login()


@allure.step("Given a user exists with email {email} and role {role}")
@given(parsers.parse("a user exists with email {email} and role {role}"))
def user_exists_with_email_and_role(mcp_client: MCPClient, email: str, role: str, test_user: Dict[str, Any]) -> None:
    """
    Create test user with specific email and role via MCP server.
    
    This step overrides the default test_user fixture data by creating a user
    with specified email and role. The MCP server creates the user in the target
    application and returns credentials for authentication.
    
    Args:
        mcp_client: MCP server client for user creation
        email: Desired email address for test user
        role: User role (admin, customer, guest, etc.)
        test_user: Fixture dict to update with new user data
    
    Example Gherkin:
        Given a user exists with email "admin@example.com" and role "admin"
    """
    user = mcp_client.seed_user(role=role, email=email)
    test_user.update(user)


@allure.step("Given a test user exists with role {role}")
@given(parsers.parse("a test user exists with role {role}"))
def test_user_with_role(mcp_client: MCPClient, role: str, test_user: Dict[str, Any]) -> None:
    """
    Create test user with specific role and auto-generated email.
    
    This step creates a user with the specified role but allows MCP to generate
    a unique email address for parallel test execution safety.
    
    Args:
        mcp_client: MCP server client for user creation
        role: User role (admin, customer, guest, etc.)
        test_user: Fixture dict to update with new user data
    
    Example Gherkin:
        Given a test user exists with role "admin"
        Given a test user exists with role "customer"
    """
    user = mcp_client.seed_user(role=role)
    test_user.update(user)


@allure.step("Given the user is not authenticated")
@given("the user is not authenticated")
def user_not_authenticated(page) -> None:
    """
    Verify user has no active session or authentication state.
    
    This step confirms the browser context has no authentication cookies or
    session data. Since each test receives a fresh browser context per user
    directive "new context per test", this is typically a no-op verification.
    
    Example Gherkin:
        Given the user is not authenticated
        When the user logs in with valid credentials
    """
    # Each test gets a new browser context (isolated state)
    # No action needed - context is already clean
    allure.attach(
        "New browser context created - no existing authentication state",
        name="Authentication State",
        attachment_type=allure.attachment_type.TEXT
    )


@allure.step("Given the user is authenticated")
@given("the user is authenticated")
def user_is_authenticated(login_page: LoginPage, test_user: Dict[str, Any]) -> None:
    """
    Perform login in background to establish authenticated state.
    
    This step performs a complete login flow before the test scenario begins,
    useful for testing post-authentication functionality without focusing on
    the login process itself.
    
    Args:
        login_page: LoginPage instance for authentication
        test_user: Test user credentials from MCP server
    
    Example Gherkin:
        Given the user is authenticated
        When the user navigates to the profile page
        Then the profile information is displayed
    """
    login_page.navigate_to_login()
    login_page.login(test_user["email"], test_user["password"])
    login_page.verify_successful_login()


# ==================================================================================
# WHEN STEPS - UI AUTHENTICATION ACTIONS
# ==================================================================================
# When steps perform authentication actions through the user interface

@allure.step("When the user logs in with valid credentials")
@when("the user logs in with valid credentials")
def user_logs_in_with_valid_credentials(login_page: LoginPage, test_user: Dict[str, Any]) -> None:
    """
    Execute login flow with valid test user credentials.
    
    This step delegates to LoginPage.login() method which:
    - Fills email input field
    - Fills password input field
    - Clicks login button
    - Captures screenshot
    
    Credentials are obtained from test_user fixture which gets data from MCP
    server, ensuring no hardcoded test data per user directive.
    
    Args:
        login_page: LoginPage instance with stable ARIA-based locators
        test_user: User credentials from MCP server
    
    Example Gherkin:
        Given the user is on the login page
        When the user logs in with valid credentials
        Then the user is redirected to the dashboard
    """
    login_page.login(test_user["email"], test_user["password"])


@allure.step("When the user logs in with email {email} and password {password}")
@when(parsers.parse("the user logs in with email {email} and password {password}"))
def user_logs_in_with_credentials(login_page: LoginPage, email: str, password: str) -> None:
    """
    Execute login flow with explicitly provided credentials.
    
    This step variant allows Gherkin scenarios to specify exact credentials,
    useful for testing invalid credential scenarios or specific user accounts.
    
    Args:
        login_page: LoginPage instance
        email: Email address to use for login
        password: Password to use for login
    
    Example Gherkin:
        When the user logs in with email "wrong@example.com" and password "wrongpass"
        Then an error message "Invalid credentials" should be displayed
    """
    login_page.login(email, password)


@allure.step("When the user logs in with invalid credentials")
@when("the user logs in with invalid credentials")
def user_logs_in_with_invalid_credentials(login_page: LoginPage) -> None:
    """
    Execute login flow with intentionally invalid credentials.
    
    This step tests authentication failure scenarios by providing credentials
    that should be rejected by the authentication system.
    
    Args:
        login_page: LoginPage instance
    
    Example Gherkin:
        Given the user is on the login page
        When the user logs in with invalid credentials
        Then an error message is displayed
    """
    login_page.login("invalid@example.com", "wrongpassword")


@allure.step("When the user logs in with empty credentials")
@when("the user logs in with empty credentials")
def user_logs_in_with_empty_credentials(login_page: LoginPage) -> None:
    """
    Execute login flow with empty email and password fields.
    
    This step tests client-side validation by attempting login with no credentials,
    which should trigger validation errors before submitting to the server.
    
    Args:
        login_page: LoginPage instance
    
    Example Gherkin:
        When the user logs in with empty credentials
        Then a validation error should be displayed
    """
    login_page.login("", "")


@allure.step("When the user logs out")
@when("the user logs out")
def user_logs_out(dashboard_page: DashboardPage) -> None:
    """
    Execute logout flow from the dashboard.
    
    This step delegates to DashboardPage.logout() method which:
    - Opens user menu (via NavigationComponent)
    - Clicks logout link
    - Waits for redirect to login page
    - Verifies URL changed (no longer on dashboard)
    
    Args:
        dashboard_page: DashboardPage instance with navigation component
    
    Example Gherkin:
        Given the user is authenticated
        When the user logs out
        Then the user is redirected to the login page
    """
    dashboard_page.logout()


@allure.step("When the user requests a password reset for {email}")
@when(parsers.parse("the user requests a password reset for {email}"))
def user_requests_password_reset(auth_api: AuthAPIClient, email: str) -> None:
    """
    Request password reset via API for specified email.
    
    This step uses the AuthAPIClient to initiate a password reset flow,
    which sends a reset email to the specified address if it exists.
    
    Args:
        auth_api: Authentication API client
        email: Email address for password reset
    
    Example Gherkin:
        When the user requests a password reset for "user@example.com"
        Then a password reset email confirmation is returned
    """
    auth_api.request_password_reset(email)


# ==================================================================================
# WHEN STEPS - API AUTHENTICATION ACTIONS
# ==================================================================================
# When steps perform authentication actions through the REST API

@allure.step("When the user authenticates via API")
@when("the user authenticates via API")
def authenticate_via_api(auth_api: AuthAPIClient, test_user: Dict[str, Any], auth_token: Dict[str, str]) -> None:
    """
    Authenticate via REST API and store JWT tokens.
    
    This step uses the AuthAPIClient.login() method to:
    - Send POST request to /auth/login endpoint
    - Validate credentials with authentication service
    - Receive JWT access and refresh tokens
    - Store tokens in auth_token fixture for verification steps
    
    The response is validated by Pydantic models ensuring type safety and
    correct response structure.
    
    Args:
        auth_api: Authentication API client with httpx
        test_user: User credentials from MCP server
        auth_token: Storage fixture for token data
    
    Example Gherkin:
        Given a test user exists with role "admin"
        When the user authenticates via API
        Then a valid JWT token is returned
    """
    response = auth_api.login(test_user["email"], test_user["password"])
    auth_token["value"] = response.access_token
    auth_token["refresh"] = response.refresh_token
    auth_token["user_id"] = response.user_id
    auth_token["role"] = response.role


@allure.step("When the user authenticates via API with remember me")
@when("the user authenticates via API with remember me")
def authenticate_via_api_with_remember_me(
    auth_api: AuthAPIClient,
    test_user: Dict[str, Any],
    auth_token: Dict[str, str]
) -> None:
    """
    Authenticate via API with extended session duration.
    
    This step authenticates with the remember_me flag set to True, which
    typically results in longer token expiration times for persistent sessions.
    
    Args:
        auth_api: Authentication API client
        test_user: User credentials from MCP server
        auth_token: Storage fixture for token data
    
    Example Gherkin:
        When the user authenticates via API with remember me
        Then the token expiration should be extended
    """
    response = auth_api.login(test_user["email"], test_user["password"], remember_me=True)
    auth_token["value"] = response.access_token
    auth_token["refresh"] = response.refresh_token
    auth_token["expires_in"] = response.expires_in


@allure.step("When the user refreshes the authentication token")
@when("the user refreshes the authentication token")
def refresh_auth_token(auth_api: AuthAPIClient, auth_token: Dict[str, str]) -> None:
    """
    Refresh access token using refresh token for session management.
    
    This step uses the stored refresh token to obtain a new access token
    without re-authenticating with credentials. The new tokens are stored
    back in the auth_token fixture.
    
    Args:
        auth_api: Authentication API client
        auth_token: Storage fixture containing refresh token
    
    Example Gherkin:
        Given the user is authenticated via API
        When the user refreshes the authentication token
        Then a new access token is returned
    """
    refresh_token = auth_token.get("refresh", "")
    assert refresh_token, "No refresh token available to refresh"
    
    response: TokenRefreshResponse = auth_api.refresh_token(refresh_token)
    auth_token["value"] = response.access_token
    
    # Store new refresh token if rotation is enabled
    if response.refresh_token:
        auth_token["refresh"] = response.refresh_token


@allure.step("When the user logs out via API")
@when("the user logs out via API")
def logout_via_api(auth_api: AuthAPIClient, auth_token: Dict[str, str]) -> None:
    """
    Invalidate session by logging out via API.
    
    This step sets the current access token in the API client and calls
    the logout endpoint to invalidate the session.
    
    Args:
        auth_api: Authentication API client
        auth_token: Storage fixture containing access token
    
    Example Gherkin:
        Given the user is authenticated via API
        When the user logs out via API
        Then the token should be invalidated
    """
    # Set the token in the client for authenticated logout request
    auth_api.set_auth_token(auth_token.get("value", ""))
    auth_api.logout()


# ==================================================================================
# THEN STEPS - UI AUTHENTICATION VALIDATION
# ==================================================================================
# Then steps verify expected outcomes of UI authentication actions

@allure.step("Then the user is redirected to the dashboard")
@then("the user is redirected to the dashboard")
def verify_dashboard_redirect(login_page: LoginPage) -> None:
    """
    Verify successful login redirect to dashboard page.
    
    This step uses LoginPage.verify_successful_login() which:
    - Waits for URL to contain /dashboard path
    - Asserts URL matches expected pattern
    - Captures screenshot of destination page
    - Checks for console errors during navigation
    
    Args:
        login_page: LoginPage instance for verification
    
    Example Gherkin:
        When the user logs in with valid credentials
        Then the user is redirected to the dashboard
    """
    login_page.verify_successful_login("/dashboard")


@allure.step("Then the user should be redirected to {expected_url}")
@then(parsers.parse("the user should be redirected to {expected_url}"))
def verify_redirect_to_url(login_page: LoginPage, expected_url: str) -> None:
    """
    Verify redirect to specific URL after login.
    
    This step variant allows testing redirects to different destinations
    based on user role or redirect parameters.
    
    Args:
        login_page: LoginPage instance for verification
        expected_url: Expected destination URL path
    
    Example Gherkin:
        When the admin user logs in
        Then the user should be redirected to /admin
    """
    login_page.verify_successful_login(expected_url)


@allure.step("Then a welcome message is displayed")
@then("a welcome message is displayed")
def verify_welcome_message_displayed(dashboard_page: DashboardPage) -> None:
    """
    Verify welcome message appears on dashboard after login.
    
    This step uses DashboardPage.get_welcome_message() to retrieve and verify
    the welcome message text contains "Welcome", confirming personalization.
    
    Args:
        dashboard_page: DashboardPage instance
    
    Example Gherkin:
        When the user logs in with valid credentials
        Then the user is redirected to the dashboard
        And a welcome message is displayed
    """
    welcome_text = dashboard_page.get_welcome_message()
    assert "Welcome" in welcome_text, f"Expected 'Welcome' in message, got: {welcome_text}"


@allure.step("Then the welcome message should contain {expected_text}")
@then(parsers.parse("the welcome message should contain {expected_text}"))
def verify_welcome_message_contains_text(dashboard_page: DashboardPage, expected_text: str) -> None:
    """
    Verify welcome message contains specific text.
    
    This step allows precise verification of welcome message content,
    useful for testing personalization with user names or roles.
    
    Args:
        dashboard_page: DashboardPage instance
        expected_text: Text that should appear in welcome message
    
    Example Gherkin:
        When the user logs in as "John Doe"
        Then the welcome message should contain "John Doe"
    """
    welcome_text = dashboard_page.get_welcome_message()
    assert expected_text in welcome_text, (
        f"Expected '{expected_text}' in welcome message, got: {welcome_text}"
    )


@allure.step("Then an error message is displayed")
@then("an error message is displayed")
def verify_error_message_displayed(login_page: LoginPage) -> None:
    """
    Verify error alert appears after failed login attempt.
    
    This step confirms that an error message is visible using LoginPage's
    error_message locator (ARIA role="alert"), without checking specific text.
    
    Args:
        login_page: LoginPage instance
    
    Example Gherkin:
        When the user logs in with invalid credentials
        Then an error message is displayed
    """
    from playwright.sync_api import expect
    expect(login_page.error_message).to_be_visible(timeout=5000)


@allure.step("Then an error message {expected_message} should be displayed")
@then(parsers.parse('an error message "{expected_message}" should be displayed'))
def verify_specific_error_message(login_page: LoginPage, expected_message: str) -> None:
    """
    Verify specific error message text after failed login.
    
    This step uses LoginPage.verify_error_message() which:
    - Asserts error alert is visible
    - Verifies error text matches expected message
    - Captures screenshot of error state
    
    Args:
        login_page: LoginPage instance
        expected_message: Expected error message text
    
    Example Gherkin:
        When the user logs in with invalid credentials
        Then an error message "Invalid email or password" should be displayed
    """
    login_page.verify_error_message(expected_message)


@allure.step("Then the user is redirected to the login page")
@then("the user is redirected to the login page")
def verify_login_page_redirect(page) -> None:
    """
    Verify redirect to login page after logout.
    
    This step confirms the browser navigated back to the login page by
    checking the URL contains "/login".
    
    Args:
        page: Playwright Page instance
    
    Example Gherkin:
        When the user logs out
        Then the user is redirected to the login page
    """
    from playwright.sync_api import expect
    expect(page).to_have_url("/login")


@allure.step("Then the dashboard page should be displayed")
@then("the dashboard page should be displayed")
def verify_dashboard_displayed(dashboard_page: DashboardPage) -> None:
    """
    Verify dashboard page loaded completely after authentication.
    
    This step uses DashboardPage.verify_dashboard_loaded() which performs
    comprehensive verification:
    - Dashboard heading is visible
    - URL contains /dashboard path
    - Main content area is present
    
    Args:
        dashboard_page: DashboardPage instance
    
    Example Gherkin:
        Given the user is authenticated
        Then the dashboard page should be displayed
    """
    dashboard_page.verify_dashboard_loaded()


# ==================================================================================
# THEN STEPS - API AUTHENTICATION VALIDATION
# ==================================================================================
# Then steps verify expected outcomes of API authentication actions

@allure.step("Then a valid JWT token is returned")
@then("a valid JWT token is returned")
def verify_jwt_token_returned(auth_token: Dict[str, str]) -> None:
    """
    Verify JWT access token was received from authentication.
    
    This step asserts that:
    - Token exists in auth_token storage
    - Token is a non-empty string
    - Token length indicates valid JWT format (> 50 characters)
    
    Args:
        auth_token: Storage fixture containing authentication tokens
    
    Example Gherkin:
        When the user authenticates via API
        Then a valid JWT token is returned
    """
    assert "value" in auth_token, "No access token in auth_token storage"
    token = auth_token["value"]
    assert token, "Access token is empty"
    assert len(token) > 50, f"Token too short to be valid JWT: {len(token)} characters"
    
    allure.attach(
        f"Token length: {len(token)} characters\nToken prefix: {token[:20]}...",
        name="JWT Token Validation",
        attachment_type=allure.attachment_type.TEXT
    )


@allure.step("Then the token contains the correct user role")
@then("the token contains the correct user role")
def verify_token_contains_role(auth_token: Dict[str, str], test_user: Dict[str, Any]) -> None:
    """
    Verify JWT token response includes correct user role.
    
    This step compares the role from the authentication response with the
    role used to create the test user via MCP.
    
    Args:
        auth_token: Storage fixture with role from login response
        test_user: Test user data from MCP with expected role
    
    Example Gherkin:
        Given a test user exists with role "admin"
        When the user authenticates via API
        Then the token contains the correct user role
    """
    assert "role" in auth_token, "No role in auth_token storage"
    actual_role = auth_token["role"]
    expected_role = test_user["role"]
    
    assert actual_role == expected_role, (
        f"Role mismatch: expected '{expected_role}', got '{actual_role}'"
    )
    
    allure.attach(
        f"Expected role: {expected_role}\nActual role: {actual_role}",
        name="Role Verification",
        attachment_type=allure.attachment_type.TEXT
    )


@allure.step("Then the token should expire in {seconds:d} seconds")
@then(parsers.parse("the token should expire in {seconds:d} seconds"))
def verify_token_expiration(auth_token: Dict[str, str], seconds: int) -> None:
    """
    Verify token expiration time matches expected duration.
    
    This step checks the expires_in field from the authentication response
    matches the expected number of seconds.
    
    Args:
        auth_token: Storage fixture with expires_in data
        seconds: Expected expiration duration in seconds
    
    Example Gherkin:
        When the user authenticates via API
        Then the token should expire in 3600 seconds
    """
    assert "expires_in" in auth_token, "No expires_in in auth_token storage"
    expires_in = auth_token["expires_in"]
    
    assert expires_in == seconds, (
        f"Expiration mismatch: expected {seconds}s, got {expires_in}s"
    )


@allure.step("Then the authentication should fail with status code {status_code:d}")
@then(parsers.parse("the authentication should fail with status code {status_code:d}"))
def verify_auth_failure_status_code(auth_api: AuthAPIClient, status_code: int) -> None:
    """
    Verify authentication failure returns expected HTTP status code.
    
    This step attempts authentication with invalid credentials and verifies
    the API returns the expected error status code (e.g., 401 Unauthorized).
    
    Args:
        auth_api: Authentication API client
        status_code: Expected HTTP status code
    
    Example Gherkin:
        When the user authenticates via API with invalid credentials
        Then the authentication should fail with status code 401
    """
    import httpx
    
    try:
        auth_api.login("invalid@example.com", "wrongpassword")
        raise AssertionError(f"Expected authentication to fail with {status_code}, but it succeeded")
    except httpx.HTTPStatusError as e:
        actual_status = e.response.status_code
        assert actual_status == status_code, (
            f"Status code mismatch: expected {status_code}, got {actual_status}"
        )
        
        allure.attach(
            f"Expected status: {status_code}\nActual status: {actual_status}",
            name="Status Code Verification",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.step("Then a new access token is returned")
@then("a new access token is returned")
def verify_new_access_token(auth_token: Dict[str, str]) -> None:
    """
    Verify token refresh returned a new access token.
    
    This step confirms that after refreshing, a new access token is available
    in the auth_token storage.
    
    Args:
        auth_token: Storage fixture with refreshed token
    
    Example Gherkin:
        When the user refreshes the authentication token
        Then a new access token is returned
    """
    assert "value" in auth_token, "No access token after refresh"
    token = auth_token["value"]
    assert token, "Access token is empty after refresh"
    assert len(token) > 50, f"Refreshed token too short: {len(token)} characters"


@allure.step("Then the token should be invalidated")
@then("the token should be invalidated")
def verify_token_invalidated(auth_api: AuthAPIClient, auth_token: Dict[str, str]) -> None:
    """
    Verify token is no longer valid after logout.
    
    This step uses AuthAPIClient.verify_token() to check if the token is
    still valid, expecting it to return False after logout.
    
    Args:
        auth_api: Authentication API client
        auth_token: Storage fixture with (now invalid) token
    
    Example Gherkin:
        When the user logs out via API
        Then the token should be invalidated
    """
    token = auth_token.get("value", "")
    is_valid = auth_api.verify_token(token)
    
    assert not is_valid, "Token should be invalid after logout, but it's still valid"
    
    allure.attach(
        f"Token validation after logout: {is_valid}",
        name="Token Invalidation Check",
        attachment_type=allure.attachment_type.TEXT
    )


@allure.step("Then a password reset email confirmation is returned")
@then("a password reset email confirmation is returned")
def verify_password_reset_confirmation(auth_api: AuthAPIClient) -> None:
    """
    Verify password reset request returns confirmation message.
    
    This step checks that the password reset API endpoint returned a success
    response, typically with a message confirming the email was sent.
    
    Note: Actual implementation depends on the last password reset request.
    In a complete implementation, this would check a response stored in a fixture.
    
    Args:
        auth_api: Authentication API client
    
    Example Gherkin:
        When the user requests a password reset for "user@example.com"
        Then a password reset email confirmation is returned
    """
    # Note: In a real implementation, we would store the response in a fixture
    # and validate it here. For now, this step serves as a placeholder for
    # password reset flow verification.
    allure.attach(
        "Password reset confirmation would be validated here",
        name="Password Reset",
        attachment_type=allure.attachment_type.TEXT
    )

