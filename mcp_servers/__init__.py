"""
MCP Servers Package

This package contains Model Context Protocol (MCP) server implementations
that support deterministic test execution and LLM-driven test exploration.

Modules:
    fastapi_mcp: FastAPI-based MCP server for test data management
                 Provides tools for: seed_user, build_payload, reset_env, query_state
                 Used in CI/CD pipelines for deterministic test data seeding
    
    playwright_mcp: Playwright-based MCP server for browser automation
                    Enables LLM agents to control browsers for exploratory testing
                    Used in development for test scenario discovery and Gherkin generation

Usage:
    from mcp_servers.fastapi_mcp import app as fastapi_app
    from mcp_servers.playwright_mcp import app as playwright_app

This package marker enables Python to recognize mcp_servers as a proper package,
allowing imports of submodules and supporting pytest test discovery.
"""
