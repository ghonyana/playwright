"""
Bearer Token Authentication for FastAPI MCP Server

This module implements two authentication strategies for securing the FastAPI
Model Context Protocol (MCP) server endpoints:

1. **Static Bearer Token Validation** (Primary - Production/CI):
   - Simple token comparison against FASTAPI_MCP_TOKEN environment variable
   - Recommended for deterministic test execution in CI/CD pipelines
   - No token expiration or complex claim management
   - Suitable for pytest test runners with pre-shared secrets

2. **JWT Token Verification** (Secondary - Advanced Scenarios):
   - Full JWT decoding with signature verification using python-jose
   - Supports token expiration, claims extraction, and algorithm validation
   - Uses auth_secret_key and auth_algorithm from centralized config
   - Suitable for production deployments with rotating tokens and authorization

Both authentication methods integrate with FastAPI's dependency injection system,
allowing MCP tool endpoints to require authentication by adding:
    
    @app.post("/tools/seed_user")
    async def seed_user(
        payload: dict,
        token: str = Depends(validate_bearer_token)  # Enforces authentication
    ):
        # Only authenticated requests reach this code
        pass

Security Model:
    - All MCP tool endpoints (seed_user, build_payload, reset_env, query_state)
      should be protected with authentication to prevent unauthorized test data
      manipulation in shared test environments
    - Bearer tokens must be transmitted via HTTP Authorization header:
      "Authorization: Bearer <token>"
    - Invalid tokens return HTTP 401 Unauthorized with WWW-Authenticate header
    - Missing configuration returns HTTP 500 Internal Server Error

Environment Variables:
    FASTAPI_MCP_TOKEN: Static bearer token for simple authentication (required
        for validate_bearer_token). Generate with: openssl rand -hex 32
    
    AUTH_SECRET_KEY: JWT signing secret for JWT verification (required for
        verify_token). Configured via settings object from config.py.

Usage Examples:
    # Example 1: Static token authentication in endpoint
    from fastapi import APIRouter, Depends
    from mcp_servers.fastapi_mcp.auth.bearer import validate_bearer_token
    
    router = APIRouter()
    
    @router.post("/tools/seed_user")
    async def seed_user(token: str = Depends(validate_bearer_token)):
        return {"status": "authenticated", "tool": "seed_user"}
    
    # Example 2: JWT authentication with claim extraction
    from mcp_servers.fastapi_mcp.auth.bearer import verify_token
    
    @router.post("/tools/reset_env")
    async def reset_env(payload: dict = Depends(verify_token)):
        user_id = payload.get("sub")  # Extract subject claim
        return {"authenticated_user": user_id}
    
    # Example 3: pytest test making authenticated MCP request
    import httpx
    import os
    
    async def test_mcp_seed_user():
        token = os.getenv("FASTAPI_MCP_TOKEN")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/tools/seed_user",
                headers={"Authorization": f"Bearer {token}"},
                json={"role": "admin"}
            )
            assert response.status_code == 200

Production Deployment Considerations:
    - Store FASTAPI_MCP_TOKEN in secure secrets management (GitHub Secrets,
      AWS Secrets Manager, HashiCorp Vault)
    - Rotate tokens regularly using automated secret rotation
    - Never commit tokens to version control (.env.example should have placeholders)
    - Use JWT verification (verify_token) for multi-tenant or user-specific access
    - Consider implementing rate limiting to prevent token brute-force attacks
    - Log authentication failures for security monitoring and alerting
"""

import os
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt  # type: ignore[import-untyped]

from mcp_servers.fastapi_mcp.config import settings


# HTTPBearer security scheme for extracting tokens from Authorization headers
# This automatically handles:
# - Parsing "Authorization: Bearer <token>" header format
# - Extracting the token string for validation functions
# Note: auto_error=False allows custom 401 responses instead of FastAPI's default 403
security = HTTPBearer(
    scheme_name="Bearer Token",
    description="Bearer token for MCP server authentication. Include in Authorization header as: Bearer <token>",
    auto_error=False  # Manual error handling for proper 401 Unauthorized responses
)


async def validate_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Validate static bearer token against FASTAPI_MCP_TOKEN environment variable.
    
    This is the PRIMARY authentication method for deterministic test execution
    in CI/CD pipelines. It performs simple string comparison between the provided
    token and the expected token from the environment, with no expiration or
    complex claim management.
    
    Authentication Flow:
        1. FastAPI extracts token from "Authorization: Bearer <token>" header
        2. HTTPBearer dependency provides credentials object (None if missing)
        3. credentials.credentials contains the token string
        4. Compare token against os.getenv("FASTAPI_MCP_TOKEN")
        5. Return token if match, raise HTTPException if mismatch or missing config
    
    Args:
        credentials: HTTPAuthorizationCredentials from FastAPI's HTTPBearer
            dependency injection. Contains the extracted bearer token in
            credentials.credentials attribute. None if Authorization header missing.
    
    Returns:
        str: The validated bearer token string. This can be used by endpoints
            for logging or audit trails.
    
    Raises:
        HTTPException: 
            - 401 Unauthorized if Authorization header is missing
            - 401 Unauthorized if token doesn't match FASTAPI_MCP_TOKEN
            - 401 Unauthorized if provided token is empty/whitespace
            - 500 Internal Server Error if FASTAPI_MCP_TOKEN env var not configured
    
    Example Usage:
        @app.post("/tools/seed_user")
        async def seed_user(
            payload: dict,
            token: str = Depends(validate_bearer_token)
        ):
            # Token validated, proceed with tool logic
            return {"status": "success"}
    
    Security Notes:
        - Tokens are compared using standard string equality (not constant-time)
        - For production, consider implementing constant-time comparison to
          prevent timing attacks
        - Token should be at least 32 bytes (64 hex characters) for security
        - Tokens should be generated with: openssl rand -hex 32
    
    Environment Configuration:
        export FASTAPI_MCP_TOKEN="your-secure-token-here"
        
        Or in .env file:
        FASTAPI_MCP_TOKEN=abc123def456...
    """
    # Check if Authorization header was provided
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Retrieve expected token from environment variable
    expected_token = os.getenv("FASTAPI_MCP_TOKEN")
    
    # Check if token is configured in environment
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "FASTAPI_MCP_TOKEN environment variable not configured. "
                "Set this variable to enable static token authentication. "
                "Generate token with: openssl rand -hex 32"
            ),
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract provided token from credentials
    provided_token = credentials.credentials
    
    # Validate token is not empty
    if not provided_token or not provided_token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token cannot be empty",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Compare provided token with expected token
    if provided_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token. Ensure FASTAPI_MCP_TOKEN matches.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Token validated successfully
    return provided_token


async def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Verify JWT bearer token using python-jose with signature and claim validation.
    
    This is the SECONDARY authentication method for advanced scenarios requiring
    token expiration, claim-based authorization, or multi-tenant access control.
    It performs full JWT decoding with signature verification using the secret
    key and algorithm from centralized configuration.
    
    JWT Verification Process:
        1. FastAPI extracts token from "Authorization: Bearer <token>" header
        2. HTTPBearer dependency provides credentials object (None if missing)
        3. jwt.decode() validates signature using settings.auth_secret_key
        4. Algorithm verified against settings.auth_algorithm (default: HS256)
        5. Expiration checked automatically by jwt.decode()
        6. Decoded payload (claims) returned as dictionary
    
    Args:
        credentials: HTTPAuthorizationCredentials from FastAPI's HTTPBearer
            dependency injection. Contains the JWT token string to decode.
            None if Authorization header missing.
    
    Returns:
        Dict[str, Any]: Decoded JWT payload containing claims such as:
            - sub: Subject (typically user ID or test runner identifier)
            - exp: Expiration timestamp (verified automatically)
            - iat: Issued at timestamp
            - Custom claims: Any application-specific data
    
    Raises:
        HTTPException:
            - 401 Unauthorized if Authorization header is missing
            - 401 Unauthorized if JWT signature is invalid
            - 401 Unauthorized if JWT is expired
            - 401 Unauthorized if JWT is malformed or uses wrong algorithm
            - 401 Unauthorized if required claims are missing
            - 500 Internal Server Error if auth_secret_key not configured
    
    Example Usage:
        @app.post("/tools/build_payload")
        async def build_payload(
            request: dict,
            token_payload: Dict[str, Any] = Depends(verify_token)
        ):
            # Extract user information from token claims
            user_id = token_payload.get("sub")
            role = token_payload.get("role", "user")
            
            # Use claims for authorization logic
            if role != "admin":
                raise HTTPException(403, "Admin access required")
            
            return {"status": "authorized", "user": user_id}
    
    JWT Structure:
        Header:
            {"alg": "HS256", "typ": "JWT"}
        
        Payload (claims):
            {
                "sub": "test-runner-123",
                "exp": 1699999999,
                "iat": 1699996399,
                "role": "admin"
            }
        
        Signature:
            HMACSHA256(
                base64UrlEncode(header) + "." + base64UrlEncode(payload),
                settings.auth_secret_key
            )
    
    Security Notes:
        - Only use HS256 (HMAC with SHA-256) or RS256 (RSA) algorithms
        - Never use "none" algorithm (disabled by jwt.decode by default)
        - Rotate auth_secret_key regularly in production
        - Keep token expiration short (60 minutes default)
        - Include minimal claims to reduce token size
    
    Configuration:
        From mcp_servers/fastapi_mcp/config.py settings:
            - auth_secret_key: Secret key for JWT signing/verification
            - auth_algorithm: Algorithm (HS256, HS384, HS512, RS256, etc.)
            - auth_token_expire_minutes: Token validity duration
    """
    # Check if Authorization header was provided
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Validate that JWT secret key is configured
    if not settings.auth_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "auth_secret_key not configured in settings. "
                "Set AUTH_SECRET_KEY environment variable for JWT authentication. "
                "Generate with: openssl rand -hex 32"
            ),
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Extract JWT token from credentials
    token = credentials.credentials
    
    try:
        # Decode and verify JWT token
        # jwt.decode() automatically:
        # - Verifies signature using settings.auth_secret_key
        # - Checks token expiration (exp claim)
        # - Validates algorithm matches settings.auth_algorithm
        # - Raises JWTError for any validation failures
        payload: Dict[str, Any] = jwt.decode(
            token=token,
            key=settings.auth_secret_key,
            algorithms=[settings.auth_algorithm]
        )
        
        # JWT successfully decoded and verified
        return payload
        
    except JWTError as e:
        # JWT validation failed - invalid signature, expired, malformed, etc.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
