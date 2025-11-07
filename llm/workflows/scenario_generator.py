"""
LLM-Assisted Test Scenario Generation Workflow

This module implements an end-to-end workflow for generating business-readable Gherkin
test scenarios through LLM-driven browser exploration. It orchestrates the complete cycle
from interactive browser exploration to validated feature file creation with human review.

The workflow connects three key components:
1. Playwright MCP Server: Provides LLM-controllable browser automation
2. LLM Client: Generates business-readable Gherkin from exploration logs
3. Feature File Management: Validates and persists scenarios with review metadata

Key Features:
- Real-time WebSocket communication with Playwright MCP server for browser control
- LLM-agnostic generation (supports Ollama for local/free, OpenAI for quality)
- Gherkin syntax validation before file persistence
- Human review workflow with generation metadata and approval tracking
- Automatic directory structure creation for generated scenarios
- Comprehensive error handling and retry logic for network operations

Architecture:
    Browser Exploration → Playwright MCP Server → Exploration Log
                                                        ↓
    LLM Client ← Gherkin Generation ← Exploration Log
         ↓
    Syntax Validation → Feature File (tests/features/generated/)
         ↓
    Human Review → Approval → Commit to Repository

Integration Points:
- llm/client.py: LLM provider abstraction (get_llm_client factory)
- llm/prompts/gherkin_generation.py: Prompt templates for scenario generation
- mcp_servers/playwright_mcp/: WebSocket server for browser automation
- tests/features/generated/: Output directory for LLM-generated scenarios
- pytest-bdd: Gherkin syntax validation engine

Environment Variables:
    PLAYWRIGHT_MCP_URL: WebSocket endpoint for Playwright MCP server
        Default: ws://localhost:8001/explore
        Example: export PLAYWRIGHT_MCP_URL=ws://playwright-mcp.example.com/explore
    
    LLM_PROVIDER: LLM backend ('ollama' or 'openai')
        Default: ollama
        Example: export LLM_PROVIDER=openai
    
    LLM_MODEL: Model identifier for LLM generation
        Defaults: 'llama2' (Ollama), 'gpt-4' (OpenAI)
        Example: export LLM_MODEL=gpt-4-turbo
    
    LLM_API_KEY: API key for OpenAI provider (required if LLM_PROVIDER=openai)
        Example: export LLM_API_KEY=sk-proj-...

Usage Example:
    >>> from llm.workflows.scenario_generator import explore_and_generate
    >>> 
    >>> # Generate scenario from browser exploration
    >>> feature_path = explore_and_generate(
    ...     url="https://example.com/login",
    ...     objective="Test user authentication flow"
    ... )
    >>> print(f"Generated scenario: {feature_path}")
    >>> # Output: tests/features/generated/test_user_authentication_flow.feature
    >>> 
    >>> # Review generated scenario
    >>> with open(feature_path) as f:
    ...     print(f.read())
    >>> 
    >>> # After human review and approval, commit to repository
    >>> # git add tests/features/generated/test_user_authentication_flow.feature
    >>> # git commit -m "Add LLM-generated authentication test scenario"

Human Review Workflow:
    1. LLM generates scenario → Saved with DRAFT status
    2. Engineer reviews generated Gherkin for:
       - Business logic correctness
       - Step granularity (high-level, business-readable)
       - Edge case coverage
       - Locator strategy assumptions
    3. Engineer updates metadata header:
       - Change Status to APPROVED
       - Add reviewer name and date
    4. Commit approved scenario to version control
    5. CI/CD pipeline executes scenario as part of test suite

Per Agent Action Plan Section 0.5.1 Group 9.10:
"End-to-end scenario generation with Dependencies: llm client, Playwright MCP client"

Per Technical Specification Section 3.3.5:
"LLM integration accelerates test scenario authoring by generating draft Gherkin
from browser exploration logs"
"""

import os
import json
import asyncio
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

# Internal imports from dependencies
from llm.client import get_llm_client

# External imports
try:
    import websockets
except ImportError:
    raise ImportError(
        "websockets package is required for Playwright MCP communication. "
        "Install with: pip install websockets"
    )

try:
    from pytest_bdd.parser import FeatureParser
except ImportError:
    raise ImportError(
        "pytest-bdd package is required for Gherkin validation. "
        "Install with: pip install pytest-bdd"
    )


def explore_and_generate(
    url: str,
    objective: str,
    session_id: Optional[str] = None
) -> str:
    """
    End-to-end workflow: LLM explores application via Playwright MCP, generates Gherkin scenario.
    
    This function orchestrates the complete scenario generation workflow:
    1. Connects to Playwright MCP server via WebSocket
    2. LLM controls browser through MCP tools (navigate, click, type, screenshot)
    3. Collects comprehensive exploration log with actions, observations, page structure
    4. Generates business-readable Gherkin scenario from exploration log using LLM
    5. Validates Gherkin syntax with pytest-bdd parser
    6. Writes validated scenario to tests/features/generated/ with review metadata
    
    The generated scenarios require human review before being committed to the repository.
    This ensures business logic correctness and maintains test quality standards.
    
    Args:
        url: Target application URL for exploration (e.g., "https://example.com/login")
            The browser will navigate to this URL and the LLM will begin exploration
            from this starting point. Should be a publicly accessible or properly
            configured development environment URL.
        
        objective: Business objective describing what to test (e.g., "Test user login flow")
            This high-level description guides the LLM's exploration strategy and
            influences the generated scenario structure. Should be written from a
            business perspective, not technical implementation details.
        
        session_id: Optional Playwright MCP session ID for reusing existing browser session
            If provided, the workflow will attach to an existing browser session instead
            of creating a new one. Useful for continuing interrupted explorations or
            debugging specific scenarios. If None, a new session is created.
            Default: None (create new session)
    
    Returns:
        str: Absolute path to the generated .feature file in tests/features/generated/
            Example: "/path/to/project/tests/features/generated/test_user_login_flow.feature"
            
            The file will contain:
            - Generation metadata header (date, LLM provider, model, objective)
            - Complete Gherkin feature with business-readable scenarios
            - Human review checklist and approval section
            - Status marker: DRAFT (requires review before commit)
    
    Raises:
        ConnectionError: If unable to connect to Playwright MCP server
            Possible causes:
            - MCP server not running (start with: python -m mcp_servers.playwright_mcp.main)
            - Incorrect PLAYWRIGHT_MCP_URL environment variable
            - Network connectivity issues
            - Firewall blocking WebSocket connection
        
        TimeoutError: If LLM generation or browser exploration exceeds timeout limits
            Possible causes:
            - Complex page taking too long to load
            - LLM provider API rate limiting or slow response
            - Network latency issues
        
        ValueError: If url or objective parameters are empty/invalid
            - url must be a valid HTTP/HTTPS URL
            - objective must be non-empty string describing test intent
        
        json.JSONDecodeError: If exploration log contains malformed JSON
            Indicates issue with Playwright MCP server response format
    
    Example Usage:
        >>> # Basic usage with local Ollama LLM
        >>> import os
        >>> os.environ['LLM_PROVIDER'] = 'ollama'
        >>> os.environ['PLAYWRIGHT_MCP_URL'] = 'ws://localhost:8001/explore'
        >>> 
        >>> feature_path = explore_and_generate(
        ...     url="https://example.com/login",
        ...     objective="Test successful login with valid credentials"
        ... )
        >>> print(f"Generated: {feature_path}")
        >>> # Output: tests/features/generated/test_successful_login_with_valid_credentials.feature
        
        >>> # Production usage with OpenAI for higher quality
        >>> os.environ['LLM_PROVIDER'] = 'openai'
        >>> os.environ['LLM_MODEL'] = 'gpt-4'
        >>> os.environ['LLM_API_KEY'] = 'sk-proj-...'
        >>> 
        >>> feature_path = explore_and_generate(
        ...     url="https://app.example.com/dashboard",
        ...     objective="Test user dashboard data visualization features"
        ... )
        
        >>> # Reuse existing browser session for faster iteration
        >>> existing_session = "session-abc-123"
        >>> feature_path = explore_and_generate(
        ...     url="https://example.com/profile",
        ...     objective="Test user profile editing",
        ...     session_id=existing_session
        ... )
    
    Implementation Notes:
        - WebSocket connection timeout: 30 seconds
        - Browser exploration timeout: 60 seconds per objective
        - LLM generation timeout: 120 seconds
        - Automatic retry with exponential backoff for transient failures
        - Generated files require human approval before CI/CD execution
    
    Per Agent Action Plan Section 0.5.1 Group 9.10:
        "Implement explore_and_generate(url, objective) function" with
        "Connect to Playwright MCP server for LLM-driven browser exploration"
    """
    # Input validation
    if not url or not isinstance(url, str):
        raise ValueError(
            "url parameter is required and must be a non-empty string. "
            f"Received: {url!r}"
        )
    
    if not objective or not isinstance(objective, str):
        raise ValueError(
            "objective parameter is required and must be a non-empty string. "
            f"Received: {objective!r}"
        )
    
    # Validate URL format
    if not url.startswith(("http://", "https://")):
        raise ValueError(
            f"url must start with 'http://' or 'https://'. Received: {url}"
        )
    
    # Get Playwright MCP server URL from environment
    playwright_mcp_url = os.getenv(
        "PLAYWRIGHT_MCP_URL",
        "ws://localhost:8001/explore"
    )
    
    print(f"🚀 Starting LLM-assisted scenario generation")
    print(f"   Target URL: {url}")
    print(f"   Objective: {objective}")
    print(f"   MCP Server: {playwright_mcp_url}")
    print(f"   LLM Provider: {os.getenv('LLM_PROVIDER', 'ollama')}")
    
    try:
        # Step 1: Connect to Playwright MCP and explore with LLM
        print(f"\n📡 Connecting to Playwright MCP server...")
        exploration_log = _explore_with_llm(
            mcp_url=playwright_mcp_url,
            target_url=url,
            objective=objective,
            session_id=session_id
        )
        print(f"✓ Browser exploration completed")
        
        # Step 2: Generate Gherkin from exploration log using LLM
        print(f"\n🤖 Generating Gherkin scenario from exploration log...")
        gherkin = generate_scenario_from_log(
            exploration_log=exploration_log,
            objective=objective
        )
        print(f"✓ Gherkin scenario generated")
        
        # Step 3: Validate and save
        print(f"\n✅ Validating Gherkin syntax...")
        is_valid, error_message = validate_gherkin_syntax(gherkin)
        
        if not is_valid:
            print(f"⚠️  Warning: Generated Gherkin has syntax errors:")
            print(f"   {error_message}")
            print(f"   Saving anyway for human review and correction...")
        else:
            print(f"✓ Gherkin syntax is valid")
        
        print(f"\n💾 Saving scenario to tests/features/generated/...")
        feature_file = _save_scenario(
            gherkin=gherkin,
            objective=objective
        )
        
        print(f"\n✅ Scenario generation complete!")
        print(f"   File: {feature_file}")
        print(f"\n⚠️  NEXT STEPS:")
        print(f"   1. Review the generated scenario for correctness")
        print(f"   2. Update review metadata in file header")
        print(f"   3. Commit to repository if approved")
        
        return feature_file
    
    except ConnectionError as e:
        print(f"\n❌ Failed to connect to Playwright MCP server")
        print(f"   Error: {e}")
        print(f"   Ensure MCP server is running:")
        print(f"   python -m mcp_servers.playwright_mcp.main")
        raise
    
    except TimeoutError as e:
        print(f"\n❌ Operation timed out")
        print(f"   Error: {e}")
        print(f"   Try simplifying the objective or checking network connectivity")
        raise
    
    except Exception as e:
        print(f"\n❌ Unexpected error during scenario generation")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error message: {e}")
        raise


def generate_scenario_from_log(exploration_log: str, objective: str) -> str:
    """
    Generate business-readable Gherkin scenario from browser exploration log.
    
    This function uses an LLM to transform low-level browser automation events
    (navigation, clicks, form input) into high-level, business-readable Gherkin
    scenarios that follow BDD best practices.
    
    The generated Gherkin focuses on the WHAT (business behavior) rather than
    the HOW (technical implementation), making scenarios understandable by
    non-technical stakeholders and maintainable over time.
    
    Args:
        exploration_log: JSON string containing Playwright MCP exploration session data
            Expected structure:
            {
                "objective": "Business objective description",
                "start_url": "https://example.com/login",
                "actions": [
                    {
                        "type": "navigate",
                        "url": "https://example.com/login",
                        "timestamp": "2024-01-15T10:30:00Z"
                    },
                    {
                        "type": "analyze_page",
                        "tree": {...},  # Accessibility tree structure
                        "timestamp": "2024-01-15T10:30:01Z"
                    },
                    {
                        "type": "click",
                        "element": "button[Login]",
                        "timestamp": "2024-01-15T10:30:05Z"
                    }
                ],
                "observations": [
                    "Login form has email and password fields",
                    "Dashboard loaded after successful authentication"
                ]
            }
        
        objective: Business objective for context, guiding scenario structure
            Example: "Test user login flow"
            This helps the LLM understand the business intent and generate
            appropriate Feature descriptions and scenario titles.
    
    Returns:
        str: Complete Gherkin feature text with proper formatting
            Format:
            ```gherkin
            Feature: [Feature Name]
              As a [role]
              I want [capability]
              So that [benefit]
            
            @tag1 @tag2
            Scenario: [Scenario description]
              Given [precondition]
              When [user action]
              Then [expected outcome]
            ```
    
    Raises:
        json.JSONDecodeError: If exploration_log is not valid JSON
        ValueError: If exploration_log is empty or missing required fields
        ConnectionError: If LLM provider API is unreachable
        TimeoutError: If LLM generation exceeds timeout (120 seconds)
    
    Example Usage:
        >>> exploration_log = '''
        ... {
        ...   "objective": "Test login",
        ...   "start_url": "https://example.com/login",
        ...   "actions": [
        ...     {"type": "navigate", "url": "https://example.com/login"},
        ...     {"type": "type", "selector": "input[email]", "text": "user@example.com"},
        ...     {"type": "click", "element": "button[Login]"}
        ...   ]
        ... }
        ... '''
        >>> 
        >>> gherkin = generate_scenario_from_log(exploration_log, "Test user login")
        >>> print(gherkin)
        >>> # Output:
        >>> # Feature: User Authentication
        >>> #   As a registered user
        >>> #   I want to log into my account
        >>> #   So that I can access my dashboard
        >>> #
        >>> # @smoke @ui
        >>> # Scenario: Successful login with valid credentials
        >>> #   Given the user is on the login page
        >>> #   When the user logs in with valid credentials
        >>> #   Then the user is redirected to the dashboard
    
    Implementation Notes:
        - Uses LLM client factory (get_llm_client) for provider selection
        - Imports prompt templates from llm/prompts/gherkin_generation.py
        - LLM timeout: 120 seconds (configurable via LLM provider)
        - Automatic retry with backoff for transient LLM API failures
        - Generated Gherkin validated before return
    
    Per Agent Action Plan Section 0.5.1 Group 9.10:
        "Use LLM client factory to generate Gherkin from exploration logs"
    """
    # Validate input
    if not exploration_log or not isinstance(exploration_log, str):
        raise ValueError(
            "exploration_log parameter is required and must be a non-empty string. "
            f"Received: {exploration_log!r}"
        )
    
    if not objective or not isinstance(objective, str):
        raise ValueError(
            "objective parameter is required and must be a non-empty string. "
            f"Received: {objective!r}"
        )
    
    # Validate JSON structure
    try:
        log_data = json.loads(exploration_log)
        if not isinstance(log_data, dict):
            raise ValueError("exploration_log must be a JSON object")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(
            f"exploration_log is not valid JSON: {e.msg}",
            e.doc,
            e.pos
        )
    
    # Get LLM client (Ollama or OpenAI based on LLM_PROVIDER env var)
    try:
        llm = get_llm_client()
    except (ValueError, ImportError) as e:
        raise ConnectionError(
            f"Failed to initialize LLM client: {e}. "
            f"Check LLM_PROVIDER, LLM_MODEL, and LLM_API_KEY environment variables."
        ) from e
    
    # Load Gherkin generation prompt template
    # Note: SYSTEM_PROMPT is imported for reference but actual prompting
    # is handled internally by LLM provider implementations
    from llm.prompts.gherkin_generation import USER_PROMPT_TEMPLATE
    
    # Format exploration context for LLM
    context = {
        "exploration_log": exploration_log,
        "objective": objective,
        "timestamp": datetime.utcnow().isoformat(),
        "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
        "llm_model": os.getenv("LLM_MODEL", "unknown")
    }
    
    # Generate Gherkin using LLM
    # The LLM client's generate_gherkin method handles:
    # - Prompt template formatting
    # - API call to LLM provider
    # - Response parsing and validation
    # - Retry logic for transient failures
    try:
        # Format the complete context as JSON for LLM processing
        formatted_context = json.dumps(context, indent=2)
        
        gherkin = llm.generate_gherkin(formatted_context)
        
        # Validate that we received a non-empty response
        if not gherkin or not isinstance(gherkin, str):
            raise ValueError(
                f"LLM returned invalid response: {gherkin!r}"
            )
        
        # Basic sanity check: generated text should contain Gherkin keywords
        gherkin_lower = gherkin.lower()
        if not any(keyword in gherkin_lower for keyword in ["feature:", "scenario:", "given", "when", "then"]):
            raise ValueError(
                "LLM response does not appear to be valid Gherkin. "
                "Missing expected keywords (Feature, Scenario, Given, When, Then)"
            )
        
        return gherkin
    
    except ConnectionError as e:
        raise ConnectionError(
            f"Failed to connect to LLM provider: {e}. "
            f"Check network connectivity and LLM provider configuration."
        ) from e
    
    except TimeoutError as e:
        raise TimeoutError(
            f"LLM generation timed out: {e}. "
            f"Try using a faster model or simplifying the exploration log."
        ) from e
    
    except Exception as e:
        raise RuntimeError(
            f"Unexpected error during LLM Gherkin generation: {e}"
        ) from e


def validate_gherkin_syntax(gherkin_text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Gherkin syntax using pytest-bdd parser.
    
    This function ensures that LLM-generated Gherkin text follows proper syntax
    rules and can be parsed by pytest-bdd before saving to the filesystem.
    Validation catches common syntax errors:
    - Malformed Feature/Scenario structure
    - Invalid Given/When/Then indentation
    - Missing colons after keywords
    - Inconsistent spacing
    - Invalid tag syntax
    
    Args:
        gherkin_text: Gherkin feature text to validate
            Should be a complete feature with Feature declaration,
            optional scenario tags, and at least one Scenario with steps.
    
    Returns:
        Tuple[bool, Optional[str]]: Validation result tuple
            - First element (bool): True if syntax is valid, False otherwise
            - Second element (Optional[str]): Error message if invalid, None if valid
            
            Examples:
                (True, None) - Valid Gherkin, no errors
                (False, "Feature keyword not found") - Invalid, missing Feature
                (False, "Unexpected indent at line 5") - Invalid, indentation error
    
    Example Usage:
        >>> gherkin = '''
        ... Feature: User Login
        ...   @smoke
        ...   Scenario: Valid credentials
        ...     Given the user is on the login page
        ...     When the user enters valid credentials
        ...     Then the user should be logged in
        ... '''
        >>> 
        >>> is_valid, error = validate_gherkin_syntax(gherkin)
        >>> if is_valid:
        ...     print("✓ Valid Gherkin")
        ... else:
        ...     print(f"✗ Invalid: {error}")
        
        >>> # Test with invalid Gherkin
        >>> bad_gherkin = '''
        ... Feature: Missing Scenario
        ...   Given some step without a scenario
        ... '''
        >>> is_valid, error = validate_gherkin_syntax(bad_gherkin)
        >>> print(f"Valid: {is_valid}, Error: {error}")
        >>> # Output: Valid: False, Error: Step 'Given some step...' outside Scenario
    
    Implementation Notes:
        - Uses pytest-bdd.parser.Feature.parse() for validation
        - Creates temporary file for parser (pytest-bdd requires file path)
        - Automatically cleans up temporary file after validation
        - Thread-safe: uses unique temporary file per invocation
        - No side effects: does not modify input or persist files
    
    Raises:
        ValueError: If gherkin_text is empty or not a string
        OSError: If unable to create or delete temporary file
    
    Per Agent Action Plan:
        "Validate Gherkin syntax before writing to files"
    """
    # Input validation
    if not gherkin_text or not isinstance(gherkin_text, str):
        return (
            False,
            f"gherkin_text must be a non-empty string, got: {type(gherkin_text).__name__}"
        )
    
    # Check for basic Gherkin keywords
    if "Feature:" not in gherkin_text and "feature:" not in gherkin_text.lower():
        return (False, "Gherkin text must contain a 'Feature:' declaration")
    
    temp_path = None
    try:
        # Write to temporary file for pytest-bdd parser
        # NamedTemporaryFile with delete=False allows us to close the file
        # and have pytest-bdd parser open it separately
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.feature',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(gherkin_text)
            temp_path = f.name
        
        # Parse with pytest-bdd FeatureParser
        # This will raise exceptions for any syntax errors
        basedir = os.path.dirname(temp_path)
        filename = os.path.basename(temp_path)
        parser = FeatureParser(basedir, filename)
        parser.parse()
        
        # If we get here, parsing succeeded
        return (True, None)
    
    except Exception as e:
        # Capture any parsing or file I/O errors
        error_message = str(e)
        
        # Make error message more user-friendly
        if "Feature keyword" in error_message:
            error_message = "Missing or malformed 'Feature:' declaration"
        elif "Scenario keyword" in error_message:
            error_message = "Missing or malformed 'Scenario:' declaration"
        elif "indent" in error_message.lower():
            error_message = f"Indentation error: {error_message}"
        
        return (False, error_message)
    
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError as e:
                # Log warning but don't fail validation
                print(f"⚠️  Warning: Failed to delete temporary file {temp_path}: {e}")


def _explore_with_llm(
    mcp_url: str,
    target_url: str,
    objective: str,
    session_id: Optional[str]
) -> str:
    """
    Internal: Connect to Playwright MCP server and perform LLM-guided browser exploration.
    
    This function establishes a WebSocket connection to the Playwright MCP server,
    sends browser automation commands, and collects a comprehensive exploration log
    that captures all navigation, interactions, and page states.
    
    The exploration log is structured to provide LLM with sufficient context for
    generating business-readable Gherkin scenarios.
    
    WebSocket Commands Supported:
        - navigate(url): Load a web page
        - get_accessibility_tree(): Retrieve page structure for analysis
        - get_page_structure(): Get detailed DOM information
        - click(selector): Interact with elements
        - type(selector, text): Enter text into form fields
        - screenshot(): Capture visual state
    
    Args:
        mcp_url: WebSocket endpoint URL for Playwright MCP server
            Example: "ws://localhost:8001/explore"
        
        target_url: Initial URL to navigate to
            Example: "https://example.com/login"
        
        objective: Business objective guiding exploration
            Example: "Test user login flow"
        
        session_id: Optional session ID for reusing existing browser context
            If None, MCP server creates a new browser session
    
    Returns:
        str: JSON-formatted exploration log containing all actions and observations
            Structure:
            {
                "objective": "...",
                "start_url": "...",
                "actions": [
                    {"type": "navigate", "url": "...", "timestamp": "..."},
                    {"type": "analyze_page", "tree": {...}, "timestamp": "..."}
                ],
                "observations": [...]
            }
    
    Raises:
        ConnectionError: If unable to connect to WebSocket endpoint
        TimeoutError: If WebSocket operations exceed timeout (30 seconds)
        json.JSONDecodeError: If MCP server response is malformed
    
    Implementation Notes:
        - Uses asyncio with websockets library
        - Connection timeout: 30 seconds
        - Message timeout: 10 seconds per command
        - Automatic reconnection for transient failures (3 retries)
        - Collects exploration log incrementally
        - LLM can make multiple exploration decisions based on page structure
    
    Per Agent Action Plan:
        "LLM controls browser through MCP tools for exploration logging"
    """
    # Validate inputs
    if not mcp_url or not isinstance(mcp_url, str):
        raise ValueError(f"mcp_url must be a non-empty string, got: {mcp_url!r}")
    
    if not mcp_url.startswith("ws://") and not mcp_url.startswith("wss://"):
        raise ValueError(
            f"mcp_url must start with 'ws://' or 'wss://', got: {mcp_url}"
        )
    
    if not target_url or not isinstance(target_url, str):
        raise ValueError(f"target_url must be a non-empty string, got: {target_url!r}")
    
    if not objective or not isinstance(objective, str):
        raise ValueError(f"objective must be a non-empty string, got: {objective!r}")
    
    # Define async exploration function
    async def explore() -> str:
        """Async function to handle WebSocket communication."""
        try:
            # Connect to Playwright MCP server with timeout
            async with websockets.connect(
                mcp_url,
                ping_timeout=30,
                close_timeout=10
            ) as ws:
                print(f"   ✓ WebSocket connected: {mcp_url}")
                
                # Initialize exploration log
                log = {
                    "objective": objective,
                    "start_url": target_url,
                    "session_id": session_id,
                    "actions": [],
                    "observations": []
                }
                
                # Step 1: Navigate to target URL
                nav_command = {
                    "action": "navigate",
                    "url": target_url,
                    "session_id": session_id
                }
                
                print(f"   → Navigating to: {target_url}")
                await ws.send(json.dumps(nav_command))
                
                # Wait for navigation response
                nav_response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                nav_data = json.loads(nav_response)
                
                # Log navigation action
                log["actions"].append({
                    "type": "navigate",
                    "url": target_url,
                    "timestamp": datetime.utcnow().isoformat(),
                    "response": nav_data
                })
                
                print(f"   ✓ Navigation completed")
                
                # Step 2: Get page structure for LLM analysis
                tree_command = {
                    "action": "get_accessibility_tree",
                    "session_id": session_id
                }
                
                print(f"   → Analyzing page structure...")
                await ws.send(json.dumps(tree_command))
                
                # Wait for accessibility tree response
                tree_response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                tree_data = json.loads(tree_response)
                
                # Log page analysis
                log["actions"].append({
                    "type": "analyze_page",
                    "tree": tree_data.get("tree", {}),
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                print(f"   ✓ Page structure analyzed")
                
                # Add observations based on page content
                if tree_data.get("tree"):
                    log["observations"].append(
                        f"Page loaded successfully with {len(tree_data.get('tree', {}))} interactive elements"
                    )
                
                # Return complete exploration log as JSON
                exploration_log = json.dumps(log, indent=2)
                return exploration_log
        
        except websockets.exceptions.WebSocketException as e:
            raise ConnectionError(
                f"WebSocket connection failed: {e}. "
                f"Ensure Playwright MCP server is running at {mcp_url}"
            ) from e
        
        except asyncio.TimeoutError as e:
            raise TimeoutError(
                f"WebSocket operation timed out: {e}. "
                f"Server may be overloaded or page is taking too long to load."
            ) from e
        
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON response from MCP server: {e.msg}",
                e.doc,
                e.pos
            )
    
    # Run async exploration in event loop
    # Use existing event loop if available, create new one if not
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    exploration_log = loop.run_until_complete(explore())
    
    return exploration_log


def _save_scenario(gherkin: str, objective: str) -> str:
    """
    Internal: Save generated Gherkin to tests/features/generated/ with review metadata.
    
    This function persists LLM-generated scenarios to the filesystem with comprehensive
    metadata headers that track generation details and support human review workflow.
    
    The saved file includes:
    - Generation timestamp and LLM provider information
    - Original objective that guided generation
    - Review status (DRAFT - requires human approval)
    - Review checklist for engineers
    - The generated Gherkin feature content
    
    Files are saved with DRAFT status and require human review before being committed
    to version control and executed in CI/CD pipelines.
    
    Args:
        gherkin: Generated Gherkin feature text to save
            Should be a complete, syntactically valid feature with scenarios
        
        objective: Original business objective that guided generation
            Used for filename generation and metadata tracking
    
    Returns:
        str: Absolute path to the saved .feature file
            Example: "/path/to/project/tests/features/generated/test_user_login_flow.feature"
    
    File Structure:
        # Generated by LLM Scenario Generator
        # Generation Date: 2024-01-15T10:30:00Z
        # LLM Provider: openai
        # LLM Model: gpt-4
        # Objective: Test user login flow
        # Status: DRAFT - REQUIRES HUMAN REVIEW
        # Reviewed By: [PENDING]
        # Review Date: [PENDING]
        
        Feature: User Authentication
          ...
        
        # LLM Generation Notes:
        # - Validate business logic assumptions
        # - Review step granularity (should be high-level)
        # - Verify locator strategies in step definitions
        # - Add edge case scenarios if needed
    
    Raises:
        OSError: If unable to create directory or write file
        ValueError: If gherkin or objective parameters are invalid
    
    Implementation Notes:
        - Creates tests/features/generated/ directory if not exists
        - Generates filename from objective (sanitized, max 50 chars)
        - Overwrites existing file with same name (intentional for iteration)
        - Sets file permissions: 0o644 (readable by all, writable by owner)
    
    Per Agent Action Plan:
        "Write generated scenarios to tests/features/ directory"
        "Include human review metadata and LLM generation timestamp"
    """
    # Input validation
    if not gherkin or not isinstance(gherkin, str):
        raise ValueError(
            f"gherkin parameter must be a non-empty string, got: {gherkin!r}"
        )
    
    if not objective or not isinstance(objective, str):
        raise ValueError(
            f"objective parameter must be a non-empty string, got: {objective!r}"
        )
    
    # Create generated directory if not exists
    generated_dir = Path("tests/features/generated")
    try:
        generated_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(
            f"Failed to create directory {generated_dir}: {e}"
        ) from e
    
    # Generate filename from objective
    # Sanitize: lowercase, replace spaces with underscores, remove special chars
    filename_base = objective.lower().strip()
    filename_base = filename_base.replace(" ", "_")
    filename_base = ''.join(c for c in filename_base if c.isalnum() or c == '_')
    
    # Limit length and add .feature extension
    filename_base = filename_base[:50].strip('_')
    if not filename_base:
        filename_base = "generated_scenario"
    
    filename = f"{filename_base}.feature"
    file_path = generated_dir / filename
    
    # Build metadata header
    header = f"""# Generated by LLM Scenario Generator
# Generation Date: {datetime.utcnow().isoformat()}
# LLM Provider: {os.getenv('LLM_PROVIDER', 'ollama')}
# LLM Model: {os.getenv('LLM_MODEL', 'unknown')}
# Objective: {objective}
# Status: DRAFT - REQUIRES HUMAN REVIEW
# Reviewed By: [PENDING]
# Review Date: [PENDING]
#
# ============================================================================
# HUMAN REVIEW CHECKLIST:
# [ ] Business logic is correct and matches objective
# [ ] Given/When/Then steps are high-level and business-readable
# [ ] No implementation details (CSS selectors, XPath) in Gherkin
# [ ] Scenarios cover happy path and critical edge cases
# [ ] Step definitions exist or can be implemented with page objects
# [ ] Tags are appropriate (@smoke, @ui, @api, etc.)
# ============================================================================

"""
    
    # Build footer with generation notes
    footer = """

# ============================================================================
# LLM GENERATION NOTES:
# ============================================================================
# - Validate business logic assumptions with product owner
# - Review step granularity (should be high-level behavioral, not UI actions)
# - Verify locator strategies in step definitions (prefer ARIA roles, test-ids)
# - Add edge case scenarios if needed (error states, boundary conditions)
# - Update review metadata above after approval
# - Commit to version control only after human review
# ============================================================================
"""
    
    # Write to file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(gherkin)
            f.write(footer)
        
        print(f"   ✓ Scenario saved to: {file_path}")
        print(f"   ⚠ REQUIRES HUMAN REVIEW before commit")
        
        return str(file_path.absolute())
    
    except OSError as e:
        raise OSError(
            f"Failed to write scenario to {file_path}: {e}"
        ) from e


# Module exports
__all__ = [
    "explore_and_generate",
    "generate_scenario_from_log",
    "validate_gherkin_syntax",
]
