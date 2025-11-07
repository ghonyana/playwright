"""
FastAPI MCP Server - Routers Package

This package contains FastAPI router modules for the MCP (Model Context Protocol) server.

Routers:
    - tools: JSON-RPC endpoints for MCP tool operations (seed_user, build_payload, reset_env, query_state)
    - health: Health check and status endpoints for service monitoring

Usage:
    from mcp_servers.fastapi_mcp.routers import tools, health
    
    app = FastAPI()
    app.include_router(tools.router)
    app.include_router(health.router)
"""
