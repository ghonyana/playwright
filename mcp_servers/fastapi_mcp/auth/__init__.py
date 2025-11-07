"""
Authentication Module for FastAPI MCP Server

This package provides bearer token authentication strategies for securing
Model Context Protocol (MCP) server endpoints. It exposes two authentication
functions that integrate with FastAPI's dependency injection system:

1. **validate_bearer_token**: Static bearer token validation
   - Simple string comparison against FASTAPI_MCP_TOKEN environment variable
   - Recommended for CI/CD pipelines and deterministic test execution
   - No expiration or complex claim management
   - Returns the validated token string

2. **verify_token**: JWT token verification with signature validation
   - Full JWT decoding using python-jose library
   - Supports expiration checks, claim extraction, and algorithm validation
   - Uses centralized auth_secret_key and auth_algorithm from config
   - Returns decoded payload dictionary with claims

Both functions follow FastAPI Depends() pattern for securing MCP tool endpoints
such as seed_user, build_payload, reset_env, and query_state. This prevents
unauthorized test data manipulation in shared test environments.

Package Structure:
    auth/
    ├── __init__.py          # This file - exports authentication functions
    └── bearer.py            # Implementation of validation functions

Usage Examples:
    # Import authentication functions from package namespace
    from mcp_servers.fastapi_mcp.auth import validate_bearer_token, verify_token
    
    # Use in FastAPI endpoint with dependency injection
    from fastapi import APIRouter, Depends
    
    router = APIRouter()
    
    @router.post("/tools/seed_user")
    async def seed_user(
        payload: dict,
        token: str = Depends(validate_bearer_token)  # Simple token auth
    ):
        # Only authenticated requests reach this code
        return {"status": "success"}
    
    @router.post("/tools/build_payload")
    async def build_payload(
        request: dict,
        token_payload: dict = Depends(verify_token)  # JWT auth with claims
    ):
        # Extract user information from JWT claims
        user_id = token_payload.get("sub")
        return {"user": user_id}

Integration with MCP Tool Routers:
    The functions exported from this package are designed to be used as FastAPI
    dependencies in mcp_servers/fastapi_mcp/routers/tools.py. Each MCP tool
    endpoint should include authentication to ensure:
    
    - Test data seeding is restricted to authorized test runners
    - Environment resets cannot be triggered by unauthorized users
    - Payload builders are only accessible to authenticated tests
    - State queries require valid credentials
    
    This security model is critical for multi-tenant test environments where
    multiple test suites share the same MCP server infrastructure.

Configuration Requirements:
    Static Token Authentication (validate_bearer_token):
        - FASTAPI_MCP_TOKEN environment variable must be set
        - Generate secure token with: openssl rand -hex 32
        - Store in GitHub Secrets or secure secrets management system
    
    JWT Authentication (verify_token):
        - AUTH_SECRET_KEY environment variable must be set (via config.py)
        - AUTH_ALGORITHM environment variable (default: HS256)
        - AUTH_TOKEN_EXPIRE_MINUTES (default: 60)

Security Considerations:
    - Never commit tokens or secret keys to version control
    - Use .env.example with placeholder values for documentation
    - Rotate tokens regularly in production environments
    - Implement rate limiting to prevent token brute-force attacks
    - Log authentication failures for security monitoring
    - Use HTTPS in production to prevent token interception

Architecture Alignment:
    This package follows the Agent Action Plan section 0.2.2 FastAPI MCP Server
    architecture, which specifies authentication as a critical security layer for
    deterministic test data management. The exported functions enable clean import
    paths and support the dependency injection pattern used throughout the FastAPI
    MCP server implementation.
"""

# Import authentication functions from bearer module
# These are re-exported at package level for clean import paths
from mcp_servers.fastapi_mcp.auth.bearer import (
    validate_bearer_token,
    verify_token,
)


# Public API - defines what's available when importing from this package
# Example: from mcp_servers.fastapi_mcp.auth import validate_bearer_token
__all__ = [
    "validate_bearer_token",
    "verify_token",
]
