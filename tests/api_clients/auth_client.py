"""
Authentication API Client Module

Provides typed authentication API client for login, logout, token management,
and password reset operations with comprehensive Allure reporting integration.

This module implements:
- Login authentication with JWT token retrieval
- Token refresh for session management
- Logout for session termination
- Password reset request initiation
- Token verification for validity checking

Features:
- Type-safe request/response validation with Pydantic models
- Automatic Allure step annotations for test report visualization
- Bearer token authentication support
- Comprehensive error handling for authentication failures
- Integration with MCP client for test credential generation
- HTTPError propagation with descriptive messages

Usage:
    # Initialize client with base URL from environment
    auth_client = AuthAPIClient()
    
    # Login and get JWT tokens
    login_response = auth_client.login(
        email="test@example.com",
        password="SecurePass123!"
    )
    
    # Use access token for authenticated requests
    auth_client.set_auth_token(login_response.access_token)
    
    # Refresh token when access token expires
    refreshed = auth_client.refresh_token(login_response.refresh_token)
    
    # Logout to invalidate session
    auth_client.logout()
    
    # Request password reset
    auth_client.request_password_reset(email="user@example.com")
    
    # Verify token validity
    is_valid = auth_client.verify_token(token="eyJhbGciOiJI...")
"""

from typing import Dict, Any, Optional

import allure

from tests.api_clients.base_client import BaseAPIClient
from tests.api_clients.models.auth_models import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenRefreshResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    TokenVerifyRequest,
    TokenVerifyResponse,
)


class AuthAPIClient(BaseAPIClient):
    """
    Typed API client for authentication endpoints.
    
    Extends BaseAPIClient with authentication-specific methods providing type-safe
    request/response validation and Allure reporting for authentication flows.
    All methods automatically log requests/responses to Allure reports via
    BaseAPIClient event hooks and add hierarchical step annotations.
    
    This client supports:
    - User login with email/password credentials
    - JWT token refresh for session management
    - User logout with session invalidation
    - Password reset initiation
    - Token verification for validity checking
    
    Authentication responses include JWT access tokens which can be used
    with set_auth_token() for subsequent authenticated API requests.
    
    Attributes:
        base_url (str): Authentication API base URL (from API_BASE_URL env var)
        client (httpx.Client): Underlying HTTP client with retry logic
    
    Example:
        # Initialize and authenticate
        auth_client = AuthAPIClient(base_url="https://api.example.com")
        
        # Login with test credentials (from MCP-generated data)
        response = auth_client.login(
            email="test@example.com",
            password="SecurePass123!"
        )
        
        # Access token and user metadata available in response
        assert response.access_token
        assert response.user_id
        assert response.role in ["admin", "user", "guest"]
        
        # Use token for authenticated requests
        auth_client.set_auth_token(response.access_token)
    """
    
    @allure.step("Authenticate user with email={email}")
    def login(self, email: str, password: str, remember_me: bool = False) -> LoginResponse:
        """
        Authenticate user and return JWT tokens with user metadata.
        
        Validates credentials against authentication service and returns access
        and refresh tokens if successful. Access token is used for authenticated
        API requests, refresh token is used to obtain new access tokens.
        
        This method automatically logs the authentication request and response
        to Allure reports. Email is shown in step name but password is masked
        in Allure attachments for security.
        
        Args:
            email: User email address for authentication
            password: User password (8-128 characters, validated by Pydantic)
            remember_me: Extend session duration if True (default: False)
            
        Returns:
            LoginResponse: Authentication response containing:
                - access_token: JWT for authenticated API requests
                - refresh_token: JWT for obtaining new access tokens
                - token_type: "Bearer" (for Authorization header)
                - expires_in: Token expiration in seconds
                - expires_at: Absolute expiration timestamp
                - user_id: Authenticated user's unique identifier
                - email: Authenticated user's email
                - role: User role (admin, user, guest, etc.)
            
        Raises:
            httpx.HTTPStatusError: For authentication failures:
                - 401 Unauthorized: Invalid credentials
                - 403 Forbidden: Account locked or disabled
                - 422 Unprocessable Entity: Validation errors
            pydantic.ValidationError: For request/response validation failures
            httpx.TransportError: For network failures (after retries)
        
        Example:
            # Login with credentials
            response = auth_client.login(
                email="user@example.com",
                password="MyPassword123!",
                remember_me=True
            )
            
            # Check authentication success
            assert response.access_token
            assert response.token_type == "Bearer"
            
            # Use token for subsequent requests
            auth_client.set_auth_token(response.access_token)
            
            # Or pass to other clients
            users_client = UsersAPIClient(auth_token=response.access_token)
        """
        request = LoginRequest(
            email=email,
            password=password,
            remember_me=remember_me
        )
        
        response = self.post(
            endpoint="/auth/login",
            request_model=request,
            response_model=LoginResponse
        )
        assert response is not None, "Login response should not be None"
        return response
    
    @allure.step("Refresh authentication token")
    def refresh_token(self, refresh_token: str) -> TokenRefreshResponse:
        """
        Refresh access token using refresh token for session management.
        
        Exchanges a valid refresh token for a new access token without requiring
        user credentials. Optionally returns rotated refresh token if server has
        refresh token rotation enabled for enhanced security.
        
        This method should be called when access token expires (typically after
        15-60 minutes) to extend user session without re-authentication. The
        expires_in and expires_at fields in the response indicate when the new
        access token will expire.
        
        Args:
            refresh_token: Valid JWT refresh token from previous login or refresh
            
        Returns:
            TokenRefreshResponse: Token refresh response containing:
                - access_token: New JWT access token
                - refresh_token: New refresh token if rotation enabled (optional)
                - token_type: "Bearer" (for Authorization header)
                - expires_in: New access token expiration in seconds
                - expires_at: Absolute expiration timestamp
            
        Raises:
            httpx.HTTPStatusError: For token refresh failures:
                - 401 Unauthorized: Invalid or expired refresh token
                - 403 Forbidden: Refresh token revoked
            pydantic.ValidationError: For request/response validation failures
            httpx.TransportError: For network failures (after retries)
        
        Example:
            # Initial login
            login_response = auth_client.login("user@example.com", "password")
            
            # Later, when access token expires (before expiration time)
            refreshed = auth_client.refresh_token(login_response.refresh_token)
            
            # Use new access token
            auth_client.set_auth_token(refreshed.access_token)
            
            # If rotation enabled, store new refresh token
            if refreshed.refresh_token:
                # Store for next refresh cycle
                current_refresh_token = refreshed.refresh_token
        """
        request = TokenRefreshRequest(refresh_token=refresh_token)
        
        response = self.post(
            endpoint="/auth/refresh",
            request_model=request,
            response_model=TokenRefreshResponse
        )
        assert response is not None, "Refresh token response should not be None"
        
        # Validate that required token fields are present per schema
        assert response.access_token, "access_token missing from refresh response"
        assert response.token_type == "Bearer", f"Expected 'Bearer' token_type, got '{response.token_type}'"
        assert response.expires_in > 0, "expires_in must be positive"
        assert response.expires_at, "expires_at missing from refresh response"
        
        return response
    
    @allure.step("Logout user and invalidate session")
    def logout(self) -> None:
        """
        Logout user and invalidate current session tokens.
        
        Invalidates the current access token and optionally the associated refresh
        token on the authentication server. After logout, the tokens can no longer
        be used for authenticated requests.
        
        This method should be called when user explicitly logs out or when tests
        need to clean up authentication state. No return value is provided for
        successful logout (204 No Content response).
        
        The Authorization header must contain a valid access token before calling
        logout. Use set_auth_token() after login to set the token, or initialize
        the client with auth_token parameter.
        
        Raises:
            httpx.HTTPStatusError: For logout failures:
                - 401 Unauthorized: No valid token in Authorization header
                - 403 Forbidden: Token already invalidated
            httpx.TransportError: For network failures (after retries)
        
        Example:
            # Login first
            response = auth_client.login("user@example.com", "password")
            auth_client.set_auth_token(response.access_token)
            
            # Perform authenticated operations
            # ...
            
            # Logout when done
            auth_client.logout()
            
            # Token is now invalid for subsequent requests
        """
        self.post(endpoint="/auth/logout")
    
    @allure.step("Request password reset for email={email}")
    def request_password_reset(self, email: str) -> PasswordResetResponse:
        """
        Initiate password reset flow by sending reset email.
        
        Sends a password reset email to the specified address if it exists in
        the system. The response is the same whether the email exists or not to
        prevent email enumeration attacks (security best practice).
        
        The actual password reset token is sent via email, not in the API response.
        Users receive an email with a secure link containing the reset token which
        can be used to set a new password within the validity period.
        
        Args:
            email: Email address for password reset
            
        Returns:
            PasswordResetResponse: Password reset response containing:
                - message: Confirmation message (e.g., "Password reset email sent")
                - reset_token_expires_in: Reset token validity duration in seconds
            
        Raises:
            httpx.HTTPStatusError: For request failures:
                - 422 Unprocessable Entity: Invalid email format
                - 429 Too Many Requests: Rate limit exceeded
            pydantic.ValidationError: For request/response validation failures
            httpx.TransportError: For network failures (after retries)
        
        Example:
            # Request password reset
            response = auth_client.request_password_reset("user@example.com")
            
            # Check confirmation
            assert "email sent" in response.message.lower()
            assert response.reset_token_expires_in > 0
            
            # User receives email with reset link
            # Email contains: https://app.example.com/reset?token=abc123...
        """
        request = PasswordResetRequest(email=email)
        
        response = self.post(
            endpoint="/auth/password-reset",
            request_model=request,
            response_model=PasswordResetResponse
        )
        assert response is not None, "Password reset response should not be None"
        return response
    
    @allure.step("Verify JWT token validity")
    def verify_token(self, token: str) -> bool:
        """
        Verify if JWT token is valid, not expired, and not revoked.
        
        Checks token validity by calling the authentication service's verify
        endpoint. Returns True if token is valid and can be used for authenticated
        requests, False otherwise.
        
        This method is useful for:
        - Pre-flight checks before sensitive operations
        - Validating tokens received from external sources
        - Testing token expiration and revocation logic
        
        Unlike other methods, this catches exceptions and returns False rather
        than propagating errors, making it suitable for conditional checks in
        test scenarios.
        
        Args:
            token: JWT token string to verify (access or refresh token)
            
        Returns:
            bool: True if token is valid, not expired, and not revoked.
                  False if token is invalid, expired, revoked, or verification fails.
        
        Example:
            # Login and verify token
            response = auth_client.login("user@example.com", "password")
            is_valid = auth_client.verify_token(response.access_token)
            assert is_valid is True
            
            # Check expired token
            expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            is_valid = auth_client.verify_token(expired_token)
            assert is_valid is False
            
            # Use for conditional logic
            if auth_client.verify_token(stored_token):
                # Token is valid, use it
                auth_client.set_auth_token(stored_token)
            else:
                # Token invalid, need to re-authenticate
                new_response = auth_client.login(email, password)
        """
        try:
            request = TokenVerifyRequest(token=token)
            
            response = self.post(
                endpoint="/auth/verify-token",
                request_model=request,
                response_model=TokenVerifyResponse
            )
            
            # Return the valid field from response, defaulting to False
            return response.valid if response else False
            
        except Exception as e:
            # Log verification failure to Allure for debugging
            allure.attach(
                f"Token verification failed: {type(e).__name__}: {str(e)}",
                name="Token Verification Error",
                attachment_type=allure.attachment_type.TEXT
            )
            return False
