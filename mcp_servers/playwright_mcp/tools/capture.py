"""
Screenshot and trace capture tool implementations for Playwright MCP server.

This module provides comprehensive capture capabilities for LLM-driven browser exploration,
including screenshots, trace recording, PDFs, and video capture. All capture functions
support visual documentation and debugging of exploration sessions.

Capture Capabilities:
    - Full-page and viewport screenshots
    - Element-specific screenshots using stable locators
    - Base64-encoded screenshots for WebSocket streaming
    - Playwright trace recording with timeline replay
    - PDF generation (Chromium only)
    - Video recording path retrieval
    - Annotated screenshots with bounding boxes
    - Screenshot sequences for long pages

All functions return JSON-serializable dictionaries for MCP endpoint responses.
"""

from playwright.async_api import Page, BrowserContext, Error as PlaywrightError
from typing import Dict, Optional, List, Any
import logging
import base64
import os
from pathlib import Path
from datetime import datetime
import json

# Import locator builder for element screenshot support
from .interaction import build_locator

logger = logging.getLogger(__name__)


async def capture_screenshot(
    page: Page,
    full_page: bool = True,
    element_selector: Optional[str] = None
) -> Dict[str, Any]:
    """
    Capture full page, viewport, or element screenshot with base64 encoding.
    
    This function provides flexible screenshot capture for visual documentation
    during LLM exploration sessions. Screenshots are base64-encoded for easy
    transmission via WebSocket or JSON-RPC responses.
    
    Args:
        page: Playwright Page instance
        full_page: If True, capture entire scrollable page; if False, capture viewport only
        element_selector: Optional selector for element-specific screenshot
    
    Returns:
        Dict with screenshot_base64, dimensions, format, capture_type, and file_size_kb
        
    Examples:
        # Full page screenshot
        result = await capture_screenshot(page, full_page=True)
        
        # Viewport screenshot
        result = await capture_screenshot(page, full_page=False)
        
        # Element screenshot
        result = await capture_screenshot(page, element_selector="role:button[name=Submit]")
    """
    logger.info(f"Capturing screenshot: full_page={full_page}, element={element_selector}")
    
    try:
        screenshot_bytes: bytes
        capture_type: str
        
        # Element-specific screenshot
        if element_selector:
            logger.debug(f"Capturing element screenshot for selector: {element_selector}")
            locator = build_locator(page, element_selector)
            screenshot_bytes = await locator.screenshot()
            capture_type = "element"
            logger.info(f"Element screenshot captured for: {element_selector}")
        
        # Full page screenshot
        elif full_page:
            logger.debug("Capturing full page screenshot")
            screenshot_bytes = await page.screenshot(full_page=True)
            capture_type = "full_page"
            logger.info("Full page screenshot captured")
        
        # Viewport screenshot
        else:
            logger.debug("Capturing viewport screenshot")
            screenshot_bytes = await page.screenshot()
            capture_type = "viewport"
            logger.info("Viewport screenshot captured")
        
        # Encode to base64 for transmission
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        # Get viewport dimensions
        viewport = page.viewport_size
        width = viewport['width'] if viewport else 0
        height = viewport['height'] if viewport else 0
        
        # Calculate file size
        file_size_kb = len(screenshot_bytes) // 1024
        
        logger.info(f"Screenshot encoded: {file_size_kb}KB, {width}x{height}, type={capture_type}")
        
        return {
            "success": True,
            "screenshot_base64": screenshot_base64,
            "width": width,
            "height": height,
            "format": "png",
            "capture_type": capture_type,
            "file_size_kb": file_size_kb,
            "page_url": page.url
        }
    
    except PlaywrightError as e:
        error_msg = f"Screenshot capture failed: {str(e)}"
        if element_selector:
            error_msg = f"Element screenshot failed for '{element_selector}': {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "screenshot_failed",
            "error_message": error_msg,
            "element_selector": element_selector,
            "page_url": page.url
        }
    
    except Exception as e:
        error_msg = f"Unexpected error capturing screenshot: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "page_url": page.url
        }


async def save_screenshot_to_file(
    page: Page,
    file_path: str,
    full_page: bool = True
) -> Dict[str, Any]:
    """
    Save screenshot directly to file on disk.
    
    This function saves screenshots to the filesystem for persistent storage,
    debugging, and attachment to test reports. Parent directories are created
    automatically if they don't exist.
    
    Args:
        page: Playwright Page instance
        file_path: Output file path (absolute or relative)
        full_page: If True, capture entire scrollable page; if False, capture viewport
    
    Returns:
        Dict with success status, file_path, and file_size_kb
        
    Example:
        result = await save_screenshot_to_file(
            page,
            "screenshots/exploration_session_123.png",
            full_page=True
        )
    """
    logger.info(f"Saving screenshot to file: {file_path}, full_page={full_page}")
    
    try:
        # Create parent directories if they don't exist
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Playwright automatically saves to specified path
        await page.screenshot(path=file_path, full_page=full_page)
        
        # Get file size
        file_size_kb = os.path.getsize(file_path) // 1024
        
        logger.info(f"Screenshot saved: {file_path} ({file_size_kb}KB)")
        
        return {
            "success": True,
            "file_path": str(file_path_obj.absolute()),
            "file_size_kb": file_size_kb,
            "format": "png",
            "page_url": page.url
        }
    
    except IOError as e:
        error_msg = f"Failed to save screenshot to {file_path}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "io_error",
            "error_message": error_msg,
            "file_path": file_path
        }
    
    except PlaywrightError as e:
        error_msg = f"Screenshot capture failed: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "screenshot_failed",
            "error_message": error_msg,
            "file_path": file_path
        }
    
    except Exception as e:
        error_msg = f"Unexpected error saving screenshot: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "file_path": file_path
        }


async def start_trace(
    context: BrowserContext,
    name: str = 'trace',
    screenshots: bool = True,
    snapshots: bool = True
) -> Dict[str, Any]:
    """
    Start Playwright trace recording for comprehensive debugging.
    
    Traces capture a complete timeline of browser actions including screenshots,
    DOM snapshots, network requests, console logs, and source code. Traces can
    be replayed using 'playwright show-trace <trace-file>'.
    
    Captured Data:
        - Screenshots at each action (if screenshots=True)
        - DOM snapshots for timeline replay (if snapshots=True)
        - Source code for debugging (sources=True)
        - Network requests and responses
        - Console logs and errors
    
    Args:
        context: Playwright BrowserContext instance
        name: Trace name for identification
        screenshots: Whether to capture screenshots at each action
        snapshots: Whether to capture DOM snapshots
    
    Returns:
        Dict with success status, trace_name, and started_at timestamp
        
    Example:
        result = await start_trace(context, name="exploration_session_123")
    """
    logger.info(f"Starting trace recording: {name}, screenshots={screenshots}, snapshots={snapshots}")
    
    try:
        # Start trace with comprehensive capture
        await context.tracing.start(
            screenshots=screenshots,
            snapshots=snapshots,
            sources=True  # Include source code for debugging
        )
        
        started_at = datetime.utcnow().isoformat() + 'Z'
        
        logger.info(f"Trace recording started: {name} at {started_at}")
        
        return {
            "success": True,
            "trace_name": name,
            "started_at": started_at,
            "captures": {
                "screenshots": screenshots,
                "snapshots": snapshots,
                "sources": True,
                "network": True,
                "console": True
            }
        }
    
    except PlaywrightError as e:
        error_msg = f"Failed to start trace recording: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "trace_start_failed",
            "error_message": error_msg,
            "trace_name": name
        }
    
    except Exception as e:
        error_msg = f"Unexpected error starting trace: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "trace_name": name
        }


async def stop_trace(
    context: BrowserContext,
    output_path: str
) -> Dict[str, Any]:
    """
    Stop trace recording and save to ZIP file.
    
    The trace ZIP file contains:
        - trace.json: Action timeline
        - screenshots/: Action screenshots
        - snapshots/: DOM snapshots
        - Network logs
    
    View the trace with: playwright show-trace <output_path>
    
    Args:
        context: Playwright BrowserContext instance
        output_path: Path to save trace ZIP file
    
    Returns:
        Dict with success status, trace_path, file_size_mb, and viewing instructions
        
    Example:
        result = await stop_trace(context, "traces/session_123.zip")
    """
    logger.info(f"Stopping trace recording: {output_path}")
    
    try:
        # Create parent directories if they don't exist
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Stop trace and save to file
        await context.tracing.stop(path=output_path)
        
        # Get file size in MB
        file_size_bytes = os.path.getsize(output_path)
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)
        
        logger.info(f"Trace saved: {output_path} ({file_size_mb}MB)")
        
        return {
            "success": True,
            "trace_path": str(output_path_obj.absolute()),
            "file_size_mb": file_size_mb,
            "can_be_viewed_with": f"playwright show-trace {output_path}",
            "trace_contents": {
                "action_timeline": "trace.json",
                "screenshots": "screenshots/",
                "dom_snapshots": "snapshots/",
                "network_logs": "included"
            }
        }
    
    except IOError as e:
        error_msg = f"Failed to save trace to {output_path}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "io_error",
            "error_message": error_msg,
            "output_path": output_path
        }
    
    except PlaywrightError as e:
        error_msg = f"Failed to stop trace recording: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "trace_stop_failed",
            "error_message": error_msg,
            "output_path": output_path
        }
    
    except Exception as e:
        error_msg = f"Unexpected error stopping trace: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "output_path": output_path
        }


async def capture_trace_for_session(
    context: BrowserContext,
    session_id: str,
    output_dir: str = 'traces'
) -> Dict[str, Any]:
    """
    Capture trace for a specific exploration session with automatic naming.
    
    This convenience function generates a unique filename based on session ID
    and timestamp, then stops and saves the current trace.
    
    Args:
        context: Playwright BrowserContext instance
        session_id: Unique session identifier
        output_dir: Directory to save trace files (default 'traces')
    
    Returns:
        Dict with success status and trace_path
        
    Example:
        result = await capture_trace_for_session(context, "llm_exploration_abc123")
    """
    logger.info(f"Capturing trace for session: {session_id}")
    
    try:
        # Generate unique filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{session_id}_{timestamp}.zip"
        output_path = os.path.join(output_dir, filename)
        
        # Stop and save trace
        result = await stop_trace(context, output_path)
        
        if result.get("success"):
            logger.info(f"Session trace captured: {output_path}")
            result["session_id"] = session_id
        
        return result
    
    except Exception as e:
        error_msg = f"Failed to capture trace for session {session_id}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "session_trace_failed",
            "error_message": error_msg,
            "session_id": session_id
        }


async def capture_pdf(
    page: Page,
    output_path: str,
    format: str = 'A4'
) -> Dict[str, Any]:
    """
    Capture page as PDF document (Chromium only).
    
    This function generates PDF files from web pages, useful for document-based
    explorations and archival. Only works in Chromium browser (not Firefox/WebKit).
    
    Args:
        page: Playwright Page instance
        output_path: Path to save PDF file
        format: Page format (A4, Letter, Legal, etc.)
    
    Returns:
        Dict with success status, pdf_path, and page_count estimate
        
    Example:
        result = await capture_pdf(page, "documents/report.pdf", format="A4")
        
    Note:
        Browser must be Chromium. Firefox and WebKit do not support PDF generation.
    """
    logger.info(f"Capturing PDF: {output_path}, format={format}")
    
    try:
        # Create parent directories if they don't exist
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate PDF (Chromium only)
        await page.pdf(path=output_path, format=format)
        
        # Get file size
        file_size_kb = os.path.getsize(output_path) // 1024
        
        logger.info(f"PDF captured: {output_path} ({file_size_kb}KB)")
        
        return {
            "success": True,
            "pdf_path": str(output_path_obj.absolute()),
            "file_size_kb": file_size_kb,
            "format": format,
            "page_url": page.url,
            "note": "PDF generation only works in Chromium browser"
        }
    
    except IOError as e:
        error_msg = f"Failed to save PDF to {output_path}: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "io_error",
            "error_message": error_msg,
            "output_path": output_path
        }
    
    except PlaywrightError as e:
        error_msg = f"PDF capture failed: {str(e)}. Note: PDF generation only works in Chromium."
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "pdf_not_supported",
            "error_message": error_msg,
            "output_path": output_path,
            "note": "Ensure browser is Chromium (not Firefox/WebKit)"
        }
    
    except Exception as e:
        error_msg = f"Unexpected error capturing PDF: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg,
            "output_path": output_path
        }


def get_video_path(context: BrowserContext) -> Optional[str]:
    """
    Get video recording path if video capture is enabled.
    
    Video recording must be configured at context creation time with the
    record_video_dir option. This function retrieves the path to the saved
    video file after the page closes.
    
    Args:
        context: Playwright BrowserContext instance
    
    Returns:
        Optional[str]: Video file path if recording enabled, None otherwise
        
    Example:
        # Context must be created with video recording:
        # context = await browser.new_context(record_video_dir="videos/")
        
        video_path = get_video_path(context)
        if video_path:
            print(f"Video saved to: {video_path}")
        else:
            print("Video recording not enabled")
            
    Note:
        Video path is only available after page.close() is called.
    """
    logger.info("Retrieving video path from context")
    
    try:
        # Check if context has any pages
        if not context.pages:
            logger.warning("No pages in context, cannot retrieve video path")
            return None
        
        # Get video object from first page
        page = context.pages[0]
        video = page.video
        
        if video:
            # Video path is available after page closes
            video_path = video.path()
            logger.info(f"Video path retrieved: {video_path}")
            return video_path
        else:
            logger.info("Video recording not enabled for this context")
            return None
    
    except Exception as e:
        logger.error(f"Error retrieving video path: {str(e)}")
        return None


async def get_screenshot_metadata(page: Page) -> Dict[str, Any]:
    """
    Get screenshot metadata without capturing actual screenshot.
    
    This function collects contextual information about the page state without
    the overhead of capturing and encoding a full screenshot. Useful for logging
    and understanding page state during exploration.
    
    Args:
        page: Playwright Page instance
    
    Returns:
        Dict with viewport_size, page_url, page_title, scroll_position, and device_scale_factor
        
    Example:
        metadata = await get_screenshot_metadata(page)
        # {
        #     "viewport_size": {"width": 1280, "height": 720},
        #     "page_url": "https://example.com",
        #     "page_title": "Example Domain",
        #     "scroll_position": {"x": 0, "y": 250},
        #     "device_scale_factor": 2.0
        # }
    """
    logger.info(f"Collecting screenshot metadata for: {page.url}")
    
    try:
        # Get viewport size
        viewport = page.viewport_size
        viewport_size = {
            "width": viewport['width'] if viewport else 0,
            "height": viewport['height'] if viewport else 0
        }
        
        # Get page URL and title
        page_url = page.url
        page_title = await page.title()
        
        # Get scroll position
        scroll_position = await page.evaluate('({x: window.scrollX, y: window.scrollY})')
        
        # Get device scale factor (pixel ratio)
        device_scale_factor = await page.evaluate('window.devicePixelRatio')
        
        # Get timestamp
        snapshot_timestamp = datetime.utcnow().isoformat() + 'Z'
        
        logger.info(f"Screenshot metadata collected for: {page_url}")
        
        return {
            "success": True,
            "viewport_size": viewport_size,
            "page_url": page_url,
            "page_title": page_title,
            "scroll_position": scroll_position,
            "device_scale_factor": device_scale_factor,
            "snapshot_timestamp": snapshot_timestamp
        }
    
    except PlaywrightError as e:
        error_msg = f"Failed to collect screenshot metadata: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "metadata_collection_failed",
            "error_message": error_msg
        }
    
    except Exception as e:
        error_msg = f"Unexpected error collecting metadata: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg
        }


async def capture_annotated_screenshot(
    page: Page,
    annotations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Capture screenshot with annotations overlaid on the page.
    
    This function draws annotations (bounding boxes, labels, highlights) on the
    page before capturing the screenshot. Useful for highlighting elements during
    exploration and generating visual documentation.
    
    Args:
        page: Playwright Page instance
        annotations: List of annotation dictionaries with structure:
            [
                {
                    "type": "box",  # or "label", "highlight"
                    "x": 100,
                    "y": 200,
                    "width": 150,
                    "height": 50,
                    "label": "Submit Button",
                    "color": "red"
                }
            ]
    
    Returns:
        Dict with annotated_screenshot_base64 and annotation_count
        
    Example:
        annotations = [
            {"type": "box", "x": 100, "y": 200, "width": 150, "height": 50,
             "label": "Login", "color": "red"}
        ]
        result = await capture_annotated_screenshot(page, annotations)
    """
    logger.info(f"Capturing annotated screenshot with {len(annotations)} annotations")
    
    try:
        # Inject JavaScript to draw annotations
        annotation_script = """
        (annotations) => {
            const canvas = document.createElement('canvas');
            canvas.width = window.innerWidth;
            canvas.height = document.documentElement.scrollHeight;
            canvas.style.position = 'absolute';
            canvas.style.top = '0';
            canvas.style.left = '0';
            canvas.style.zIndex = '999999';
            canvas.style.pointerEvents = 'none';
            document.body.appendChild(canvas);
            
            const ctx = canvas.getContext('2d');
            
            annotations.forEach(ann => {
                if (ann.type === 'box') {
                    ctx.strokeStyle = ann.color || 'red';
                    ctx.lineWidth = 3;
                    ctx.strokeRect(ann.x, ann.y, ann.width, ann.height);
                    
                    if (ann.label) {
                        ctx.fillStyle = ann.color || 'red';
                        ctx.font = '14px Arial';
                        ctx.fillText(ann.label, ann.x, ann.y - 5);
                    }
                }
            });
        }
        """
        
        # Execute annotation script
        await page.evaluate(annotation_script, annotations)
        
        # Capture screenshot with annotations
        screenshot_bytes = await page.screenshot(full_page=True)
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        # Remove annotation canvas
        await page.evaluate('document.querySelector("canvas[style*=\'z-index: 999999\']")?.remove()')
        
        file_size_kb = len(screenshot_bytes) // 1024
        
        logger.info(f"Annotated screenshot captured: {file_size_kb}KB, {len(annotations)} annotations")
        
        return {
            "success": True,
            "annotated_screenshot_base64": screenshot_base64,
            "annotation_count": len(annotations),
            "file_size_kb": file_size_kb,
            "page_url": page.url
        }
    
    except PlaywrightError as e:
        error_msg = f"Failed to capture annotated screenshot: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "annotated_screenshot_failed",
            "error_message": error_msg
        }
    
    except Exception as e:
        error_msg = f"Unexpected error capturing annotated screenshot: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg
        }


async def capture_screenshot_sequence(
    page: Page,
    scroll_steps: int = 5,
    delay_ms: int = 500
) -> List[Dict[str, Any]]:
    """
    Capture sequence of screenshots while scrolling down the page.
    
    This function is useful for long pages where a single full-page screenshot
    would be too large or impractical. It scrolls the page in increments and
    captures a screenshot at each step.
    
    Args:
        page: Playwright Page instance
        scroll_steps: Number of scroll increments (default 5)
        delay_ms: Delay between scrolls in milliseconds for rendering (default 500)
    
    Returns:
        List of dicts with screenshot_base64 and scroll_position_y for each step
        
    Example:
        screenshots = await capture_screenshot_sequence(page, scroll_steps=5, delay_ms=500)
        for i, screenshot in enumerate(screenshots):
            print(f"Screenshot {i+1} at scroll position: {screenshot['scroll_position_y']}")
    """
    logger.info(f"Capturing screenshot sequence: {scroll_steps} steps, {delay_ms}ms delay")
    
    screenshots = []
    
    try:
        # Get page height
        page_height = await page.evaluate('document.documentElement.scrollHeight')
        viewport_height = await page.evaluate('window.innerHeight')
        
        # Calculate scroll increment
        scrollable_height = page_height - viewport_height
        scroll_increment = scrollable_height // scroll_steps if scroll_steps > 0 else 0
        
        logger.debug(f"Page height: {page_height}, viewport: {viewport_height}, increment: {scroll_increment}")
        
        # Capture screenshots at each scroll position
        for step in range(scroll_steps + 1):
            scroll_y = step * scroll_increment
            
            # Scroll to position
            await page.evaluate(f'window.scrollTo(0, {scroll_y})')
            
            # Wait for rendering
            await page.wait_for_timeout(delay_ms)
            
            # Capture screenshot
            screenshot_bytes = await page.screenshot()
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            file_size_kb = len(screenshot_bytes) // 1024
            
            screenshots.append({
                "screenshot_base64": screenshot_base64,
                "scroll_position_y": scroll_y,
                "step_number": step + 1,
                "file_size_kb": file_size_kb
            })
            
            logger.debug(f"Captured screenshot {step + 1}/{scroll_steps + 1} at scroll_y={scroll_y}")
        
        logger.info(f"Screenshot sequence completed: {len(screenshots)} screenshots captured")
        
        return screenshots
    
    except PlaywrightError as e:
        error_msg = f"Failed to capture screenshot sequence: {str(e)}"
        logger.error(error_msg)
        return [{
            "success": False,
            "error_code": "sequence_capture_failed",
            "error_message": error_msg
        }]
    
    except Exception as e:
        error_msg = f"Unexpected error capturing screenshot sequence: {str(e)}"
        logger.error(error_msg)
        return [{
            "success": False,
            "error_code": "unknown",
            "error_message": error_msg
        }]


def compress_screenshot(screenshot_bytes: bytes, quality: int = 80) -> bytes:
    """
    Compress screenshot bytes to reduce file size.
    
    This function converts PNG screenshots to JPEG format with adjustable quality
    to reduce file size for transmission or storage. Requires Pillow/PIL.
    
    Args:
        screenshot_bytes: Original PNG screenshot bytes
        quality: JPEG quality 1-100 (default 80)
    
    Returns:
        Compressed JPEG bytes
        
    Example:
        screenshot_bytes = await page.screenshot()
        compressed = compress_screenshot(screenshot_bytes, quality=80)
        # Compressed bytes are typically 50-80% smaller
        
    Note:
        This function requires Pillow (PIL) to be installed.
        If not available, it returns the original bytes unchanged.
    """
    logger.info(f"Compressing screenshot: quality={quality}")
    
    try:
        # Try to import PIL
        from PIL import Image
        import io
        
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(screenshot_bytes))
        
        # Convert RGBA to RGB if necessary
        if image.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])  # Use alpha channel as mask
            image = background
        
        # Compress to JPEG
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_bytes = output.getvalue()
        
        # Calculate compression ratio
        original_size_kb = len(screenshot_bytes) // 1024
        compressed_size_kb = len(compressed_bytes) // 1024
        compression_ratio = round((1 - len(compressed_bytes) / len(screenshot_bytes)) * 100, 1)
        
        logger.info(
            f"Screenshot compressed: {original_size_kb}KB → {compressed_size_kb}KB "
            f"({compression_ratio}% reduction)"
        )
        
        return compressed_bytes
    
    except ImportError:
        logger.warning("Pillow not installed, returning uncompressed screenshot")
        return screenshot_bytes
    
    except Exception as e:
        logger.error(f"Failed to compress screenshot: {str(e)}, returning original")
        return screenshot_bytes
