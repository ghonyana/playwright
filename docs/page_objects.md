# Page Object Pattern Guide

## Table of Contents

1. [Overview](#overview)
2. [Stable Locator Strategy](#stable-locator-strategy)
3. [ARIA Roles and Semantic Selectors](#aria-roles-and-semantic-selectors)
4. [Test ID Strategy](#test-id-strategy)
5. [BasePage Class Structure](#basepage-class-structure)
6. [Example Page Object Implementations](#example-page-object-implementations)
7. [Reusable Components](#reusable-components)
8. [Best Practices](#best-practices)
9. [Integration with Step Definitions](#integration-with-step-definitions)
10. [Playwright-Specific Features](#playwright-specific-features)
11. [Common Patterns and Anti-Patterns](#common-patterns-and-anti-patterns)
12. [Testing Page Objects](#testing-page-objects)
13. [Maintenance and Refactoring](#maintenance-and-refactoring)

---

## Overview

### What is the Page Object Pattern?

The Page Object Pattern is a design pattern that creates an object-oriented abstraction layer between test code and the user interface. Each page or component in the application under test is represented by a Python class that encapsulates:

- **Element locators**: Strategies for finding UI elements
- **Interaction methods**: Functions that perform actions on elements
- **Navigation logic**: Methods for moving between pages
- **Assertions**: Methods to verify page state

### Purpose and Benefits

**Primary Purpose**: Separate test logic from UI implementation details to create maintainable, readable, and reusable test automation code.

**Key Benefits**:

1. **Maintainability**: UI changes require updates in only one place (the page object), not scattered across hundreds of test files
2. **Reusability**: Common interactions (login, navigation, form submission) are defined once and reused across multiple tests
3. **Readability**: Tests read like business scenarios, not technical implementation details
4. **Test Isolation**: Page objects encapsulate UI complexity, keeping tests focused on business logic
5. **Type Safety**: Python type hints provide IDE autocomplete and catch errors before runtime
6. **Collaboration**: Non-technical stakeholders can understand test intent without knowing Playwright API

### When to Use Page Objects

**✅ Use Page Objects For**:
- **All UI interactions** in BDD step definitions
- **Reusable components** (navigation, modals, forms) used across multiple pages
- **Complex workflows** requiring multiple element interactions
- **Dynamic content** with conditional element visibility
- **Multi-step processes** (checkout flows, registration wizards)

**⚠️ Direct Playwright Calls Acceptable For**:
- **One-off utility scripts** not part of the test suite
- **Quick debugging** in development console
- **Performance testing** where abstraction overhead matters
- **Proof-of-concept** exploratory testing (convert to page objects once proven)

### Relationship to BDD Step Definitions

In a BDD test framework using pytest-bdd, the interaction flow is:

```
Gherkin Feature File → Step Definition → Page Object → Playwright API → Browser
```

**Example**:

```gherkin
# tests/features/authentication.feature
Scenario: Successful login with valid credentials
  Given the user is on the login page
  When the user logs in with valid credentials
  Then the user should see the dashboard
```

```python
# tests/step_definitions/auth_steps.py
from pytest_bdd import given, when, then
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage

@given("the user is on the login page")
def user_on_login_page(login_page: LoginPage):
    login_page.navigate()

@when("the user logs in with valid credentials")
def user_logs_in(login_page: LoginPage, test_user):
    login_page.login(test_user.email, test_user.password)

@then("the user should see the dashboard")
def user_sees_dashboard(dashboard_page: DashboardPage):
    assert dashboard_page.is_visible()
```

```python
# tests/pages/login_page.py
class LoginPage:
    def navigate(self):
        self.page.goto("/login")
    
    def login(self, email: str, password: str):
        self.page.get_by_label("Email").fill(email)
        self.page.get_by_label("Password").fill(password)
        self.page.get_by_role("button", name="Sign In").click()
```

**Notice**: The step definition reads like business language, delegating technical details to the page object.

---

## Stable Locator Strategy

### The Locator Priority Hierarchy

**CRITICAL**: The stability and maintainability of your test suite depends on choosing the right locator strategy. Follow this priority order:

```
1. ARIA Roles + Accessible Names  (BEST - semantic, stable, accessible)
   ↓
2. data-testid Attributes         (GOOD - explicit test contracts)
   ↓
3. Semantic Selectors             (ACCEPTABLE - HTML5 semantics)
   ↓
4. CSS Classes                    (AVOID - brittle, implementation-dependent)
   ↓
5. XPath Expressions              (AVOID - complex, position-dependent)
```

### Why Prioritize ARIA Roles?

**Advantages**:
- ✅ **Accessibility-First**: If your app is accessible, your tests benefit automatically
- ✅ **Framework-Agnostic**: ARIA roles don't change when CSS frameworks are swapped
- ✅ **Designer-Proof**: Visual redesigns don't break ARIA semantics
- ✅ **Cross-Browser**: Consistent behavior across Chromium, Firefox, WebKit
- ✅ **Self-Documenting**: `get_by_role('button', name='Submit')` is human-readable

**Real-World Example**:

```python
# ❌ BRITTLE: CSS class selector (breaks when Tailwind classes change)
page.locator(".btn.btn-primary.px-4.py-2.rounded-lg")

# ❌ BRITTLE: XPath with position (breaks when DOM structure changes)
page.locator("//div[@class='container']/div[2]/button[1]")

# ✅ STABLE: ARIA role with accessible name
page.get_by_role("button", name="Submit Order")
```

### Why Avoid CSS Classes and XPath?

**CSS Classes Are Implementation Details**:
- Change frequently during UI refactoring
- Differ across CSS frameworks (Bootstrap vs. Tailwind vs. Material UI)
- Often auto-generated by build tools (e.g., CSS modules with hashes)
- No semantic meaning for test intent

**XPath Expressions Are Fragile**:
- Position-dependent (breaks when element order changes)
- Complex and hard to read (`//div[@id='root']/section/div[3]/button[2]`)
- Performance overhead in large DOMs
- Difficult to debug when they fail

**When CSS/XPath Might Be Necessary**:
- Legacy applications without ARIA or test IDs
- Third-party components outside your control
- Complex DOM traversal requirements

**If You Must Use CSS/XPath**:
- Document WHY in comments
- Create a ticket to add proper ARIA roles or test IDs
- Isolate brittle selectors in one method to ease future refactoring

---

## ARIA Roles and Semantic Selectors

### Complete ARIA Role Reference

Playwright's `get_by_role()` method supports all standard ARIA roles. Here are the most commonly used in testing:

| Role | Description | Example Usage |
|------|-------------|---------------|
| `button` | Clickable buttons (including `<button>` and `role="button"`) | `page.get_by_role("button", name="Save")` |
| `link` | Hyperlinks (`<a>` elements) | `page.get_by_role("link", name="Contact Us")` |
| `textbox` | Text input fields (`<input type="text">`, `<textarea>`) | `page.get_by_role("textbox", name="Email")` |
| `checkbox` | Checkboxes (`<input type="checkbox">`) | `page.get_by_role("checkbox", name="Remember me")` |
| `radio` | Radio buttons (`<input type="radio">`) | `page.get_by_role("radio", name="Standard Shipping")` |
| `combobox` | Dropdown selects (`<select>`, custom dropdowns) | `page.get_by_role("combobox", name="Country")` |
| `heading` | Headings (`<h1>` through `<h6>`) | `page.get_by_role("heading", name="Welcome")` |
| `table` | Data tables (`<table>`) | `page.get_by_role("table", name="User List")` |
| `row` | Table rows (`<tr>`) | `page.get_by_role("row", name="John Doe")` |
| `cell` | Table cells (`<td>`, `<th>`) | `page.get_by_role("cell", name="Active")` |
| `dialog` | Modal dialogs (`<dialog>`, `role="dialog"`) | `page.get_by_role("dialog", name="Confirm Delete")` |
| `alert` | Alert messages (`role="alert"`) | `page.get_by_role("alert")` |
| `navigation` | Navigation landmarks (`<nav>`, `role="navigation"`) | `page.get_by_role("navigation", name="Main")` |
| `banner` | Page headers (`<header>`, `role="banner"`) | `page.get_by_role("banner")` |
| `contentinfo` | Page footers (`<footer>`, `role="contentinfo"`) | `page.get_by_role("contentinfo")` |
| `main` | Main content area (`<main>`, `role="main"`) | `page.get_by_role("main")` |
| `list` | Lists (`<ul>`, `<ol>`, `role="list"`) | `page.get_by_role("list", name="Shopping Cart")` |
| `listitem` | List items (`<li>`, `role="listitem"`) | `page.get_by_role("listitem", name="Item 1")` |
| `img` | Images (`<img>`, `role="img"`) | `page.get_by_role("img", name="Company Logo")` |

### Using Accessible Names for Precision

Many elements share the same role (e.g., multiple buttons on a page). Use the `name` parameter to target specific elements by their **accessible name**:

**Accessible Name Sources** (in priority order):
1. `aria-label` attribute: `<button aria-label="Close dialog">×</button>`
2. `aria-labelledby` pointing to another element's text
3. Visible text content: `<button>Submit Order</button>`
4. `alt` text for images: `<img alt="User avatar">`
5. `title` attribute (last resort)

**Examples**:

```python
# Multiple buttons - use accessible names to distinguish
page.get_by_role("button", name="Save Draft")
page.get_by_role("button", name="Publish")
page.get_by_role("button", name="Delete")

# Headings by level and name
page.get_by_role("heading", name="User Profile", level=1)
page.get_by_role("heading", name="Contact Information", level=2)

# Links by visible text
page.get_by_role("link", name="Privacy Policy")

# Images by alt text
page.get_by_role("img", name="Product thumbnail")
```

### Playwright's Built-in Locator Methods

Playwright provides several locator methods optimized for accessibility:

```python
# By ARIA role and name
page.get_by_role("button", name="Submit")

# By label text (for form inputs)
page.get_by_label("Email address")

# By placeholder text
page.get_by_placeholder("Enter your email")

# By visible text content
page.get_by_text("Welcome back!")

# By data-testid attribute
page.get_by_test_id("login-form")

# By alt text (images)
page.get_by_alt_text("Company logo")

# By title attribute
page.get_by_title("Close window")
```

### Cross-Browser Compatibility

**Good News**: ARIA roles are part of the W3C standard and work consistently across all browsers supported by Playwright (Chromium, Firefox, WebKit).

**Testing Tip**: Run your test suite in `--browser=all` mode periodically to catch any browser-specific issues:

```bash
pytest --browser=chromium --browser=firefox --browser=webkit
```

---

## Test ID Strategy

### When to Use data-testid Attributes

While ARIA roles should be your first choice, `data-testid` attributes provide a stable fallback when:

1. **No semantic role exists** (e.g., custom SVG icons, decorative elements)
2. **Multiple identical elements** can't be distinguished by accessible name
3. **Dynamic content** makes accessible names unpredictable
4. **Third-party components** lack proper ARIA attributes
5. **Complex UI interactions** require precise targeting

### Naming Conventions for Test IDs

**Best Practices**:

```python
# ✅ GOOD: Descriptive, kebab-case, hierarchical
data-testid="user-profile-edit-button"
data-testid="shopping-cart-item-3"
data-testid="payment-form-submit"

# ❌ BAD: Generic, ambiguous
data-testid="btn1"
data-testid="element"
data-testid="div123"
```

**Naming Pattern**: `<section>-<component>-<action>-<element-type>`

Examples:
- `data-testid="header-navigation-menu-toggle"` - Toggle button in header navigation
- `data-testid="checkout-payment-card-input"` - Card number input in checkout payment section
- `data-testid="user-list-row-5-delete-button"` - Delete button for row 5 in user list

### Adding Test IDs to Your Application

**For React Applications**:

```jsx
// components/LoginForm.jsx
export function LoginForm() {
  return (
    <form data-testid="login-form">
      <input
        type="email"
        aria-label="Email"
        data-testid="login-email-input"
      />
      <input
        type="password"
        aria-label="Password"
        data-testid="login-password-input"
      />
      <button
        type="submit"
        aria-label="Sign In"
        data-testid="login-submit-button"
      >
        Sign In
      </button>
    </form>
  );
}
```

**For Vue Applications**:

```vue
<!-- components/LoginForm.vue -->
<template>
  <form data-testid="login-form">
    <input
      type="email"
      aria-label="Email"
      data-testid="login-email-input"
    />
    <input
      type="password"
      aria-label="Password"
      data-testid="login-password-input"
    />
    <button
      type="submit"
      aria-label="Sign In"
      data-testid="login-submit-button"
    >
      Sign In
    </button>
  </form>
</template>
```

**For Plain HTML**:

```html
<form data-testid="login-form">
  <input
    type="email"
    aria-label="Email"
    data-testid="login-email-input"
  />
  <input
    type="password"
    aria-label="Password"
    data-testid="login-password-input"
  />
  <button
    type="submit"
    aria-label="Sign In"
    data-testid="login-submit-button"
  >
    Sign In
  </button>
</form>
```

### Using Test IDs in Page Objects

```python
# tests/pages/login_page.py
from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
    
    def login(self, email: str, password: str):
        # Prefer ARIA labels when available
        self.page.get_by_label("Email").fill(email)
        self.page.get_by_label("Password").fill(password)
        
        # Use test ID when ARIA role isn't sufficient
        self.page.get_by_test_id("login-submit-button").click()
    
    def get_error_message(self) -> str:
        # Test IDs for dynamic content
        return self.page.get_by_test_id("login-error-message").text_content()
```

### Production vs. Test-Only Test IDs

**Debate**: Should test IDs be present in production builds?

**Option 1: Keep in Production (Recommended)**:
- ✅ Simplifies build pipeline (no conditional compilation)
- ✅ Enables production smoke tests and monitoring
- ✅ Negligible performance/security impact
- ✅ Aids in customer support and debugging
- ❌ Slightly increases HTML size (negligible with compression)

**Option 2: Strip in Production**:
- ✅ Marginally smaller bundle size
- ❌ Requires build-time processing
- ❌ Test and production builds differ
- ❌ Can't run tests against production

**Recommendation**: Keep test IDs in production unless you have strict bundle size constraints.

---

## BasePage Class Structure

### Purpose of BasePage

The `BasePage` class serves as the foundational parent class for all page objects, providing:

1. **Common utilities** shared across all pages (navigation, waiting, screenshots)
2. **Playwright context injection** via fixtures
3. **Standardized error handling** and logging
4. **Reusable interaction patterns** (click-and-wait, fill-and-submit)
5. **Allure integration** for reporting

### Complete BasePage Implementation

```python
# tests/pages/base_page.py
from typing import Optional, Union
from playwright.sync_api import Page, Locator, expect
from urllib.parse import urljoin
import allure
import os

class BasePage:
    """
    Base class for all page objects.
    
    Provides common functionality for browser interactions, navigation,
    and element interaction patterns.
    """
    
    def __init__(self, page: Page):
        """
        Initialize the page object with a Playwright Page instance.
        
        Args:
            page: Playwright Page instance from pytest fixture
        """
        self.page = page
        self.base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    # Navigation Methods
    
    @allure.step("Navigate to {path}")
    def navigate_to(self, path: str) -> None:
        """
        Navigate to a path relative to BASE_URL.
        
        Args:
            path: Relative path (e.g., "/login", "/dashboard")
        
        Example:
            page.navigate_to("/login")  # Goes to http://localhost:3000/login
        """
        url = urljoin(self.base_url, path)
        self.page.goto(url)
    
    @allure.step("Wait for URL to match {pattern}")
    def wait_for_url(self, pattern: Union[str, re.Pattern], timeout: int = 5000) -> None:
        """
        Wait for the URL to match a pattern.
        
        Args:
            pattern: String or regex pattern to match
            timeout: Maximum wait time in milliseconds
        
        Example:
            page.wait_for_url("/dashboard")
            page.wait_for_url(re.compile(r"/users/\d+"))
        """
        self.page.wait_for_url(pattern, timeout=timeout)
    
    @allure.step("Get current URL")
    def get_current_url(self) -> str:
        """Get the current page URL."""
        return self.page.url
    
    # Element Interaction Methods
    
    @allure.step("Click element and wait for navigation")
    def click_and_wait_for_navigation(
        self,
        locator: Locator,
        timeout: int = 5000
    ) -> None:
        """
        Click an element and wait for navigation to complete.
        
        Useful for links and submit buttons that cause page transitions.
        
        Args:
            locator: Playwright locator for the element
            timeout: Maximum wait time in milliseconds
        """
        with self.page.expect_navigation(timeout=timeout):
            locator.click()
    
    @allure.step("Fill form and submit")
    def fill_and_submit(
        self,
        field_locator: Locator,
        value: str,
        submit_locator: Locator
    ) -> None:
        """
        Fill a form field and click submit button.
        
        Args:
            field_locator: Locator for the input field
            value: Value to enter
            submit_locator: Locator for the submit button
        """
        field_locator.fill(value)
        submit_locator.click()
    
    @allure.step("Wait for element to be visible")
    def wait_for_element_visible(
        self,
        locator: Locator,
        timeout: int = 5000
    ) -> None:
        """
        Wait for an element to become visible.
        
        Args:
            locator: Playwright locator for the element
            timeout: Maximum wait time in milliseconds
        """
        expect(locator).to_be_visible(timeout=timeout)
    
    @allure.step("Wait for element to be hidden")
    def wait_for_element_hidden(
        self,
        locator: Locator,
        timeout: int = 5000
    ) -> None:
        """
        Wait for an element to become hidden.
        
        Args:
            locator: Playwright locator for the element
            timeout: Maximum wait time in milliseconds
        """
        expect(locator).to_be_hidden(timeout=timeout)
    
    # Assertion Helpers
    
    def is_visible(self, locator: Locator) -> bool:
        """
        Check if an element is visible without throwing an exception.
        
        Args:
            locator: Playwright locator for the element
        
        Returns:
            True if visible, False otherwise
        """
        try:
            return locator.is_visible()
        except Exception:
            return False
    
    def is_enabled(self, locator: Locator) -> bool:
        """
        Check if an element is enabled.
        
        Args:
            locator: Playwright locator for the element
        
        Returns:
            True if enabled, False otherwise
        """
        try:
            return locator.is_enabled()
        except Exception:
            return False
    
    # Screenshot and Debugging
    
    @allure.step("Take screenshot")
    def take_screenshot(self, name: str) -> None:
        """
        Take a screenshot and attach to Allure report.
        
        Args:
            name: Descriptive name for the screenshot
        """
        screenshot_bytes = self.page.screenshot(full_page=True)
        allure.attach(
            screenshot_bytes,
            name=name,
            attachment_type=allure.attachment_type.PNG
        )
    
    @allure.step("Get page title")
    def get_page_title(self) -> str:
        """Get the current page title."""
        return self.page.title()
    
    @allure.step("Get element text")
    def get_text(self, locator: Locator) -> str:
        """
        Get the text content of an element.
        
        Args:
            locator: Playwright locator for the element
        
        Returns:
            Text content of the element
        """
        return locator.text_content() or ""
    
    # Wait Conditions
    
    def wait_for_load_state(
        self,
        state: str = "networkidle",
        timeout: int = 30000
    ) -> None:
        """
        Wait for the page to reach a specific load state.
        
        Args:
            state: Load state ('load', 'domcontentloaded', 'networkidle')
            timeout: Maximum wait time in milliseconds
        """
        self.page.wait_for_load_state(state, timeout=timeout)
    
    # Utility Methods
    
    def reload_page(self) -> None:
        """Reload the current page."""
        self.page.reload()
    
    def go_back(self) -> None:
        """Navigate back in browser history."""
        self.page.go_back()
    
    def go_forward(self) -> None:
        """Navigate forward in browser history."""
        self.page.go_forward()
```

### Browser Context and Page Injection via Fixtures

Page objects receive the Playwright `Page` instance through pytest fixtures defined in `conftest.py`:

```python
# tests/conftest.py
import pytest
from playwright.sync_api import Page, Browser, BrowserContext
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage

@pytest.fixture
def context(browser: Browser) -> BrowserContext:
    """
    Create a new browser context for each test.
    
    Ensures test isolation - each test gets a fresh context with:
    - Empty cookies
    - No cached data
    - Independent local storage
    """
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York",
        # Enable trace collection for debugging
        record_trace_on_failure=True
    )
    yield context
    context.close()

@pytest.fixture
def page(context: BrowserContext) -> Page:
    """
    Create a new page in the isolated browser context.
    
    Each test receives a fresh page instance.
    """
    page = context.new_page()
    yield page
    page.close()

# Page Object Fixtures

@pytest.fixture
def login_page(page: Page) -> LoginPage:
    """Provide a LoginPage instance for tests."""
    return LoginPage(page)

@pytest.fixture
def dashboard_page(page: Page) -> DashboardPage:
    """Provide a DashboardPage instance for tests."""
    return DashboardPage(page)
```

**Usage in Step Definitions**:

```python
# tests/step_definitions/auth_steps.py
from pytest_bdd import given, when, then

@given("the user is on the login page")
def user_on_login_page(login_page):  # Fixture automatically injected
    login_page.navigate()

@when("the user logs in with valid credentials")
def user_logs_in(login_page, test_user):
    login_page.login(test_user.email, test_user.password)
```

---

## Example Page Object Implementations

### LoginPage Implementation

```python
# tests/pages/login_page.py
from playwright.sync_api import Page
from tests.pages.base_page import BasePage
import allure

class LoginPage(BasePage):
    """
    Page object for the login page.
    
    Encapsulates all interactions with the login form including:
    - Navigation to login page
    - Email and password input
    - Form submission
    - Error message handling
    """
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.path = "/login"
    
    # Locator Properties (using stable selectors)
    
    @property
    def email_input(self):
        """Email input field - using accessible label."""
        return self.page.get_by_label("Email")
    
    @property
    def password_input(self):
        """Password input field - using accessible label."""
        return self.page.get_by_label("Password")
    
    @property
    def submit_button(self):
        """Submit button - using ARIA role and accessible name."""
        return self.page.get_by_role("button", name="Sign In")
    
    @property
    def forgot_password_link(self):
        """Forgot password link - using ARIA role."""
        return self.page.get_by_role("link", name="Forgot password?")
    
    @property
    def error_message(self):
        """Error message alert - using test ID for dynamic content."""
        return self.page.get_by_test_id("login-error-message")
    
    @property
    def remember_me_checkbox(self):
        """Remember me checkbox - using ARIA role and label."""
        return self.page.get_by_role("checkbox", name="Remember me")
    
    # Navigation Methods
    
    @allure.step("Navigate to login page")
    def navigate(self) -> None:
        """Navigate to the login page."""
        self.navigate_to(self.path)
        self.wait_for_load_state("domcontentloaded")
    
    # Interaction Methods
    
    @allure.step("Login with email: {email}")
    def login(self, email: str, password: str) -> None:
        """
        Perform login with provided credentials.
        
        Args:
            email: User email address
            password: User password
        
        Example:
            login_page.login("user@example.com", "SecurePass123")
        """
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.submit_button.click()
    
    @allure.step("Login and wait for dashboard")
    def login_and_wait(self, email: str, password: str) -> None:
        """
        Login and wait for navigation to dashboard.
        
        Use this method when you expect successful login.
        
        Args:
            email: User email address
            password: User password
        """
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.click_and_wait_for_navigation(self.submit_button)
        self.wait_for_url("/dashboard")
    
    @allure.step("Enable remember me")
    def enable_remember_me(self) -> None:
        """Check the 'Remember me' checkbox."""
        if not self.remember_me_checkbox.is_checked():
            self.remember_me_checkbox.check()
    
    @allure.step("Click forgot password link")
    def click_forgot_password(self) -> None:
        """Navigate to password reset page."""
        self.forgot_password_link.click()
        self.wait_for_url("/forgot-password")
    
    # Assertion Methods
    
    def is_login_page_visible(self) -> bool:
        """
        Check if the login page is fully loaded.
        
        Returns:
            True if login form is visible, False otherwise
        """
        return (
            self.is_visible(self.email_input) and
            self.is_visible(self.password_input) and
            self.is_visible(self.submit_button)
        )
    
    def get_error_message_text(self) -> str:
        """
        Get the error message text after failed login.
        
        Returns:
            Error message string, or empty string if no error
        """
        if self.is_visible(self.error_message):
            return self.get_text(self.error_message)
        return ""
    
    def is_error_displayed(self) -> bool:
        """
        Check if an error message is currently displayed.
        
        Returns:
            True if error visible, False otherwise
        """
        return self.is_visible(self.error_message)
    
    def is_submit_button_enabled(self) -> bool:
        """
        Check if the submit button is enabled.
        
        Returns:
            True if enabled, False if disabled
        """
        return self.is_enabled(self.submit_button)
```

### DashboardPage Implementation

```python
# tests/pages/dashboard_page.py
from playwright.sync_api import Page
from tests.pages.base_page import BasePage
from tests.pages.components.navigation import NavigationComponent
import allure

class DashboardPage(BasePage):
    """
    Page object for the user dashboard.
    
    Represents the main dashboard view after successful login.
    Includes navigation, user profile, and dashboard widgets.
    """
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.path = "/dashboard"
        # Initialize reusable components
        self.navigation = NavigationComponent(page)
    
    # Locator Properties
    
    @property
    def welcome_heading(self):
        """Welcome heading - using ARIA role and level."""
        return self.page.get_by_role("heading", name="Welcome", level=1)
    
    @property
    def user_profile_section(self):
        """User profile section - using test ID."""
        return self.page.get_by_test_id("user-profile-section")
    
    @property
    def user_email(self):
        """User email display - using test ID."""
        return self.page.get_by_test_id("user-email")
    
    @property
    def logout_button(self):
        """Logout button - using ARIA role."""
        return self.page.get_by_role("button", name="Logout")
    
    @property
    def dashboard_widgets(self):
        """All dashboard widgets - using test ID."""
        return self.page.get_by_test_id("dashboard-widget")
    
    # Navigation Methods
    
    @allure.step("Navigate to dashboard")
    def navigate(self) -> None:
        """Navigate to the dashboard page."""
        self.navigate_to(self.path)
        self.wait_for_load_state("networkidle")
    
    # Interaction Methods
    
    @allure.step("Logout user")
    def logout(self) -> None:
        """
        Click logout button and wait for redirect to login page.
        """
        self.logout_button.click()
        self.wait_for_url("/login")
    
    @allure.step("Click user profile")
    def go_to_user_profile(self) -> None:
        """Navigate to user profile page."""
        self.user_profile_section.click()
        self.wait_for_url("/profile")
    
    @allure.step("Get widget count")
    def get_widget_count(self) -> int:
        """
        Count the number of dashboard widgets displayed.
        
        Returns:
            Number of visible widgets
        """
        return self.dashboard_widgets.count()
    
    # Assertion Methods
    
    def is_visible(self) -> bool:
        """
        Check if the dashboard page is fully loaded.
        
        Returns:
            True if dashboard elements are visible
        """
        return (
            self.is_visible(self.welcome_heading) and
            self.is_visible(self.user_profile_section)
        )
    
    def get_user_email(self) -> str:
        """
        Get the displayed user email from the profile section.
        
        Returns:
            User email string
        """
        return self.get_text(self.user_email)
    
    def get_welcome_message(self) -> str:
        """
        Get the welcome heading text.
        
        Returns:
            Welcome message string
        """
        return self.get_text(self.welcome_heading)
```

### UserProfilePage Implementation

```python
# tests/pages/user_profile_page.py
from playwright.sync_api import Page
from tests.pages.base_page import BasePage
import allure

class UserProfilePage(BasePage):
    """
    Page object for the user profile page.
    
    Handles user profile viewing and editing operations.
    """
    
    def __init__(self, page: Page):
        super().__init__(page)
        self.path = "/profile"
    
    # Locator Properties
    
    @property
    def edit_profile_button(self):
        """Edit profile button - using ARIA role."""
        return self.page.get_by_role("button", name="Edit Profile")
    
    @property
    def first_name_input(self):
        """First name input - using label."""
        return self.page.get_by_label("First Name")
    
    @property
    def last_name_input(self):
        """Last name input - using label."""
        return self.page.get_by_label("Last Name")
    
    @property
    def save_button(self):
        """Save button - using ARIA role."""
        return self.page.get_by_role("button", name="Save Changes")
    
    @property
    def cancel_button(self):
        """Cancel button - using ARIA role."""
        return self.page.get_by_role("button", name="Cancel")
    
    @property
    def success_message(self):
        """Success message - using ARIA role."""
        return self.page.get_by_role("alert")
    
    # Navigation Methods
    
    @allure.step("Navigate to user profile")
    def navigate(self) -> None:
        """Navigate to the user profile page."""
        self.navigate_to(self.path)
    
    # Interaction Methods
    
    @allure.step("Click edit profile")
    def start_editing(self) -> None:
        """Enter edit mode for profile."""
        self.edit_profile_button.click()
        self.wait_for_element_visible(self.save_button)
    
    @allure.step("Update profile with first_name: {first_name}, last_name: {last_name}")
    def update_profile(self, first_name: str, last_name: str) -> None:
        """
        Update user profile information.
        
        Args:
            first_name: User's first name
            last_name: User's last name
        """
        self.start_editing()
        self.first_name_input.fill(first_name)
        self.last_name_input.fill(last_name)
        self.save_button.click()
        self.wait_for_element_visible(self.success_message)
    
    @allure.step("Cancel profile editing")
    def cancel_editing(self) -> None:
        """Cancel profile editing and discard changes."""
        self.cancel_button.click()
        self.wait_for_element_hidden(self.save_button)
    
    # Assertion Methods
    
    def is_in_edit_mode(self) -> bool:
        """
        Check if profile is in edit mode.
        
        Returns:
            True if save button is visible, False otherwise
        """
        return self.is_visible(self.save_button)
    
    def is_success_message_displayed(self) -> bool:
        """
        Check if success message is shown after save.
        
        Returns:
            True if success alert visible
        """
        return self.is_visible(self.success_message)
```

---

## Reusable Components

### NavigationComponent

```python
# tests/pages/components/navigation.py
from playwright.sync_api import Page, Locator
import allure

class NavigationComponent:
    """
    Reusable component for site navigation (header/sidebar).
    
    Can be instantiated by any page object that includes navigation.
    """
    
    def __init__(self, page: Page):
        self.page = page
    
    # Locator Properties
    
    @property
    def navigation_menu(self):
        """Main navigation menu - using ARIA role."""
        return self.page.get_by_role("navigation", name="Main")
    
    @property
    def home_link(self):
        """Home navigation link."""
        return self.navigation_menu.get_by_role("link", name="Home")
    
    @property
    def dashboard_link(self):
        """Dashboard navigation link."""
        return self.navigation_menu.get_by_role("link", name="Dashboard")
    
    @property
    def profile_link(self):
        """Profile navigation link."""
        return self.navigation_menu.get_by_role("link", name="Profile")
    
    @property
    def settings_link(self):
        """Settings navigation link."""
        return self.navigation_menu.get_by_role("link", name="Settings")
    
    @property
    def menu_toggle_button(self):
        """Mobile menu toggle button - using test ID."""
        return self.page.get_by_test_id("nav-menu-toggle")
    
    # Interaction Methods
    
    @allure.step("Navigate to Home")
    def go_to_home(self) -> None:
        """Click Home link in navigation."""
        self.home_link.click()
    
    @allure.step("Navigate to Dashboard")
    def go_to_dashboard(self) -> None:
        """Click Dashboard link in navigation."""
        self.dashboard_link.click()
    
    @allure.step("Navigate to Profile")
    def go_to_profile(self) -> None:
        """Click Profile link in navigation."""
        self.profile_link.click()
    
    @allure.step("Navigate to Settings")
    def go_to_settings(self) -> None:
        """Click Settings link in navigation."""
        self.settings_link.click()
    
    @allure.step("Toggle mobile menu")
    def toggle_mobile_menu(self) -> None:
        """Toggle mobile navigation menu visibility."""
        self.menu_toggle_button.click()
    
    # Assertion Methods
    
    def is_visible(self) -> bool:
        """Check if navigation menu is visible."""
        return self.navigation_menu.is_visible()
    
    def is_link_active(self, link_name: str) -> bool:
        """
        Check if a navigation link has 'aria-current' attribute.
        
        Args:
            link_name: Name of the link to check
        
        Returns:
            True if link is marked as current page
        """
        link = self.navigation_menu.get_by_role("link", name=link_name)
        return link.get_attribute("aria-current") == "page"
```

### ModalComponent

```python
# tests/pages/components/modal.py
from playwright.sync_api import Page, Locator
import allure

class ModalComponent:
    """
    Reusable component for modal dialogs.
    
    Handles common modal interactions like closing, confirming, and canceling.
    """
    
    def __init__(self, page: Page, modal_name: str):
        """
        Initialize modal component.
        
        Args:
            page: Playwright Page instance
            modal_name: Accessible name of the modal dialog
        """
        self.page = page
        self.modal_name = modal_name
    
    # Locator Properties
    
    @property
    def modal_dialog(self):
        """Modal dialog - using ARIA role and name."""
        return self.page.get_by_role("dialog", name=self.modal_name)
    
    @property
    def close_button(self):
        """Close button (X) - using ARIA label."""
        return self.modal_dialog.get_by_role("button", name="Close")
    
    @property
    def confirm_button(self):
        """Confirm/OK button."""
        return self.modal_dialog.get_by_role("button", name="Confirm")
    
    @property
    def cancel_button(self):
        """Cancel button."""
        return self.modal_dialog.get_by_role("button", name="Cancel")
    
    @property
    def modal_title(self):
        """Modal title heading."""
        return self.modal_dialog.get_by_role("heading", level=2)
    
    @property
    def modal_content(self):
        """Modal content area - using test ID."""
        return self.modal_dialog.get_by_test_id("modal-content")
    
    # Interaction Methods
    
    @allure.step("Close modal using X button")
    def close(self) -> None:
        """Close modal by clicking X button."""
        self.close_button.click()
        self.wait_for_modal_hidden()
    
    @allure.step("Confirm modal action")
    def confirm(self) -> None:
        """Click confirm button in modal."""
        self.confirm_button.click()
        self.wait_for_modal_hidden()
    
    @allure.step("Cancel modal action")
    def cancel(self) -> None:
        """Click cancel button in modal."""
        self.cancel_button.click()
        self.wait_for_modal_hidden()
    
    @allure.step("Wait for modal to appear")
    def wait_for_modal_visible(self, timeout: int = 5000) -> None:
        """
        Wait for modal to become visible.
        
        Args:
            timeout: Maximum wait time in milliseconds
        """
        self.modal_dialog.wait_for(state="visible", timeout=timeout)
    
    @allure.step("Wait for modal to disappear")
    def wait_for_modal_hidden(self, timeout: int = 5000) -> None:
        """
        Wait for modal to become hidden.
        
        Args:
            timeout: Maximum wait time in milliseconds
        """
        self.modal_dialog.wait_for(state="hidden", timeout=timeout)
    
    # Assertion Methods
    
    def is_visible(self) -> bool:
        """Check if modal is currently visible."""
        return self.modal_dialog.is_visible()
    
    def get_title_text(self) -> str:
        """Get the modal title text."""
        return self.modal_title.text_content() or ""
    
    def get_content_text(self) -> str:
        """Get the modal content text."""
        return self.modal_content.text_content() or ""
```

### Usage of Reusable Components

```python
# Example: Using NavigationComponent in DashboardPage
from tests.pages.components.navigation import NavigationComponent

class DashboardPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.navigation = NavigationComponent(page)
    
    def go_to_settings_via_nav(self):
        """Navigate to settings using the navigation menu."""
        self.navigation.go_to_settings()

# Example: Using ModalComponent for confirmation dialogs
from tests.pages.components.modal import ModalComponent

class UserListPage(BasePage):
    def delete_user_with_confirmation(self, user_email: str):
        """Delete a user and handle confirmation modal."""
        # Trigger delete action
        self.get_delete_button_for_user(user_email).click()
        
        # Handle modal
        delete_modal = ModalComponent(self.page, "Confirm Delete")
        delete_modal.wait_for_modal_visible()
        delete_modal.confirm()
```

---

## Best Practices

### 1. One Page Object Per Page or Major Component

**Guideline**: Each page or major UI component should have its own page object class.

```python
# ✅ GOOD: Separate page objects
tests/pages/
├── login_page.py         # Handles /login route
├── dashboard_page.py     # Handles /dashboard route
├── user_profile_page.py  # Handles /profile route
└── settings_page.py      # Handles /settings route

# ❌ BAD: Single monolithic page object
tests/pages/
└── app_page.py  # Contains all pages in one huge file
```

**When to Split Components**:
- Headers/Footers → `NavigationComponent`, `FooterComponent`
- Modals/Dialogs → `ModalComponent`, `ConfirmDialogComponent`
- Forms → `LoginFormComponent`, `RegistrationFormComponent`

### 2. Keep Methods Focused and Single-Purpose

**Guideline**: Each method should do one thing and do it well.

```python
# ✅ GOOD: Focused methods
def fill_email(self, email: str):
    """Fill email field."""
    self.email_input.fill(email)

def fill_password(self, password: str):
    """Fill password field."""
    self.password_input.fill(password)

def click_submit(self):
    """Click submit button."""
    self.submit_button.click()

# ❌ BAD: Overly complex method
def login_and_verify_dashboard_and_check_notifications(self, email, password):
    """Do everything in one method (hard to reuse, test, debug)."""
    self.email_input.fill(email)
    self.password_input.fill(password)
    self.submit_button.click()
    assert self.dashboard_heading.is_visible()
    notifications = self.get_notification_count()
    if notifications > 0:
        self.open_notifications_panel()
    # ... 50 more lines
```

**Exception**: Convenience methods for common workflows are acceptable:

```python
def login(self, email: str, password: str):
    """Convenience method for full login flow."""
    self.fill_email(email)
    self.fill_password(password)
    self.click_submit()
```

### 3. Return Page Objects for Method Chaining

**Guideline**: Methods that navigate to another page should return the new page object.

```python
# ✅ GOOD: Fluent interface with return values
class LoginPage(BasePage):
    def login(self, email: str, password: str) -> 'DashboardPage':
        """
        Login and return dashboard page object.
        
        Returns:
            DashboardPage instance
        """
        self.email_input.fill(email)
        self.password_input.fill(password)
        self.submit_button.click()
        
        # Import here to avoid circular dependency
        from tests.pages.dashboard_page import DashboardPage
        return DashboardPage(self.page)

# Usage in tests
dashboard = login_page.login("user@example.com", "password123")
dashboard.go_to_profile()
```

**Benefits**:
- Clear intent: Method signature shows navigation will occur
- Type safety: IDE autocomplete works for chained methods
- Readability: Tests read like user workflows

### 4. Use Type Hints for IDE Support and Maintainability

**Guideline**: Add type hints to all method parameters and return values.

```python
from typing import Optional
from playwright.sync_api import Page, Locator

class LoginPage(BasePage):
    def __init__(self, page: Page) -> None:
        super().__init__(page)
    
    def login(self, email: str, password: str) -> None:
        ...
    
    def get_error_message(self) -> Optional[str]:
        ...
    
    def is_visible(self) -> bool:
        ...
```

**Benefits**:
- IDE autocomplete and IntelliSense
- Early error detection (with mypy)
- Self-documenting code
- Easier refactoring

### 5. Document Complex Locator Strategies

**Guideline**: Add comments explaining non-obvious locators.

```python
@property
def submit_button(self):
    """
    Submit button - uses test ID because this button has dynamic text
    that changes based on form state ("Continue", "Submit", "Processing").
    
    Test ID ensures stability regardless of button text.
    """
    return self.page.get_by_test_id("checkout-submit-button")

@property
def third_party_widget(self):
    """
    Third-party payment widget - uses CSS selector because vendor
    does not provide ARIA roles or test IDs.
    
    TODO: Request vendor to add aria-label="Payment form"
    """
    return self.page.locator(".stripe-payment-element")
```

### 6. Avoid Test Logic in Page Objects

**Guideline**: Page objects should only contain interactions, not assertions or test logic.

```python
# ✅ GOOD: Page object provides data, test makes assertion
class DashboardPage(BasePage):
    def get_user_name(self) -> str:
        """Return the displayed user name."""
        return self.get_text(self.user_name_element)

# Test file
def test_user_name_displayed(dashboard_page):
    actual_name = dashboard_page.get_user_name()
    assert actual_name == "John Doe", f"Expected 'John Doe', got '{actual_name}'"

# ❌ BAD: Page object contains test assertion
class DashboardPage(BasePage):
    def verify_user_name_is_john_doe(self):
        """Verify user name is John Doe."""
        actual = self.get_text(self.user_name_element)
        assert actual == "John Doe"  # ← Assertion belongs in test, not page object
```

**Exception**: Visibility/existence checks are acceptable:

```python
def is_error_displayed(self) -> bool:
    """Check if error message is visible."""
    return self.is_visible(self.error_message)
```

### 7. Use Properties for Locators

**Guideline**: Define locators as `@property` methods, not in `__init__`.

```python
# ✅ GOOD: Locators as properties (lazy evaluation)
class LoginPage(BasePage):
    @property
    def email_input(self):
        return self.page.get_by_label("Email")
    
    @property
    def submit_button(self):
        return self.page.get_by_role("button", name="Sign In")

# ❌ BAD: Locators in __init__ (evaluated immediately)
class LoginPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.email_input = page.get_by_label("Email")  # ← Evaluated too early
        self.submit_button = page.get_by_role("button", name="Sign In")
```

**Why Properties Are Better**:
- Locators are evaluated when accessed, not when page object is created
- Avoids stale element issues with dynamic content
- Works correctly with Playwright's auto-waiting

---

## Integration with Step Definitions

### How Step Definitions Consume Page Objects

Step definitions act as the glue between Gherkin scenarios and page objects:

```
Feature File (What to test)
    ↓
Step Definition (How to test - high level)
    ↓
Page Object (How to interact with UI - low level)
    ↓
Playwright API (Browser automation)
```

### Fixture Patterns for Page Object Injection

Define page object fixtures in `conftest.py`:

```python
# tests/conftest.py
import pytest
from playwright.sync_api import Page
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage
from tests.pages.user_profile_page import UserProfilePage

@pytest.fixture
def login_page(page: Page) -> LoginPage:
    """Provide LoginPage instance."""
    return LoginPage(page)

@pytest.fixture
def dashboard_page(page: Page) -> DashboardPage:
    """Provide DashboardPage instance."""
    return DashboardPage(page)

@pytest.fixture
def user_profile_page(page: Page) -> UserProfilePage:
    """Provide UserProfilePage instance."""
    return UserProfilePage(page)
```

**Usage in step definitions**:

```python
# tests/step_definitions/auth_steps.py
from pytest_bdd import scenarios, given, when, then
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage

scenarios("../features/authentication.feature")

@given("the user is on the login page")
def user_on_login_page(login_page: LoginPage):
    login_page.navigate()

@when("the user logs in with email '<email>' and password '<password>'")
def user_logs_in(login_page: LoginPage, email: str, password: str):
    login_page.login(email, password)

@then("the user should see the dashboard")
def user_sees_dashboard(dashboard_page: DashboardPage):
    assert dashboard_page.is_visible(), "Dashboard not visible after login"
```

### Sharing Page Objects Across Multiple Step Definitions

Page objects can be reused in multiple step definition files:

```python
# tests/step_definitions/navigation_steps.py
from pytest_bdd import scenarios, when
from tests.pages.dashboard_page import DashboardPage

scenarios("../features/navigation.feature")

@when("the user navigates to their profile")
def navigate_to_profile(dashboard_page: DashboardPage):
    dashboard_page.go_to_user_profile()

# tests/step_definitions/user_steps.py
from pytest_bdd import scenarios, when
from tests.pages.dashboard_page import DashboardPage

scenarios("../features/user_management.feature")

@when("the user views their dashboard")
def view_dashboard(dashboard_page: DashboardPage):
    dashboard_page.navigate()
```

### Example: Complete BDD Integration

**Feature File**:

```gherkin
# tests/features/user_profile.feature
Feature: User Profile Management
  As a logged-in user
  I want to update my profile information
  So that my account details are accurate

  Scenario: Update user profile successfully
    Given the user is logged in
    And the user is on the profile page
    When the user updates their first name to "Jane"
    And the user updates their last name to "Smith"
    And the user saves the profile changes
    Then the user should see a success message
    And the profile should display "Jane Smith"
```

**Step Definitions**:

```python
# tests/step_definitions/profile_steps.py
from pytest_bdd import scenarios, given, when, then, parsers
from tests.pages.login_page import LoginPage
from tests.pages.user_profile_page import UserProfilePage

scenarios("../features/user_profile.feature")

@given("the user is logged in")
def user_is_logged_in(login_page: LoginPage, test_user):
    login_page.navigate()
    login_page.login(test_user.email, test_user.password)

@given("the user is on the profile page")
def user_on_profile_page(user_profile_page: UserProfilePage):
    user_profile_page.navigate()

@when(parsers.parse("the user updates their first name to \"{first_name}\""))
def update_first_name(user_profile_page: UserProfilePage, first_name: str):
    user_profile_page.first_name_input.fill(first_name)

@when(parsers.parse("the user updates their last name to \"{last_name}\""))
def update_last_name(user_profile_page: UserProfilePage, last_name: str):
    user_profile_page.last_name_input.fill(last_name)

@when("the user saves the profile changes")
def save_profile(user_profile_page: UserProfilePage):
    user_profile_page.save_button.click()

@then("the user should see a success message")
def verify_success_message(user_profile_page: UserProfilePage):
    assert user_profile_page.is_success_message_displayed()

@then(parsers.parse("the profile should display \"{full_name}\""))
def verify_profile_name(user_profile_page: UserProfilePage, full_name: str):
    # This would require additional page object methods
    displayed_name = user_profile_page.get_displayed_name()
    assert displayed_name == full_name
```

---

## Playwright-Specific Features

### Automatic Waiting and Actionability Checks

**Key Feature**: Playwright automatically waits for elements to become actionable before performing actions.

**Actionability Checks Include**:
- Element is attached to DOM
- Element is visible
- Element is stable (not animating)
- Element receives events (not covered by another element)
- Element is enabled (not disabled)

**Example**:

```python
# Playwright automatically waits up to 30 seconds (default) for button to be clickable
self.submit_button.click()

# No manual waits needed! This replaces:
# WebDriverWait(driver, 10).until(EC.element_to_be_clickable(submit_button))
```

**Configure Timeout**:

```python
# tests/conftest.py
@pytest.fixture
def context(browser):
    context = browser.new_context()
    context.set_default_timeout(10000)  # 10 seconds
    yield context
    context.close()
```

### Trace Collection on Failures

**Purpose**: Playwright traces capture a complete recording of test execution for debugging.

**Configure in conftest.py**:

```python
# tests/conftest.py
@pytest.fixture
def context(browser):
    context = browser.new_context()
    
    # Start tracing before test
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    
    yield context
    
    # Save trace on failure
    trace_path = "test-results/trace.zip"
    context.tracing.stop(path=trace_path)
    context.close()
```

**View Traces**:

```bash
playwright show-trace test-results/trace.zip
```

**Trace Viewer Features**:
- Timeline of all actions
- DOM snapshots before/after each action
- Network requests
- Console logs
- Screenshots

### Screenshot Capture Capabilities

**Automatic Screenshots on Failure**:

```python
# tests/conftest.py
import pytest

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Take screenshot on test failure."""
    outcome = yield
    result = outcome.get_result()
    
    if result.when == "call" and result.failed:
        page = item.funcargs.get("page")
        if page:
            screenshot_bytes = page.screenshot(full_page=True)
            allure.attach(
                screenshot_bytes,
                name="failure_screenshot",
                attachment_type=allure.attachment_type.PNG
            )
```

**Manual Screenshots in Page Objects**:

```python
def take_screenshot(self, name: str):
    """Capture screenshot and attach to Allure."""
    screenshot_bytes = self.page.screenshot(full_page=True)
    allure.attach(
        screenshot_bytes,
        name=name,
        attachment_type=allure.attachment_type.PNG
    )
```

### Network Request Interception for Testing

**Monitor API Calls**:

```python
# tests/pages/dashboard_page.py
def wait_for_data_load(self):
    """Wait for dashboard data API call to complete."""
    with self.page.expect_response(
        lambda response: "/api/dashboard" in response.url and response.status == 200
    ) as response_info:
        self.page.reload()
    
    response = response_info.value
    assert response.ok, f"Dashboard API call failed: {response.status}"
```

**Mock API Responses**:

```python
# tests/test_dashboard_offline.py
def test_dashboard_displays_cached_data(page, dashboard_page):
    """Test dashboard behavior when API is offline."""
    
    # Mock API to return error
    def handle_route(route):
        route.abort("failed")
    
    page.route("**/api/dashboard", handle_route)
    
    dashboard_page.navigate()
    
    # Verify cached data is displayed
    assert dashboard_page.shows_cached_indicator()
```

---

## Common Patterns and Anti-Patterns

### Pattern: Fluent Interfaces for Readable Test Code

**Example**:

```python
# Page object with fluent interface
class LoginPage(BasePage):
    def fill_email(self, email: str) -> 'LoginPage':
        self.email_input.fill(email)
        return self
    
    def fill_password(self, password: str) -> 'LoginPage':
        self.password_input.fill(password)
        return self
    
    def click_remember_me(self) -> 'LoginPage':
        self.remember_me_checkbox.check()
        return self
    
    def submit(self) -> 'DashboardPage':
        self.submit_button.click()
        from tests.pages.dashboard_page import DashboardPage
        return DashboardPage(self.page)

# Usage: Method chaining
dashboard = (login_page
    .fill_email("user@example.com")
    .fill_password("SecurePass123")
    .click_remember_me()
    .submit())
```

### Pattern: Wait Conditions for Dynamic Content

**Example**:

```python
def wait_for_user_list_loaded(self):
    """Wait until user list has loaded at least one row."""
    self.page.wait_for_function(
        "document.querySelectorAll('[data-testid=\"user-row\"]').length > 0"
    )

def wait_for_spinner_gone(self):
    """Wait for loading spinner to disappear."""
    spinner = self.page.get_by_test_id("loading-spinner")
    spinner.wait_for(state="hidden", timeout=10000)
```

### Anti-Pattern: Hardcoded Waits (time.sleep)

**❌ BAD**:

```python
import time

def login(self, email, password):
    self.email_input.fill(email)
    time.sleep(2)  # ← Never do this!
    self.password_input.fill(password)
    time.sleep(2)  # ← Slows tests unnecessarily
    self.submit_button.click()
    time.sleep(5)  # ← Flaky: What if page takes 6 seconds?
```

**✅ GOOD**:

```python
def login(self, email, password):
    self.email_input.fill(email)  # Playwright waits automatically
    self.password_input.fill(password)
    self.submit_button.click()
    self.wait_for_url("/dashboard")  # Explicit wait for condition
```

### Anti-Pattern: XPath with Positional Indices

**❌ BAD**:

```python
# Breaks when element order changes
first_user_delete_button = page.locator("//tr[1]/td[5]/button")
third_item_in_cart = page.locator("//ul[@id='cart']/li[3]")
```

**✅ GOOD**:

```python
# Stable: Select by content or test ID
first_user_delete_button = page.get_by_test_id("user-row-1-delete")
third_item_in_cart = page.get_by_role("listitem", name="Product C")
```

### Anti-Pattern: CSS Selectors Based on Styling Classes

**❌ BAD**:

```python
# Breaks when CSS framework changes (Bootstrap → Tailwind)
primary_button = page.locator(".btn.btn-primary.btn-lg")
card_header = page.locator(".card-header.bg-blue-500.rounded-t-lg")
```

**✅ GOOD**:

```python
# Stable: Use semantic meaning, not visual styling
primary_button = page.get_by_role("button", name="Submit Order")
card_header = page.get_by_role("heading", name="Order Summary")
```

---

## Testing Page Objects

### Unit Testing Page Object Methods

While page objects primarily support integration tests, you can unit test complex logic:

```python
# tests/unit/test_login_page.py
from unittest.mock import Mock, MagicMock
from tests.pages.login_page import LoginPage

def test_login_page_constructs_correct_url():
    """Test that navigate() builds the correct URL."""
    mock_page = Mock()
    login_page = LoginPage(mock_page)
    
    login_page.navigate()
    
    mock_page.goto.assert_called_once_with("http://localhost:3000/login")

def test_login_fills_both_fields():
    """Test that login() fills email and password."""
    mock_page = MagicMock()
    login_page = LoginPage(mock_page)
    
    # Setup mocks
    email_input = Mock()
    password_input = Mock()
    submit_button = Mock()
    
    mock_page.get_by_label.side_effect = [email_input, password_input]
    mock_page.get_by_role.return_value = submit_button
    
    login_page.login("user@example.com", "password123")
    
    email_input.fill.assert_called_once_with("user@example.com")
    password_input.fill.assert_called_once_with("password123")
    submit_button.click.assert_called_once()
```

### Mocking Playwright Page for Isolated Tests

**Why Mock?**
- Test page object logic without launching a real browser
- Faster test execution
- Isolate page object behavior from Playwright implementation

**Example**:

```python
import pytest
from unittest.mock import Mock, MagicMock
from tests.pages.dashboard_page import DashboardPage

@pytest.fixture
def mock_page():
    """Create a mock Playwright Page."""
    page = MagicMock()
    page.url = "http://localhost:3000/dashboard"
    return page

def test_dashboard_get_widget_count(mock_page):
    """Test widget counting logic."""
    dashboard = DashboardPage(mock_page)
    
    # Mock widget locator to return 3 elements
    mock_widgets = Mock()
    mock_widgets.count.return_value = 3
    mock_page.get_by_test_id.return_value = mock_widgets
    
    count = dashboard.get_widget_count()
    
    assert count == 3
    mock_page.get_by_test_id.assert_called_with("dashboard-widget")
```

### Integration Testing with Real Browsers

**Most page object testing happens via integration tests**:

```python
# tests/ui/test_login_flow.py
import pytest
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage

def test_successful_login_navigation(page, test_user):
    """Full integration test with real browser."""
    login_page = LoginPage(page)
    dashboard_page = DashboardPage(page)
    
    # Execute real browser interactions
    login_page.navigate()
    assert login_page.is_login_page_visible()
    
    login_page.login(test_user.email, test_user.password)
    
    # Verify navigation occurred
    assert dashboard_page.is_visible()
    assert "/dashboard" in page.url
```

---

## Maintenance and Refactoring

### When to Split Large Page Objects

**Signs a page object is too large**:
- File exceeds 300-400 lines
- Multiple unrelated UI sections (navigation + forms + tables)
- Difficult to find specific methods
- Many developers editing simultaneously (merge conflicts)

**Refactoring Strategies**:

**Strategy 1: Extract Components**

```python
# Before: Monolithic DashboardPage
class DashboardPage(BasePage):
    # Navigation methods (10 methods)
    # User profile methods (8 methods)
    # Widgets methods (12 methods)
    # Notifications methods (7 methods)
    # ...300+ lines

# After: Extracted components
class DashboardPage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.navigation = NavigationComponent(page)
        self.profile = UserProfileComponent(page)
        self.widgets = DashboardWidgetsComponent(page)
        self.notifications = NotificationsComponent(page)
```

**Strategy 2: Split by Workflow**

```python
# Split large checkout page into steps
tests/pages/checkout/
├── checkout_cart_page.py       # Shopping cart view
├── checkout_shipping_page.py   # Shipping address form
├── checkout_payment_page.py    # Payment information
└── checkout_confirmation_page.py  # Order confirmation
```

### Handling Page Redesigns with Stable Locators

**Scenario**: UI redesign changes element positions, colors, and class names.

**Impact with Stable Locators**: ✅ Minimal

```python
# Locators using ARIA roles remain unchanged
self.page.get_by_role("button", name="Sign In")  # Still works after redesign

# Test IDs remain unchanged if preserved in new design
self.page.get_by_test_id("login-submit")  # Still works
```

**Impact with Brittle Locators**: ❌ High

```python
# CSS classes changed from Bootstrap to Tailwind
self.page.locator(".btn.btn-primary")  # BREAKS - classes no longer exist

# XPath based on DOM structure changed
self.page.locator("//div[@class='container']/form/button")  # BREAKS - structure changed
```

**Redesign Checklist**:
1. **Before redesign**: Audit all page objects for brittle selectors
2. **During redesign**: Ensure `data-testid` attributes are preserved
3. **After redesign**: Run full test suite to identify breaks
4. **Refactor**: Update only broken locators (should be minimal with stable strategy)

### Version Control Best Practices for Page Objects

**Commit Messages**:

```
# Good commit messages for page object changes
feat: Add UserProfilePage for profile editing tests
fix: Update LoginPage submit button locator after accessibility improvements
refactor: Extract NavigationComponent from DashboardPage
docs: Add docstrings to all LoginPage methods
```

**Code Review Checklist**:
- [ ] Uses stable locators (ARIA roles > test IDs > CSS)
- [ ] Methods are single-purpose and well-named
- [ ] Type hints on all parameters and returns
- [ ] Docstrings explain complex interactions
- [ ] No hardcoded waits (`time.sleep`)
- [ ] No test assertions in page object methods
- [ ] Follows project naming conventions

**Branching Strategy**:
- **Feature branches**: For new page objects or major refactors
- **Bug fix branches**: For locator updates after UI changes
- **Keep page objects in sync**: Don't let page objects diverge between branches

---

## Summary

The Page Object Pattern is essential for building maintainable, scalable test automation. Key takeaways:

1. **Prioritize stable locators**: ARIA roles → data-testid → semantic selectors
2. **Encapsulate UI logic**: Keep tests focused on business logic, not DOM details
3. **Use BasePage**: Inherit common functionality for consistency
4. **Leverage Playwright features**: Auto-waiting, traces, and network interception
5. **Avoid anti-patterns**: No hardcoded waits, no XPath indices, no CSS class selectors
6. **Integrate with BDD**: Page objects make step definitions readable and maintainable
7. **Refactor proactively**: Split large page objects, extract reusable components
8. **Design for change**: Stable locators minimize maintenance when UI changes

By following these patterns and best practices, your test automation suite will remain reliable, readable, and maintainable as your application evolves.

---

## Additional Resources

- [Playwright Python Documentation](https://playwright.dev/python/)
- [pytest-bdd Documentation](https://pytest-bdd.readthedocs.io/)
- [ARIA Roles Reference](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Writing Tests Guide](./writing_tests.md)
- [MCP Servers Documentation](./mcp_servers.md)
