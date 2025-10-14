"""
Users API Client Module

Provides typed HTTP client for user management API operations with comprehensive
CRUD functionality including:
- User creation with validation via CreateUserRequest
- User retrieval by ID with UserResponse
- Paginated user listing with filters (role, status)
- User updates (full and partial) via UpdateUserRequest
- User deletion by ID
- User search by query string
- Account activation/deactivation

This client extends BaseAPIClient to inherit:
- Automatic Pydantic request/response validation
- Retry logic with exponential backoff
- Allure test report integration
- Bearer token authentication
- HTTP error handling

Integration with MCP Server:
Per Agent Action Plan Section 0.4.3, this client integrates with the FastAPI MCP
server for deterministic test data generation. Instead of hardcoded test data, tests
should use MCP's build_payload tool to generate valid CreateUserRequest payloads:

Example with MCP integration:
    # Generate test payload via MCP server
    payload = mcp_client.build_payload("create_user", {"role": "admin"})
    request = CreateUserRequest(**payload)
    
    # Execute type-safe API call
    user = users_api.create_user(request)
    assert user.role == "admin"

All methods are decorated with @allure.step for hierarchical test reporting,
showing user management operations with parameter details in test execution logs.

Usage:
    # Initialize client with authentication
    users_api = UsersAPIClient(
        base_url="https://api.example.com",
        auth_token="jwt_token_here"
    )
    
    # Create user
    new_user = users_api.create_user(
        CreateUserRequest(
            email="test@example.com",
            name="Test User",
            password="SecurePass123!"
        )
    )
    
    # List users with filtering
    users = users_api.list_users(role="admin", page=1, page_size=20)
    
    # Update user
    updated = users_api.update_user(
        user_id=new_user.id,
        request=UpdateUserRequest(department="Engineering")
    )
    
    # Search users
    results = users_api.search_users(query="test", limit=10)
    
    # Activate/deactivate
    activated = users_api.activate_user(new_user.id)
    deactivated = users_api.deactivate_user(new_user.id)
    
    # Delete user
    users_api.delete_user(new_user.id)
"""

from typing import Optional

import allure

from tests.api_clients.base_client import BaseAPIClient
from tests.api_clients.models.user_models import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
    UserListResponse,
)


class UsersAPIClient(BaseAPIClient):
    """
    Typed API client for user management endpoints.
    
    Provides type-safe methods for all user CRUD operations with automatic
    Pydantic validation ensuring API contract compliance. All operations are
    instrumented with Allure steps for comprehensive test reporting.
    
    This client follows the Page Object Pattern principles applied to API testing:
    - Encapsulates API endpoint details
    - Provides high-level business methods
    - Uses stable endpoint paths (not brittle)
    - Returns typed responses for compile-time safety
    
    Attributes:
        Inherits all attributes from BaseAPIClient including:
        - base_url (str): API base URL
        - client (httpx.Client): HTTP client instance
        - timeout (float): Request timeout
        - max_retries (int): Retry attempts
    
    Methods:
        create_user: Create new user account
        get_user: Retrieve user by ID
        list_users: List users with pagination and filtering
        update_user: Update existing user (partial or full)
        delete_user: Delete user account
        search_users: Search users by query string
        activate_user: Activate user account
        deactivate_user: Deactivate user account
    """
    
    @allure.step("Create user with email={request.email}")
    def create_user(self, request: CreateUserRequest) -> UserResponse:
        """
        Create new user account with validation.
        
        Executes POST /users with CreateUserRequest payload validated by Pydantic
        before transmission. Password must meet strength requirements (8+ chars,
        uppercase, lowercase, digit). Email must be unique in the system.
        
        Per Agent Action Plan Section 0.1.3, test data should be generated via
        MCP build_payload tool rather than hardcoded in tests to ensure
        deterministic, isolated test execution.
        
        Args:
            request: CreateUserRequest with validated user data including
                    email, name, password, and optional fields (role, age,
                    department, phone, is_active)
        
        Returns:
            UserResponse containing created user with system-assigned ID,
            timestamps (created_at, updated_at), and all user fields
        
        Raises:
            httpx.HTTPError: For HTTP errors:
                - 400 Bad Request: Invalid input or validation failure
                - 409 Conflict: Email already exists
                - 401 Unauthorized: Missing or invalid auth token
                - 500 Internal Server Error: Server-side error
            ValidationError: If response doesn't match UserResponse schema
        
        Example:
            request = CreateUserRequest(
                email="john.doe@example.com",
                name="John Doe",
                password="SecurePass123!",
                role=UserRole.ADMIN
            )
            user = users_api.create_user(request)
            print(f"Created user {user.id} with email {user.email}")
        """
        response = self.post(
            endpoint="/users",
            request_model=request,
            response_model=UserResponse
        )
        assert response is not None, "Create user response should not be None"
        return response
    
    @allure.step("Get user by ID={user_id}")
    def get_user(self, user_id: str) -> UserResponse:
        """
        Retrieve user by ID.
        
        Executes GET /users/{user_id} returning complete user record with all
        fields populated. Password is never included in responses for security.
        
        Args:
            user_id: Unique user identifier (e.g., "user_abc123")
        
        Returns:
            UserResponse containing user data including:
                - id, email, name, role
                - Optional fields: age, department, phone
                - Status fields: is_active, status
                - Timestamps: created_at, updated_at, last_login_at
        
        Raises:
            httpx.HTTPError: For HTTP errors:
                - 404 Not Found: User ID doesn't exist
                - 401 Unauthorized: Missing or invalid auth token
                - 403 Forbidden: Insufficient permissions to view user
            ValidationError: If response doesn't match UserResponse schema
        
        Example:
            user = users_api.get_user("user_abc123")
            print(f"User {user.name} has role {user.role}")
        """
        return self.get(
            endpoint=f"/users/{user_id}",
            response_model=UserResponse
        )
    
    @allure.step("List users with filters: role={role}, status={status}, page={page}")
    def list_users(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> UserListResponse:
        """
        List users with optional filtering and pagination.
        
        Executes GET /users with query parameters for filtering by role and status,
        and pagination controls. Returns paginated results with metadata indicating
        total count and available pages.
        
        Per Agent Action Plan Section 0.1.2, tests must be parallel-friendly and
        isolated, so filtering should be used to scope queries to test-specific
        users (e.g., by unique role or email pattern).
        
        Args:
            role: Optional role filter (e.g., "admin", "user", "editor")
            status: Optional status filter (e.g., "active", "inactive", "suspended")
            page: Page number (1-indexed, default: 1)
            page_size: Users per page (1-100, default: 20)
        
        Returns:
            UserListResponse containing:
                - users: List of UserResponse objects for current page
                - total: Total count matching filter criteria
                - page: Current page number
                - page_size: Users per page
                - total_pages: Total available pages
                - has_next: True if more pages exist
                - has_previous: True if previous pages exist
        
        Raises:
            httpx.HTTPError: For HTTP errors:
                - 400 Bad Request: Invalid query parameters
                - 401 Unauthorized: Missing or invalid auth token
            ValidationError: If response doesn't match UserListResponse schema
        
        Example:
            # Get first page of admin users
            admins = users_api.list_users(role="admin", page=1, page_size=50)
            print(f"Found {admins.total} admin users")
            
            # Iterate through all pages
            page = 1
            while True:
                result = users_api.list_users(page=page)
                for user in result.users:
                    process_user(user)
                if not result.has_next:
                    break
                page += 1
        """
        # Build query parameters, excluding None values per REST best practices
        params = {
            "role": role,
            "status": status,
            "page": page,
            "page_size": page_size
        }
        # Remove None values to avoid sending null query params
        params = {k: v for k, v in params.items() if v is not None}
        
        return self.get(
            endpoint="/users",
            response_model=UserListResponse,
            params=params
        )
    
    @allure.step("Update user {user_id}")
    def update_user(
        self,
        user_id: str,
        request: UpdateUserRequest
    ) -> UserResponse:
        """
        Update existing user (partial or full update).
        
        Executes PUT /users/{user_id} with UpdateUserRequest payload supporting
        PATCH semantics (all fields optional). Only provided fields will be updated
        on the target user resource, other fields remain unchanged.
        
        Args:
            user_id: Unique user identifier to update
            request: UpdateUserRequest with fields to update (all optional):
                    email, name, role, age, department, phone, is_active
        
        Returns:
            UserResponse containing updated user with new values and
            refreshed updated_at timestamp
        
        Raises:
            httpx.HTTPError: For HTTP errors:
                - 404 Not Found: User ID doesn't exist
                - 400 Bad Request: Invalid field values or validation failure
                - 409 Conflict: Email already in use by another user
                - 401 Unauthorized: Missing or invalid auth token
                - 403 Forbidden: Insufficient permissions to update user
            ValidationError: If request or response validation fails
        
        Example:
            # Partial update - only change department
            updated = users_api.update_user(
                user_id="user_abc123",
                request=UpdateUserRequest(department="Engineering")
            )
            
            # Full update - change multiple fields
            updated = users_api.update_user(
                user_id="user_abc123",
                request=UpdateUserRequest(
                    email="newemail@example.com",
                    role=UserRole.EDITOR,
                    department="Marketing"
                )
            )
        """
        return self.put(
            endpoint=f"/users/{user_id}",
            request_model=request,
            response_model=UserResponse
        )
    
    @allure.step("Delete user {user_id}")
    def delete_user(self, user_id: str) -> None:
        """
        Delete user account.
        
        Executes DELETE /users/{user_id} permanently removing the user from the
        system. This operation is typically irreversible. For temporary account
        suspension, use deactivate_user() instead.
        
        Per Agent Action Plan Section 0.1.2, tests should use MCP reset_env tool
        for cleanup rather than manual deletion, but this method is provided for
        explicit user removal scenarios.
        
        Args:
            user_id: Unique user identifier to delete
        
        Returns:
            None (successful deletion returns 204 No Content)
        
        Raises:
            httpx.HTTPError: For HTTP errors:
                - 404 Not Found: User ID doesn't exist
                - 401 Unauthorized: Missing or invalid auth token
                - 403 Forbidden: Insufficient permissions to delete user
                - 409 Conflict: Cannot delete user with dependencies
        
        Example:
            # Delete test user after test completion
            users_api.delete_user("user_test123")
            
            # Verify deletion
            try:
                users_api.get_user("user_test123")
                assert False, "User should be deleted"
            except httpx.HTTPStatusError as e:
                assert e.response.status_code == 404
        """
        self.delete(endpoint=f"/users/{user_id}")
    
    @allure.step("Search users by query='{query}' with limit={limit}")
    def search_users(self, query: str, limit: int = 10) -> UserListResponse:
        """
        Search users by name or email.
        
        Executes GET /users/search with query parameter performing text search
        across user name and email fields. Returns matching users up to specified
        limit, useful for autocomplete or user lookup scenarios.
        
        Args:
            query: Search string to match against name or email (case-insensitive)
            limit: Maximum number of results to return (1-100, default: 10)
        
        Returns:
            UserListResponse containing matching users with pagination metadata.
            The users list will contain at most 'limit' entries sorted by
            relevance or creation date (API-dependent).
        
        Raises:
            httpx.HTTPError: For HTTP errors:
                - 400 Bad Request: Invalid query or limit parameter
                - 401 Unauthorized: Missing or invalid auth token
            ValidationError: If response doesn't match UserListResponse schema
        
        Example:
            # Search for users with "john" in name or email
            results = users_api.search_users(query="john", limit=25)
            print(f"Found {len(results.users)} users matching 'john'")
            for user in results.users:
                print(f"  - {user.name} ({user.email})")
            
            # Autocomplete scenario
            search_term = "john.doe"
            suggestions = users_api.search_users(query=search_term, limit=5)
        """
        return self.get(
            endpoint="/users/search",
            response_model=UserListResponse,
            params={"q": query, "limit": limit}
        )
    
    @allure.step("Activate user {user_id}")
    def activate_user(self, user_id: str) -> UserResponse:
        """
        Activate user account.
        
        Executes POST /users/{user_id}/activate changing user's is_active flag
        to True and status to ACTIVE. Activated users can authenticate and access
        the system according to their role permissions.
        
        This operation is idempotent - activating an already-active user succeeds
        without error and returns current user state.
        
        Args:
            user_id: Unique user identifier to activate
        
        Returns:
            UserResponse containing updated user with:
                - is_active: True
                - status: UserStatus.ACTIVE
                - updated_at: Timestamp of activation
        
        Raises:
            httpx.HTTPError: For HTTP errors:
                - 404 Not Found: User ID doesn't exist
                - 401 Unauthorized: Missing or invalid auth token
                - 403 Forbidden: Insufficient permissions to activate user
        
        Example:
            # Activate suspended user account
            user = users_api.activate_user("user_abc123")
            assert user.is_active is True
            assert user.status == UserStatus.ACTIVE
            
            # Test activation workflow
            # 1. Create user as inactive
            new_user = users_api.create_user(
                CreateUserRequest(
                    email="test@example.com",
                    name="Test User",
                    password="Pass123!",
                    is_active=False
                )
            )
            # 2. Verify initial state
            assert new_user.is_active is False
            # 3. Activate account
            activated = users_api.activate_user(new_user.id)
            assert activated.is_active is True
        """
        response = self.post(
            endpoint=f"/users/{user_id}/activate",
            response_model=UserResponse
        )
        assert response is not None, "Activate user response should not be None"
        return response
    
    @allure.step("Deactivate user {user_id}")
    def deactivate_user(self, user_id: str) -> UserResponse:
        """
        Deactivate user account.
        
        Executes POST /users/{user_id}/deactivate changing user's is_active flag
        to False and status to INACTIVE. Deactivated users cannot authenticate or
        access the system. This is a soft delete - user data is preserved and
        account can be reactivated later.
        
        This operation is idempotent - deactivating an already-inactive user
        succeeds without error and returns current user state.
        
        Args:
            user_id: Unique user identifier to deactivate
        
        Returns:
            UserResponse containing updated user with:
                - is_active: False
                - status: UserStatus.INACTIVE
                - updated_at: Timestamp of deactivation
        
        Raises:
            httpx.HTTPError: For HTTP errors:
                - 404 Not Found: User ID doesn't exist
                - 401 Unauthorized: Missing or invalid auth token
                - 403 Forbidden: Insufficient permissions to deactivate user
        
        Example:
            # Deactivate user account (soft delete)
            user = users_api.deactivate_user("user_abc123")
            assert user.is_active is False
            assert user.status == UserStatus.INACTIVE
            
            # Test deactivation prevents login
            deactivated = users_api.deactivate_user("user_abc123")
            # Attempt login should fail with 401
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                auth_api.login(email=deactivated.email, password="original_password")
            assert exc_info.value.response.status_code == 401
        """
        response = self.post(
            endpoint=f"/users/{user_id}/deactivate",
            response_model=UserResponse
        )
        assert response is not None, "Expected response from deactivate_user endpoint"
        return response
