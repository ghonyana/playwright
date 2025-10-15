"""
Base Page Object Module

This module provides the foundational BasePage class that serves as the parent class
for all page objects in the test automation framework. It encapsulates common
functionality, enforces stable locator strategies, and integrates with Allure reporting.

The Page Object Pattern:
-----------------------
The Page Object Pattern is a design pattern that creates an abstraction layer between
test code and UI implementation details. Benefits include:
- Reduced code duplication across tests
- Improved test maintainability when UI changes
- Business-readable test code focusing on actions, not implementation
- Centralized element locator management

Stable Locator Strategy:
-----------------------
This BasePage enforces a stable locator hierarchy to avoid brittle tests:
1. ARIA roles (get_by_role) - Preferred for accessibility-based selection
2. Accessible names/labels (get_by_label) - Semantic labeling
3. Test IDs (get_by_test_id) - Explicit test-only attributes
4. Avoid: CSS class selectors and complex XPath expressions

This strategy ensures tests remain stable across UI refactoring and styling changes.

Integration Points:
------------------
- Playwright: Browser automation via Page instance from pytest fixtures
- Allure: Hierarchical test step reporting with screenshots and diagnostics
- Environment Config: BASE_URL from environment variables for flexible deployment testing
"""

import os
from typing import Optional, List, Dict, Any

import allure
from playwright.sync_api import Page


class BasePage:
    """
    Base page class providing common functionality for all page objects.
    
    This class encapsulates the Playwright Page instance and provides utility methods
    for navigation, waiting, screenshot capture, console error retrieval, network
    failure tracking, and stable element location strategies. All page objects should
    inherit from this class.
    
    Attributes:
        page (Page): Playwright Page instance for browser interactions
        base_url (str): Base URL of the application under test from BASE_URL env var
        _console_errors (List[str]): Collected console error messages
        _failed_requests (List[str]): Collected failed network request URLs (status >= 400)
    
    Example Usage:
        ```python
        # In a specific page object
        class LoginPage(BasePage):
            def __init__(self, page: Page):
                super().__init__(page)
                
            def enter_credentials(self, username: str, password: str):
                # Use stable locators provided by BasePage
                self.page.get_by_label("Username").fill(username)
                self.page.get_by_label("Password").fill(password)
                self.page.get_by_role("button", name="Login").click()
        
        # In a test
        def test_login(page: Page):
            login_page = LoginPage(page)
            login_page.navigate("/login")
            login_page.wait_for_load()
            login_page.enter_credentials("testuser", "password123")
        ```
    """
    
    def __init__(self, page: Page, base_url: Optional[str] = None):
        """
        Initialize the BasePage with a Playwright Page instance and base URL.
        
        Args:
            page (Page): Playwright Page instance from pytest fixture
            base_url (Optional[str]): Base URL override; defaults to BASE_URL env var
        
        Raises:
            ValueError: If neither base_url parameter nor BASE_URL env var is provided
        """
        self.page: Page = page
        # Get base_url from parameter or environment variable
        url_value: Optional[str] = base_url or os.getenv("BASE_URL", None)
        
        if not url_value:
            raise ValueError(
                "BASE_URL must be provided either as parameter or environment variable. "
                "Set BASE_URL environment variable or pass base_url parameter."
            )
        
        # Now we know url_value is not None, assign to typed attribute
        self.base_url: str = url_value
        
        # Ensure base_url doesn't end with trailing slash for consistent URL joining
        self.base_url = self.base_url.rstrip("/")
        
        # Initialize console error collection
        self._console_errors: List[str] = []
        self._setup_console_listener()
        
        # Initialize network request failure tracking
        self._failed_requests: List[str] = []
        self._setup_network_listener()
    
    def _setup_console_listener(self) -> None:
        """
        Set up listener for browser console messages to capture errors.
        
        This internal method registers a console event handler that filters
        and stores error-level messages for later retrieval and debugging.
        """
        def handle_console_message(msg: Any) -> None:
            """Capture console error messages."""
            if msg.type == "error":
                self._console_errors.append(f"[{msg.type}] {msg.text}")
        
        self.page.on("console", handle_console_message)
    
    def _setup_network_listener(self) -> None:
        """
        Set up listener for network requests to capture failures.
        
        This internal method registers event handlers for response events that
        track failed HTTP requests (4xx, 5xx status codes) for debugging.
        """
        def handle_response(response: Any) -> None:
            """Capture failed network requests."""
            if response.status >= 400:
                self._failed_requests.append(
                    f"[{response.status}] {response.request.method} {response.url}"
                )
        
        self.page.on("response", handle_response)
    
    @allure.step("Navigate to {path}")
    def navigate(self, path: str = "", timeout: Optional[int] = None) -> None:
        """
        Navigate to a URL path relative to the base URL.
        
        This method constructs the full URL by combining base_url and the provided path,
        then navigates the browser to that location. The navigation appears as a step
        in Allure reports with the full URL visible.
        
        Args:
            path (str): Relative path to navigate to (e.g., "/login", "/dashboard")
                       If empty string, navigates to base_url
            timeout (Optional[int]): Maximum navigation time in milliseconds
                                     Defaults to Playwright's default (30000ms)
        
        Example:
            ```python
            page_obj.navigate("/login")  # Goes to {base_url}/login
            page_obj.navigate()          # Goes to {base_url}
            ```
        """
        # Construct full URL
        if path:
            full_url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        else:
            full_url = self.base_url
        
        # Log the navigation
        allure.attach(
            f"Navigating to: {full_url}",
            name="Navigation URL",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Perform navigation
        if timeout:
            self.page.goto(full_url, timeout=timeout)
        else:
            self.page.goto(full_url)
    
    @allure.step("Wait for page to load (state: {state})")
    def wait_for_load(self, state: str = "networkidle", timeout: Optional[int] = None) -> None:
        """
        Wait for the page to reach a specific load state.
        
        This method provides explicit waits for various page load conditions,
        ensuring the page is ready for interaction before proceeding with test actions.
        
        Args:
            state (str): Load state to wait for. Options:
                - "load": Wait for load event (fired when page and resources loaded)
                - "domcontentloaded": Wait for DOMContentLoaded event (DOM ready)
                - "networkidle": Wait for no network connections for 500ms (default)
                - "commit": Wait for network response received and document started loading
            timeout (Optional[int]): Maximum wait time in milliseconds
                                     Defaults to Playwright's default (30000ms)
        
        Raises:
            TimeoutError: If page doesn't reach the specified state within timeout
        
        Example:
            ```python
            page_obj.navigate("/dashboard")
            page_obj.wait_for_load("networkidle")  # Ensure all AJAX calls complete
            ```
        """
        # Cast state to Any to avoid mypy literal type checking
        state_param: Any = state
        if timeout:
            self.page.wait_for_load_state(state_param, timeout=timeout)
        else:
            self.page.wait_for_load_state(state_param)
        
        allure.attach(
            f"Page reached load state: {state}",
            name="Load State",
            attachment_type=allure.attachment_type.TEXT
        )
    
    @allure.step("Capture screenshot: {name}")
    def capture_screenshot(self, name: Optional[str] = None, full_page: bool = False) -> bytes:
        """
        Capture a screenshot of the current page and attach it to Allure report.
        
        This method takes a screenshot and automatically attaches it to the Allure
        test report, providing visual evidence of the page state at this point in
        the test execution.
        
        Args:
            name (Optional[str]): Descriptive name for the screenshot in Allure report
                                 Defaults to "Screenshot" if not provided
            full_page (bool): Whether to capture the full scrollable page (True)
                             or just the visible viewport (False, default)
        
        Returns:
            bytes: Screenshot image data as bytes
        
        Example:
            ```python
            # Capture viewport screenshot
            page_obj.capture_screenshot("After Login")
            
            # Capture full page screenshot
            page_obj.capture_screenshot("Full Dashboard View", full_page=True)
            ```
        """
        screenshot_name = name or "Screenshot"
        screenshot_bytes = self.page.screenshot(full_page=full_page)
        
        allure.attach(
            screenshot_bytes,
            name=screenshot_name,
            attachment_type=allure.attachment_type.PNG
        )
        
        return screenshot_bytes
    
    def get_console_errors(self) -> List[str]:
        """
        Retrieve all console error messages captured during page lifecycle.
        
        This method returns browser console errors that have been collected since
        the page object was instantiated. Useful for debugging unexpected failures
        or validating that no JavaScript errors occurred during test execution.
        
        Returns:
            List[str]: List of console error messages in format "[error] message text"
        
        Example:
            ```python
            page_obj.navigate("/dashboard")
            page_obj.wait_for_load()
            
            # Check for JavaScript errors
            errors = page_obj.get_console_errors()
            assert len(errors) == 0, f"Console errors detected: {errors}"
            ```
        """
        if self._console_errors:
            # Attach console errors to Allure report for visibility
            allure.attach(
                "\n".join(self._console_errors),
                name="Console Errors",
                attachment_type=allure.attachment_type.TEXT
            )
        
        return self._console_errors.copy()
    
    def get_failed_network_requests(self) -> List[str]:
        """
        Retrieve all failed network requests captured during page lifecycle.
        
        This method returns HTTP requests that received error responses (4xx, 5xx)
        since the page object was instantiated. Useful for debugging broken links,
        missing resources, or API errors during test execution.
        
        Returns:
            List[str]: List of failed requests in format "[status] METHOD url"
        
        Example:
            ```python
            page_obj.navigate("/dashboard")
            page_obj.wait_for_load()
            
            # Check for failed requests
            failed = page_obj.get_failed_network_requests()
            assert len(failed) == 0, f"Failed requests detected: {failed}"
            ```
        """
        if self._failed_requests:
            # Attach failed requests to Allure report for visibility
            allure.attach(
                "\n".join(self._failed_requests),
                name="Failed Network Requests",
                attachment_type=allure.attachment_type.TEXT
            )
        
        return self._failed_requests.copy()
    
    # Utility methods for stable locator strategies
    
    def find_by_role(
        self,
        role: str,
        name: Optional[str] = None,
        exact: bool = False
    ) -> Any:
        """
        Locate element by ARIA role - the most stable locator strategy.
        
        This is the PREFERRED locator method as it relies on semantic HTML and
        ARIA attributes that reflect the element's purpose rather than implementation
        details like CSS classes.
        
        Args:
            role (str): ARIA role (e.g., "button", "link", "textbox", "heading")
            name (Optional[str]): Accessible name to filter by (aria-label, text content)
            exact (bool): Whether name matching should be exact (True) or substring (False)
        
        Returns:
            Locator: Playwright locator for the element
        
        Example:
            ```python
            # Find by role only
            submit_btn = page_obj.find_by_role("button")
            
            # Find by role and accessible name
            login_btn = page_obj.find_by_role("button", name="Login")
            
            # Find with exact name match
            heading = page_obj.find_by_role("heading", name="Welcome", exact=True)
            ```
        """
        # Cast role to Any to avoid mypy literal type checking
        role_param: Any = role
        kwargs: Dict[str, Any] = {}
        if name is not None:
            kwargs["name"] = name
        if exact:
            kwargs["exact"] = exact
        
        return self.page.get_by_role(role_param, **kwargs)
    
    def find_by_label(self, text: str, exact: bool = False) -> Any:
        """
        Locate form input by its associated label text.
        
        This method is RECOMMENDED for form inputs as it uses the semantic relationship
        between labels and inputs, which is stable and accessibility-friendly.
        
        Args:
            text (str): Label text to search for
            exact (bool): Whether text matching should be exact (True) or substring (False)
        
        Returns:
            Locator: Playwright locator for the associated input element
        
        Example:
            ```python
            # Find input by label
            username_input = page_obj.find_by_label("Username")
            username_input.fill("testuser")
            
            # Exact label match
            email_input = page_obj.find_by_label("Email Address", exact=True)
            ```
        """
        return self.page.get_by_label(text, exact=exact)
    
    def find_by_test_id(self, test_id: str) -> Any:
        """
        Locate element by data-testid attribute.
        
        This method is ACCEPTABLE when semantic locators (role/label) are insufficient.
        Test IDs are explicit markers for testing and remain stable across styling changes.
        
        Args:
            test_id (str): Value of the data-testid attribute
        
        Returns:
            Locator: Playwright locator for the element
        
        Example:
            ```python
            # In HTML: <div data-testid="user-profile-card">...</div>
            profile_card = page_obj.find_by_test_id("user-profile-card")
            
            # Test IDs are preferred over CSS classes
            # GOOD: find_by_test_id("submit-form")
            # AVOID: page.locator(".btn-primary.submit")
            ```
        """
        return self.page.get_by_test_id(test_id)
    
    def wait_for_url(
        self,
        url_pattern: str,
        timeout: Optional[int] = None,
        wait_until: str = "load"
    ) -> None:
        """
        Wait for the browser URL to match a specific pattern.
        
        Useful for asserting navigation completed successfully, especially after
        clicking links or submitting forms that trigger page transitions.
        
        Args:
            url_pattern (str): URL pattern to match (can be string or regex)
            timeout (Optional[int]): Maximum wait time in milliseconds
            wait_until (str): Load state to wait for after URL matches
                             Options: "load", "domcontentloaded", "networkidle", "commit"
        
        Example:
            ```python
            page_obj.find_by_role("button", name="Login").click()
            page_obj.wait_for_url("/dashboard")  # Assert navigation occurred
            ```
        """
        # Cast wait_until to Any to avoid mypy literal type checking
        wait_until_param: Any = wait_until
        if timeout:
            self.page.wait_for_url(url_pattern, timeout=timeout, wait_until=wait_until_param)
        else:
            self.page.wait_for_url(url_pattern, wait_until=wait_until_param)
    
    def get_current_url(self) -> str:
        """
        Get the current page URL.
        
        Returns:
            str: Current page URL
        
        Example:
            ```python
            current_url = page_obj.get_current_url()
            assert "/dashboard" in current_url
            ```
        """
        return self.page.url
    
    def get_page_content(self) -> str:
        """
        Get the full HTML content of the current page.
        
        Useful for debugging or performing custom assertions on page source.
        
        Returns:
            str: Full HTML content of the page
        
        Example:
            ```python
            content = page_obj.get_page_content()
            assert "Welcome" in content
            
            # Attach to Allure for debugging
            allure.attach(content, "Page Source", allure.attachment_type.HTML)
            ```
        """
        return self.page.content()
    
    def evaluate_javascript(self, expression: str) -> Any:
        """
        Execute JavaScript expression in the browser context.
        
        Allows custom JavaScript execution for advanced scenarios not covered
        by standard Playwright methods. Use sparingly as it couples tests to
        implementation details.
        
        Args:
            expression (str): JavaScript expression to evaluate
        
        Returns:
            Any: Result of the JavaScript evaluation
        
        Example:
            ```python
            # Get localStorage value
            token = page_obj.evaluate_javascript("localStorage.getItem('authToken')")
            
            # Scroll to element
            page_obj.evaluate_javascript("window.scrollTo(0, document.body.scrollHeight)")
            ```
        """
        return self.page.evaluate(expression)
    
    def locator(self, selector: str) -> Any:
        """
        Fallback method to create a locator using a CSS selector.
        
        WARNING: Use this method as a LAST RESORT only when semantic locators
        (role, label, test_id) are not feasible. CSS selectors are brittle and
        break easily when styling or structure changes.
        
        Args:
            selector (str): CSS selector string
        
        Returns:
            Locator: Playwright locator for the element
        
        Example:
            ```python
            # AVOID if possible - brittle selector
            element = page_obj.locator(".btn-primary.submit")
            
            # PREFER semantic alternatives:
            # - page_obj.find_by_role("button", name="Submit")
            # - page_obj.find_by_test_id("submit-button")
            ```
        """
        return self.page.locator(selector)

