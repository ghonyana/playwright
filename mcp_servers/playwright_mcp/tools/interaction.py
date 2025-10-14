"""
Element interaction tool implementations for Playwright MCP server.

This module provides element interaction functions for LLM-driven browser automation,
prioritizing stable ARIA-based locator strategies over brittle CSS/XPath selectors.

Locator Strategy Priority:
    1. role:button[name=Submit] - ARIA roles (highest stability)
    2. label:Email Address - Form labels
    3. testid:login-button - Explicit test IDs
    4. text:Sign In - Text content
    5. CSS/XPath - Fallback (least stable, generates warnings)

All functions return JSON-serializable dictionaries for MCP endpoint responses.
"""

from playwright.async_api import Page, Locator, Error as PlaywrightError, TimeoutError
from typing import Dict, Any, Optional, Literal, Tuple
import logging
import re
import json

logger = logging.getLogger(__name__)


def parse_selector(selector: str) -> Tuple[str, str, Optional[str]]:
    """
    Parse selector string to extract locator strategy and value.
    
    Selector Formats:
        - 'role:button[name=Submit]' -> ('role', 'button', 'Submit')
        - 'label:Email Address' -> ('label', 'Email Address', None)
        - 'testid:submit-btn' -> ('testid', 'submit-btn', None)
        - 'text:Click here' -> ('text', 'Click here', None)
        - 'placeholder:Enter email' -> ('placeholder', 'Enter email', None)
        - '.btn-primary' -> ('css', '.btn-primary', None)
    
    Args:
        selector: Selector string with optional strategy prefix
    
    Returns:
        Tuple of (strategy, value, name) where name is optional for role-based selectors
    """
    # Pattern for role-based selectors with name attribute: role:button[name=Submit]
    role_with_name_pattern = r'^role:(\w+)\[name=([^\]]+)\]$'
    match = re.match(role_with_name_pattern, selector)
    if match:
        return ('role', match.group(1), match.group(2))
    
    # Pattern for strategy:value format (label:, testid:, text:, placeholder:)
    strategy_pattern = r'^(label|testid|text|placeholder|title):(.+)$'
    match = re.match(strategy_pattern, selector)
    if match:
        strategy = match.group(1)
        value = match.group(2)
        return (strategy, value, None)
    
    # Fallback to CSS selector
    logger.warning(
        f"Using fallback CSS selector: '{selector}'. "
        "Consider using stable locators (role:, label:, testid:, text:)"
    )
    return ('css', selector, None)


def build_locator(page: Page, selector: str) -> Locator:
    """
    Build Playwright Locator from parsed selector string.
    
    Maps selector strategy to appropriate Playwright locator method:
        - 'role' -> page.get_by_role()
        - 'label' -> page.get_by_label()
        - 'testid' -> page.get_by_test_id()
        - 'text' -> page.get_by_text()
        - 'placeholder' -> page.get_by_placeholder()
        - 'title' -> page.get_by_title()
        - 'css' -> page.locator()
    
    Args:
        page: Playwright Page instance
        selector: Selector string to parse and build
    
    Returns:
        Playwright Locator object ready for interaction
    """
    strategy, value, name = parse_selector(selector)
    
    logger.debug(f"Building locator: strategy={strategy}, value={value}, name={name}")
    
    if strategy == 'role':
        if name:
            return page.get_by_role(value, name=name)
        else:
            return page.get_by_role(value)
    elif strategy == 'label':
        return page.get_by_label(value)
    elif strategy == 'testid':
        return page.get_by_test_id(value)
    elif strategy == 'text':
        return page.get_by_text(value)
    elif strategy == 'placeholder':
        return page.get_by_placeholder(value)
    elif strategy == 'title':
        return page.get_by_title(value)
    else:  # css fallback
        return page.locator(value)


async def click_element(page: Page, selector: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    Click an element using stable locator strategies.
    
    Args:
        page: Playwright Page instance
        selector: Selector string (supports role:, label:, testid:, text:, css)
        timeout: Timeout in milliseconds (default 30000)
    
    Returns:
        Dict with success status, element metadata, and selector used
        
    Example:
        result = await click_element(page, "role:button[name=Submit]")
        # {"success": True, "element_text": "Submit", "element_role": "button", "selector_used": "role:button[name=Submit]"}
    """
    logger.info(f"Attempting to click element: {selector}")
    
    try:
        locator = build_locator(page, selector)
        
        # Click with automatic actionability waits
        await locator.click(timeout=timeout)
        
        # Extract element metadata
        element_text = await locator.text_content() or ""
        
        # Try to get role attribute, fallback to empty string
        try:
            element_role = await locator.get_attribute('role') or ""
        except Exception:
            element_role = ""
        
        logger.info(f"Successfully clicked element: {selector} (text: '{element_text}')")
        
        return {
            "success": True,
            "element_text": element_text.strip(),
            "element_role": element_role,
            "selector_used": selector
        }
    
    except TimeoutError:
        error_msg = f"Element not found within {timeout}ms: {selector}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "timeout",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except PlaywrightError as e:
        error_msg = f"Element not actionable: {selector}. Reason: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "not_actionable",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except Exception as e:
        error_msg = f"Unexpected error clicking element {selector}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "selector_used": selector
        }


async def type_text(page: Page, selector: str, text: str, clear_first: bool = True) -> Dict[str, Any]:
    """
    Type text into an input element.
    
    Args:
        page: Playwright Page instance
        selector: Selector string for the input element
        text: Text to type
        clear_first: Whether to clear existing content first (default True)
    
    Returns:
        Dict with success status, element label, and text entered
    """
    logger.info(f"Attempting to type text into element: {selector}")
    
    try:
        locator = build_locator(page, selector)
        
        # Clear existing content if requested
        if clear_first:
            await locator.clear()
        
        # Use fill for efficiency (faster than character-by-character typing)
        await locator.fill(text)
        
        # Extract element label
        try:
            element_label = await locator.get_attribute('aria-label') or ""
            if not element_label:
                # Try to find associated label element
                element_id = await locator.get_attribute('id')
                if element_id:
                    label_locator = page.locator(f'label[for="{element_id}"]')
                    if await label_locator.count() > 0:
                        element_label = await label_locator.text_content() or ""
        except Exception:
            element_label = ""
        
        logger.info(f"Successfully typed text into element: {selector}")
        
        return {
            "success": True,
            "element_label": element_label.strip(),
            "text_entered": text,
            "selector_used": selector
        }
    
    except TimeoutError:
        error_msg = f"Element not found: {selector}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "timeout",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except PlaywrightError as e:
        error_msg = f"Cannot type into element {selector}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "not_actionable",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except Exception as e:
        error_msg = f"Unexpected error typing text: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "selector_used": selector
        }


async def press_key(page: Page, key: str, selector: Optional[str] = None) -> Dict[str, Any]:
    """
    Press a keyboard key, optionally on a specific element.
    
    Args:
        page: Playwright Page instance
        key: Key to press (e.g., 'Enter', 'Escape', 'Tab', 'Control+A')
        selector: Optional selector to focus element before pressing key
    
    Returns:
        Dict with success status and key pressed
        
    Examples:
        await press_key(page, 'Enter', 'role:button[name=Submit]')
        await press_key(page, 'Escape')  # Press on currently focused element
    """
    logger.info(f"Attempting to press key: {key}" + (f" on element: {selector}" if selector else ""))
    
    try:
        # Focus element if selector provided
        if selector:
            locator = build_locator(page, selector)
            await locator.focus()
        
        # Press the key
        await page.keyboard.press(key)
        
        logger.info(f"Successfully pressed key: {key}")
        
        return {
            "success": True,
            "key_pressed": key,
            "selector_used": selector if selector else None
        }
    
    except TimeoutError:
        error_msg = f"Element not found: {selector}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "timeout",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except Exception as e:
        error_msg = f"Error pressing key {key}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "selector_used": selector
        }


async def toggle_checkbox(page: Page, selector: str, checked: bool) -> Dict[str, Any]:
    """
    Check or uncheck a checkbox element.
    
    Args:
        page: Playwright Page instance
        selector: Selector string for the checkbox element
        checked: True to check, False to uncheck
    
    Returns:
        Dict with success status, final state, and element label
    """
    logger.info(f"Attempting to {'check' if checked else 'uncheck'} checkbox: {selector}")
    
    try:
        locator = build_locator(page, selector)
        
        # Check or uncheck
        if checked:
            await locator.check()
        else:
            await locator.uncheck()
        
        # Verify final state
        final_state = await locator.is_checked()
        
        # Extract element label
        try:
            element_label = await locator.get_attribute('aria-label') or ""
            if not element_label:
                element_id = await locator.get_attribute('id')
                if element_id:
                    label_locator = page.locator(f'label[for="{element_id}"]')
                    if await label_locator.count() > 0:
                        element_label = await label_locator.text_content() or ""
        except Exception:
            element_label = ""
        
        logger.info(f"Successfully toggled checkbox: {selector} to {final_state}")
        
        return {
            "success": True,
            "final_state": final_state,
            "element_label": element_label.strip(),
            "selector_used": selector
        }
    
    except TimeoutError:
        error_msg = f"Checkbox not found: {selector}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "timeout",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except PlaywrightError as e:
        error_msg = f"Cannot toggle checkbox {selector}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "not_actionable",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except Exception as e:
        error_msg = f"Unexpected error toggling checkbox: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "selector_used": selector
        }


async def select_option(page: Page, selector: str, option: str, by: str = 'label') -> Dict[str, Any]:
    """
    Select an option from a dropdown element.
    
    Args:
        page: Playwright Page instance
        selector: Selector string for the select element
        option: Option to select
        by: Selection method - 'label', 'value', or 'index' (default 'label')
    
    Returns:
        Dict with success status, selected option, and element label
    """
    logger.info(f"Attempting to select option '{option}' by {by} in: {selector}")
    
    try:
        locator = build_locator(page, selector)
        
        # Select option based on method
        if by == 'label':
            await locator.select_option(label=option)
        elif by == 'value':
            await locator.select_option(value=option)
        elif by == 'index':
            await locator.select_option(index=int(option))
        else:
            raise ValueError(f"Invalid selection method: {by}. Must be 'label', 'value', or 'index'")
        
        # Extract element label
        try:
            element_label = await locator.get_attribute('aria-label') or ""
            if not element_label:
                element_id = await locator.get_attribute('id')
                if element_id:
                    label_locator = page.locator(f'label[for="{element_id}"]')
                    if await label_locator.count() > 0:
                        element_label = await label_locator.text_content() or ""
        except Exception:
            element_label = ""
        
        logger.info(f"Successfully selected option '{option}' in: {selector}")
        
        return {
            "success": True,
            "selected_option": option,
            "element_label": element_label.strip(),
            "selector_used": selector
        }
    
    except TimeoutError:
        error_msg = f"Select element not found: {selector}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "timeout",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except (PlaywrightError, ValueError) as e:
        error_msg = f"Cannot select option in {selector}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "not_actionable",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except Exception as e:
        error_msg = f"Unexpected error selecting option: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "selector_used": selector
        }


async def hover_element(page: Page, selector: str, timeout: int = 30000) -> Dict[str, Any]:
    """
    Hover over an element to reveal tooltips or trigger hover effects.
    
    Args:
        page: Playwright Page instance
        selector: Selector string for the element to hover
        timeout: Timeout in milliseconds (default 30000)
    
    Returns:
        Dict with success status, element text, and selector used
    """
    logger.info(f"Attempting to hover over element: {selector}")
    
    try:
        locator = build_locator(page, selector)
        
        # Hover with timeout
        await locator.hover(timeout=timeout)
        
        # Extract element text after hover (may reveal tooltips)
        element_text = await locator.text_content() or ""
        
        logger.info(f"Successfully hovered over element: {selector}")
        
        return {
            "success": True,
            "element_text": element_text.strip(),
            "hovered_selector": selector
        }
    
    except TimeoutError:
        error_msg = f"Element not found within {timeout}ms: {selector}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "timeout",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except PlaywrightError as e:
        error_msg = f"Cannot hover over element {selector}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "not_actionable",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except Exception as e:
        error_msg = f"Unexpected error hovering element: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "selector_used": selector
        }


async def focus_element(page: Page, selector: str) -> Dict[str, Any]:
    """
    Focus an element to trigger focus events or prepare for keyboard input.
    
    Args:
        page: Playwright Page instance
        selector: Selector string for the element to focus
    
    Returns:
        Dict with success status and element label
    """
    logger.info(f"Attempting to focus element: {selector}")
    
    try:
        locator = build_locator(page, selector)
        
        # Focus the element
        await locator.focus()
        
        # Extract element label
        try:
            element_label = await locator.get_attribute('aria-label') or ""
            if not element_label:
                element_id = await locator.get_attribute('id')
                if element_id:
                    label_locator = page.locator(f'label[for="{element_id}"]')
                    if await label_locator.count() > 0:
                        element_label = await label_locator.text_content() or ""
        except Exception:
            element_label = ""
        
        logger.info(f"Successfully focused element: {selector}")
        
        return {
            "success": True,
            "element_label": element_label.strip(),
            "selector_used": selector
        }
    
    except TimeoutError:
        error_msg = f"Element not found: {selector}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "timeout",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except PlaywrightError as e:
        error_msg = f"Cannot focus element {selector}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "not_actionable",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except Exception as e:
        error_msg = f"Unexpected error focusing element: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "selector_used": selector
        }


async def get_element_info(page: Page, selector: str) -> Dict[str, Any]:
    """
    Extract comprehensive metadata about an element for LLM understanding.
    
    Provides detailed information including tag name, role, ARIA attributes,
    text content, visibility, and bounding box for exploration and debugging.
    
    Args:
        page: Playwright Page instance
        selector: Selector string for the element to inspect
    
    Returns:
        Dict with comprehensive element metadata including:
            - tag_name: HTML tag name
            - role: ARIA role or implicit role
            - aria_label: ARIA label attribute
            - text_content: Element text content
            - is_visible: Visibility status
            - is_enabled: Enabled status
            - is_editable: Editability status
            - bounding_box: Element position and size
    """
    logger.info(f"Attempting to get element info for: {selector}")
    
    try:
        locator = build_locator(page, selector)
        
        # Wait for element to be attached to DOM
        await locator.wait_for(state='attached', timeout=10000)
        
        # Extract tag name using JavaScript evaluation
        tag_name = await locator.evaluate('el => el.tagName.toLowerCase()')
        
        # Extract ARIA role
        role = await locator.get_attribute('role') or ""
        if not role:
            # Try to determine implicit role based on tag name
            implicit_roles = {
                'button': 'button',
                'a': 'link',
                'input': 'textbox',
                'textarea': 'textbox',
                'select': 'combobox',
                'h1': 'heading',
                'h2': 'heading',
                'h3': 'heading',
                'h4': 'heading',
                'h5': 'heading',
                'h6': 'heading',
                'nav': 'navigation',
                'main': 'main',
                'article': 'article',
                'aside': 'complementary',
                'footer': 'contentinfo',
                'header': 'banner'
            }
            role = implicit_roles.get(tag_name, "")
        
        # Extract ARIA label
        aria_label = await locator.get_attribute('aria-label') or ""
        
        # Extract text content
        text_content = await locator.text_content() or ""
        
        # Extract visibility status
        is_visible = await locator.is_visible()
        
        # Extract enabled status
        is_enabled = await locator.is_enabled()
        
        # Extract editable status
        is_editable = await locator.is_editable()
        
        # Extract bounding box (returns None if not visible)
        bounding_box = await locator.bounding_box()
        if bounding_box:
            # Convert to JSON-serializable dict
            bounding_box = {
                'x': bounding_box['x'],
                'y': bounding_box['y'],
                'width': bounding_box['width'],
                'height': bounding_box['height']
            }
        
        # Extract additional useful attributes
        element_id = await locator.get_attribute('id') or ""
        element_name = await locator.get_attribute('name') or ""
        element_type = await locator.get_attribute('type') or ""
        element_value = await locator.get_attribute('value') or ""
        element_placeholder = await locator.get_attribute('placeholder') or ""
        
        logger.info(f"Successfully extracted element info for: {selector}")
        
        return {
            "success": True,
            "tag_name": tag_name,
            "role": role,
            "aria_label": aria_label,
            "text_content": text_content.strip(),
            "is_visible": is_visible,
            "is_enabled": is_enabled,
            "is_editable": is_editable,
            "bounding_box": bounding_box,
            "attributes": {
                "id": element_id,
                "name": element_name,
                "type": element_type,
                "value": element_value,
                "placeholder": element_placeholder
            },
            "selector_used": selector
        }
    
    except TimeoutError:
        error_msg = f"Element not found: {selector}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "timeout",
            "error_message": error_msg,
            "selector_used": selector
        }
    
    except Exception as e:
        error_msg = f"Error getting element info for {selector}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "selector_used": selector
        }

