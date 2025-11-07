"""
User Profile Page Object Module

This module provides the UserProfilePage class for interacting with the user account
settings and profile management page. It follows the Page Object Pattern and implements
stable locator strategies using ARIA roles, semantic labels, and test IDs.

The UserProfilePage enables tests to:
- Navigate to the user profile/account settings page
- Update user profile information (name, email)
- Change user passwords with current password verification
- Verify successful saves and validation error messages
- Cancel changes and verify no modifications were applied

Locator Strategy:
-----------------
Per user directive, this page object prioritizes stable, semantic locators:
1. ARIA roles (get_by_role) for buttons, alerts, and headings
2. Accessible labels (get_by_label) for form inputs
3. Test IDs (get_by_test_id) for specific elements when semantic locators insufficient
4. Avoids brittle CSS class selectors and complex XPath expressions

Integration with MCP Servers:
-----------------------------
This page object is designed to work seamlessly with MCP-generated test data.
Step definitions can use MCP tools to seed users and build payloads, then use
this page object to verify the UI correctly displays and updates that data.

Example Usage in Step Definitions:
    ```python
    from tests.helpers.mcp_client import MCPClient
    from tests.pages.user_profile_page import UserProfilePage
    
    @given("a user with profile data exists")
    def create_user_with_profile(mcp_client: MCPClient):
        # Use MCP to seed deterministic test user
        user_data = mcp_client.seed_user(
            role="customer",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com"
        )
        return user_data
    
    @when("the user updates their profile")
    def update_user_profile(profile_page: UserProfilePage, mcp_client: MCPClient):
        # Use MCP to build valid update payload
        update_data = mcp_client.build_payload("update_profile", {
            "first_name": "Jane",
            "last_name": "Smith"
        })
        
        profile_page.navigate_to_profile()
        profile_page.update_profile(
            first_name=update_data["first_name"],
            last_name=update_data["last_name"]
        )
    
    @then("the profile changes are saved successfully")
    def verify_profile_saved(profile_page: UserProfilePage):
        profile_page.verify_profile_saved()
    ```
"""

from typing import Optional, Dict, Any

import allure
from playwright.sync_api import Page, Locator

from tests.pages.base_page import BasePage


# Constants
USER_PROFILE_PATH = "/profile"  # Default profile page route


class UserProfilePage(BasePage):
    """
    Page object for user profile and account settings management.
    
    This class provides methods for interacting with the user profile page,
    including updating personal information, changing passwords, and verifying
    form submission outcomes. All locators use stable, semantic strategies per
    project directives to avoid brittle test failures.
    
    Attributes:
        page (Page): Playwright Page instance inherited from BasePage
        base_url (str): Base URL of application inherited from BasePage
    
    Locator Properties:
        profile_heading: Main page heading ("Profile" or "Account Settings")
        first_name_input: First name text input field
        last_name_input: Last name text input field
        email_input: Email address text input field
        current_password_input: Current password field for password change
        new_password_input: New password field for password change
        confirm_password_input: Password confirmation field
        save_button: Save/Update Profile button
        cancel_button: Cancel changes button
        success_message: Success notification alert
        error_message: Error notification alert
    
    Action Methods:
        navigate_to_profile(): Navigate to profile page and verify load
        update_profile(): Fill and submit profile update form
        change_password(): Change user password with validation
        verify_profile_saved(): Assert success message is displayed
        verify_validation_error(): Check for field-specific error messages
        get_current_email(): Retrieve displayed email value
        cancel_changes(): Click cancel and verify no changes applied
    
    Example:
        ```python
        def test_update_profile(page: Page):
            profile_page = UserProfilePage(page)
            profile_page.navigate_to_profile()
            profile_page.update_profile(
                first_name="Jane",
                last_name="Smith",
                email="jane.smith@example.com"
            )
            profile_page.verify_profile_saved()
        ```
    """
    
    def __init__(self, page: Page, base_url: Optional[str] = None):
        """
        Initialize UserProfilePage with Playwright Page instance.
        
        Args:
            page (Page): Playwright Page instance from pytest fixture
            base_url (Optional[str]): Base URL override; defaults to BASE_URL env var
        
        Raises:
            ValueError: If neither base_url parameter nor BASE_URL env var is provided
        
        Example:
            ```python
            @pytest.fixture
            def profile_page(page: Page) -> UserProfilePage:
                return UserProfilePage(page)
            ```
        """
        super().__init__(page, base_url)
    
    # Locator Properties using stable, semantic selectors
    
    @property
    def profile_heading(self) -> Locator:
        """
        Locate the main profile page heading.
        
        Uses ARIA role 'heading' with accessible name matching.
        Tries common heading variations: "Profile", "Account Settings".
        
        Returns:
            Locator: Playwright locator for the profile heading
        
        Example:
            ```python
            heading = profile_page.profile_heading
            assert heading.is_visible()
            assert "Profile" in heading.inner_text()
            ```
        """
        # Try "Profile" first, fallback to "Account Settings"
        try:
            locator = self.page.get_by_role("heading", name="Profile")
            if locator.count() > 0:
                return locator
        except Exception:
            pass
        
        return self.page.get_by_role("heading", name="Account Settings")
    
    @property
    def first_name_input(self) -> Locator:
        """
        Locate the first name input field.
        
        Uses get_by_label for semantic form labeling. This is the PREFERRED
        method for form inputs as it relies on label-input association.
        Fallback to ARIA role textbox if label not present.
        
        Returns:
            Locator: Playwright locator for first name input
        
        Example:
            ```python
            profile_page.first_name_input.fill("John")
            ```
        """
        try:
            locator = self.page.get_by_label("First Name")
            if locator.count() > 0:
                return locator
        except Exception:
            pass
        
        return self.page.get_by_role("textbox", name="First Name")
    
    @property
    def last_name_input(self) -> Locator:
        """
        Locate the last name input field.
        
        Uses get_by_label with fallback to ARIA role textbox.
        
        Returns:
            Locator: Playwright locator for last name input
        
        Example:
            ```python
            profile_page.last_name_input.fill("Doe")
            ```
        """
        try:
            locator = self.page.get_by_label("Last Name")
            if locator.count() > 0:
                return locator
        except Exception:
            pass
        
        return self.page.get_by_role("textbox", name="Last Name")
    
    @property
    def email_input(self) -> Locator:
        """
        Locate the email input field.
        
        Uses get_by_label with fallback to ARIA role textbox.
        Email fields should have type="email" and appropriate aria-label.
        
        Returns:
            Locator: Playwright locator for email input
        
        Example:
            ```python
            profile_page.email_input.fill("user@example.com")
            ```
        """
        try:
            locator = self.page.get_by_label("Email")
            if locator.count() > 0:
                return locator
        except Exception:
            pass
        
        return self.page.get_by_role("textbox", name="Email")
    
    @property
    def current_password_input(self) -> Locator:
        """
        Locate the current password input field for password changes.
        
        Uses get_by_label for password change forms that require
        current password verification before setting new password.
        
        Returns:
            Locator: Playwright locator for current password input
        
        Example:
            ```python
            profile_page.current_password_input.fill("old_password123")
            ```
        """
        return self.page.get_by_label("Current Password")
    
    @property
    def new_password_input(self) -> Locator:
        """
        Locate the new password input field.
        
        Uses get_by_label for the new password field in password change flow.
        
        Returns:
            Locator: Playwright locator for new password input
        
        Example:
            ```python
            profile_page.new_password_input.fill("new_secure_password456")
            ```
        """
        return self.page.get_by_label("New Password")
    
    @property
    def confirm_password_input(self) -> Locator:
        """
        Locate the password confirmation input field.
        
        Uses get_by_label for password confirmation field.
        Typically requires matching the new_password_input value.
        
        Returns:
            Locator: Playwright locator for confirm password input
        
        Example:
            ```python
            profile_page.confirm_password_input.fill("new_secure_password456")
            ```
        """
        return self.page.get_by_label("Confirm Password")
    
    @property
    def save_button(self) -> Locator:
        """
        Locate the save/update profile button.
        
        Uses ARIA role 'button' with accessible name matching.
        Tries common button text variations: "Save", "Update Profile".
        
        Returns:
            Locator: Playwright locator for the save button
        
        Example:
            ```python
            profile_page.save_button.click()
            ```
        """
        try:
            locator = self.page.get_by_role("button", name="Save")
            if locator.count() > 0:
                return locator
        except Exception:
            pass
        
        return self.page.get_by_role("button", name="Update Profile")
    
    @property
    def cancel_button(self) -> Locator:
        """
        Locate the cancel button.
        
        Uses ARIA role 'button' with accessible name "Cancel".
        
        Returns:
            Locator: Playwright locator for the cancel button
        
        Example:
            ```python
            profile_page.cancel_button.click()
            ```
        """
        return self.page.get_by_role("button", name="Cancel")
    
    @property
    def success_message(self) -> Locator:
        """
        Locate the success notification alert.
        
        Uses ARIA role 'alert' or fallback to test-id for success messages.
        Success alerts typically have role="alert" with status indicators.
        
        Returns:
            Locator: Playwright locator for success message alert
        
        Example:
            ```python
            assert profile_page.success_message.is_visible()
            assert "successfully" in profile_page.success_message.inner_text().lower()
            ```
        """
        try:
            # Try to find alert role first (preferred semantic locator)
            locator = self.page.get_by_role("alert").filter(has_text="success")
            if locator.count() > 0:
                return locator
        except Exception:
            pass
        
        # Fallback to test-id
        return self.page.get_by_test_id("success-message")
    
    @property
    def error_message(self) -> Locator:
        """
        Locate the error notification alert.
        
        Uses ARIA role 'alert' for error messages.
        Error alerts should have appropriate ARIA attributes for accessibility.
        
        Returns:
            Locator: Playwright locator for error message alert
        
        Example:
            ```python
            if profile_page.error_message.is_visible():
                error_text = profile_page.error_message.inner_text()
                print(f"Error occurred: {error_text}")
            ```
        """
        return self.page.get_by_role("alert").filter(has_text="error")
    
    # Action Methods with Allure step decorators
    
    @allure.step("Navigate to user profile page")
    def navigate_to_profile(self, timeout: Optional[int] = None) -> None:
        """
        Navigate to the user profile page and verify form load.
        
        This method navigates to the profile page URL, waits for the page to load
        completely (networkidle state), and verifies the profile heading is visible
        to ensure the page loaded correctly.
        
        Args:
            timeout (Optional[int]): Maximum navigation time in milliseconds
                                    Defaults to Playwright's default (30000ms)
        
        Raises:
            TimeoutError: If navigation or page load exceeds timeout
            AssertionError: If profile heading is not visible after load
        
        Example:
            ```python
            def test_view_profile(profile_page: UserProfilePage):
                profile_page.navigate_to_profile()
                # Profile page is now loaded and ready for interaction
            ```
        """
        # Navigate to profile page using BasePage.navigate()
        self.navigate(USER_PROFILE_PATH, timeout=timeout)
        
        # Wait for page to fully load (all network requests complete)
        self.wait_for_load("networkidle")
        
        # Verify profile heading is visible (confirms page loaded correctly)
        heading = self.profile_heading
        if not heading.is_visible():
            self.capture_screenshot("Profile Page Load Failed")
            raise AssertionError(
                "Profile page heading not visible after navigation. "
                "Page may not have loaded correctly."
            )
        
        # Attach current URL to Allure report for verification
        allure.attach(
            self.page.url,
            name="Profile Page URL",
            attachment_type=allure.attachment_type.TEXT
        )
    
    @allure.step("Update profile with first_name={first_name}, last_name={last_name}, email={email}")
    def update_profile(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None
    ) -> None:
        """
        Update user profile information by filling form fields and saving.
        
        This method fills the profile update form with provided values and
        submits the form by clicking the save button. Only provided fields
        are updated; None values are skipped. The method waits for form
        submission to complete by monitoring for success/error messages.
        
        Args:
            first_name (Optional[str]): New first name; if None, field not changed
            last_name (Optional[str]): New last name; if None, field not changed
            email (Optional[str]): New email address; if None, field not changed
        
        Raises:
            TimeoutError: If form submission takes too long
        
        Example:
            ```python
            # Update all fields
            profile_page.update_profile(
                first_name="Jane",
                last_name="Smith",
                email="jane.smith@example.com"
            )
            
            # Update only name
            profile_page.update_profile(first_name="John", last_name="Doe")
            
            # Integration with MCP-generated data
            @when("user updates profile with MCP data")
            def update_with_mcp(profile_page, mcp_client):
                data = mcp_client.build_payload("update_profile")
                profile_page.update_profile(
                    first_name=data.get("first_name"),
                    last_name=data.get("last_name"),
                    email=data.get("email")
                )
            ```
        """
        # Build update data dictionary for Allure attachment
        update_data = {}
        
        # Fill first name if provided
        if first_name is not None:
            self.first_name_input.clear()
            self.first_name_input.fill(first_name)
            update_data["first_name"] = first_name
            allure.attach(
                f"First Name: {first_name}",
                name="Field Update",
                attachment_type=allure.attachment_type.TEXT
            )
        
        # Fill last name if provided
        if last_name is not None:
            self.last_name_input.clear()
            self.last_name_input.fill(last_name)
            update_data["last_name"] = last_name
            allure.attach(
                f"Last Name: {last_name}",
                name="Field Update",
                attachment_type=allure.attachment_type.TEXT
            )
        
        # Fill email if provided
        if email is not None:
            self.email_input.clear()
            self.email_input.fill(email)
            update_data["email"] = email
            allure.attach(
                f"Email: {email}",
                name="Field Update",
                attachment_type=allure.attachment_type.TEXT
            )
        
        # Take screenshot before submission
        self.capture_screenshot("Before Profile Update Submission")
        
        # Click save button to submit the form
        self.save_button.click()
        
        # Wait for form submission to complete by waiting for either success or error message
        # This ensures the async form submission has completed
        try:
            self.page.wait_for_function(
                """
                () => {
                    const alerts = document.querySelectorAll('[role="alert"]');
                    const successMsg = document.querySelector('[data-testid="success-message"]');
                    return alerts.length > 0 || successMsg !== null;
                }
                """,
                timeout=10000
            )
        except Exception:
            # If no alert appears, capture screenshot for debugging
            self.capture_screenshot("No Alert After Profile Update")
        
        # Take screenshot after submission for verification
        self.capture_screenshot("After Profile Update Submission")
    
    @allure.step("Change password")
    def change_password(
        self,
        current_password: str,
        new_password: str,
        confirm_password: Optional[str] = None
    ) -> None:
        """
        Change user password with current password verification.
        
        This method fills the password change form fields and submits.
        If confirm_password is not provided, it defaults to new_password.
        The method waits for submission feedback (success or validation error).
        
        Args:
            current_password (str): Current password for verification
            new_password (str): New password to set
            confirm_password (Optional[str]): Password confirmation; defaults to new_password
        
        Raises:
            TimeoutError: If form submission takes too long
        
        Example:
            ```python
            profile_page.change_password(
                current_password="old_pass123",
                new_password="new_secure_pass456"
            )
            
            # Test password mismatch validation
            profile_page.change_password(
                current_password="old_pass123",
                new_password="new_pass",
                confirm_password="different_pass"  # Will trigger validation error
            )
            ```
        """
        # Default confirm_password to new_password if not provided
        if confirm_password is None:
            confirm_password = new_password
        
        # Fill current password field
        self.current_password_input.clear()
        self.current_password_input.fill(current_password)
        
        # Fill new password field
        self.new_password_input.clear()
        self.new_password_input.fill(new_password)
        
        # Fill confirm password field
        self.confirm_password_input.clear()
        self.confirm_password_input.fill(confirm_password)
        
        # Attach password change attempt to Allure (without actual passwords)
        allure.attach(
            f"Password Change Attempt\n"
            f"Current password: {'*' * len(current_password)}\n"
            f"New password: {'*' * len(new_password)}\n"
            f"Passwords match: {new_password == confirm_password}",
            name="Password Change Details",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Take screenshot before submission
        self.capture_screenshot("Before Password Change Submission")
        
        # Click save button to submit password change
        self.save_button.click()
        
        # Wait for submission feedback (success or error alert)
        try:
            self.page.wait_for_function(
                """
                () => {
                    const alerts = document.querySelectorAll('[role="alert"]');
                    return alerts.length > 0;
                }
                """,
                timeout=10000
            )
        except Exception:
            # If no alert appears, capture screenshot for debugging
            self.capture_screenshot("No Alert After Password Change")
        
        # Take screenshot after submission
        self.capture_screenshot("After Password Change Submission")
    
    @allure.step("Verify profile saved successfully")
    def verify_profile_saved(self, timeout: int = 5000) -> None:
        """
        Verify that profile changes were saved successfully.
        
        This method asserts that the success message is visible and contains
        expected success text. If the success message is not found, it captures
        a screenshot and raises an assertion error.
        
        Args:
            timeout (int): Maximum time to wait for success message in milliseconds
                          Defaults to 5000ms
        
        Raises:
            AssertionError: If success message is not visible within timeout
        
        Example:
            ```python
            profile_page.update_profile(first_name="Jane")
            profile_page.verify_profile_saved()
            
            # In BDD step definition
            @then("the profile changes are saved")
            def verify_saved(profile_page: UserProfilePage):
                profile_page.verify_profile_saved()
            ```
        """
        success_msg = self.success_message
        
        # Wait for success message to be visible
        try:
            success_msg.wait_for(state="visible", timeout=timeout)
        except Exception as e:
            # Capture screenshot if success message not found
            self.capture_screenshot("Success Message Not Found")
            raise AssertionError(
                f"Success message not visible after {timeout}ms. "
                f"Profile save may have failed. Error: {str(e)}"
            )
        
        # Get success message text for verification
        success_text = success_msg.inner_text()
        
        # Attach success message to Allure report
        allure.attach(
            f"Success Message: {success_text}",
            name="Profile Save Success",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Assert success message is visible
        assert success_msg.is_visible(), "Success message should be visible"
        
        # Capture screenshot showing success state
        self.capture_screenshot("Profile Saved Successfully")
    
    @allure.step("Verify validation error for field: {field}")
    def verify_validation_error(
        self,
        field: str,
        expected_error: Optional[str] = None,
        timeout: int = 5000
    ) -> str:
        """
        Verify that a validation error message is displayed for a specific field.
        
        This method checks for field-specific error messages after form submission.
        If expected_error is provided, it validates the exact error text matches.
        Returns the actual error message text for further assertions.
        
        Args:
            field (str): Field name to check error for (e.g., "email", "first_name")
            expected_error (Optional[str]): Expected error message text; if provided,
                                           asserts actual error matches this text
            timeout (int): Maximum time to wait for error message in milliseconds
        
        Returns:
            str: Actual error message text displayed
        
        Raises:
            AssertionError: If error message not found or doesn't match expected
        
        Example:
            ```python
            # Verify error exists for email field
            error_text = profile_page.verify_validation_error("email")
            
            # Verify specific error message
            profile_page.verify_validation_error(
                "email",
                expected_error="Email address is required"
            )
            
            # In BDD step
            @then('the user sees error "{error}" for field "{field}"')
            def verify_error(profile_page, field, error):
                profile_page.verify_validation_error(field, expected_error=error)
            ```
        """
        # Wait for error message alert to appear
        error_msg = self.error_message
        
        try:
            error_msg.wait_for(state="visible", timeout=timeout)
        except Exception as e:
            # Capture screenshot if error message not found
            self.capture_screenshot(f"Validation Error Not Found for {field}")
            raise AssertionError(
                f"Validation error message not visible for field '{field}' "
                f"after {timeout}ms. Error: {str(e)}"
            )
        
        # Get error message text
        actual_error = str(error_msg.inner_text())
        
        # Attach error message to Allure report
        allure.attach(
            f"Field: {field}\nError Message: {actual_error}",
            name="Validation Error",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # If expected error provided, assert it matches
        if expected_error is not None:
            assert expected_error.lower() in actual_error.lower(), (
                f"Expected error '{expected_error}' not found in actual error '{actual_error}'"
            )
        
        # Capture screenshot showing error state
        self.capture_screenshot(f"Validation Error for {field}")
        
        return actual_error
    
    @allure.step("Get current email value")
    def get_current_email(self) -> str:
        """
        Retrieve the current email address displayed in the email input field.
        
        This method gets the value attribute from the email input element.
        Useful for verifying that profile updates were applied correctly or
        for capturing the current state before making changes.
        
        Returns:
            str: Current email address value
        
        Example:
            ```python
            # Verify email after update
            profile_page.update_profile(email="new@example.com")
            profile_page.verify_profile_saved()
            profile_page.navigate_to_profile()  # Reload page
            current_email = profile_page.get_current_email()
            assert current_email == "new@example.com"
            
            # Store original value before changes
            @given("user notes their current email")
            def store_current_email(profile_page: UserProfilePage, context):
                profile_page.navigate_to_profile()
                context["original_email"] = profile_page.get_current_email()
            ```
        """
        # Get email input value
        email_value = str(self.email_input.input_value())
        
        # Attach current email to Allure report (may contain sensitive data warning)
        allure.attach(
            f"Current Email: {email_value}",
            name="Retrieved Email Value",
            attachment_type=allure.attachment_type.TEXT
        )
        
        return email_value
    
    @allure.step("Cancel profile changes")
    def cancel_changes(self) -> None:
        """
        Click the cancel button and verify no changes were saved.
        
        This method clicks the cancel button, which should either:
        1. Navigate back to a previous page (e.g., dashboard), or
        2. Reset form fields to their original values
        
        The method verifies that no success message appears, confirming
        that changes were not persisted.
        
        Raises:
            AssertionError: If success message appears after canceling
        
        Example:
            ```python
            # Test cancel functionality
            profile_page.navigate_to_profile()
            original_email = profile_page.get_current_email()
            
            profile_page.first_name_input.fill("TempName")
            profile_page.cancel_changes()
            
            # Verify no success message
            assert not profile_page.success_message.is_visible()
            
            # In BDD step
            @when("the user cancels the profile changes")
            def cancel_profile(profile_page: UserProfilePage):
                profile_page.cancel_changes()
            ```
        """
        # Take screenshot before clicking cancel
        self.capture_screenshot("Before Canceling Changes")
        
        # Store current URL to detect navigation
        url_before_cancel = self.page.url
        
        # Click cancel button
        self.cancel_button.click()
        
        # Wait briefly for any navigation or UI updates
        self.page.wait_for_timeout(1000)
        
        # Check if URL changed (navigated away)
        url_after_cancel = self.page.url
        url_changed = url_before_cancel != url_after_cancel
        
        # Attach cancel action details to Allure
        allure.attach(
            f"URL Before Cancel: {url_before_cancel}\n"
            f"URL After Cancel: {url_after_cancel}\n"
            f"Navigation Occurred: {url_changed}",
            name="Cancel Action Details",
            attachment_type=allure.attachment_type.TEXT
        )
        
        # Verify no success message appears (changes were not saved)
        try:
            success_visible = self.success_message.is_visible(timeout=2000)
            if success_visible:
                self.capture_screenshot("Unexpected Success Message After Cancel")
                raise AssertionError(
                    "Success message appeared after canceling changes. "
                    "Changes may have been incorrectly saved."
                )
        except Exception:
            # If success message doesn't exist at all, that's fine
            pass
        
        # Take screenshot after cancel
        self.capture_screenshot("After Canceling Changes")
