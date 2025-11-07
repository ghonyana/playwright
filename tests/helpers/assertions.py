"""
Custom Assertion Helpers for Test Automation Framework

This module provides domain-specific assertion functions for API response validation
and UI state verification with enhanced error messages that improve test readability
and debugging compared to standard Python assertions.

Features:
- API response assertions (status codes, JSON schemas, headers, performance)
- UI state assertions (visibility, text content, URL patterns, element counts)
- Data validation assertions (email format, date format)
- Descriptive error messages with contextual information
- Type-safe interfaces using type hints

Usage:
    from tests.helpers.assertions import (
        assert_status_code,
        assert_json_schema,
        assert_element_visible
    )
    
    # API assertion
    response = httpx.get("https://api.example.com/users/123")
    assert_status_code(response, 200, "User retrieval should succeed")
    assert_response_contains(response, "email")
    
    # UI assertion
    assert_element_visible(page, "button[aria-label='Submit']", "Submit button should be visible")
"""

import re
from datetime import datetime
from typing import Any, Optional, Dict

try:
    import httpx
except ImportError:
    httpx = None

try:
    from playwright.sync_api import Page
except ImportError:
    Page = None

try:
    import jsonschema
    from jsonschema import ValidationError as JSONSchemaValidationError
except ImportError:
    jsonschema = None
    JSONSchemaValidationError = None


# =============================================================================
# API Response Assertions
# =============================================================================

def assert_status_code(
    response: "httpx.Response",
    expected: int,
    message: Optional[str] = None
) -> None:
    """
    Assert HTTP response status code matches expected value.
    
    Provides detailed error message including actual status code and
    response body snippet for debugging failed assertions.
    
    Args:
        response: httpx Response object to validate
        expected: Expected HTTP status code (e.g., 200, 201, 404)
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If status code doesn't match expected value
        
    Example:
        >>> response = httpx.get("https://api.example.com/users")
        >>> assert_status_code(response, 200, "User list should return successfully")
    """
    if response.status_code != expected:
        error_msg = f"Expected status {expected}, got {response.status_code}"
        
        if message:
            error_msg = f"{message}: {error_msg}"
        
        # Include response body snippet for debugging (max 500 chars)
        try:
            body_text = response.text[:500]
            if len(response.text) > 500:
                body_text += "... (truncated)"
            error_msg += f"\nResponse body: {body_text}"
        except Exception:
            error_msg += "\nResponse body: <unable to decode>"
        
        # Include response headers for additional context
        try:
            content_type = response.headers.get("content-type", "unknown")
            error_msg += f"\nContent-Type: {content_type}"
        except Exception:
            pass
        
        raise AssertionError(error_msg)


def assert_json_schema(
    response: "httpx.Response",
    schema: Dict[str, Any]
) -> None:
    """
    Validate JSON response body against a JSON Schema.
    
    Uses jsonschema library to perform comprehensive schema validation.
    Provides detailed error messages indicating which part of the schema
    validation failed.
    
    Args:
        response: httpx Response object with JSON body
        schema: JSON Schema dictionary defining expected structure
        
    Raises:
        AssertionError: If response JSON doesn't match schema
        ImportError: If jsonschema library is not installed
        
    Example:
        >>> schema = {
        ...     "type": "object",
        ...     "properties": {
        ...         "id": {"type": "integer"},
        ...         "name": {"type": "string"}
        ...     },
        ...     "required": ["id", "name"]
        ... }
        >>> assert_json_schema(response, schema)
    """
    if jsonschema is None:
        raise ImportError(
            "jsonschema library is required for assert_json_schema. "
            "Install with: pip install jsonschema"
        )
    
    try:
        response_json = response.json()
    except Exception as e:
        raise AssertionError(
            f"Failed to parse response as JSON: {str(e)}\n"
            f"Response body: {response.text[:500]}"
        )
    
    try:
        jsonschema.validate(instance=response_json, schema=schema)
    except JSONSchemaValidationError as e:
        # Build detailed error message with validation failure context
        error_msg = "JSON Schema validation failed"
        error_msg += f"\nValidation error: {e.message}"
        
        if e.path:
            path_str = ".".join(str(p) for p in e.path)
            error_msg += f"\nFailed at path: {path_str}"
        
        if e.validator:
            error_msg += f"\nValidator: {e.validator}"
        
        if e.validator_value:
            error_msg += f"\nExpected constraint: {e.validator_value}"
        
        # Include actual value that failed validation
        error_msg += f"\nActual response: {response_json}"
        
        raise AssertionError(error_msg)


def assert_response_contains(
    response: "httpx.Response",
    key: str,
    value: Optional[Any] = None,
    message: Optional[str] = None
) -> None:
    """
    Assert response JSON contains a specific key (and optionally a specific value).
    
    Validates that the response body is valid JSON and contains the specified
    key. If value is provided, also validates the key's value matches.
    
    Args:
        response: httpx Response object with JSON body
        key: Key name to search for in JSON response
        value: Optional expected value for the key (if None, only checks key exists)
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If key is missing or value doesn't match
        
    Example:
        >>> assert_response_contains(response, "email")
        >>> assert_response_contains(response, "status", "active")
    """
    try:
        data = response.json()
    except Exception as e:
        error_msg = f"Failed to parse response as JSON: {str(e)}"
        if message:
            error_msg = f"{message}: {error_msg}"
        error_msg += f"\nResponse body: {response.text[:500]}"
        raise AssertionError(error_msg)
    
    # Check if key exists
    if key not in data:
        error_msg = f"Key '{key}' not found in response"
        if message:
            error_msg = f"{message}: {error_msg}"
        
        # Show available keys for debugging
        available_keys = list(data.keys()) if isinstance(data, dict) else []
        error_msg += f"\nAvailable keys: {available_keys}"
        error_msg += f"\nResponse: {data}"
        raise AssertionError(error_msg)
    
    # Check value if provided
    if value is not None:
        actual_value = data[key]
        if actual_value != value:
            error_msg = f"Expected {key}={value}, got {key}={actual_value}"
            if message:
                error_msg = f"{message}: {error_msg}"
            error_msg += f"\nFull response: {data}"
            raise AssertionError(error_msg)


def assert_response_time(
    response: "httpx.Response",
    max_seconds: float,
    message: Optional[str] = None
) -> None:
    """
    Assert API response completed within specified time limit.
    
    Validates response time performance requirement, useful for
    ensuring API endpoints meet SLA requirements.
    
    Args:
        response: httpx Response object to check timing
        max_seconds: Maximum allowed response time in seconds
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If response time exceeds max_seconds
        
    Example:
        >>> assert_response_time(response, 2.0, "User API should respond within 2s")
    """
    if not hasattr(response, 'elapsed'):
        raise AssertionError(
            "Response object doesn't have elapsed attribute. "
            "Ensure you're using httpx.Response object."
        )
    
    elapsed_seconds = response.elapsed.total_seconds()
    
    if elapsed_seconds > max_seconds:
        error_msg = (
            f"Response took {elapsed_seconds:.3f}s, "
            f"expected <{max_seconds:.3f}s"
        )
        if message:
            error_msg = f"{message}: {error_msg}"
        
        # Add URL context for debugging
        error_msg += f"\nRequest URL: {response.url}"
        error_msg += f"\nStatus code: {response.status_code}"
        
        raise AssertionError(error_msg)


# =============================================================================
# UI State Assertions (Playwright)
# =============================================================================

def assert_element_visible(
    page: "Page",
    selector: str,
    timeout: float = 5.0,
    message: Optional[str] = None
) -> None:
    """
    Assert that a UI element is visible on the page.
    
    Waits up to timeout seconds for element to become visible before failing.
    Provides enhanced error message with current URL and page state context.
    
    Args:
        page: Playwright Page instance
        selector: CSS selector, ARIA role, or test-id to locate element
        timeout: Maximum seconds to wait for visibility (default: 5.0)
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If element is not visible within timeout
        
    Example:
        >>> assert_element_visible(page, "button[aria-label='Submit']")
        >>> assert_element_visible(page, "role=navigation", timeout=10.0)
    """
    try:
        locator = page.locator(selector)
        # Use Playwright's built-in wait and visibility check
        if not locator.is_visible(timeout=timeout * 1000):  # Convert to milliseconds
            raise AssertionError(f"Element '{selector}' is not visible")
    except Exception as e:
        error_msg = f"Element '{selector}' not visible: {str(e)}"
        if message:
            error_msg = f"{message}: {error_msg}"
        
        # Add page context for debugging
        error_msg += f"\nCurrent URL: {page.url}"
        
        # Try to get page title for additional context
        try:
            page_title = page.title()
            error_msg += f"\nPage title: {page_title}"
        except Exception:
            pass
        
        raise AssertionError(error_msg)


def assert_text_present(
    page: "Page",
    text: str,
    message: Optional[str] = None
) -> None:
    """
    Assert that specific text appears somewhere on the page.
    
    Searches entire page content for the specified text string.
    Case-sensitive by default.
    
    Args:
        page: Playwright Page instance
        text: Text string to search for on page
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If text is not found on page
        
    Example:
        >>> assert_text_present(page, "Welcome back")
        >>> assert_text_present(page, "Order confirmed", "Success message should appear")
    """
    try:
        # Use Playwright's text content API for reliable text search
        content = page.text_content("body")
        if content is None or text not in content:
            error_msg = f"Text '{text}' not found on page"
            if message:
                error_msg = f"{message}: {error_msg}"
            error_msg += f"\nCurrent URL: {page.url}"
            
            # Show snippet of page content for debugging
            if content:
                snippet = content[:200].replace('\n', ' ')
                error_msg += f"\nPage content preview: {snippet}..."
            
            raise AssertionError(error_msg)
    except AssertionError:
        raise
    except Exception as e:
        error_msg = f"Failed to check text presence: {str(e)}"
        if message:
            error_msg = f"{message}: {error_msg}"
        error_msg += f"\nCurrent URL: {page.url}"
        raise AssertionError(error_msg)


def assert_url_matches(
    page: "Page",
    pattern: str,
    message: Optional[str] = None
) -> None:
    """
    Assert current browser URL matches a regular expression pattern.
    
    Useful for validating navigation, redirects, and URL parameters.
    
    Args:
        page: Playwright Page instance
        pattern: Regular expression pattern to match against URL
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If URL doesn't match pattern
        
    Example:
        >>> assert_url_matches(page, r"/dashboard$")
        >>> assert_url_matches(page, r"/users/\\d+", "Should navigate to user detail page")
    """
    current_url = page.url
    
    try:
        match = re.search(pattern, current_url)
        if not match:
            error_msg = f"URL '{current_url}' doesn't match pattern '{pattern}'"
            if message:
                error_msg = f"{message}: {error_msg}"
            
            # Add page title for context
            try:
                page_title = page.title()
                error_msg += f"\nPage title: {page_title}"
            except Exception:
                pass
            
            raise AssertionError(error_msg)
    except AssertionError:
        raise
    except re.error as e:
        raise AssertionError(f"Invalid regex pattern '{pattern}': {str(e)}")


def assert_element_count(
    page: "Page",
    selector: str,
    expected_count: int,
    message: Optional[str] = None
) -> None:
    """
    Assert exact number of elements matching selector on page.
    
    Useful for validating lists, tables, and repeated UI components.
    
    Args:
        page: Playwright Page instance
        selector: CSS selector, ARIA role, or test-id to locate elements
        expected_count: Expected number of matching elements
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If actual count doesn't match expected count
        
    Example:
        >>> assert_element_count(page, "tr.user-row", 10, "Should show 10 users")
        >>> assert_element_count(page, "role=button", 3)
    """
    try:
        actual_count = page.locator(selector).count()
        
        if actual_count != expected_count:
            error_msg = (
                f"Expected {expected_count} elements matching '{selector}', "
                f"found {actual_count}"
            )
            if message:
                error_msg = f"{message}: {error_msg}"
            
            error_msg += f"\nCurrent URL: {page.url}"
            
            raise AssertionError(error_msg)
    except AssertionError:
        raise
    except Exception as e:
        error_msg = f"Failed to count elements: {str(e)}"
        if message:
            error_msg = f"{message}: {error_msg}"
        error_msg += f"\nSelector: {selector}"
        error_msg += f"\nCurrent URL: {page.url}"
        raise AssertionError(error_msg)


# =============================================================================
# Data Validation Assertions
# =============================================================================

def assert_valid_email(
    email: str,
    message: Optional[str] = None
) -> None:
    """
    Assert string is a valid email address format.
    
    Uses RFC 5322 simplified regex pattern for email validation.
    Checks basic structure: localpart@domain.tld
    
    Args:
        email: Email address string to validate
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If email format is invalid
        
    Example:
        >>> assert_valid_email("user@example.com")
        >>> assert_valid_email(response_data["email"], "API should return valid email")
    """
    # RFC 5322 simplified email regex pattern
    # Matches: localpart@domain.tld
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not isinstance(email, str):
        error_msg = f"Expected string, got {type(email).__name__}"
        if message:
            error_msg = f"{message}: {error_msg}"
        raise AssertionError(error_msg)
    
    if not re.match(pattern, email):
        error_msg = f"Invalid email format: '{email}'"
        if message:
            error_msg = f"{message}: {error_msg}"
        
        # Provide helpful hints
        if '@' not in email:
            error_msg += "\nHint: Email must contain @ symbol"
        elif '.' not in email.split('@')[-1]:
            error_msg += "\nHint: Domain must contain at least one dot"
        
        raise AssertionError(error_msg)


def assert_date_format(
    date_str: str,
    format_str: str = "%Y-%m-%d",
    message: Optional[str] = None
) -> None:
    """
    Assert string matches expected date/datetime format.
    
    Uses Python's datetime.strptime to validate format compliance.
    Common formats:
    - "%Y-%m-%d" for "2024-03-15"
    - "%Y-%m-%d %H:%M:%S" for "2024-03-15 14:30:00"
    - "%d/%m/%Y" for "15/03/2024"
    
    Args:
        date_str: Date string to validate
        format_str: Expected date format (default: ISO 8601 date format)
        message: Optional custom error message prefix
        
    Raises:
        AssertionError: If date string doesn't match format
        
    Example:
        >>> assert_date_format("2024-03-15")
        >>> assert_date_format("2024-03-15 14:30:00", "%Y-%m-%d %H:%M:%S")
        >>> assert_date_format(response["created_at"], "%Y-%m-%dT%H:%M:%SZ")
    """
    if not isinstance(date_str, str):
        error_msg = f"Expected string, got {type(date_str).__name__}"
        if message:
            error_msg = f"{message}: {error_msg}"
        raise AssertionError(error_msg)
    
    try:
        datetime.strptime(date_str, format_str)
    except ValueError as e:
        error_msg = f"Date '{date_str}' doesn't match format '{format_str}'"
        if message:
            error_msg = f"{message}: {error_msg}"
        
        error_msg += f"\nParsing error: {str(e)}"
        
        # Provide format examples
        error_msg += f"\nExpected format example: {datetime.now().strftime(format_str)}"
        
        raise AssertionError(error_msg)


# =============================================================================
# Module Metadata
# =============================================================================

__all__ = [
    # API assertions
    "assert_status_code",
    "assert_json_schema",
    "assert_response_contains",
    "assert_response_time",
    # UI assertions
    "assert_element_visible",
    "assert_text_present",
    "assert_url_matches",
    "assert_element_count",
    # Data validation assertions
    "assert_valid_email",
    "assert_date_format",
]
