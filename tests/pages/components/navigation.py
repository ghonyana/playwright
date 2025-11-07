"""
Navigation Component Module

This module provides a reusable NavigationComponent class that represents common
navigation bars, menus, and navigation elements appearing across multiple pages.
Following the Page Object Pattern, this component encapsulates navigation-related
element locators and interaction methods with stable ARIA-based selectors.

Component Pattern:
-----------------
Components are smaller, reusable Page Objects representing UI elements that appear
across multiple pages (navigation bars, modals, footers, etc.). They inherit from
BasePage to access Playwright functionality and provide high-level interaction methods.

Stable Locator Strategy:
------------------------
This component prioritizes stable locators following the user directive:
1. ARIA roles (get_by_role) - Primary strategy for semantic elements
2. Accessible names/labels - For elements with aria-label attributes
3. Test IDs (data-testid) - When semantic selectors are insufficient
4. AVOID: Brittle CSS classes and XPath expressions

Usage Example:
-------------
```python
# In a page object
from tests.pages.components.navigation import NavigationComponent
from tests.pages.base_page import BasePage

class DashboardPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.navigation = NavigationComponent(page)
    
    def navigate_to_profile(self):
        self.navigation.navigate_to_section("Profile")

# In a test
def test_navigation(page: Page):
    dashboard = DashboardPage(page)
    dashboard.navigate("/dashboard")
    
    # Use navigation component
    dashboard.navigation.navigate_to_section("Settings")
    dashboard.navigation.open_user_menu()
    dashboard.navigation.click_logout()
```

Integration Points:
------------------
- BasePage: Inherits Playwright page access and common utilities
- Allure: Hierarchical test step reporting for navigation actions
- Page Objects: Imported and used by multiple page objects for navigation
"""

from typing import Optional, List, Dict

import allure
from playwright.sync_api import Page

from tests.pages.base_page import BasePage


class NavigationComponent(BasePage):
    """
    Reusable navigation component for navigation bars, menus, and navigation elements.
    
    This component encapsulates common navigation interactions across the application,
    providing stable ARIA-based locators and high-level methods for navigation actions.
    Supports both desktop and mobile responsive navigation patterns.
    
    Attributes:
        page (Page): Playwright Page instance (inherited from BasePage)
        base_url (str): Base URL of application (inherited from BasePage)
    
    Locator Properties:
        main_navigation: Primary navigation container element
        navigation_links: All navigation links within the main nav
        user_menu_button: Button to open user menu dropdown
        user_menu_dropdown: User menu dropdown container
        logout_link: Logout menu item within user menu
        home_link: Home navigation link
        breadcrumb_nav: Breadcrumb navigation container
        hamburger_menu: Mobile navigation menu button
    
    Example Usage:
        ```python
        # Initialize in a page object
        class HomePage(BasePage):
            def __init__(self, page: Page):
                super().__init__(page)
                self.nav = NavigationComponent(page)
        
        # Use in tests
        home_page = HomePage(page)
        home_page.nav.navigate_to_section("About")
        home_page.nav.is_section_active("About")  # Returns True
        
        # User menu interactions
        home_page.nav.open_user_menu()
        home_page.nav.click_logout()
        
        # Breadcrumb navigation
        breadcrumbs = home_page.nav.get_breadcrumb_items()
        assert breadcrumbs == ["Home", "Dashboard", "Settings"]
        ```
    """
    
    def __init__(self, page: Page, base_url: Optional[str] = None):
        """
        Initialize the NavigationComponent with a Playwright Page instance.
        
        Args:
            page (Page): Playwright Page instance from pytest fixture
            base_url (Optional[str]): Base URL override; defaults to BASE_URL env var
        
        Raises:
            ValueError: If neither base_url parameter nor BASE_URL env var is provided
        
        Example:
            ```python
            # In a page object
            def __init__(self, page: Page):
                super().__init__(page)
                self.navigation = NavigationComponent(page)
            ```
        """
        super().__init__(page, base_url)
    
    # Stable Locator Properties
    # -------------------------
    # These properties provide lazy-evaluated locators for navigation elements
    # using stable ARIA roles, accessible names, and test IDs.
    
    @property
    def main_navigation(self):
        """
        Locate the primary navigation container using ARIA navigation role.
        
        Returns:
            Locator: Playwright locator for the main navigation element
        
        Example HTML:
            <nav role="navigation" aria-label="Main navigation">...</nav>
        
        Usage:
            ```python
            nav = self.main_navigation
            assert nav.is_visible()
            ```
        """
        return self.page.get_by_role("navigation").first
    
    @property
    def navigation_links(self):
        """
        Locate all navigation links within the main navigation container.
        
        Returns:
            Locator: Playwright locator for all navigation links
        
        Example HTML:
            <nav role="navigation">
                <a href="/home">Home</a>
                <a href="/about">About</a>
            </nav>
        
        Usage:
            ```python
            links = self.navigation_links.all()
            link_texts = [link.inner_text() for link in links]
            ```
        """
        return self.main_navigation.get_by_role("link")
    
    @property
    def user_menu_button(self):
        """
        Locate the user menu button using ARIA role and accessible name.
        
        Returns:
            Locator: Playwright locator for the user menu button
        
        Example HTML:
            <button role="button" aria-label="User Menu">...</button>
            OR
            <button data-testid="user-menu">...</button>
        
        Usage:
            ```python
            self.user_menu_button.click()
            ```
        """
        # Try ARIA role with name first (most stable)
        button_locator = self.page.get_by_role("button", name="User Menu")
        
        # Fallback to test ID if ARIA not available
        if button_locator.count() == 0:
            return self.page.get_by_test_id("user-menu")
        
        return button_locator
    
    @property
    def user_menu_dropdown(self):
        """
        Locate the user menu dropdown container using ARIA menu role.
        
        Returns:
            Locator: Playwright locator for the user menu dropdown
        
        Example HTML:
            <div role="menu" aria-label="User menu">...</div>
        
        Usage:
            ```python
            assert self.user_menu_dropdown.is_visible()
            ```
        """
        return self.page.get_by_role("menu")
    
    @property
    def logout_link(self):
        """
        Locate the logout menu item within the user menu.
        
        Returns:
            Locator: Playwright locator for the logout link/button
        
        Example HTML:
            <a role="menuitem" href="/logout">Logout</a>
            OR
            <button role="menuitem">Logout</button>
        
        Usage:
            ```python
            self.logout_link.click()
            ```
        """
        return self.page.get_by_role("menuitem", name="Logout")
    
    @property
    def home_link(self):
        """
        Locate the Home navigation link.
        
        Returns:
            Locator: Playwright locator for the home link
        
        Example HTML:
            <a role="link" href="/">Home</a>
        
        Usage:
            ```python
            self.home_link.click()
            ```
        """
        return self.page.get_by_role("link", name="Home")
    
    @property
    def breadcrumb_nav(self):
        """
        Locate the breadcrumb navigation container.
        
        Returns:
            Locator: Playwright locator for the breadcrumb navigation
        
        Example HTML:
            <nav role="navigation" aria-label="Breadcrumb">...</nav>
        
        Usage:
            ```python
            breadcrumbs = self.breadcrumb_nav.get_by_role("link").all()
            ```
        """
        return self.page.get_by_role("navigation", name="Breadcrumb")
    
    @property
    def hamburger_menu(self):
        """
        Locate the mobile hamburger menu button.
        
        Returns:
            Locator: Playwright locator for the hamburger menu button
        
        Example HTML:
            <button role="button" aria-label="Menu">...</button>
            OR
            <button data-testid="hamburger-menu">...</button>
        
        Usage:
            ```python
            if self.hamburger_menu.is_visible():
                self.hamburger_menu.click()
            ```
        """
        # Try ARIA role with "Menu" name first
        button_locator = self.page.get_by_role("button", name="Menu")
        
        # Fallback to test ID if ARIA not available
        if button_locator.count() == 0:
            return self.page.get_by_test_id("hamburger-menu")
        
        return button_locator
    
    # High-Level Interaction Methods
    # ------------------------------
    # These methods provide business-readable navigation actions with Allure reporting.
    
    @allure.step("Navigate to section: {section_name}")
    def navigate_to_section(self, section_name: str, exact_match: bool = False) -> None:
        """
        Navigate to a specific section by clicking the corresponding navigation link.
        
        This method locates a navigation link by its accessible name and clicks it,
        triggering navigation to that section. The navigation action appears as a
        step in Allure reports with the section name visible.
        
        Args:
            section_name (str): Name of the section to navigate to (e.g., "About", "Settings")
            exact_match (bool): Whether to match the section name exactly (default: False)
        
        Raises:
            TimeoutError: If the navigation link is not found within the default timeout
        
        Example:
            ```python
            # Navigate to About section
            nav.navigate_to_section("About")
            
            # Navigate with exact name matching
            nav.navigate_to_section("Settings", exact_match=True)
            
            # In Gherkin step definition
            @when('the user navigates to "{section}"')
            def navigate_to_section(nav_component, section):
                nav_component.navigate_to_section(section)
            ```
        """
        # Try to find the link within the main navigation first
        try:
            link = self.navigation_links.get_by_text(section_name, exact=exact_match)
            
            # Ensure link is visible before clicking
            link.wait_for(state="visible", timeout=5000)
            
            allure.attach(
                f"Clicking navigation link: {section_name}",
                name="Navigation Action",
                attachment_type=allure.attachment_type.TEXT
            )
            
            link.click()
            
            # Wait for navigation to complete
            self.wait_for_load()
            
        except Exception as e:
            # Capture screenshot on failure for debugging
            self.capture_screenshot(f"Navigation to {section_name} Failed")
            allure.attach(
                f"Failed to navigate to section '{section_name}': {str(e)}",
                name="Navigation Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Open user menu")
    def open_user_menu(self, timeout: Optional[int] = 5000) -> None:
        """
        Open the user menu dropdown by clicking the user menu button.
        
        This method clicks the user menu button and waits for the dropdown menu
        to become visible, ensuring the menu is ready for interaction.
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for menu to appear
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            TimeoutError: If the user menu doesn't appear within the timeout period
        
        Example:
            ```python
            # Open user menu
            nav.open_user_menu()
            
            # Verify menu is visible
            assert nav.user_menu_dropdown.is_visible()
            
            # In test with custom timeout
            nav.open_user_menu(timeout=10000)
            ```
        """
        try:
            # Check if menu is already open
            if self.user_menu_dropdown.is_visible():
                allure.attach(
                    "User menu is already open",
                    name="Menu State",
                    attachment_type=allure.attachment_type.TEXT
                )
                return
            
            # Click user menu button
            self.user_menu_button.wait_for(state="visible", timeout=timeout)
            self.user_menu_button.click()
            
            # Wait for dropdown to appear
            self.user_menu_dropdown.wait_for(state="visible", timeout=timeout)
            
            allure.attach(
                "User menu opened successfully",
                name="Menu State",
                attachment_type=allure.attachment_type.TEXT
            )
            
        except Exception as e:
            self.capture_screenshot("Open User Menu Failed")
            allure.attach(
                f"Failed to open user menu: {str(e)}",
                name="Menu Open Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Close user menu")
    def close_user_menu(self, timeout: Optional[int] = 5000) -> None:
        """
        Close the user menu dropdown if it's currently open.
        
        This method attempts to close the user menu by clicking the user menu button
        again (toggle behavior) or by clicking outside the menu area. It verifies
        the menu is no longer visible after the action.
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for menu to close
                                     Defaults to 5000ms (5 seconds)
        
        Example:
            ```python
            # Open and then close menu
            nav.open_user_menu()
            nav.close_user_menu()
            
            # Verify menu is closed
            assert not nav.user_menu_dropdown.is_visible()
            ```
        """
        try:
            # Check if menu is already closed
            if not self.user_menu_dropdown.is_visible():
                allure.attach(
                    "User menu is already closed",
                    name="Menu State",
                    attachment_type=allure.attachment_type.TEXT
                )
                return
            
            # Click user menu button to toggle close
            self.user_menu_button.click()
            
            # Wait for dropdown to disappear
            self.user_menu_dropdown.wait_for(state="hidden", timeout=timeout)
            
            allure.attach(
                "User menu closed successfully",
                name="Menu State",
                attachment_type=allure.attachment_type.TEXT
            )
            
        except Exception as e:
            self.capture_screenshot("Close User Menu Failed")
            allure.attach(
                f"Failed to close user menu: {str(e)}",
                name="Menu Close Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Click logout from user menu")
    def click_logout(self, timeout: Optional[int] = 5000) -> None:
        """
        Execute the logout flow by opening the user menu and clicking logout.
        
        This method provides a complete logout interaction: opening the user menu
        if it's not already open, clicking the logout link, and waiting for the
        logout action to complete (typically redirects to login page).
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for each step
                                     Defaults to 5000ms (5 seconds)
        
        Raises:
            TimeoutError: If user menu or logout link is not found within timeout
        
        Example:
            ```python
            # Logout from any page
            nav.click_logout()
            
            # Verify redirection to login
            assert "/login" in nav.get_current_url()
            
            # In Gherkin step definition
            @when("the user logs out")
            def user_logs_out(nav_component):
                nav_component.click_logout()
            ```
        """
        try:
            # Try dropdown menu pattern first (user menu -> logout link)
            try:
                # Ensure user menu is open
                self.open_user_menu(timeout=timeout)
                
                # Wait for logout link to be visible
                self.logout_link.wait_for(state="visible", timeout=timeout)
                
                allure.attach(
                    "Clicking logout link in dropdown menu",
                    name="Logout Action",
                    attachment_type=allure.attachment_type.TEXT
                )
                
                # Click logout
                self.logout_link.click()
                
            except Exception as dropdown_error:
                # Fallback: Try direct logout button (no dropdown menu)
                allure.attach(
                    f"Dropdown menu pattern failed: {str(dropdown_error)}\nTrying direct logout button",
                    name="Logout Pattern Fallback",
                    attachment_type=allure.attachment_type.TEXT
                )
                
                # Try to find a direct logout button by test-id or aria-label
                logout_button = self.page.get_by_test_id("logout-button").or_(
                    self.page.get_by_role("button", name="Log Out")
                ).or_(
                    self.page.get_by_role("button", name="Logout")
                )
                
                # Wait for and click the direct logout button
                logout_button.wait_for(state="visible", timeout=timeout)
                logout_button.click()
                
                allure.attach(
                    "Clicked direct logout button",
                    name="Logout Action",
                    attachment_type=allure.attachment_type.TEXT
                )
            
            # Wait for logout to complete (page navigation)
            self.wait_for_load()
            
            allure.attach(
                f"Logout completed, current URL: {self.get_current_url()}",
                name="Logout Result",
                attachment_type=allure.attachment_type.TEXT
            )
            
        except Exception as e:
            self.capture_screenshot("Logout Failed")
            allure.attach(
                f"Failed to logout: {str(e)}",
                name="Logout Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise
    
    @allure.step("Get breadcrumb navigation items")
    def get_breadcrumb_items(self) -> List[str]:
        """
        Retrieve the list of breadcrumb navigation items as text.
        
        This method extracts all breadcrumb items from the breadcrumb navigation
        container and returns them as a list of strings, representing the current
        navigation path through the application.
        
        Returns:
            List[str]: List of breadcrumb text items in order from root to current page
        
        Raises:
            TimeoutError: If breadcrumb navigation is not found
        
        Example:
            ```python
            # Get breadcrumb items
            breadcrumbs = nav.get_breadcrumb_items()
            assert breadcrumbs == ["Home", "Products", "Electronics", "Laptops"]
            
            # Verify current page in breadcrumbs
            assert breadcrumbs[-1] == "Laptops"
            
            # In Gherkin assertion
            @then('the breadcrumb shows "{expected_path}"')
            def verify_breadcrumb(nav_component, expected_path):
                breadcrumbs = nav_component.get_breadcrumb_items()
                assert " > ".join(breadcrumbs) == expected_path
            ```
        """
        try:
            # Wait for breadcrumb navigation to be present
            self.breadcrumb_nav.wait_for(state="visible", timeout=5000)
            
            # Get all links within breadcrumb (typically <a> or <span> elements)
            breadcrumb_links = self.breadcrumb_nav.get_by_role("link").all()
            
            # If no links found, try getting all text content (for non-link breadcrumbs)
            if not breadcrumb_links:
                # Some breadcrumbs use spans or list items instead of links
                breadcrumb_container = self.breadcrumb_nav
                breadcrumb_text = breadcrumb_container.inner_text()
                
                # Split by common breadcrumb separators
                for separator in [" > ", " / ", " | ", ">"]:
                    if separator in breadcrumb_text:
                        items = [item.strip() for item in breadcrumb_text.split(separator)]
                        allure.attach(
                            f"Breadcrumbs (via text split): {items}",
                            name="Breadcrumb Items",
                            attachment_type=allure.attachment_type.TEXT
                        )
                        return items
                
                # If no separator found, return as single item
                items = [breadcrumb_text.strip()]
            else:
                # Extract text from each link
                items = [link.inner_text().strip() for link in breadcrumb_links]
            
            allure.attach(
                f"Breadcrumbs: {items}",
                name="Breadcrumb Items",
                attachment_type=allure.attachment_type.TEXT
            )
            
            return items
            
        except Exception as e:
            self.capture_screenshot("Get Breadcrumbs Failed")
            allure.attach(
                f"Failed to retrieve breadcrumbs: {str(e)}",
                name="Breadcrumb Error",
                attachment_type=allure.attachment_type.TEXT
            )
            # Return empty list instead of raising to allow graceful degradation
            return []
    
    @allure.step("Check if section '{section_name}' is active")
    def is_section_active(self, section_name: str, timeout: Optional[int] = 2000) -> bool:
        """
        Check if a navigation section is currently active (selected/highlighted).
        
        This method determines if a navigation link is marked as active, typically
        indicated by an ARIA attribute (aria-current="page"), CSS class, or other
        active state marker.
        
        Args:
            section_name (str): Name of the section to check
            timeout (Optional[int]): Maximum wait time in milliseconds to find the link
                                     Defaults to 2000ms (2 seconds)
        
        Returns:
            bool: True if the section is active, False otherwise
        
        Example:
            ```python
            # Check if Dashboard is active
            assert nav.is_section_active("Dashboard")
            
            # Navigate and verify active state
            nav.navigate_to_section("Settings")
            assert nav.is_section_active("Settings")
            assert not nav.is_section_active("Dashboard")
            
            # In Gherkin assertion
            @then('the "{section}" section should be active')
            def verify_active_section(nav_component, section):
                assert nav_component.is_section_active(section)
            ```
        """
        try:
            # Find the navigation link by text
            link = self.navigation_links.get_by_text(section_name, exact=False)
            
            # Wait briefly for link to exist
            link.wait_for(state="attached", timeout=timeout)
            
            # Check for aria-current attribute (most semantic indicator)
            aria_current = link.get_attribute("aria-current")
            if aria_current in ["page", "true", "location"]:
                allure.attach(
                    f"Section '{section_name}' is active (aria-current={aria_current})",
                    name="Active Section Status",
                    attachment_type=allure.attachment_type.TEXT
                )
                return True
            
            # Check for common active class names (fallback)
            class_attr = link.get_attribute("class") or ""
            active_classes = ["active", "selected", "current", "is-active", "is-current"]
            
            is_active = any(active_class in class_attr for active_class in active_classes)
            
            allure.attach(
                f"Section '{section_name}' active status: {is_active} (class={class_attr})",
                name="Active Section Status",
                attachment_type=allure.attachment_type.TEXT
            )
            
            return is_active
            
        except Exception as e:
            allure.attach(
                f"Could not determine active status for '{section_name}': {str(e)}",
                name="Active Section Error",
                attachment_type=allure.attachment_type.TEXT
            )
            # Return False if link not found or error occurs
            return False
    
    @allure.step("Wait for navigation elements to load")
    def wait_for_navigation_load(self, timeout: Optional[int] = 10000) -> None:
        """
        Wait for navigation elements to be fully loaded and visible.
        
        This method ensures the main navigation container and its links are present
        and visible before proceeding with interactions. Useful for pages where
        navigation loads asynchronously or after initial page render.
        
        Args:
            timeout (Optional[int]): Maximum wait time in milliseconds for navigation
                                     Defaults to 10000ms (10 seconds)
        
        Raises:
            TimeoutError: If navigation elements don't load within the timeout period
        
        Example:
            ```python
            # Wait for navigation after page load
            page_obj.navigate("/dashboard")
            page_obj.navigation.wait_for_navigation_load()
            
            # Now safe to interact with navigation
            page_obj.navigation.navigate_to_section("Profile")
            
            # In conftest.py fixture
            @pytest.fixture
            def dashboard_page(page):
                dashboard = DashboardPage(page)
                dashboard.navigate("/dashboard")
                dashboard.navigation.wait_for_navigation_load()
                return dashboard
            ```
        """
        try:
            # Wait for main navigation container to be visible
            self.main_navigation.wait_for(state="visible", timeout=timeout)
            
            # Wait for at least one navigation link to be present
            # This ensures navigation content has loaded, not just the container
            self.navigation_links.first.wait_for(state="visible", timeout=timeout)
            
            # Give a brief moment for any JavaScript enhancements to complete
            self.page.wait_for_timeout(200)
            
            allure.attach(
                "Navigation elements loaded successfully",
                name="Navigation Load Status",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Optional: Capture screenshot of loaded navigation for verification
            self.capture_screenshot("Navigation Loaded")
            
        except Exception as e:
            self.capture_screenshot("Navigation Load Failed")
            allure.attach(
                f"Failed to load navigation elements: {str(e)}",
                name="Navigation Load Error",
                attachment_type=allure.attachment_type.TEXT
            )
            raise

