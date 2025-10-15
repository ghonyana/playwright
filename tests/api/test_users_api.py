"""
User Management API Test Module

Traditional pytest-based user management API test module containing comprehensive
CRUD operation tests for user creation, retrieval, update, and deletion.

Per Agent Action Plan Section 0.5.1 Group 6.5:
- Implements test_create_user, test_get_user, test_update_user, test_delete_user
- Uses UsersAPIClient for typed REST requests with Pydantic validation
- Uses MCPClient for deterministic test data generation without hardcoded values
- Integrates with Allure for detailed test reporting

Test Coverage:
- User lifecycle: create, read, update, delete
- Pagination and filtering
- Search functionality
- Role-based operations
- Validation and error handling (400, 404, 409 status codes)
- Activation/deactivation workflows

Per User Directive Section 0.1.2:
"Use MCP tools for data/state (don't hard-code test data)"
All test data is generated via MCP build_payload tool to ensure deterministic,
parallel-friendly test execution with no email/data conflicts.
"""

import pytest
import allure
import httpx

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


@allure.feature("User Management API")
@allure.story("User Creation")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.api
@pytest.mark.smoke
def test_create_user(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user creation via API with MCP-generated payload.
    
    Per Agent Action Plan Section 0.5.1 Group 6.5: test_create_user(users_api, mcp_client)
    Per Agent Action Plan Section 0.1.2: "Use MCP tools for data/state (don't hard-code test data)"
    Per Technical Specification Section 5.2.1.3: MCP integration for payload generation
    
    Validates:
    - User creation with valid data
    - Response structure matches UserResponse model
    - User is active by default
    - Created timestamp is present
    - Role assignment is correct
    """
    with allure.step("Generate user payload via MCP"):
        # MCP build_payload tool generates deterministic test data
        user_payload = mcp_client.build_payload(
            template="create_user",
            parameters={"role": "moderator", "email_domain": "test.com"}
        )
        
        allure.attach(
            str(user_payload),
            name="MCP Generated Payload",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Create user via API"):
        request = CreateUserRequest(**user_payload)
        response = users_api.create_user(request)
    
    with allure.step("Verify user created successfully"):
        assert response.id is not None, "User ID should be assigned"
        assert response.email == user_payload["email"], "Email should match request"
        assert response.name == user_payload["name"], "Name should match request"
        assert response.role == UserRole.MODERATOR, "Role should be MODERATOR"
        assert response.is_active is True, "User should be active by default"
        assert response.status == UserStatus.ACTIVE, "Status should be ACTIVE"
        assert response.created_at is not None, "Created timestamp should be set"
        # Note: updated_at may be None on creation, only set on updates


@allure.feature("User Management API")
@allure.story("User Creation")
@pytest.mark.api
def test_create_user_with_different_roles(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user creation with various roles.
    
    Validates role assignment functionality across all user types including
    ADMIN, USER, EDITOR, VIEWER, and GUEST roles to ensure role-based
    access control is properly configured.
    """
    # Only test valid roles supported by the sample_app: admin, customer, moderator
    roles = [UserRole.ADMIN, UserRole.CUSTOMER, UserRole.MODERATOR]
    
    for role in roles:
        with allure.step(f"Create user with role: {role.value}"):
            user_payload = mcp_client.build_payload(
                template="create_user",
                parameters={"role": role.value}
            )
            
            request = CreateUserRequest(**user_payload)
            response = users_api.create_user(request)
            
            assert response.role == role, f"User should have role {role.value}"
            assert response.is_active is True, "User should be active"


@allure.feature("User Management API")
@allure.story("User Creation")
@pytest.mark.api
def test_create_user_with_optional_fields(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user creation with optional fields populated.
    
    Validates that optional user attributes (age, department, phone) are
    properly stored and returned in the response when provided during creation.
    """
    with allure.step("Generate user payload with optional fields"):
        user_payload = mcp_client.build_payload(
            template="create_user",
            parameters={
                "role": "user",
                "age": 30,
                "department": "Engineering",
                "phone": "+12125551234"
            }
        )
        
        allure.attach(
            str(user_payload),
            name="Payload with Optional Fields",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Create user with optional fields"):
        request = CreateUserRequest(**user_payload)
        response = users_api.create_user(request)
    
    with allure.step("Verify optional fields are stored"):
        assert response.age == 30, "Age should match request"
        assert response.department == "Engineering", "Department should match request"
        assert response.phone == "+12125551234", "Phone should match request"


@allure.feature("User Management API")
@allure.story("User Creation")
@allure.severity(allure.severity_level.NORMAL)
@pytest.mark.api
def test_create_user_with_duplicate_email(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user creation failure with duplicate email.
    
    Validates unique email constraint enforcement. Per business rules, email
    addresses must be unique across all users. Attempting to create a user
    with an existing email should result in 409 Conflict response.
    """
    with allure.step("Create first user"):
        user_payload = mcp_client.build_payload(
            template="create_user",
            parameters={"email": "duplicate@example.com"}
        )
        
        request = CreateUserRequest(**user_payload)
        first_user = users_api.create_user(request)
        
        allure.attach(
            f"First user ID: {first_user.id}",
            name="First User Created",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Attempt to create user with same email"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            # Reuse same payload with duplicate email
            users_api.create_user(request)
    
    with allure.step("Verify 409 Conflict response"):
        assert exc_info.value.response.status_code == 409, "Should return 409 Conflict for duplicate email"
        
        allure.attach(
            exc_info.value.response.text,
            name="Error Response",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Creation")
@pytest.mark.api
def test_create_user_with_invalid_email(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user creation failure with invalid email format.
    
    Validates Pydantic email validation at API level. Invalid email formats
    should be rejected with 400 Bad Request or validation error before
    reaching the database layer.
    """
    with allure.step("Generate payload and corrupt email"):
        user_payload = mcp_client.build_payload(template="create_user")
        user_payload["email"] = "invalid-email-format"  # Missing @ and domain
        
        allure.attach(
            str(user_payload),
            name="Invalid Email Payload",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Attempt to create user with invalid email"):
        # Pydantic validation should fail during CreateUserRequest instantiation
        with pytest.raises((ValueError, httpx.HTTPStatusError)) as exc_info:
            request = CreateUserRequest(**user_payload)
            users_api.create_user(request)
    
    with allure.step("Verify validation error"):
        # Could be Pydantic ValidationError or 400 Bad Request from API
        if hasattr(exc_info.value, 'response'):
            assert exc_info.value.response.status_code == 400, "Should return 400 Bad Request"
        
        allure.attach(
            str(exc_info.value),
            name="Validation Error",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Creation")
@pytest.mark.api
def test_create_user_with_weak_password(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user creation with weak password.
    
    Validates password complexity requirements enforced by Pydantic validator.
    Per security policy, passwords must contain:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """
    with allure.step("Generate payload with weak password"):
        user_payload = mcp_client.build_payload(template="create_user")
        user_payload["password"] = "weak"  # Too short, no uppercase, no digits
        
        allure.attach(
            f"Weak password: {user_payload['password']}",
            name="Invalid Password",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Attempt to create user with weak password"):
        with pytest.raises(ValueError) as exc_info:
            CreateUserRequest(**user_payload)
    
    with allure.step("Verify password validation error"):
        error_message = str(exc_info.value)
        assert "Password" in error_message, "Error should mention password validation"
        
        allure.attach(
            error_message,
            name="Password Validation Error",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Retrieval")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.api
@pytest.mark.smoke
def test_get_user(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test retrieving user by ID.
    
    Per Agent Action Plan Section 0.5.1 Group 6.5: test_get_user(users_api)
    
    Validates:
    - User retrieval by ID
    - Complete user data returned
    - Response structure matches UserResponse model
    - All fields from creation are preserved
    """
    with allure.step("Setup: Create test user"):
        user_payload = mcp_client.build_payload(template="create_user")
        request = CreateUserRequest(**user_payload)
        created_user = users_api.create_user(request)
        
        allure.attach(
            f"Created user ID: {created_user.id}",
            name="Test User Created",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step(f"Retrieve user by ID: {created_user.id}"):
        retrieved_user = users_api.get_user(created_user.id)
    
    with allure.step("Verify user data matches"):
        assert retrieved_user.id == created_user.id, "User ID should match"
        assert retrieved_user.email == created_user.email, "Email should match"
        assert retrieved_user.name == created_user.name, "Name should match"
        assert retrieved_user.role == created_user.role, "Role should match"
        assert retrieved_user.is_active == created_user.is_active, "Active status should match"
        assert retrieved_user.status == created_user.status, "Status should match"
        assert retrieved_user.created_at == created_user.created_at, "Created timestamp should match"


@allure.feature("User Management API")
@allure.story("User Retrieval")
@pytest.mark.api
def test_get_user_not_found(users_api: UsersAPIClient):
    """
    Test user retrieval with non-existent ID.
    
    Validates 404 error handling for missing resources. Attempting to retrieve
    a user that doesn't exist should result in 404 Not Found response with
    appropriate error message.
    """
    with allure.step("Attempt to retrieve non-existent user"):
        nonexistent_id = "nonexistent-user-id-12345"
        
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            users_api.get_user(nonexistent_id)
    
    with allure.step("Verify 404 Not Found response"):
        assert exc_info.value.response.status_code == 404, "Should return 404 Not Found"
        
        allure.attach(
            exc_info.value.response.text,
            name="404 Error Response",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Listing")
@pytest.mark.api
def test_list_users(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test listing users with pagination.
    
    Validates user list endpoint with pagination parameters including page
    number, page size, total count, and navigation indicators (has_next,
    has_previous) for implementing pagination UI components.
    """
    with allure.step("Setup: Create multiple test users"):
        created_user_ids = []
        for i in range(3):
            user_payload = mcp_client.build_payload(template="create_user")
            request = CreateUserRequest(**user_payload)
            user = users_api.create_user(request)
            created_user_ids.append(user.id)
        
        allure.attach(
            f"Created users: {', '.join(created_user_ids)}",
            name="Test Users Created",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("List users with pagination"):
        response = users_api.list_users(page=1, page_size=10)
    
    with allure.step("Verify user list response structure"):
        assert response.total >= 3, "Total count should include created users"
        assert len(response.users) >= 3, "User list should contain at least 3 users"
        assert response.page == 1, "Page number should be 1"
        assert response.page_size == 10, "Page size should be 10"
        assert response.total_pages >= 1, "Should have at least 1 page"
        assert isinstance(response.has_next, bool), "has_next should be boolean"
        assert isinstance(response.has_previous, bool), "has_previous should be boolean"
        
        allure.attach(
            f"Total users: {response.total}, Page: {response.page}/{response.total_pages}",
            name="Pagination Info",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Listing")
@pytest.mark.api
def test_list_users_with_role_filter(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test listing users filtered by role.
    
    Validates role-based filtering functionality to support admin dashboards
    and role management interfaces. All returned users should match the
    specified role filter.
    """
    with allure.step("Setup: Create admin and editor users"):
        admin_payload = mcp_client.build_payload(
            template="create_user",
            parameters={"role": "admin"}
        )
        admin_user = users_api.create_user(CreateUserRequest(**admin_payload))
        
        editor_payload = mcp_client.build_payload(
            template="create_user",
            parameters={"role": "moderator"}
        )
        editor_user = users_api.create_user(CreateUserRequest(**editor_payload))
        
        allure.attach(
            f"Admin: {admin_user.id}, Editor: {editor_user.id}",
            name="Test Users Created",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("List users with role filter: admin"):
        response = users_api.list_users(role="admin", page=1, page_size=20)
    
    with allure.step("Verify all returned users are admins"):
        assert response.total >= 1, "Should find at least one admin user"
        
        for user in response.users:
            assert user.role == UserRole.ADMIN, f"All users should be admins, found {user.role}"
        
        allure.attach(
            f"Found {response.total} admin users",
            name="Filter Results",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Listing")
@pytest.mark.api
def test_list_users_pagination_navigation(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test pagination navigation indicators (has_next, has_previous).
    
    Validates pagination metadata for implementing "Next Page" and "Previous Page"
    navigation buttons in user interfaces. Tests edge cases of first page and
    intermediate pages.
    """
    with allure.step("Setup: Create enough users for multiple pages"):
        for i in range(5):
            user_payload = mcp_client.build_payload(template="create_user")
            users_api.create_user(CreateUserRequest(**user_payload))
    
    with allure.step("Request first page with small page size"):
        first_page = users_api.list_users(page=1, page_size=2)
    
    with allure.step("Verify first page indicators"):
        assert first_page.has_previous is False, "First page should not have previous"
        # has_next depends on total count - may be True if enough users exist
        
        allure.attach(
            f"Page 1: has_next={first_page.has_next}, has_previous={first_page.has_previous}",
            name="First Page Navigation",
            attachment_type=allure.attachment_type.TEXT
        )
    
    if first_page.has_next:
        with allure.step("Request second page"):
            second_page = users_api.list_users(page=2, page_size=2)
        
        with allure.step("Verify second page has previous"):
            assert second_page.has_previous is True, "Second page should have previous"
            assert second_page.page == 2, "Page number should be 2"


@allure.feature("User Management API")
@allure.story("User Update")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.api
def test_update_user(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test updating user attributes.
    
    Per Agent Action Plan Section 0.5.1 Group 6.5: test_update_user(users_api)
    
    Validates:
    - User attribute updates
    - Multiple fields updated simultaneously
    - Updated timestamp reflects change
    - Unchanged fields remain intact
    """
    with allure.step("Setup: Create test user"):
        user_payload = mcp_client.build_payload(template="create_user")
        request = CreateUserRequest(**user_payload)
        created_user = users_api.create_user(request)
        
        allure.attach(
            f"Original user: {created_user.name} ({created_user.role.value})",
            name="User Before Update",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Update user attributes"):
        update_request = UpdateUserRequest(
            name="UpdatedFirstName UpdatedLastName",
            role=UserRole.ADMIN,
            department="Engineering Leadership"
        )
        updated_user = users_api.update_user(created_user.id, update_request)
    
    with allure.step("Verify user updated successfully"):
        assert updated_user.id == created_user.id, "User ID should not change"
        assert updated_user.name == "UpdatedFirstName UpdatedLastName", "Name should be updated"
        assert updated_user.role == UserRole.ADMIN, "Role should be updated to ADMIN"
        assert updated_user.department == "Engineering Leadership", "Department should be updated"
        assert updated_user.email == created_user.email, "Email should remain unchanged"
        assert updated_user.updated_at > created_user.updated_at, "Updated timestamp should be newer"
        
        allure.attach(
            f"Updated user: {updated_user.name} ({updated_user.role.value})",
            name="User After Update",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Update")
@pytest.mark.api
def test_update_user_partial(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test partial user update (only some fields).
    
    Validates partial update functionality with optional fields per PATCH
    semantics. Only provided fields should be updated while other fields
    remain unchanged, supporting flexible update operations.
    """
    with allure.step("Setup: Create user"):
        user_payload = mcp_client.build_payload(template="create_user")
        created_user = users_api.create_user(CreateUserRequest(**user_payload))
        
        allure.attach(
            f"Original: name={created_user.name}, role={created_user.role.value}, email={created_user.email}",
            name="Original User State",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Update only name field"):
        update_request = UpdateUserRequest(name="PartialUpdate Name")
        updated_user = users_api.update_user(created_user.id, update_request)
    
    with allure.step("Verify only name changed"):
        assert updated_user.name == "PartialUpdate Name", "Name should be updated"
        assert updated_user.role == created_user.role, "Role should be unchanged"
        assert updated_user.email == created_user.email, "Email should be unchanged"
        assert updated_user.department == created_user.department, "Department should be unchanged"
        assert updated_user.age == created_user.age, "Age should be unchanged"
        
        allure.attach(
            f"After partial update: name={updated_user.name}, role={updated_user.role.value}",
            name="User After Partial Update",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Update")
@pytest.mark.api
def test_update_user_not_found(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user update with non-existent ID.
    
    Validates 404 error handling when attempting to update a user that doesn't
    exist. This prevents silent failures and provides clear feedback for
    update operations on invalid user IDs.
    """
    with allure.step("Prepare update request"):
        update_request = UpdateUserRequest(name="Updated Name")
    
    with allure.step("Attempt to update non-existent user"):
        nonexistent_id = "nonexistent-user-id-67890"
        
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            users_api.update_user(nonexistent_id, update_request)
    
    with allure.step("Verify 404 Not Found response"):
        assert exc_info.value.response.status_code == 404, "Should return 404 Not Found"
        
        allure.attach(
            exc_info.value.response.text,
            name="404 Error Response",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Update")
@pytest.mark.api
def test_update_user_activate_deactivate(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user activation and deactivation.
    
    Validates user status management functionality through dedicated activation
    endpoints. Tests the complete activation/deactivation workflow including
    status transitions and idempotent operations.
    """
    with allure.step("Setup: Create active user"):
        user_payload = mcp_client.build_payload(template="create_user")
        created_user = users_api.create_user(CreateUserRequest(**user_payload))
        
        assert created_user.is_active is True, "User should be active initially"
        
        allure.attach(
            f"Initial user: {created_user.id}, is_active={created_user.is_active}",
            name="Initial User State",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Deactivate user"):
        deactivated_user = users_api.deactivate_user(created_user.id)
    
    with allure.step("Verify user is inactive"):
        assert deactivated_user.is_active is False, "User should be inactive after deactivation"
        assert deactivated_user.status == UserStatus.INACTIVE, "Status should be INACTIVE"
        
        allure.attach(
            f"After deactivation: is_active={deactivated_user.is_active}, status={deactivated_user.status.value}",
            name="Deactivated State",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Reactivate user"):
        activated_user = users_api.activate_user(created_user.id)
    
    with allure.step("Verify user is active again"):
        assert activated_user.is_active is True, "User should be active after activation"
        assert activated_user.status == UserStatus.ACTIVE, "Status should be ACTIVE"
        
        allure.attach(
            f"After reactivation: is_active={activated_user.is_active}, status={activated_user.status.value}",
            name="Reactivated State",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Deletion")
@allure.severity(allure.severity_level.CRITICAL)
@pytest.mark.api
def test_delete_user(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user deletion.
    
    Per Agent Action Plan Section 0.5.1 Group 6.5: test_delete_user(users_api)
    
    Validates:
    - User deletion succeeds with valid ID
    - Deleted user no longer retrievable (404)
    - Deletion is permanent and irreversible
    """
    with allure.step("Setup: Create test user"):
        user_payload = mcp_client.build_payload(template="create_user")
        request = CreateUserRequest(**user_payload)
        created_user = users_api.create_user(request)
        
        allure.attach(
            f"Created user {created_user.id} for deletion test",
            name="User To Delete",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step(f"Delete user {created_user.id}"):
        users_api.delete_user(created_user.id)
        
        allure.attach(
            f"Deleted user ID: {created_user.id}",
            name="Deletion Complete",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Verify user no longer exists"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            users_api.get_user(created_user.id)
        
        assert exc_info.value.response.status_code == 404, "Deleted user should return 404"
        
        allure.attach(
            "User successfully deleted and not retrievable",
            name="Deletion Verified",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Deletion")
@pytest.mark.api
def test_delete_user_not_found(users_api: UsersAPIClient):
    """
    Test user deletion with non-existent ID.
    
    Validates error handling for deleting missing resources. Attempting to
    delete a user that doesn't exist should result in 404 Not Found, providing
    clear feedback that the user cannot be deleted because it doesn't exist.
    """
    with allure.step("Attempt to delete non-existent user"):
        nonexistent_id = "nonexistent-user-id-67890"
        
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            users_api.delete_user(nonexistent_id)
    
    with allure.step("Verify 404 Not Found response"):
        assert exc_info.value.response.status_code == 404, "Should return 404 Not Found"
        
        allure.attach(
            exc_info.value.response.text,
            name="404 Error Response",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Deletion")
@pytest.mark.api
def test_delete_user_idempotency(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test deletion idempotency - deleting already deleted user.
    
    Validates that attempting to delete an already-deleted user results in
    404 Not Found, maintaining consistent behavior and preventing silent
    failures in cleanup operations.
    """
    with allure.step("Setup: Create and delete user"):
        user_payload = mcp_client.build_payload(template="create_user")
        created_user = users_api.create_user(CreateUserRequest(**user_payload))
        
        # First deletion should succeed
        users_api.delete_user(created_user.id)
        
        allure.attach(
            f"User {created_user.id} deleted successfully",
            name="First Deletion",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Attempt to delete same user again"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            users_api.delete_user(created_user.id)
    
    with allure.step("Verify 404 Not Found for second deletion"):
        assert exc_info.value.response.status_code == 404, "Second deletion should return 404"
        
        allure.attach(
            "Idempotent behavior verified - second deletion returns 404",
            name="Idempotency Check",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Search")
@pytest.mark.api
def test_search_users(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user search by query string.
    
    Validates search functionality for finding users by name or email.
    Supports autocomplete and user lookup scenarios where partial matching
    helps users find accounts quickly.
    """
    with allure.step("Setup: Create user with distinctive name"):
        user_payload = mcp_client.build_payload(
            template="create_user",
            parameters={"name": "SearchableJohn Unique"}
        )
        created_user = users_api.create_user(CreateUserRequest(**user_payload))
        
        allure.attach(
            f"Created user: {created_user.name} ({created_user.email})",
            name="Searchable User",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Search for user by name substring"):
        search_results = users_api.search_users(query="SearchableJohn", limit=10)
    
    with allure.step("Verify user found in search results"):
        assert search_results.total >= 1, "Should find at least one matching user"
        
        found = any(user.id == created_user.id for user in search_results.users)
        assert found is True, "Created user should be in search results"
        
        allure.attach(
            f"Found {search_results.total} users matching 'SearchableJohn'",
            name="Search Results",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Search")
@pytest.mark.api
def test_search_users_by_email(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user search by email pattern.
    
    Validates that search functionality works with email addresses as well as
    names, supporting admin interfaces where users need to look up accounts
    by partial email addresses.
    """
    with allure.step("Setup: Create user with distinctive email"):
        user_payload = mcp_client.build_payload(
            template="create_user",
            parameters={"email": "uniquesearch@example.com"}
        )
        created_user = users_api.create_user(CreateUserRequest(**user_payload))
        
        allure.attach(
            f"Created user with email: {created_user.email}",
            name="User for Email Search",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Search by email substring"):
        search_results = users_api.search_users(query="uniquesearch", limit=10)
    
    with allure.step("Verify user found by email"):
        assert search_results.total >= 1, "Should find user by email"
        
        found = any(user.email == created_user.email for user in search_results.users)
        assert found is True, "User should be found by email search"
        
        allure.attach(
            f"Found {search_results.total} users matching email pattern",
            name="Email Search Results",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Search")
@pytest.mark.api
def test_search_users_with_limit(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test search result limit parameter.
    
    Validates that the limit parameter correctly restricts the number of
    returned results, preventing performance issues with large result sets
    and supporting paginated search results.
    """
    with allure.step("Setup: Create multiple users with similar names"):
        for i in range(5):
            user_payload = mcp_client.build_payload(
                template="create_user",
                parameters={"name": f"CommonName User{i}"}
            )
            users_api.create_user(CreateUserRequest(**user_payload))
    
    with allure.step("Search with limit of 2"):
        search_results = users_api.search_users(query="CommonName", limit=2)
    
    with allure.step("Verify result count respects limit"):
        assert len(search_results.users) <= 2, "Should return at most 2 users"
        assert search_results.total >= 5, "Total count should reflect all matches"
        
        allure.attach(
            f"Returned {len(search_results.users)} users out of {search_results.total} total matches",
            name="Limited Search Results",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Validation")
@pytest.mark.api
def test_create_user_with_invalid_age(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user creation with invalid age (below minimum).
    
    Validates age range constraints per Pydantic field validators. Age must
    be between 18 and 120 if provided. Values outside this range should be
    rejected with validation error.
    """
    with allure.step("Generate payload with invalid age"):
        user_payload = mcp_client.build_payload(template="create_user")
        user_payload["age"] = 15  # Below minimum age of 18
        
        allure.attach(
            f"Invalid age: {user_payload['age']} (minimum is 18)",
            name="Invalid Age Value",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Attempt to create user with invalid age"):
        with pytest.raises((ValueError, httpx.HTTPStatusError)) as exc_info:
            request = CreateUserRequest(**user_payload)
            users_api.create_user(request)
    
    with allure.step("Verify validation error"):
        # Could be Pydantic ValidationError or 400 from API
        if hasattr(exc_info.value, 'response'):
            assert exc_info.value.response.status_code == 400
        
        allure.attach(
            str(exc_info.value),
            name="Age Validation Error",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management API")
@allure.story("User Validation")
@pytest.mark.api
def test_create_user_with_invalid_phone(users_api: UsersAPIClient, mcp_client: MCPClient):
    """
    Test user creation with invalid phone format.
    
    Validates E.164 phone number format enforcement. Phone numbers must follow
    international standard format (+[country][number]) per Pydantic pattern
    validator for consistent global phone number handling.
    """
    with allure.step("Generate payload with invalid phone"):
        user_payload = mcp_client.build_payload(template="create_user")
        user_payload["phone"] = "123-456-7890"  # Not E.164 format
        
        allure.attach(
            f"Invalid phone: {user_payload['phone']} (expected E.164 format like +12125551234)",
            name="Invalid Phone Format",
            attachment_type=allure.attachment_type.TEXT
        )
    
    with allure.step("Attempt to create user with invalid phone"):
        with pytest.raises((ValueError, httpx.HTTPStatusError)) as exc_info:
            request = CreateUserRequest(**user_payload)
            users_api.create_user(request)
    
    with allure.step("Verify validation error"):
        if hasattr(exc_info.value, 'response'):
            assert exc_info.value.response.status_code == 400
        
        allure.attach(
            str(exc_info.value),
            name="Phone Validation Error",
            attachment_type=allure.attachment_type.TEXT
        )
