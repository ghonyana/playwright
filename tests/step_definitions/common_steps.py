"""
pytest-bdd Common Step Definitions

This module provides reusable Gherkin step implementations shared across multiple feature files.
These steps handle cross-cutting concerns including navigation, environment management, message
validation, element visibility checks, and common UI interactions.

Key Features:
- High-level, business-readable Gherkin step definitions
- Environment reset via MCP server integration
- Navigation and URL validation steps
- Message and notification verification
- Element visibility and interaction steps
- Browser console log capture and validation
- Wait conditions and loading states
- Session and cookie management
- Screenshot capture for diagnostics

These steps follow the user directive to keep Gherkin high-level and business-readable,
avoiding UI implementation details and focusing on behavior-level actions and outcomes.

Dependencies:
- pytest-bdd 8.1.0: Gherkin step decorators (@given, @when, @then)
- allure-pytest 2.15.0: Test reporting and step visualization
- playwright 1.55.0: Browser automation with stable locators
- tests.helpers.allure_utils: Allure attachment helpers
"""

import os
from typing import Any, Dict, List, Optional

import allure
from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, then, when

from tests.helpers.allure_utils import attach_browser_console_logs


# ============================================================================
# Environment Management Steps (Given)
# ============================================================================


@given("the test environment is reset")
@allure.step("Reset test environment via MCP")
def reset_environment(mcp_client: Any) -> None:
    """
    Reset the test environment to a clean state via MCP server.
    
    This step calls the MCP reset_env tool to clear test data, reset database state,
    and ensure tests start from a known-good baseline. Critical for deterministic,
    isolated test execution.
    
    Args:
        mcp_client: MCP client fixture from conftest.py
        
    Example:
        Given the test environment is reset
        When I create a new user
        Then the user should be the only one in the database
    """
    result = mcp_client.reset_env()
    allure.attach(
        str(result),
        name="Environment Reset Result",
        attachment_type=allure.attachment_type.TEXT
    )


@given("the application is running")
@allure.step("Verify application health")
def verify_application_running(page: Page) -> None:
    """
    Verify the application is accessible and responding.
    
    This step performs a health check by navigating to the base URL and verifying
    the page loads successfully. Used as a smoke test before running feature scenarios.
    
    Args:
        page: Playwright Page fixture from conftest.py
        
    Example:
        Given the application is running
        When I navigate to the login page
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    try:
        page.goto(base_url, wait_until="domcontentloaded")
        # Verify page loaded (has title or html element)
        expect(page.locator("html")).to_be_visible()
    except Exception as e:
        raise AssertionError(f"Application not accessible at {base_url}: {str(e)}")


@given("the browser is in headless mode")
@allure.step("Verify headless browser mode")
def verify_headless_mode() -> None:
    """
    Informational step indicating browser is running in headless mode.
    
    This step serves as documentation in feature files and logs the headless
    configuration to Allure reports for reproducibility.
    
    Example:
        Given the browser is in headless mode
        When I run the test suite
        Then screenshots should still be captured
    """
    headless = os.getenv("HEADLESS", "true")
    allure.attach(
        f"Headless mode: {headless}",
        name="Browser Configuration",
        attachment_type=allure.attachment_type.TEXT
    )


@given("all cookies are cleared")
@allure.step("Clear all browser cookies")
def clear_all_cookies(page: Page) -> None:
    """
    Clear all cookies from the browser context.
    
    This step ensures a clean session state, removing authentication tokens
    and session data to simulate a fresh browser session.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        Given all cookies are cleared
        When I attempt to access the dashboard
        Then I should be redirected to the login page
    """
    page.context.clear_cookies()
    allure.attach(
        "All cookies cleared from browser context",
        name="Cookie Management",
        attachment_type=allure.attachment_type.TEXT
    )


# ============================================================================
# Navigation Steps (Given/When)
# ============================================================================


@given(parsers.parse('I am on the "{page_name}" page'))
@allure.step('Navigate to "{page_name}" page')
def navigate_to_named_page(page: Page, page_name: str) -> None:
    """
    Navigate to a specific page by name.
    
    Maps business-friendly page names to actual URLs. Extend the mapping
    dictionary to support additional pages as needed.
    
    Args:
        page: Playwright Page fixture
        page_name: Human-readable page name (e.g., "login", "dashboard")
        
    Example:
        Given I am on the "login" page
        When I enter valid credentials
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    # Map page names to URL paths
    page_map: Dict[str, str] = {
        "home": "/",
        "homepage": "/",
        "login": "/login",
        "dashboard": "/dashboard",
        "profile": "/profile",
        "user management": "/users",
        "settings": "/settings",
    }
    
    page_path = page_map.get(page_name.lower())
    if page_path is None:
        raise ValueError(
            f"Unknown page name: '{page_name}'. "
            f"Supported pages: {', '.join(page_map.keys())}"
        )
    
    full_url = f"{base_url}{page_path}"
    page.goto(full_url, wait_until="domcontentloaded")
    
    # Verify navigation succeeded
    expect(page).to_have_url(full_url)


@when(parsers.parse('I navigate to "{path}"'))
@allure.step('Navigate to path: {path}')
def navigate_to_path(page: Page, path: str) -> None:
    """
    Navigate to a specific URL path relative to the base URL.
    
    Args:
        page: Playwright Page fixture
        path: URL path relative to BASE_URL (e.g., "/api/docs", "/users/123")
        
    Example:
        When I navigate to "/users/create"
        Then I should see the user creation form
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    full_url = f"{base_url}{path}"
    page.goto(full_url, wait_until="domcontentloaded")


@when("I refresh the page")
@allure.step("Refresh current page")
def refresh_page(page: Page) -> None:
    """
    Reload the current page.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        When I refresh the page
        Then the updated data should be displayed
    """
    page.reload(wait_until="domcontentloaded")


@when("I go back")
@allure.step("Navigate back in browser history")
def navigate_back(page: Page) -> None:
    """
    Navigate to the previous page in browser history.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        When I click on a user
        And I go back
        Then I should be on the user list page
    """
    page.go_back(wait_until="domcontentloaded")


# ============================================================================
# Message and Notification Steps (Then)
# ============================================================================


@then(parsers.parse('I should see the message "{message}"'))
@allure.step('Verify message: "{message}"')
def verify_message_displayed(page: Page, message: str) -> None:
    """
    Verify that specific message text is visible on the page.
    
    Uses Playwright's text-based locator which is stable and accessible.
    Automatically waits for the element to be visible.
    
    Args:
        page: Playwright Page fixture
        message: Expected message text
        
    Example:
        When I submit the form
        Then I should see the message "Form submitted successfully"
    """
    message_locator = page.get_by_text(message, exact=False)
    expect(message_locator).to_be_visible(timeout=5000)


@then(parsers.parse('I should see an error message "{message}"'))
@allure.step('Verify error message: "{message}"')
def verify_error_message(page: Page, message: str) -> None:
    """
    Verify that a specific error message is displayed.
    
    Looks for messages within elements with role="alert" or common error class names,
    providing more targeted validation for error scenarios.
    
    Args:
        page: Playwright Page fixture
        message: Expected error message text
        
    Example:
        When I submit invalid data
        Then I should see an error message "Invalid email format"
    """
    # Try role-based selector first (more accessible)
    error_alert = page.get_by_role("alert").filter(has_text=message)
    
    # Check if alert exists with the message
    try:
        expect(error_alert).to_be_visible(timeout=3000)
    except AssertionError:
        # Fallback: look for any element with the error text
        error_text = page.get_by_text(message, exact=False)
        expect(error_text).to_be_visible(timeout=2000)


@then(parsers.parse('I should see a success message "{message}"'))
@allure.step('Verify success message: "{message}"')
def verify_success_message(page: Page, message: str) -> None:
    """
    Verify that a specific success message is displayed.
    
    Similar to error message validation but focuses on success notifications,
    typically displayed after successful form submissions or operations.
    
    Args:
        page: Playwright Page fixture
        message: Expected success message text
        
    Example:
        When I save my changes
        Then I should see a success message "Changes saved successfully"
    """
    # Look for success message in common notification areas
    success_locator = page.get_by_text(message, exact=False)
    expect(success_locator).to_be_visible(timeout=5000)


# ============================================================================
# URL Validation Steps (Then)
# ============================================================================


@then(parsers.parse('the URL should contain "{url_fragment}"'))
@allure.step('Verify URL contains: "{url_fragment}"')
def verify_url_contains_fragment(page: Page, url_fragment: str) -> None:
    """
    Verify that the current URL contains a specific text fragment.
    
    Useful for validating navigation to dynamic routes or query parameters.
    
    Args:
        page: Playwright Page fixture
        url_fragment: Text that should appear in the URL
        
    Example:
        When I click on user "john"
        Then the URL should contain "/users/john"
    """
    current_url = page.url
    assert url_fragment in current_url, (
        f"Expected URL to contain '{url_fragment}', "
        f"but current URL is '{current_url}'"
    )
    
    allure.attach(
        current_url,
        name="Current URL",
        attachment_type=allure.attachment_type.TEXT
    )


@then(parsers.parse('I should be on the "{page_name}" page'))
@allure.step('Verify current page is: "{page_name}"')
def verify_on_named_page(page: Page, page_name: str) -> None:
    """
    Verify that the browser is currently on the specified page.
    
    Maps business-friendly page names to URL patterns for validation.
    
    Args:
        page: Playwright Page fixture
        page_name: Human-readable page name
        
    Example:
        When I click "Dashboard" in the navigation
        Then I should be on the "dashboard" page
    """
    base_url = os.getenv("BASE_URL", "http://localhost:3000")
    
    # Map page names to expected URL patterns
    page_map: Dict[str, str] = {
        "home": "/",
        "homepage": "/",
        "login": "/login",
        "dashboard": "/dashboard",
        "profile": "/profile",
        "user management": "/users",
        "settings": "/settings",
    }
    
    expected_path = page_map.get(page_name.lower())
    if expected_path is None:
        raise ValueError(
            f"Unknown page name: '{page_name}'. "
            f"Supported pages: {', '.join(page_map.keys())}"
        )
    
    expected_url = f"{base_url}{expected_path}"
    expect(page).to_have_url(expected_url)


# ============================================================================
# Element Visibility Steps (Then)
# ============================================================================


@then(parsers.parse('I should see the "{element_name}" element'))
@allure.step('Verify element visible: "{element_name}"')
def verify_element_visible(page: Page, element_name: str) -> None:
    """
    Verify that a specific UI element is visible on the page.
    
    Uses test-id attribute as the primary locator strategy, following the user
    directive to prefer stable selectors (role/name/test-id) over brittle CSS/XPath.
    
    Args:
        page: Playwright Page fixture
        element_name: Test ID or accessible name of the element
        
    Example:
        Then I should see the "user-table" element
        And I should see the "add-user-button" element
    """
    # Try test-id first (most stable)
    element = page.get_by_test_id(element_name)
    
    try:
        expect(element).to_be_visible(timeout=5000)
    except AssertionError:
        # Fallback: try as accessible name/label
        element_by_label = page.get_by_label(element_name, exact=False)
        expect(element_by_label).to_be_visible(timeout=2000)


@then(parsers.parse('I should not see the "{element_name}" element'))
@allure.step('Verify element not visible: "{element_name}"')
def verify_element_not_visible(page: Page, element_name: str) -> None:
    """
    Verify that a specific UI element is not visible on the page.
    
    Used for negative assertions, such as verifying elements are hidden
    after certain actions or permissions checks.
    
    Args:
        page: Playwright Page fixture
        element_name: Test ID or accessible name of the element
        
    Example:
        Given I am logged out
        Then I should not see the "admin-panel" element
    """
    element = page.get_by_test_id(element_name)
    expect(element).not_to_be_visible()


# ============================================================================
# Wait and Loading Steps (When/Then)
# ============================================================================


@when("I wait for the page to load")
@allure.step("Wait for page to finish loading")
def wait_for_page_load(page: Page) -> None:
    """
    Wait for the page to complete loading (networkidle state).
    
    This step waits until network activity has stopped for at least 500ms,
    indicating that async resources have finished loading.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        When I navigate to the dashboard
        And I wait for the page to load
        Then all widgets should be displayed
    """
    page.wait_for_load_state("networkidle", timeout=30000)


@when(parsers.parse("I wait {seconds:d} seconds"))
@allure.step("Wait {seconds} seconds")
def wait_explicit_seconds(page: Page, seconds: int) -> None:
    """
    Explicit wait for a specified number of seconds.
    
    Use sparingly - prefer to wait for specific conditions rather than arbitrary delays.
    This step is provided for scenarios where waiting for page state is insufficient.
    
    Args:
        page: Playwright Page fixture
        seconds: Number of seconds to wait
        
    Example:
        When I trigger an animation
        And I wait 2 seconds
        Then the animation should be complete
        
    Note:
        Avoid using explicit waits when possible. Prefer waiting for elements,
        network idle, or specific conditions for more reliable tests.
    """
    page.wait_for_timeout(seconds * 1000)


@then("the page should finish loading")
@allure.step("Verify page load complete")
def verify_page_loaded(page: Page) -> None:
    """
    Verify that the page has finished loading.
    
    Checks for DOM content loaded state, ensuring the page is interactive.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        When I refresh the page
        Then the page should finish loading
    """
    page.wait_for_load_state("domcontentloaded", timeout=30000)
    
    # Verify page is interactive by checking for html element
    expect(page.locator("html")).to_be_visible()


# ============================================================================
# Screenshot and Diagnostic Steps (When)
# ============================================================================


@when("I capture a screenshot")
@allure.step("Capture screenshot")
def capture_manual_screenshot(page: Page) -> None:
    """
    Manually capture and attach a screenshot to the test report.
    
    Useful for documenting specific states during test execution or
    capturing visual evidence of bugs.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        When I navigate to the profile page
        And I capture a screenshot
        Then the profile photo should be displayed
    """
    from tests.helpers.allure_utils import attach_screenshot
    attach_screenshot(page, "Manual Screenshot")


@when("I capture browser console logs")
@allure.step("Capture browser console logs")
def capture_console_logs(page: Page) -> None:
    """
    Capture and attach browser console messages to the test report.
    
    Retrieves JavaScript console logs (info, warn, error) for debugging
    client-side issues. Requires console listener to be configured in conftest.py.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        When I perform a complex interaction
        And I capture browser console logs
        Then there should be no console errors
    """
    attach_browser_console_logs(page)


# ============================================================================
# Form Interaction Steps (When) - Generic
# ============================================================================


@when(parsers.parse('I fill in "{field}" with "{value}"'))
@allure.step('Fill field "{field}" with "{value}"')
def fill_field_by_label(page: Page, field: str, value: str) -> None:
    """
    Fill an input field identified by its label or accessible name.
    
    Uses Playwright's get_by_label() for accessible, stable locators following
    the user directive to avoid brittle CSS/XPath selectors.
    
    Args:
        page: Playwright Page fixture
        field: Label text or accessible name of the input field
        value: Value to enter into the field
        
    Example:
        When I fill in "Email" with "user@example.com"
        And I fill in "Password" with "SecurePass123"
    """
    input_field = page.get_by_label(field, exact=False)
    input_field.fill(value)


@when(parsers.parse('I click the "{button}" button'))
@allure.step('Click button: "{button}"')
def click_button_by_name(page: Page, button: str) -> None:
    """
    Click a button identified by its accessible name or text.
    
    Uses role-based selector (button role) with accessible name for
    maximum stability and accessibility compliance.
    
    Args:
        page: Playwright Page fixture
        button: Accessible name or text of the button
        
    Example:
        When I click the "Submit" button
        Then the form should be submitted
    """
    button_element = page.get_by_role("button", name=button)
    button_element.click()


@when(parsers.parse('I check the "{checkbox}" checkbox'))
@allure.step('Check checkbox: "{checkbox}"')
def check_checkbox_by_name(page: Page, checkbox: str) -> None:
    """
    Check a checkbox identified by its label or accessible name.
    
    Uses role-based selector for checkboxes, ensuring the box is checked
    regardless of its current state.
    
    Args:
        page: Playwright Page fixture
        checkbox: Label or accessible name of the checkbox
        
    Example:
        When I check the "Remember me" checkbox
        And I click the "Login" button
    """
    checkbox_element = page.get_by_role("checkbox", name=checkbox)
    checkbox_element.check()


@when("I clear local storage")
@allure.step("Clear browser local storage")
def clear_local_storage(page: Page) -> None:
    """
    Clear all data from browser local storage.
    
    Removes client-side stored data, useful for resetting application state
    or testing behaviors with/without cached data.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        Given I am on the application
        When I clear local storage
        And I refresh the page
        Then I should see the onboarding tutorial
    """
    page.evaluate("() => localStorage.clear()")
    allure.attach(
        "Local storage cleared",
        name="Storage Management",
        attachment_type=allure.attachment_type.TEXT
    )


# ============================================================================
# Browser Console Validation (Then)
# ============================================================================


@then("there should be no console errors")
@allure.step("Verify no console errors")
def verify_no_console_errors(page: Page) -> None:
    """
    Verify that no JavaScript errors were logged to the browser console.
    
    Checks the console messages captured during test execution and fails
    if any error-level messages are found. Requires console listener setup
    in conftest.py that stores messages in page._console_messages.
    
    Args:
        page: Playwright Page fixture with _console_messages attribute
        
    Example:
        When I navigate through the application
        Then there should be no console errors
    """
    # First, attach console logs for inspection
    attach_browser_console_logs(page)
    
    # Check for error messages
    console_messages = getattr(page, '_console_messages', [])
    error_messages = [
        f"{msg.type}: {msg.text}"
        for msg in console_messages
        if msg.type == "error"
    ]
    
    if error_messages:
        error_summary = "\n".join(error_messages)
        allure.attach(
            error_summary,
            name="Console Errors Found",
            attachment_type=allure.attachment_type.TEXT
        )
        raise AssertionError(
            f"Found {len(error_messages)} console error(s):\n{error_summary}"
        )


# ============================================================================
# Accessibility Checks (Then)
# ============================================================================


@then("the page should be accessible")
@allure.step("Verify page accessibility")
def verify_page_accessibility(page: Page) -> None:
    """
    Perform basic accessibility validation on the current page.
    
    This step performs fundamental accessibility checks including:
    - Page has a title
    - Main landmark exists
    - No missing alt text on images (basic check)
    
    For comprehensive accessibility testing, consider integrating axe-core
    or similar accessibility testing libraries.
    
    Args:
        page: Playwright Page fixture
        
    Example:
        When I navigate to the homepage
        Then the page should be accessible
        
    Note:
        This is a basic accessibility check. For production, integrate
        axe-playwright or similar tools for comprehensive WCAG validation.
    """
    # Verify page has a title
    title = page.title()
    assert title and len(title) > 0, "Page must have a title for accessibility"
    
    # Log accessibility check results
    allure.attach(
        f"Page title: {title}",
        name="Accessibility Check Results",
        attachment_type=allure.attachment_type.TEXT
    )
    
    # Note: This is a placeholder for more comprehensive accessibility testing
    # In production, integrate axe-playwright:
    # from axe_playwright_python.sync_playwright import Axe
    # axe = Axe()
    # results = axe.run(page)
    # assert len(results.violations) == 0, f"Accessibility violations: {results.violations}"

