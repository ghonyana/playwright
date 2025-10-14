"""
Pydantic data models for Playwright MCP server tool request/response schemas.

This module defines comprehensive type-safe models for all Playwright MCP tools including:
- Navigation: URL navigation and page loading
- Interaction: Element clicking and text input
- Capture: Screenshots and trace collection
- Analysis: Accessibility tree and page structure inspection
- Session Management: Browser context lifecycle
- Gherkin Generation: LLM-assisted test scenario creation

All models include:
- Field validation with descriptions for OpenAPI documentation
- Type annotations for static type checking
- JSON schema generation for FastAPI automatic API docs
- Consistent serialization configuration (ISO datetime, exclude None)
- Comprehensive docstrings with usage examples
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# =============================================================================
# ENUMERATIONS
# =============================================================================


class BrowserType(str, Enum):
    """
    Supported Playwright browser types for session creation.
    
    Values:
        chromium: Google Chrome/Chromium browser (default, fastest)
        firefox: Mozilla Firefox browser
        webkit: Apple Safari/WebKit browser
    
    Example:
        >>> session_req = CreateSessionRequest(browser_type=BrowserType.chromium)
        >>> assert session_req.browser_type == "chromium"
    """
    
    chromium = "chromium"
    firefox = "firefox"
    webkit = "webkit"


# =============================================================================
# NAVIGATION TOOL MODELS
# =============================================================================


class NavigateRequest(BaseModel):
    """
    Request model for browser navigation to a specific URL.
    
    Attributes:
        session_id: Unique identifier for the browser session
        url: Target URL to navigate to (validated as valid HTTP/HTTPS URL)
        wait_until: Navigation wait condition (networkidle, load, domcontentloaded)
    
    Example:
        >>> req = NavigateRequest(
        ...     session_id="session-123",
        ...     url="https://example.com/login",
        ...     wait_until="networkidle"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "url": "https://example.com/dashboard",
                "wait_until": "networkidle"
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique session identifier for the browser context",
        min_length=1
    )
    url: HttpUrl = Field(
        ...,
        description="Target URL to navigate to (must be valid HTTP/HTTPS URL)"
    )
    wait_until: str = Field(
        default="networkidle",
        description="Wait condition: 'networkidle', 'load', or 'domcontentloaded'"
    )


class NavigateResponse(BaseModel):
    """
    Response model for navigation operation result.
    
    Attributes:
        success: Whether navigation completed successfully
        url: The requested URL
        title: Page title after navigation
        current_url: Final URL after redirects
    
    Example:
        >>> resp = NavigateResponse(
        ...     success=True,
        ...     url="https://example.com/login",
        ...     title="Login - Example App",
        ...     current_url="https://example.com/login"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "url": "https://example.com/dashboard",
                "title": "Dashboard - Example App",
                "current_url": "https://example.com/dashboard"
            }
        }
    )
    
    success: bool = Field(
        ...,
        description="Indicates if navigation completed successfully"
    )
    url: str = Field(
        ...,
        description="The requested navigation URL"
    )
    title: str = Field(
        ...,
        description="Page title after successful navigation"
    )
    current_url: str = Field(
        ...,
        description="Final URL after any redirects or hash changes"
    )


# =============================================================================
# INTERACTION TOOL MODELS
# =============================================================================


class ClickRequest(BaseModel):
    """
    Request model for clicking an element on the page.
    
    Attributes:
        session_id: Unique identifier for the browser session
        selector: Element selector (prefer ARIA roles, test-ids, labels)
        timeout: Maximum wait time in milliseconds for element
    
    Example:
        >>> req = ClickRequest(
        ...     session_id="session-123",
        ...     selector="button[aria-label='Submit']",
        ...     timeout=30000
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "selector": "button[role='button']:has-text('Login')",
                "timeout": 30000
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique session identifier for the browser context",
        min_length=1
    )
    selector: str = Field(
        ...,
        description="Element selector (prefer role='button', aria-label, data-testid)",
        min_length=1
    )
    timeout: int = Field(
        default=30000,
        description="Maximum wait time in milliseconds for element to be clickable",
        ge=0
    )


class ClickResponse(BaseModel):
    """
    Response model for click operation result.
    
    Attributes:
        success: Whether click operation completed successfully
        element_text: Text content of the clicked element (if available)
        element_role: ARIA role of the clicked element (if available)
    
    Example:
        >>> resp = ClickResponse(
        ...     success=True,
        ...     element_text="Submit",
        ...     element_role="button"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "element_text": "Login",
                "element_role": "button"
            }
        }
    )
    
    success: bool = Field(
        ...,
        description="Indicates if click operation completed successfully"
    )
    element_text: Optional[str] = Field(
        default=None,
        description="Text content of the clicked element"
    )
    element_role: Optional[str] = Field(
        default=None,
        description="ARIA role attribute of the clicked element"
    )


class TypeRequest(BaseModel):
    """
    Request model for typing text into an input element.
    
    Attributes:
        session_id: Unique identifier for the browser session
        selector: Input element selector
        text: Text to type into the element
        clear_first: Whether to clear existing text before typing
    
    Example:
        >>> req = TypeRequest(
        ...     session_id="session-123",
        ...     selector="input[aria-label='Username']",
        ...     text="testuser@example.com",
        ...     clear_first=True
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "selector": "input[name='email']",
                "text": "user@example.com",
                "clear_first": True
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique session identifier for the browser context",
        min_length=1
    )
    selector: str = Field(
        ...,
        description="Input element selector (prefer aria-label, name, data-testid)",
        min_length=1
    )
    text: str = Field(
        ...,
        description="Text content to type into the input element"
    )
    clear_first: bool = Field(
        default=True,
        description="Clear existing text before typing (default: True)"
    )


class TypeResponse(BaseModel):
    """
    Response model for text typing operation result.
    
    Attributes:
        success: Whether typing operation completed successfully
        element_label: Accessible label of the input element (if available)
    
    Example:
        >>> resp = TypeResponse(
        ...     success=True,
        ...     element_label="Username"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "element_label": "Email Address"
            }
        }
    )
    
    success: bool = Field(
        ...,
        description="Indicates if typing operation completed successfully"
    )
    element_label: Optional[str] = Field(
        default=None,
        description="Accessible label or aria-label of the input element"
    )


# =============================================================================
# CAPTURE TOOL MODELS
# =============================================================================


class ScreenshotRequest(BaseModel):
    """
    Request model for capturing page screenshots.
    
    Attributes:
        session_id: Unique identifier for the browser session
        full_page: Whether to capture the entire scrollable page
        element_selector: Optional selector to screenshot specific element only
    
    Example:
        >>> req = ScreenshotRequest(
        ...     session_id="session-123",
        ...     full_page=True,
        ...     element_selector=None
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "full_page": True,
                "element_selector": None
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique session identifier for the browser context",
        min_length=1
    )
    full_page: bool = Field(
        default=True,
        description="Capture entire scrollable page (True) or viewport only (False)"
    )
    element_selector: Optional[str] = Field(
        default=None,
        description="Optional selector to capture specific element only"
    )


class ScreenshotResponse(BaseModel):
    """
    Response model for screenshot capture result.
    
    Attributes:
        screenshot_base64: Base64-encoded PNG screenshot data
        width: Screenshot width in pixels
        height: Screenshot height in pixels
        format: Image format (always 'png')
    
    Example:
        >>> resp = ScreenshotResponse(
        ...     screenshot_base64="iVBORw0KGgoAAAANSUhEUgA...",
        ...     width=1920,
        ...     height=1080,
        ...     format="png"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "screenshot_base64": "iVBORw0KGgoAAAANSUhEUgAAAAUA...",
                "width": 1920,
                "height": 1080,
                "format": "png"
            }
        }
    )
    
    screenshot_base64: str = Field(
        ...,
        description="Base64-encoded PNG screenshot data"
    )
    width: int = Field(
        ...,
        description="Screenshot width in pixels",
        gt=0
    )
    height: int = Field(
        ...,
        description="Screenshot height in pixels",
        gt=0
    )
    format: str = Field(
        default="png",
        description="Image format (always 'png')"
    )


class CaptureTraceRequest(BaseModel):
    """
    Request model for capturing Playwright trace files.
    
    Attributes:
        session_id: Unique identifier for the browser session
        trace_name: Name for the trace file (without extension)
    
    Example:
        >>> req = CaptureTraceRequest(
        ...     session_id="session-123",
        ...     trace_name="login_flow_exploration"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "trace_name": "user_journey_exploration"
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique session identifier for the browser context",
        min_length=1
    )
    trace_name: str = Field(
        ...,
        description="Name for the trace file (extension added automatically)",
        min_length=1
    )


class CaptureTraceResponse(BaseModel):
    """
    Response model for trace capture result.
    
    Attributes:
        success: Whether trace capture completed successfully
        trace_path: Filesystem path to the saved trace file
    
    Example:
        >>> resp = CaptureTraceResponse(
        ...     success=True,
        ...     trace_path="/traces/login_flow_exploration.zip"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "trace_path": "/tmp/traces/user_journey_exploration.zip"
            }
        }
    )
    
    success: bool = Field(
        ...,
        description="Indicates if trace capture completed successfully"
    )
    trace_path: str = Field(
        ...,
        description="Filesystem path to the saved Playwright trace file"
    )


# =============================================================================
# ANALYSIS TOOL MODELS
# =============================================================================


class AccessibilityNode(BaseModel):
    """
    Recursive model representing a node in the accessibility tree.
    
    Attributes:
        role: ARIA role of the element (e.g., 'button', 'textbox', 'heading')
        name: Accessible name of the element (computed from aria-label, etc.)
        value: Current value for input elements
        children: Nested accessibility nodes (recursive)
    
    Example:
        >>> node = AccessibilityNode(
        ...     role="button",
        ...     name="Submit Form",
        ...     value=None,
        ...     children=[]
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "button",
                "name": "Login",
                "value": None,
                "children": []
            }
        }
    )
    
    role: str = Field(
        ...,
        description="ARIA role of the accessibility element"
    )
    name: Optional[str] = Field(
        default=None,
        description="Computed accessible name (from aria-label, text content, etc.)"
    )
    value: Optional[str] = Field(
        default=None,
        description="Current value for input/select elements"
    )
    children: List['AccessibilityNode'] = Field(
        default_factory=list,
        description="Nested child accessibility nodes in the tree"
    )


# Enable forward reference for recursive model
AccessibilityNode.model_rebuild()


class GetAccessibilityTreeRequest(BaseModel):
    """
    Request model for retrieving page accessibility tree.
    
    Attributes:
        session_id: Unique identifier for the browser session
        max_depth: Optional maximum tree depth to retrieve (for performance)
    
    Example:
        >>> req = GetAccessibilityTreeRequest(
        ...     session_id="session-123",
        ...     max_depth=5
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "max_depth": 10
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique session identifier for the browser context",
        min_length=1
    )
    max_depth: Optional[int] = Field(
        default=None,
        description="Maximum tree depth to traverse (None for unlimited)",
        ge=1
    )


class GetAccessibilityTreeResponse(BaseModel):
    """
    Response model for accessibility tree retrieval.
    
    Attributes:
        tree: Root accessibility node with nested children
        node_count: Total number of nodes in the tree
    
    Example:
        >>> resp = GetAccessibilityTreeResponse(
        ...     tree=AccessibilityNode(role="WebArea", name="Login Page", children=[...]),
        ...     node_count=47
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tree": {
                    "role": "WebArea",
                    "name": "Dashboard",
                    "value": None,
                    "children": []
                },
                "node_count": 42
            }
        }
    )
    
    tree: AccessibilityNode = Field(
        ...,
        description="Root node of the accessibility tree with nested children"
    )
    node_count: int = Field(
        ...,
        description="Total count of accessibility nodes in the tree",
        ge=0
    )


class PageElement(BaseModel):
    """
    Model representing a DOM element in page structure.
    
    Attributes:
        tag: HTML tag name (e.g., 'div', 'button', 'input')
        id: Element ID attribute
        classes: List of CSS class names
        text_content: Visible text content of the element
        attributes: Dictionary of element attributes (name: value)
    
    Example:
        >>> elem = PageElement(
        ...     tag="button",
        ...     id="submit-btn",
        ...     classes=["btn", "btn-primary"],
        ...     text_content="Submit",
        ...     attributes={"type": "submit", "aria-label": "Submit Form"}
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tag": "button",
                "id": "login-button",
                "classes": ["btn", "btn-primary"],
                "text_content": "Login",
                "attributes": {"type": "button", "aria-label": "Login"}
            }
        }
    )
    
    tag: str = Field(
        ...,
        description="HTML tag name (lowercase)"
    )
    id: Optional[str] = Field(
        default=None,
        description="Element ID attribute value"
    )
    classes: List[str] = Field(
        default_factory=list,
        description="List of CSS class names"
    )
    text_content: Optional[str] = Field(
        default=None,
        description="Visible text content (trimmed)"
    )
    attributes: Dict[str, str] = Field(
        default_factory=dict,
        description="Element attributes as key-value pairs"
    )


class GetPageStructureRequest(BaseModel):
    """
    Request model for retrieving page DOM structure.
    
    Attributes:
        session_id: Unique identifier for the browser session
        include_hidden: Whether to include hidden elements in results
    
    Example:
        >>> req = GetPageStructureRequest(
        ...     session_id="session-123",
        ...     include_hidden=False
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "include_hidden": False
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique session identifier for the browser context",
        min_length=1
    )
    include_hidden: bool = Field(
        default=False,
        description="Include elements with display:none or visibility:hidden"
    )


class GetPageStructureResponse(BaseModel):
    """
    Response model for page structure retrieval.
    
    Attributes:
        elements: List of page elements with metadata
        total_elements: Total count of elements returned
    
    Example:
        >>> resp = GetPageStructureResponse(
        ...     elements=[PageElement(tag="div", ...), ...],
        ...     total_elements=127
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "elements": [
                    {
                        "tag": "button",
                        "id": "submit",
                        "classes": ["btn"],
                        "text_content": "Submit",
                        "attributes": {"type": "submit"}
                    }
                ],
                "total_elements": 127
            }
        }
    )
    
    elements: List[PageElement] = Field(
        ...,
        description="List of page elements with metadata"
    )
    total_elements: int = Field(
        ...,
        description="Total number of elements in the response",
        ge=0
    )


# =============================================================================
# SESSION MANAGEMENT MODELS
# =============================================================================


class CreateSessionRequest(BaseModel):
    """
    Request model for creating a new browser session.
    
    Attributes:
        browser_type: Browser engine to use (chromium, firefox, webkit)
        viewport_width: Browser viewport width in pixels
        viewport_height: Browser viewport height in pixels
        headless: Run browser in headless mode (no visible window)
    
    Example:
        >>> req = CreateSessionRequest(
        ...     browser_type=BrowserType.chromium,
        ...     viewport_width=1920,
        ...     viewport_height=1080,
        ...     headless=False
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "browser_type": "chromium",
                "viewport_width": 1920,
                "viewport_height": 1080,
                "headless": False
            }
        }
    )
    
    browser_type: BrowserType = Field(
        default=BrowserType.chromium,
        description="Browser engine: chromium (default), firefox, or webkit"
    )
    viewport_width: int = Field(
        default=1920,
        description="Browser viewport width in pixels",
        ge=320,
        le=7680
    )
    viewport_height: int = Field(
        default=1080,
        description="Browser viewport height in pixels",
        ge=240,
        le=4320
    )
    headless: bool = Field(
        default=False,
        description="Run browser in headless mode (no UI) for development exploration"
    )


class CreateSessionResponse(BaseModel):
    """
    Response model for browser session creation.
    
    Attributes:
        session_id: Unique identifier for the created session
        browser_type: The browser type that was launched
        created_at: ISO 8601 timestamp of session creation
    
    Example:
        >>> resp = CreateSessionResponse(
        ...     session_id="session-abc123",
        ...     browser_type="chromium",
        ...     created_at="2025-01-15T10:30:00Z"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "browser_type": "chromium",
                "created_at": "2025-01-15T10:30:00Z"
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique identifier for the browser session"
    )
    browser_type: str = Field(
        ...,
        description="Browser engine that was launched"
    )
    created_at: str = Field(
        ...,
        description="Session creation timestamp (ISO 8601 format)"
    )


class CloseSessionRequest(BaseModel):
    """
    Request model for closing a browser session.
    
    Attributes:
        session_id: Unique identifier of the session to close
    
    Example:
        >>> req = CloseSessionRequest(session_id="session-123")
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123"
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique identifier of the browser session to close",
        min_length=1
    )


class CloseSessionResponse(BaseModel):
    """
    Response model for browser session closure.
    
    Attributes:
        success: Whether session was closed successfully
        session_id: The session ID that was closed
    
    Example:
        >>> resp = CloseSessionResponse(
        ...     success=True,
        ...     session_id="session-123"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "session_id": "session-abc123"
            }
        }
    )
    
    success: bool = Field(
        ...,
        description="Indicates if session closure completed successfully"
    )
    session_id: str = Field(
        ...,
        description="The session identifier that was closed"
    )


# =============================================================================
# GHERKIN GENERATION MODELS
# =============================================================================


class GenerateGherkinRequest(BaseModel):
    """
    Request model for generating Gherkin scenarios from exploration session.
    
    Attributes:
        session_id: Unique identifier of the exploration session
        feature_name: Name of the feature being tested
        exploration_goal: High-level objective of the exploration
        template_style: Optional Gherkin style template (e.g., 'business', 'technical')
    
    Example:
        >>> req = GenerateGherkinRequest(
        ...     session_id="session-123",
        ...     feature_name="User Authentication",
        ...     exploration_goal="Test login flow with valid credentials",
        ...     template_style="business"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "session-abc123",
                "feature_name": "User Authentication",
                "exploration_goal": "Test login with valid credentials",
                "template_style": "business"
            }
        }
    )
    
    session_id: str = Field(
        ...,
        description="Unique identifier of the exploration session",
        min_length=1
    )
    feature_name: str = Field(
        ...,
        description="Name of the feature for the Gherkin feature file",
        min_length=1
    )
    exploration_goal: str = Field(
        ...,
        description="High-level objective or user story for the exploration",
        min_length=1
    )
    template_style: Optional[str] = Field(
        default=None,
        description="Gherkin template style: 'business' (high-level) or 'technical' (detailed)"
    )


class GenerateGherkinResponse(BaseModel):
    """
    Response model for Gherkin scenario generation.
    
    Attributes:
        feature_content: Complete Gherkin feature file content
        scenarios_count: Number of scenarios generated
        metadata: Additional metadata (model name, token usage, assumptions)
    
    Example:
        >>> resp = GenerateGherkinResponse(
        ...     feature_content="Feature: User Auth\\n  Scenario: ...",
        ...     scenarios_count=3,
        ...     metadata={"model": "gpt-4", "tokens": 450}
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feature_content": "Feature: User Authentication\\n  Scenario: Login with valid credentials\\n    Given...",
                "scenarios_count": 2,
                "metadata": {
                    "model": "gpt-4",
                    "tokens_used": 387,
                    "assumptions": ["User exists in database"]
                }
            }
        }
    )
    
    feature_content: str = Field(
        ...,
        description="Complete Gherkin feature file content with scenarios"
    )
    scenarios_count: int = Field(
        ...,
        description="Number of scenarios included in the feature",
        ge=0
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata including model name, token usage, and assumptions"
    )


# =============================================================================
# ERROR MODELS
# =============================================================================


class MCPError(BaseModel):
    """
    Base error model for MCP tool operation failures.
    
    Attributes:
        error_code: Machine-readable error code (e.g., 'SESSION_NOT_FOUND')
        message: Human-readable error message
        details: Optional additional error context and debugging information
    
    Example:
        >>> error = MCPError(
        ...     error_code="INVALID_SELECTOR",
        ...     message="Selector syntax is invalid",
        ...     details={"selector": "//invalid[xpath"}
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "TIMEOUT",
                "message": "Operation timed out after 30000ms",
                "details": {"selector": "button[aria-label='Submit']", "timeout": 30000}
            }
        }
    )
    
    error_code: str = Field(
        ...,
        description="Machine-readable error code (uppercase snake_case)"
    )
    message: str = Field(
        ...,
        description="Human-readable error description"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error context and debugging information"
    )


class SessionNotFoundError(MCPError):
    """
    Error raised when a session ID does not exist or has expired.
    
    Inherits all attributes from MCPError.
    Always uses error_code='SESSION_NOT_FOUND'.
    
    Example:
        >>> error = SessionNotFoundError(
        ...     error_code="SESSION_NOT_FOUND",
        ...     message="Session 'abc123' not found or expired",
        ...     details={"session_id": "abc123"}
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "SESSION_NOT_FOUND",
                "message": "Session 'session-abc123' does not exist or has expired",
                "details": {"session_id": "session-abc123"}
            }
        }
    )


class BrowserActionError(MCPError):
    """
    Error raised when a browser action fails (navigation, click, type, etc.).
    
    Inherits all attributes from MCPError.
    Uses error codes like 'NAVIGATION_FAILED', 'CLICK_FAILED', 'TYPE_FAILED'.
    
    Example:
        >>> error = BrowserActionError(
        ...     error_code="CLICK_FAILED",
        ...     message="Element is not clickable",
        ...     details={"selector": "button.disabled", "reason": "Element is disabled"}
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "NAVIGATION_FAILED",
                "message": "Navigation to URL failed due to timeout",
                "details": {"url": "https://example.com", "timeout": 30000}
            }
        }
    )


class SelectorNotFoundError(MCPError):
    """
    Error raised when an element selector does not match any elements.
    
    Inherits all attributes from MCPError.
    Always uses error_code='SELECTOR_NOT_FOUND'.
    
    Example:
        >>> error = SelectorNotFoundError(
        ...     error_code="SELECTOR_NOT_FOUND",
        ...     message="No element found matching selector",
        ...     details={"selector": "button[id='nonexistent']", "timeout": 30000}
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "SELECTOR_NOT_FOUND",
                "message": "No element found for selector 'button.missing'",
                "details": {"selector": "button.missing", "wait_timeout": 30000}
            }
        }
    )
