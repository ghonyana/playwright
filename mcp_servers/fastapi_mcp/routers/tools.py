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
for secured operations.
"""

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

# Create router with prefix and tags
router = APIRouter(
    prefix="/tools",
    tags=["mcp_tools"]
)


@router.post(
    "/seed_user",
    response_model=SeedUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create deterministic test user",
    description="Creates a test user in the application with specified role and attributes"
)
async def seed_user(
    request: SeedUserRequest,
    user_service: UserService = Depends()
) -> SeedUserResponse:
    """
    Seed User MCP Tool
    
    Creates a test user in the target application with deterministic attributes.
    This tool eliminates hardcoded test data and ensures tests start with
    known-good user accounts.
    
    Args:
        request: User creation parameters including role, email, name
        user_service: User service dependency for business logic
    
    Returns:
        SeedUserResponse with created user details
    
    Raises:
        HTTPException 409: User with given email already exists
        HTTPException 500: User creation failed
    
    Example pytest usage:
        def test_admin_operations(mcp_client):
            user = mcp_client.seed_user(role="admin", email="test@example.com")
            # Test uses this user for authentication
    """
    try:
        result = await user_service.create_test_user(
            role=request.role,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            custom_attributes=request.custom_attributes
        )
        # result is already a SeedUserResponse, return directly
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User creation failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during user creation: {str(e)}"
        )


@router.post(
    "/build_payload",
    response_model=BuildPayloadResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate API request payload from template",
    description="Builds valid JSON payload from template with parameter substitution"
)
async def build_payload(
    request: BuildPayloadRequest,
    payload_service: PayloadService = Depends()
) -> BuildPayloadResponse:
    """
    Build Payload MCP Tool
    
    Generates valid API request payloads from predefined templates with
    parameter substitution. Eliminates hardcoded request bodies in tests
    and ensures payloads match expected schemas.
    
    Args:
        request: Template name and parameters
        payload_service: Payload service dependency for template processing
    
    Returns:
        BuildPayloadResponse with generated payload
    
    Raises:
        HTTPException 400: Invalid template name or parameters
        HTTPException 500: Payload generation failed
    
    Example pytest usage:
        def test_create_user_api(mcp_client, users_api):
            payload = mcp_client.build_payload("create_user", {"role": "admin"})
            response = users_api.create(json=payload)
    """
    try:
        payload = await payload_service.build_from_template(
            template_name=request.template_name,
            parameters=request.parameters
        )
        return BuildPayloadResponse(
            template_name=request.template_name,
            payload=payload
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template name: {str(e)}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid parameters: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during payload generation: {str(e)}"
        )


@router.post(
    "/reset_env",
    response_model=ResetEnvResponse,
    status_code=status.HTTP_200_OK,
    summary="Reset test environment to known state",
    description="Clears test data and resets environment based on scope parameter",
    dependencies=[Depends(validate_bearer_token)]
)
async def reset_env(
    request: ResetEnvRequest,
    state_service: StateService = Depends()
) -> ResetEnvResponse:
    """
    Reset Environment MCP Tool
    
    Resets the test environment to a known-good state by clearing test data.
    Supports scoped resets (all, users, sessions, data) for efficient test
    isolation without full environment rebuilds.
    
    Args:
        request: Reset scope and options
        state_service: State service dependency for environment management
    
    Returns:
        ResetEnvResponse with reset status and deleted item counts
    
    Raises:
        HTTPException 403: Insufficient permissions
        HTTPException 500: Reset operation failed
    
    Example pytest usage:
        @pytest.fixture(scope="function")
        def clean_environment(mcp_client):
            mcp_client.reset_env(scope="all")
            yield
    """
    try:
        result = await state_service.reset_environment(
            scope=request.scope,
            preserve_admin=request.preserve_admin
        )
        return ResetEnvResponse(**result)
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Reset operation not permitted: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during environment reset: {str(e)}"
        )


@router.post(
    "/query_state",
    response_model=QueryStateResponse,
    status_code=status.HTTP_200_OK,
    summary="Query test environment state",
    description="Retrieves current state of test environment resources",
    dependencies=[Depends(validate_bearer_token)]
)
async def query_state(
    request: QueryStateRequest,
    state_service: StateService = Depends()
) -> QueryStateResponse:
    """
    Query State MCP Tool
    
    Queries the current state of test environment resources for debugging
    and verification. Useful for asserting environment state during tests
    and troubleshooting test failures.
    
    Args:
        request: Resource type and filter parameters
        state_service: State service dependency for state queries
    
    Returns:
        QueryStateResponse with resource list and count
    
    Raises:
        HTTPException 400: Invalid resource type
        HTTPException 500: Query operation failed
    
    Example pytest usage:
        def test_user_count(mcp_client):
            state = mcp_client.query_state(resource_type="users")
            assert state["count"] == 5
    """
    try:
        result = await state_service.query_resources(
            resource_type=request.resource_type,
            filters=request.filters
        )
        return QueryStateResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid resource type: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during state query: {str(e)}"
        )
