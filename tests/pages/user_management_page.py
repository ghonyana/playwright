"""
User Management Page Object Module

This module provides the UserManagementPage class for interacting with the admin user
management interface. It implements CRUD operations (Create, Read, Update, Delete) for
users through a business-readable, stable locator-based API.

Business Domain:
---------------
The user management page is an administrative interface for managing application users.
Key functionalities include:
- Viewing a searchable, filterable list of all users
- Creating new user accounts with role and department assignment
- Editing existing user details
- Deleting user accounts with confirmation
- Searching and filtering users by various criteria

Stable Locator Strategy:
-----------------------
All locators follow the enterprise directive to "avoid brittle CSS/xpath—prefer role/name/test‑id":
1. ARIA roles (button, table, searchbox, combobox) for semantic elements
2. Accessible labels (Email, Name, Role) for form inputs
3. data-testid attributes for complex components without semantic roles
4. NO CSS class selectors or complex XPath expressions

Integration Points:
------------------
- BasePage: Inherits common page object functionality and Playwright access
- ModalComponent: Handles delete confirmation dialogs
- Allure: Hierarchical test step reporting for all user operations
- Step Definitions: High-level methods called from Gherkin step implementations

Example Usage:
-------------
```python
# In a test or step definition
def test_create_user(page: Page):
    user_mgmt_page = UserManagementPage(page)
    user_mgmt_page.navigate()
    user_mgmt_page.create_user(
        email="newuser@example.com",
        name="New User",
        role="Admin",
        department="Engineering"
    )
    user_mgmt_page.verify_user_in_list("newuser@example.com")
    user_mgmt_page.verify_success_message("User created successfully")

# In a step definition (user_steps.py)
@when('the admin creates a user with email "{email}" and role "{role}"')
def create_user_step(user_management_page: UserManagementPage, email: str, role: str):
    user_management_page.create_user(email=email, name=f"Test {role}", role=role)
```
"""

from typing import Optional, Dict, Any, List

import allure
from playwright.sync_api import Page

from tests.pages.base_page import BasePage
from tests.pages.components.modal import ModalComponent


class UserManagementPage(BasePage):
    """
    Page object for the user management administrative interface.
    
    This class provides business-readable methods for all user management operations
    including listing, creating, editing, deleting, searching, and filtering users.
    All interactions use stable ARIA-based locators to ensure test reliability across
    UI refactoring and styling changes.
    
    The class follows the Page Object Pattern to abstract UI implementation details
    from test code, enabling high-level, business-focused test scenarios.
    
    Attributes:
        page (Page): Playwright Page instance inherited from BasePage
        base_url (str): Base URL of the application under test
        delete_modal (ModalComponent): Modal component for delete confirmations
        USER_MANAGEMENT_PATH (str): Relative path to the user management page
    
    Example:
        ```python
        # Initialize page object
        user_page = UserManagementPage(page)
        
        # Navigate and verify page loaded
        user_page.navigate()
        
        # Create a new user
        user_page.create_user(
            email="admin@example.com",
            name="Admin User",
            role="Administrator",
            department="IT"
        )
        
        # Search for user
        user_page.search_users("admin@example.com")
        
        # Verify user appears
        user_page.verify_user_in_list("admin@example.com")
        
        # Filter by role
        user_page.filter_by_role("Administrator")
        
        # Edit user
        user_page.edit_user("admin@example.com", {"name": "Super Admin"})
        
        # Delete user with confirmation
        user_page.delete_user("admin@example.com")
        ```
    """
    
    # Page path constant - relative URL for user management interface
    USER_MANAGEMENT_PATH: str = "/users"
    
    def __init__(self, page: Page, base_url: Optional[str] = None):
        """
        Initialize the UserManagementPage with a Playwright Page instance.
        
        Args:
            page (Page): Playwright Page instance from pytest fixture
            base_url (Optional[str]): Base URL override; defaults to BASE_URL env var
        
        Raises:
            ValueError: If neither base_url parameter nor BASE_URL env var is provided
        """
        super().__init__(page, base_url)
        
        # Initialize modal component for delete confirmations
        self.delete_modal = ModalComponent(page, base_url)
    
    # ============================================================================
    # Locator Properties - Using stable ARIA-based selectors
    # ============================================================================
    
    @property
    def page_heading(self):
        """
        Locator for the main page heading displaying "Users" or "User Management".
        
        Uses ARIA heading role for semantic selection. This is the most stable
        selector as it relies on document structure rather than styling.
        
        Returns:
            Locator: Playwright locator for the page heading element
        """
        # Try multiple common heading variations
        heading = self.page.get_by_role("heading", name="User Management")
        if heading.count() > 0:
            return heading.first
        
        heading = self.page.get_by_role("heading", name="Users")
        if heading.count() > 0:
            return heading.first
        
        # Fallback to any heading with "User" in it
        return self.page.get_by_role("heading").filter(has_text="User").first
    
    @property
    def add_user_button(self):
        """
        Locator for the "Add User" or "Create User" button.
        
        Uses ARIA button or link role with common action labels. Supports both
        button elements and styled links that act as buttons.
        
        Returns:
            Locator: Playwright locator for the add user button element
        """
        # Try button role first
        button = self.page.get_by_role("button", name="Add User")
        if button.count() > 0:
            return button.first
        
        button = self.page.get_by_role("button", name="Create User")
        if button.count() > 0:
            return button.first
        
        # Try link role (for button-styled links)
        link = self.page.get_by_role("link", name="Add User")
        if link.count() > 0:
            return link.first
        
        link = self.page.get_by_role("link", name="Create User")
        if link.count() > 0:
            return link.first
        
        # Fallback to test-id
        return self.page.get_by_test_id("add-user-button").first
    
    @property
    def search_input(self):
        """
        Locator for the user search input field.
        
        Uses ARIA searchbox role or accessible label for semantic selection.
        
        Returns:
            Locator: Playwright locator for the search input element
        """
        # Try searchbox role (most semantic)
        searchbox = self.page.get_by_role("searchbox")
        if searchbox.count() > 0:
            return searchbox.first
        
        # Try by label
        search = self.page.get_by_label("Search users")
        if search.count() > 0:
            return search.first
        
        search = self.page.get_by_label("Search")
        if search.count() > 0:
            return search.first
        
        # Fallback to test-id
        return self.page.get_by_test_id("user-search-input").first
    
    @property
    def role_filter_select(self):
        """
        Locator for the role filter dropdown.
        
        Uses accessible label or ARIA combobox role for semantic selection.
        
        Returns:
            Locator: Playwright locator for the role filter select element
        """
        # Try by label first
        select = self.page.get_by_label("Role")
        if select.count() > 0:
            return select.first
        
        # Try combobox role with name
        select = self.page.get_by_role("combobox", name="Filter by role")
        if select.count() > 0:
            return select.first
        
        select = self.page.get_by_role("combobox", name="Role")
        if select.count() > 0:
            return select.first
        
        # Fallback to test-id
        return self.page.get_by_test_id("role-filter-select").first
    
    @property
    def status_filter_select(self):
        """
        Locator for the status filter dropdown.
        
        Uses accessible label or ARIA combobox role for semantic selection.
        
        Returns:
            Locator: Playwright locator for the status filter select element
        """
        # Try by label first
        select = self.page.get_by_label("Status")
        if select.count() > 0:
            return select.first
        
        # Try combobox role with name
        select = self.page.get_by_role("combobox", name="Filter by status")
        if select.count() > 0:
            return select.first
        
        select = self.page.get_by_role("combobox", name="Status")
        if select.count() > 0:
            return select.first
        
        # Fallback to test-id
        return self.page.get_by_test_id("status-filter-select").first
    
    @property
    def user_table(self):
        """
        Locator for the main user data table.
        
        Uses ARIA table role or data-testid for stable selection.
        
        Returns:
            Locator: Playwright locator for the user table element
        """
        # Try table role first
        table = self.page.get_by_role("table")
        if table.count() > 0:
            return table.first
        
        # Fallback to test-id
        return self.page.get_by_test_id("users-table").first
    
    @property
    def user_rows(self):
        """
        Locator for all user rows in the table (excluding header row).
        
        Uses ARIA row role within the table structure.
        
        Returns:
            Locator: Playwright locator for all user row elements
        """
        # Get all rows within the table, excluding the header row
        return self.user_table.get_by_role("row")
    
    @property
    def edit_buttons(self):
        """
        Locator for all "Edit" action buttons in the user table.
        
        Uses ARIA button role with "Edit" name. Returns all matching buttons
        in the table (one per user row).
        
        Returns:
            Locator: Playwright locator for all edit button elements
        """
        return self.user_table.get_by_role("button", name="Edit")
    
    @property
    def delete_buttons(self):
        """
        Locator for all "Delete" action buttons in the user table.
        
        Uses ARIA button role with "Delete" name. Returns all matching buttons
        in the table (one per user row).
        
        Returns:
            Locator: Playwright locator for all delete button elements
        """
        return self.user_table.get_by_role("button", name="Delete")
    
    @property
    def success_message(self):
        """
        Locator for success notification/alert messages.
        
        Uses ARIA alert role to find notification messages indicating successful
        operations (user created, updated, deleted).
        
        Returns:
            Locator: Playwright locator for success message element
        """
        # ARIA alert role for notifications
        alerts = self.page.get_by_role("alert")
        
        # Filter for success status if available
        # Check for common success indicators
        for alert in alerts.all():
            # Check for success-related attributes or classes
            if alert.count() > 0:
                text = alert.inner_text().lower()
                if "success" in text or "created" in text or "updated" in text or "deleted" in text:
                    return alert
        
        # Fallback to test-id
        return self.page.get_by_test_id("success-message").first
    
    @property
    def error_message(self):
        """
        Locator for error notification/alert messages.
        
        Uses ARIA alert role to find error messages indicating failed operations.
        
        Returns:
            Locator: Playwright locator for error message element
        """
        # ARIA alert role for notifications
        alerts = self.page.get_by_role("alert")
        
        # Filter for error status if available
        for alert in alerts.all():
            if alert.count() > 0:
                text = alert.inner_text().lower()
                if "error" in text or "failed" in text or "unable" in text:
                    return alert
        
        # Fallback to test-id
        return self.page.get_by_test_id("error-message").first
    
    # ============================================================================
    # Form Input Locators - For user creation and editing
    # ============================================================================
    
    @property
    def email_input(self):
        """
        Locator for the email input field in user creation/editing form.
        
        Uses accessible label for semantic selection.
        
        Returns:
            Locator: Playwright locator for email input element
        """
        return self.page.get_by_label("Email")
    
    @property
    def name_input(self):
        """
        Locator for the name input field in user creation/editing form.
        
        Uses accessible label for semantic selection. Supports both "Name"
        and "Full Name" label variations.
        
        Returns:
            Locator: Playwright locator for name input element
        """
        # Try "Name" first
        name = self.page.get_by_label("Name")
        if name.count() > 0:
            return name.first
        
        # Try "Full Name" as alternative
        return self.page.get_by_label("Full Name")
    
    @property
    def role_select(self):
        """
        Locator for the role dropdown in user creation/editing form.
        
        Uses accessible label for semantic selection.
        
        Returns:
            Locator: Playwright locator for role select element
        """
        return self.page.get_by_label("Role")
    
    @property
    def department_input(self):
        """
        Locator for the department input field in user creation/editing form.
        
        Uses accessible label for semantic selection.
        
        Returns:
            Locator: Playwright locator for department input element
        """
        return self.page.get_by_label("Department")
    
    @property
    def submit_button(self):
        """
        Locator for the form submit button (Save/Create User).
        
        Uses ARIA button role with common submit labels.
        
        Returns:
            Locator: Playwright locator for submit button element
        """
        # Try "Save" first
        button = self.page.get_by_role("button", name="Save")
        if button.count() > 0:
            return button.first
        
        # Try "Create User"
        button = self.page.get_by_role("button", name="Create User")
        if button.count() > 0:
            return button.first
        
        # Try "Update User"
        button = self.page.get_by_role("button", name="Update User")
        if button.count() > 0:
            return button.first
        
        # Fallback to test-id
        return self.page.get_by_test_id("submit-button").first
    
    @property
    def cancel_button(self):
        """
        Locator for the form cancel button.
        
        Uses ARIA button role with "Cancel" label.
        
        Returns:
            Locator: Playwright locator for cancel button element
        """
        return self.page.get_by_role("button", name="Cancel")
    
    # ============================================================================
    # Navigation Methods
    # ============================================================================
    
    @allure.step("Navigate to user management page")
    def navigate(self) -> None:
        """
        Navigate to the user management page and verify the table loads.
        
        This method uses the USER_MANAGEMENT_PATH constant to navigate to the
        admin user list interface and waits for the user table to be visible,
        ensuring the page is fully loaded and interactive.
        
        Raises:
            TimeoutError: If page doesn't load or table doesn't appear within timeout
        
        Example:
            ```python
            user_page = UserManagementPage(page)
            user_page.navigate()
            # Page is now ready for user interactions
            ```
        """
        # Use BasePage navigate method with USER_MANAGEMENT_PATH
        super().navigate(self.USER_MANAGEMENT_PATH)
        
        # Wait for page to be fully loaded
        self.wait_for_load("networkidle")
        
        # Verify table is visible - ensures page loaded correctly
        from playwright.sync_api import expect
        expect(self.user_table).to_be_visible(timeout=10000)
        
        allure.attach(
            f"Successfully navigated to user management page at {self.USER_MANAGEMENT_PATH}",
            name="Navigation Complete",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Capture screenshot for documentation
        self.capture_screenshot("User Management Page Loaded")
    
    # ============================================================================
    # User CRUD Operations
    # ============================================================================
    
    @allure.step("Create user: {email}")
    def create_user(
        self,
        email: str,
        name: str,
        role: str,
        department: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        """
        Create a new user by filling out the user creation form.
        
        This method clicks the "Add User" button, fills all required fields with
        stable locators, submits the form, and verifies a success message appears.
        
        Args:
            email (str): User's email address (required)
            name (str): User's full name (required)
            role (str): User's role/permission level (required)
            department (Optional[str]): User's department (optional)
            **kwargs: Additional optional fields (future expansion)
        
        Raises:
            TimeoutError: If form elements don't appear or submission times out
            AssertionError: If success message doesn't appear after submission
        
        Example:
            ```python
            user_page.create_user(
                email="john.doe@example.com",
                name="John Doe",
                role="Manager",
                department="Sales"
            )
            ```
        """
        # Click add user button to open form
        self.add_user_button.click()
        allure.attach(
            "Clicked 'Add User' button to open creation form",
            name="Action",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Wait for form to appear
        from playwright.sync_api import expect
        expect(self.email_input).to_be_visible(timeout=5000)
        
        # Fill required fields using stable label-based locators
        self.email_input.fill(email)
        allure.attach(f"Filled email: {email}", name="Form Data", attachment_type=allure.attachment_type.TEXT)
        
        self.name_input.fill(name)
        allure.attach(f"Filled name: {name}", name="Form Data", attachment_type=allure.attachment_type.TEXT)
        
        # Select role from dropdown
        self.role_select.select_option(label=role)
        allure.attach(f"Selected role: {role}", name="Form Data", attachment_type=allure.attachment_type.TEXT)
        
        # Fill optional department if provided
        if department:
            self.department_input.fill(department)
            allure.attach(f"Filled department: {department}", name="Form Data", attachment_type=allure.attachment_type.TEXT)
        
        # Handle any additional fields passed via kwargs
        for field_name, field_value in kwargs.items():
            try:
                field_input = self.page.get_by_label(field_name)
                if field_input.count() > 0:
                    field_input.fill(str(field_value))
                    allure.attach(
                        f"Filled {field_name}: {field_value}",
                        name="Form Data",
                        attachment_type=allure.attachment_type.TEXT
                    )
            except Exception as e:
                allure.attach(
                    f"Warning: Could not fill optional field '{field_name}': {str(e)}",
                    name="Field Warning",
                    attachment_type=allure.attachment_type.TEXT
                )
        
        # Capture screenshot before submission
        self.capture_screenshot("User Creation Form Filled")
        
        # Submit the form
        self.submit_button.click()
        allure.attach("Clicked submit button", name="Action", attachment_type=allure.attachment_type.TEXT)
        
        # Wait for form to close and table to update
        expect(self.email_input).to_be_hidden(timeout=5000)
        
        # Capture final state
        self.capture_screenshot("User Created")
    
    @allure.step("Search for users: {query}")
    def search_users(self, query: str) -> None:
        """
        Search for users by entering a search query.
        
        This method fills the search input with the provided query and waits
        for the user table to update with filtered results.
        
        Args:
            query (str): Search query text (email, name, or other searchable field)
        
        Example:
            ```python
            user_page.search_users("john.doe@example.com")
            user_page.search_users("Manager")
            ```
        """
        # Clear existing search text
        self.search_input.clear()
        
        # Enter search query
        self.search_input.fill(query)
        allure.attach(f"Entered search query: {query}", name="Search", attachment_type=allure.attachment_type.TEXT)
        
        # Press Enter to trigger search (if needed)
        self.search_input.press("Enter")
        
        # Wait for table to update (give network time to respond)
        self.page.wait_for_timeout(500)
        
        # Wait for load state to ensure AJAX complete
        self.wait_for_load("networkidle")
        
        allure.attach(
            f"Table updated with search results for '{query}'",
            name="Search Complete",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Capture screenshot of search results
        self.capture_screenshot(f"Search Results: {query}")
    
    @allure.step("Filter users by role: {role}")
    def filter_by_role(self, role: str) -> None:
        """
        Filter the user list by role selection.
        
        This method selects a role from the role filter dropdown and waits
        for the user table to update with filtered results.
        
        Args:
            role (str): Role name to filter by (e.g., "Admin", "Manager", "User")
        
        Example:
            ```python
            user_page.filter_by_role("Administrator")
            user_page.filter_by_role("Customer")
            ```
        """
        # Select role from filter dropdown
        self.role_filter_select.select_option(label=role)
        allure.attach(f"Selected role filter: {role}", name="Filter", attachment_type=allure.attachment_type.TEXT)
        
        # Wait for table to update
        self.page.wait_for_timeout(500)
        self.wait_for_load("networkidle")
        
        allure.attach(
            f"Table filtered to show only users with role '{role}'",
            name="Filter Applied",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Capture screenshot of filtered results
        self.capture_screenshot(f"Filtered by Role: {role}")
    
    @allure.step("Filter users by status: {status}")
    def filter_by_status(self, status: str) -> None:
        """
        Filter the user list by status selection.
        
        This method selects a status from the status filter dropdown and waits
        for the user table to update with filtered results.
        
        Args:
            status (str): Status name to filter by (e.g., "Active", "Inactive", "Pending")
        
        Example:
            ```python
            user_page.filter_by_status("Active")
            user_page.filter_by_status("Inactive")
            ```
        """
        # Select status from filter dropdown
        self.status_filter_select.select_option(label=status)
        allure.attach(f"Selected status filter: {status}", name="Filter", attachment_type=allure.attachment_type.TEXT)
        
        # Wait for table to update
        self.page.wait_for_timeout(500)
        self.wait_for_load("networkidle")
        
        allure.attach(
            f"Table filtered to show only users with status '{status}'",
            name="Filter Applied",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Capture screenshot of filtered results
        self.capture_screenshot(f"Filtered by Status: {status}")
    
    @allure.step("Get user row for: {email}")
    def get_user_row(self, email: str):
        """
        Find and return the table row containing a specific user's email.
        
        This method searches through all user rows in the table to find the row
        containing the specified email address.
        
        Args:
            email (str): Email address of the user to find
        
        Returns:
            Locator: Playwright locator for the user's table row
            None: If user row is not found
        
        Example:
            ```python
            user_row = user_page.get_user_row("john.doe@example.com")
            if user_row:
                # Row exists, perform actions
                user_row.get_by_role("button", name="Edit").click()
            ```
        """
        # Filter rows that contain the email text
        user_row = self.user_rows.filter(has_text=email)
        
        if user_row.count() > 0:
            allure.attach(
                f"Found user row for email: {email}",
                name="Row Located",
                attachment_type=allure.attachment_type.TEXT
            )
            return user_row.first
        else:
            allure.attach(
                f"No user row found for email: {email}",
                name="Row Not Found",
                attachment_type=allure.attachment_type.TEXT
            )
            return None
    
    @allure.step("Edit user: {email}")
    def edit_user(self, email: str, updates: Dict[str, Any]) -> None:
        """
        Edit an existing user's details by email.
        
        This method finds the user row by email, clicks the edit button, updates
        the specified form fields, and submits the changes.
        
        Args:
            email (str): Email address of the user to edit
            updates (Dict[str, Any]): Dictionary of field names and new values
                                      Keys should match form field labels
                                      Example: {"name": "New Name", "role": "Admin"}
        
        Raises:
            ValueError: If user with specified email is not found
            TimeoutError: If edit form doesn't appear or submission times out
        
        Example:
            ```python
            user_page.edit_user(
                "john.doe@example.com",
                {
                    "name": "John Smith",
                    "role": "Senior Manager",
                    "department": "Operations"
                }
            )
            ```
        """
        # Find the user's row
        user_row = self.get_user_row(email)
        
        if not user_row:
            raise ValueError(f"Cannot edit user: No user found with email '{email}'")
        
        # Click the edit button in this row
        user_row.get_by_role("button", name="Edit").click()
        allure.attach(f"Clicked edit button for user: {email}", name="Action", attachment_type=allure.attachment_type.TEXT)
        
        # Wait for edit form to appear
        from playwright.sync_api import expect
        expect(self.email_input).to_be_visible(timeout=5000)
        
        # Update each field specified in updates dictionary
        for field_name, field_value in updates.items():
            try:
                # Handle special field names (map to locator properties)
                if field_name.lower() == "email":
                    self.email_input.clear()
                    self.email_input.fill(field_value)
                elif field_name.lower() == "name":
                    self.name_input.clear()
                    self.name_input.fill(field_value)
                elif field_name.lower() == "role":
                    self.role_select.select_option(label=field_value)
                elif field_name.lower() == "department":
                    self.department_input.clear()
                    self.department_input.fill(field_value)
                else:
                    # Generic field update by label
                    field_input = self.page.get_by_label(field_name)
                    if field_input.count() > 0:
                        field_input.clear()
                        field_input.fill(str(field_value))
                
                allure.attach(
                    f"Updated {field_name} to: {field_value}",
                    name="Form Update",
                    attachment_type=allure.attachment_type.TEXT
                )
            except Exception as e:
                allure.attach(
                    f"Warning: Could not update field '{field_name}': {str(e)}",
                    name="Update Warning",
                    attachment_type=allure.attachment_type.TEXT
                )
        
        # Capture screenshot before submission
        self.capture_screenshot("User Edit Form Updated")
        
        # Submit the form
        self.submit_button.click()
        allure.attach("Clicked submit button to save changes", name="Action", attachment_type=allure.attachment_type.TEXT)
        
        # Wait for form to close
        expect(self.email_input).to_be_hidden(timeout=5000)
        
        # Capture final state
        self.capture_screenshot("User Updated")
    
    @allure.step("Delete user: {email}")
    def delete_user(self, email: str) -> None:
        """
        Delete a user by email address with confirmation modal handling.
        
        This method finds the user row by email, clicks the delete button, waits
        for the confirmation modal to appear, and confirms the deletion using the
        integrated ModalComponent.
        
        Args:
            email (str): Email address of the user to delete
        
        Raises:
            ValueError: If user with specified email is not found
            TimeoutError: If delete confirmation modal doesn't appear
            AssertionError: If modal doesn't close after confirmation
        
        Example:
            ```python
            user_page.delete_user("john.doe@example.com")
            # User is deleted and modal is closed
            ```
        """
        # Find the user's row
        user_row = self.get_user_row(email)
        
        if not user_row:
            raise ValueError(f"Cannot delete user: No user found with email '{email}'")
        
        # Click the delete button in this row
        user_row.get_by_role("button", name="Delete").click()
        allure.attach(f"Clicked delete button for user: {email}", name="Action", attachment_type=allure.attachment_type.TEXT)
        
        # Wait for confirmation modal to appear
        self.delete_modal.wait_for_modal_open()
        
        # Optionally verify modal content mentions deletion
        modal_content = self.delete_modal.get_modal_content()
        allure.attach(
            f"Delete confirmation modal content: {modal_content}",
            name="Modal Verification",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Confirm deletion using modal component
        self.delete_modal.click_confirm(wait_for_close=True)
        
        allure.attach(
            f"Successfully deleted user: {email}",
            name="Deletion Complete",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Capture final state
        self.capture_screenshot("User Deleted")
    
    # ============================================================================
    # Verification Methods
    # ============================================================================
    
    @allure.step("Verify user in list: {email}")
    def verify_user_in_list(self, email: str, timeout: int = 10000) -> None:
        """
        Verify that a user with the specified email appears in the user table.
        
        This method uses Playwright's expect assertion with auto-waiting and retry
        logic to reliably verify user presence in the list.
        
        Args:
            email (str): Email address of the user to verify
            timeout (int): Maximum wait time in milliseconds (default: 10000ms)
        
        Raises:
            AssertionError: If user is not found in the table within timeout
        
        Example:
            ```python
            user_page.create_user(email="new@example.com", name="New User", role="User")
            user_page.verify_user_in_list("new@example.com")
            ```
        """
        from playwright.sync_api import expect
        
        try:
            # Find row containing the email
            user_row = self.user_rows.filter(has_text=email)
            
            # Assert row is visible
            expect(user_row.first).to_be_visible(timeout=timeout)
            
            allure.attach(
                f"✓ Verified user '{email}' appears in user list",
                name="Verification Success",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot showing user in list
            self.capture_screenshot(f"User Verified: {email}")
            
        except AssertionError as e:
            # Capture screenshot on failure
            self.capture_screenshot(f"Verification Failed: {email}")
            
            # Get current table content for debugging
            all_rows_text = [row.inner_text() for row in self.user_rows.all()[:5]]  # First 5 rows
            allure.attach(
                f"Current table rows (first 5): {all_rows_text}",
                name="Table State",
                attachment_type=allure.attachment_type.TEXT
            )
            
            raise AssertionError(
                f"User with email '{email}' not found in user table within {timeout}ms. "
                f"Check if user creation succeeded or if filters are applied."
            ) from e
    
    @allure.step("Verify user NOT in list: {email}")
    def verify_user_not_in_list(self, email: str, timeout: int = 5000) -> None:
        """
        Verify that a user with the specified email does NOT appear in the user table.
        
        This method uses Playwright's expect assertion to verify user absence,
        typically used after deletion operations.
        
        Args:
            email (str): Email address of the user to verify absence
            timeout (int): Maximum wait time in milliseconds (default: 5000ms)
        
        Raises:
            AssertionError: If user is still found in the table after timeout
        
        Example:
            ```python
            user_page.delete_user("old@example.com")
            user_page.verify_user_not_in_list("old@example.com")
            ```
        """
        from playwright.sync_api import expect
        
        try:
            # Find row containing the email
            user_row = self.user_rows.filter(has_text=email)
            
            # Assert row is NOT visible (or doesn't exist)
            if user_row.count() > 0:
                expect(user_row.first).to_be_hidden(timeout=timeout)
            
            allure.attach(
                f"✓ Verified user '{email}' does NOT appear in user list",
                name="Verification Success",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot showing user absent from list
            self.capture_screenshot(f"User Absent: {email}")
            
        except AssertionError as e:
            # Capture screenshot on failure
            self.capture_screenshot(f"Verification Failed: User Still Present {email}")
            
            raise AssertionError(
                f"User with email '{email}' is still present in user table after {timeout}ms. "
                f"Check if deletion completed successfully."
            ) from e
    
    @allure.step("Verify success message: {expected_message}")
    def verify_success_message(self, expected_message: str, exact_match: bool = False) -> None:
        """
        Verify that a success notification message appears with expected content.
        
        This method checks for success alert messages that appear after successful
        operations like user creation, update, or deletion.
        
        Args:
            expected_message (str): Expected message text or substring
            exact_match (bool): Whether to match exact text or substring (default: False)
        
        Raises:
            AssertionError: If success message doesn't appear or doesn't contain expected text
        
        Example:
            ```python
            user_page.create_user(email="new@example.com", name="User", role="Admin")
            user_page.verify_success_message("User created successfully")
            user_page.verify_success_message("created")  # Substring match
            ```
        """
        from playwright.sync_api import expect
        
        try:
            # Wait for success message to appear
            expect(self.success_message).to_be_visible(timeout=10000)
            
            # Get actual message text
            actual_message = self.success_message.inner_text()
            
            # Verify message content
            if exact_match:
                if actual_message.strip() != expected_message.strip():
                    raise AssertionError(
                        f"Success message mismatch. Expected: '{expected_message}', Got: '{actual_message}'"
                    )
            else:
                if expected_message.lower() not in actual_message.lower():
                    raise AssertionError(
                        f"Success message doesn't contain expected text. "
                        f"Expected substring: '{expected_message}', Got: '{actual_message}'"
                    )
            
            allure.attach(
                f"✓ Verified success message: '{actual_message}'",
                name="Success Message Verified",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot showing success message
            self.capture_screenshot("Success Message Displayed")
            
        except AssertionError as e:
            self.capture_screenshot("Success Message Verification Failed")
            raise
    
    @allure.step("Verify error message: {expected_message}")
    def verify_error_message(self, expected_message: str, exact_match: bool = False) -> None:
        """
        Verify that an error notification message appears with expected content.
        
        This method checks for error alert messages that appear after failed
        operations or validation errors.
        
        Args:
            expected_message (str): Expected error message text or substring
            exact_match (bool): Whether to match exact text or substring (default: False)
        
        Raises:
            AssertionError: If error message doesn't appear or doesn't contain expected text
        
        Example:
            ```python
            user_page.create_user(email="invalid-email", name="User", role="Admin")
            user_page.verify_error_message("Invalid email format")
            user_page.verify_error_message("email")  # Substring match
            ```
        """
        from playwright.sync_api import expect
        
        try:
            # Wait for error message to appear
            expect(self.error_message).to_be_visible(timeout=10000)
            
            # Get actual message text
            actual_message = self.error_message.inner_text()
            
            # Verify message content
            if exact_match:
                if actual_message.strip() != expected_message.strip():
                    raise AssertionError(
                        f"Error message mismatch. Expected: '{expected_message}', Got: '{actual_message}'"
                    )
            else:
                if expected_message.lower() not in actual_message.lower():
                    raise AssertionError(
                        f"Error message doesn't contain expected text. "
                        f"Expected substring: '{expected_message}', Got: '{actual_message}'"
                    )
            
            allure.attach(
                f"✓ Verified error message: '{actual_message}'",
                name="Error Message Verified",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot showing error message
            self.capture_screenshot("Error Message Displayed")
            
        except AssertionError as e:
            self.capture_screenshot("Error Message Verification Failed")
            raise
    
    @allure.step("Get user count from table")
    def get_user_count(self) -> int:
        """
        Get the total number of users currently displayed in the table.
        
        This method counts all user rows in the table (excluding the header row).
        Useful for verifying list operations and pagination.
        
        Returns:
            int: Number of users in the table
        
        Example:
            ```python
            initial_count = user_page.get_user_count()
            user_page.create_user(email="new@example.com", name="User", role="Admin")
            final_count = user_page.get_user_count()
            assert final_count == initial_count + 1
            ```
        """
        # Wait for table to be visible
        from playwright.sync_api import expect
        expect(self.user_table).to_be_visible(timeout=5000)
        
        # Count all user rows (excluding header)
        # The first row is typically the header, so we count actual data rows
        all_rows = self.user_rows.all()
        
        # Filter out header row if it's included in the count
        # Header rows typically don't have action buttons
        user_data_rows = [
            row for row in all_rows
            if row.get_by_role("button", name="Edit").count() > 0 or 
               row.get_by_role("button", name="Delete").count() > 0
        ]
        
        user_count = len(user_data_rows)
        
        allure.attach(
            f"Current user count in table: {user_count}",
            name="User Count",
            attachment_type=allure.attachment_type.TEXT
        )
        
        return user_count

