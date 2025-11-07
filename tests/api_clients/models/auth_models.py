"""
Authentication API Models

Pydantic model definitions for authentication API request/response validation.
Provides type-safe data structures with field validation, custom validators for
email format and password strength, and JSON schema generation for authentication endpoints.

This module supports:
- Login request/response models with JWT token handling
- Token refresh request/response models
- Password reset flow models
- Token verification models
- Field-level validation (email format, password strength)
- Runtime validation and compile-time type checking with mypy
- JSON schema generation for OpenAPI documentation

Usage:
    from tests.api_clients.models.auth_models import LoginRequest, LoginResponse
    
    # Create and validate login request
    request = LoginRequest(
        email="user@example.com",
        password="SecurePass123!",
        remember_me=True
    )
    
    # Parse and validate API response
    response_data = await client.post("/auth/login", json=request.model_dump())
    login_response = LoginResponse.model_validate(response_data.json())
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class LoginRequest(BaseModel):
    """
    Request model for user login/authentication.
    
    Validates:
    - Email format using EmailStr type (RFC 5322 compliant)
    - Password minimum length requirements (8-128 characters)
    - Password strength (uppercase, lowercase, digit requirements)
    - No additional fields allowed (extra='forbid')
    
    Attributes:
        email: User email address for authentication
        password: User password meeting strength requirements
        remember_me: Extend session duration flag
    """
    
    email: EmailStr = Field(
        ...,
        description="User email address for authentication",
        examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (8-128 characters)",
        examples=["SecurePass123!"]
    )
    remember_me: bool = Field(
        default=False,
        description="Extend session duration if true"
    )
    
    model_config = {
        "extra": "forbid",  # Reject unexpected fields to catch API contract violations
        "json_schema_extra": {
            "examples": [{
                "email": "test@example.com",
                "password": "MyPassword123!",
                "remember_me": False
            }]
        }
    }
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets minimum security requirements.
        
        Requirements:
        - At least 8 characters (enforced by Field min_length)
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        
        Args:
            v: Password value to validate
            
        Returns:
            str: Validated password value
            
        Raises:
            ValueError: If password doesn't meet strength requirements
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginResponse(BaseModel):
    """
    Response model for successful authentication.
    
    Contains JWT access and refresh tokens with expiration information
    and authenticated user metadata.
    
    Attributes:
        access_token: JWT access token for authenticated API requests
        refresh_token: JWT refresh token for obtaining new access tokens
        token_type: Token type for Authorization header (always "Bearer")
        expires_in: Access token expiration time in seconds
        expires_at: Absolute access token expiration timestamp
        user_id: Unique identifier of authenticated user
        email: Authenticated user's email address
        role: User role (admin, user, guest, etc.)
    """
    
    access_token: str = Field(
        ...,
        description="JWT access token for authenticated API requests",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for obtaining new access tokens",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    token_type: Literal["Bearer"] = Field(
        default="Bearer",
        description="Token type for Authorization header"
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        examples=[3600]
    )
    expires_at: datetime = Field(
        ...,
        description="Absolute access token expiration timestamp"
    )
    user_id: str = Field(
        ...,
        description="Unique identifier of authenticated user"
    )
    email: EmailStr = Field(
        ...,
        description="Authenticated user's email address"
    )
    role: str = Field(
        ...,
        description="User role (admin, user, guest, etc.)",
        examples=["admin", "user"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "expires_at": "2024-01-15T11:30:00Z",
                "user_id": "user_abc123",
                "email": "test@example.com",
                "role": "admin"
            }]
        }
    }


class TokenRefreshRequest(BaseModel):
    """
    Request model for refreshing access tokens.
    
    Used when access token expires to obtain new tokens
    without re-authenticating with credentials.
    
    Attributes:
        refresh_token: Valid JWT refresh token from previous login
    """
    
    refresh_token: str = Field(
        ...,
        description="Valid JWT refresh token from previous login",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    
    model_config = {
        "extra": "forbid"
    }


class TokenRefreshResponse(BaseModel):
    """
    Response model for token refresh operation.
    
    Returns new access token and optionally rotated refresh token
    if refresh token rotation is enabled on the server.
    
    Attributes:
        access_token: New JWT access token
        refresh_token: New refresh token if rotation enabled (optional)
        token_type: Token type for Authorization header (always "Bearer")
        expires_in: New access token expiration in seconds
        expires_at: Absolute expiration timestamp
    """
    
    access_token: str = Field(
        ...,
        description="New JWT access token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    refresh_token: Optional[str] = Field(
        default=None,
        description="New refresh token if rotation enabled"
    )
    token_type: Literal["Bearer"] = Field(
        default="Bearer",
        description="Token type for Authorization header"
    )
    expires_in: int = Field(
        ...,
        description="New access token expiration in seconds",
        examples=[3600]
    )
    expires_at: datetime = Field(
        ...,
        description="Absolute expiration timestamp"
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "Bearer",
                "expires_in": 3600,
                "expires_at": "2024-01-15T12:30:00Z"
            }]
        }
    }


class PasswordResetRequest(BaseModel):
    """
    Request model for initiating password reset flow.
    
    Sends password reset email to the specified address if it exists
    in the system. Response is the same whether email exists or not
    to prevent email enumeration attacks.
    
    Attributes:
        email: Email address for password reset
    """
    
    email: EmailStr = Field(
        ...,
        description="Email address for password reset",
        examples=["user@example.com"]
    )
    
    model_config = {
        "extra": "forbid"
    }


class PasswordResetResponse(BaseModel):
    """
    Response model for password reset request.
    
    Returns confirmation message and reset token validity period.
    Actual reset token is sent via email, not in API response.
    
    Attributes:
        message: Status message confirming reset email sent
        reset_token_expires_in: Reset token validity duration in seconds
    """
    
    message: str = Field(
        ...,
        description="Status message",
        examples=["Password reset email sent"]
    )
    reset_token_expires_in: int = Field(
        ...,
        description="Reset token validity duration in seconds",
        examples=[3600]
    )


class TokenVerifyRequest(BaseModel):
    """
    Request model for verifying token validity.
    
    Used to check if a JWT token is valid, not expired, and not revoked.
    Useful for validating tokens before performing sensitive operations.
    
    Attributes:
        token: JWT token to verify
    """
    
    token: str = Field(
        ...,
        description="JWT token to verify",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."]
    )
    
    model_config = {
        "extra": "forbid"
    }


class TokenVerifyResponse(BaseModel):
    """
    Response model for token verification.
    
    Returns validation status and token metadata if valid.
    
    Attributes:
        valid: Whether token is valid, not expired, and not revoked
        user_id: User ID if token is valid (None if invalid)
        expires_at: Token expiration timestamp if valid (None if invalid)
    """
    
    valid: bool = Field(
        ...,
        description="Whether token is valid",
        examples=[True]
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID if token is valid"
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Token expiration timestamp if valid"
    )

