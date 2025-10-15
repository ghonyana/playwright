"""
Dashboard Page Object Module

This module provides the DashboardPage class representing the main application interface
displayed after successful authentication. It implements the Page Object Pattern with
stable ARIA-based locators following the framework's directive to avoid brittle CSS/XPath
selectors and prefer role/name/test-id based element location strategies.

Purpose:
--------
The DashboardPage encapsulates interactions with the post-authentication dashboard view,
including:
- Dashboard heading and welcome message verification
- User menu interactions (open menu, logout)
- Navigation to other application sections
- Main content area access
- Integration with reusable NavigationComponent

Stable Locator Strategy:
------------------------
This page object strictly follows the stable locator hierarchy:
1. ARIA roles with accessible names (get_by_role with name parameter)
2. Test IDs (data-testid attributes) as fallback
3. Semantic text matching for headings and messages
4. NEVER brittle CSS classes or complex XPath expressions

Integration Points:
------------------
- BasePage: Inherits common page object functionality, navigation utilities, and Allure integration
- NavigationComponent: Delegates navigation bar interactions to reusable component
- Playwright: Browser automation via Page instance from pytest fixtures
- Allure: Hierarchical test step reporting with screenshots and diagnostics
- Gherkin Steps: Methods designed for business-readable BDD step definitions

Example Usage in Tests:
----------------------
```python
# In a pytest test
def test_dashboard_access(page: Page):
    dashboard = DashboardPage(page)
    dashboard.navigate_to_dashboard()
    dashboard.verify_dashboard_loaded()
    
    welcome_msg = dashboard.get_welcome_message()
    assert "Welcome" in welcome_msg
    
    dashboard.logout()

# In a Gherkin step definition
@given("the user is on the dashboard")
def user_on_dashboard(dashboard_page: DashboardPage):
    dashboard_page.navigate_to_dashboard()
    dashboard_page.verify_dashboard_loaded()

@when('the user navigates to "{section}"')
def navigate_to_section(dashboard_page: DashboardPage, section: str):
    dashboard_page.navigate_to_section(section)

@when("the user logs out")
def user_logs_out(dashboard_page: DashboardPage):
    dashboard_page.logout()
```

Design Rationale:
----------------
- Inherits from BasePage to reuse navigation, waiting, and screenshot utilities
- Integrates NavigationComponent following DRY principle (Don't Repeat Yourself)
- Each method represents a business action, not implementation details
- Locators are lazy-evaluated properties for efficiency and clarity
- All interactions use Allure step decorators for detailed test reports
- Error handling with automatic screenshots for debugging failures
"""

from typing import Optional, Dict, Any

import allure
from playwright.sync_api import Page, Locator

from tests.pages.base_page import BasePage
from tests.pages.components.navigation import NavigationComponent


# Dashboard route constant for consistent navigation
DASHBOARD_PATH = "/dashboard"


class DashboardPage(BasePage):
    """
    Page Object representing the main dashboard interface after authentication.
    
    The DashboardPage provides high-level methods for interacting with the dashboard
    view, including verifying page load, accessing user menu, navigating to sections,
    and performing logout. All element locators use stable ARIA roles and test IDs
    to ensure test resilience across UI refactoring.
    
    Attributes:
        page (Page): Playwright Page instance (inherited from BasePage)
        base_url (str): Application base URL (inherited from BasePage)
        navigation (NavigationComponent): Reusable navigation component for menu interactions
    
    Locator Properties:
        dashboard_heading: Main dashboard heading element (h1 or h2)
        user_menu_button: Button to open user menu dropdown
        logout_link: Logout menu item within user menu
        welcome_message: Welcome message heading (typically h2)
        main_content: Main content area container
        navigation_links: All navigation links in navigation bar
    
    Action Methods:
        navigate_to_dashboard(): Navigate to dashboard URL and wait for load
        verify_dashboard_loaded(): Assert dashboard heading visible and URL correct
        get_welcome_message(): Retrieve welcome message text content
        open_user_menu(): Open user menu dropdown
        logout(): Execute complete logout flow with verification
        navigate_to_section(section_name): Navigate to specific application section
    
    Example:
        ```python
        # Initialize in test or fixture
        dashboard = DashboardPage(page)
        
        # Navigate and verify
        dashboard.navigate_to_dashboard()
        dashboard.verify_dashboard_loaded()
        
        # Interact with dashboard
        welcome = dashboard.get_welcome_message()
        assert "Welcome, John" in welcome
        
        # Navigate to other sections
        dashboard.navigate_to_section("Profile")
        dashboard.navigate_to_section("Settings")
        
        # Logout
        dashboard.logout()
        ```
    """
    
    def __init__(self, page: Page, base_url: Optional[str] = None):
        """
        Initialize the DashboardPage with a Playwright Page instance.
        
        This constructor calls the BasePage initializer to set up page and base_url,
        then creates a NavigationComponent instance for reusable navigation interactions.
        
        Args:
            page (Page): Playwright Page instance from pytest fixture
            base_url (Optional[str]): Base URL override; defaults to BASE_URL env var
        
        Raises:
            ValueError: If neither base_url parameter nor BASE_URL env var is provided
        
        Example:
            ```python
            # In a pytest fixture
            @pytest.fixture
            def dashboard_page(page: Page):
                return DashboardPage(page)
            
            # In a test with custom base URL
            def test_dashboard_custom_url(page: Page):
                dashboard = DashboardPage(page, base_url="https://staging.example.com")
                dashboard.navigate_to_dashboard()
            ```
        """
        # Initialize BasePage with page and base_url
        super().__init__(page, base_url)
        
        # Initialize NavigationComponent for reusable navigation interactions
        # This follows DRY principle by delegating navigation bar actions to the component
        self.navigation = NavigationComponent(page, base_url)
    
    # ==================================================================================
    # STABLE LOCATOR PROPERTIES
    # ==================================================================================
    # These properties provide lazy-evaluated locators using stable ARIA roles,
    # accessible names, and test IDs. They follow the user directive to avoid
    # brittle CSS selectors and XPath expressions.
    
    @property
    def dashboard_heading(self) -> Locator:
        """
        Locate the main dashboard heading element using ARIA heading role.
        
        This is the primary heading that indicates the user is on the dashboard page,
        typically an h1 or h2 element with text like "Dashboard" or "Main Dashboard".
        
        Returns:
            Locator: Playwright locator for the dashboard heading element
        
        Example HTML:
            <h1 role="heading">Dashboard</h1>
            OR
            <h2>Dashboard</h2>
        
        Usage:
            ```python
            # Verify heading is visible
            assert dashboard_page.dashboard_heading.is_visible()
            
            # Get heading text
            heading_text = dashboard_page.dashboard_heading.inner_text()
            assert heading_text == "Dashboard"
            ```
        """
        return self.page.get_by_role("heading", name="Dashboard")
    
    @property
    def user_menu_button(self) -> Locator:
        """
        Locate the user menu button using ARIA role with accessible name or test ID.
        
        This button opens the user menu dropdown containing profile, settings, and
        logout options. The locator tries ARIA role first, then falls back to test ID.
        
        Returns:
            Locator: Playwright locator for the user menu button
        
        Example HTML:
            <button role="button" aria-label="User Menu">...</button>
            OR
            <button data-testid="user-menu">...</button>
        
        Usage:
            ```python
            # Click to open menu
            dashboard_page.user_menu_button.click()
            
            # Verify button exists
            assert dashboard_page.user_menu_button.is_visible()
            ```
        """
        # Try ARIA role with accessible name first (most stable)
        button_locator = self.page.get_by_role("button", name="User Menu")
        
        # Fallback to test ID if ARIA not available
        if button_locator.count() == 0:
            return self.page.get_by_test_id("user-menu")
        
        return button_locator
    
    @property
    def logout_link(self) -> Locator:
        """
        Locate the logout menu item using ARIA menuitem role or link role.
        
        This element is typically within the user menu dropdown and triggers the logout
        action when clicked. It may be a menuitem, button, or link depending on implementation.
        
        Returns:
            Locator: Playwright locator for the logout link/button
        
        Example HTML:
            <a role="menuitem" href="/logout">Logout</a>
            OR
            <button role="menuitem">Logout</button>
            OR
            <a role="link" href="/logout">Logout</a>
        
        Usage:
            ```python
            # Open menu first, then click logout
            dashboard_page.open_user_menu()
            dashboard_page.logout_link.click()
            ```
        """
        # Try menuitem role first (most semantic for menu items)
        menuitem_locator = self.page.get_by_role("menuitem", name="Logout")
        
        # Fallback to link role if not a menuitem
        if menuitem_locator.count() == 0:
            return self.page.get_by_role("link", name="Logout")
        
        return menuitem_locator
    
    @property
    def welcome_message(self) -> Locator:
        """
        Locate the welcome message heading on the dashboard.
        
        This is typically a secondary heading (h2 or h3) that greets the user with
        personalized text like "Welcome, John" or "Welcome back!".
        
        Returns:
            Locator: Playwright locator for the welcome message element
        
        Example HTML:
            <h2 role="heading">Welcome, John Doe</h2>
            OR
            <h2>Welcome</h2>
        
        Usage:
            ```python
            # Get welcome text
            welcome_text = dashboard_page.welcome_message.inner_text()
            assert "Welcome" in welcome_text
            
            # Verify visibility
            assert dashboard_page.welcome_message.is_visible()
            ```
        """
        # Try heading with level 2 first (common for subheadings)
        heading_locator = self.page.get_by_role("heading", level=2)
        
        # Filter by text containing "Welcome" if multiple h2 elements exist
        welcome_heading = heading_locator.filter(has_text="Welcome").first
        
        # Fallback to generic text search if role-based locator fails
        if welcome_heading.count() == 0:
            return self.page.get_by_text("Welcome", exact=False).first
        
        return welcome_heading
    
    @property
    def main_content(self) -> Locator:
        """
        Locate the main content area of the dashboard using ARIA main role.
        
        This is the primary content container that holds dashboard widgets, data,
        and information. The main landmark role provides semantic meaning and
        accessibility compliance.
        
        Returns:
            Locator: Playwright locator for the main content area
        
        Example HTML:
            <main role="main">
                <!-- Dashboard content here -->
            </main>
            OR
            <div role="main">
                <!-- Dashboard content here -->
            </div>
        
        Usage:
            ```python
            # Verify main content is visible
            assert dashboard_page.main_content.is_visible()
            
            # Get all text within main content
            content_text = dashboard_page.main_content.inner_text()
            
            # Find elements within main content
            widget = dashboard_page.main_content.get_by_role("article").first
            ```
        """
        return self.page.get_by_role("main")
    
    @property
    def navigation_links(self) -> Locator:
        """
        Locate all navigation links in the navigation bar.
        
        This property returns all links within the primary navigation container,
        allowing iteration over navigation options or selection of specific links.
        
        Returns:
            Locator: Playwright locator for all navigation links
        
        Example HTML:
            <nav role="navigation">
                <a href="/home">Home</a>
                <a href="/profile">Profile</a>
                <a href="/settings">Settings</a>
            </nav>
        
        Usage:
            ```python
            # Get all navigation link texts
            links = dashboard_page.navigation_links.all()
            link_texts = [link.inner_text() for link in links]
            assert "Profile" in link_texts
            
            # Click specific link
            dashboard_page.navigation_links.get_by_text("Settings").click()
            ```
        """
        return self.page.get_by_role("navigation").get_by_role("link")
    
    # ==================================================================================
    # HIGH-LEVEL ACTION METHODS
    # ==================================================================================
    # These methods provide business-readable actions for dashboard interactions.
    # All methods use @allure.step decorators for detailed test reporting.
    
    @allure.step("Navigate to dashboard page")
    def navigate_to_dashboard(self, timeout: Optional[int] = None) -> None:
        """
        Navigate to the dashboard page and wait for it to load completely.
        
        This method combines navigation to the dashboard URL with verification that
        the page has loaded. It uses the DASHBOARD_PATH constant for consistent routing
        and waits for network idle state to ensure all AJAX calls complete.
        
        Args:
            timeout (Optional[int]): Maximum navigation time in milliseconds
                                     Defaults to Playwright's default (30000ms)
        
        Raises:
            TimeoutError: If navigation or page load exceeds the timeout period
        
        Example:
            ```python
            # Basic navigation
            dashboard_page.navigate_to_dashboard()
            
            # Navigation with custom timeout
            dashboard_page.navigate_to_dashboard(timeout=60000)
            
            # In Gherkin step definition
            @given("the user is on the dashboard")
            def user_on_dashboard(dashboard_page: DashboardPage):
                dashboard_page.navigate_to_dashboard()
            ```
        """
        try:
            # Navigate to dashboard using BasePage navigate method
            self.navigate(path=DASHBOARD_PATH, timeout=timeout)
            
            # Wait for page to reach network idle state (all AJAX calls complete)
            self.wait_for_load(state="networkidle", timeout=timeout)
            
            allure.attach(
                f"Successfully navigated to dashboard: {self.base_url}{DASHBOARD_PATH}",
                name="Navigation Success",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot for visual verification
            self.capture_screenshot("Dashboard Page Loaded")
            
        except Exception as e:
            # Capture screenshot on navigation failure for debugging
            self.capture_screenshot("Dashboard Navigation Failed")
            allure.attach(
                f"Failed to navigate to dashboard: {str(e)}",
                name="Navigation Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    def get_dashboard_url(self) -> str:
        """
        Get the complete URL for the dashboard page.
        
        Returns:
            str: Full dashboard URL combining base_url and DASHBOARD_PATH
        
        Example:
            >>> dashboard_page.get_dashboard_url()
            'http://localhost:3000/dashboard'
        """
        return f"{self.base_url}{DASHBOARD_PATH}"
    
    def get_section_url(self, section: str) -> str:
        """
        Get the complete URL for a specific dashboard section.
        
        Args:
            section: Section identifier (e.g., "users", "settings", "reports")
        
        Returns:
            str: Full section URL combining base_url and section
        
        Example:
            >>> dashboard_page.get_section_url("users")
            'http://localhost:3000/users'
        """
        return f"{self.base_url}/{section}"
    
    def get_profile_url(self) -> str:
        """
        Get the complete URL for the user profile page.
        
        Returns:
            str: Full profile URL combining base_url and /profile path
        
        Example:
            >>> dashboard_page.get_profile_url()
            'http://localhost:3000/profile'
        """
        return f"{self.base_url}/profile"
    
    def get_account_settings_url(self) -> str:
        """
        Get the complete URL for the account settings page.
        
        Returns:
            str: Full account settings URL combining base_url and /account-settings path
        
        Example:
            >>> dashboard_page.get_account_settings_url()
            'http://localhost:3000/account-settings'
        """
        return f"{self.base_url}/account-settings"
    
    def get_page_heading(self) -> Locator:
        """
        Get the main heading element on the current page.
        
        This method returns the page title heading element using the stable
        data-testid="page-title" selector, which contains the page-specific
        title (e.g., "Dashboard", "Users", "Settings").
        
        Returns:
            Locator: Playwright locator for the main page heading
        
        Example:
            >>> heading = dashboard_page.get_page_heading()
            >>> expect(heading).to_contain_text("Dashboard")
        """
        return self.page.get_by_test_id("page-title")
    
    @allure.step("Verify dashboard page is loaded")
    def verify_dashboard_loaded(self, timeout: Optional[int] = 5000) -> None:
        """
        Verify that the dashboard page has loaded successfully.
        
        This method performs multiple assertions to confirm the dashboard page:
        1. Dashboard heading is visible
        2. Current URL contains the dashboard path
        3. Main content area is present
        
        These checks ensure the page has not only navigated but fully rendered
        the expected dashboard interface.
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for elements
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            AssertionError: If dashboard heading not visible or URL doesn't match
            TimeoutError: If elements don't appear within the timeout period
        
        Example:
            ```python
            # Navigate and verify
            dashboard_page.navigate_to_dashboard()
            dashboard_page.verify_dashboard_loaded()
            
            # Verify after login
            login_page.submit_credentials("user@example.com", "password")
            dashboard_page.verify_dashboard_loaded()
            
            # In Gherkin step definition
            @then("the dashboard page should be displayed")
            def verify_dashboard_displayed(dashboard_page: DashboardPage):
                dashboard_page.verify_dashboard_loaded()
            ```
        """
        try:
            # Wait for dashboard heading to be visible (primary indicator)
            self.dashboard_heading.wait_for(state="visible", timeout=timeout)
            
            # Verify dashboard heading is visible
            assert self.dashboard_heading.is_visible(), "Dashboard heading is not visible"
            
            allure.attach(
                "Dashboard heading is visible",
                name="Heading Check",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Verify URL contains dashboard path
            current_url = self.get_current_url()
            assert DASHBOARD_PATH in current_url, (
                f"Expected URL to contain '{DASHBOARD_PATH}', but got: {current_url}"
            )
            
            allure.attach(
                f"Current URL verified: {current_url}",
                name="URL Check",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Verify main content area is present
            assert self.main_content.is_visible(), "Main content area is not visible"
            
            allure.attach(
                "Dashboard verification successful: heading visible, URL correct, main content present",
                name="Verification Result",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot of verified dashboard
            self.capture_screenshot("Dashboard Verified")
            
        except AssertionError as e:
            # Capture screenshot on assertion failure
            self.capture_screenshot("Dashboard Verification Failed")
            allure.attach(
                f"Dashboard verification failed: {str(e)}",
                name="Verification Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
        except Exception as e:
            # Capture screenshot on unexpected errors
            self.capture_screenshot("Dashboard Verification Error")
            allure.attach(
                f"Unexpected error during dashboard verification: {str(e)}",
                name="Verification Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Get welcome message text")
    def get_welcome_message(self, timeout: Optional[int] = 5000) -> str:
        """
        Retrieve the welcome message text from the dashboard.
        
        This method locates the welcome message element and extracts its text content,
        which typically includes personalized greetings like "Welcome, John Doe" or
        "Welcome back!". Useful for verifying personalization and user context.
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for welcome message
                                     Defaults to 5000ms (5 seconds)
        
        Returns:
            str: Welcome message text content
        
        Raises:
            TimeoutError: If welcome message element is not found within timeout
        
        Example:
            ```python
            # Get and verify welcome message
            welcome = dashboard_page.get_welcome_message()
            assert "Welcome" in welcome
            assert "John Doe" in welcome
            
            # In Gherkin step definition
            @then('the dashboard should show "{expected_message}"')
            def verify_welcome_message(dashboard_page: DashboardPage, expected_message: str):
                actual_message = dashboard_page.get_welcome_message()
                assert expected_message in actual_message
            ```
        """
        try:
            # Wait for welcome message to be visible
            self.welcome_message.wait_for(state="visible", timeout=timeout)
            
            # Extract text content
            welcome_text = self.welcome_message.inner_text().strip()
            
            allure.attach(
                f"Welcome message retrieved: {welcome_text}",
                name="Welcome Message",
                attachment_type=allure.attachment_type.TEXT
            )
            
            return welcome_text
            
        except Exception as e:
            # Capture screenshot on failure
            self.capture_screenshot("Get Welcome Message Failed")
            allure.attach(
                f"Failed to retrieve welcome message: {str(e)}",
                name="Welcome Message Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Open user menu")
    def open_user_menu(self, timeout: Optional[int] = 5000) -> None:
        """
        Open the user menu dropdown by delegating to the NavigationComponent.
        
        This method uses the integrated NavigationComponent to open the user menu,
        following the DRY principle by reusing the component's implementation. It
        ensures the menu is visible before returning control to the test.
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for menu to appear
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            TimeoutError: If user menu doesn't appear within the timeout period
        
        Example:
            ```python
            # Open user menu and verify
            dashboard_page.open_user_menu()
            assert dashboard_page.navigation.user_menu_dropdown.is_visible()
            
            # Open with custom timeout
            dashboard_page.open_user_menu(timeout=10000)
            
            # In Gherkin step definition
            @when("the user opens the user menu")
            def open_user_menu(dashboard_page: DashboardPage):
                dashboard_page.open_user_menu()
            ```
        """
        try:
            # Delegate to NavigationComponent's open_user_menu method
            # This follows DRY principle and maintains consistent behavior
            self.navigation.open_user_menu(timeout=timeout)
            
            allure.attach(
                "User menu opened successfully via NavigationComponent",
                name="User Menu State",
                attachment_type=allure.attachment_type.TEXT
            )
            
        except Exception as e:
            # Error handling and screenshot capture already done by NavigationComponent
            # Re-raise to allow test to handle the failure
            allure.attach(
                f"Failed to open user menu from dashboard: {str(e)}",
                name="User Menu Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Get user menu dropdown element")
    def get_user_menu_dropdown(self) -> Locator:
        """
        Get the user menu dropdown element.
        
        Returns the dropdown menu locator that contains all menu items.
        This element is initially hidden and becomes visible after clicking
        the user menu button.
        
        Returns:
            Locator: The user menu dropdown element
        
        Example:
            ```python
            dropdown = dashboard_page.get_user_menu_dropdown()
            expect(dropdown).to_be_visible()
            ```
        """
        return self.page.get_by_test_id("user-menu-dropdown")
    
    @allure.step("Get all user menu items")
    def get_user_menu_items(self) -> list:
        """
        Get all menu items from the user menu dropdown.
        
        Returns a list of all clickable menu items within the dropdown.
        This is useful for verifying that all expected menu options are present.
        
        Returns:
            list: List of Locator objects for each menu item
        
        Example:
            ```python
            items = dashboard_page.get_user_menu_items()
            item_texts = [item.inner_text() for item in items]
            assert "Profile" in item_texts
            ```
        """
        dropdown = self.get_user_menu_dropdown()
        menu_items = dropdown.get_by_role("menuitem").all()
        return menu_items
    
    @allure.step("Click user menu item: {item_name}")
    def click_user_menu_item(self, item_name: str, timeout: Optional[int] = 5000) -> None:
        """
        Click a specific item in the user menu dropdown.
        
        This method finds a menu item by its visible text and clicks it.
        The menu should be opened before calling this method.
        
        Args:
            item_name (str): The visible text of the menu item to click
            timeout (Optional[int]): Maximum wait time in milliseconds
        
        Raises:
            TimeoutError: If the menu item is not found or not clickable
        
        Example:
            ```python
            dashboard_page.open_user_menu()
            dashboard_page.click_user_menu_item("Profile")
            ```
        """
        try:
            dropdown = self.get_user_menu_dropdown()
            # Find the menu item by its text content
            menu_item = dropdown.get_by_role("menuitem").filter(has_text=item_name)
            menu_item.click(timeout=timeout)
            
            allure.attach(
                f"Clicked menu item: {item_name}",
                name="Menu Item Click",
                attachment_type=allure.attachment_type.TEXT
            )
        except Exception as e:
            allure.attach(
                f"Failed to click menu item '{item_name}': {str(e)}",
                name="Menu Item Click Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Logout from dashboard")
    def logout(self, timeout: Optional[int] = 5000) -> None:
        """
        Execute the complete logout flow and verify redirection.
        
        This method performs the full logout sequence:
        1. Opens the user menu (if not already open)
        2. Clicks the logout link
        3. Waits for logout to complete (typically redirects to login page)
        4. Verifies the URL has changed (no longer on dashboard)
        
        The implementation delegates to NavigationComponent for consistent behavior
        across all pages that use the same navigation component.
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for each step
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            TimeoutError: If any step of the logout flow exceeds the timeout
        
        Example:
            ```python
            # Logout from dashboard
            dashboard_page.logout()
            
            # Verify redirection to login
            assert "/login" in dashboard_page.get_current_url()
            
            # In Gherkin step definition
            @when("the user logs out")
            def user_logs_out(dashboard_page: DashboardPage):
                dashboard_page.logout()
            
            @then("the user should be redirected to the login page")
            def verify_login_redirect(dashboard_page: DashboardPage):
                current_url = dashboard_page.get_current_url()
                assert "/login" in current_url
            ```
        """
        try:
            # Store current URL to verify logout occurred
            initial_url = self.get_current_url()
            
            allure.attach(
                f"Starting logout from: {initial_url}",
                name="Initial URL",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Delegate to NavigationComponent's click_logout method
            # This handles: open menu → click logout → wait for navigation
            self.navigation.click_logout(timeout=timeout)
            
            # Verify URL has changed (logout successful)
            final_url = self.get_current_url()
            
            allure.attach(
                f"Logout completed, redirected to: {final_url}",
                name="Final URL",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot of post-logout page
            self.capture_screenshot("After Logout")
            
            # Assert we're no longer on dashboard (logout successful)
            assert DASHBOARD_PATH not in final_url, (
                f"Still on dashboard after logout. Current URL: {final_url}"
            )
            
        except AssertionError as e:
            # Capture screenshot on assertion failure
            self.capture_screenshot("Logout Verification Failed")
            allure.attach(
                f"Logout verification failed: {str(e)}",
                name="Logout Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
        except Exception as e:
            # Error handling and screenshot already done by NavigationComponent
            # Add additional context for dashboard-specific logout
            allure.attach(
                f"Failed to logout from dashboard: {str(e)}",
                name="Logout Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Navigate to section: {section_name}")
    def navigate_to_section(self, section_name: str, exact_match: bool = False, timeout: Optional[int] = 5000) -> None:
        """
        Navigate to a specific application section using the navigation bar.
        
        This method delegates to the NavigationComponent to click on a navigation
        link by its accessible name, triggering navigation to that section. It follows
        the DRY principle by reusing the component's implementation.
        
        Args:
            section_name (str): Name of the section to navigate to (e.g., "Profile", "Settings")
            exact_match (bool): Whether to match the section name exactly (default: False)
            timeout (Optional[int]): Maximum wait time in milliseconds for navigation
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            TimeoutError: If the navigation link is not found or navigation times out
        
        Example:
            ```python
            # Navigate to Profile section
            dashboard_page.navigate_to_section("Profile")
            
            # Navigate with exact name matching
            dashboard_page.navigate_to_section("User Settings", exact_match=True)
            
            # Navigate with custom timeout
            dashboard_page.navigate_to_section("Reports", timeout=10000)
            
            # In Gherkin step definition
            @when('the user navigates to "{section}"')
            def navigate_to_section(dashboard_page: DashboardPage, section: str):
                dashboard_page.navigate_to_section(section)
            
            @then('the user should be on the "{section}" page')
            def verify_section(dashboard_page: DashboardPage, section: str):
                # Verify navigation succeeded
                assert dashboard_page.navigation.is_section_active(section)
            ```
        """
        try:
            # Delegate to NavigationComponent's navigate_to_section method
            # This follows DRY principle and maintains consistent navigation behavior
            self.navigation.navigate_to_section(section_name, exact_match=exact_match)
            
            # Give page time to load after navigation
            self.wait_for_load(state="networkidle", timeout=timeout)
            
            allure.attach(
                f"Successfully navigated to section: {section_name}",
                name="Section Navigation",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot of destination section
            self.capture_screenshot(f"Section: {section_name}")
            
        except Exception as e:
            # Error handling and screenshot already done by NavigationComponent
            # Add additional context for dashboard navigation
            allure.attach(
                f"Failed to navigate to section '{section_name}' from dashboard: {str(e)}",
                name="Section Navigation Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    # ==================================================================================
    # BREADCRUMB NAVIGATION METHODS
    # ==================================================================================
    
    @allure.step("Navigate to user profile: {user_id}")
    def navigate_to_user_profile(self, user_id: str, timeout: Optional[int] = 5000) -> None:
        """
        Navigate to a specific user's profile page.
        
        This method navigates to the detailed profile page for a specific user,
        typically from the users list page. It constructs the URL based on the
        user ID and waits for the page to load.
        
        Args:
            user_id (str): ID of the user whose profile to view
            timeout (Optional[int]): Maximum wait time in milliseconds for navigation
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            TimeoutError: If navigation times out
        
        Example:
            ```python
            # Navigate to specific user profile
            dashboard_page.navigate_to_section("users")
            dashboard_page.navigate_to_user_profile("test-user-123")
            
            # Verify profile page loaded
            expect(dashboard_page.get_page_heading()).to_contain_text("User Profile")
            ```
        """
        try:
            user_profile_url = self.get_user_profile_url(user_id)
            self.page.goto(user_profile_url, wait_until="networkidle", timeout=timeout)
            
            # Wait for the profile page to be fully loaded
            self.wait_for_load(state="load", timeout=timeout)
            
            # Wait for the page title to appear
            self.page.get_by_test_id("page-title").wait_for(state="visible", timeout=timeout)
            
            allure.attach(
                f"Successfully navigated to user profile: {user_profile_url}",
                name="User Profile Navigation",
                attachment_type=allure.attachment_type.TEXT
            )
            
            self.capture_screenshot(f"User Profile: {user_id}")
            
        except Exception as e:
            self.capture_screenshot("Navigate to User Profile Failed")
            allure.attach(
                f"Failed to navigate to user profile {user_id}: {str(e)}",
                name="User Profile Navigation Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Navigate to edit profile page")
    def navigate_to_edit_profile(self, timeout: Optional[int] = 5000) -> None:
        """
        Navigate to the edit profile page from the current user profile page.
        
        This method clicks the "Edit Profile" link on the user profile page
        to navigate to the profile editing form. It assumes you're already
        on a user profile page.
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for navigation
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            TimeoutError: If edit profile link not found or navigation times out
        
        Example:
            ```python
            # Navigate from profile to edit page
            dashboard_page.navigate_to_user_profile("test-user-123")
            dashboard_page.navigate_to_edit_profile()
            
            # Verify edit page loaded
            expect(dashboard_page.get_page_heading()).to_contain_text("Edit Profile")
            ```
        """
        try:
            # Find and click the edit profile link
            edit_link = self.page.get_by_test_id("edit-profile-link")
            edit_link.wait_for(state="visible", timeout=timeout)
            edit_link.click()
            
            # Wait for navigation to complete
            self.wait_for_load(state="networkidle", timeout=timeout)
            
            allure.attach(
                "Successfully navigated to edit profile page",
                name="Edit Profile Navigation",
                attachment_type=allure.attachment_type.TEXT
            )
            
            self.capture_screenshot("Edit Profile Page")
            
        except Exception as e:
            self.capture_screenshot("Navigate to Edit Profile Failed")
            allure.attach(
                f"Failed to navigate to edit profile: {str(e)}",
                name="Edit Profile Navigation Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    def get_user_profile_url(self, user_id: str) -> str:
        """
        Get the complete URL for a specific user's profile page.
        
        Args:
            user_id (str): ID of the user
        
        Returns:
            str: Full user profile URL
        
        Example:
            >>> dashboard_page.get_user_profile_url("test-user-123")
            'http://localhost:3000/users/test-user-123'
        """
        return f"{self.base_url}/users/{user_id}"
    
    def get_breadcrumb_items(self) -> list:
        """
        Get all breadcrumb navigation items on the current page.
        
        This method locates the breadcrumb navigation and returns all breadcrumb
        items (both links and the current page indicator). The breadcrumbs show
        the navigation hierarchy from Dashboard down to the current page.
        
        Returns:
            list: List of Playwright Locator objects for each breadcrumb item
        
        Example:
            ```python
            # Get and verify breadcrumbs
            breadcrumbs = dashboard_page.get_breadcrumb_items()
            assert len(breadcrumbs) == 3
            expect(breadcrumbs[0]).to_have_text("Dashboard")
            expect(breadcrumbs[1]).to_have_text("Users")
            expect(breadcrumbs[2]).to_have_text("User Profile")
            ```
        """
        breadcrumb_container = self.page.get_by_test_id("breadcrumb")
        breadcrumb_items = breadcrumb_container.locator("li.breadcrumb-item").all()
        return breadcrumb_items
    
    @allure.step("Click breadcrumb: {breadcrumb_text}")
    def click_breadcrumb(self, breadcrumb_text: str, timeout: Optional[int] = 5000) -> None:
        """
        Click on a specific breadcrumb link to navigate up the hierarchy.
        
        This method finds a breadcrumb by its text content and clicks it to
        navigate to that level in the navigation hierarchy. It's used for
        navigating "up" from deeply nested pages.
        
        Args:
            breadcrumb_text (str): Text of the breadcrumb to click (e.g., "Users", "Dashboard")
            timeout (Optional[int]): Maximum wait time in milliseconds for navigation
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            TimeoutError: If breadcrumb not found or navigation times out
        
        Example:
            ```python
            # Navigate up the breadcrumb trail
            dashboard_page.click_breadcrumb("Users")
            
            # Verify navigation
            expect(dashboard_page.page).to_have_url(dashboard_page.get_section_url("users"))
            ```
        """
        try:
            # Find the breadcrumb item containing the text
            breadcrumb_container = self.page.get_by_test_id("breadcrumb")
            breadcrumb_link = breadcrumb_container.get_by_role("link", name=breadcrumb_text, exact=False)
            
            # Wait for it to be visible
            breadcrumb_link.wait_for(state="visible", timeout=timeout)
            
            # Click the breadcrumb
            breadcrumb_link.click()
            
            # Wait for navigation to complete
            self.wait_for_load(state="networkidle", timeout=timeout)
            
            allure.attach(
                f"Successfully clicked breadcrumb: {breadcrumb_text}",
                name="Breadcrumb Click",
                attachment_type=allure.attachment_type.TEXT
            )
            
            self.capture_screenshot(f"After Breadcrumb Click: {breadcrumb_text}")
            
        except Exception as e:
            self.capture_screenshot("Breadcrumb Click Failed")
            allure.attach(
                f"Failed to click breadcrumb '{breadcrumb_text}': {str(e)}",
                name="Breadcrumb Click Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise

