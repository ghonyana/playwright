"""
Page Objects Package

This package contains Page Object Model (POM) implementations for the test automation
framework. The Page Object Pattern creates an abstraction layer between test code and
UI implementation details, improving test maintainability and readability.

Package Structure:
-----------------
- base_page.py: BasePage class providing common functionality for all page objects
- login_page.py: LoginPage for authentication UI interactions
- dashboard_page.py: DashboardPage for post-login main interface
- user_profile_page.py: UserProfilePage for account settings and profile management
- components/: Reusable UI components (navigation, modals, etc.)

Stable Locator Strategy:
------------------------
All page objects in this package follow the stable locator hierarchy per user directive:
1. ARIA roles (get_by_role) - Preferred for semantic elements
2. Accessible labels (get_by_label) - For form inputs with labels
3. Test IDs (get_by_test_id) - When semantic options insufficient
4. NEVER use brittle CSS class selectors or complex XPath expressions

This strategy ensures:
- Tests remain stable across UI refactoring and styling changes
- Better accessibility compliance testing
- Business-readable test code
- Reduced maintenance burden

Integration with Test Framework:
--------------------------------
Page objects integrate seamlessly with:
- pytest fixtures: Instantiated with Playwright Page instances
- pytest-bdd step definitions: Called from Gherkin steps for BDD scenarios
- MCP servers: Use MCP client for deterministic test data management
- Allure reporting: Automatic step documentation and screenshot capture

Usage Examples:
--------------

# Direct usage in pytest tests
```python
from tests.pages import LoginPage, DashboardPage

def test_user_login(page: Page):
    login_page = LoginPage(page)
    login_page.navigate_to_login()
    login_page.login("user@example.com", "password123")
    login_page.verify_successful_login()
    
    dashboard_page = DashboardPage(page)
    dashboard_page.verify_dashboard_loaded()
```

# Usage in pytest-bdd step definitions
```python
from pytest_bdd import given, when, then
from tests.pages import LoginPage

@given("the user is on the login page")
def navigate_to_login(login_page: LoginPage):
    login_page.navigate_to_login()

@when("the user logs in with valid credentials")
def user_logs_in(login_page: LoginPage):
    login_page.login("user@example.com", "SecurePass123!")

@then("the user should be logged in successfully")
def verify_login_success(login_page: LoginPage):
    login_page.verify_successful_login()
```

# Integration with MCP server for test data
```python
from tests.pages import LoginPage, UserProfilePage
from tests.helpers.mcp_client import MCPClient

def test_profile_update_with_seeded_user(page: Page, mcp_client: MCPClient):
    # Seed deterministic test user via MCP
    user = mcp_client.seed_user(role="customer", email="test@example.com")
    
    # Login with seeded credentials
    login_page = LoginPage(page)
    login_page.navigate_to_login()
    login_page.login(user['email'], user['password'])
    login_page.verify_successful_login()
    
    # Update profile
    profile_page = UserProfilePage(page)
    profile_page.navigate_to_profile()
    profile_page.update_profile(first_name="Jane", last_name="Doe")
    profile_page.verify_profile_saved()
```

Best Practices:
--------------
1. Always use page objects in tests, never direct Playwright API calls
2. Keep page object methods business-readable (e.g., login(), not fill_form_and_click_button())
3. Use stable locators in order of preference: role > label > test-id
4. Leverage BasePage utilities (navigate, wait_for_load, capture_screenshot)
5. Add Allure step decorators to page object methods for detailed reporting
6. Handle optional elements gracefully (check visibility before interaction)
7. Return meaningful data from getter methods for flexible assertions
8. Keep page objects focused on a single page or logical view

Maintenance Guidelines:
----------------------
When UI changes occur:
- Update locators in page objects, not in test files
- Prefer updating locator strategies over updating test logic
- If multiple tests break, the issue is likely in a page object
- Use BasePage's stable locator methods to future-proof selectors
- Test page objects in isolation before running full test suites

For more information, see:
- docs/page_objects.md: Comprehensive Page Object Pattern guide
- docs/writing_tests.md: Test writing guidelines with page objects
- tests/pages/base_page.py: BasePage implementation and utilities
"""

# Import page object classes for re-export
from tests.pages.base_page import BasePage
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage
from tests.pages.user_profile_page import UserProfilePage

# Public API - defines what's available when importing from tests.pages
__all__ = [
    "BasePage",
    "LoginPage",
    "DashboardPage",
    "UserProfilePage",
]

# Version information
__version__ = "1.0.0"

# Package metadata
__author__ = "Test Automation Framework Team"
__description__ = "Page Object Model implementations for UI test automation"
