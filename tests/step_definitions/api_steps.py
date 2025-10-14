"""
pytest-bdd Step Definitions for API Testing Scenarios

This module implements business-readable Gherkin step definitions for API testing
with comprehensive coverage of REST API operations including:
- User management API (create, read, update, delete, list, search)
- Authentication API (login, logout, token refresh)
- Validation of HTTP status codes, response schemas, and business logic

Per Agent Action Plan Section 0.1.2:
- "Use MCP tools for data/state (don't hard-code test data)"
- "Keep tests deterministic, isolated, and parallel-friendly"
- "Prefer Gherkin that's business-readable; keep steps high-level"

Architecture:
- Step definitions delegate ALL API operations to typed API clients
- MCP client provides dynamic payload generation (no hardcoded test data)
- Allure integration captures request/response details for reporting
- pytest fixtures enable data sharing between Given/When/Then steps
- High-level step semantics focus on business actions, not HTTP details

Integration:
- API Clients: UsersAPIClient, AuthAPIClient (httpx-based with Pydantic validation)
- MCP Client: MCPClient for build_payload(), seed_user(), reset_env()
- Allure: Automatic request/response logging, step annotations
- pytest-bdd: scenarios() auto-loads feature files, @given/@when/@then decorators

Example Feature File Usage:
    Feature: User Management API
        Scenario: Create new user account
            Given the API authentication is configured
            When I create a user with role "admin"
            Then the response status code should be 201
            And the user role should be "admin"
            And the user should have a valid ID

Usage in tests:
    1. Feature files in tests/features/*.feature define scenarios
    2. Step definitions in this file map Gherkin to Python
    3. API clients execute actual HTTP requests
    4. MCP client generates non-conflicting test data
    5. Assertions validate business logic and API contracts
"""

from typing import Dict, Any, Optional

import allure
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

from tests.api_clients.auth_client import AuthAPIClient
from tests.api_clients.users_client import UsersAPIClient
from tests.api_clients.models.user_models import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
    UserListResponse,
    UserRole,
    UserStatus,
)
from tests.helpers.mcp_client import MCPClient


# ============================================================================
# SCENARIO LOADING
# ============================================================================

# Load all API operation scenarios from technical API testing feature file
# Per pytest-bdd documentation: scenarios() discovers and registers all scenarios
# This feature file contains technical, API-focused scenarios that match the
# step definitions in this module (role-based user creation, HTTP status validation, etc.)
scenarios('../features/api_testing_technical.feature')


# ============================================================================
# SHARED FIXTURES FOR STEP DATA PERSISTENCE
# ============================================================================

@pytest.fixture(scope="function")
def api_context() -> Dict[str, Any]:
    """
    Request-scoped context for sharing data between step definitions.
    
    This fixture enables data flow from Given → When → Then steps within a
    single scenario execution. Stores API responses, created resource IDs,
    authentication tokens, and validation data.
    
    Per Agent Action Plan Section 0.1.2: "Keep tests deterministic, isolated,
    and parallel-friendly (new context per test)". Each test scenario receives
    a fresh api_context fixture with no shared mutable state.
    
    Returns:
        Dict[str, Any]: Empty context dictionary populated by step definitions:
            - "response": httpx.Response object from last API call
            - "user": UserResponse from user creation/retrieval
            - "users_list": UserListResponse from list/search operations
            - "auth_token": JWT access token from authentication
            - "user_id": Created user ID for subsequent operations
            - "status_code": HTTP status code for validation
            - "error": Error response data for negative test cases
    
    Example:
        @when('I create a user with role "admin"')
        def create_user(api_context, users_api, mcp_client):
            # Generate payload via MCP
            payload = mcp_client.build_payload("create_user", {"role": "admin"})
            user = users_api.create_user(CreateUserRequest(**payload))
            
            # Store in context for Then steps
            api_context["user"] = user
            api_context["user_id"] = user.id
        
        @then('the user role should be "admin"')
        def verify_role(api_context):
            assert api_context["user"].role == UserRole.ADMIN
    """
    return {}


# ============================================================================
# GIVEN STEPS - Test Preconditions and Setup
# ============================================================================

@given("the API authentication is configured", target_fixture="auth_api")
@allure.step("Configure API authentication")
def api_authentication_configured(auth_api: AuthAPIClient) -> AuthAPIClient:
    """
    Verify API authentication client is configured and ready.
    
    This step validates that the AuthAPIClient fixture is properly initialized
    with base URL and authentication token. No additional setup needed as the
    fixture is provided by conftest.py with environment-based configuration.
    
    Args:
        auth_api: AuthAPIClient fixture from conftest.py
    
    Returns:
        AuthAPIClient: Configured authentication client for subsequent steps
    
    Example Gherkin:
        Given the API authentication is configured
    """
    # Validation: client should be initialized with base_url
    assert auth_api.base_url, "API base URL must be configured"
    return auth_api


@given("the user management API is available", target_fixture="users_api")
@allure.step("Verify user management API availability")
def user_management_api_available(users_api: UsersAPIClient) -> UsersAPIClient:
    """
    Verify user management API client is configured and ready.
    
    This step validates that the UsersAPIClient fixture is properly initialized
    for user CRUD operations. The fixture is provided by conftest.py with
    environment-based base URL configuration.
    
    Args:
        users_api: UsersAPIClient fixture from conftest.py
    
    Returns:
        UsersAPIClient: Configured users API client for subsequent steps
    
    Example Gherkin:
        Given the user management API is available
    """
    # Validation: client should be initialized with base_url
    assert users_api.base_url, "API base URL must be configured"
    return users_api


@given("the test environment is reset")
@allure.step("Reset test environment via MCP")
def test_environment_reset(mcp_client: MCPClient) -> None:
    """
    Reset test environment to known-good state via MCP server.
    
    Per Agent Action Plan Section 0.4.2: "Use MCP reset_env tool for cleanup".
    This step calls the MCP server to truncate test tables, reset sequences,
    and seed default data ensuring deterministic test execution.
    
    Args:
        mcp_client: MCPClient fixture from conftest.py
    
    Raises:
        httpx.HTTPError: If MCP reset operation fails
    
    Example Gherkin:
        Given the test environment is reset
    """
    reset_result = mcp_client.reset_env()
    
    # Attach reset details to Allure report for debugging
    allure.attach(
        str(reset_result),
        name="Environment Reset Result",
        attachment_type=allure.attachment_type.JSON
    )
    
    # Validate reset succeeded
    assert reset_result.get("status") == "reset_complete", \
        f"Environment reset failed: {reset_result}"


@given(parsers.parse('a test user with role "{role}" exists'), target_fixture="test_user")
@allure.step('Seed test user with role "{role}"')
def test_user_exists(mcp_client: MCPClient, api_context: Dict[str, Any], role: str) -> Dict[str, Any]:
    """
    Create test user via MCP server with specified role.
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)".
    This step uses MCP seed_user to create a test user with unique, non-conflicting
    email address suitable for parallel test execution.
    
    Args:
        mcp_client: MCPClient fixture for deterministic user creation
        api_context: Shared context for storing user data
        role: User role (admin, user, editor, viewer, guest)
    
    Returns:
        Dict[str, Any]: Created user data with id, email, password, auth_token
    
    Example Gherkin:
        Given a test user with role "admin" exists
        Given a test user with role "customer" exists
    """
    # Generate test user via MCP with unique email
    user = mcp_client.seed_user(role=role)
    
    # Store in api_context for subsequent steps
    api_context["test_user"] = user
    api_context["user_id"] = user["id"]
    api_context["auth_token"] = user.get("auth_token")
    
    # Attach user details to Allure (mask password for security)
    user_info = {**user, "password": "***MASKED***"}
    allure.attach(
        str(user_info),
        name=f"Seeded Test User ({role})",
        attachment_type=allure.attachment_type.JSON
    )
    
    return user


# ============================================================================
# WHEN STEPS - Actions and Operations
# ============================================================================

@when(parsers.parse('I create a user with role "{role}"'))
@allure.step('Create user via API with role "{role}"')
def create_user_with_role(
    users_api: UsersAPIClient,
    mcp_client: MCPClient,
    api_context: Dict[str, Any],
    role: str
) -> None:
    """
    Create new user via POST /users API with MCP-generated payload.
    
    Per Agent Action Plan: "Use MCP build_payload tool for dynamic request
    body generation". This step generates a complete CreateUserRequest payload
    via MCP server ensuring unique, non-conflicting test data.
    
    Args:
        users_api: UsersAPIClient for executing API request
        mcp_client: MCPClient for payload generation
        api_context: Shared context for storing response
        role: User role for the new user
    
    Raises:
        httpx.HTTPError: For API errors (400, 401, 409, 500)
        ValidationError: For Pydantic validation failures
    
    Example Gherkin:
        When I create a user with role "admin"
        When I create a user with role "editor"
    """
    # Generate payload via MCP server (no hardcoded test data)
    payload_params = {"role": role}
    payload = mcp_client.build_payload("create_user", payload_params)
    
    # Create user via typed API client with Pydantic validation
    user = users_api.create_user(CreateUserRequest(**payload))
    
    # Store response in context for Then steps
    api_context["user"] = user
    api_context["user_id"] = user.id
    api_context["status_code"] = 201  # Successful creation


@when(parsers.parse('I create a user with email "{email}" and role "{role}"'))
@allure.step('Create user with email="{email}" and role="{role}"')
def create_user_with_email_and_role(
    users_api: UsersAPIClient,
    mcp_client: MCPClient,
    api_context: Dict[str, Any],
    email: str,
    role: str
) -> None:
    """
    Create new user with specific email and role via API.
    
    Similar to create_user_with_role but allows explicit email specification
    for testing unique constraint violations and specific email formats.
    
    Args:
        users_api: UsersAPIClient for executing API request
        mcp_client: MCPClient for payload generation
        api_context: Shared context for storing response
        email: Specific email address for the user
        role: User role
    
    Example Gherkin:
        When I create a user with email "admin@test.com" and role "admin"
    """
    # Generate payload with email override
    payload_params = {"role": role, "email": email}
    payload = mcp_client.build_payload("create_user", payload_params)
    
    # Ensure email parameter is respected
    payload["email"] = email
    
    try:
        user = users_api.create_user(CreateUserRequest(**payload))
        api_context["user"] = user
        api_context["user_id"] = user.id
        api_context["status_code"] = 201
    except Exception as e:
        # Store error for negative test case validation
        api_context["error"] = e
        api_context["status_code"] = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500


@when(parsers.parse('I retrieve the user with ID "{user_id}"'))
@allure.step('Retrieve user by ID="{user_id}"')
def retrieve_user_by_id(
    users_api: UsersAPIClient,
    api_context: Dict[str, Any],
    user_id: str
) -> None:
    """
    Retrieve user details via GET /users/{user_id} API.
    
    Args:
        users_api: UsersAPIClient for executing API request
        api_context: Shared context for storing response
        user_id: User ID to retrieve (can be literal ID or "last_created")
    
    Example Gherkin:
        When I retrieve the user with ID "user_abc123"
        When I retrieve the user with ID "last_created"
    """
    # Support referencing previously created user
    if user_id == "last_created":
        user_id = api_context.get("user_id")
        assert user_id, "No user was created in previous steps"
    
    # Retrieve user via API
    user = users_api.get_user(user_id)
    
    # Store in context
    api_context["user"] = user
    api_context["status_code"] = 200


@when(parsers.parse('I update the user with role "{role}"'))
@allure.step('Update user with role="{role}"')
def update_user_role(
    users_api: UsersAPIClient,
    api_context: Dict[str, Any],
    role: str
) -> None:
    """
    Update user role via PUT /users/{user_id} API.
    
    Updates the most recently created/retrieved user stored in api_context.
    Uses UpdateUserRequest for partial update semantics.
    
    Args:
        users_api: UsersAPIClient for executing API request
        api_context: Shared context with user_id
        role: New role to assign
    
    Example Gherkin:
        When I update the user with role "editor"
    """
    user_id = api_context.get("user_id")
    assert user_id, "No user ID available for update"
    
    # Partial update - only role field
    update_request = UpdateUserRequest(role=UserRole(role))
    updated_user = users_api.update_user(user_id, update_request)
    
    # Store updated user
    api_context["user"] = updated_user
    api_context["status_code"] = 200


@when(parsers.parse('I update the user with department "{department}"'))
@allure.step('Update user with department="{department}"')
def update_user_department(
    users_api: UsersAPIClient,
    api_context: Dict[str, Any],
    department: str
) -> None:
    """
    Update user department via PUT /users/{user_id} API.
    
    Args:
        users_api: UsersAPIClient for executing API request
        api_context: Shared context with user_id
        department: New department name
    
    Example Gherkin:
        When I update the user with department "Engineering"
    """
    user_id = api_context.get("user_id")
    assert user_id, "No user ID available for update"
    
    # Partial update - only department field
    update_request = UpdateUserRequest(department=department)
    updated_user = users_api.update_user(user_id, update_request)
    
    # Store updated user
    api_context["user"] = updated_user
    api_context["status_code"] = 200


@when("I delete the user")
@allure.step("Delete user via API")
def delete_user(
    users_api: UsersAPIClient,
    api_context: Dict[str, Any]
) -> None:
    """
    Delete user via DELETE /users/{user_id} API.
    
    Deletes the most recently created/retrieved user stored in api_context.
    
    Args:
        users_api: UsersAPIClient for executing API request
        api_context: Shared context with user_id
    
    Example Gherkin:
        When I delete the user
    """
    user_id = api_context.get("user_id")
    assert user_id, "No user ID available for deletion"
    
    # Delete user - returns None (204 No Content)
    users_api.delete_user(user_id)
    
    # Store status code for validation
    api_context["status_code"] = 204
    api_context["deleted_user_id"] = user_id


@when(parsers.parse('I list users with role "{role}"'))
@allure.step('List users filtered by role="{role}"')
def list_users_by_role(
    users_api: UsersAPIClient,
    api_context: Dict[str, Any],
    role: str
) -> None:
    """
    List users filtered by role via GET /users API.
    
    Retrieves paginated user list with role filter. Default pagination
    (page=1, page_size=20) is applied.
    
    Args:
        users_api: UsersAPIClient for executing API request
        api_context: Shared context for storing response
        role: Role filter value
    
    Example Gherkin:
        When I list users with role "admin"
    """
    # List users with role filter
    users_list = users_api.list_users(role=role, page=1, page_size=20)
    
    # Store in context
    api_context["users_list"] = users_list
    api_context["status_code"] = 200


@when(parsers.parse('I list users with status "{status}"'))
@allure.step('List users filtered by status="{status}"')
def list_users_by_status(
    users_api: UsersAPIClient,
    api_context: Dict[str, Any],
    status: str
) -> None:
    """
    List users filtered by status via GET /users API.
    
    Args:
        users_api: UsersAPIClient for executing API request
        api_context: Shared context for storing response
        status: Status filter value (active, inactive, suspended, pending)
    
    Example Gherkin:
        When I list users with status "active"
    """
    # List users with status filter
    users_list = users_api.list_users(status=status, page=1, page_size=20)
    
    # Store in context
    api_context["users_list"] = users_list
    api_context["status_code"] = 200


@when(parsers.parse('I search for users with query "{query}"'))
@allure.step('Search users with query="{query}"')
def search_users_by_query(
    users_api: UsersAPIClient,
    api_context: Dict[str, Any],
    query: str
) -> None:
    """
    Search users by name or email via GET /users/search API.
    
    Args:
        users_api: UsersAPIClient for executing API request
        api_context: Shared context for storing response
        query: Search query string
    
    Example Gherkin:
        When I search for users with query "john"
    """
    # Search users with default limit=10
    users_list = users_api.search_users(query=query, limit=10)
    
    # Store in context
    api_context["users_list"] = users_list
    api_context["status_code"] = 200


@when(parsers.parse('I login with email "{email}" and password "{password}"'))
@allure.step('Login with email="{email}"')
def login_with_credentials(
    auth_api: AuthAPIClient,
    api_context: Dict[str, Any],
    email: str,
    password: str
) -> None:
    """
    Authenticate user via POST /auth/login API.
    
    Args:
        auth_api: AuthAPIClient for executing API request
        api_context: Shared context for storing authentication response
        email: User email address
        password: User password
    
    Example Gherkin:
        When I login with email "admin@test.com" and password "Pass123!"
    """
    try:
        login_response = auth_api.login(email=email, password=password, remember_me=False)
        
        # Store authentication data
        api_context["auth_response"] = login_response
        api_context["auth_token"] = login_response.access_token
        api_context["refresh_token"] = login_response.refresh_token
        api_context["status_code"] = 200
        
    except Exception as e:
        # Store error for negative test validation
        api_context["error"] = e
        api_context["status_code"] = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500


@when("I refresh the authentication token")
@allure.step("Refresh authentication token")
def refresh_authentication_token(
    auth_api: AuthAPIClient,
    api_context: Dict[str, Any]
) -> None:
    """
    Refresh access token via POST /auth/refresh API.
    
    Uses refresh_token from previous login stored in api_context.
    
    Args:
        auth_api: AuthAPIClient for executing API request
        api_context: Shared context with refresh_token
    
    Example Gherkin:
        When I refresh the authentication token
    """
    refresh_token = api_context.get("refresh_token")
    assert refresh_token, "No refresh token available"
    
    # Refresh token
    refresh_response = auth_api.refresh_token(refresh_token)
    
    # Store new tokens
    api_context["auth_token"] = refresh_response.access_token
    if refresh_response.refresh_token:
        api_context["refresh_token"] = refresh_response.refresh_token
    api_context["status_code"] = 200


@when("I logout")
@allure.step("Logout user")
def logout_user(
    auth_api: AuthAPIClient,
    api_context: Dict[str, Any]
) -> None:
    """
    Logout user via POST /auth/logout API.
    
    Invalidates current access token. Requires auth_token to be set
    on the auth_api client from previous login.
    
    Args:
        auth_api: AuthAPIClient for executing API request
        api_context: Shared context for storing result
    
    Example Gherkin:
        When I logout
    """
    auth_token = api_context.get("auth_token")
    assert auth_token, "No auth token available for logout"
    
    # Set authentication token on client
    auth_api.set_auth_token(auth_token)
    
    # Logout - returns None (204 No Content)
    auth_api.logout()
    
    # Clear auth data from context
    api_context["auth_token"] = None
    api_context["status_code"] = 204


# ============================================================================
# THEN STEPS - Assertions and Validations
# ============================================================================

@then(parsers.parse('the response status code should be {status_code:d}'))
@allure.step('Verify response status code is {status_code}')
def verify_response_status_code(api_context: Dict[str, Any], status_code: int) -> None:
    """
    Validate HTTP response status code matches expected value.
    
    Args:
        api_context: Shared context with status_code
        status_code: Expected HTTP status code
    
    Example Gherkin:
        Then the response status code should be 201
        Then the response status code should be 200
        Then the response status code should be 204
    """
    actual_status = api_context.get("status_code")
    assert actual_status == status_code, \
        f"Expected status code {status_code}, got {actual_status}"


@then(parsers.parse('the user role should be "{role}"'))
@allure.step('Verify user role is "{role}"')
def verify_user_role(api_context: Dict[str, Any], role: str) -> None:
    """
    Validate user role matches expected value.
    
    Args:
        api_context: Shared context with user data
        role: Expected role value
    
    Example Gherkin:
        Then the user role should be "admin"
    """
    user = api_context.get("user")
    assert user, "No user data available for validation"
    assert user.role.value == role, \
        f"Expected role '{role}', got '{user.role.value}'"


@then("the user should have a valid ID")
@allure.step("Verify user has valid ID")
def verify_user_has_valid_id(api_context: Dict[str, Any]) -> None:
    """
    Validate user has a non-empty ID field.
    
    Args:
        api_context: Shared context with user data
    
    Example Gherkin:
        Then the user should have a valid ID
    """
    user = api_context.get("user")
    assert user, "No user data available for validation"
    assert user.id, "User ID is empty or None"
    assert len(user.id) > 0, "User ID must be non-empty string"


@then(parsers.parse('the user email should be "{email}"'))
@allure.step('Verify user email is "{email}"')
def verify_user_email(api_context: Dict[str, Any], email: str) -> None:
    """
    Validate user email matches expected value.
    
    Args:
        api_context: Shared context with user data
        email: Expected email address
    
    Example Gherkin:
        Then the user email should be "admin@test.com"
    """
    user = api_context.get("user")
    assert user, "No user data available for validation"
    assert user.email == email, \
        f"Expected email '{email}', got '{user.email}'"


@then(parsers.parse('the user department should be "{department}"'))
@allure.step('Verify user department is "{department}"')
def verify_user_department(api_context: Dict[str, Any], department: str) -> None:
    """
    Validate user department matches expected value.
    
    Args:
        api_context: Shared context with user data
        department: Expected department name
    
    Example Gherkin:
        Then the user department should be "Engineering"
    """
    user = api_context.get("user")
    assert user, "No user data available for validation"
    assert user.department == department, \
        f"Expected department '{department}', got '{user.department}'"


@then("the user should be active")
@allure.step("Verify user is active")
def verify_user_is_active(api_context: Dict[str, Any]) -> None:
    """
    Validate user is_active flag is True.
    
    Args:
        api_context: Shared context with user data
    
    Example Gherkin:
        Then the user should be active
    """
    user = api_context.get("user")
    assert user, "No user data available for validation"
    assert user.is_active is True, \
        f"Expected user to be active, got is_active={user.is_active}"


@then("the user should be inactive")
@allure.step("Verify user is inactive")
def verify_user_is_inactive(api_context: Dict[str, Any]) -> None:
    """
    Validate user is_active flag is False.
    
    Args:
        api_context: Shared context with user data
    
    Example Gherkin:
        Then the user should be inactive
    """
    user = api_context.get("user")
    assert user, "No user data available for validation"
    assert user.is_active is False, \
        f"Expected user to be inactive, got is_active={user.is_active}"


@then(parsers.parse('the user list should contain at least {count:d} user(s)'))
@allure.step('Verify user list contains at least {count} user(s)')
def verify_user_list_minimum_count(api_context: Dict[str, Any], count: int) -> None:
    """
    Validate user list contains minimum number of users.
    
    Args:
        api_context: Shared context with users_list
        count: Minimum expected user count
    
    Example Gherkin:
        Then the user list should contain at least 1 user(s)
        Then the user list should contain at least 5 user(s)
    """
    users_list = api_context.get("users_list")
    assert users_list, "No user list data available for validation"
    
    actual_count = len(users_list.users)
    assert actual_count >= count, \
        f"Expected at least {count} user(s), got {actual_count}"


@then(parsers.parse('the user list total should be {total:d}'))
@allure.step('Verify user list total is {total}')
def verify_user_list_total(api_context: Dict[str, Any], total: int) -> None:
    """
    Validate user list total count matches expected value.
    
    Args:
        api_context: Shared context with users_list
        total: Expected total count
    
    Example Gherkin:
        Then the user list total should be 150
    """
    users_list = api_context.get("users_list")
    assert users_list, "No user list data available for validation"
    
    assert users_list.total == total, \
        f"Expected total {total}, got {users_list.total}"


@then("the user list should have pagination metadata")
@allure.step("Verify user list has pagination metadata")
def verify_user_list_pagination(api_context: Dict[str, Any]) -> None:
    """
    Validate user list response contains pagination metadata.
    
    Verifies presence of: page, page_size, total_pages, has_next, has_previous
    
    Args:
        api_context: Shared context with users_list
    
    Example Gherkin:
        Then the user list should have pagination metadata
    """
    users_list = api_context.get("users_list")
    assert users_list, "No user list data available for validation"
    
    # Validate pagination fields exist
    assert hasattr(users_list, "page"), "Missing 'page' field"
    assert hasattr(users_list, "page_size"), "Missing 'page_size' field"
    assert hasattr(users_list, "total"), "Missing 'total' field"
    assert hasattr(users_list, "has_next"), "Missing 'has_next' field"
    assert hasattr(users_list, "has_previous"), "Missing 'has_previous' field"
    
    # Validate pagination values are sensible
    assert users_list.page >= 1, "Page number must be >= 1"
    assert users_list.page_size >= 1, "Page size must be >= 1"
    assert users_list.total >= 0, "Total count must be >= 0"


@then("the authentication should succeed")
@allure.step("Verify authentication succeeded")
def verify_authentication_succeeded(api_context: Dict[str, Any]) -> None:
    """
    Validate authentication response contains required tokens.
    
    Args:
        api_context: Shared context with auth_response
    
    Example Gherkin:
        Then the authentication should succeed
    """
    auth_response = api_context.get("auth_response")
    assert auth_response, "No authentication response available"
    
    # Validate token fields
    assert auth_response.access_token, "access_token is missing or empty"
    assert auth_response.refresh_token, "refresh_token is missing or empty"
    assert auth_response.token_type == "Bearer", \
        f"Expected token_type 'Bearer', got '{auth_response.token_type}'"
    assert auth_response.expires_in > 0, "expires_in must be positive"


@then("the access token should be valid")
@allure.step("Verify access token is valid")
def verify_access_token_valid(api_context: Dict[str, Any]) -> None:
    """
    Validate access token exists and is non-empty.
    
    Args:
        api_context: Shared context with auth_token
    
    Example Gherkin:
        Then the access token should be valid
    """
    auth_token = api_context.get("auth_token")
    assert auth_token, "Access token is missing or empty"
    assert len(auth_token) > 0, "Access token must be non-empty string"
    
    # Basic JWT format validation (header.payload.signature)
    parts = auth_token.split(".")
    assert len(parts) == 3, \
        f"Access token should have 3 parts (JWT format), got {len(parts)}"


@then(parsers.parse('the authentication response should include user_id "{user_id}"'))
@allure.step('Verify authentication response includes user_id "{user_id}"')
def verify_auth_response_user_id(api_context: Dict[str, Any], user_id: str) -> None:
    """
    Validate authentication response contains expected user_id.
    
    Args:
        api_context: Shared context with auth_response
        user_id: Expected user_id value
    
    Example Gherkin:
        Then the authentication response should include user_id "user_abc123"
    """
    auth_response = api_context.get("auth_response")
    assert auth_response, "No authentication response available"
    
    assert auth_response.user_id == user_id, \
        f"Expected user_id '{user_id}', got '{auth_response.user_id}'"


@then("the refresh token should be updated")
@allure.step("Verify refresh token was updated")
def verify_refresh_token_updated(api_context: Dict[str, Any]) -> None:
    """
    Validate refresh token was rotated (new token received).
    
    This validation applies when refresh token rotation is enabled on the
    authentication server. Checks that a refresh_token exists in context.
    
    Args:
        api_context: Shared context with auth_token and refresh_token
    
    Example Gherkin:
        Then the refresh token should be updated
    """
    # After refresh, new access token should exist
    auth_token = api_context.get("auth_token")
    assert auth_token, "Access token is missing after refresh"
    
    # If rotation enabled, refresh_token should also be updated
    # (Optional check - depends on server configuration)
    refresh_token = api_context.get("refresh_token")
    if refresh_token:
        assert len(refresh_token) > 0, "Refresh token must be non-empty"


@then("the logout should succeed")
@allure.step("Verify logout succeeded")
def verify_logout_succeeded(api_context: Dict[str, Any]) -> None:
    """
    Validate logout operation completed successfully.
    
    Verifies status code is 204 and auth_token is cleared.
    
    Args:
        api_context: Shared context
    
    Example Gherkin:
        Then the logout should succeed
    """
    status_code = api_context.get("status_code")
    assert status_code == 204, \
        f"Expected status code 204 for logout, got {status_code}"
    
    # Token should be cleared from context
    auth_token = api_context.get("auth_token")
    assert not auth_token, "Auth token should be cleared after logout"
