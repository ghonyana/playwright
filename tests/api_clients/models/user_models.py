"""
Pydantic model definitions for user management API request/response validation.

This module provides type-safe data structures for user CRUD operations including:
- CreateUserRequest: User registration with comprehensive field validation
- UserResponse: Complete user data with timestamps and audit fields
- UpdateUserRequest: Partial user updates with optional fields
- UserListResponse: Paginated user lists with metadata
- UserSearchQuery: Search and filter operations
- UserActivationResponse: Account activation/deactivation responses

All models leverage Pydantic v2 features for runtime validation and compile-time
type checking with mypy. Field validators enforce business rules including email
format, name constraints, password strength, and phone number format (E.164).

Integration points:
- Used by tests/api_clients/users_client.py for type-safe API testing
- Works with MCP client build_payload for deterministic test data generation
- Enables OpenAPI schema generation for API documentation
- Provides compile-time safety via mypy static type checking
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRole(str, Enum):
    """
    Enumeration of valid user roles with associated permissions.
    
    Roles define access levels:
    - ADMIN: Full system access including user management
    - USER: Standard authenticated user access
    - EDITOR: Content creation and editing permissions
    - MODERATOR: Moderation and management permissions (mapped from editor in MCP)
    - VIEWER: Read-only access to resources
    - CUSTOMER: Customer-level access with limited permissions (mapped from viewer in MCP)
    - GUEST: Limited unauthenticated access
    """
    ADMIN = "admin"
    USER = "user"
    EDITOR = "editor"
    MODERATOR = "moderator"
    VIEWER = "viewer"
    CUSTOMER = "customer"
    GUEST = "guest"


class UserStatus(str, Enum):
    """
    Enumeration of user account statuses for lifecycle management.
    
    Statuses track account state:
    - ACTIVE: Account is active and can authenticate
    - INACTIVE: Account is deactivated, no authentication allowed
    - SUSPENDED: Temporary suspension due to policy violation
    - PENDING: Account awaiting email verification or approval
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class CreateUserRequest(BaseModel):
    """
    Request model for creating new user accounts.
    
    Validates all required fields for user registration including:
    - Email format validation via EmailStr type
    - Name format (letters, spaces, hyphens, apostrophes only)
    - Password strength (min 8 chars, uppercase, lowercase, digit)
    - Role from predefined enum values
    - Optional fields with sensible defaults
    - Phone number in E.164 international format
    
    Used by POST /users endpoint for user creation with MCP-generated
    test data to avoid hardcoded values in tests.
    """
    email: EmailStr = Field(
        ...,
        description="User email address (must be unique)",
        examples=["newuser@example.com"]
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User full name",
        examples=["John Doe"]
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="User role determining permissions",
        examples=["admin", "user", "guest"]
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User password (8-128 characters)",
        examples=["SecurePass123!"]
    )
    age: Optional[int] = Field(
        default=None,
        ge=18,
        le=120,
        description="User age (18-120 if provided)",
        examples=[25]
    )
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Department or organization",
        examples=["Engineering"]
    )
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",  # E.164 format
        description="Phone number in E.164 format",
        examples=["+12125551234"]
    )
    is_active: bool = Field(
        default=True,
        description="Whether account is active"
    )
    
    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [{
                "email": "john.doe@example.com",
                "name": "John Doe",
                "role": "user",
                "password": "MyPassword123!",
                "age": 30,
                "department": "Engineering",
                "phone": "+12125551234",
                "is_active": True
            }]
        }
    }
    
    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """
        Validate name contains only letters, spaces, hyphens, apostrophes.
        
        Business rule: Names must be composed of alphabetic characters with
        support for compound names (spaces), hyphenated names (hyphens), and
        names with apostrophes (O'Brien, D'Angelo).
        
        Args:
            v: Name string to validate
            
        Returns:
            Stripped name string if valid
            
        Raises:
            ValueError: If name is empty or contains invalid characters
        """
        if not v.strip():
            raise ValueError("Name cannot be empty or only whitespace")
        
        # Allow letters, spaces, hyphens, apostrophes
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ -'")
        if not all(c in allowed_chars for c in v):
            raise ValueError(
                "Name must contain only letters, spaces, hyphens, and apostrophes"
            )
        
        return v.strip()
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password meets security requirements.
        
        Security policy requires:
        - Minimum 8 characters length
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        
        Args:
            v: Password string to validate
            
        Returns:
            Password string if valid
            
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


class UpdateUserRequest(BaseModel):
    """
    Request model for updating existing user accounts.
    
    All fields are optional to support partial updates (PATCH semantics).
    Only provided fields will be updated on the target user resource.
    
    Used by PATCH /users/{user_id} endpoint for partial user updates
    without requiring all fields to be resent.
    """
    email: Optional[EmailStr] = Field(
        default=None,
        description="New email address"
    )
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated full name"
    )
    role: Optional[UserRole] = Field(
        default=None,
        description="Updated user role"
    )
    age: Optional[int] = Field(
        default=None,
        ge=18,
        le=120,
        description="Updated age"
    )
    department: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Updated department"
    )
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        description="Updated phone number"
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Updated account status"
    )
    
    model_config = {
        "extra": "forbid"
    }
    
    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate name format if provided in update request.
        
        Args:
            v: Optional name string to validate
            
        Returns:
            Stripped name string if valid, None if not provided
            
        Raises:
            ValueError: If name is invalid
        """
        if v is None:
            return v
        
        if not v.strip():
            raise ValueError("Name cannot be empty or only whitespace")
        
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ -'")
        if not all(c in allowed_chars for c in v):
            raise ValueError(
                "Name must contain only letters, spaces, hyphens, and apostrophes"
            )
        
        return v.strip()


class UserResponse(BaseModel):
    """
    Response model for user data retrieval.
    
    Represents complete user record with all fields populated including:
    - Unique identifier assigned by system
    - Email and personal information
    - Role and permission level
    - Account status and activation state
    - Audit timestamps (created, updated, last login)
    
    Password field is NEVER included in responses for security.
    
    Used by GET /users/{user_id} and as items in UserListResponse for
    paginated user listings.
    """
    id: str = Field(
        ...,
        description="Unique user identifier",
        examples=["user_abc123"]
    )
    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["john.doe@example.com"]
    )
    name: str = Field(
        ...,
        description="User full name",
        examples=["John Doe"]
    )
    role: UserRole = Field(
        ...,
        description="User role",
        examples=["admin", "user"]
    )
    age: Optional[int] = Field(
        default=None,
        description="User age if provided",
        examples=[30]
    )
    department: Optional[str] = Field(
        default=None,
        description="Department or organization",
        examples=["Engineering"]
    )
    phone: Optional[str] = Field(
        default=None,
        description="Phone number",
        examples=["+12125551234"]
    )
    is_active: Optional[bool] = Field(
        default=True,
        description="Whether account is active (not always returned by API)",
        examples=[True]
    )
    status: UserStatus = Field(
        default=UserStatus.ACTIVE,
        description="Account status",
        examples=["active", "suspended"]
    )
    created_at: datetime = Field(
        ...,
        description="User creation timestamp",
        examples=["2024-01-15T10:30:00Z"]
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp (not always returned by API)",
        examples=["2024-01-15T12:45:00Z"]
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        description="Last successful login timestamp",
        examples=["2024-01-15T14:20:00Z"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "id": "user_abc123",
                "email": "john.doe@example.com",
                "name": "John Doe",
                "role": "user",
                "age": 30,
                "department": "Engineering",
                "phone": "+12125551234",
                "is_active": True,
                "status": "active",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T12:45:00Z",
                "last_login_at": "2024-01-15T14:20:00Z"
            }]
        }
    }


class UserListResponse(BaseModel):
    """
    Response model for paginated user list retrieval.
    
    Supports pagination, filtering, and sorting of user records with metadata:
    - users: List of UserResponse objects for current page
    - total: Total count of users matching filter criteria
    - page: Current page number (1-indexed)
    - page_size: Number of users per page
    - total_pages: Total number of available pages
    - has_next: Boolean indicating if more pages exist
    - has_previous: Boolean indicating if previous pages exist
    
    Used by GET /users endpoint for paginated user listings with configurable
    page size (1-100 users per page).
    """
    users: List[UserResponse] = Field(
        ...,
        description="List of user records for current page",
        examples=[[]]
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of users matching filter criteria",
        examples=[150]
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-indexed)",
        examples=[1]
    )
    page_size: int = Field(
        ...,
        ge=1,
        le=100,
        description="Number of users per page",
        examples=[20]
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
        examples=[8]
    )
    has_next: bool = Field(
        ...,
        description="Whether more pages are available",
        examples=[True]
    )
    has_previous: bool = Field(
        ...,
        description="Whether previous pages exist",
        examples=[False]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [{
                "users": [
                    {
                        "id": "user_abc123",
                        "email": "john.doe@example.com",
                        "name": "John Doe",
                        "role": "user",
                        "is_active": True,
                        "status": "active",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-15T12:45:00Z"
                    }
                ],
                "total": 150,
                "page": 1,
                "page_size": 20,
                "total_pages": 8,
                "has_next": True,
                "has_previous": False
            }]
        }
    }


class UserSearchQuery(BaseModel):
    """
    Request model for user search operations.
    
    Supports searching users by:
    - query: Text search in name or email fields
    - role: Filter by specific user role
    - status: Filter by account status
    - limit: Maximum number of results (1-100)
    
    Used by GET /users/search endpoint for finding users matching
    specific criteria with configurable result limits.
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Search query for name or email",
        examples=["john"]
    )
    role: Optional[UserRole] = Field(
        default=None,
        description="Filter by role"
    )
    status: Optional[UserStatus] = Field(
        default=None,
        description="Filter by status"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum results to return",
        examples=[10]
    )
    
    model_config = {
        "extra": "forbid"
    }


class UserActivationResponse(BaseModel):
    """
    Response model for user activation/deactivation operations.
    
    Returned by account status change endpoints including:
    - POST /users/{user_id}/activate
    - POST /users/{user_id}/deactivate
    
    Provides confirmation of the status change with:
    - user_id: ID of the affected user
    - is_active: New activation status
    - message: Human-readable status message
    - updated_at: Timestamp of the status change
    
    Used to verify account state transitions in tests.
    """
    user_id: str = Field(
        ...,
        description="ID of affected user"
    )
    is_active: bool = Field(
        ...,
        description="New activation status"
    )
    message: str = Field(
        ...,
        description="Status message",
        examples=["User activated successfully"]
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp of status change"
    )

