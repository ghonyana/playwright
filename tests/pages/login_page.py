"""
Login Page Object Module

This module provides the LoginPage class for automating authentication UI interactions
in the test automation framework. It implements the Page Object Pattern with stable
ARIA-based locators, ensuring maintainable and reliable login flow testing.

Key Features:
-------------
- Stable locator strategies using ARIA roles, labels, and accessible names
- High-level methods for complete login workflows
- Comprehensive error message verification
- Successful login validation with URL pattern matching
- Integration with Allure reporting for step-by-step test documentation
- Parallel test execution friendly with per-test browser context isolation

Locator Priority Strategy:
-------------------------
Following user directive: "avoid brittle CSS/xpath—prefer role/name/test‑id"

1. ARIA roles (get_by_role) - Highest priority for semantic elements
2. Label associations (get_by_label) - For form inputs with labels
3. Test IDs (get_by_test_id) - When semantic options insufficient
4. Text content - For links and visible text
5. AVOID: CSS class selectors and XPath expressions

This approach ensures tests remain stable across:
- UI refactoring and styling changes
- CSS framework updates
- DOM structure modifications
- Internationalization (when using test-ids as fallback)

Example Usage in Step Definitions:
---------------------------------
```python
from pytest_bdd import given, when, then
from tests.pages.login_page import LoginPage

@given("the user is on the login page")
def navigate_to_login_page(page, login_page: LoginPage):
    login_page.navigate_to_login()

@when("the user logs in with email '<email>' and password '<password>'")
def user_logs_in(login_page: LoginPage, email: str, password: str):
    login_page.login(email, password)

@then("the login error message '<message>' should be displayed")
def verify_login_error(login_page: LoginPage, message: str):
    login_page.verify_error_message(message)

@then("the user should be redirected to the dashboard")
def verify_dashboard_redirect(login_page: LoginPage):
    login_page.verify_successful_login()
```

Integration with MCP Server:
---------------------------
This page object works seamlessly with the FastAPI MCP server for test data:

```python
def test_login_with_seeded_user(page, login_page: LoginPage, mcp_client):
    # Seed test user via MCP
    user = mcp_client.seed_user(role="customer", email="test@example.com")
    
    # Use in login flow
    login_page.navigate_to_login()
    login_page.login(user['email'], user['password'])
    login_page.verify_successful_login()
```
"""

from typing import Optional

import allure
from playwright.sync_api import Page, expect

from tests.pages.base_page import BasePage


class LoginPage(BasePage):
    """
    Login page object for authentication UI interactions.
    
    This class encapsulates all login page elements and actions, providing
    high-level, business-readable methods for authentication testing. It inherits
    common functionality from BasePage including navigation, waiting, screenshot
    capture, and console error collection.
    
    Attributes:
        LOGIN_PATH (str): Relative URL path to the login page
        page (Page): Playwright Page instance (inherited from BasePage)
        base_url (str): Application base URL (inherited from BasePage)
    
    Locator Properties:
        email_input: Email address input field
        password_input: Password input field
        login_button: Sign in submission button
        error_message: Error alert message display
        remember_me_checkbox: Remember me persistence option
        forgot_password_link: Password recovery link
    
    Action Methods:
        navigate_to_login(): Navigate to login page
        login(): Perform complete login flow
        verify_error_message(): Assert error message visibility and content
        verify_successful_login(): Validate successful authentication redirect
    
    Example:
        ```python
        def test_valid_login(page: Page):
            login_page = LoginPage(page)
            login_page.navigate_to_login()
            login_page.login("user@example.com", "SecurePass123!")
            login_page.verify_successful_login("/dashboard")
        
        def test_invalid_credentials(page: Page):
            login_page = LoginPage(page)
            login_page.navigate_to_login()
            login_page.login("wrong@example.com", "wrongpass")
            login_page.verify_error_message("Invalid email or password")
        ```
    """
    
    # Class constant for login page route
    LOGIN_PATH: str = "/login"
    
    def __init__(self, page: Page, base_url: Optional[str] = None):
        """
        Initialize the LoginPage with a Playwright Page instance.
        
        Args:
            page (Page): Playwright Page instance from pytest fixture
            base_url (Optional[str]): Base URL override; defaults to BASE_URL env var
        
        Raises:
            ValueError: If neither base_url parameter nor BASE_URL env var is provided
        
        Example:
            ```python
            # In pytest fixture (tests/conftest.py)
            @pytest.fixture
            def login_page(page: Page) -> LoginPage:
                return LoginPage(page)
            
            # In test
            def test_login(login_page: LoginPage):
                login_page.navigate_to_login()
            ```
        """
        super().__init__(page, base_url)
    
    # Locator Properties using stable selector strategies
    
    @property
    def email_input(self):
        """
        Locate the email input field using accessible label.
        
        Priority: get_by_label (semantic relationship between label and input)
        Fallback: get_by_role('textbox', name='Email') for ARIA-labeled inputs
        
        Returns:
            Locator: Playwright locator for email input element
        
        Expected HTML patterns:
            <label for="email">Email</label>
            <input id="email" type="email" name="email" />
            
            OR
            
            <input type="email" aria-label="Email" />
            
            OR
            
            <input type="email" role="textbox" aria-label="Email" />
        """
        try:
            # Prefer label association (most semantic)
            return self.page.get_by_label("Email", exact=False)
        except Exception:
            # Fallback to ARIA role with accessible name
            return self.page.get_by_role("textbox", name="Email")
    
    @property
    def password_input(self):
        """
        Locate the password input field using accessible label.
        
        Priority: get_by_label (semantic relationship between label and input)
        Fallback: get_by_role('textbox', name='Password') for ARIA-labeled inputs
        
        Returns:
            Locator: Playwright locator for password input element
        
        Expected HTML patterns:
            <label for="password">Password</label>
            <input id="password" type="password" name="password" />
            
            OR
            
            <input type="password" aria-label="Password" />
        
        Note: Some implementations may use role="textbox" even for password fields
        when ARIA attributes are explicitly set for accessibility.
        """
        try:
            # Prefer label association (most semantic)
            return self.page.get_by_label("Password", exact=False)
        except Exception:
            # Fallback to ARIA role with accessible name
            return self.page.get_by_role("textbox", name="Password")
    
    @property
    def login_button(self):
        """
        Locate the login submission button using ARIA role and accessible name.
        
        Priority: get_by_role('button', name='Sign In') - most stable approach
        
        Returns:
            Locator: Playwright locator for login button element
        
        Expected HTML patterns:
            <button type="submit">Sign In</button>
            
            OR
            
            <button type="submit" aria-label="Sign In">Login</button>
            
            OR
            
            <input type="submit" value="Sign In" />
        
        Note: Matches buttons with text content "Sign In" or similar variations
        (Login, Log in, Sign in, etc.). The name parameter matches accessible name
        which includes button text content, aria-label, and aria-labelledby.
        """
        return self.page.get_by_role("button", name="Sign In")
    
    @property
    def error_message(self):
        """
        Locate the error alert message display using ARIA role.
        
        Priority: get_by_role('alert') - semantic error messaging
        
        Returns:
            Locator: Playwright locator for error message element
        
        Expected HTML patterns:
            <div role="alert">Invalid credentials</div>
            
            OR
            
            <div role="alert" aria-live="polite">
                <p>Invalid email or password</p>
            </div>
        
        Note: Elements with role="alert" are automatically announced by screen
        readers, making this the most accessible and semantic choice for error
        messages. This approach ensures we're testing the same UX that assistive
        technology users experience.
        """
        return self.page.get_by_role("alert")
    
    @property
    def remember_me_checkbox(self):
        """
        Locate the remember me checkbox using ARIA role and accessible name.
        
        Priority: get_by_role('checkbox', name='Remember me') - semantic checkbox
        
        Returns:
            Locator: Playwright locator for remember me checkbox element
        
        Expected HTML patterns:
            <label>
                <input type="checkbox" name="remember" />
                Remember me
            </label>
            
            OR
            
            <input type="checkbox" id="remember" />
            <label for="remember">Remember me</label>
            
            OR
            
            <input type="checkbox" aria-label="Remember me" />
        """
        return self.page.get_by_role("checkbox", name="Remember me")
    
    @property
    def forgot_password_link(self):
        """
        Locate the forgot password link using ARIA role and accessible name.
        
        Priority: get_by_role('link', name='Forgot password?') - semantic link
        
        Returns:
            Locator: Playwright locator for forgot password link element
        
        Expected HTML patterns:
            <a href="/forgot-password">Forgot password?</a>
            
            OR
            
            <a href="/reset" aria-label="Forgot password?">Reset Password</a>
        """
        return self.page.get_by_role("link", name="Forgot password?")
    
    # Action Methods with Allure step decorators
    
    @allure.step("Navigate to login page")
    def navigate_to_login(self) -> None:
        """
        Navigate to the login page and wait for the page to be ready.
        
        This method navigates to the login page URL and waits for the login button
        to be visible, ensuring the page is fully loaded and interactive before
        proceeding with test actions.
        
        The navigation appears as a step in Allure reports with automatic
        screenshot capture on failure.
        
        Raises:
            TimeoutError: If login button doesn't become visible within timeout
        
        Example:
            ```python
            def test_login_page_loads(login_page: LoginPage):
                login_page.navigate_to_login()
                # Page is now ready for interaction
                assert login_page.get_current_url().endswith("/login")
            ```
        
        Integration with Step Definitions:
            ```python
            @given("the user is on the login page")
            def user_on_login_page(login_page: LoginPage):
                login_page.navigate_to_login()
            ```
        """
        # Navigate to login page using inherited navigate method
        self.navigate(self.LOGIN_PATH)
        
        # Wait for login button to be visible (indicates page ready)
        expect(self.login_button).to_be_visible(timeout=10000)
        
        # Attach page URL to Allure report
        allure.attach(
            self.get_current_url(),
            name="Login Page URL",
            attachment_type=allure.attachment_type.TEXT
        )
    
    @allure.step("Login with email: {email}")
    def login(
        self,
        email: str,
        password: str,
        remember_me: bool = False
    ) -> None:
        """
        Perform complete login flow with email and password.
        
        This method fills the email and password fields, optionally checks the
        remember me checkbox, and clicks the login button. It represents the
        complete user login interaction in a single high-level method call.
        
        Args:
            email (str): User email address for authentication
            password (str): User password for authentication
            remember_me (bool): Whether to check "Remember me" checkbox (default: False)
        
        Note: This method does NOT wait for navigation or verify success.
        Use verify_successful_login() or verify_error_message() afterwards
        to assert the expected outcome.
        
        Example:
            ```python
            def test_successful_login(login_page: LoginPage):
                login_page.navigate_to_login()
                login_page.login("user@example.com", "SecurePass123!")
                login_page.verify_successful_login()
            
            def test_login_with_remember_me(login_page: LoginPage):
                login_page.navigate_to_login()
                login_page.login("user@example.com", "pass", remember_me=True)
                login_page.verify_successful_login()
            ```
        
        Integration with Step Definitions:
            ```python
            @when("the user logs in with '<email>' and '<password>'")
            def user_logs_in(login_page: LoginPage, email: str, password: str):
                login_page.login(email, password)
            
            @when("the user logs in and selects remember me")
            def user_logs_in_with_remember(login_page: LoginPage):
                login_page.login("test@example.com", "password", remember_me=True)
            ```
        
        Integration with MCP Server:
            ```python
            def test_login_seeded_user(login_page: LoginPage, mcp_client):
                # Get credentials from MCP server
                user = mcp_client.seed_user(role="admin")
                
                # Use in login
                login_page.navigate_to_login()
                login_page.login(user['email'], user['password'])
                login_page.verify_successful_login()
            ```
        """
        # Fill email input
        self.email_input.fill(email)
        allure.attach(
            email,
            name="Email Address",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Fill password input (don't attach password to report for security)
        self.password_input.fill(password)
        allure.attach(
            "********",
            name="Password",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Handle remember me checkbox if requested
        if remember_me:
            # Check if checkbox exists and is not already checked
            if self.remember_me_checkbox.is_visible():
                if not self.remember_me_checkbox.is_checked():
                    self.remember_me_checkbox.check()
                    allure.attach(
                        "Remember me checkbox selected",
                        name="Remember Me",
                        attachment_type=allure.attachment_type.TEXT
                    )
        
        # Click login button
        self.login_button.click()
        
        # Capture screenshot after login attempt
        self.capture_screenshot("After Login Click")
    
    @allure.step("Verify error message: {expected_message}")
    def verify_error_message(self, expected_message: str) -> None:
        """
        Verify that an error message is displayed with expected content.
        
        This method asserts that the error alert is visible and contains the
        expected error message text. It uses Playwright's expect assertions
        for automatic waiting and retry logic.
        
        Args:
            expected_message (str): Expected error message text to verify
        
        Raises:
            AssertionError: If error message is not visible or text doesn't match
        
        Example:
            ```python
            def test_invalid_credentials(login_page: LoginPage):
                login_page.navigate_to_login()
                login_page.login("wrong@example.com", "wrongpass")
                login_page.verify_error_message("Invalid email or password")
            
            def test_empty_fields(login_page: LoginPage):
                login_page.navigate_to_login()
                login_page.login("", "")
                login_page.verify_error_message("Email and password are required")
            ```
        
        Integration with Step Definitions:
            ```python
            @then("an error message '<message>' should be displayed")
            def verify_error_displayed(login_page: LoginPage, message: str):
                login_page.verify_error_message(message)
            
            @then("the login should fail with invalid credentials error")
            def verify_invalid_credentials_error(login_page: LoginPage):
                login_page.verify_error_message("Invalid email or password")
            ```
        
        Note: This method uses Playwright's expect() for built-in retry logic
        and automatic waiting, ensuring robust error verification even when
        error messages appear after API calls or validation delays.
        """
        # Assert error message is visible
        expect(self.error_message).to_be_visible(timeout=5000)
        
        # Assert error message contains expected text
        expect(self.error_message).to_have_text(expected_message)
        
        # Attach error message to Allure report
        actual_error = self.error_message.text_content()
        allure.attach(
            f"Expected: {expected_message}\nActual: {actual_error}",
            name="Error Message Verification",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Capture screenshot of error state
        self.capture_screenshot("Error Message Displayed")
    
    @allure.step("Verify successful login (expected URL: {expected_url})")
    def verify_successful_login(self, expected_url: str = "/dashboard") -> None:
        """
        Verify that login was successful by checking URL navigation.
        
        This method waits for the browser to navigate to the expected post-login
        URL (default: /dashboard) and asserts that the URL matches the expected
        pattern. This validates that authentication succeeded and the application
        redirected the user appropriately.
        
        Args:
            expected_url (str): Expected URL path or pattern after successful login
                               Default: "/dashboard"
                               Can be full URL, path, or regex pattern
        
        Raises:
            AssertionError: If navigation doesn't occur or URL doesn't match
            TimeoutError: If navigation timeout expires before URL change
        
        Example:
            ```python
            def test_successful_login_redirect(login_page: LoginPage):
                login_page.navigate_to_login()
                login_page.login("valid@example.com", "ValidPass123!")
                login_page.verify_successful_login("/dashboard")
            
            def test_admin_login_redirect(login_page: LoginPage):
                login_page.navigate_to_login()
                login_page.login("admin@example.com", "AdminPass!")
                login_page.verify_successful_login("/admin")
            
            def test_login_with_redirect_param(login_page: LoginPage):
                # Login page with ?redirect=/profile parameter
                login_page.navigate("/login?redirect=/profile")
                login_page.login("user@example.com", "Pass123!")
                login_page.verify_successful_login("/profile")
            ```
        
        Integration with Step Definitions:
            ```python
            @then("the user should be logged in successfully")
            def verify_login_success(login_page: LoginPage):
                login_page.verify_successful_login()
            
            @then("the user should be redirected to '<page>'")
            def verify_redirect_to_page(login_page: LoginPage, page: str):
                login_page.verify_successful_login(page)
            ```
        
        Integration with MCP Server State Verification:
            ```python
            def test_login_creates_session(login_page: LoginPage, mcp_client):
                user = mcp_client.seed_user(role="user")
                
                login_page.navigate_to_login()
                login_page.login(user['email'], user['password'])
                login_page.verify_successful_login()
                
                # Verify session state via MCP
                state = mcp_client.query_state("user_sessions")
                assert user['email'] in state['active_sessions']
            ```
        
        Note: This method uses Playwright's wait_for_url() which provides
        automatic retry logic and waiting for navigation to complete, ensuring
        robust validation even with slow network conditions or async redirects.
        """
        # Wait for URL to match expected pattern (with automatic retry)
        self.wait_for_url(expected_url, timeout=10000, wait_until="networkidle")
        
        # Get actual URL for verification
        actual_url = self.get_current_url()
        
        # Verify URL contains expected pattern using expect assertion
        expect(self.page).to_have_url(expected_url)
        
        # Attach URL verification details to Allure report
        allure.attach(
            f"Expected URL pattern: {expected_url}\nActual URL: {actual_url}",
            name="Login Redirect Verification",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Capture screenshot of successful login destination page
        self.capture_screenshot("Successful Login - Destination Page")
        
        # Check for any console errors during login process
        console_errors = self.get_console_errors()
        if console_errors:
            allure.attach(
                "\n".join(console_errors),
                name="Console Errors During Login",
                attachment_type=allure.attachment_type.TEXT
            )
