"""
Browser navigation tool implementations for Playwright MCP server.

This module provides navigation functions that enable LLM agents to control browser
navigation during exploratory testing sessions. All functions operate on Playwright
Page objects and return structured dict responses for JSON serialization.

Functions:
    - navigate_to_url: Navigate to a specified URL with wait conditions
    - reload_page: Reload the current page
    - navigate_back: Navigate to previous page in history
    - navigate_forward: Navigate to next page in history
    - wait_for_navigation: Wait for navigation events to complete
    - validate_url: Validate URL format before navigation
"""

import logging
import asyncio
from typing import Dict, Optional, Literal, Any
from urllib.parse import urlparse

from playwright.async_api import Page, Error as PlaywrightError


# Module-level logger for navigation operations
logger = logging.getLogger(__name__)

# Type alias for wait_until states
WaitUntilState = Literal['load', 'domcontentloaded', 'networkidle', 'commit']


async def navigate_to_url(
    page: Page,
    url: str,
    wait_until: WaitUntilState = 'networkidle',
    timeout: int = 30000
) -> Dict[str, Any]:
    """
    Navigate to a specified URL with configurable wait conditions.
    
    This is the primary navigation function for LLM agents controlling browser
    navigation through the MCP server. It handles URL validation, navigation
    execution, and error handling.
    
    Args:
        page: Playwright Page instance to navigate
        url: Target URL to navigate to (must include http:// or https:// scheme)
        wait_until: Wait condition for navigation completion. Options:
            - 'load': Wait for load event (default browser behavior)
            - 'domcontentloaded': Wait for DOMContentLoaded event
            - 'networkidle': Wait for network to be idle (recommended for SPAs)
            - 'commit': Wait for navigation to be committed
        timeout: Maximum time to wait for navigation in milliseconds (default: 30000)
    
    Returns:
        Dict with structure:
            {
                'success': bool,
                'url': str (requested URL),
                'current_url': str (actual URL after navigation, may differ due to redirects),
                'title': str (page title after navigation),
                'duration_ms': int (navigation time in milliseconds),
                'error_code': str (optional, present on failure),
                'error_message': str (optional, present on failure)
            }
    
    Example:
        result = await navigate_to_url(page, 'https://example.com', wait_until='networkidle')
        if result['success']:
            print(f"Navigated to {result['current_url']} - {result['title']}")
    """
    import time
    start_time = time.time()
    
    logger.info(f"Navigating to URL: {url} with wait_until='{wait_until}', timeout={timeout}ms")
    
    # Validate URL format before attempting navigation
    is_valid, validation_error = validate_url(url)
    if not is_valid:
        logger.error(f"URL validation failed: {validation_error}")
        return {
            'success': False,
            'url': url,
            'current_url': '',
            'title': '',
            'duration_ms': 0,
            'error_code': 'INVALID_URL',
            'error_message': validation_error
        }
    
    try:
        # Execute navigation with specified wait condition
        response = await page.goto(url, wait_until=wait_until, timeout=timeout)
        
        # Extract page information after successful navigation
        current_url = page.url
        title = await page.title()
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Navigation successful: {current_url} - '{title}' (took {duration_ms}ms)")
        
        return {
            'success': True,
            'url': url,
            'current_url': current_url,
            'title': title,
            'duration_ms': duration_ms
        }
    
    except asyncio.TimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Navigation timeout after {timeout}ms"
        logger.error(f"Navigation timeout: {url} (waited {duration_ms}ms)")
        
        return {
            'success': False,
            'url': url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'NAVIGATION_TIMEOUT',
            'error_message': error_msg
        }
    
    except PlaywrightError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        logger.error(f"Playwright navigation error: {error_msg}", exc_info=True)
        
        # Determine error code based on error message
        error_code = 'NAVIGATION_FAILED'
        if 'net::ERR_NAME_NOT_RESOLVED' in error_msg:
            error_code = 'DNS_ERROR'
        elif 'net::ERR_CONNECTION_REFUSED' in error_msg:
            error_code = 'CONNECTION_REFUSED'
        elif 'net::ERR_CERT' in error_msg:
            error_code = 'SSL_ERROR'
        
        return {
            'success': False,
            'url': url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': error_code,
            'error_message': error_msg
        }
    
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Unexpected error during navigation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'url': url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'UNEXPECTED_ERROR',
            'error_message': error_msg
        }


async def reload_page(
    page: Page,
    wait_until: WaitUntilState = 'networkidle',
    timeout: int = 30000
) -> Dict[str, Any]:
    """
    Reload the current page.
    
    Refreshes the current page, useful for testing dynamic content updates
    or resetting page state during exploration.
    
    Args:
        page: Playwright Page instance to reload
        wait_until: Wait condition for reload completion (same options as navigate_to_url)
        timeout: Maximum time to wait for reload in milliseconds (default: 30000)
    
    Returns:
        Dict with structure:
            {
                'success': bool,
                'current_url': str (URL after reload),
                'title': str (page title after reload),
                'duration_ms': int,
                'error_code': str (optional),
                'error_message': str (optional)
            }
    
    Example:
        result = await reload_page(page)
        if result['success']:
            print(f"Page reloaded: {result['title']}")
    """
    import time
    start_time = time.time()
    
    current_url = page.url
    logger.info(f"Reloading page: {current_url} with wait_until='{wait_until}'")
    
    try:
        # Execute page reload
        await page.reload(wait_until=wait_until, timeout=timeout)
        
        # Extract page information after reload
        title = await page.title()
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Page reload successful: {current_url} - '{title}' (took {duration_ms}ms)")
        
        return {
            'success': True,
            'current_url': page.url,
            'title': title,
            'duration_ms': duration_ms
        }
    
    except asyncio.TimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Reload timeout after {timeout}ms"
        logger.error(f"Reload timeout: {current_url} (waited {duration_ms}ms)")
        
        return {
            'success': False,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'RELOAD_TIMEOUT',
            'error_message': error_msg
        }
    
    except PlaywrightError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        logger.error(f"Playwright reload error: {error_msg}", exc_info=True)
        
        return {
            'success': False,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'RELOAD_FAILED',
            'error_message': error_msg
        }
    
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Unexpected error during reload: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'UNEXPECTED_ERROR',
            'error_message': error_msg
        }


async def navigate_back(
    page: Page,
    timeout: int = 30000
) -> Dict[str, Any]:
    """
    Navigate to the previous page in browser history (back button).
    
    Simulates clicking the browser's back button, useful for testing navigation
    flows and multi-step user journeys.
    
    Args:
        page: Playwright Page instance to navigate
        timeout: Maximum time to wait for navigation in milliseconds (default: 30000)
    
    Returns:
        Dict with structure:
            {
                'success': bool,
                'previous_url': str (URL before navigation),
                'current_url': str (URL after navigation back),
                'title': str (page title after navigation),
                'duration_ms': int,
                'error_code': str (optional),
                'error_message': str (optional)
            }
    
    Example:
        result = await navigate_back(page)
        if result['success']:
            print(f"Navigated back to: {result['current_url']}")
    """
    import time
    start_time = time.time()
    
    previous_url = page.url
    logger.info(f"Navigating back from: {previous_url}")
    
    try:
        # Attempt to navigate back in history
        response = await page.go_back(timeout=timeout)
        
        # Check if navigation occurred (response is None if no history available)
        if response is None:
            logger.warning("No history available for back navigation")
            return {
                'success': False,
                'previous_url': previous_url,
                'current_url': previous_url,
                'title': await page.title(),
                'duration_ms': 0,
                'error_code': 'NO_HISTORY',
                'error_message': 'No previous page in history'
            }
        
        # Extract page information after successful navigation
        current_url = page.url
        title = await page.title()
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Back navigation successful: {previous_url} -> {current_url} (took {duration_ms}ms)")
        
        return {
            'success': True,
            'previous_url': previous_url,
            'current_url': current_url,
            'title': title,
            'duration_ms': duration_ms
        }
    
    except asyncio.TimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Back navigation timeout after {timeout}ms"
        logger.error(f"Back navigation timeout (waited {duration_ms}ms)")
        
        return {
            'success': False,
            'previous_url': previous_url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'NAVIGATION_TIMEOUT',
            'error_message': error_msg
        }
    
    except PlaywrightError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        logger.error(f"Playwright back navigation error: {error_msg}", exc_info=True)
        
        return {
            'success': False,
            'previous_url': previous_url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'NAVIGATION_FAILED',
            'error_message': error_msg
        }
    
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Unexpected error during back navigation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'previous_url': previous_url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'UNEXPECTED_ERROR',
            'error_message': error_msg
        }


async def navigate_forward(
    page: Page,
    timeout: int = 30000
) -> Dict[str, Any]:
    """
    Navigate to the next page in browser history (forward button).
    
    Simulates clicking the browser's forward button, useful after using
    navigate_back() to test forward navigation flows.
    
    Args:
        page: Playwright Page instance to navigate
        timeout: Maximum time to wait for navigation in milliseconds (default: 30000)
    
    Returns:
        Dict with structure:
            {
                'success': bool,
                'previous_url': str (URL before navigation),
                'current_url': str (URL after navigation forward),
                'title': str (page title after navigation),
                'duration_ms': int,
                'error_code': str (optional),
                'error_message': str (optional)
            }
    
    Example:
        result = await navigate_forward(page)
        if result['success']:
            print(f"Navigated forward to: {result['current_url']}")
    """
    import time
    start_time = time.time()
    
    previous_url = page.url
    logger.info(f"Navigating forward from: {previous_url}")
    
    try:
        # Attempt to navigate forward in history
        response = await page.go_forward(timeout=timeout)
        
        # Check if navigation occurred (response is None if no forward history available)
        if response is None:
            logger.warning("No forward history available")
            return {
                'success': False,
                'previous_url': previous_url,
                'current_url': previous_url,
                'title': await page.title(),
                'duration_ms': 0,
                'error_code': 'NO_FORWARD_HISTORY',
                'error_message': 'No next page in history'
            }
        
        # Extract page information after successful navigation
        current_url = page.url
        title = await page.title()
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Forward navigation successful: {previous_url} -> {current_url} (took {duration_ms}ms)")
        
        return {
            'success': True,
            'previous_url': previous_url,
            'current_url': current_url,
            'title': title,
            'duration_ms': duration_ms
        }
    
    except asyncio.TimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Forward navigation timeout after {timeout}ms"
        logger.error(f"Forward navigation timeout (waited {duration_ms}ms)")
        
        return {
            'success': False,
            'previous_url': previous_url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'NAVIGATION_TIMEOUT',
            'error_message': error_msg
        }
    
    except PlaywrightError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        logger.error(f"Playwright forward navigation error: {error_msg}", exc_info=True)
        
        return {
            'success': False,
            'previous_url': previous_url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'NAVIGATION_FAILED',
            'error_message': error_msg
        }
    
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Unexpected error during forward navigation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'previous_url': previous_url,
            'current_url': page.url,
            'title': '',
            'duration_ms': duration_ms,
            'error_code': 'UNEXPECTED_ERROR',
            'error_message': error_msg
        }


async def wait_for_navigation(
    page: Page,
    state: WaitUntilState = 'networkidle',
    timeout: int = 30000
) -> Dict[str, Any]:
    """
    Wait for navigation events to complete on the current page.
    
    Useful for waiting after triggering navigation through click events or
    form submissions, ensuring the page has fully loaded before proceeding.
    
    Args:
        page: Playwright Page instance to wait for
        state: Load state to wait for:
            - 'load': Wait for load event
            - 'domcontentloaded': Wait for DOMContentLoaded event
            - 'networkidle': Wait for network idle (no requests for 500ms)
            - 'commit': Wait for navigation commit
        timeout: Maximum time to wait in milliseconds (default: 30000)
    
    Returns:
        Dict with structure:
            {
                'success': bool,
                'current_url': str (URL after navigation),
                'title': str (page title),
                'state': str (wait state that was achieved),
                'duration_ms': int,
                'error_code': str (optional),
                'error_message': str (optional)
            }
    
    Example:
        # After clicking a link
        await page.click('a[href="/dashboard"]')
        result = await wait_for_navigation(page, state='networkidle')
        if result['success']:
            print(f"Navigation complete to: {result['current_url']}")
    """
    import time
    start_time = time.time()
    
    logger.info(f"Waiting for navigation state '{state}' with timeout={timeout}ms")
    
    try:
        # Wait for the specified load state
        await page.wait_for_load_state(state=state, timeout=timeout)
        
        # Extract page information after load state achieved
        current_url = page.url
        title = await page.title()
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"Navigation wait completed: {current_url} - state '{state}' achieved (took {duration_ms}ms)")
        
        return {
            'success': True,
            'current_url': current_url,
            'title': title,
            'state': state,
            'duration_ms': duration_ms
        }
    
    except asyncio.TimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Wait for navigation state '{state}' timeout after {timeout}ms"
        logger.error(f"Navigation wait timeout: state '{state}' not achieved (waited {duration_ms}ms)")
        
        return {
            'success': False,
            'current_url': page.url,
            'title': '',
            'state': state,
            'duration_ms': duration_ms,
            'error_code': 'WAIT_TIMEOUT',
            'error_message': error_msg
        }
    
    except PlaywrightError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        logger.error(f"Playwright wait error: {error_msg}", exc_info=True)
        
        return {
            'success': False,
            'current_url': page.url,
            'title': '',
            'state': state,
            'duration_ms': duration_ms,
            'error_code': 'WAIT_FAILED',
            'error_message': error_msg
        }
    
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Unexpected error while waiting for navigation: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        return {
            'success': False,
            'current_url': page.url,
            'title': '',
            'state': state,
            'duration_ms': duration_ms,
            'error_code': 'UNEXPECTED_ERROR',
            'error_message': error_msg
        }


def validate_url(url: str) -> tuple[bool, str]:
    """
    Validate URL format before navigation attempts.
    
    Checks that the URL has a valid format with required components (scheme, netloc).
    This prevents navigation errors from malformed URLs and provides clear error
    messages for LLM agents.
    
    Args:
        url: URL string to validate
    
    Returns:
        Tuple of (is_valid, error_message):
            - (True, "") if URL is valid
            - (False, "error description") if URL is invalid
    
    Validation checks:
        - URL must have http:// or https:// scheme
        - URL must have a valid netloc (domain)
        - URL must be parseable by urlparse
    
    Example:
        is_valid, error = validate_url("https://example.com")
        if is_valid:
            # Proceed with navigation
        else:
            print(f"Invalid URL: {error}")
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"
    
    # Remove leading/trailing whitespace
    url = url.strip()
    
    if not url:
        return False, "URL cannot be empty or whitespace only"
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        
        # Check for required scheme (http or https)
        if not parsed.scheme:
            return False, "URL must include scheme (http:// or https://)"
        
        if parsed.scheme not in ('http', 'https'):
            return False, f"URL scheme must be http or https, got: {parsed.scheme}"
        
        # Check for netloc (domain)
        if not parsed.netloc:
            return False, "URL must include a valid domain (netloc)"
        
        # Additional validation for netloc format
        if '.' not in parsed.netloc and parsed.netloc != 'localhost':
            logger.warning(f"URL netloc '{parsed.netloc}' may be invalid (no TLD and not localhost)")
            # Allow it but log a warning - some internal URLs may not have TLDs
        
        logger.debug(f"URL validation passed: {url}")
        return True, ""
    
    except ValueError as e:
        error_msg = f"URL parsing failed: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    
    except Exception as e:
        error_msg = f"Unexpected error validating URL: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, error_msg
