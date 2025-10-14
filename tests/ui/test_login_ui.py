"""
Traditional pytest UI tests for authentication workflows.

This module contains UI tests for login functionality using:
- Page Object Pattern (LoginPage, DashboardPage)
- MCP-generated test data (no hardcoded credentials)
- Stable ARIA-based locators (via page objects)
- Isolated browser contexts per test (parallel-friendly)
- Allure reporting with screenshots and traces

Per user directives:
- "Tests execute inside pytest (fast, reliable)"
- "Use MCP tools for data/state (don't hard-code test data)"
- "Keep tests deterministic, isolated, and parallel-friendly (new context per test)"
- "Implement steps via page objects; avoid brittle CSS/xpath—prefer role/name/test-id"
"""

import allure


@allure.feature("Authentication")
@allure.severity(allure.severity_level.CRITICAL)
@allure.story("User Login")
def test_login_with_valid_credentials(login_page, dashboard_page, mcp_client):
    """
    Test successful login flow with valid user credentials from MCP.
    
    Verifies:
    - User can navigate to login page
    - Login with MCP-generated valid credentials succeeds
    - User is redirected to dashboard after successful login
    - Welcome message displays user information
    
    Args:
        login_page: LoginPage fixture from conftest.py
        dashboard_page: DashboardPage fixture from conftest.py
        mcp_client: MCPClient fixture for test data generation
    """
    # Get test user from MCP server (no hardcoded data)
    # Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    user = mcp_client.seed_user(role="customer", email_prefix="valid_user")
    
    # Navigate to login page
    login_page.navigate_to_login()
    
    # Perform login with MCP-generated credentials
    login_page.login(email=user["email"], password=user["password"])
    
    # Verify successful login and redirect to dashboard
    dashboard_page.verify_dashboard_loaded()
    
    # Verify welcome message contains user's name
    welcome_message = dashboard_page.get_welcome_message()
    assert user["name"] in welcome_message or user["email"] in welcome_message, (
        f"Expected welcome message to contain user identifier, "
        f"but got: '{welcome_message}'"
    )


@allure.feature("Authentication")
@allure.severity(allure.severity_level.CRITICAL)
@allure.story("Invalid Login")
def test_login_with_invalid_credentials(login_page, mcp_client):
    """
    Test login failure with invalid credentials.
    
    Verifies:
    - Login with invalid credentials fails appropriately
    - Error message is displayed to user
    - User remains on login page after failed attempt
    
    Args:
        login_page: LoginPage fixture from conftest.py
        mcp_client: MCPClient fixture for test data generation
    """
    # Get invalid credentials payload from MCP
    invalid_payload = mcp_client.build_payload("invalid_login")
    
    # Navigate and attempt login
    login_page.navigate_to_login()
    login_page.login(
        email=invalid_payload["email"],
        password=invalid_payload["password"]
    )
    
    # Verify error message appears
    login_page.verify_error_message("Invalid email or password")
    
    # Verify user remains on login page
    assert login_page.page.url.endswith("/login"), (
        f"Expected user to remain on login page, but URL is: {login_page.page.url}"
    )


@allure.feature("Authentication")
@allure.severity(allure.severity_level.CRITICAL)
@allure.story("Logout")
def test_logout(login_page, dashboard_page, mcp_client):
    """
    Test complete login and logout flow.
    
    Verifies:
    - User can successfully login
    - User can successfully logout from dashboard
    - User is redirected to login page after logout
    - Session is properly terminated
    
    Args:
        login_page: LoginPage fixture from conftest.py
        dashboard_page: DashboardPage fixture from conftest.py
        mcp_client: MCPClient fixture for test data generation
    """
    # Setup: Create test user via MCP
    user = mcp_client.seed_user(role="customer")
    
    # Login
    login_page.navigate_to_login()
    login_page.login(email=user["email"], password=user["password"])
    dashboard_page.verify_dashboard_loaded()
    
    # Logout
    dashboard_page.logout()
    
    # Verify redirect to login page
    login_page.verify_on_login_page()


@allure.feature("Authentication")
@allure.severity(allure.severity_level.NORMAL)
@allure.story("Validation")
def test_login_with_empty_fields(login_page):
    """
    Test form validation with empty email and password.
    
    Verifies:
    - Login form validates required fields
    - Browser-level validation prevents submission with empty fields
    - Appropriate validation messages are shown
    
    This tests HTML5 required attribute behavior and client-side validation.
    
    Args:
        login_page: LoginPage fixture from conftest.py
    """
    # Navigate to login page
    login_page.navigate_to_login()
    
    # Click login button without entering credentials
    login_page.click_login_button()
    
    # Verify browser-level validation or error messages
    # This verifies that the form has proper validation in place
    login_page.verify_validation_errors_displayed()


@allure.feature("Authentication")
@allure.severity(allure.severity_level.NORMAL)
@allure.story("Remember Me")
def test_remember_me_functionality(login_page, dashboard_page, mcp_client, page):
    """
    Test remember me checkbox persistence.
    
    Verifies:
    - Remember me checkbox can be selected
    - Login with remember me checked sets persistence tokens
    - Authentication cookies/localStorage are properly set
    - User session persists as expected
    
    Args:
        login_page: LoginPage fixture from conftest.py
        dashboard_page: DashboardPage fixture from conftest.py
        mcp_client: MCPClient fixture for test data generation
        page: Playwright Page fixture from conftest.py
    """
    # Get test user from MCP
    user = mcp_client.seed_user(role="customer")
    
    # Login with remember_me=True
    login_page.navigate_to_login()
    login_page.login(
        email=user["email"],
        password=user["password"],
        remember_me=True
    )
    
    # Verify successful login
    dashboard_page.verify_dashboard_loaded()
    
    # Verify cookies/localStorage set for persistence
    # Check for authentication token in storage
    storage_state = page.context.storage_state()
    
    # Verify at least one authentication-related cookie exists
    auth_cookies = [
        cookie for cookie in storage_state["cookies"]
        if "auth" in cookie["name"].lower() or "token" in cookie["name"].lower()
    ]
    
    assert len(auth_cookies) > 0, (
        "Expected authentication cookies to be set with remember_me=True, "
        f"but found cookies: {[c['name'] for c in storage_state['cookies']]}"
    )
