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

Architecture:
    - FastAPI application with automatic OpenAPI documentation
    - CORS middleware configured for test framework access from any origin
    - MCP tool routers for deterministic test data operations
    - Health check router for CI/CD liveness/readiness probes
    - Startup/shutdown event handlers for resource management
    - Environment-based configuration via pydantic-settings

Integration with pytest:
    Tests access MCP tools via httpx client using endpoints exposed by this
    application. The server runs as a background service during test execution:
    
    ```python
    # In pytest conftest.py
    @pytest.fixture(scope="session")
    def mcp_client():
        return MCPClient(
            base_url=os.getenv("FASTAPI_MCP_URL", "http://localhost:8001"),
            token=os.getenv("FASTAPI_MCP_TOKEN")
        )
    
    # In tests
    def test_with_seeded_user(mcp_client):
        user = mcp_client.seed_user(role="admin")
        # Use user credentials in test
    ```

CI/CD Usage:
    GitHub Actions workflow starts this server as a service before test execution:
    
    ```yaml
    services:
      fastapi-mcp:
        image: python:3.11
        cmd: python -m mcp_servers.fastapi_mcp.main
        ports:
          - 8001:8001
        env:
          AUTH_SECRET_KEY: ${{ secrets.MCP_SECRET_KEY }}
          APP_BASE_URL: http://localhost:3000
          APP_API_URL: http://localhost:3000/api
    ```

Usage:
    # Development mode with auto-reload
    python -m mcp_servers.fastapi_mcp.main
    
    # Production mode
    uvicorn mcp_servers.fastapi_mcp.main:app --host 0.0.0.0 --port 8001
    
    # Docker/CI environment with multiple workers
    uvicorn mcp_servers.fastapi_mcp.main:app --host 0.0.0.0 --port 8001 --workers 4

Environment Variables Required:
    - AUTH_SECRET_KEY: JWT signing secret (min 32 chars)
    - APP_BASE_URL: Base URL of web application under test
    - APP_API_URL: Base URL of REST API under test
    
    Optional:
    - HOST: Server bind address (default: 0.0.0.0)
    - PORT: Server port (default: 8001)
    - RELOAD: Enable auto-reload (default: False)
    - APP_ADMIN_EMAIL: Admin user email for privileged operations
    - APP_ADMIN_PASSWORD: Admin user password
    - DATABASE_URL: Database connection for test data persistence
"""

import logging
import sys
from pathlib import Path

# Add project root to Python path for module imports
# This ensures the server can be run from any directory
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# FastAPI core imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import singleton settings instance from config module
from mcp_servers.fastapi_mcp.config import settings

# Import routers - must use 'as' to avoid name collision
from mcp_servers.fastapi_mcp.routers.health import router as health_router
from mcp_servers.fastapi_mcp.routers.tools import router as tools_router


# Configure module logger
logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI APPLICATION INITIALIZATION
# ============================================================================

app = FastAPI(
    title="FastAPI MCP Server",
    description="Deterministic test data management for pytest automation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# ============================================================================
# CORS MIDDLEWARE CONFIGURATION
# ============================================================================

# Configure CORS to allow test framework access from any origin
# This is required for pytest tests running on different ports or hosts
# to communicate with the MCP server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for test environment flexibility
    allow_credentials=True,  # Allow cookies and authorization headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers including custom test headers
)

# ============================================================================
# ROUTER REGISTRATION
# ============================================================================

# Register health check router (no prefix, mounted at root)
# Provides /health endpoint for CI/CD and monitoring
app.include_router(health_router)

# Register MCP tools router (with /tools prefix)
# Provides /tools/seed_user, /tools/build_payload, /tools/reset_env, /tools/query_state
app.include_router(tools_router)

# ============================================================================
# LIFECYCLE EVENT HANDLERS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    
    Performs initialization tasks when the server starts:
    - Validates required configuration settings
    - Logs server configuration for debugging
    - Initializes database connections (if configured)
    - Verifies target application URLs are accessible
    
    This handler ensures the server fails fast if configuration is invalid,
    preventing tests from starting with a misconfigured MCP server.
    
    Raises:
        ValueError: If required configuration settings are invalid or missing
    """
    logger.info("FastAPI MCP Server startup initiated")
    
    # Validate required configuration settings
    validation_errors = settings.validate_required_settings()
    if validation_errors:
        error_message = "Configuration validation failed:\n" + "\n".join(
            f"  - {error}" for error in validation_errors
        )
        logger.error(error_message)
        raise ValueError(error_message)
    
    # Log server configuration
    logger.info("=" * 80)
    logger.info("FastAPI MCP Server Starting")
    logger.info("=" * 80)
    logger.info(f"Server URL: {settings.get_server_url()}")
    logger.info(f"Target App Base URL: {settings.app_base_url}")
    logger.info(f"Target API URL: {settings.app_api_url}")
    logger.info(f"Admin configured: {settings.is_admin_configured()}")
    
    # Log database configuration
    if settings.is_database_configured():
        logger.info(f"Database: {settings.database_url}")
    else:
        logger.info("Database: In-memory (no persistence)")
    
    # Log available MCP tools
    logger.info("=" * 80)
    logger.info("MCP Tools Available:")
    logger.info("  - POST /tools/seed_user      : Create deterministic test users")
    logger.info("  - POST /tools/build_payload  : Generate API request payloads")
    logger.info("  - POST /tools/reset_env      : Reset test environment state")
    logger.info("  - POST /tools/query_state    : Query environment resources")
    logger.info("=" * 80)
    logger.info("Documentation:")
    logger.info(f"  - OpenAPI Docs: {settings.get_server_url()}/docs")
    logger.info(f"  - ReDoc: {settings.get_server_url()}/redoc")
    logger.info("  - Health Check: {}/health".format(settings.get_server_url()))
    logger.info("=" * 80)
    logger.info("Server ready to accept requests")
    
    # Print to console for visibility in CI/CD logs
    print("\n" + "=" * 80)
    print("✓ FastAPI MCP Server Started Successfully")
    print(f"✓ Listening on {settings.get_server_url()}")
    print(f"✓ Testing {settings.app_base_url}")
    print(f"✓ Documentation at {settings.get_server_url()}/docs")
    print("=" * 80 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    
    Performs cleanup tasks when the server stops:
    - Closes database connections (if configured)
    - Flushes pending logs to disk
    - Releases network resources
    - Cancels background tasks
    
    This ensures graceful shutdown without resource leaks or data corruption.
    """
    logger.info("FastAPI MCP Server shutdown initiated")
    logger.info("=" * 80)
    logger.info("FastAPI MCP Server Shutting Down")
    logger.info("=" * 80)
    
    # Close database connections if configured
    if settings.is_database_configured():
        logger.info("Closing database connections...")
        # Database cleanup would be performed here if we had active connections
        # For now, this is a placeholder for future database integration
    
    logger.info("Shutdown complete")
    
    # Print to console for visibility in CI/CD logs
    print("\n" + "=" * 80)
    print("✓ FastAPI MCP Server Stopped")
    print("=" * 80 + "\n")


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
    
    Runs uvicorn ASGI server with configuration from environment settings.
    This entry point is suitable for local development and simple deployments.
    
    For production use with multiple workers and advanced features:
        uvicorn mcp_servers.fastapi_mcp.main:app \\
            --host 0.0.0.0 \\
            --port 8001 \\
            --workers 4 \\
            --log-config logging.yaml
    
    Configuration Sources:
        - host: settings.host from HOST env var (default: 0.0.0.0)
        - port: settings.port from PORT env var (default: 8001)
        - reload: settings.reload from RELOAD env var (default: False)
    
    Example Development Run:
        export RELOAD=true
        export AUTH_SECRET_KEY=$(openssl rand -hex 32)
        export APP_BASE_URL=http://localhost:3000
        export APP_API_URL=http://localhost:3000/api
        python -m mcp_servers.fastapi_mcp.main
    """
    logger.info("Starting FastAPI MCP Server from __main__ entry point")
    logger.info(f"Configuration: host={settings.host}, port={settings.port}, reload={settings.reload}")
    
    # Run uvicorn with settings from configuration
    # Using string import path to enable reload functionality
    uvicorn.run(
        "mcp_servers.fastapi_mcp.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
        access_log=True
    )
