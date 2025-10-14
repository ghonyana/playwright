"""
Traditional pytest UI tests for navigation functionality.

This module contains UI tests that verify navigation behaviors including:
- Main menu navigation between application sections
- Breadcrumb navigation for hierarchical page traversal
- User menu dropdown interactions
- Page transition smoothness and error-free navigation

Test Strategy:
- Uses isolated browser contexts per test for parallel execution
- Delegates all UI interactions to DashboardPage page object
- Uses stable ARIA-based locators (no brittle CSS/XPath)
- Integrates with Allure for comprehensive reporting
- Verifies UI state with Playwright's expect() auto-waiting assertions

Per user directives:
- "Tests execute inside pytest (fast, reliable)"
- "Keep tests deterministic, isolated, and parallel-friendly (new context per test)"
- "Implement steps via page objects; avoid brittle CSS/xpath—prefer role/name/test-id"
"""

import allure
from playwright.sync_api import expect


@allure.feature("Navigation")
@allure.story("Main Menu Navigation")
@allure.severity(allure.severity_level.NORMAL)
def test_main_menu_navigation(dashboard_page):
    """
    Test navigating through main menu items and verify correct page loads.
    
    This test validates that clicking on main menu navigation items correctly
    navigates to their respective sections with proper URL updates and page
    content loading. Uses stable ARIA role-based selectors via page objects.
    
    Test Flow:
    1. Navigate to dashboard (starting point)
    2. Click on "Users" menu item and verify navigation
    3. Click on "Settings" menu item and verify navigation
    4. Click on "Reports" menu item and verify navigation
    5. Return to dashboard via menu
    
    Assertions:
    - Each menu item click navigates to expected URL
    - Page content loads correctly after navigation
    - No console errors during navigation
    
    Args:
        dashboard_page: DashboardPage fixture from conftest.py providing
                       page object with navigation methods
    """
    # Navigate to dashboard as starting point
    dashboard_page.navigate()
    expect(dashboard_page.page).to_have_url(dashboard_page.get_dashboard_url())
    
    # Test navigation to Users section
    dashboard_page.navigate_to_section("users")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_section_url("users"))
    expect(dashboard_page.get_page_heading()).to_contain_text("Users")
    
    # Test navigation to Settings section
    dashboard_page.navigate_to_section("settings")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_section_url("settings"))
    expect(dashboard_page.get_page_heading()).to_contain_text("Settings")
    
    # Test navigation to Reports section
    dashboard_page.navigate_to_section("reports")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_section_url("reports"))
    expect(dashboard_page.get_page_heading()).to_contain_text("Reports")
    
    # Return to dashboard home
    dashboard_page.navigate_to_section("dashboard")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_dashboard_url())
    expect(dashboard_page.get_page_heading()).to_contain_text("Dashboard")
    
    # Verify no console errors occurred during navigation
    console_errors = dashboard_page.get_console_errors()
    assert len(console_errors) == 0, f"Console errors detected during navigation: {console_errors}"


@allure.feature("Navigation")
@allure.story("Breadcrumb Navigation")
@allure.severity(allure.severity_level.NORMAL)
def test_breadcrumb_navigation(dashboard_page):
    """
    Test breadcrumb navigation functionality for hierarchical page traversal.
    
    This test validates breadcrumb navigation that allows users to navigate
    back through parent pages in a hierarchical structure. Tests multiple
    levels of depth and verifies correct URL and content updates.
    
    Test Flow:
    1. Navigate to a deep nested page (Users > User Details > Edit Profile)
    2. Verify full breadcrumb trail is displayed
    3. Click on middle breadcrumb (User Details) and verify navigation
    4. Click on root breadcrumb (Users) and verify navigation
    5. Verify breadcrumbs update correctly at each level
    
    Assertions:
    - Breadcrumb trail displays correct hierarchy
    - Clicking breadcrumb navigates to correct parent page
    - URL updates correctly after breadcrumb navigation
    - Page content matches expected breadcrumb level
    
    Args:
        dashboard_page: DashboardPage fixture providing breadcrumb navigation
    """
    # Navigate to deep nested page: Dashboard > Users > User Profile > Edit
    dashboard_page.navigate()
    dashboard_page.navigate_to_section("users")
    dashboard_page.navigate_to_user_profile(user_id="test-user-123")
    dashboard_page.navigate_to_edit_profile()
    
    # Verify full breadcrumb trail is visible
    breadcrumbs = dashboard_page.get_breadcrumb_items()
    assert len(breadcrumbs) == 4, f"Expected 4 breadcrumb items, got {len(breadcrumbs)}"
    expect(breadcrumbs[0]).to_have_text("Dashboard")
    expect(breadcrumbs[1]).to_have_text("Users")
    expect(breadcrumbs[2]).to_have_text("User Profile")
    expect(breadcrumbs[3]).to_have_text("Edit Profile")
    
    # Click on "User Profile" breadcrumb (navigate up one level)
    dashboard_page.click_breadcrumb("User Profile")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_user_profile_url("test-user-123"))
    expect(dashboard_page.get_page_heading()).to_contain_text("User Profile")
    
    # Verify breadcrumb updated (Edit Profile should be gone)
    breadcrumbs_after_click = dashboard_page.get_breadcrumb_items()
    assert len(breadcrumbs_after_click) == 3, "Breadcrumb should have 3 items after navigation"
    
    # Click on "Users" breadcrumb (navigate to parent list)
    dashboard_page.click_breadcrumb("Users")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_section_url("users"))
    expect(dashboard_page.get_page_heading()).to_contain_text("Users")
    
    # Click on "Dashboard" breadcrumb (return to root)
    dashboard_page.click_breadcrumb("Dashboard")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_dashboard_url())
    expect(dashboard_page.get_page_heading()).to_contain_text("Dashboard")
    
    # Verify no console errors during breadcrumb navigation
    console_errors = dashboard_page.get_console_errors()
    assert len(console_errors) == 0, f"Console errors during breadcrumb navigation: {console_errors}"


@allure.feature("Navigation")
@allure.story("User Menu")
@allure.severity(allure.severity_level.NORMAL)
def test_user_menu_access(dashboard_page):
    """
    Test opening and interacting with user menu dropdown.
    
    This test validates the user menu dropdown functionality, which typically
    appears in the top-right corner of the application. Tests visibility,
    menu item interactions, and proper dropdown behavior.
    
    Test Flow:
    1. Navigate to dashboard
    2. Open user menu dropdown
    3. Verify all expected menu items are visible
    4. Click on "Profile" menu item and verify navigation
    5. Re-open menu and click "Settings"
    6. Verify menu closes after selection
    
    Assertions:
    - User menu button is visible and clickable
    - Dropdown opens on click with correct menu items
    - Menu items are interactive and navigate correctly
    - Menu closes automatically after selection
    
    Args:
        dashboard_page: DashboardPage fixture with user menu methods
    """
    # Navigate to dashboard
    dashboard_page.navigate()
    expect(dashboard_page.page).to_have_url(dashboard_page.get_dashboard_url())
    
    # Open user menu dropdown
    dashboard_page.open_user_menu()
    
    # Verify user menu is expanded and visible
    user_menu = dashboard_page.get_user_menu_dropdown()
    expect(user_menu).to_be_visible()
    
    # Verify expected menu items are present
    menu_items = dashboard_page.get_user_menu_items()
    expected_items = ["Profile", "Account Settings", "Preferences", "Help", "Logout"]
    
    actual_item_texts = [item.inner_text() for item in menu_items]
    for expected_item in expected_items:
        assert expected_item in actual_item_texts, f"Expected menu item '{expected_item}' not found"
    
    # Click on "Profile" menu item
    dashboard_page.click_user_menu_item("Profile")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_profile_url())
    expect(dashboard_page.get_page_heading()).to_contain_text("Profile")
    
    # Verify menu closed after selection
    user_menu_after_click = dashboard_page.get_user_menu_dropdown()
    expect(user_menu_after_click).not_to_be_visible()
    
    # Re-open menu and test another item
    dashboard_page.open_user_menu()
    expect(dashboard_page.get_user_menu_dropdown()).to_be_visible()
    
    dashboard_page.click_user_menu_item("Account Settings")
    expect(dashboard_page.page).to_have_url(dashboard_page.get_account_settings_url())
    expect(dashboard_page.get_page_heading()).to_contain_text("Account Settings")
    
    # Verify no console errors during user menu interactions
    console_errors = dashboard_page.get_console_errors()
    assert len(console_errors) == 0, f"Console errors in user menu: {console_errors}"


@allure.feature("Navigation")
@allure.story("Page Transitions")
@allure.severity(allure.severity_level.MINOR)
def test_page_transition_animations(dashboard_page):
    """
    Test smooth page transitions without errors or visual glitches.
    
    This test validates that navigation between pages occurs smoothly with
    proper animations/transitions and without JavaScript errors. Focuses on
    the technical quality of page transitions rather than specific navigation
    paths.
    
    Test Flow:
    1. Navigate to dashboard
    2. Navigate to multiple different sections in sequence
    3. Verify each transition completes successfully
    4. Check for console errors throughout
    5. Verify no broken images or failed resource loads
    
    Assertions:
    - Page transitions complete without hanging
    - No JavaScript console errors during transitions
    - No failed network requests (images, CSS, JS)
    - Page content loads fully after each transition
    
    Args:
        dashboard_page: DashboardPage fixture for page transitions
    """
    # Navigate to dashboard starting point
    dashboard_page.navigate()
    expect(dashboard_page.page).to_have_url(dashboard_page.get_dashboard_url())
    
    # Track console errors throughout test
    initial_error_count = len(dashboard_page.get_console_errors())
    
    # Navigate through multiple sections to test transitions
    sections_to_test = ["users", "reports", "settings", "dashboard"]
    
    for section in sections_to_test:
        # Navigate to section
        dashboard_page.navigate_to_section(section)
        
        # Verify page loaded successfully
        expected_url = dashboard_page.get_section_url(section) if section != "dashboard" else dashboard_page.get_dashboard_url()
        expect(dashboard_page.page).to_have_url(expected_url)
        
        # Wait for page to be fully loaded (network idle)
        dashboard_page.wait_for_page_load()
        
        # Verify page heading is visible (content loaded)
        page_heading = dashboard_page.get_page_heading()
        expect(page_heading).to_be_visible()
        
        # Check no new console errors appeared
        current_errors = dashboard_page.get_console_errors()
        new_error_count = len(current_errors)
        assert new_error_count == initial_error_count, \
            f"New console errors after navigating to {section}: {current_errors[initial_error_count:]}"
    
    # Verify no failed network requests (broken images, CSS, JS)
    failed_requests = dashboard_page.get_failed_network_requests()
    assert len(failed_requests) == 0, \
        f"Failed network requests detected during transitions: {failed_requests}"
    
    # Test rapid navigation (stress test for race conditions)
    dashboard_page.navigate_to_section("users")
    dashboard_page.navigate_to_section("reports")
    dashboard_page.navigate_to_section("dashboard")
    
    # Verify final state is correct (last navigation wins)
    expect(dashboard_page.page).to_have_url(dashboard_page.get_dashboard_url())
    expect(dashboard_page.get_page_heading()).to_be_visible()
    
    # Final console error check
    final_errors = dashboard_page.get_console_errors()
    assert len(final_errors) == initial_error_count, \
        f"Console errors detected after all transitions: {final_errors}"
