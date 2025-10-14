"""
SessionManager Module

Provides session management for isolated Playwright browser contexts across
concurrent LLM agent exploration sessions. This module enables multiple LLM
agents to explore different application workflows simultaneously without
shared state contamination.

Key Features:
- Browser instance lifecycle management (initialize/cleanup)
- Per-session isolated browser contexts with viewport configuration
- Exploration action logging for Gherkin scenario generation
- Multi-session support for concurrent LLM agent explorations
- Comprehensive error handling and logging

Integration Points:
- Used by main.py as FastAPI dependency
- Injected into all MCP tool endpoints (/tools/navigate, /tools/click, etc.)
- Exploration logs consumed by gherkin/generator.py for scenario generation
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

# Configure module-level logger
logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages isolated Playwright browser contexts for concurrent LLM agent
    exploration sessions.
    
    This class handles the complete lifecycle of browser sessions:
    - Initializing Playwright and launching browsers
    - Creating isolated browser contexts per session
    - Tracking exploration actions for Gherkin generation
    - Providing page access for MCP tool operations
    - Cleaning up sessions and browser resources
    
    Each session receives a dedicated BrowserContext with independent cookies,
    storage, and cache, preventing cross-session state contamination during
    parallel explorations.
    
    Attributes:
        playwright: Playwright async API instance
        browser: Launched browser instance (Chromium, Firefox, or WebKit)
        sessions: Dictionary mapping session_id to BrowserContext
        exploration_logs: Dictionary mapping session_id to action log list
        session_metadata: Dictionary mapping session_id to creation timestamp
    """
    
    def __init__(self):
        """
        Initialize SessionManager with empty state.
        
        All browser resources are lazily initialized via the initialize() method
        to support async context manager patterns.
        """
        self.playwright = None  # Playwright instance
        self.browser: Optional[Browser] = None  # Browser instance
        self.sessions: Dict[str, BrowserContext] = {}  # session_id -> BrowserContext
        self.exploration_logs: Dict[str, List[Dict]] = {}  # session_id -> action log
        self.session_metadata: Dict[str, Dict[str, Any]] = {}  # session_id -> metadata
        
        logger.debug("SessionManager instance created")
    
    async def initialize(
        self,
        browser_type: str = "chromium",
        headless: bool = False,
        viewport_width: int = 1920,
        viewport_height: int = 1080
    ) -> None:
        """
        Initialize Playwright and launch browser instance.
        
        This method must be called before creating sessions. It starts the
        Playwright async context and launches a browser based on the specified
        type. The browser instance is reused across all sessions for resource
        efficiency.
        
        Args:
            browser_type: Browser to launch - "chromium", "firefox", or "webkit"
            headless: Run browser in headless mode (False for LLM visibility)
            viewport_width: Default viewport width for browser contexts
            viewport_height: Default viewport height for browser contexts
        
        Raises:
            ValueError: If browser_type is not supported
            RuntimeError: If browser launch fails
        
        Note:
            headless=False is the default per Agent Action Plan to enable
            LLM visibility during exploration sessions.
        """
        try:
            logger.info(
                f"Initializing SessionManager with browser_type={browser_type}, "
                f"headless={headless}, viewport={viewport_width}x{viewport_height}"
            )
            
            # Start Playwright async API
            self.playwright = await async_playwright().start()
            logger.debug("Playwright async API started successfully")
            
            # Launch browser based on type
            if browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(headless=headless)
            elif browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(headless=headless)
            elif browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(headless=headless)
            else:
                error_msg = (
                    f"Unsupported browser_type: {browser_type}. "
                    f"Must be 'chromium', 'firefox', or 'webkit'"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(
                f"Browser launched successfully: {browser_type} "
                f"(headless={headless})"
            )
            
        except ValueError:
            # Re-raise ValueError for invalid browser_type
            raise
        except Exception as e:
            error_msg = f"Failed to initialize browser: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    async def create_session(
        self,
        viewport_width: Optional[int] = None,
        viewport_height: Optional[int] = None
    ) -> str:
        """
        Create a new isolated browser session for LLM agent exploration.
        
        This method generates a unique session ID, creates a dedicated browser
        context with configured viewport settings, and initializes an empty
        exploration log. Each session is completely isolated with independent
        cookies, storage, and cache.
        
        Args:
            viewport_width: Optional viewport width (defaults to browser default)
            viewport_height: Optional viewport height (defaults to browser default)
        
        Returns:
            Unique session_id string (UUID4 format)
        
        Raises:
            RuntimeError: If browser is not initialized or context creation fails
        
        Example:
            session_id = await manager.create_session(
                viewport_width=1920,
                viewport_height=1080
            )
        """
        if self.browser is None:
            error_msg = (
                "Browser not initialized. Call initialize() before creating sessions."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            # Generate unique session identifier
            session_id = str(uuid.uuid4())
            logger.debug(f"Generated session_id: {session_id}")
            
            # Configure viewport settings
            viewport_config = None
            if viewport_width is not None and viewport_height is not None:
                viewport_config = {
                    "width": viewport_width,
                    "height": viewport_height
                }
                logger.debug(
                    f"Creating context with viewport: "
                    f"{viewport_width}x{viewport_height}"
                )
            
            # Create isolated browser context
            context = await self.browser.new_context(viewport=viewport_config)
            logger.debug(f"Browser context created for session: {session_id}")
            
            # Create initial page in context
            page = await context.new_page()
            logger.debug(f"Initial page created for session: {session_id}")
            
            # Store session resources
            self.sessions[session_id] = context
            self.exploration_logs[session_id] = []
            self.session_metadata[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "viewport": viewport_config
            }
            
            logger.info(
                f"Session created successfully: {session_id} "
                f"(viewport: {viewport_config})"
            )
            
            return session_id
            
        except Exception as e:
            error_msg = f"Failed to create session: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    async def get_page(self, session_id: str) -> Page:
        """
        Retrieve the active page for a given session.
        
        This method returns the current page from the session's browser context.
        If no pages exist, a new page is created. This ensures MCP tools always
        have a valid page reference for browser operations.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            Playwright Page instance for the session
        
        Raises:
            ValueError: If session_id does not exist
        
        Example:
            page = await manager.get_page(session_id)
            await page.goto("https://example.com")
        """
        # Retrieve session context
        context = self.sessions.get(session_id)
        
        if context is None:
            error_msg = f"Session not found: {session_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Get existing pages from context
            pages = context.pages
            
            if pages:
                # Return first page if exists
                logger.debug(
                    f"Returning existing page for session: {session_id} "
                    f"({len(pages)} pages active)"
                )
                return pages[0]
            else:
                # Create new page if none exist
                logger.debug(f"Creating new page for session: {session_id}")
                page = await context.new_page()
                logger.info(f"New page created for session: {session_id}")
                return page
                
        except Exception as e:
            error_msg = f"Failed to get page for session {session_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    async def log_action(
        self,
        session_id: str,
        action: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Log an exploration action for Gherkin scenario generation.
        
        This method records browser interactions (navigate, click, type, screenshot)
        with timestamps and details. The complete exploration log enables LLM-driven
        conversion of exploration sessions into business-readable Gherkin scenarios.
        
        Args:
            session_id: Unique session identifier
            action: Action type (navigate, click, type, screenshot, etc.)
            details: Action-specific details dictionary
        
        Raises:
            ValueError: If session_id does not exist
        
        Example:
            await manager.log_action(
                session_id="abc-123",
                action="navigate",
                details={"url": "https://example.com", "title": "Example Domain"}
            )
        
        Action Details Structure:
            - navigate: {"url": str, "title": str}
            - click: {"selector": str, "element_text": str}
            - type: {"selector": str, "text": str}
            - screenshot: {"width": int, "height": int}
        """
        # Validate session exists
        if session_id not in self.exploration_logs:
            error_msg = f"Session not found: {session_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Create action entry with timestamp
            action_entry = {
                "action": action,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Append to exploration log
            self.exploration_logs[session_id].append(action_entry)
            
            logger.debug(
                f"Action logged for session {session_id}: {action} "
                f"(total actions: {len(self.exploration_logs[session_id])})"
            )
            
        except Exception as e:
            error_msg = (
                f"Failed to log action for session {session_id}: {str(e)}"
            )
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e
    
    async def get_exploration_log(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve the complete exploration log for a session.
        
        This method returns all logged actions with timestamps and details,
        used by the Gherkin generator to convert exploration sessions into
        test scenarios. Returns an empty list if the session doesn't exist
        for graceful degradation.
        
        Args:
            session_id: Unique session identifier
        
        Returns:
            List of action dictionaries with action, details, and timestamp
        
        Example:
            log = await manager.get_exploration_log("abc-123")
            # Returns: [
            #     {
            #         "action": "navigate",
            #         "details": {"url": "...", "title": "..."},
            #         "timestamp": "2024-01-15T10:30:00.000000"
            #     },
            #     ...
            # ]
        """
        log = self.exploration_logs.get(session_id, [])
        
        logger.debug(
            f"Retrieved exploration log for session {session_id}: "
            f"{len(log)} actions"
        )
        
        return log
    
    async def close_session(self, session_id: str) -> None:
        """
        Close a session and release all associated resources.
        
        This method closes the browser context, removes the session from
        tracking dictionaries, and clears the exploration log. Should be
        called when an LLM agent completes its exploration or when cleaning
        up idle sessions.
        
        Args:
            session_id: Unique session identifier
        
        Raises:
            ValueError: If session_id does not exist
        
        Example:
            await manager.close_session("abc-123")
        """
        # Retrieve context
        context = self.sessions.get(session_id)
        
        if context is None:
            error_msg = f"Session not found: {session_id}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Close browser context
            await context.close()
            logger.debug(f"Browser context closed for session: {session_id}")
            
            # Remove session tracking data
            del self.sessions[session_id]
            del self.exploration_logs[session_id]
            
            # Remove metadata if exists
            if session_id in self.session_metadata:
                del self.session_metadata[session_id]
            
            logger.info(f"Session closed successfully: {session_id}")
            
        except Exception as e:
            error_msg = f"Failed to close session {session_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Attempt cleanup even if close failed
            self.sessions.pop(session_id, None)
            self.exploration_logs.pop(session_id, None)
            self.session_metadata.pop(session_id, None)
            
            raise RuntimeError(error_msg) from e
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions with metadata.
        
        Returns session information including creation timestamp and action
        count for monitoring and debugging purposes. Used by the /sessions
        endpoint for session management.
        
        Returns:
            List of session metadata dictionaries
        
        Example:
            sessions = manager.list_sessions()
            # Returns: [
            #     {
            #         "session_id": "abc-123",
            #         "actions_logged": 15,
            #         "created_at": "2024-01-15T10:30:00.000000"
            #     },
            #     ...
            # ]
        """
        sessions_info = []
        
        for session_id in self.sessions.keys():
            metadata = self.session_metadata.get(session_id, {})
            
            session_info = {
                "session_id": session_id,
                "actions_logged": len(self.exploration_logs.get(session_id, [])),
                "created_at": metadata.get("created_at", "unknown"),
                "viewport": metadata.get("viewport")
            }
            
            sessions_info.append(session_info)
        
        logger.debug(f"Listed {len(sessions_info)} active sessions")
        
        return sessions_info
    
    async def cleanup(self) -> None:
        """
        Clean up all sessions and browser resources.
        
        This method closes all active sessions, shuts down the browser instance,
        and stops the Playwright context. Should be called during FastAPI
        shutdown events to ensure proper resource cleanup.
        
        This is a graceful cleanup that continues even if individual session
        closures fail, ensuring the browser and Playwright instances are
        properly terminated.
        
        Example:
            # In FastAPI shutdown event
            @app.on_event("shutdown")
            async def shutdown():
                await session_manager.cleanup()
        """
        logger.info("Starting SessionManager cleanup")
        
        # Close all active sessions
        session_ids = list(self.sessions.keys())
        
        for session_id in session_ids:
            try:
                await self.close_session(session_id)
            except Exception as e:
                logger.warning(
                    f"Error closing session {session_id} during cleanup: {e}"
                )
                # Continue cleanup even if individual session fails
        
        # Close browser instance
        if self.browser:
            try:
                await self.browser.close()
                logger.info("Browser instance closed")
            except Exception as e:
                logger.error(f"Error closing browser: {e}", exc_info=True)
            finally:
                self.browser = None
        
        # Stop Playwright
        if self.playwright:
            try:
                await self.playwright.stop()
                logger.info("Playwright stopped")
            except Exception as e:
                logger.error(f"Error stopping Playwright: {e}", exc_info=True)
            finally:
                self.playwright = None
        
        # Reset internal state
        self.sessions = {}
        self.exploration_logs = {}
        self.session_metadata = {}
        
        logger.info("SessionManager cleanup completed")


