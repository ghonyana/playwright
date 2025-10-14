"""
Playwright MCP Server - FastAPI Application Entry Point

This module implements the Model Context Protocol (MCP) server for LLM-driven browser
exploration and Gherkin test scenario generation. It provides JSON-RPC endpoints for
browser automation tools that enable LLM agents to control Playwright browsers, explore
applications, and generate business-readable BDD scenarios.

Key Features:
- Browser automation tools: navigate, click, type, screenshot, accessibility analysis
- Session management: isolated browser contexts for concurrent LLM agents
- Real-time WebSocket support for streaming LLM-browser communication
- Gherkin generation: LLM-assisted conversion of exploration logs to test scenarios
- Health monitoring and OpenAPI documentation via Swagger UI

Per Technical Specification Section 0.1.2:
- Development-only server (CI uses only FastAPI MCP for deterministic data)
- WebSocket support for real-time LLM streaming interactions
- Browser actions logged for Gherkin scenario generation
- No authentication by default (enable via PLAYWRIGHT_MCP_REQUIRE_AUTH)

Integration Points:
- SessionManager: Browser context lifecycle and exploration logging
- GherkinGenerator: LLM-assisted scenario generation from logs
- Config: Environment-based settings from config.py
- Models: Pydantic request/response validation

Usage:
    # Start server (development)
    python -m mcp_servers.playwright_mcp.main
    
    # Or with uvicorn directly
    uvicorn mcp_servers.playwright_mcp.main:app --host 0.0.0.0 --port 8001 --reload
    
    # Access API documentation
    http://localhost:8001/docs
"""

import base64
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeoutError
import uvicorn

# Internal imports from depends_on_files
from mcp_servers.playwright_mcp.config import settings
from mcp_servers.playwright_mcp.models import (
    # Navigation models
    NavigateRequest,
    NavigateResponse,
    # Interaction models
    ClickRequest,
    ClickResponse,
    TypeRequest,
    TypeResponse,
    # Capture models
    ScreenshotRequest,
    ScreenshotResponse,
    # Analysis models
    GetAccessibilityTreeRequest,
    GetAccessibilityTreeResponse,
    GetPageStructureRequest,
    GetPageStructureResponse,
    AccessibilityNode,
    PageElement,
    # Session management models
    CreateSessionRequest,
    CreateSessionResponse,
    CloseSessionRequest,
    CloseSessionResponse,
    # Gherkin generation models
    GenerateGherkinRequest,
    GenerateGherkinResponse,
    # Error models
    MCPError,
    SessionNotFoundError,
    BrowserActionError,
    SelectorNotFoundError,
)
from mcp_servers.playwright_mcp.session.manager import SessionManager
from mcp_servers.playwright_mcp.gherkin.generator import GherkinGenerator

# Configure module-level logger
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# FASTAPI APPLICATION INITIALIZATION
# =============================================================================

app = FastAPI(
    title='Playwright MCP Server',
    description=(
        'Model Context Protocol server for LLM-driven browser exploration and Gherkin '
        'generation. Provides JSON-RPC tools for browser automation (navigate, click, type, '
        'screenshot, accessibility analysis) and real-time WebSocket support for streaming '
        'LLM agents. Converts exploration sessions into business-readable BDD scenarios.'
    ),
    version='1.0.0',
    docs_url='/docs',  # Swagger UI at /docs
    redoc_url='/redoc',  # ReDoc alternative documentation
)

# =============================================================================
# CORS MIDDLEWARE CONFIGURATION
# =============================================================================

# Enable CORS for all origins (development-only server)
# Allows LLM clients and browser-based interfaces to access MCP tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # Accept requests from any origin
    allow_credentials=True,
    allow_methods=['*'],  # Allow all HTTP methods
    allow_headers=['*'],  # Allow all headers
)

logger.info("CORS middleware configured for development (allow_origins=['*'])")

# =============================================================================
# GLOBAL STATE AND DEPENDENCY INJECTION
# =============================================================================

# Global SessionManager instance (initialized in startup event)
session_manager: Optional[SessionManager] = None

# Global GherkinGenerator instance (initialized in startup event)
gherkin_generator: Optional[GherkinGenerator] = None


def get_session_manager() -> SessionManager:
    """
    FastAPI dependency for injecting SessionManager into endpoint handlers.
    
    Returns:
        Initialized SessionManager instance
        
    Raises:
        HTTPException: If SessionManager not initialized (startup event failed)
        
    Example:
        @app.post("/tools/navigate")
        async def navigate(
            request: NavigateRequest,
            manager: SessionManager = Depends(get_session_manager)
        ):
            page = await manager.get_page(request.session_id)
            # ...
    """
    if session_manager is None:
        logger.error("SessionManager not initialized - startup event may have failed")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: SessionManager not initialized. Check server logs."
        )
    return session_manager


def get_gherkin_generator() -> GherkinGenerator:
    """
    FastAPI dependency for injecting GherkinGenerator into endpoint handlers.
    
    Returns:
        Initialized GherkinGenerator instance
        
    Raises:
        HTTPException: If GherkinGenerator not initialized
        
    Example:
        @app.post("/tools/generate_gherkin")
        async def generate(
            request: GenerateGherkinRequest,
            generator: GherkinGenerator = Depends(get_gherkin_generator)
        ):
            feature = await generator.generate_from_exploration(...)
            # ...
    """
    if gherkin_generator is None:
        logger.error("GherkinGenerator not initialized")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: GherkinGenerator not initialized. Check server logs."
        )
    return gherkin_generator


# =============================================================================
# LIFECYCLE EVENT HANDLERS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event handler for resource initialization.
    
    Initializes:
    - SessionManager with Playwright browser instance
    - GherkinGenerator with optional LLM client
    
    Browser configuration loaded from settings:
    - default_browser: chromium, firefox, or webkit
    - headless: False for LLM visibility (per Agent Action Plan)
    - viewport: width and height for browser contexts
    
    Raises:
        RuntimeError: If browser initialization fails (terminates server)
    """
    global session_manager, gherkin_generator
    
    logger.info("=" * 80)
    logger.info("Starting Playwright MCP Server")
    logger.info("=" * 80)
    logger.info(f"Server configuration:")
    logger.info(f"  Host: {settings.host}")
    logger.info(f"  Port: {settings.port}")
    logger.info(f"  Browser: {settings.default_browser}")
    logger.info(f"  Headless: {settings.headless}")
    logger.info(f"  Viewport: {settings.viewport_width}x{settings.viewport_height}")
    logger.info(f"  Max sessions: {settings.max_sessions}")
    logger.info(f"  LLM provider: {settings.llm_provider or 'None (template-based generation)'}")
    logger.info("=" * 80)
    
    try:
        # Initialize SessionManager with Playwright browser
        logger.info("Initializing SessionManager...")
        session_manager = SessionManager()
        await session_manager.initialize(
            browser_type=settings.default_browser,
            headless=settings.headless,
            viewport_width=settings.viewport_width,
            viewport_height=settings.viewport_height
        )
        logger.info(f"✓ SessionManager initialized with {settings.default_browser} browser")
        
        # Initialize GherkinGenerator (with optional LLM client)
        logger.info("Initializing GherkinGenerator...")
        gherkin_generator = GherkinGenerator()
        logger.info("✓ GherkinGenerator initialized")
        
        logger.info("=" * 80)
        logger.info("Playwright MCP Server startup complete")
        logger.info(f"API documentation available at: http://{settings.host}:{settings.port}/docs")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"FATAL: Startup failed: {e}")
        logger.error("=" * 80)
        raise RuntimeError(f"Failed to start Playwright MCP Server: {e}") from e


@app.on_event("shutdown")
async def shutdown_event():
    """
    FastAPI shutdown event handler for resource cleanup.
    
    Performs graceful shutdown:
    - Closes all active browser sessions
    - Shuts down browser instance
    - Stops Playwright context
    
    Continues cleanup even if individual operations fail to ensure
    resources are released properly.
    """
    global session_manager
    
    logger.info("=" * 80)
    logger.info("Shutting down Playwright MCP Server")
    logger.info("=" * 80)
    
    if session_manager:
        try:
            logger.info("Cleaning up SessionManager resources...")
            await session_manager.cleanup()
            logger.info("✓ SessionManager cleanup complete")
        except Exception as e:
            logger.error(f"Error during SessionManager cleanup: {e}", exc_info=True)
    else:
        logger.warning("SessionManager was not initialized - skipping cleanup")
    
    logger.info("=" * 80)
    logger.info("Playwright MCP Server shutdown complete")
    logger.info("=" * 80)


# =============================================================================
# ROOT AND HEALTH ENDPOINTS
# =============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint redirects to API documentation.
    
    Returns:
        RedirectResponse to /docs (Swagger UI)
    """
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check(manager: SessionManager = Depends(get_session_manager)):
    """
    Health check endpoint for service monitoring.
    
    Returns service status, active session count, and Playwright version.
    Used by container orchestration, load balancers, and monitoring tools.
    
    Args:
        manager: Injected SessionManager instance
        
    Returns:
        Dictionary with status, active_sessions, browser_type, timestamp
        
    Example Response:
        {
            "status": "healthy",
            "active_sessions": 3,
            "browser_type": "chromium",
            "max_sessions": 10,
            "timestamp": "2025-01-15T10:30:00Z"
        }
    """
    active_sessions = manager.list_sessions()
    
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "browser_type": settings.default_browser,
        "max_sessions": settings.max_sessions,
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# SESSION MANAGEMENT ENDPOINTS
# =============================================================================

@app.post("/sessions/create", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    Create a new isolated browser session for LLM agent exploration.
    
    Each session receives a dedicated BrowserContext with independent cookies,
    storage, and cache. Sessions are tracked with unique IDs and can be managed
    independently for concurrent explorations.
    
    Args:
        request: Session creation parameters (browser_type, viewport, headless)
        manager: Injected SessionManager instance
        
    Returns:
        CreateSessionResponse with session_id, browser_type, created_at
        
    Raises:
        HTTPException 500: If session creation fails
        HTTPException 503: If max_sessions limit reached
        
    Example:
        POST /sessions/create
        {
            "browser_type": "chromium",
            "viewport_width": 1920,
            "viewport_height": 1080,
            "headless": false
        }
        
        Response:
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "browser_type": "chromium",
            "created_at": "2025-01-15T10:30:00Z"
        }
    """
    try:
        # Check session limit
        active_sessions = manager.list_sessions()
        if len(active_sessions) >= settings.max_sessions:
            logger.warning(
                f"Session creation rejected: max_sessions limit ({settings.max_sessions}) reached"
            )
            raise HTTPException(
                status_code=503,
                detail=f"Maximum sessions limit reached ({settings.max_sessions}). "
                       f"Please close an existing session first."
            )
        
        # Create new session with requested viewport settings
        session_id = await manager.create_session(
            viewport_width=request.viewport_width,
            viewport_height=request.viewport_height
        )
        
        logger.info(
            f"Session created: {session_id} "
            f"(browser: {request.browser_type}, viewport: {request.viewport_width}x{request.viewport_height})"
        )
        
        return CreateSessionResponse(
            session_id=session_id,
            browser_type=request.browser_type.value,
            created_at=datetime.utcnow().isoformat()
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Session creation failed: {str(e)}"
        )


@app.post("/sessions/{session_id}/close", response_model=CloseSessionResponse)
async def close_session(
    session_id: str,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    Close a browser session and release all associated resources.
    
    Closes the browser context, clears exploration logs, and removes the
    session from tracking. Should be called when LLM agent completes exploration
    or when cleaning up idle sessions.
    
    Args:
        session_id: Unique session identifier to close
        manager: Injected SessionManager instance
        
    Returns:
        CloseSessionResponse with success status and session_id
        
    Raises:
        HTTPException 404: If session_id not found
        HTTPException 500: If session closure fails
        
    Example:
        POST /sessions/550e8400-e29b-41d4-a716-446655440000/close
        
        Response:
        {
            "success": true,
            "session_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    """
    try:
        # Attempt to close session
        await manager.close_session(session_id)
        
        logger.info(f"Session closed: {session_id}")
        
        return CloseSessionResponse(
            success=True,
            session_id=session_id
        )
        
    except ValueError as e:
        # Session not found
        logger.warning(f"Close session failed - session not found: {session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {session_id}"
        )
    except Exception as e:
        logger.error(f"Failed to close session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Session closure failed: {str(e)}"
        )


@app.get("/sessions")
async def list_sessions(manager: SessionManager = Depends(get_session_manager)):
    """
    List all active browser sessions with metadata.
    
    Returns session information including creation timestamp and action count
    for monitoring and debugging concurrent LLM agent explorations.
    
    Args:
        manager: Injected SessionManager instance
        
    Returns:
        Dictionary with sessions array containing session metadata
        
    Example Response:
        {
            "sessions": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "actions_logged": 15,
                    "created_at": "2025-01-15T10:30:00Z",
                    "viewport": {"width": 1920, "height": 1080}
                }
            ],
            "total_sessions": 1
        }
    """
    sessions = manager.list_sessions()
    
    logger.debug(f"Listed {len(sessions)} active sessions")
    
    return {
        "sessions": sessions,
        "total_sessions": len(sessions)
    }


# =============================================================================
# BROWSER AUTOMATION TOOL ENDPOINTS
# =============================================================================

@app.post("/tools/navigate", response_model=NavigateResponse)
async def navigate_tool(
    request: NavigateRequest,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    Navigate browser to a specific URL.
    
    Navigates the session's page to the requested URL and waits for the
    specified load condition. Logs the navigation action for Gherkin generation.
    
    Args:
        request: Navigation parameters (session_id, url, wait_until)
        manager: Injected SessionManager instance
        
    Returns:
        NavigateResponse with success status, url, page title, current_url
        
    Raises:
        HTTPException 404: If session_id not found
        HTTPException 500: If navigation fails (timeout, network error, etc.)
        
    Example:
        POST /tools/navigate
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "url": "https://example.com/login",
            "wait_until": "networkidle"
        }
        
        Response:
        {
            "success": true,
            "url": "https://example.com/login",
            "title": "Login - Example App",
            "current_url": "https://example.com/login"
        }
    """
    try:
        # Get page for session
        page = await manager.get_page(request.session_id)
        
        # Navigate to URL with wait condition
        url_str = str(request.url)
        await page.goto(url_str, wait_until=request.wait_until, timeout=30000)
        
        # Extract page metadata
        title = await page.title()
        current_url = page.url
        
        # Log action for Gherkin generation
        await manager.log_action(
            session_id=request.session_id,
            action='navigate',
            details={
                'url': url_str,
                'title': title,
                'wait_until': request.wait_until
            }
        )
        
        logger.info(f"Navigation successful: {request.session_id} -> {url_str}")
        
        return NavigateResponse(
            success=True,
            url=url_str,
            title=title,
            current_url=current_url
        )
        
    except ValueError as e:
        # Session not found
        logger.error(f"Navigate failed - session not found: {request.session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}"
        )
    except PlaywrightTimeoutError as e:
        logger.error(f"Navigation timeout: {request.session_id} -> {request.url}")
        raise HTTPException(
            status_code=500,
            detail=f"Navigation timeout after 30000ms: {str(e)}"
        )
    except Exception as e:
        logger.error(
            f"Navigation failed: {request.session_id} -> {request.url}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Navigation failed: {str(e)}"
        )


@app.post("/tools/click", response_model=ClickResponse)
async def click_tool(
    request: ClickRequest,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    Click an element on the page.
    
    Locates an element using the provided selector and performs a click action.
    Logs the click with element metadata for Gherkin generation. Prefer ARIA
    roles, aria-label, and data-testid selectors over brittle CSS/XPath.
    
    Args:
        request: Click parameters (session_id, selector, timeout)
        manager: Injected SessionManager instance
        
    Returns:
        ClickResponse with success status, element_text, element_role
        
    Raises:
        HTTPException 404: If session_id not found or element not found
        HTTPException 500: If click operation fails
        
    Example:
        POST /tools/click
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "selector": "button[aria-label='Submit']",
            "timeout": 30000
        }
        
        Response:
        {
            "success": true,
            "element_text": "Submit",
            "element_role": "button"
        }
    """
    try:
        # Get page for session
        page = await manager.get_page(request.session_id)
        
        # Locate and click element
        locator = page.locator(request.selector)
        await locator.click(timeout=request.timeout)
        
        # Extract element metadata
        element_text = await locator.text_content() if await locator.count() > 0 else None
        element_role = await locator.get_attribute('role') if await locator.count() > 0 else None
        
        # Log action for Gherkin generation
        await manager.log_action(
            session_id=request.session_id,
            action='click',
            details={
                'selector': request.selector,
                'element_text': element_text,
                'element_role': element_role
            }
        )
        
        logger.info(
            f"Click successful: {request.session_id} -> {request.selector} "
            f"(text: {element_text})"
        )
        
        return ClickResponse(
            success=True,
            element_text=element_text,
            element_role=element_role
        )
        
    except ValueError as e:
        # Session not found
        logger.error(f"Click failed - session not found: {request.session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}"
        )
    except PlaywrightTimeoutError as e:
        logger.error(
            f"Click timeout: {request.session_id} -> {request.selector} "
            f"(timeout: {request.timeout}ms)"
        )
        raise HTTPException(
            status_code=404,
            detail=f"Element not found or not clickable: {request.selector} "
                   f"(timeout: {request.timeout}ms)"
        )
    except Exception as e:
        logger.error(
            f"Click failed: {request.session_id} -> {request.selector}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Click operation failed: {str(e)}"
        )


@app.post("/tools/type", response_model=TypeResponse)
async def type_tool(
    request: TypeRequest,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    Type text into an input element.
    
    Locates an input element and types the specified text. Optionally clears
    existing content first. Logs the typing action (with password masking) for
    Gherkin generation.
    
    Args:
        request: Type parameters (session_id, selector, text, clear_first)
        manager: Injected SessionManager instance
        
    Returns:
        TypeResponse with success status and element_label
        
    Raises:
        HTTPException 404: If session_id not found or element not found
        HTTPException 500: If typing operation fails
        
    Example:
        POST /tools/type
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "selector": "input[name='email']",
            "text": "user@example.com",
            "clear_first": true
        }
        
        Response:
        {
            "success": true,
            "element_label": "Email Address"
        }
    """
    try:
        # Get page for session
        page = await manager.get_page(request.session_id)
        
        # Locate input element
        locator = page.locator(request.selector)
        
        # Clear existing content if requested
        if request.clear_first:
            await locator.clear()
        
        # Type text into element
        await locator.fill(request.text)
        
        # Extract element label (aria-label or associated label)
        element_label = None
        if await locator.count() > 0:
            element_label = await locator.get_attribute('aria-label')
            if not element_label:
                element_label = await locator.get_attribute('placeholder')
        
        # Mask sensitive data in logs (password fields)
        logged_text = request.text
        if 'password' in request.selector.lower() or (element_label and 'password' in element_label.lower()):
            logged_text = '***'
        
        # Log action for Gherkin generation
        await manager.log_action(
            session_id=request.session_id,
            action='type',
            details={
                'selector': request.selector,
                'text': logged_text,
                'element_label': element_label,
                'clear_first': request.clear_first
            }
        )
        
        logger.info(
            f"Type successful: {request.session_id} -> {request.selector} "
            f"(label: {element_label})"
        )
        
        return TypeResponse(
            success=True,
            element_label=element_label
        )
        
    except ValueError as e:
        # Session not found
        logger.error(f"Type failed - session not found: {request.session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}"
        )
    except PlaywrightTimeoutError as e:
        logger.error(f"Type timeout: {request.session_id} -> {request.selector}")
        raise HTTPException(
            status_code=404,
            detail=f"Input element not found: {request.selector}"
        )
    except Exception as e:
        logger.error(
            f"Type failed: {request.session_id} -> {request.selector}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Typing operation failed: {str(e)}"
        )


@app.post("/tools/screenshot", response_model=ScreenshotResponse)
async def screenshot_tool(
    request: ScreenshotRequest,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    Capture a screenshot of the current page or specific element.
    
    Takes a screenshot in PNG format and returns base64-encoded data.
    Supports full-page capture or element-specific screenshots. Logs the
    screenshot action for Gherkin generation tracking.
    
    Args:
        request: Screenshot parameters (session_id, full_page, element_selector)
        manager: Injected SessionManager instance
        
    Returns:
        ScreenshotResponse with base64 screenshot data, width, height, format
        
    Raises:
        HTTPException 404: If session_id not found or element not found
        HTTPException 500: If screenshot capture fails
        
    Example:
        POST /tools/screenshot
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "full_page": true,
            "element_selector": null
        }
        
        Response:
        {
            "screenshot_base64": "iVBORw0KGgoAAAANSUhEUgA...",
            "width": 1920,
            "height": 2400,
            "format": "png"
        }
    """
    try:
        # Get page for session
        page = await manager.get_page(request.session_id)
        
        # Capture screenshot (full page or element)
        screenshot_bytes: bytes
        if request.element_selector:
            # Screenshot specific element
            locator = page.locator(request.element_selector)
            screenshot_bytes = await locator.screenshot()
        else:
            # Screenshot entire page
            screenshot_bytes = await page.screenshot(full_page=request.full_page)
        
        # Encode to base64
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        # Get viewport dimensions (approximate for width/height)
        viewport = page.viewport_size
        width = viewport['width'] if viewport else settings.viewport_width
        height = viewport['height'] if viewport else settings.viewport_height
        
        # Log action for Gherkin generation
        await manager.log_action(
            session_id=request.session_id,
            action='screenshot',
            details={
                'full_page': request.full_page,
                'element_selector': request.element_selector,
                'width': width,
                'height': height
            }
        )
        
        logger.info(
            f"Screenshot captured: {request.session_id} "
            f"(full_page: {request.full_page}, element: {request.element_selector})"
        )
        
        return ScreenshotResponse(
            screenshot_base64=screenshot_base64,
            width=width,
            height=height,
            format='png'
        )
        
    except ValueError as e:
        # Session not found
        logger.error(f"Screenshot failed - session not found: {request.session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}"
        )
    except PlaywrightTimeoutError as e:
        if request.element_selector:
            logger.error(
                f"Screenshot timeout - element not found: {request.element_selector}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Element not found: {request.element_selector}"
            )
        raise
    except Exception as e:
        logger.error(
            f"Screenshot failed: {request.session_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Screenshot capture failed: {str(e)}"
        )


# =============================================================================
# PAGE ANALYSIS TOOL ENDPOINTS
# =============================================================================

@app.post("/tools/get_accessibility_tree", response_model=GetAccessibilityTreeResponse)
async def get_accessibility_tree_tool(
    request: GetAccessibilityTreeRequest,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    Retrieve the accessibility tree for the current page.
    
    Extracts the page's accessibility tree showing ARIA roles, accessible names,
    and values. Useful for LLM agents to understand page structure and identify
    semantic elements for interaction. Logs action for Gherkin generation.
    
    Args:
        request: Accessibility tree parameters (session_id, max_depth)
        manager: Injected SessionManager instance
        
    Returns:
        GetAccessibilityTreeResponse with nested AccessibilityNode tree
        
    Raises:
        HTTPException 404: If session_id not found
        HTTPException 500: If accessibility tree extraction fails
        
    Example:
        POST /tools/get_accessibility_tree
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "max_depth": 10
        }
        
        Response:
        {
            "tree": {
                "role": "WebArea",
                "name": "Login Page",
                "value": null,
                "children": [
                    {
                        "role": "button",
                        "name": "Login",
                        "value": null,
                        "children": []
                    }
                ]
            },
            "node_count": 42
        }
    """
    try:
        # Get page for session
        page = await manager.get_page(request.session_id)
        
        # Get accessibility snapshot from Playwright
        snapshot = await page.accessibility.snapshot()
        
        # Convert snapshot to AccessibilityNode structure
        def build_accessibility_node(node_data: Optional[Dict[str, Any]]) -> Optional[AccessibilityNode]:
            """Recursively build AccessibilityNode from Playwright snapshot."""
            if not node_data:
                return None
            
            children = []
            for child_data in node_data.get('children', []):
                child_node = build_accessibility_node(child_data)
                if child_node:
                    children.append(child_node)
            
            return AccessibilityNode(
                role=node_data.get('role', 'unknown'),
                name=node_data.get('name'),
                value=node_data.get('value'),
                children=children
            )
        
        # Build tree from snapshot
        tree = build_accessibility_node(snapshot) if snapshot else AccessibilityNode(
            role='WebArea',
            name='Empty page',
            value=None,
            children=[]
        )
        
        # Count total nodes in tree
        def count_nodes(node: AccessibilityNode) -> int:
            """Recursively count nodes in accessibility tree."""
            return 1 + sum(count_nodes(child) for child in node.children)
        
        node_count = count_nodes(tree)
        
        # Log action for Gherkin generation
        await manager.log_action(
            session_id=request.session_id,
            action='get_accessibility_tree',
            details={
                'node_count': node_count,
                'max_depth': request.max_depth
            }
        )
        
        logger.info(
            f"Accessibility tree extracted: {request.session_id} "
            f"({node_count} nodes)"
        )
        
        return GetAccessibilityTreeResponse(
            tree=tree,
            node_count=node_count
        )
        
    except ValueError as e:
        # Session not found
        logger.error(
            f"Get accessibility tree failed - session not found: {request.session_id}"
        )
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}"
        )
    except Exception as e:
        logger.error(
            f"Get accessibility tree failed: {request.session_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Accessibility tree extraction failed: {str(e)}"
        )


@app.post("/tools/get_page_structure", response_model=GetPageStructureResponse)
async def get_page_structure_tool(
    request: GetPageStructureRequest,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    Retrieve the DOM structure of the current page.
    
    Extracts page elements with tag names, IDs, classes, text content, and
    attributes. Useful for LLM agents to understand page layout and identify
    elements for interaction. Logs action for Gherkin generation.
    
    Args:
        request: Page structure parameters (session_id, include_hidden)
        manager: Injected SessionManager instance
        
    Returns:
        GetPageStructureResponse with list of PageElement instances
        
    Raises:
        HTTPException 404: If session_id not found
        HTTPException 500: If page structure extraction fails
        
    Example:
        POST /tools/get_page_structure
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "include_hidden": false
        }
        
        Response:
        {
            "elements": [
                {
                    "tag": "button",
                    "id": "submit-btn",
                    "classes": ["btn", "btn-primary"],
                    "text_content": "Submit",
                    "attributes": {"type": "submit", "aria-label": "Submit Form"}
                }
            ],
            "total_elements": 127
        }
    """
    try:
        # Get page for session
        page = await manager.get_page(request.session_id)
        
        # JavaScript to extract page structure
        js_extract_structure = """
        () => {
            const includeHidden = %s;
            const elements = [];
            const allElements = document.querySelectorAll('*');
            
            for (const el of allElements) {
                // Skip hidden elements if requested
                if (!includeHidden) {
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') {
                        continue;
                    }
                }
                
                // Extract element metadata
                const element = {
                    tag: el.tagName.toLowerCase(),
                    id: el.id || null,
                    classes: Array.from(el.classList),
                    text_content: el.textContent ? el.textContent.trim().substring(0, 100) : null,
                    attributes: {}
                };
                
                // Extract key attributes
                for (const attr of el.attributes) {
                    if (['aria-label', 'aria-role', 'role', 'name', 'type', 'placeholder', 'data-testid'].includes(attr.name)) {
                        element.attributes[attr.name] = attr.value;
                    }
                }
                
                elements.push(element);
            }
            
            return elements;
        }
        """ % ('true' if request.include_hidden else 'false')
        
        # Execute JavaScript to extract structure
        elements_data = await page.evaluate(js_extract_structure)
        
        # Convert to PageElement models
        elements = [
            PageElement(
                tag=elem['tag'],
                id=elem.get('id'),
                classes=elem.get('classes', []),
                text_content=elem.get('text_content'),
                attributes=elem.get('attributes', {})
            )
            for elem in elements_data
        ]
        
        # Log action for Gherkin generation
        await manager.log_action(
            session_id=request.session_id,
            action='get_page_structure',
            details={
                'total_elements': len(elements),
                'include_hidden': request.include_hidden
            }
        )
        
        logger.info(
            f"Page structure extracted: {request.session_id} "
            f"({len(elements)} elements)"
        )
        
        return GetPageStructureResponse(
            elements=elements,
            total_elements=len(elements)
        )
        
    except ValueError as e:
        # Session not found
        logger.error(
            f"Get page structure failed - session not found: {request.session_id}"
        )
        raise HTTPException(
            status_code=404,
            detail=f"Session not found: {request.session_id}"
        )
    except Exception as e:
        logger.error(
            f"Get page structure failed: {request.session_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Page structure extraction failed: {str(e)}"
        )


# =============================================================================
# GHERKIN GENERATION ENDPOINT
# =============================================================================

@app.post("/tools/generate_gherkin", response_model=GenerateGherkinResponse)
async def generate_gherkin_tool(
    request: GenerateGherkinRequest,
    manager: SessionManager = Depends(get_session_manager),
    generator: GherkinGenerator = Depends(get_gherkin_generator)
):
    """
    Generate Gherkin scenarios from exploration session log.
    
    Converts browser exploration actions into business-readable Gherkin scenarios
    using LLM assistance (Ollama/OpenAI) or template-based fallback. Generated
    scenarios include metadata for human review workflow.
    
    Per Technical Specification Section 0.7.2:
    - Generates high-level Given/When/Then steps (no implementation details)
    - Uses business language stakeholders understand
    - No CSS selectors, XPath expressions, or DOM coordinates
    - Includes Feature descriptions with business value statements
    
    Args:
        request: Gherkin generation parameters (session_id, feature_name, etc.)
        manager: Injected SessionManager instance
        generator: Injected GherkinGenerator instance
        
    Returns:
        GenerateGherkinResponse with feature_content, scenarios_count, metadata
        
    Raises:
        HTTPException 404: If session_id not found
        HTTPException 422: If exploration log is empty
        HTTPException 500: If generation fails
        
    Example:
        POST /tools/generate_gherkin
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "feature_name": "User Authentication",
            "exploration_goal": "Test login with valid credentials",
            "template_style": "business"
        }
        
        Response:
        {
            "feature_content": "Feature: User Authentication\\n  Scenario: ...",
            "scenarios_count": 2,
            "metadata": {
                "model": "gpt-4",
                "tokens_used": 387,
                "assumptions": ["User exists in database"]
            }
        }
    """
    try:
        # Retrieve exploration log for session
        exploration_log = await manager.get_exploration_log(request.session_id)
        
        if not exploration_log:
            logger.warning(
                f"Generate Gherkin failed - empty exploration log: {request.session_id}"
            )
            raise HTTPException(
                status_code=422,
                detail=f"Exploration log is empty for session {request.session_id}. "
                       f"Perform browser actions before generating Gherkin."
            )
        
        # Generate Gherkin feature from exploration
        feature_content = await generator.generate_from_exploration(
            feature_name=request.feature_name,
            exploration_goal=request.exploration_goal,
            exploration_log=exploration_log,
            session_id=request.session_id,
            additional_context=None  # Could pass accessibility tree in future
        )
        
        # Count scenarios in generated content
        scenarios_count = generator.count_scenarios(feature_content)
        
        # Validate Gherkin syntax
        is_valid = generator.validate_gherkin_syntax(feature_content)
        if not is_valid:
            logger.warning(
                f"Generated Gherkin has validation warnings: {request.session_id}"
            )
        
        # Build metadata for response
        metadata = {
            "model": generator.model_name or "template-based",
            "exploration_actions": len(exploration_log),
            "assumptions": generator.assumptions,
            "open_questions": generator.open_questions,
            "validation_passed": is_valid
        }
        
        logger.info(
            f"Gherkin generated: {request.session_id} "
            f"(feature: {request.feature_name}, scenarios: {scenarios_count})"
        )
        
        return GenerateGherkinResponse(
            feature_content=feature_content,
            scenarios_count=scenarios_count,
            metadata=metadata
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        # Session not found or exploration log error
        if "not found" in str(e).lower():
            logger.error(
                f"Generate Gherkin failed - session not found: {request.session_id}"
            )
            raise HTTPException(
                status_code=404,
                detail=f"Session not found: {request.session_id}"
            )
        else:
            logger.error(
                f"Generate Gherkin failed - validation error: {e}",
                exc_info=True
            )
            raise HTTPException(
                status_code=422,
                detail=str(e)
            )
    except Exception as e:
        logger.error(
            f"Generate Gherkin failed: {request.session_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Gherkin generation failed: {str(e)}"
        )


# =============================================================================
# WEBSOCKET ENDPOINT FOR REAL-TIME LLM EXPLORATION
# =============================================================================

@app.websocket("/explore")
async def websocket_explore(
    websocket: WebSocket,
    manager: SessionManager = Depends(get_session_manager)
):
    """
    WebSocket endpoint for real-time LLM-browser communication.
    
    Enables streaming interaction between LLM agents and browsers. LLM sends
    JSON commands (navigate, click, type, screenshot) and receives immediate
    responses with page updates, accessibility information, and screenshots.
    
    Per Technical Specification Section 0.1.2:
    - Development-only feature for LLM exploration
    - WebSocket enables streaming responses for large payloads
    - Session auto-created on connection, auto-closed on disconnect
    
    WebSocket Message Protocol:
        Client sends:
        {
            "action": "navigate" | "click" | "type" | "screenshot" | "get_page_structure",
            "params": { ... }  // Action-specific parameters
        }
        
        Server responds:
        {
            "success": true,
            "result": { ... },  // Action result
            "error": null
        }
        
        Or on error:
        {
            "success": false,
            "result": null,
            "error": "Error message"
        }
    
    Supported Actions:
        - navigate: {"url": "https://...", "wait_until": "networkidle"}
        - click: {"selector": "button[aria-label='Submit']"}
        - type: {"selector": "input[name='email']", "text": "user@example.com"}
        - screenshot: {"full_page": true}
        - get_page_structure: {"include_hidden": false}
        - get_accessibility_tree: {"max_depth": 10}
    
    Args:
        websocket: FastAPI WebSocket connection
        manager: Injected SessionManager instance
    """
    session_id: Optional[str] = None
    
    try:
        # Accept WebSocket connection
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Create session for this WebSocket connection
        session_id = await manager.create_session(
            viewport_width=settings.viewport_width,
            viewport_height=settings.viewport_height
        )
        
        # Send session_id to client
        await websocket.send_json({
            "type": "session_created",
            "session_id": session_id,
            "message": f"Browser session created: {session_id}"
        })
        
        logger.info(f"WebSocket session created: {session_id}")
        
        # Message loop - receive commands from LLM agent
        while True:
            try:
                # Receive command from client
                message = await websocket.receive_json()
                
                action = message.get("action")
                params = message.get("params", {})
                
                logger.debug(f"WebSocket received: {action} (session: {session_id})")
                
                # Get page for session
                page = await manager.get_page(session_id)
                
                # Execute action and send response
                if action == "navigate":
                    url = params.get("url")
                    wait_until = params.get("wait_until", "networkidle")
                    
                    await page.goto(url, wait_until=wait_until, timeout=30000)
                    title = await page.title()
                    
                    await manager.log_action(
                        session_id=session_id,
                        action='navigate',
                        details={'url': url, 'title': title}
                    )
                    
                    await websocket.send_json({
                        "success": True,
                        "result": {
                            "url": url,
                            "title": title,
                            "current_url": page.url
                        },
                        "error": None
                    })
                
                elif action == "click":
                    selector = params.get("selector")
                    
                    locator = page.locator(selector)
                    await locator.click()
                    
                    element_text = await locator.text_content() if await locator.count() > 0 else None
                    
                    await manager.log_action(
                        session_id=session_id,
                        action='click',
                        details={'selector': selector, 'element_text': element_text}
                    )
                    
                    await websocket.send_json({
                        "success": True,
                        "result": {
                            "element_text": element_text
                        },
                        "error": None
                    })
                
                elif action == "type":
                    selector = params.get("selector")
                    text = params.get("text")
                    clear_first = params.get("clear_first", True)
                    
                    locator = page.locator(selector)
                    
                    if clear_first:
                        await locator.clear()
                    
                    await locator.fill(text)
                    
                    await manager.log_action(
                        session_id=session_id,
                        action='type',
                        details={'selector': selector, 'text': '***' if 'password' in selector.lower() else text}
                    )
                    
                    await websocket.send_json({
                        "success": True,
                        "result": {
                            "typed": True
                        },
                        "error": None
                    })
                
                elif action == "screenshot":
                    full_page = params.get("full_page", True)
                    
                    screenshot_bytes = await page.screenshot(full_page=full_page)
                    screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                    
                    await manager.log_action(
                        session_id=session_id,
                        action='screenshot',
                        details={'full_page': full_page}
                    )
                    
                    await websocket.send_json({
                        "success": True,
                        "result": {
                            "screenshot_base64": screenshot_base64,
                            "format": "png"
                        },
                        "error": None
                    })
                
                elif action == "get_page_structure":
                    include_hidden = params.get("include_hidden", False)
                    
                    js_extract = f"""
                    () => {{
                        const elements = [];
                        const allElements = document.querySelectorAll('*');
                        
                        for (const el of allElements) {{
                            if (!{str(include_hidden).lower()}) {{
                                const style = window.getComputedStyle(el);
                                if (style.display === 'none' || style.visibility === 'hidden') {{
                                    continue;
                                }}
                            }}
                            
                            elements.push({{
                                tag: el.tagName.toLowerCase(),
                                id: el.id || null,
                                text: el.textContent ? el.textContent.trim().substring(0, 50) : null,
                                role: el.getAttribute('role') || null,
                                ariaLabel: el.getAttribute('aria-label') || null
                            }});
                        }}
                        
                        return elements;
                    }}
                    """
                    
                    elements = await page.evaluate(js_extract)
                    
                    await manager.log_action(
                        session_id=session_id,
                        action='get_page_structure',
                        details={'total_elements': len(elements)}
                    )
                    
                    await websocket.send_json({
                        "success": True,
                        "result": {
                            "elements": elements,
                            "total_elements": len(elements)
                        },
                        "error": None
                    })
                
                elif action == "get_accessibility_tree":
                    snapshot = await page.accessibility.snapshot()
                    
                    await manager.log_action(
                        session_id=session_id,
                        action='get_accessibility_tree',
                        details={}
                    )
                    
                    await websocket.send_json({
                        "success": True,
                        "result": {
                            "tree": snapshot
                        },
                        "error": None
                    })
                
                else:
                    # Unknown action
                    await websocket.send_json({
                        "success": False,
                        "result": None,
                        "error": f"Unknown action: {action}"
                    })
            
            except PlaywrightTimeoutError as e:
                await websocket.send_json({
                    "success": False,
                    "result": None,
                    "error": f"Timeout: {str(e)}"
                })
            except Exception as e:
                logger.error(f"WebSocket action error: {e}", exc_info=True)
                await websocket.send_json({
                    "success": False,
                    "result": None,
                    "error": str(e)
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        # Clean up session on disconnect
        if session_id:
            try:
                await manager.close_session(session_id)
                logger.info(f"WebSocket session cleaned up: {session_id}")
            except Exception as e:
                logger.warning(f"Error cleaning up WebSocket session {session_id}: {e}")


# =============================================================================
# GLOBAL EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    """
    Global handler for ValueError exceptions (typically session not found).
    
    Args:
        request: FastAPI request object
        exc: ValueError exception
        
    Returns:
        JSON error response with 404 status
    """
    logger.warning(f"ValueError in request {request.url.path}: {exc}")
    return HTTPException(
        status_code=404,
        detail=str(exc)
    )


@app.exception_handler(PlaywrightTimeoutError)
async def playwright_timeout_handler(request, exc: PlaywrightTimeoutError):
    """
    Global handler for Playwright timeout errors.
    
    Args:
        request: FastAPI request object
        exc: PlaywrightTimeoutError exception
        
    Returns:
        JSON error response with 500 status
    """
    logger.error(f"Playwright timeout in request {request.url.path}: {exc}")
    return HTTPException(
        status_code=500,
        detail=f"Browser operation timeout: {str(exc)}"
    )


# =============================================================================
# MAIN EXECUTION BLOCK
# =============================================================================

if __name__ == '__main__':
    """
    Main entry point for running Playwright MCP server directly.
    
    Starts uvicorn ASGI server with configuration from settings.
    For production, use uvicorn directly or process manager (systemd, supervisor).
    
    Usage:
        python -m mcp_servers.playwright_mcp.main
    """
    logger.info("Starting Playwright MCP Server via __main__ block")
    
    # Get uvicorn configuration from settings
    uvicorn_config = settings.get_uvicorn_config()
    
    # Run uvicorn server
    uvicorn.run(
        'mcp_servers.playwright_mcp.main:app',
        **uvicorn_config
    )
