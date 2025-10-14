"""
Page structure analysis tool implementations for Playwright MCP server.

This module provides comprehensive page analysis functions that enable LLM agents
to understand page structure, identify interaction targets, and make intelligent
exploration decisions during test scenario discovery sessions.

All functions use Playwright's accessibility features and semantic locators,
aligned with the stable locator strategy requirements (ARIA roles, labels, test-ids).
"""

from playwright.async_api import Page, Locator, Error as PlaywrightError
from typing import Dict, List, Optional, Any, Tuple
import logging
import json
import re
from datetime import datetime
from urllib.parse import urlparse

# Initialize module-level logger
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def build_locator_recommendation(
    role: Optional[str] = None,
    name: Optional[str] = None,
    test_id: Optional[str] = None,
    text: Optional[str] = None
) -> str:
    """
    Generate recommended stable selector string following priority order.
    
    Priority:
    1. Role + Name (semantic and stable)
    2. Test ID (explicit test marker)
    3. Text content (readable but may change)
    4. CSS fallback (with warning)
    
    Args:
        role: ARIA role of the element
        name: Accessible name of the element
        test_id: data-testid attribute value
        text: Visible text content
    
    Returns:
        Recommended selector string
    """
    if role and name:
        # Escape quotes in name
        safe_name = name.replace('"', '\\"')
        return f'page.get_by_role("{role}", name="{safe_name}")'
    
    if test_id:
        return f'page.get_by_test_id("{test_id}")'
    
    if text:
        safe_text = text.replace('"', '\\"')
        return f'page.get_by_text("{safe_text}")'
    
    # Fallback with warning
    logger.warning("Unable to generate stable selector recommendation - consider adding role, name, or test-id")
    return "page.locator('...') # WARNING: Add stable selector"


def convert_accessibility_node(
    node: Dict[str, Any],
    current_depth: int,
    max_depth: Optional[int]
) -> Dict[str, Any]:
    """
    Recursively convert Playwright accessibility snapshot node to serializable dict.
    
    Prunes tree at max_depth to avoid overwhelming API responses.
    
    Args:
        node: Playwright accessibility node dictionary
        current_depth: Current depth in the tree
        max_depth: Maximum depth to traverse (None for unlimited)
    
    Returns:
        Serializable dictionary with accessibility node data
    """
    result = {
        "role": node.get("role", "unknown"),
        "name": node.get("name", ""),
        "value": node.get("value"),
        "description": node.get("description"),
        "level": node.get("level"),  # For headings
        "depth": current_depth
    }
    
    # Prune if max depth reached
    if max_depth is not None and current_depth >= max_depth:
        result["children"] = []
        result["pruned"] = True
        return result
    
    # Recursively process children
    children = node.get("children", [])
    result["children"] = [
        convert_accessibility_node(child, current_depth + 1, max_depth)
        for child in children
    ]
    result["pruned"] = False
    
    return result


async def build_nested_structure(
    elements: List[Locator],
    parent_selector: str
) -> List[Dict[str, Any]]:
    """
    Build hierarchical structure from flat element list.
    
    Detects parent-child relationships using bounding box containment.
    
    Args:
        elements: List of Playwright Locator objects
        parent_selector: CSS selector of parent container
    
    Returns:
        List of dictionaries with nested children arrays
    """
    structure = []
    
    for element in elements:
        try:
            # Get element properties
            box = await element.bounding_box()
            if not box:
                continue
            
            element_data = {
                "tag": await element.evaluate("el => el.tagName.toLowerCase()"),
                "text": (await element.text_content() or "")[:200],
                "bounding_box": box,
                "children": []
            }
            
            structure.append(element_data)
        except PlaywrightError as e:
            logger.warning(f"Error building nested structure for element: {e}")
            continue
    
    return structure


# ============================================================================
# Main Analysis Functions
# ============================================================================

async def get_accessibility_tree(
    page: Page,
    max_depth: Optional[int] = None
) -> Dict[str, Any]:
    """
    Extract accessibility tree using Playwright's accessibility.snapshot().
    
    Provides semantic understanding of page structure for LLM agents.
    
    Args:
        page: Playwright Page instance
        max_depth: Maximum tree depth to include (None for unlimited)
    
    Returns:
        Dictionary containing:
        - tree: Recursive accessibility node structure
        - node_count: Total number of nodes
        - max_depth_reached: Actual maximum depth in tree
        - snapshot_timestamp: ISO format timestamp
    """
    logger.info(f"Extracting accessibility tree (max_depth={max_depth})")
    
    try:
        # Execute Playwright accessibility snapshot
        snapshot = await page.accessibility.snapshot()
        
        if not snapshot:
            return {
                "tree": None,
                "node_count": 0,
                "max_depth_reached": 0,
                "snapshot_timestamp": datetime.utcnow().isoformat(),
                "error": "No accessibility tree available"
            }
        
        # Convert to serializable format with depth limiting
        converted_tree = convert_accessibility_node(snapshot, 0, max_depth)
        
        # Count total nodes
        def count_nodes(node: Dict[str, Any]) -> int:
            return 1 + sum(count_nodes(child) for child in node.get("children", []))
        
        # Calculate actual max depth
        def calc_max_depth(node: Dict[str, Any]) -> int:
            if not node.get("children"):
                return node.get("depth", 0)
            return max(calc_max_depth(child) for child in node["children"])
        
        node_count = count_nodes(converted_tree)
        actual_max_depth = calc_max_depth(converted_tree)
        
        logger.info(f"Accessibility tree extracted: {node_count} nodes, depth {actual_max_depth}")
        
        # Check for accessibility issues
        if node_count < 5:
            logger.warning("Very few accessibility nodes found - page may have accessibility issues")
        
        return {
            "tree": converted_tree,
            "node_count": node_count,
            "max_depth_reached": actual_max_depth,
            "snapshot_timestamp": datetime.utcnow().isoformat()
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract accessibility tree: {e}")
        return {
            "tree": None,
            "node_count": 0,
            "max_depth_reached": 0,
            "snapshot_timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


async def get_interactive_elements(
    page: Page,
    include_hidden: bool = False
) -> Dict[str, Any]:
    """
    Query for all interactive element types using semantic roles.
    
    Identifies buttons, links, inputs, and other interactive elements with
    stable selector recommendations.
    
    Args:
        page: Playwright Page instance
        include_hidden: Whether to include hidden/invisible elements
    
    Returns:
        Dictionary containing:
        - elements: List of interactive element details
        - total_elements: Total count
        - by_role: Count per role type
        - recommendations: Suggested next exploration actions
    """
    logger.info(f"Extracting interactive elements (include_hidden={include_hidden})")
    
    elements = []
    by_role = {}
    
    # Define interactive roles to query
    interactive_roles = [
        ("button", "button"),
        ("link", "link"),
        ("textbox", "textbox"),
        ("checkbox", "checkbox"),
        ("radio", "radio"),
        ("combobox", "combobox"),
        ("searchbox", "searchbox"),
        ("slider", "slider"),
        ("spinbutton", "spinbutton"),
        ("switch", "switch")
    ]
    
    try:
        for role_name, role_value in interactive_roles:
            # Query all elements with this role
            locators = await page.get_by_role(role_value).all()
            by_role[role_name] = len(locators)
            
            for locator in locators:
                try:
                    # Check visibility
                    is_visible = await locator.is_visible()
                    
                    if not include_hidden and not is_visible:
                        continue
                    
                    # Extract element properties
                    name = await locator.get_attribute("aria-label") or await locator.text_content() or ""
                    name = name.strip()[:100]  # Truncate long names
                    
                    test_id = await locator.get_attribute("data-testid")
                    is_enabled = await locator.is_enabled() if is_visible else False
                    bounding_box = await locator.bounding_box() if is_visible else None
                    
                    # Build selector recommendation
                    selector_rec = build_locator_recommendation(
                        role=role_value,
                        name=name if name else None,
                        test_id=test_id
                    )
                    
                    element_data = {
                        "role": role_name,
                        "name": name,
                        "selector_recommendation": selector_rec,
                        "is_visible": is_visible,
                        "is_enabled": is_enabled,
                        "bounding_box": bounding_box,
                        "test_id": test_id
                    }
                    
                    elements.append(element_data)
                    
                    # Warn about unlabeled elements
                    if not name and role_name in ["button", "link"]:
                        logger.warning(f"Found unlabeled {role_name} - accessibility issue")
                
                except PlaywrightError as e:
                    logger.debug(f"Error extracting {role_name} element: {e}")
                    continue
        
        # Generate exploration recommendations
        recommendations = []
        if by_role.get("button", 0) > 0:
            recommendations.append("Consider clicking primary action buttons to explore workflows")
        if by_role.get("link", 0) > 3:
            recommendations.append("Multiple navigation links available - explore different sections")
        if by_role.get("textbox", 0) > 0 or by_role.get("searchbox", 0) > 0:
            recommendations.append("Form inputs found - consider filling and submitting")
        
        logger.info(f"Found {len(elements)} interactive elements across {len(by_role)} role types")
        
        return {
            "elements": elements,
            "total_elements": len(elements),
            "by_role": by_role,
            "recommendations": recommendations
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract interactive elements: {e}")
        return {
            "elements": [],
            "total_elements": 0,
            "by_role": {},
            "recommendations": [],
            "error": str(e)
        }


async def get_page_structure(
    page: Page,
    include_hidden: bool = False
) -> Dict[str, Any]:
    """
    Extract comprehensive DOM structure with semantic grouping.
    
    Provides headings, landmarks, forms, lists, and tables for page understanding.
    
    Args:
        page: Playwright Page instance
        include_hidden: Whether to include hidden elements
    
    Returns:
        Dictionary containing:
        - headings: Page outline with heading hierarchy
        - landmarks: Major page sections (main, nav, etc.)
        - forms: Form elements with input fields
        - interactive_elements: Buttons and links
        - total_elements: Total count
    """
    logger.info("Extracting comprehensive page structure")
    
    try:
        structure = {
            "headings": [],
            "landmarks": [],
            "forms": [],
            "interactive_elements": [],
            "total_elements": 0
        }
        
        # Extract headings (h1-h6)
        heading_locators = await page.get_by_role("heading").all()
        for heading in heading_locators:
            try:
                if not include_hidden and not await heading.is_visible():
                    continue
                
                text = await heading.text_content() or ""
                level = await heading.get_attribute("aria-level") or \
                        await heading.evaluate("el => el.tagName.toLowerCase()")
                
                # Parse level from tag if needed
                if isinstance(level, str) and level.startswith("h"):
                    level = int(level[1])
                else:
                    level = int(level) if level else 1
                
                structure["headings"].append({
                    "level": level,
                    "text": text.strip()[:200],
                    "is_visible": await heading.is_visible()
                })
            except (PlaywrightError, ValueError) as e:
                logger.debug(f"Error extracting heading: {e}")
                continue
        
        # Extract landmarks
        landmark_selectors = [
            ('[role="main"], main', 'main'),
            ('[role="navigation"], nav', 'navigation'),
            ('[role="banner"], header', 'banner'),
            ('[role="contentinfo"], footer', 'contentinfo'),
            ('[role="complementary"], aside', 'complementary'),
            ('[role="search"]', 'search')
        ]
        
        for selector, role in landmark_selectors:
            landmarks = await page.locator(selector).all()
            for landmark in landmarks:
                try:
                    if not include_hidden and not await landmark.is_visible():
                        continue
                    
                    aria_label = await landmark.get_attribute("aria-label")
                    structure["landmarks"].append({
                        "role": role,
                        "label": aria_label,
                        "is_visible": await landmark.is_visible()
                    })
                except PlaywrightError as e:
                    logger.debug(f"Error extracting landmark: {e}")
                    continue
        
        # Extract forms
        form_locators = await page.locator("form").all()
        for form in form_locators:
            try:
                if not include_hidden and not await form.is_visible():
                    continue
                
                action = await form.get_attribute("action") or ""
                method = await form.get_attribute("method") or "GET"
                
                # Count input fields
                inputs = await form.locator("input, select, textarea").count()
                
                structure["forms"].append({
                    "action": action,
                    "method": method.upper(),
                    "input_count": inputs,
                    "is_visible": await form.is_visible()
                })
            except PlaywrightError as e:
                logger.debug(f"Error extracting form: {e}")
                continue
        
        # Get interactive elements summary
        interactive_summary = await get_interactive_elements(page, include_hidden)
        structure["interactive_elements"] = interactive_summary.get("by_role", {})
        
        # Calculate total
        structure["total_elements"] = (
            len(structure["headings"]) +
            len(structure["landmarks"]) +
            len(structure["forms"]) +
            sum(structure["interactive_elements"].values())
        )
        
        logger.info(f"Page structure extracted: {structure['total_elements']} elements")
        
        # Accessibility warnings
        if not structure["headings"]:
            logger.warning("No headings found - page may have accessibility issues")
        if not any(l["role"] == "main" for l in structure["landmarks"]):
            logger.warning("No main landmark found - consider adding role='main'")
        
        return structure
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract page structure: {e}")
        return {
            "headings": [],
            "landmarks": [],
            "forms": [],
            "interactive_elements": {},
            "total_elements": 0,
            "error": str(e)
        }


async def get_form_details(
    page: Page,
    form_selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze form structures with input field details and validation rules.
    
    Args:
        page: Playwright Page instance
        form_selector: Optional CSS selector for specific form (None for all forms)
    
    Returns:
        Dictionary containing:
        - forms: List of form details with inputs and buttons
        - recommendations: Form interaction suggestions
    """
    logger.info(f"Extracting form details (selector={form_selector})")
    
    try:
        forms = []
        
        # Find forms
        if form_selector:
            form_locators = await page.locator(form_selector).all()
        else:
            form_locators = await page.locator("form").all()
        
        for form in form_locators:
            try:
                form_data = {
                    "action": await form.get_attribute("action") or "",
                    "method": (await form.get_attribute("method") or "GET").upper(),
                    "inputs": [],
                    "buttons": [],
                    "validation_rules": {}
                }
                
                # Extract input fields
                input_locators = await form.locator("input, select, textarea").all()
                for input_elem in input_locators:
                    input_type = await input_elem.get_attribute("type") or "text"
                    name = await input_elem.get_attribute("name") or ""
                    
                    # Find associated label
                    input_id = await input_elem.get_attribute("id")
                    label = ""
                    if input_id:
                        label_locator = page.locator(f'label[for="{input_id}"]')
                        if await label_locator.count() > 0:
                            label = await label_locator.text_content() or ""
                    
                    if not label:
                        label = await input_elem.get_attribute("aria-label") or \
                                await input_elem.get_attribute("placeholder") or ""
                    
                    # Validation attributes
                    required = await input_elem.get_attribute("required") is not None
                    pattern = await input_elem.get_attribute("pattern")
                    min_val = await input_elem.get_attribute("min")
                    max_val = await input_elem.get_attribute("max")
                    
                    input_data = {
                        "type": input_type,
                        "name": name,
                        "label": label.strip()[:100],
                        "required": required,
                        "pattern": pattern,
                        "min": min_val,
                        "max": max_val
                    }
                    
                    form_data["inputs"].append(input_data)
                    
                    # Track validation rules
                    if required:
                        form_data["validation_rules"][name] = "required"
                    if pattern:
                        form_data["validation_rules"][name + "_pattern"] = pattern
                
                # Extract buttons
                button_locators = await form.locator("button, input[type='submit'], input[type='reset']").all()
                for button in button_locators:
                    button_type = await button.get_attribute("type") or "submit"
                    button_text = await button.text_content() or \
                                  await button.get_attribute("value") or ""
                    
                    form_data["buttons"].append({
                        "type": button_type,
                        "text": button_text.strip()
                    })
                
                forms.append(form_data)
            
            except PlaywrightError as e:
                logger.debug(f"Error extracting form details: {e}")
                continue
        
        # Generate recommendations
        recommendations = []
        for form in forms:
            required_fields = [inp["name"] for inp in form["inputs"] if inp["required"]]
            if required_fields:
                recommendations.append(f"Form requires fields: {', '.join(required_fields)}")
            
            # Suggest input values based on type
            for inp in form["inputs"]:
                if inp["type"] == "email":
                    recommendations.append(f"Use valid email format for '{inp['label'] or inp['name']}'")
                elif inp["type"] == "tel":
                    recommendations.append(f"Use valid phone format for '{inp['label'] or inp['name']}'")
                elif inp["type"] == "url":
                    recommendations.append(f"Use valid URL format for '{inp['label'] or inp['name']}'")
        
        logger.info(f"Extracted {len(forms)} form(s) with {sum(len(f['inputs']) for f in forms)} total inputs")
        
        return {
            "forms": forms,
            "recommendations": recommendations
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract form details: {e}")
        return {
            "forms": [],
            "recommendations": [],
            "error": str(e)
        }


async def get_links_summary(page: Page) -> Dict[str, Any]:
    """
    Categorize all links on the page (internal, external, anchor, downloads).
    
    Args:
        page: Playwright Page instance
    
    Returns:
        Dictionary containing:
        - total_links: Total count
        - internal_links: Same-domain links
        - external_links: Different-domain links
        - anchor_links: Hash fragment links
    """
    logger.info("Extracting links summary")
    
    try:
        current_url = page.url
        current_domain = urlparse(current_url).netloc
        
        link_locators = await page.get_by_role("link").all()
        
        internal_links = []
        external_links = []
        anchor_links = []
        download_extensions = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".tar", ".gz"}
        
        for link in link_locators:
            try:
                href = await link.get_attribute("href")
                if not href:
                    continue
                
                text = (await link.text_content() or "").strip()[:100]
                opens_in_new_tab = await link.get_attribute("target") == "_blank"
                
                # Categorize link
                if href.startswith("#"):
                    anchor_links.append({
                        "href": href,
                        "text": text,
                        "opens_in_new_tab": opens_in_new_tab
                    })
                else:
                    parsed = urlparse(href)
                    link_domain = parsed.netloc if parsed.netloc else current_domain
                    
                    # Check if download link
                    is_download = any(href.lower().endswith(ext) for ext in download_extensions)
                    
                    link_data = {
                        "href": href,
                        "text": text,
                        "opens_in_new_tab": opens_in_new_tab,
                        "is_download": is_download
                    }
                    
                    if link_domain == current_domain:
                        internal_links.append(link_data)
                    else:
                        external_links.append(link_data)
            
            except PlaywrightError as e:
                logger.debug(f"Error extracting link: {e}")
                continue
        
        logger.info(
            f"Links summary: {len(internal_links)} internal, "
            f"{len(external_links)} external, {len(anchor_links)} anchor"
        )
        
        return {
            "total_links": len(link_locators),
            "internal_links": internal_links,
            "external_links": external_links,
            "anchor_links": anchor_links
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract links summary: {e}")
        return {
            "total_links": 0,
            "internal_links": [],
            "external_links": [],
            "anchor_links": [],
            "error": str(e)
        }


async def get_navigation_structure(page: Page) -> Dict[str, Any]:
    """
    Extract navigation menu structures with hierarchical relationships.
    
    Args:
        page: Playwright Page instance
    
    Returns:
        Dictionary containing:
        - navigation_sections: List of navigation areas with menu items
    """
    logger.info("Extracting navigation structure")
    
    try:
        navigation_sections = []
        
        # Find all navigation landmarks
        nav_locators = await page.locator('[role="navigation"], nav').all()
        
        for nav in nav_locators:
            try:
                if not await nav.is_visible():
                    continue
                
                nav_label = await nav.get_attribute("aria-label") or "Unnamed navigation"
                
                # Extract links within this navigation
                nav_links = await nav.get_by_role("link").all()
                menu_items = []
                
                for link in nav_links:
                    href = await link.get_attribute("href") or ""
                    text = (await link.text_content() or "").strip()
                    aria_current = await link.get_attribute("aria-current")
                    is_active = aria_current in ["page", "true"]
                    
                    # Check if part of submenu
                    parent_menu = await link.evaluate(
                        "el => el.closest('[role=\"menu\"]') !== null"
                    )
                    
                    menu_items.append({
                        "text": text,
                        "href": href,
                        "is_active": is_active,
                        "is_submenu_item": parent_menu
                    })
                
                navigation_sections.append({
                    "label": nav_label,
                    "menu_items": menu_items,
                    "item_count": len(menu_items)
                })
            
            except PlaywrightError as e:
                logger.debug(f"Error extracting navigation section: {e}")
                continue
        
        logger.info(f"Found {len(navigation_sections)} navigation section(s)")
        
        return {
            "navigation_sections": navigation_sections
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract navigation structure: {e}")
        return {
            "navigation_sections": [],
            "error": str(e)
        }


async def get_semantic_outline(page: Page) -> Dict[str, Any]:
    """
    Extract page hierarchy using heading levels to build document outline.
    
    Args:
        page: Playwright Page instance
    
    Returns:
        Dictionary containing:
        - outline: Nested heading structure
        - page_title: HTML title
        - main_heading: h1 text
    """
    logger.info("Extracting semantic outline")
    
    try:
        # Get page title
        page_title = await page.title()
        
        # Extract all headings
        heading_locators = await page.get_by_role("heading").all()
        headings = []
        
        for heading in heading_locators:
            try:
                if not await heading.is_visible():
                    continue
                
                text = (await heading.text_content() or "").strip()
                
                # Determine level
                tag = await heading.evaluate("el => el.tagName.toLowerCase()")
                if tag.startswith("h") and len(tag) == 2:
                    level = int(tag[1])
                else:
                    aria_level = await heading.get_attribute("aria-level")
                    level = int(aria_level) if aria_level else 1
                
                headings.append({
                    "level": level,
                    "text": text
                })
            
            except (PlaywrightError, ValueError) as e:
                logger.debug(f"Error extracting heading: {e}")
                continue
        
        # Build nested outline
        def build_outline(headings_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            if not headings_list:
                return []
            
            outline = []
            stack = []
            
            for heading in headings_list:
                # Create node
                node = {
                    "level": heading["level"],
                    "text": heading["text"],
                    "children": []
                }
                
                # Find parent
                while stack and stack[-1]["level"] >= node["level"]:
                    stack.pop()
                
                if stack:
                    stack[-1]["children"].append(node)
                else:
                    outline.append(node)
                
                stack.append(node)
            
            return outline
        
        outline = build_outline(headings)
        
        # Find main heading (first h1)
        main_heading = next(
            (h["text"] for h in headings if h["level"] == 1),
            ""
        )
        
        logger.info(f"Semantic outline extracted with {len(headings)} headings")
        
        if not main_heading:
            logger.warning("No h1 heading found - page should have exactly one h1")
        
        return {
            "outline": outline,
            "page_title": page_title,
            "main_heading": main_heading
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract semantic outline: {e}")
        return {
            "outline": [],
            "page_title": "",
            "main_heading": "",
            "error": str(e)
        }


async def extract_table_data(
    page: Page,
    table_selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract structured data from HTML tables.
    
    Args:
        page: Playwright Page instance
        table_selector: Optional CSS selector for specific table
    
    Returns:
        Dictionary containing:
        - tables: List of table data with headers and rows
    """
    logger.info(f"Extracting table data (selector={table_selector})")
    
    try:
        tables = []
        
        # Find tables
        if table_selector:
            table_locators = await page.locator(table_selector).all()
        else:
            table_locators = await page.get_by_role("table").all()
        
        for table in table_locators:
            try:
                if not await table.is_visible():
                    continue
                
                # Extract headers
                header_cells = await table.locator("thead th, thead td").all()
                headers = []
                for cell in header_cells:
                    text = (await cell.text_content() or "").strip()
                    headers.append(text)
                
                # If no thead, try first row
                if not headers:
                    first_row_cells = await table.locator("tr:first-child th, tr:first-child td").all()
                    for cell in first_row_cells:
                        text = (await cell.text_content() or "").strip()
                        headers.append(text)
                
                # Extract data rows
                row_locators = await table.locator("tbody tr").all()
                if not row_locators:
                    row_locators = await table.locator("tr").all()
                    # Skip first row if it was headers
                    if headers:
                        row_locators = row_locators[1:]
                
                rows = []
                for row in row_locators[:50]:  # Limit to 50 rows
                    cell_locators = await row.locator("td, th").all()
                    row_data = []
                    for cell in cell_locators:
                        text = (await cell.text_content() or "").strip()
                        row_data.append(text)
                    rows.append(row_data)
                
                # Analyze column types
                column_types = []
                if rows:
                    for col_idx in range(len(headers) if headers else len(rows[0])):
                        # Sample first few values
                        sample_values = [row[col_idx] for row in rows[:10] if col_idx < len(row)]
                        
                        # Simple type detection
                        if all(v.replace(".", "").replace(",", "").replace("-", "").isdigit() for v in sample_values if v):
                            column_types.append("numeric")
                        elif all(re.match(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}', v) for v in sample_values if v):
                            column_types.append("date")
                        else:
                            column_types.append("text")
                
                tables.append({
                    "headers": headers,
                    "rows": rows,
                    "row_count": len(rows),
                    "column_types": column_types
                })
            
            except PlaywrightError as e:
                logger.debug(f"Error extracting table: {e}")
                continue
        
        logger.info(f"Extracted {len(tables)} table(s)")
        
        return {
            "tables": tables
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract table data: {e}")
        return {
            "tables": [],
            "error": str(e)
        }


async def find_elements_by_description(
    page: Page,
    description: str
) -> Dict[str, Any]:
    """
    Search for elements matching natural language description.
    
    Uses multiple Playwright locator strategies to find matches.
    
    Args:
        page: Playwright Page instance
        description: Natural language element description
    
    Returns:
        Dictionary containing:
        - matches: List of matching elements
        - suggested_selectors: Recommended selector strings
        - match_count: Total matches found
    """
    logger.info(f"Finding elements by description: '{description}'")
    
    try:
        matches = []
        suggested_selectors = []
        
        # Strategy 1: Text content
        text_matches = await page.get_by_text(description).all()
        for match in text_matches:
            if await match.is_visible():
                tag = await match.evaluate("el => el.tagName.toLowerCase()")
                text = (await match.text_content() or "").strip()[:100]
                
                matches.append({
                    "strategy": "text",
                    "tag": tag,
                    "text": text
                })
                suggested_selectors.append(build_locator_recommendation(text=description))
        
        # Strategy 2: Label
        label_matches = await page.get_by_label(description).all()
        for match in label_matches:
            if await match.is_visible():
                tag = await match.evaluate("el => el.tagName.toLowerCase()")
                label = await match.get_attribute("aria-label") or description
                
                matches.append({
                    "strategy": "label",
                    "tag": tag,
                    "label": label
                })
                suggested_selectors.append(f'page.get_by_label("{description}")')
        
        # Strategy 3: Placeholder
        placeholder_matches = await page.get_by_placeholder(description).all()
        for match in placeholder_matches:
            if await match.is_visible():
                tag = await match.evaluate("el => el.tagName.toLowerCase()")
                placeholder = await match.get_attribute("placeholder") or description
                
                matches.append({
                    "strategy": "placeholder",
                    "tag": tag,
                    "placeholder": placeholder
                })
                suggested_selectors.append(f'page.get_by_placeholder("{description}")')
        
        # Strategy 4: Role + Name (try common roles)
        for role in ["button", "link", "heading"]:
            try:
                role_matches = await page.get_by_role(role, name=description).all()
                for match in role_matches:
                    if await match.is_visible():
                        matches.append({
                            "strategy": "role+name",
                            "role": role,
                            "name": description
                        })
                        suggested_selectors.append(
                            build_locator_recommendation(role=role, name=description)
                        )
            except PlaywrightError:
                continue
        
        # Deduplicate suggested selectors
        suggested_selectors = list(dict.fromkeys(suggested_selectors))
        
        logger.info(f"Found {len(matches)} element(s) matching description")
        
        return {
            "matches": matches,
            "suggested_selectors": suggested_selectors[:5],  # Limit to top 5
            "match_count": len(matches)
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to find elements by description: {e}")
        return {
            "matches": [],
            "suggested_selectors": [],
            "match_count": 0,
            "error": str(e)
        }


async def get_page_metadata(page: Page) -> Dict[str, Any]:
    """
    Extract page-level metadata (title, URL, meta tags, language, viewport).
    
    Args:
        page: Playwright Page instance
    
    Returns:
        Dictionary containing comprehensive page metadata
    """
    logger.info("Extracting page metadata")
    
    try:
        # Basic page info
        title = await page.title()
        url = page.url
        
        # Extract meta tags
        meta_tags = {}
        meta_locators = await page.locator("meta").all()
        
        for meta in meta_locators:
            name = await meta.get_attribute("name") or await meta.get_attribute("property")
            content = await meta.get_attribute("content")
            
            if name and content:
                meta_tags[name] = content
        
        # Language and charset
        lang = await page.evaluate("() => document.documentElement.lang")
        charset = await page.evaluate("() => document.characterSet")
        
        # Viewport
        viewport = page.viewport_size
        
        logger.info(f"Page metadata extracted for: {title}")
        
        return {
            "title": title,
            "url": url,
            "meta_tags": meta_tags,
            "lang": lang or "en",
            "charset": charset or "UTF-8",
            "viewport": viewport
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to extract page metadata: {e}")
        return {
            "title": "",
            "url": page.url,
            "meta_tags": {},
            "lang": "",
            "charset": "",
            "viewport": None,
            "error": str(e)
        }


async def analyze_page_complexity(page: Page) -> Dict[str, Any]:
    """
    Calculate page complexity metrics for exploration planning.
    
    Provides heuristic estimates of DOM size, interactive elements, and
    estimated exploration time.
    
    Args:
        page: Playwright Page instance
    
    Returns:
        Dictionary containing:
        - complexity_score: Float (0-10)
        - element_counts: Breakdown by element type
        - exploration_estimate_minutes: Estimated time for thorough exploration
    """
    logger.info("Analyzing page complexity")
    
    try:
        # Count total DOM nodes
        total_nodes = await page.evaluate("() => document.getElementsByTagName('*').length")
        
        # Count interactive elements
        interactive_data = await get_interactive_elements(page, include_hidden=False)
        interactive_count = interactive_data.get("total_elements", 0)
        
        # Count forms
        form_count = await page.locator("form").count()
        
        # Count links
        link_count = await page.get_by_role("link").count()
        
        # Calculate DOM depth
        max_depth = await page.evaluate("""
            () => {
                let maxDepth = 0;
                function getDepth(element) {
                    let depth = 0;
                    let current = element;
                    while (current.parentElement) {
                        depth++;
                        current = current.parentElement;
                    }
                    return depth;
                }
                const allElements = document.getElementsByTagName('*');
                for (let el of allElements) {
                    maxDepth = Math.max(maxDepth, getDepth(el));
                }
                return maxDepth;
            }
        """)
        
        # Calculate complexity score (0-10)
        # Factors: DOM size, interactive elements, depth, forms
        dom_score = min(total_nodes / 1000, 3)  # 0-3 points
        interactive_score = min(interactive_count / 20, 3)  # 0-3 points
        depth_score = min(max_depth / 20, 2)  # 0-2 points
        form_score = min(form_count * 0.5, 2)  # 0-2 points
        
        complexity_score = round(dom_score + interactive_score + depth_score + form_score, 2)
        
        # Estimate exploration time (very rough heuristic)
        # Base: 2 minutes
        # +0.5 minutes per 10 interactive elements
        # +1 minute per form
        # +0.1 minutes per 50 DOM nodes
        exploration_estimate = (
            2 +
            (interactive_count / 10) * 0.5 +
            form_count +
            (total_nodes / 50) * 0.1
        )
        exploration_estimate_minutes = round(exploration_estimate)
        
        element_counts = {
            "total_dom_nodes": total_nodes,
            "interactive_elements": interactive_count,
            "forms": form_count,
            "links": link_count,
            "max_dom_depth": max_depth
        }
        
        logger.info(
            f"Page complexity: score={complexity_score}/10, "
            f"estimated exploration time={exploration_estimate_minutes} minutes"
        )
        
        # Provide warnings
        warnings = []
        if total_nodes > 2000:
            warnings.append("Very large DOM - page may be slow to interact with")
        if max_depth > 30:
            warnings.append("Deep DOM nesting - consider simplified selectors")
        if interactive_count < 5:
            warnings.append("Few interactive elements - page may be static content")
        
        return {
            "complexity_score": complexity_score,
            "element_counts": element_counts,
            "exploration_estimate_minutes": exploration_estimate_minutes,
            "warnings": warnings
        }
    
    except PlaywrightError as e:
        logger.error(f"Failed to analyze page complexity: {e}")
        return {
            "complexity_score": 0,
            "element_counts": {},
            "exploration_estimate_minutes": 0,
            "warnings": ["Error analyzing page complexity"],
            "error": str(e)
        }

