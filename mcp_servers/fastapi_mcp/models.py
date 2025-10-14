"""
Pydantic Models for FastAPI MCP Server

This module defines request/response models for the FastAPI Model Context Protocol (MCP) server,
providing type-safe API contracts with automatic validation for deterministic test data management.

The MCP server exposes four primary tools:
- seed_user: Create test users with specific roles and attributes
- build_payload: Generate valid request payloads from templates
- reset_env: Reset test environment state with configurable scope
- query_state: Query current state of test environment resources

All models provide comprehensive validation, JSON schema generation, and automatic
OpenAPI documentation integration for enterprise test automation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """
    Enumeration of available user roles for test user creation.
    
    These roles map to application authorization levels and determine
    access permissions for seeded test users. Used in both SeedUserRequest
    and SeedUserResponse to ensure type-safe role assignment.
    
    Attributes:
        ADMIN: Administrative user with full system access
        EDITOR: User with content creation and modification permissions
        VIEWER: Read-only user with limited access permissions
    """
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class SeedUserRequest(BaseModel):
    """
    Request model for the seed_user MCP tool.
    
    Creates a new test user in the target application with specified role
    and optional profile attributes. The MCP server will generate a valid
    password and create the user account in the test environment database.
    
    Attributes:
        role: User authorization role (ADMIN, EDITOR, or VIEWER)
        email: Optional email address (auto-generated if not provided)
        first_name: Optional user first name for profile
        last_name: Optional user last name for profile
        custom_attributes: Optional dictionary of additional user attributes
                          for application-specific fields (e.g., department, phone)
    
    Example:
        ```python
        request = SeedUserRequest(
            role=UserRole.ADMIN,
            email="test.admin@example.com",
            first_name="Test",
            last_name="Admin",
            custom_attributes={"department": "Engineering", "employee_id": "EMP001"}
        )
        ```
    """
    role: UserRole = Field(
        ...,
        description="User role determining access permissions (ADMIN, EDITOR, or VIEWER)"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Email address for the test user. If not provided, a unique email will be auto-generated"
    )
    first_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="First name of the test user for profile display"
    )
    last_name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Last name of the test user for profile display"
    )
    custom_attributes: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional user attributes as key-value pairs for application-specific fields"
    )


class SeedUserResponse(BaseModel):
    """
    Response model for the seed_user MCP tool.
    
    Returns details of the successfully created test user, including the
    generated user ID, credentials, and profile information. The password
    is auto-generated and returned for test authentication purposes.
    
    Attributes:
        user_id: Unique identifier for the created user in the system
        email: Email address of the created user
        password: Auto-generated password for test authentication
        first_name: First name of the user (if provided in request)
        last_name: Last name of the user (if provided in request)
        role: Assigned user role
        created_at: ISO 8601 timestamp of user creation for audit trail
    
    Example:
        ```python
        response = SeedUserResponse(
            user_id="usr_abc123",
            email="test.admin@example.com",
            password="TempPass123!",
            first_name="Test",
            last_name="Admin",
            role=UserRole.ADMIN,
            created_at=datetime.utcnow()
        )
        ```
    """
    user_id: str = Field(
        ...,
        description="Unique identifier for the created user",
        min_length=1
    )
    email: EmailStr = Field(
        ...,
        description="Email address of the created test user"
    )
    password: str = Field(
        ...,
        description="Auto-generated password for test authentication",
        min_length=8
    )
    first_name: Optional[str] = Field(
        None,
        description="First name of the created user"
    )
    last_name: Optional[str] = Field(
        None,
        description="Last name of the created user"
    )
    role: str = Field(
        ...,
        description="Assigned role for the created user (actual role in application)"
    )
    created_at: datetime = Field(
        ...,
        description="ISO 8601 timestamp of user creation"
    )


class BuildPayloadRequest(BaseModel):
    """
    Request model for the build_payload MCP tool.
    
    Generates a valid request payload from a predefined template with
    parameter substitution. Templates ensure test requests match the
    expected schema and validation rules of the target API.
    
    Attributes:
        template_name: Name of the payload template to use (e.g., "create_user", "update_project")
        params: Dictionary of parameters to substitute into the template
    
    Example:
        ```python
        request = BuildPayloadRequest(
            template_name="create_project",
            params={"name": "Test Project", "owner_id": "usr_123", "status": "active"}
        )
        ```
    """
    template_name: str = Field(
        ...,
        description="Name of the payload template to use for generation",
        min_length=1,
        max_length=100
    )
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to substitute into the template as key-value pairs"
    )


class BuildPayloadResponse(BaseModel):
    """
    Response model for the build_payload MCP tool.
    
    Returns the generated payload ready for use in API requests, along with
    the template name for traceability and debugging purposes.
    
    Attributes:
        payload: Generated request payload as a dictionary
        template_used: Name of the template that was used for generation
    
    Example:
        ```python
        response = BuildPayloadResponse(
            payload={"name": "Test Project", "owner_id": "usr_123", "status": "active", "created_at": "2024-01-15T10:30:00Z"},
            template_used="create_project"
        )
        ```
    """
    payload: Dict[str, Any] = Field(
        ...,
        description="Generated request payload ready for API submission"
    )
    template_used: str = Field(
        ...,
        description="Name of the template used for payload generation",
        min_length=1
    )


class ResetEnvRequest(BaseModel):
    """
    Request model for the reset_env MCP tool.
    
    Resets the test environment to a clean state by removing test data.
    The scope parameter controls which categories of data are deleted,
    allowing for partial or complete environment cleanup.
    
    Attributes:
        scope: Scope of the reset operation
               - "all": Delete all test data (users, projects, and other resources)
               - "users": Delete only test users
               - "projects": Delete only projects
               - "data": Delete only application data (preserve users and projects)
    
    Example:
        ```python
        request = ResetEnvRequest(scope="users")  # Delete only test users
        ```
    """
    scope: Literal["all", "users", "projects", "data"] = Field(
        default="all",
        description="Scope of environment reset: 'all' (complete reset), 'users' (users only), 'projects' (projects only), or 'data' (application data only)"
    )


class ResetEnvResponse(BaseModel):
    """
    Response model for the reset_env MCP tool.
    
    Returns the result of the environment reset operation, including
    confirmation of success, the scope that was applied, and the count
    of items deleted.
    
    Attributes:
        success: Whether the reset operation completed successfully
        scope: The scope that was applied for the reset
        items_deleted: Total count of items removed from the environment
    
    Example:
        ```python
        response = ResetEnvResponse(
            success=True,
            scope="users",
            items_deleted=15
        )
        ```
    """
    success: bool = Field(
        ...,
        description="Whether the environment reset completed successfully"
    )
    scope: str = Field(
        ...,
        description="The scope that was applied for the reset operation",
        min_length=1
    )
    items_deleted: int = Field(
        ...,
        description="Total count of items deleted during the reset operation",
        ge=0
    )


class QueryStateRequest(BaseModel):
    """
    Request model for the query_state MCP tool.
    
    Queries the current state of test environment resources for inspection
    and debugging. Supports filtering to narrow down results to specific
    resource instances.
    
    Attributes:
        resource_type: Type of resource to query
                      - "users": Query test users
                      - "projects": Query projects
                      - "sessions": Query active sessions
                      - "data": Query application data entries
        filters: Optional dictionary of filter criteria (e.g., {"role": "admin", "status": "active"})
    
    Example:
        ```python
        request = QueryStateRequest(
            resource_type="users",
            filters={"role": "admin"}
        )
        ```
    """
    resource_type: Literal["users", "projects", "sessions", "data"] = Field(
        ...,
        description="Type of resource to query: 'users', 'projects', 'sessions', or 'data'"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional filter criteria as key-value pairs to narrow query results"
    )


class QueryStateResponse(BaseModel):
    """
    Response model for the query_state MCP tool.
    
    Returns the current state of queried resources, including the resource
    type, total count, and list of matching resource instances.
    
    Attributes:
        resource_type: Type of resource that was queried
        count: Total number of matching resources found
        items: List of resource instances as dictionaries
    
    Example:
        ```python
        response = QueryStateResponse(
            resource_type="users",
            count=3,
            items=[
                {"user_id": "usr_1", "email": "admin@test.com", "role": "admin"},
                {"user_id": "usr_2", "email": "editor@test.com", "role": "editor"},
                {"user_id": "usr_3", "email": "viewer@test.com", "role": "viewer"}
            ]
        )
        ```
    """
    resource_type: str = Field(
        ...,
        description="Type of resource that was queried",
        min_length=1
    )
    count: int = Field(
        ...,
        description="Total number of matching resources found",
        ge=0
    )
    items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of matching resource instances as dictionaries"
    )
