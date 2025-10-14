"""
Components Package - Reusable UI Component Objects

This package provides reusable UI component abstractions that represent common interface
elements appearing across multiple pages. Components follow the Page Object Pattern,
encapsulating locators and interaction methods for elements like navigation bars, modals,
footers, and form widgets.

Purpose and Architecture:
------------------------
Components are specialized Page Objects that represent UI elements shared across multiple
pages in the application. Rather than duplicating modal logic or navigation logic in every
page object, components provide a single source of truth for interacting with these
reusable elements.

Benefits of Component Objects:
- DRY (Don't Repeat Yourself): Centralized logic for common UI elements
- Maintainability: Update component locators in one place when UI changes
- Testability: Components can be tested independently
- Composability: Page objects compose multiple components for complex interactions
- Stable Locators: Components enforce ARIA-based stable selector strategies

Available Components:
--------------------
This package exports the following reusable component classes:

1. ModalComponent
   - Purpose: Interact with modal dialogs, alerts, and confirmation popups
   - Key Methods: wait_for_modal_open(), click_confirm(), get_modal_content()
   - Locator Strategy: ARIA dialog role, button roles with accessible names
   - Use Cases: Confirmation dialogs, alert messages, form modals

2. NavigationComponent
   - Purpose: Interact with navigation bars, menus, and breadcrumbs
   - Key Methods: navigate_to_section(), open_user_menu(), click_logout()
   - Locator Strategy: ARIA navigation role, link roles, menu items
   - Use Cases: Main navigation, user menus, breadcrumb navigation

Usage Examples:
--------------
Components can be imported directly from this package for clean, readable imports:

```python
# Clean import from components package
from tests.pages.components import ModalComponent, NavigationComponent

# Use in a page object
from tests.pages.base_page import BasePage
from playwright.sync_api import Page

class DashboardPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        # Compose page object with reusable components
        self.navigation = NavigationComponent(page)
        self.modal = ModalComponent(page)
    
    def delete_user_account(self):
        '''Execute account deletion with modal confirmation.'''
        # Trigger delete action
        self.find_by_role("button", name="Delete Account").click()
        
        # Use modal component for confirmation flow
        self.modal.wait_for_modal_open()
        assert "permanently delete" in self.modal.get_modal_content()
        self.modal.click_confirm()
        self.modal.wait_for_modal_close()
    
    def navigate_to_profile(self):
        '''Navigate to user profile using navigation component.'''
        self.navigation.navigate_to_section("Profile")

# Use in a BDD step definition
from tests.pages.components import NavigationComponent

@when("the user navigates to {section}")
def navigate_to_section(page: Page, section: str):
    nav = NavigationComponent(page)
    nav.navigate_to_section(section)

@when("the user logs out")
def user_logs_out(page: Page):
    nav = NavigationComponent(page)
    nav.click_logout()
```

Design Principles:
-----------------
All components in this package adhere to the following design principles:

1. Stable Locators First
   - Prioritize ARIA roles (role="dialog", role="navigation", role="button")
   - Use accessible names and labels (aria-label, aria-labelledby)
   - Fall back to data-testid attributes when semantic selectors insufficient
   - AVOID brittle CSS classes and XPath expressions

2. High-Level Business Methods
   - Method names reflect user actions, not implementation details
   - Example: navigate_to_section() not click_nav_link()
   - Methods encapsulate complex interaction sequences
   - Hide wait conditions and retry logic from callers

3. Allure Integration
   - All public methods decorated with @allure.step for reporting
   - Screenshot capture on failures for debugging
   - Meaningful step names with parameter interpolation

4. Isolation and Reusability
   - Components don't depend on specific page objects
   - Accept Playwright Page instance as constructor parameter
   - Can be instantiated independently for testing
   - No shared mutable state between component instances

5. Playwright Best Practices
   - Use expect() assertions with auto-waiting and retry logic
   - Property-based locators for lazy evaluation
   - Timeout parameters with sensible defaults
   - Explicit wait methods for async operations

Integration with Page Objects:
------------------------------
Page objects compose components to build page-specific functionality:

```python
class UserManagementPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        # Compose components
        self.navigation = NavigationComponent(page)
        self.delete_modal = ModalComponent(page)
        self.confirm_modal = ModalComponent(page)
    
    def delete_selected_user(self, username: str):
        # Page-specific action
        self.find_by_role("row", name=username).get_by_role("button", name="Delete").click()
        
        # Reusable component interaction
        self.delete_modal.wait_for_modal_open()
        self.delete_modal.verify_modal_contains_text(f"Delete {username}")
        self.delete_modal.click_confirm()
```

Adding New Components:
---------------------
When adding new reusable components to this package:

1. Create a new Python module in tests/pages/components/ (e.g., footer.py)
2. Define a component class inheriting from BasePage
3. Implement stable locator properties using ARIA roles
4. Add high-level interaction methods with @allure.step decorators
5. Import and export the component in this __init__.py file
6. Update the docstring above to document the new component
7. Add usage examples and integration patterns

Example new component structure:
```python
# tests/pages/components/footer.py
from tests.pages.base_page import BasePage
import allure

class FooterComponent(BasePage):
    '''Reusable footer component for site-wide footer interactions.'''
    
    @property
    def footer_container(self):
        return self.page.get_by_role("contentinfo")
    
    @allure.step("Navigate to {link_name} in footer")
    def click_footer_link(self, link_name: str):
        link = self.footer_container.get_by_role("link", name=link_name)
        link.click()
        self.wait_for_load()
```

Then add to this __init__.py:
```python
from tests.pages.components.footer import FooterComponent

__all__ = [
    "ModalComponent",
    "NavigationComponent",
    "FooterComponent",  # New component
]
```

Error Handling:
--------------
This package implements graceful error handling for import failures. If a component
module cannot be imported (e.g., due to missing dependencies or circular imports),
an ImportError is raised with a descriptive message explaining which component failed
and why. This ensures clear error messages during development and test execution.

Version and Compatibility:
-------------------------
Package: tests.pages.components
Framework: pytest + Playwright
Python Requirement: 3.9+
Dependencies: playwright, allure-pytest

For more information on the Page Object Pattern and component design, see:
- docs/page_objects.md
- docs/writing_tests.md
- docs/architecture.md
"""

# Explicit imports with error handling for graceful failure messages
try:
    from tests.pages.components.modal import ModalComponent
except ImportError as e:
    raise ImportError(
        f"Failed to import ModalComponent from tests.pages.components.modal. "
        f"Ensure the modal.py module exists and all its dependencies are installed. "
        f"Original error: {e}"
    ) from e

try:
    from tests.pages.components.navigation import NavigationComponent
except ImportError as e:
    raise ImportError(
        f"Failed to import NavigationComponent from tests.pages.components.navigation. "
        f"Ensure the navigation.py module exists and all its dependencies are installed. "
        f"Original error: {e}"
    ) from e


# Explicit public API definition
# This __all__ list controls what gets exported when using "from tests.pages.components import *"
# and provides explicit documentation of the package's public interface
__all__ = [
    "ModalComponent",
    "NavigationComponent",
]


# Package metadata for introspection and documentation
__version__ = "1.0.0"
__author__ = "Test Automation Framework"
__package_name__ = "tests.pages.components"


# Module-level docstring verification for documentation tools
def _validate_exports():
    """
    Internal validation function to ensure all exported components are properly imported.
    
    This function is called on module import to verify that all components declared in
    __all__ are actually available in the module namespace. Helps catch import errors
    early and provides clear error messages.
    
    Raises:
        AssertionError: If any component in __all__ is not available in the module
    """
    current_module = __import__(__name__)
    for component_name in __all__:
        if not hasattr(current_module, component_name):
            raise AssertionError(
                f"Component '{component_name}' is declared in __all__ but not available "
                f"in module namespace. Check for import errors above."
            )


# Run validation on module import
_validate_exports()
