"""Playwright MCP Server Module.

This package provides a Model Context Protocol (MCP) server that enables LLM agents
to control Playwright browsers for exploratory testing and automated Gherkin scenario
generation.

Key Components:
    - main.py: MCP server entry point and FastAPI application
    - config.py: Server configuration and environment settings
    - models.py: Pydantic models for MCP tool requests and responses
    - tools/: Browser automation tool implementations (navigation, interaction, capture)
    - session/: Browser session lifecycle management
    - gherkin/: Gherkin scenario generation from exploration sessions

Usage:
    # Import the main server application
    from mcp_servers.playwright_mcp import main
    
    # Import specific models
    from mcp_servers.playwright_mcp.models import NavigateRequest, ClickRequest
    
    # Import tool implementations
    from mcp_servers.playwright_mcp.tools import navigation, interaction

Note:
    This is a development-only MCP server. It should NOT be started in CI/CD
    pipelines unless explicitly required for specific test scenarios. The FastAPI
    MCP server handles deterministic test data management in production/CI environments.

Architecture:
    This module intentionally keeps __init__.py minimal to avoid circular import
    issues. All exports are defined in their respective component files, and imports
    should be explicit (e.g., 'from mcp_servers.playwright_mcp.main import app'
    rather than 'from mcp_servers.playwright_mcp import app').
"""
