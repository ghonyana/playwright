"""
FastAPI MCP Server - MCP Tools Router

This module implements the core Model Context Protocol (MCP) tool endpoints
for deterministic test data management in the pytest automation framework.

The tools provided enable tests to:
- Create test users with specific roles and attributes (seed_user)
- Generate valid API request payloads from templates (build_payload)
- Reset test environment to known-good state (reset_env)
- Query current test environment state (query_state)

All endpoints accept JSON-RPC style requests and return structured responses
validated by Pydantic models. Authentication is enforced via Bearer tokens
for secured operations (seed_user, reset_env, query_state).

Architecture:
    - APIRouter with /tools prefix for MCP tool organization
    - Pydantic request/response models for automatic validation
    - Service layer delegation for business logic separation
    - Bearer token authentication for secure endpoints
    - Comprehensive error handling with appropriate HTTP status codes
    - OpenAPI documentation generation for test framework integration

Integration with pytest:
    Tests use MCP client fixtures to call these endpoints, receiving
    deterministic test data and environment state management:
    
    ```python
    def test_with_seeded_user(mcp_client):
        # Create test user via seed_user endpoint
        user = mcp_client.seed_user(role="admin")
        
        # Generate API payload via build_payload endpoint
        payload = mcp_client.build_payload("create_project", {"name": "Test"})
        
        # Reset environment via reset_env endpoint
        mcp_client.reset_env(scope="users")
        
        # Query state via query_state endpoint
        state = mcp_client.query_state(resource_type="users", filters={"role": "admin"})
    ```
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

# Import request/response models
from mcp_servers.fastapi_mcp.models import (
    SeedUserRequest,
    SeedUserResponse,
    BuildPayloadRequest,
    BuildPayloadResponse,
    ResetEnvRequest,
    ResetEnvResponse,
    QueryStateRequest,
    QueryStateResponse
)

# Import authentication dependency
from mcp_servers.fastapi_mcp.auth.bearer import validate_bearer_token

# Import service classes
from mcp_servers.fastapi_mcp.services.user_service import UserService
from mcp_servers.fastapi_mcp.services.payload_service import PayloadService
from mcp_servers.fastapi_mcp.services.state_service import StateService


# Configure module logger for request/response logging
logger = logging.getLogger(__name__)


# Create router with prefix and tags for OpenAPI documentation
router = APIRouter(
    prefix="/tools",
    tags=["mcp_tools"]
)


@router.post(
    "/seed_user",
    response_model=SeedUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create deterministic test user",
    description="Creates a test user in the application with specified role and attributes. "
                "Requires Bearer token authentication for security.",
    dependencies=[Depends(validate_bearer_token)]
)
async def seed_user(
    request: SeedUserRequest,
    token: str = Depends(validate_bearer_token)
) -> SeedUserResponse:
    """
    Seed User MCP Tool - POST /tools/seed_user
    
    Creates a test user in the target application with deterministic attributes.
    This tool eliminates hardcoded test data and ensures tests start with
    known-good user accounts. User credentials are auto-generated and returned
    for test authentication.
    
    Authentication:
        Requires Bearer token in Authorization header. Token must match
        FASTAPI_MCP_TOKEN environment variable for access.
    
    Business Logic:
        Delegates to UserService.create_test_user() for user creation operations,
        including password generation, realistic attribute defaults, and application
        API integration.
    
    Args:
        request: SeedUserRequest containing user creation parameters:
            - role: UserRole enum (ADMIN, EDITOR, or VIEWER)
            - email: Optional email (auto-generated if not provided)
            - first_name: Optional first name (Faker-generated if not provided)
            - last_name: Optional last name (Faker-generated if not provided)
            - custom_attributes: Optional dict for application-specific fields
        token: Validated bearer token from authentication dependency
    
    Returns:
        SeedUserResponse with:
            - user_id: Unique identifier of created user
            - email: Email address of created user
            - password: Auto-generated password for test authentication
            - first_name: User's first name
            - last_name: User's last name
            - role: Assigned role in application
            - created_at: ISO 8601 timestamp of creation
    
    Raises:
        HTTPException 401: Invalid or missing bearer token
        HTTPException 409: User with given email already exists (duplicate)
        HTTPException 500: User creation failed due to service error
    
    Example pytest usage:
        ```python
        def test_admin_operations(mcp_client):
            # Create admin user with auto-generated credentials
            user = mcp_client.seed_user(role="admin")
            
            # Or create with specific email
            user = mcp_client.seed_user(
                role="editor",
                email="test.editor@example.com",
                first_name="Test",
                last_name="Editor"
            )
            
            # Use credentials for authentication
            auth_response = login(user.email, user.password)
            assert auth_response.status_code == 200
        ```
    
    Error Handling:
        - RuntimeError containing "already exists" → HTTP 409 Conflict
        - RuntimeError from service layer → HTTP 500 Internal Server Error
        - Other exceptions → HTTP 500 with error details logged
    """
    logger.info(
        f"seed_user called: role={request.role.value}, "
        f"email={request.email or 'auto-generated'}"
    )
    
    # Instantiate UserService for this request
    user_service = UserService()
    
    try:
        # Delegate to service layer for user creation
        result = await user_service.create_test_user(
            role=request.role,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            custom_attributes=request.custom_attributes
        )
        
        logger.info(
            f"seed_user success: user_id={result.user_id}, email={result.email}"
        )
        
        # UserService.create_test_user returns SeedUserResponse directly
        return result
        
    except RuntimeError as e:
        error_message = str(e)
        
        # Check if error indicates duplicate user (409 Conflict)
        if "already exists" in error_message.lower():
            logger.warning(f"Duplicate user creation attempt: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User already exists: {error_message}"
            )
        else:
            # Other runtime errors are service failures (500)
            logger.error(f"User creation failed: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"User creation failed: {error_message}"
            )
    
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error in seed_user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during user creation: {str(e)}"
        )


@router.post(
    "/build_payload",
    response_model=BuildPayloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate API request payload from template",
    description="Builds valid JSON payload from template with parameter substitution. "
                "No authentication required for payload generation."
)
async def build_payload(
    request: BuildPayloadRequest
) -> BuildPayloadResponse:
    """
    Build Payload MCP Tool - POST /tools/build_payload
    
    Generates valid API request payloads from predefined templates with
    parameter substitution and auto-generation of missing fields. Eliminates
    hardcoded request bodies in tests and ensures payloads match expected
    application schemas.
    
    Authentication:
        No authentication required. Payload generation is stateless and does
        not modify application state.
    
    Business Logic:
        Delegates to PayloadService.build_from_template() for template processing,
        parameter substitution, and default value generation using Faker library.
    
    Args:
        request: BuildPayloadRequest containing:
            - template_name: Name of payload template (e.g., "create_user", "update_project")
            - params: Dictionary of parameters to substitute into template
    
    Returns:
        BuildPayloadResponse with:
            - payload: Generated request payload as dictionary ready for API submission
            - template_used: Name of template used for generation (for traceability)
    
    Raises:
        HTTPException 400: Invalid template name (template not found)
        HTTPException 400: Invalid parameters or unresolved placeholders
        HTTPException 500: Payload generation failed due to service error
    
    Example pytest usage:
        ```python
        def test_create_user_api(mcp_client, users_api):
            # Generate user creation payload with custom role
            response = mcp_client.build_payload(
                template_name="create_user",
                params={"role": "admin", "email": "test@example.com"}
            )
            
            # Use generated payload in API request
            api_response = users_api.create(json=response.payload)
            assert api_response.status_code == 201
            
            # Generate with all defaults
            response = mcp_client.build_payload(template_name="create_project")
            assert "name" in response.payload
            assert "owner_id" in response.payload
        ```
    
    Available Templates:
        - create_user: User creation with email, names, role, password
        - update_user: User profile updates
        - create_project: Project creation with name, description, settings
        - update_project: Project updates
        - create_task: Task creation with title, assignee, priority
        - update_task: Task updates
        - create_comment: Comment creation
        - authenticate: Login credentials
        - refresh_token: Token refresh request
        - invite_user: User invitation
    
    Error Handling:
        - ValueError with "not found" → HTTP 400 Bad Request (invalid template)
        - ValueError with "unresolved" → HTTP 400 Bad Request (missing params)
        - Other exceptions → HTTP 500 Internal Server Error
    """
    logger.info(
        f"build_payload called: template_name={request.template_name}, "
        f"params_count={len(request.params)}"
    )
    
    # Instantiate PayloadService for this request
    payload_service = PayloadService()
    
    try:
        # Delegate to service layer for payload generation
        # PayloadService.build_from_template returns BuildPayloadResponse directly
        result = await payload_service.build_from_template(
            template_name=request.template_name,
            params=request.params
        )
        
        logger.info(
            f"build_payload success: template={result.template_used}, "
            f"payload_keys={list(result.payload.keys())}"
        )
        
        return result
        
    except ValueError as e:
        error_message = str(e)
        logger.warning(f"build_payload validation error: {error_message}")
        
        # ValueError from PayloadService indicates bad template or parameters
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template or parameters: {error_message}"
        )
    
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error in build_payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during payload generation: {str(e)}"
        )


@router.post(
    "/reset_env",
    response_model=ResetEnvResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset test environment to known state",
    description="Clears test data and resets environment based on scope parameter. "
                "Requires Bearer token authentication for security.",
    dependencies=[Depends(validate_bearer_token)]
)
async def reset_env(
    request: ResetEnvRequest,
    token: str = Depends(validate_bearer_token)
) -> ResetEnvResponse:
    """
    Reset Environment MCP Tool - POST /tools/reset_env
    
    Resets the test environment to a known-good state by clearing test data
    based on the specified scope. Supports scoped resets (all, users, projects,
    data) for efficient test isolation without full environment rebuilds.
    
    Authentication:
        Requires Bearer token in Authorization header. Token must match
        FASTAPI_MCP_TOKEN environment variable for access. This prevents
        unauthorized environment manipulation.
    
    Business Logic:
        Delegates to StateService.reset_environment() for scoped cleanup
        operations, including database deletion, API-based cleanup, and
        cache invalidation with transaction management.
    
    Args:
        request: ResetEnvRequest containing:
            - scope: Literal["all", "users", "projects", "data"]
                * "all": Complete reset (users, projects, data, sessions, cache)
                * "users": Delete only test users
                * "projects": Delete only projects
                * "data": Delete only application data
        token: Validated bearer token from authentication dependency
    
    Returns:
        ResetEnvResponse with:
            - success: Whether operation completed without errors
            - scope: The scope that was applied
            - items_deleted: Total count of items removed
    
    Raises:
        HTTPException 401: Invalid or missing bearer token
        HTTPException 403: Insufficient permissions for reset operation
        HTTPException 500: Reset operation failed due to service error
    
    Example pytest usage:
        ```python
        @pytest.fixture(scope="function")
        def clean_environment(mcp_client):
            # Complete environment reset before each test
            result = mcp_client.reset_env(scope="all")
            assert result.success is True
            yield
        
        def test_with_user_cleanup(mcp_client):
            # Create test users
            user1 = mcp_client.seed_user(role="admin")
            user2 = mcp_client.seed_user(role="editor")
            
            # Run test...
            
            # Cleanup only users (preserve other data)
            mcp_client.reset_env(scope="users")
        ```
    
    Safe Deletion Patterns:
        StateService uses safe deletion patterns to ensure only test data
        is removed:
        - Email patterns: *@example.com, *@test.com, test.*@*
        - Name patterns: test.*, test_*
        - Metadata tags: {"test": true}, {"environment": "test"}
    
    Error Handling:
        - PermissionError from service → HTTP 403 Forbidden
        - RuntimeError from service → HTTP 500 Internal Server Error
        - Other exceptions → HTTP 500 with error details logged
    """
    logger.info(f"reset_env called: scope={request.scope}")
    
    # Instantiate StateService for this request
    state_service = StateService()
    
    try:
        # Delegate to service layer for environment reset
        # StateService.reset_environment returns Dict[str, Any]
        result_dict = await state_service.reset_environment(scope=request.scope)
        
        logger.info(
            f"reset_env success: scope={request.scope}, "
            f"items_deleted={result_dict.get('items_deleted', 0)}, "
            f"success={result_dict.get('success', False)}"
        )
        
        # Construct ResetEnvResponse from service result dict
        return ResetEnvResponse(
            success=result_dict.get("success", False),
            scope=result_dict.get("scope", request.scope),
            items_deleted=result_dict.get("items_deleted", 0)
        )
        
    except PermissionError as e:
        logger.error(f"reset_env permission error: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Reset operation not permitted: {str(e)}"
        )
    
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error in reset_env: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during environment reset: {str(e)}"
        )


@router.post(
    "/query_state",
    response_model=QueryStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Query test environment state",
    description="Retrieves current state of test environment resources with optional filtering. "
                "Requires Bearer token authentication for security.",
    dependencies=[Depends(validate_bearer_token)]
)
async def query_state(
    request: QueryStateRequest,
    token: str = Depends(validate_bearer_token)
) -> QueryStateResponse:
    """
    Query State MCP Tool - POST /tools/query_state
    
    Queries the current state of test environment resources for debugging,
    verification, and test assertions. Supports filtering by resource attributes
    to narrow down results to specific instances.
    
    Authentication:
        Requires Bearer token in Authorization header. Token must match
        FASTAPI_MCP_TOKEN environment variable for access. This prevents
        unauthorized environment inspection.
    
    Business Logic:
        Delegates to StateService.query_resources() for database/API queries
        with filter application, result normalization, and performance optimization.
    
    Args:
        request: QueryStateRequest containing:
            - resource_type: Literal["users", "projects", "sessions", "data"]
                * "users": Query test users with roles and emails
                * "projects": Query test projects
                * "sessions": Query active test sessions
                * "data": Query application data entries
            - filters: Optional dict of filter criteria (e.g., {"role": "admin"})
        token: Validated bearer token from authentication dependency
    
    Returns:
        QueryStateResponse with:
            - resource_type: Type of resource queried
            - count: Number of matching resources found
            - items: List of resource instances as dictionaries
    
    Raises:
        HTTPException 401: Invalid or missing bearer token
        HTTPException 400: Invalid resource type (though Literal prevents this)
        HTTPException 500: Query operation failed due to service error
    
    Example pytest usage:
        ```python
        def test_user_count(mcp_client):
            # Query all users
            state = mcp_client.query_state(resource_type="users")
            assert state.count >= 0
            
            # Query admin users only
            admin_state = mcp_client.query_state(
                resource_type="users",
                filters={"role": "admin"}
            )
            assert admin_state.count >= 1
            
            # Verify specific user exists
            user_items = admin_state.items
            assert any(u["email"] == "admin@test.com" for u in user_items)
        
        def test_session_cleanup(mcp_client):
            # Query active sessions
            sessions = mcp_client.query_state(resource_type="sessions")
            
            # Verify no stale sessions remain
            assert sessions.count == 0, "Stale sessions found after cleanup"
        ```
    
    Query Performance:
        - Database queries: 10-50ms depending on table size
        - API queries: 50-200ms depending on network latency
        - Filters applied at database/API level for efficiency
    
    Error Handling:
        - ValueError from service → HTTP 400 Bad Request
        - RuntimeError from service → HTTP 500 Internal Server Error
        - Other exceptions → HTTP 500 with error details logged
    """
    logger.info(
        f"query_state called: resource_type={request.resource_type}, "
        f"filters={request.filters or {}}"
    )
    
    # Instantiate StateService for this request
    state_service = StateService()
    
    try:
        # Delegate to service layer for resource query
        # StateService.query_resources returns Dict[str, Any]
        result_dict = await state_service.query_resources(
            resource_type=request.resource_type,
            filters=request.filters
        )
        
        logger.info(
            f"query_state success: resource_type={request.resource_type}, "
            f"count={result_dict.get('count', 0)}"
        )
        
        # Construct QueryStateResponse from service result dict
        return QueryStateResponse(
            resource_type=result_dict.get("resource_type", request.resource_type),
            count=result_dict.get("count", 0),
            items=result_dict.get("items", [])
        )
        
    except ValueError as e:
        logger.warning(f"query_state validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resource type or filters: {str(e)}"
        )
    
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error in query_state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during state query: {str(e)}"
        )
