"""
Gherkin Generation Package for Playwright MCP Server

This package provides functionality to convert Playwright MCP exploration session logs
into business-readable Gherkin BDD scenarios. It transforms low-level browser automation
actions (navigate, click, type, screenshot) into high-level Given/When/Then steps that
describe user behavior without implementation details.

Key Components:
    GherkinGenerator: Main class for converting exploration logs to .feature files
                     Uses LLM assistance (Ollama/OpenAI) or template-based fallback

Purpose:
    Enable LLM-assisted test authoring where AI agents explore web applications via
    the Playwright MCP server, then generate human-readable test scenarios for review
    and refinement by QA engineers and domain experts.

Integration Points:
    - mcp_servers/playwright_mcp/main.py: Playwright MCP server generate_gherkin endpoint
    - llm/client.py: LLM provider abstraction for scenario generation
    - llm/prompts/gherkin_generation.py: Expert-engineered prompts for Gherkin best practices
    - tests/features/: Target directory for approved generated scenarios

Per Technical Specification Section 0.7.2 "Gherkin Best Practices":
    - Generated scenarios are business-readable, focusing on WHAT not HOW
    - No CSS selectors, XPath expressions, or DOM coordinates in output
    - High-level steps using domain language stakeholders understand
    - Feature descriptions include business value statements

Per Technical Specification Section 0.7.8 "LLM-Generated Content Review":
    - All generated scenarios require human review before use
    - Generation metadata includes assumptions and open questions
    - Timestamp, model, and session tracking for audit trail

Usage Examples:
    Basic import and usage:
        >>> from mcp_servers.playwright_mcp.gherkin import GherkinGenerator
        >>> generator = GherkinGenerator()
        >>> 
        >>> exploration_log = [
        ...     {"action": "navigate", "details": {"url": "/login"}},
        ...     {"action": "type", "details": {"label": "Email", "value": "user@test.com"}},
        ...     {"action": "click", "details": {"text": "Sign In"}}
        ... ]
        >>> 
        >>> feature = await generator.generate_from_exploration(
        ...     feature_name="User Authentication",
        ...     exploration_goal="User logs in with valid credentials",
        ...     exploration_log=exploration_log,
        ...     session_id="session-abc123"
        ... )
        >>> print(feature)
    
    With LLM client:
        >>> from llm.client import get_llm_client
        >>> from mcp_servers.playwright_mcp.gherkin import GherkinGenerator
        >>> 
        >>> llm_client = get_llm_client()  # Uses LLM_PROVIDER env var
        >>> generator = GherkinGenerator(llm_client=llm_client)
        >>> 
        >>> feature = await generator.generate_from_exploration(
        ...     feature_name="Shopping Cart",
        ...     exploration_goal="User adds items to cart and checks out",
        ...     exploration_log=cart_exploration_log,
        ...     session_id="session-xyz789"
        ... )

Architecture Notes:
    This package is part of the development-only Playwright MCP server that enables
    LLM agents to explore web applications and generate test scenarios. It is NOT
    used in production CI/CD pipelines but rather supports test authoring workflows
    where humans review and approve AI-generated scenarios.
    
    The Playwright MCP server itself is optional and runs separately from the test
    execution framework (pytest + Playwright). Tests execute deterministically using
    pytest, while the Playwright MCP server assists in test discovery and authoring.

Module Structure:
    generator.py: GherkinGenerator class implementation with LLM integration
    __init__.py:  Package exports and documentation (this file)
"""

from mcp_servers.playwright_mcp.gherkin.generator import GherkinGenerator

# Public API exports
__all__ = [
    "GherkinGenerator",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Test Automation Framework"
__description__ = "Gherkin scenario generation from Playwright exploration logs"
