"""
Custom Playwright wait condition helpers for UI testing and API polling.

This module provides reusable wait strategies that enhance test reliability beyond
Playwright's built-in wait mechanisms. It includes conditions for element counting,
text appearance, URL patterns, loading indicators, API polling, and dynamic content.

Functions:
    wait_for_element_count: Wait for specific number of elements matching selector
    wait_for_text_to_appear: Wait for specific text to appear anywhere on page
    wait_for_url_pattern: Wait for URL to match regex pattern
    wait_for_no_loading_indicators: Wait for all loading spinners/overlays to disappear
    wait_for_api_condition: Poll API endpoint until condition function returns True
    wait_for_entity_state: Wait for entity to reach specific state
    wait_for_stable_dom: Wait for DOM to stop changing under selector
    wait_for_network_idle: Wait for all network requests to complete
"""

import re
import time
from typing import Any, Callable, Dict, Optional

from playwright.sync_api import Page
from httpx import Client


def wait_for_element_count(
    page: Page, selector: str, count: int, timeout: int = 30000
) -> bool:
    """
    Wait for a specific number of elements matching the selector.
    
    This is useful when you need to wait for a specific number of items to be rendered,
    such as waiting for a table to have exactly 5 rows, or a list to contain 10 items.
    
    Args:
        page: Playwright Page instance
        selector: CSS selector or other locator strategy
        count: Expected number of elements
        timeout: Maximum wait time in milliseconds (default: 30000)
    
    Returns:
        bool: True if condition is met within timeout
    
    Raises:
        TimeoutError: If condition is not met within timeout
    
    Example:
        # Wait for exactly 5 table rows
        wait_for_element_count(page, "table tbody tr", 5)
    """
    try:
        locator = page.locator(selector)
        page.wait_for_function(
            """
            ([selector, expectedCount]) => {
                const elements = document.querySelectorAll(selector);
                return elements.length === expectedCount;
            }
            """,
            arg=[selector, count],
            timeout=timeout
        )
        # Verify the count one more time
        actual_count = locator.count()
        if actual_count != count:
            raise TimeoutError(
                f"Expected {count} elements matching '{selector}', "
                f"but found {actual_count}"
            )
        return True
    except Exception as e:
        actual_count = page.locator(selector).count()
        raise TimeoutError(
            f"Timeout waiting for {count} elements matching '{selector}'. "
            f"Current count: {actual_count}. Timeout: {timeout}ms"
        ) from e


def wait_for_text_to_appear(
    page: Page, text: str, timeout: int = 30000
) -> bool:
    """
    Wait for specific text to appear anywhere on the page.
    
    This is more flexible than Playwright's get_by_text().wait_for() as it searches
    the entire page content without needing to know the exact element structure.
    
    Args:
        page: Playwright Page instance
        text: Text string to search for (case-sensitive)
        timeout: Maximum wait time in milliseconds (default: 30000)
    
    Returns:
        bool: True if text appears within timeout
    
    Raises:
        TimeoutError: If text does not appear within timeout
    
    Example:
        # Wait for success message
        wait_for_text_to_appear(page, "Operation completed successfully")
    """
    try:
        page.wait_for_function(
            """
            (searchText) => {
                return document.body.innerText.includes(searchText);
            }
            """,
            arg=text,
            timeout=timeout
        )
        # Double-check by reading page content
        page_content = page.content()
        if text not in page_content:
            raise TimeoutError(f"Text '{text}' not found in page content")
        return True
    except Exception as e:
        raise TimeoutError(
            f"Timeout waiting for text '{text}' to appear. Timeout: {timeout}ms"
        ) from e


def wait_for_url_pattern(
    page: Page, pattern: str, timeout: int = 30000
) -> bool:
    """
    Wait for URL to match a regex pattern.
    
    This enables flexible URL waiting strategies like waiting for /dashboard/.*
    pattern or /users/[0-9]+ pattern instead of exact URL matching, supporting
    dynamic routing and parameterized URLs in SPA navigation tests.
    
    Args:
        page: Playwright Page instance
        pattern: Regular expression pattern to match against URL
        timeout: Maximum wait time in milliseconds (default: 30000)
    
    Returns:
        bool: True if URL matches pattern within timeout
    
    Raises:
        TimeoutError: If URL doesn't match pattern within timeout
    
    Example:
        # Wait for any user profile URL
        wait_for_url_pattern(page, r"/users/\d+/profile")
    """
    compiled_pattern = re.compile(pattern)
    start_time = time.time()
    timeout_seconds = timeout / 1000.0
    
    try:
        while time.time() - start_time < timeout_seconds:
            current_url = page.url
            if compiled_pattern.search(current_url):
                return True
            time.sleep(0.1)  # Poll every 100ms
        
        # Timeout reached
        current_url = page.url
        raise TimeoutError(
            f"Timeout waiting for URL to match pattern '{pattern}'. "
            f"Current URL: {current_url}. Timeout: {timeout}ms"
        )
    except TimeoutError:
        raise
    except Exception as e:
        current_url = page.url
        raise TimeoutError(
            f"Error waiting for URL pattern '{pattern}'. Current URL: {current_url}"
        ) from e


def wait_for_no_loading_indicators(
    page: Page, timeout: int = 30000
) -> bool:
    """
    Wait for all loading spinners and overlays to disappear.
    
    This waits for common loading indicator patterns to be removed from the DOM,
    ensuring the page is fully loaded before proceeding with test actions.
    
    Args:
        page: Playwright Page instance
        timeout: Maximum wait time in milliseconds (default: 30000)
    
    Returns:
        bool: True if all loading indicators are gone within timeout
    
    Raises:
        TimeoutError: If loading indicators don't disappear within timeout
    
    Example:
        # Wait for page to finish loading
        wait_for_no_loading_indicators(page)
    """
    # Common selectors for loading indicators
    loading_selectors = [
        "[data-testid='loading']",
        "[data-testid='spinner']",
        ".loading",
        ".spinner",
        "[aria-busy='true']",
        "[role='progressbar']",
        ".overlay.loading",
    ]
    
    try:
        page.wait_for_function(
            """
            (selectors) => {
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    // Check if any loading indicators are visible
                    for (const el of elements) {
                        const style = window.getComputedStyle(el);
                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                            return false;
                        }
                    }
                }
                return true;
            }
            """,
            arg=loading_selectors,
            timeout=timeout
        )
        return True
    except Exception as e:
        # Find which loading indicators are still visible
        visible_indicators = []
        for selector in loading_selectors:
            count = page.locator(f"{selector}:visible").count()
            if count > 0:
                visible_indicators.append(f"{selector} ({count})")
        
        raise TimeoutError(
            f"Timeout waiting for loading indicators to disappear. "
            f"Still visible: {', '.join(visible_indicators) if visible_indicators else 'unknown'}. "
            f"Timeout: {timeout}ms"
        ) from e


def wait_for_api_condition(
    api_client: Client,
    endpoint: str,
    condition_fn: Callable[[Any], bool],
    timeout: int = 30,
    poll_interval: float = 1.0
) -> Any:
    """
    Poll an API endpoint until a condition function returns True.
    
    This is useful for waiting on async operations that need polling, such as
    waiting for a background job to complete or a resource to reach a desired state.
    
    Args:
        api_client: httpx Client instance
        endpoint: API endpoint path (relative to client base URL)
        condition_fn: Function that takes response data and returns bool
        timeout: Maximum wait time in seconds (default: 30)
        poll_interval: Time between polls in seconds (default: 1.0)
    
    Returns:
        Any: The response data when condition is met
    
    Raises:
        TimeoutError: If condition is not met within timeout
        httpx.HTTPError: If API request fails
    
    Example:
        # Wait for job to complete
        def is_complete(data):
            return data.get("status") == "completed"
        
        result = wait_for_api_condition(
            client, "/jobs/123", is_complete, timeout=60
        )
    """
    start_time = time.time()
    last_response = None
    attempts = 0
    
    while time.time() - start_time < timeout:
        attempts += 1
        try:
            response = api_client.get(endpoint)
            response.raise_for_status()
            data = response.json()
            last_response = data
            
            if condition_fn(data):
                return data
            
        except Exception as e:
            # Log but continue polling unless it's a critical error
            if response and response.status_code >= 500:
                raise
            # For 4xx errors or connection issues, continue polling
            pass
        
        time.sleep(poll_interval)
    
    # Timeout reached
    raise TimeoutError(
        f"Timeout waiting for API condition on {endpoint}. "
        f"Attempts: {attempts}. Timeout: {timeout}s. "
        f"Last response: {last_response}"
    )


def wait_for_entity_state(
    api_client: Client,
    entity_type: str,
    entity_id: str,
    expected_state: str,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Wait for an entity to reach a specific state.
    
    This is a common pattern for async job completion, where you need to poll
    an entity's status field until it reaches 'completed', 'ready', 'active', etc.
    
    Args:
        api_client: httpx Client instance
        entity_type: Type of entity (e.g., 'jobs', 'users', 'orders')
        entity_id: Unique identifier of the entity
        expected_state: The state value to wait for (e.g., 'completed', 'ready')
        timeout: Maximum wait time in seconds (default: 30)
    
    Returns:
        Dict: The complete entity data when expected state is reached
    
    Raises:
        TimeoutError: If entity doesn't reach expected state within timeout
        httpx.HTTPError: If API request fails
    
    Example:
        # Wait for order to be processed
        order = wait_for_entity_state(
            client, "orders", "12345", "processed", timeout=60
        )
    """
    endpoint = f"/{entity_type}/{entity_id}"
    
    def check_state(data: Dict[str, Any]) -> bool:
        current_state = data.get("state") or data.get("status")
        return current_state == expected_state
    
    try:
        return wait_for_api_condition(
            api_client=api_client,
            endpoint=endpoint,
            condition_fn=check_state,
            timeout=timeout,
            poll_interval=1.0
        )
    except TimeoutError as e:
        raise TimeoutError(
            f"Entity {entity_type}/{entity_id} did not reach state '{expected_state}' "
            f"within {timeout}s"
        ) from e


def wait_for_stable_dom(
    page: Page, selector: str, timeout: int = 30000
) -> bool:
    """
    Wait for the DOM to stop changing under a specific selector.
    
    This is useful for AJAX-heavy pages where content is dynamically updated.
    The function waits until the DOM structure remains stable for a short period.
    
    Args:
        page: Playwright Page instance
        selector: CSS selector to monitor for changes
        timeout: Maximum wait time in milliseconds (default: 30000)
    
    Returns:
        bool: True if DOM becomes stable within timeout
    
    Raises:
        TimeoutError: If DOM keeps changing beyond timeout
    
    Example:
        # Wait for search results to stop updating
        wait_for_stable_dom(page, "#search-results")
    """
    stability_threshold = 500  # DOM must be stable for 500ms
    start_time = time.time()
    timeout_seconds = timeout / 1000.0
    last_content = None
    stable_since = None
    
    try:
        while time.time() - start_time < timeout_seconds:
            current_content = page.locator(selector).evaluate(
                "(el) => el.innerHTML"
            )
            
            if current_content == last_content:
                # Content hasn't changed
                if stable_since is None:
                    stable_since = time.time()
                elif (time.time() - stable_since) * 1000 >= stability_threshold:
                    # Stable for long enough
                    return True
            else:
                # Content changed, reset stability timer
                stable_since = None
                last_content = current_content
            
            time.sleep(0.1)  # Check every 100ms
        
        # Timeout reached
        raise TimeoutError(
            f"Timeout waiting for stable DOM under selector '{selector}'. "
            f"DOM kept changing. Timeout: {timeout}ms"
        )
    except TimeoutError:
        raise
    except Exception as e:
        raise TimeoutError(
            f"Error waiting for stable DOM under selector '{selector}'"
        ) from e


def wait_for_network_idle(
    page: Page, timeout: int = 30000
) -> bool:
    """
    Wait for all network requests to complete.
    
    This waits for the network to become idle (no pending requests) using
    Playwright's networkidle load state, which is useful for AJAX-heavy pages.
    
    Args:
        page: Playwright Page instance
        timeout: Maximum wait time in milliseconds (default: 30000)
    
    Returns:
        bool: True if network becomes idle within timeout
    
    Raises:
        TimeoutError: If network doesn't become idle within timeout
    
    Example:
        # Wait for all AJAX calls to complete
        wait_for_network_idle(page)
    """
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        return True
    except Exception as e:
        raise TimeoutError(
            f"Timeout waiting for network idle. Timeout: {timeout}ms"
        ) from e
