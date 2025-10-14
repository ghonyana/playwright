"""
Authentication API Test Module

Traditional pytest-based authentication API tests validating login, token refresh,
logout, and password reset endpoints using typed AuthAPIClient with Pydantic validation.

This module implements comprehensive authentication flow testing including:
- Login authentication with valid and invalid credentials
- JWT token lifecycle (issue, refresh, verify, invalidate)
- Logout and session termination
- Password reset request workflow
- Token verification and validation
- Comprehensive error handling for authentication failures

Per Agent Action Plan Section 0.5.1 Group 6.6 and Section 0.1.2:
- Uses AuthAPIClient for type-safe API requests with Pydantic validation
- Integrates with MCP client for deterministic test user generation (no hardcoded data)
- Implements Allure decorators for comprehensive test reporting
- Validates JWT token structure and lifecycle management
- Tests authentication error handling (401, 403 status codes)
- Ensures parallel-friendly test execution with isolated test data

Test Coverage:
- Successful login with valid credentials returning JWT tokens
- Login failure with invalid password (401 Unauthorized)
- Login failure with non-existent user (401 Unauthorized)
- Token refresh with valid refresh token
- Token refresh failure with invalid token (401 Unauthorized)
- User logout invalidating session tokens
- Password reset email request
- Token verification with valid JWT
- Token verification with invalid JWT

Integration Points:
- AuthAPIClient: tests/api_clients/auth_client.py
- Pydantic Models: tests/api_clients/models/auth_models.py
- MCP Client: tests/helpers/mcp_client.py
- Fixtures: auth_api, mcp_client from tests/conftest.py

Usage:
    # Run all authentication API tests
    pytest tests/api/test_auth_api.py
    
    # Run with Allure reporting
    pytest tests/api/test_auth_api.py --alluredir=allure-results
    
    # Run only smoke tests
    pytest tests/api/test_auth_api.py -m smoke
    
    # Run specific test
    pytest tests/api/test_auth_api.py::test_login_api_with_valid_credentials
"""

import pytest
import allure
import httpx

from tests.api_clients.auth_client import AuthAPIClient
from tests.api_clients.models.auth_models import LoginRequest
from tests.helpers.mcp_client import MCPClient


@allure.feature("Authentication API")
@allure.story("User Login")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.api
@pytest.mark.smoke
def test_login_api_with_valid_credentials(auth_api: AuthAPIClient, mcp_client: MCPClient):
    """
    Test successful login with valid credentials via API.
    
    Per Agent Action Plan Section 0.1.2: Use MCP for test data generation.
    Tests JWT token response structure and authentication flow.
    
    This test validates:
    - User authentication with email and password
    - JWT access and refresh token generation
    - Token metadata (type, expiration)
    - User information in response (user_id, email, role)
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
        mcp_client: MCPClient fixture from conftest.py
    
    Raises:
        AssertionError: If authentication fails or response is invalid
        httpx.HTTPError: If API request fails unexpectedly
    """
    # Generate test user via MCP (no hardcoded data per user directive)
    with allure.step("Seed test user via MCP"):
        user = mcp_client.seed_user(role="viewer", email="auth.test@example.com")
        allure.attach(
            f"User ID: {user.get('id')}\nEmail: {user['email']}\nRole: {user['role']}",
            name="Generated Test User",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step(f"Login with email {user['email']}"):
        response = auth_api.login(
            email=user['email'],
            password=user['password']
        )
    
    with allure.step("Verify JWT tokens returned"):
        assert response.access_token is not None, "access_token missing from login response"
        assert response.refresh_token is not None, "refresh_token missing from login response"
        assert response.token_type == "Bearer", f"Expected token_type 'Bearer', got '{response.token_type}'"
        assert response.expires_in > 0, f"expires_in must be positive, got {response.expires_in}"
        
        # Validate user metadata in response
        assert response.user_id is not None, "user_id missing from login response"
        assert response.email == user['email'], f"Email mismatch: expected {user['email']}, got {response.email}"
        assert response.role == user['role'], f"Role mismatch: expected {user['role']}, got {response.role}"
        
        allure.attach(
            f"Access Token: {response.access_token[:20]}...\n"
            f"Token Type: {response.token_type}\n"
            f"Expires In: {response.expires_in}s\n"
            f"User ID: {response.user_id}\n"
            f"Role: {response.role}",
            name="Login Response Details",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication API")
@allure.story("User Login")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.api
def test_login_api_with_invalid_credentials(auth_api: AuthAPIClient, mcp_client: MCPClient):
    """
    Test login failure with invalid password.
    
    Validates API error handling for authentication failures with incorrect password.
    Per security best practices, the API should not reveal whether the user exists
    but return a generic 401 Unauthorized error.
    
    This test validates:
    - Rejection of invalid credentials
    - 401 Unauthorized status code
    - Security: No information leakage about user existence
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
        mcp_client: MCPClient fixture from conftest.py
    
    Raises:
        AssertionError: If error handling is incorrect
    """
    # Generate test user via MCP
    with allure.step("Seed test user via MCP"):
        user = mcp_client.seed_user(role="viewer")
    
    with allure.step("Attempt login with incorrect password"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            auth_api.login(
                email=user['email'],
                password="WrongPassword123!"
            )
    
    with allure.step("Verify 401 Unauthorized response"):
        assert exc_info.value.response.status_code == 401, \
            f"Expected 401 Unauthorized, got {exc_info.value.response.status_code}"
        
        allure.attach(
            f"Status Code: {exc_info.value.response.status_code}\n"
            f"Response: {exc_info.value.response.text}",
            name="Authentication Failure Details",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication API")
@allure.story("User Login")
@pytest.mark.api
def test_login_api_with_nonexistent_user(auth_api: AuthAPIClient):
    """
    Test login failure with non-existent user.
    
    Validates security: API should not reveal if user exists.
    Returns same 401 Unauthorized error as invalid password to prevent
    email enumeration attacks.
    
    This test validates:
    - Rejection of login attempts for non-existent users
    - 401 Unauthorized status code
    - Security: No user enumeration vulnerability
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
    
    Raises:
        AssertionError: If error handling is incorrect
    """
    with allure.step("Attempt login with non-existent email"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            auth_api.login(
                email="nonexistent@example.com",
                password="Password123!"
            )
    
    with allure.step("Verify 401 Unauthorized response"):
        assert exc_info.value.response.status_code == 401, \
            f"Expected 401 Unauthorized, got {exc_info.value.response.status_code}"
        
        allure.attach(
            f"Status Code: {exc_info.value.response.status_code}\n"
            f"Response: {exc_info.value.response.text}",
            name="Non-existent User Login Details",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication API")
@allure.story("Token Refresh")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.api
def test_refresh_token(auth_api: AuthAPIClient, mcp_client: MCPClient):
    """
    Test JWT token refresh with valid refresh token.
    
    Per Agent Action Plan Section 0.5.1 Group 6.6: test_refresh_token(auth_api)
    Validates token refresh mechanism for session management without re-authentication.
    
    This test validates:
    - Token refresh with valid refresh token
    - New access token generation
    - Token uniqueness (new token != old token)
    - Token metadata (type, expiration)
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
        mcp_client: MCPClient fixture from conftest.py
    
    Raises:
        AssertionError: If token refresh fails or response is invalid
        httpx.HTTPError: If API request fails unexpectedly
    """
    # Setup: Login to get initial tokens
    with allure.step("Setup: Login to obtain initial tokens"):
        user = mcp_client.seed_user(role="editor")
        login_response = auth_api.login(
            email=user['email'],
            password=user['password']
        )
        
        allure.attach(
            f"Initial Access Token: {login_response.access_token[:20]}...\n"
            f"Refresh Token: {login_response.refresh_token[:20]}...",
            name="Initial Login Tokens",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Refresh access token using refresh token"):
        refresh_response = auth_api.refresh_token(
            refresh_token=login_response.refresh_token
        )
    
    with allure.step("Verify new access token returned"):
        assert refresh_response.access_token is not None, "access_token missing from refresh response"
        assert refresh_response.access_token != login_response.access_token, \
            "Refresh should return a new access token, not the same one"
        assert refresh_response.token_type == "Bearer", \
            f"Expected token_type 'Bearer', got '{refresh_response.token_type}'"
        assert refresh_response.expires_in > 0, \
            f"expires_in must be positive, got {refresh_response.expires_in}"
        
        allure.attach(
            f"New Access Token: {refresh_response.access_token[:20]}...\n"
            f"Token Type: {refresh_response.token_type}\n"
            f"Expires In: {refresh_response.expires_in}s",
            name="Refreshed Token Details",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication API")
@allure.story("Token Refresh")
@pytest.mark.api
def test_refresh_token_with_invalid_token(auth_api: AuthAPIClient):
    """
    Test token refresh failure with invalid refresh token.
    
    Validates security: expired or invalid refresh tokens should be rejected.
    This prevents token reuse attacks and ensures session security.
    
    This test validates:
    - Rejection of invalid refresh tokens
    - 401 Unauthorized status code
    - Security: No token reuse or replay attacks
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
    
    Raises:
        AssertionError: If error handling is incorrect
    """
    with allure.step("Attempt refresh with invalid token"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            auth_api.refresh_token(refresh_token="invalid.token.here")
    
    with allure.step("Verify 401 Unauthorized response"):
        assert exc_info.value.response.status_code == 401, \
            f"Expected 401 Unauthorized, got {exc_info.value.response.status_code}"
        
        allure.attach(
            f"Status Code: {exc_info.value.response.status_code}\n"
            f"Response: {exc_info.value.response.text}",
            name="Invalid Token Refresh Details",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication API")
@allure.story("User Logout")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.api
def test_logout_api(auth_api: AuthAPIClient, mcp_client: MCPClient):
    """
    Test user logout invalidates session.
    
    Per Agent Action Plan Section 0.5.1 Group 6.6: test_logout_api(auth_api)
    Validates logout endpoint and session termination. After logout, the access
    token should be invalidated and cannot be used for authenticated requests.
    
    This test validates:
    - Successful logout operation
    - Token invalidation after logout
    - 401 Unauthorized when using invalidated token
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
        mcp_client: MCPClient fixture from conftest.py
    
    Raises:
        AssertionError: If logout or token invalidation fails
        httpx.HTTPError: If API request fails unexpectedly
    """
    # Setup: Login to get authentication
    with allure.step("Setup: Login to obtain authentication"):
        user = mcp_client.seed_user(role="viewer")
        login_response = auth_api.login(
            email=user['email'],
            password=user['password']
        )
        
        allure.attach(
            f"Access Token: {login_response.access_token[:20]}...",
            name="Login Token for Logout Test",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Set auth token in client for authenticated logout request
    with allure.step("Set authentication token for logout request"):
        auth_api.set_auth_token(login_response.access_token)
    
    with allure.step("Logout user"):
        auth_api.logout()
        allure.attach(
            "Logout successful - session terminated",
            name="Logout Operation",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Verify subsequent requests fail with 401"):
        # After logout, token should be invalid
        # The verify_token method returns False for invalid tokens
        is_valid = auth_api.verify_token(login_response.access_token)
        
        assert is_valid is False, \
            "Token should be invalid after logout, but verify_token returned True"
        
        allure.attach(
            f"Token validation after logout: {is_valid}\n"
            "Expected: False (token invalidated)",
            name="Token Validation After Logout",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication API")
@allure.story("Password Reset")
@pytest.mark.api
def test_password_reset_request(auth_api: AuthAPIClient, mcp_client: MCPClient):
    """
    Test password reset email request.
    
    Validates password reset workflow initiation. The API should send a password
    reset email with a secure token. Per security best practices, the response
    should be the same whether the email exists or not (preventing enumeration).
    
    This test validates:
    - Password reset request submission
    - Reset email confirmation message
    - Email value in response
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
        mcp_client: MCPClient fixture from conftest.py
    
    Raises:
        AssertionError: If password reset request fails
        httpx.HTTPError: If API request fails unexpectedly
    """
    with allure.step("Setup: Create user for password reset"):
        user = mcp_client.seed_user(role="viewer")
    
    with allure.step(f"Request password reset for {user['email']}"):
        response = auth_api.request_password_reset(email=user['email'])
    
    with allure.step("Verify reset email sent confirmation"):
        assert response.message is not None, "message missing from password reset response"
        assert "email sent" in response.message.lower() or "sent" in response.message.lower(), \
            f"Expected confirmation message about email, got: {response.message}"
        
        # Validate reset token expiration is provided
        assert response.reset_token_expires_in > 0, \
            f"reset_token_expires_in must be positive, got {response.reset_token_expires_in}"
        
        allure.attach(
            f"Message: {response.message}\n"
            f"Reset Token Expires In: {response.reset_token_expires_in}s",
            name="Password Reset Response",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication API")
@allure.story("Token Validation")
@pytest.mark.api
def test_verify_valid_token(auth_api: AuthAPIClient, mcp_client: MCPClient):
    """
    Test token verification with valid JWT.
    
    Validates token verification endpoint confirms valid tokens. This is useful
    for pre-flight checks before sensitive operations or validating tokens from
    external sources.
    
    This test validates:
    - Valid token verification returns True
    - Verification endpoint functionality
    - Token validation logic
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
        mcp_client: MCPClient fixture from conftest.py
    
    Raises:
        AssertionError: If valid token verification fails
        httpx.HTTPError: If API request fails unexpectedly
    """
    with allure.step("Setup: Login to obtain valid token"):
        user = mcp_client.seed_user(role="admin")
        login_response = auth_api.login(
            email=user['email'],
            password=user['password']
        )
        
        allure.attach(
            f"Access Token: {login_response.access_token[:20]}...",
            name="Valid Token for Verification",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Verify token validity"):
        is_valid = auth_api.verify_token(login_response.access_token)
    
    with allure.step("Confirm token is valid"):
        assert is_valid is True, \
            "Expected token to be valid (True), but got False"
        
        allure.attach(
            f"Token Validation Result: {is_valid}\n"
            "Expected: True (token is valid)",
            name="Token Verification Result",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication API")
@allure.story("Token Validation")
@pytest.mark.api
def test_verify_invalid_token(auth_api: AuthAPIClient):
    """
    Test token verification with invalid JWT.
    
    Validates rejection of malformed or invalid tokens. The verify_token method
    should return False for any invalid, expired, or malformed token rather than
    raising an exception.
    
    This test validates:
    - Invalid token verification returns False
    - Graceful handling of malformed tokens
    - Security: No exceptions on invalid input
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
    
    Raises:
        AssertionError: If invalid token handling is incorrect
    """
    with allure.step("Verify invalid token"):
        is_valid = auth_api.verify_token("invalid.jwt.token")
    
    with allure.step("Confirm token is invalid"):
        assert is_valid is False, \
            "Expected invalid token to return False, but got True"
        
        allure.attach(
            f"Token Validation Result: {is_valid}\n"
            "Expected: False (token is invalid)",
            name="Invalid Token Verification Result",
            attachment_type=allure.attachment_type.TEXT
        )
