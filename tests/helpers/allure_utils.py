"""
Allure Reporting Helper Utilities

This module provides comprehensive Allure reporting helpers for enhanced test documentation
and diagnostics. It includes custom step decorators, attachment functions for screenshots,
logs, and API responses, metadata management for test categorization, and environment
information capture that enhance Allure HTML reports with comprehensive diagnostic information.

Key Features:
- Custom Allure step decorators for test action logging
- Attachment helpers for screenshots, traces, and API logs
- Metadata management utilities for test categorization and severity
- Automatic screenshot capture on test failure
- Environment information capture for test reproducibility
- Helpers for JSON, text, and HTML attachments to Allure reports

Dependencies:
- allure-pytest 2.15.0: Core Allure reporting framework
- httpx 0.28.1: HTTP client for API request/response logging
- playwright 1.55.0: Browser automation for UI diagnostics
"""

import json
from functools import wraps
from typing import Any, Callable, Dict, Optional

import allure
import httpx
from playwright.sync_api import Page


# ============================================================================
# Custom Step Decorators
# ============================================================================


def allure_step(step_title: str) -> Callable:
    """
    Decorator for logging test actions as Allure steps with a fixed title.
    
    This decorator wraps test functions and helper methods to create visible
    steps in Allure reports, improving test readability and debugging.
    
    Args:
        step_title: The title to display in the Allure report step
        
    Returns:
        Decorated function that executes within an Allure step context
        
    Example:
        @allure_step("Navigate to login page")
        def go_to_login(page):
            page.goto("/login")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with allure.step(step_title):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def allure_step_with_params(step_title_template: str) -> Callable:
    """
    Decorator that formats step title with function parameters.
    
    This decorator allows dynamic step titles that include actual parameter values,
    making Allure reports more informative by showing what data was used in each step.
    
    Args:
        step_title_template: Template string with format placeholders for parameters
        
    Returns:
        Decorated function with dynamically formatted step titles
        
    Example:
        @allure_step_with_params("Login with email: {email}")
        def login(page, email, password):
            page.fill("#email", email)
            page.fill("#password", password)
            page.click("#submit")
            
    Note:
        Template placeholders must match the function's parameter names.
        Positional and keyword arguments are both supported.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                # Attempt to format title with provided arguments
                # Support both positional and keyword arguments
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                step_title = step_title_template.format(**bound_args.arguments)
            except (KeyError, IndexError, AttributeError):
                # Fallback to template if formatting fails
                step_title = step_title_template
            
            with allure.step(step_title):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# Screenshot and Page Capture Helpers
# ============================================================================


def attach_screenshot(page: Page, name: str = "Screenshot") -> None:
    """
    Capture and attach a full-page screenshot to the Allure report.
    
    This function captures the entire page (including content below the fold)
    and attaches it to the current test's Allure report for visual verification.
    
    Args:
        page: Playwright Page instance to capture
        name: Name for the screenshot attachment in Allure report
        
    Example:
        def test_homepage(page):
            page.goto("https://example.com")
            attach_screenshot(page, "Homepage Initial Load")
            assert page.title() == "Example Domain"
    """
    try:
        screenshot_bytes = page.screenshot(full_page=True)
        allure.attach(
            screenshot_bytes,
            name=name,
            attachment_type=allure.attachment_type.PNG
        )
    except Exception as e:
        # Gracefully handle screenshot failures without breaking tests
        allure.attach(
            f"Failed to capture screenshot: {str(e)}",
            name=f"{name} (Error)",
            attachment_type=allure.attachment_type.TEXT
        )


def attach_page_source(page: Page, name: str = "Page HTML") -> None:
    """
    Attach the current page's HTML source code to the Allure report.
    
    This function captures the full HTML content of the page, useful for
    debugging element locator issues or verifying server-rendered content.
    
    Args:
        page: Playwright Page instance to capture
        name: Name for the HTML attachment in Allure report
        
    Example:
        def test_dynamic_content(page):
            page.goto("/dashboard")
            attach_page_source(page, "Dashboard HTML After Login")
    """
    try:
        html_content = page.content()
        allure.attach(
            html_content,
            name=name,
            attachment_type=allure.attachment_type.HTML
        )
    except Exception as e:
        allure.attach(
            f"Failed to capture page source: {str(e)}",
            name=f"{name} (Error)",
            attachment_type=allure.attachment_type.TEXT
        )


def attach_browser_console_logs(page: Page) -> None:
    """
    Capture and attach browser console logs to the Allure report.
    
    This function retrieves JavaScript console messages (log, warn, error) that
    occurred during test execution. Requires console message listener to be set up
    in conftest.py or page fixture.
    
    Args:
        page: Playwright Page instance with _console_messages attribute
        
    Example:
        # In conftest.py:
        @pytest.fixture
        def page(page):
            page._console_messages = []
            page.on("console", lambda msg: page._console_messages.append(msg))
            yield page
            
        # In test:
        def test_app(page):
            page.goto("/")
            attach_browser_console_logs(page)
    """
    console_messages = getattr(page, '_console_messages', [])
    
    if not console_messages:
        allure.attach(
            "No console messages captured. Ensure console listener is configured.",
            name="Browser Console Logs",
            attachment_type=allure.attachment_type.TEXT
        )
        return
    
    console_logs = "\n".join(
        [f"[{msg.type.upper()}] {msg.text}" for msg in console_messages]
    )
    
    allure.attach(
        console_logs,
        name="Browser Console Logs",
        attachment_type=allure.attachment_type.TEXT
    )


def attach_trace_file(trace_path: str) -> None:
    """
    Attach a Playwright trace file to the Allure report.
    
    Playwright traces contain detailed browser interaction recordings that can be
    viewed in the Playwright Trace Viewer for in-depth debugging.
    
    Args:
        trace_path: Absolute file path to the Playwright trace ZIP file
        
    Example:
        def test_complex_flow(page, browser_context):
            browser_context.tracing.start(screenshots=True, snapshots=True)
            # ... test steps ...
            trace_path = "traces/test_complex_flow.zip"
            browser_context.tracing.stop(path=trace_path)
            attach_trace_file(trace_path)
    """
    try:
        # Note: Allure doesn't have a ZIP attachment type, so we use None for binary files
        allure.attach.file(
            trace_path,
            name="Playwright Trace"
        )
    except FileNotFoundError:
        allure.attach(
            f"Trace file not found: {trace_path}",
            name="Playwright Trace (Error)",
            attachment_type=allure.attachment_type.TEXT
        )
    except Exception as e:
        allure.attach(
            f"Failed to attach trace file: {str(e)}",
            name="Playwright Trace (Error)",
            attachment_type=allure.attachment_type.TEXT
        )


# ============================================================================
# API Request/Response Logging Helpers
# ============================================================================


def attach_api_request(request: httpx.Request) -> None:
    """
    Format and attach HTTP request details to the Allure report.
    
    This function captures comprehensive request information including method,
    URL, headers, and body for API test debugging.
    
    Args:
        request: httpx Request instance to log
        
    Example:
        def test_create_user(api_client):
            response = api_client.post("/users", json={"name": "Alice"})
            attach_api_request(response.request)
            attach_api_response(response)
    """
    try:
        # Format request body
        if request.content:
            try:
                body_content = request.content.decode('utf-8')
            except UnicodeDecodeError:
                body_content = f"<binary data: {len(request.content)} bytes>"
        else:
            body_content = "No body"
        
        # Build formatted request details
        request_details = f"""Method: {request.method}
URL: {request.url}

Headers:
{_format_dict(dict(request.headers))}

Body:
{body_content}
"""
        
        allure.attach(
            request_details,
            name=f"Request: {request.method} {request.url.path}",
            attachment_type=allure.attachment_type.TEXT
        )
    except Exception as e:
        allure.attach(
            f"Failed to attach API request: {str(e)}",
            name="API Request (Error)",
            attachment_type=allure.attachment_type.TEXT
        )


def attach_api_response(response: httpx.Response) -> None:
    """
    Format and attach HTTP response details to the Allure report.
    
    This function captures comprehensive response information including status code,
    elapsed time, headers, and body for API test debugging.
    
    Args:
        response: httpx Response instance to log
        
    Example:
        def test_get_user(api_client):
            response = api_client.get("/users/123")
            attach_api_response(response)
            assert response.status_code == 200
    """
    try:
        # Calculate elapsed time safely
        try:
            elapsed_seconds = response.elapsed.total_seconds()
            elapsed_str = f"{elapsed_seconds:.3f}s"
        except AttributeError:
            elapsed_str = "N/A"
        
        # Format response body (handle binary and JSON)
        try:
            response_body = response.text
        except Exception:
            response_body = f"<binary data: {len(response.content)} bytes>"
        
        # Build formatted response details
        response_details = f"""Status: {response.status_code} {response.reason_phrase}
Elapsed: {elapsed_str}

Headers:
{_format_dict(dict(response.headers))}

Body:
{response_body}
"""
        
        allure.attach(
            response_details,
            name=f"Response: {response.status_code}",
            attachment_type=allure.attachment_type.TEXT
        )
    except Exception as e:
        allure.attach(
            f"Failed to attach API response: {str(e)}",
            name="API Response (Error)",
            attachment_type=allure.attachment_type.TEXT
        )


def get_api_logging_hooks() -> Dict[str, list]:
    """
    Return httpx event hooks for automatic Allure logging of API requests/responses.
    
    These hooks automatically attach all API requests and responses to Allure reports
    when configured on an httpx Client instance.
    
    Returns:
        Dictionary of event hooks compatible with httpx.Client(event_hooks=...)
        
    Example:
        # In conftest.py:
        @pytest.fixture
        def api_client():
            from tests.helpers.allure_utils import get_api_logging_hooks
            client = httpx.Client(
                base_url=os.getenv("API_BASE_URL"),
                event_hooks=get_api_logging_hooks()
            )
            yield client
            client.close()
            
        # Now all API calls automatically log to Allure
        def test_api(api_client):
            response = api_client.get("/health")  # Auto-logged
            assert response.status_code == 200
    """
    return {
        "request": [attach_api_request],
        "response": [attach_api_response]
    }


# ============================================================================
# JSON and Data Attachment Helpers
# ============================================================================


def attach_json_data(data: Dict[str, Any], name: str) -> None:
    """
    Attach JSON-formatted data to the Allure report.
    
    This function serializes Python dictionaries to pretty-printed JSON for
    readable Allure report attachments.
    
    Args:
        data: Dictionary to serialize and attach
        name: Name for the JSON attachment in Allure report
        
    Example:
        def test_with_payload(mcp_client):
            payload = mcp_client.build_payload("create_user", {"role": "admin"})
            attach_json_data(payload, "MCP Generated Payload")
            response = api_client.post("/users", json=payload)
    """
    try:
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        allure.attach(
            json_str,
            name=name,
            attachment_type=allure.attachment_type.JSON
        )
    except (TypeError, ValueError) as e:
        # Fallback to string representation if JSON serialization fails
        allure.attach(
            f"Failed to serialize as JSON: {str(e)}\n\nData: {str(data)}",
            name=f"{name} (Serialization Error)",
            attachment_type=allure.attachment_type.TEXT
        )


def attach_test_data(test_data: Dict[str, Any], prefix: str = "") -> None:
    """
    Attach test data used in test (e.g., from MCP) with automatic sensitive data sanitization.
    
    This function sanitizes sensitive fields (passwords, tokens, API keys) before
    attaching test data to Allure reports to prevent credential leakage.
    
    Args:
        test_data: Dictionary containing test data
        prefix: Optional prefix for the attachment name
        
    Example:
        def test_user_creation(mcp_client):
            user_data = mcp_client.seed_user(
                role="customer",
                email="test@example.com",
                password="SecurePass123"
            )
            attach_test_data(user_data, "Seeded User")
            # Password will be redacted in Allure report
    """
    # Sensitive field names to redact
    sensitive_fields = {'password', 'token', 'api_key', 'secret', 'auth', 
                       'authorization', 'bearer', 'api_secret', 'private_key'}
    
    # Sanitize sensitive data
    sanitized_data = {}
    for key, value in test_data.items():
        if key.lower() in sensitive_fields or any(s in key.lower() for s in sensitive_fields):
            sanitized_data[key] = "***REDACTED***"
        else:
            sanitized_data[key] = value
    
    # Attach sanitized data
    attachment_name = f"{prefix} Test Data" if prefix else "Test Data"
    attach_json_data(sanitized_data, name=attachment_name)


# ============================================================================
# Metadata Management Helpers
# ============================================================================


def add_test_labels(
    feature: Optional[str] = None,
    story: Optional[str] = None,
    severity: Optional[str] = None,
    **labels: str
) -> None:
    """
    Dynamically add Allure labels to a test at runtime.
    
    This function allows tests to programmatically set metadata for better
    organization in Allure reports. Useful for data-driven tests where metadata
    depends on test parameters.
    
    Args:
        feature: Feature name for grouping related tests
        story: User story or sub-feature name
        severity: Test severity (blocker, critical, normal, minor, trivial)
        **labels: Additional custom labels as keyword arguments
        
    Example:
        def test_user_workflow(user_role):
            add_test_labels(
                feature="User Management",
                story=f"{user_role} Workflow",
                severity="critical",
                test_type="integration"
            )
            # ... test implementation ...
    """
    try:
        if feature:
            allure.dynamic.feature(feature)
        if story:
            allure.dynamic.story(story)
        if severity:
            allure.dynamic.severity(severity)
        
        # Add custom labels
        for label_name, label_value in labels.items():
            allure.dynamic.label(label_name, str(label_value))
    except Exception as e:
        # Non-critical: log error but don't fail the test
        allure.attach(
            f"Failed to add test labels: {str(e)}",
            name="Label Addition Error",
            attachment_type=allure.attachment_type.TEXT
        )


def attach_environment_info(env_vars: Dict[str, str]) -> None:
    """
    Attach environment configuration to the test for reproducibility.
    
    This function captures key environment variables used during test execution,
    making it easier to reproduce test results in different environments.
    
    Args:
        env_vars: Dictionary of environment variable names and values
        
    Example:
        def test_configuration(page):
            import os
            env_info = {
                "BASE_URL": os.getenv("BASE_URL"),
                "HEADLESS": os.getenv("HEADLESS"),
                "BROWSER": page.context.browser.browser_type.name
            }
            attach_environment_info(env_info)
    """
    try:
        env_text = "\n".join([f"{key}: {value}" for key, value in env_vars.items()])
        allure.attach(
            env_text,
            name="Test Environment",
            attachment_type=allure.attachment_type.TEXT
        )
    except Exception as e:
        allure.attach(
            f"Failed to attach environment info: {str(e)}",
            name="Environment Info (Error)",
            attachment_type=allure.attachment_type.TEXT
        )


# ============================================================================
# Failure Diagnostic Helpers
# ============================================================================


def capture_failure_diagnostics(page: Page, test_name: str) -> None:
    """
    Comprehensive failure diagnostic capture for failed tests.
    
    This function captures all available diagnostic information when a test fails,
    including screenshot, page source, console logs, and current URL. Designed to
    be called from pytest hooks on test failure.
    
    Args:
        page: Playwright Page instance to capture diagnostics from
        test_name: Name of the failed test for labeling attachments
        
    Example:
        # In conftest.py:
        @pytest.hookimpl(tryfirst=True, hookwrapper=True)
        def pytest_runtest_makereport(item, call):
            outcome = yield
            rep = outcome.get_result()
            
            if rep.when == "call" and rep.failed:
                page = item.funcargs.get("page")
                if page:
                    from tests.helpers.allure_utils import capture_failure_diagnostics
                    capture_failure_diagnostics(page, item.name)
    """
    # Capture screenshot
    attach_screenshot(page, name=f"Failure Screenshot - {test_name}")
    
    # Capture page source
    attach_page_source(page, name=f"Page HTML - {test_name}")
    
    # Capture console logs
    attach_browser_console_logs(page)
    
    # Capture current URL
    try:
        current_url = page.url
        allure.attach(
            current_url,
            name="Current URL",
            attachment_type=allure.attachment_type.TEXT
        )
    except Exception as e:
        allure.attach(
            f"Failed to capture URL: {str(e)}",
            name="Current URL (Error)",
            attachment_type=allure.attachment_type.TEXT
        )


# ============================================================================
# Private Helper Functions
# ============================================================================


def _format_dict(d: Dict[str, Any], indent: str = "  ") -> str:
    """
    Format dictionary as multi-line indented text for readable attachments.
    
    Args:
        d: Dictionary to format
        indent: Indentation string for each line
        
    Returns:
        Formatted string representation
    """
    return "\n".join([f"{indent}{key}: {value}" for key, value in d.items()])
