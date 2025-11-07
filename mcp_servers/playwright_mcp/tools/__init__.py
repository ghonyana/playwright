"""
Playwright MCP Tools Package

This package provides browser automation tool implementations for the Playwright MCP server,
enabling LLM agents to control browsers during exploratory testing sessions.

Tool Categories:
- Navigation: URL navigation, page reload, back/forward
- Interaction: Click, type, checkbox, select, hover
- Capture: Screenshots, traces, video paths
- Analysis: Accessibility tree, page structure, interactive elements

Usage:
    from mcp_servers.playwright_mcp.tools import navigate_to_url, click_element
    
    # In FastAPI endpoint
    result = await navigate_to_url(page, 'https://example.com')

Note: These are low-level utility functions operating on Playwright Page/BrowserContext objects.
Session management and action logging are handled by main.py endpoint wrappers.
"""

import logging
from typing import Dict, List, Optional, Any

# Export commonly used types for convenience
from playwright.async_api import Page, BrowserContext, Locator

# Navigation tools
from mcp_servers.playwright_mcp.tools.navigation import (
    navigate_to_url,
    reload_page,
    navigate_back,
    navigate_forward,
    wait_for_navigation,
    validate_url
)

# Interaction tools
from mcp_servers.playwright_mcp.tools.interaction import (
    click_element,
    type_text,
    press_key,
    toggle_checkbox,
    select_option,
    hover_element,
    focus_element,
    get_element_info,
    build_locator
)

# Capture tools
from mcp_servers.playwright_mcp.tools.capture import (
    capture_screenshot,
    save_screenshot_to_file,
    start_trace,
    stop_trace,
    capture_trace_for_session,
    capture_pdf,
    get_video_path,
    get_screenshot_metadata
)

# Analysis tools
from mcp_servers.playwright_mcp.tools.analysis import (
    get_accessibility_tree,
    get_interactive_elements,
    get_page_structure,
    get_form_details,
    get_links_summary,
    get_navigation_structure,
    get_semantic_outline,
    extract_table_data,
    find_elements_by_description,
    get_page_metadata,
    analyze_page_complexity
)


# Define __all__ for explicit exports
__all__ = [
    # Type exports
    'Page',
    'BrowserContext',
    'Locator',
    
    # Navigation
    'navigate_to_url',
    'reload_page',
    'navigate_back',
    'navigate_forward',
    'wait_for_navigation',
    'validate_url',
    
    # Interaction
    'click_element',
    'type_text',
    'press_key',
    'toggle_checkbox',
    'select_option',
    'hover_element',
    'focus_element',
    'get_element_info',
    'build_locator',
    
    # Capture
    'capture_screenshot',
    'save_screenshot_to_file',
    'start_trace',
    'stop_trace',
    'capture_trace_for_session',
    'capture_pdf',
    'get_video_path',
    'get_screenshot_metadata',
    
    # Analysis
    'get_accessibility_tree',
    'get_interactive_elements',
    'get_page_structure',
    'get_form_details',
    'get_links_summary',
    'get_navigation_structure',
    'get_semantic_outline',
    'extract_table_data',
    'find_elements_by_description',
    'get_page_metadata',
    'analyze_page_complexity',
]


# Package version
__version__ = '1.0.0'


# Logger configuration
logger = logging.getLogger(__name__)
logger.info('Playwright MCP tools package initialized')


# Conditional imports for development introspection
if __name__ == '__main__':
    from . import navigation
    from . import interaction
    from . import capture
    from . import analysis
    
    print('Playwright MCP Tools Package')
    print(f'Version: {__version__}')
    print(f'Available tool modules: {[navigation, interaction, capture, analysis]}')
    print(f'Total exported functions: {len(__all__)}')
    print(f'\nNavigation tools: {[n for n in __all__ if n in ["navigate_to_url", "reload_page", "navigate_back", "navigate_forward", "wait_for_navigation", "validate_url"]]}')
    print(f'Interaction tools: {[n for n in __all__ if n in ["click_element", "type_text", "press_key", "toggle_checkbox", "select_option", "hover_element", "focus_element", "get_element_info", "build_locator"]]}')
    print(f'Capture tools: {[n for n in __all__ if n in ["capture_screenshot", "save_screenshot_to_file", "start_trace", "stop_trace", "capture_trace_for_session", "capture_pdf", "get_video_path", "get_screenshot_metadata"]]}')
    print(f'Analysis tools: {[n for n in __all__ if n in ["get_accessibility_tree", "get_interactive_elements", "get_page_structure", "get_form_details", "get_links_summary", "get_navigation_structure", "get_semantic_outline", "extract_table_data", "find_elements_by_description", "get_page_metadata", "analyze_page_complexity"]]}')
