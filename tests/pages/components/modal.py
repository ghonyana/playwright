"""
Modal Component Module

This module provides a reusable ModalComponent class for interacting with modal dialogs,
confirmation popups, and alert overlays that appear across multiple pages. The component
follows the Page Object Pattern and uses stable ARIA-based locators to ensure test reliability.

Modal Dialog Patterns:
---------------------
The ModalComponent supports various modal types commonly found in web applications:
- Confirmation modals: Yes/No, OK/Cancel dialogs for user confirmations
- Alert modals: Single OK button for information/error/warning messages
- Form modals: Dialogs containing input fields for data entry
- Error/warning modals: Critical messages requiring user acknowledgment

Stable Locator Strategy:
-----------------------
This component prioritizes ARIA dialog semantics for maximum stability:
1. role="dialog" or role="alertdialog" for modal containers
2. ARIA roles for buttons and headings within the modal
3. data-testid for backdrop and container elements when needed
4. Avoid brittle CSS class selectors

Integration Points:
------------------
- BasePage: Inherits common page object functionality and Playwright access
- Allure: Hierarchical test step reporting for modal interactions
- Playwright expect: Reliable assertions with auto-waiting and retry logic

Example Usage:
-------------
```python
# In a page object
from tests.pages.components.modal import ModalComponent

class UserProfilePage(BasePage):
    def __init__(self, page: Page):
        super().__init__(page)
        self.delete_modal = ModalComponent(page)
    
    def delete_account(self):
        self.find_by_role("button", name="Delete Account").click()
        self.delete_modal.wait_for_modal_open()
        assert "Are you sure" in self.delete_modal.get_modal_content()
        self.delete_modal.click_confirm()
        self.delete_modal.wait_for_modal_close()

# In a test
def test_account_deletion(page: Page):
    profile_page = UserProfilePage(page)
    profile_page.navigate("/profile")
    profile_page.delete_account()
```
"""

from typing import Optional, Dict, Any

import allure
from playwright.sync_api import expect

from tests.pages.base_page import BasePage


class ModalComponent(BasePage):
    """
    Reusable component for interacting with modal dialogs and overlays.
    
    This component encapsulates all modal interaction patterns including waiting for
    modal visibility, retrieving modal content, clicking action buttons, and verifying
    modal state. It follows the Page Object Pattern to abstract modal implementation
    details from test code.
    
    The component supports various modal types:
    - Confirmation dialogs with Confirm/Cancel buttons
    - Alert dialogs with single OK button
    - Form dialogs with input fields
    - Error/warning dialogs requiring acknowledgment
    
    All locator properties use stable ARIA-based selectors to ensure test reliability
    across UI refactoring and styling changes.
    
    Attributes:
        page (Page): Playwright Page instance inherited from BasePage
        modal_container: Locator for the modal dialog container element
        modal_title: Locator for the modal heading/title element
        modal_description: Locator for the modal body/description text
        close_button: Locator for the X close button
        confirm_button: Locator for Confirm/OK/Yes action button
        cancel_button: Locator for Cancel/No button
        modal_backdrop: Locator for the modal overlay/backdrop element
    
    Example:
        ```python
        # Create modal component instance
        modal = ModalComponent(page)
        
        # Trigger an action that shows a modal
        page.get_by_role("button", name="Delete User").click()
        
        # Wait for modal to appear
        modal.wait_for_modal_open()
        
        # Verify modal content
        assert "permanently delete" in modal.get_modal_content()
        
        # Confirm the action
        modal.click_confirm()
        
        # Verify modal closed
        modal.wait_for_modal_close()
        ```
    """
    
    def __init__(self, page, base_url: Optional[str] = None):
        """
        Initialize the ModalComponent with a Playwright Page instance.
        
        Args:
            page: Playwright Page instance from pytest fixture
            base_url: Optional base URL override (inherited from BasePage)
        """
        super().__init__(page, base_url)
    
    # Locator Properties - Using ARIA-based stable selectors
    
    @property
    def modal_container(self):
        """
        Locator for the modal dialog container using ARIA dialog role.
        
        Prefers role="dialog" for standard modals or role="alertdialog" for
        alert/confirmation modals. This is the most stable selector as it relies
        on semantic ARIA attributes.
        
        Returns:
            Locator: Playwright locator for the modal container element
        """
        # Try dialog role first (most common), fallback to alertdialog
        dialog = self.page.get_by_role("dialog")
        if dialog.count() > 0:
            return dialog.first
        return self.page.get_by_role("alertdialog").first
    
    @property
    def modal_title(self):
        """
        Locator for the modal title/heading element.
        
        Finds the heading within the modal dialog using ARIA role hierarchy.
        
        Returns:
            Locator: Playwright locator for the modal title element
        """
        return self.modal_container.get_by_role("heading")
    
    @property
    def modal_description(self):
        """
        Locator for the modal body/description text.
        
        Attempts to find the modal description using aria-describedby relationship
        or falls back to locating text content within the modal container.
        
        Returns:
            Locator: Playwright locator for the modal description element
        """
        # Try to find element with id matching aria-describedby
        container = self.modal_container
        described_by = container.get_attribute("aria-describedby")
        
        if described_by:
            return self.page.locator(f"#{described_by}")
        
        # Fallback: Find paragraph or div with description content
        # Look for common description containers within the modal
        return container.locator('[id*="description"], [class*="description"], p, div').first
    
    @property
    def close_button(self):
        """
        Locator for the close (X) button typically in the modal header.
        
        Uses ARIA button role with common close button labels.
        
        Returns:
            Locator: Playwright locator for the close button element
        """
        modal = self.modal_container
        
        # Try various common close button labels
        close_labels = ["Close", "close", "×", "✕", "Dismiss"]
        
        for label in close_labels:
            button = modal.get_by_role("button", name=label)
            if button.count() > 0:
                return button.first
        
        # Fallback to aria-label
        return modal.get_by_label("Close").first
    
    @property
    def confirm_button(self):
        """
        Locator for the confirm/primary action button.
        
        Finds buttons with common confirmation labels (Confirm, OK, Yes, Submit, etc.).
        
        Returns:
            Locator: Playwright locator for the confirm button element
        """
        modal = self.modal_container
        
        # Try various common confirmation button labels
        confirm_labels = ["Confirm", "OK", "Yes", "Submit", "Accept", "Continue", "Delete", "Save"]
        
        for label in confirm_labels:
            button = modal.get_by_role("button", name=label)
            if button.count() > 0:
                return button.first
        
        # Fallback to primary button by test-id
        return modal.get_by_test_id("confirm-button").first
    
    @property
    def cancel_button(self):
        """
        Locator for the cancel/secondary action button.
        
        Finds buttons with common cancellation labels (Cancel, No, etc.).
        
        Returns:
            Locator: Playwright locator for the cancel button element
        """
        modal = self.modal_container
        
        # Try various common cancel button labels
        cancel_labels = ["Cancel", "No", "Dismiss", "Close"]
        
        for label in cancel_labels:
            button = modal.get_by_role("button", name=label)
            if button.count() > 0:
                return button.first
        
        # Fallback to cancel button by test-id
        return modal.get_by_test_id("cancel-button").first
    
    @property
    def modal_backdrop(self):
        """
        Locator for the modal backdrop/overlay element.
        
        The backdrop is the semi-transparent overlay behind the modal that dims
        the rest of the page. Uses data-testid for identification.
        
        Returns:
            Locator: Playwright locator for the modal backdrop element
        """
        return self.page.get_by_test_id("modal-backdrop")
    
    # Interaction Methods
    
    @allure.step("Wait for modal to open")
    def wait_for_modal_open(self, timeout: Optional[int] = 10000) -> None:
        """
        Wait for the modal dialog to appear and become visible.
        
        This method uses Playwright's expect assertion with auto-waiting and retry
        logic to ensure the modal is fully rendered and visible before proceeding.
        
        Args:
            timeout: Maximum wait time in milliseconds (default: 10000ms = 10s)
        
        Raises:
            AssertionError: If modal doesn't appear within the timeout period
        
        Example:
            ```python
            page.get_by_role("button", name="Open Dialog").click()
            modal.wait_for_modal_open()
            # Modal is now visible and ready for interaction
            ```
        """
        try:
            expect(self.modal_container).to_be_visible(timeout=timeout)
            
            allure.attach(
                "Modal dialog is now visible and ready for interaction",
                name="Modal State",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Capture screenshot of open modal for debugging
            self.capture_screenshot("Modal Opened", full_page=False)
            
        except AssertionError as e:
            # Capture screenshot on failure for debugging
            self.capture_screenshot("Modal Failed to Open", full_page=True)
            raise AssertionError(
                f"Modal dialog did not appear within {timeout}ms timeout. "
                f"Check if the modal trigger action succeeded."
            ) from e
    
    @allure.step("Wait for modal to close")
    def wait_for_modal_close(self, timeout: Optional[int] = 10000) -> None:
        """
        Wait for the modal dialog to disappear from the page.
        
        This method verifies the modal is no longer visible after a close action,
        ensuring the page is ready for subsequent interactions.
        
        Args:
            timeout: Maximum wait time in milliseconds (default: 10000ms = 10s)
        
        Raises:
            AssertionError: If modal remains visible after the timeout period
        
        Example:
            ```python
            modal.click_confirm()
            modal.wait_for_modal_close()
            # Modal is now closed and page is interactive
            ```
        """
        try:
            expect(self.modal_container).to_be_hidden(timeout=timeout)
            
            allure.attach(
                "Modal dialog has been closed successfully",
                name="Modal State",
                attachment_type=allure.attachment_type.TEXT
            )
            
        except AssertionError as e:
            # Capture screenshot showing modal still visible
            self.capture_screenshot("Modal Failed to Close", full_page=True)
            raise AssertionError(
                f"Modal dialog remained visible after {timeout}ms timeout. "
                f"Check if the close action completed successfully."
            ) from e
    
    @allure.step("Click confirm button")
    def click_confirm(self, wait_for_close: bool = True, timeout: Optional[int] = 10000) -> None:
        """
        Click the modal's confirm/primary action button.
        
        This method clicks the confirm button (OK, Yes, Confirm, Submit, etc.) and
        optionally waits for the modal to close. Use this for affirmative actions
        that proceed with the modal's intended operation.
        
        Args:
            wait_for_close: Whether to wait for modal to close after clicking (default: True)
            timeout: Maximum wait time for modal to close in milliseconds (default: 10000ms)
        
        Raises:
            TimeoutError: If confirm button is not clickable
            AssertionError: If wait_for_close=True and modal doesn't close
        
        Example:
            ```python
            # Standard confirmation flow
            modal.wait_for_modal_open()
            modal.click_confirm()  # Clicks and waits for close
            
            # For modals that don't auto-close
            modal.click_confirm(wait_for_close=False)
            ```
        """
        try:
            # Ensure modal is visible before clicking
            expect(self.modal_container).to_be_visible()
            
            # Click the confirm button
            self.confirm_button.click()
            
            allure.attach(
                "Clicked confirm button in modal dialog",
                name="Action",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Wait for modal to close if requested
            if wait_for_close:
                self.wait_for_modal_close(timeout=timeout)
                
        except Exception as e:
            self.capture_screenshot("Confirm Button Click Failed", full_page=True)
            raise
    
    @allure.step("Click cancel button")
    def click_cancel(self, wait_for_close: bool = True, timeout: Optional[int] = 10000) -> None:
        """
        Click the modal's cancel/secondary action button.
        
        This method clicks the cancel button (Cancel, No, Dismiss, etc.) to abort
        the modal's action and optionally waits for the modal to close.
        
        Args:
            wait_for_close: Whether to wait for modal to close after clicking (default: True)
            timeout: Maximum wait time for modal to close in milliseconds (default: 10000ms)
        
        Raises:
            TimeoutError: If cancel button is not clickable
            AssertionError: If wait_for_close=True and modal doesn't close
        
        Example:
            ```python
            modal.wait_for_modal_open()
            modal.click_cancel()  # Dismisses modal
            ```
        """
        try:
            # Ensure modal is visible before clicking
            expect(self.modal_container).to_be_visible()
            
            # Click the cancel button
            self.cancel_button.click()
            
            allure.attach(
                "Clicked cancel button in modal dialog",
                name="Action",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Wait for modal to close if requested
            if wait_for_close:
                self.wait_for_modal_close(timeout=timeout)
                
        except Exception as e:
            self.capture_screenshot("Cancel Button Click Failed", full_page=True)
            raise
    
    @allure.step("Click close button")
    def click_close(self, wait_for_close: bool = True, timeout: Optional[int] = 10000) -> None:
        """
        Click the modal's close (X) button in the header.
        
        This method clicks the close button typically located in the modal header's
        top-right corner. This is distinct from cancel buttons and is often used
        for dismissing informational modals.
        
        Args:
            wait_for_close: Whether to wait for modal to close after clicking (default: True)
            timeout: Maximum wait time for modal to close in milliseconds (default: 10000ms)
        
        Raises:
            TimeoutError: If close button is not clickable
            AssertionError: If wait_for_close=True and modal doesn't close
        
        Example:
            ```python
            modal.wait_for_modal_open()
            modal.click_close()  # Click X button
            ```
        """
        try:
            # Ensure modal is visible before clicking
            expect(self.modal_container).to_be_visible()
            
            # Click the close button
            self.close_button.click()
            
            allure.attach(
                "Clicked close (X) button in modal dialog",
                name="Action",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Wait for modal to close if requested
            if wait_for_close:
                self.wait_for_modal_close(timeout=timeout)
                
        except Exception as e:
            self.capture_screenshot("Close Button Click Failed", full_page=True)
            raise
    
    @allure.step("Click backdrop to close modal")
    def click_backdrop_to_close(self, timeout: Optional[int] = 10000) -> None:
        """
        Click outside the modal (on the backdrop) to dismiss it.
        
        Some modals support dismissal by clicking on the semi-transparent backdrop
        overlay. This method simulates that user action.
        
        Args:
            timeout: Maximum wait time for modal to close in milliseconds (default: 10000ms)
        
        Raises:
            TimeoutError: If backdrop is not clickable
            AssertionError: If modal doesn't close after clicking backdrop
        
        Note:
            Not all modals support backdrop dismissal. If the modal requires explicit
            button interaction, this method may not close the modal.
        
        Example:
            ```python
            modal.wait_for_modal_open()
            modal.click_backdrop_to_close()  # Click outside modal
            ```
        """
        try:
            # Ensure backdrop is visible
            expect(self.modal_backdrop).to_be_visible()
            
            # Click the backdrop
            self.modal_backdrop.click()
            
            allure.attach(
                "Clicked modal backdrop to dismiss dialog",
                name="Action",
                attachment_type=allure.attachment_type.TEXT
            )
            
            # Wait for modal to close
            self.wait_for_modal_close(timeout=timeout)
            
        except Exception as e:
            self.capture_screenshot("Backdrop Click Failed", full_page=True)
            raise
    
    @allure.step("Get modal title")
    def get_modal_title(self) -> str:
        """
        Retrieve the modal's title/heading text.
        
        This method extracts the text content from the modal's heading element,
        useful for verifying the correct modal is displayed.
        
        Returns:
            str: Modal title text content
        
        Raises:
            TimeoutError: If modal title element is not visible
        
        Example:
            ```python
            modal.wait_for_modal_open()
            title = modal.get_modal_title()
            assert title == "Confirm Deletion"
            ```
        """
        try:
            # Wait for title to be visible
            expect(self.modal_title).to_be_visible()
            
            # Get the title text
            title_text = self.modal_title.inner_text()
            
            allure.attach(
                f"Modal title: {title_text}",
                name="Modal Content",
                attachment_type=allure.attachment_type.TEXT
            )
            
            return title_text
            
        except Exception as e:
            self.capture_screenshot("Failed to Get Modal Title", full_page=True)
            raise
    
    @allure.step("Get modal content")
    def get_modal_content(self) -> str:
        """
        Retrieve the modal's body/description text content.
        
        This method extracts the descriptive text from the modal's body, useful for
        verifying modal messages, error text, or confirmation prompts.
        
        Returns:
            str: Modal body text content
        
        Raises:
            TimeoutError: If modal description element is not visible
        
        Example:
            ```python
            modal.wait_for_modal_open()
            content = modal.get_modal_content()
            assert "permanently delete" in content.lower()
            ```
        """
        try:
            # Wait for description to be visible
            expect(self.modal_description).to_be_visible()
            
            # Get the description text
            description_text = self.modal_description.inner_text()
            
            allure.attach(
                f"Modal content: {description_text}",
                name="Modal Content",
                attachment_type=allure.attachment_type.TEXT
            )
            
            return description_text
            
        except Exception as e:
            self.capture_screenshot("Failed to Get Modal Content", full_page=True)
            raise
    
    @allure.step("Check if modal is open")
    def is_modal_open(self) -> bool:
        """
        Check if the modal dialog is currently visible on the page.
        
        This method provides a non-blocking check of modal visibility state,
        useful for conditional logic in tests.
        
        Returns:
            bool: True if modal is visible, False otherwise
        
        Example:
            ```python
            if modal.is_modal_open():
                modal.click_close()
            
            # Or use in assertions
            assert modal.is_modal_open(), "Expected modal to be visible"
            ```
        """
        try:
            # Check if modal container is visible (short timeout)
            expect(self.modal_container).to_be_visible(timeout=1000)
            
            allure.attach(
                "Modal is currently open",
                name="Modal State",
                attachment_type=allure.attachment_type.TEXT
            )
            
            return True
            
        except AssertionError:
            allure.attach(
                "Modal is not currently open",
                name="Modal State",
                attachment_type=allure.attachment_type.TEXT
            )
            
            return False
    
    @allure.step("Verify modal contains text: {text}")
    def verify_modal_contains_text(self, text: str, case_sensitive: bool = False) -> None:
        """
        Assert that the modal contains specific text in its title or body.
        
        This method uses Playwright's expect assertion with to_contain_text() to verify
        that expected content is displayed in the modal dialog. The assertion provides
        auto-waiting and retry logic for reliable verification.
        
        Args:
            text: Expected text to find in modal
            case_sensitive: Whether the text search should be case-sensitive (default: False)
        
        Raises:
            AssertionError: If text is not found in modal container within timeout
        
        Example:
            ```python
            modal.wait_for_modal_open()
            modal.verify_modal_contains_text("Are you sure")
            modal.verify_modal_contains_text("CONFIRM", case_sensitive=True)
            ```
        """
        try:
            # Use Playwright's expect with to_contain_text for reliable assertion
            # This provides auto-waiting and retry logic
            if case_sensitive:
                # For case-sensitive, get text and do manual comparison
                # since Playwright's to_contain_text is case-insensitive by default
                title = self.get_modal_title()
                content = self.get_modal_content()
                full_modal_text = f"{title} {content}"
                
                if text not in full_modal_text:
                    raise AssertionError(
                        f"Expected text '{text}' not found in modal (case-sensitive). "
                        f"Modal title: '{title}', Modal content: '{content}'"
                    )
            else:
                # Use expect with to_contain_text for case-insensitive matching
                expect(self.modal_container).to_contain_text(text)
            
            allure.attach(
                f"Verified modal contains text: '{text}' (case_sensitive={case_sensitive})",
                name="Modal Verification",
                attachment_type=allure.attachment_type.TEXT
            )
            
        except Exception as e:
            self.capture_screenshot("Modal Text Verification Failed", full_page=True)
            raise
    
    @allure.step("Verify modal title is exactly: {expected_title}")
    def verify_modal_title_exact(self, expected_title: str) -> None:
        """
        Assert that the modal title exactly matches the expected text.
        
        This method uses Playwright's expect assertion with to_have_text() to verify
        the modal title contains exactly the expected text (no partial matching).
        
        Args:
            expected_title: Exact text expected in the modal title
        
        Raises:
            AssertionError: If modal title doesn't exactly match expected text
        
        Example:
            ```python
            modal.wait_for_modal_open()
            modal.verify_modal_title_exact("Delete Account")
            ```
        """
        try:
            # Use expect with to_have_text for exact text matching
            expect(self.modal_title).to_have_text(expected_title)
            
            allure.attach(
                f"Verified modal title exactly matches: '{expected_title}'",
                name="Modal Title Verification",
                attachment_type=allure.attachment_type.TEXT
            )
            
        except Exception as e:
            self.capture_screenshot("Modal Title Verification Failed", full_page=True)
            actual_title = self.modal_title.inner_text() if self.modal_title.count() > 0 else "N/A"
            raise AssertionError(
                f"Expected modal title to be '{expected_title}', but got '{actual_title}'"
            ) from e

