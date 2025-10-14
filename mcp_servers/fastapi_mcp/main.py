"""
FastAPI MCP Server - Application Entry Point

This module provides the main FastAPI application for the Model Context Protocol
(MCP) server, which enables deterministic test data management for the pytest
automation framework.

The server exposes JSON-RPC style endpoints for:
- Test user creation with specific roles and attributes
- API request payload generation from templates
- Test environment state reset and management
- Environment state querying for debugging and verification

This server is designed to run alongside pytest tests in both local development
and CI/CD environments to ensure tests start from known-good states and remain
deterministic, isolated, and parallel-friendly.

Usage:
    # Development mode with auto-reload
    python -m mcp_servers.fastapi_mcp.main
    
    # Production mode
    uvicorn mcp_servers.fastapi_mcp.main:app --host 0.0.0.0 --port 8001
    
    # Docker/CI environment
    uvicorn mcp_servers.fastapi_mcp.main:app --host 0.0.0.0 --port 8001 --workers 4
"""

import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import configuration
from mcp_servers.fastapi_mcp.config import Settings

# Import routers
from mcp_servers.fastapi_mcp.routers import health
from mcp_servers.fastapi_mcp.routers import tools

# Initialize settings
settings = Settings()

# ============================================================================
# FASTAPI APPLICATION INITIALIZATION
# ============================================================================

app = FastAPI(
    title="FastAPI MCP Server",
    description="Deterministic test data management for pytest automation framework",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ============================================================================
# CORS MIDDLEWARE CONFIGURATION
# ============================================================================

# Configure CORS to allow test framework access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for test environment
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# ============================================================================
# ROUTER REGISTRATION
# ============================================================================

# Register health check endpoints
app.include_router(health.router)

# Register MCP tool endpoints
app.include_router(tools.router)

# ============================================================================
# LIFECYCLE EVENT HANDLERS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    
    Performs initialization tasks when the server starts:
    - Log server configuration
    - Initialize database connections (if configured)
    - Warm up caches
    - Verify target application connectivity
    """
    print("=" * 80)
    print("FastAPI MCP Server Starting")
    print("=" * 80)
    print(f"Server URL: {settings.get_server_url()}")
    print(f"Target App Base URL: {settings.app_base_url}")
    print(f"Target API URL: {settings.app_api_url}")
    print(f"Admin configured: {settings.is_admin_configured()}")
    
    if settings.database_url:
        print(f"Database: {settings.database_url}")
    else:
        print("Database: In-memory (no persistence)")
    
    print("=" * 80)
    print("MCP Tools Available:")
    print("  - POST /tools/seed_user      : Create test users")
    print("  - POST /tools/build_payload  : Generate API payloads")
    print("  - POST /tools/reset_env      : Reset environment")
    print("  - POST /tools/query_state    : Query environment state")
    print("=" * 80)
    print("Documentation:")
    print(f"  - OpenAPI Docs: {settings.get_server_url()}/docs")
    print(f"  - ReDoc: {settings.get_server_url()}/redoc")
    print("=" * 80)


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    
    Performs cleanup tasks when the server stops:
    - Close database connections
    - Flush logs
    - Release resources
    """
    print("=" * 80)
    print("FastAPI MCP Server Shutting Down")
    print("=" * 80)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint providing server information.
    
    Returns:
        Server metadata and available endpoints
    """
    return {
        "name": "FastAPI MCP Server",
        "version": "1.0.0",
        "description": "Model Context Protocol server for deterministic test data management",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "tools": "/tools",
            "docs": "/docs",
            "redoc": "/redoc"
        },
        "mcp_tools": [
            "seed_user",
            "build_payload",
            "reset_env",
            "query_state"
        ]
    }


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Development server entry point.
    
    Runs uvicorn with settings from configuration. For production use,
    run uvicorn directly with appropriate workers and configuration.
    """
    uvicorn.run(
        "mcp_servers.fastapi_mcp.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info"
    )
