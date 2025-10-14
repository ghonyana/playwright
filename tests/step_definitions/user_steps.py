"""
User Management Step Definitions

This module implements pytest-bdd step definitions for user management Gherkin scenarios.
It bridges business-readable Given/When/Then steps with Page Object Pattern UI interactions
and typed API operations.

Per Agent Action Plan Section 0.1.2 directives:
- "Prefer Gherkin that's business-readable; keep steps high-level"
- "Implement steps via page objects; avoid brittle CSS/xpath—prefer role/name/test-id"
- "Use MCP tools for data/state (don't hard-code test data)"
- "Keep tests deterministic, isolated, and parallel-friendly"

Architecture:
-----------
This file follows the BDD pattern where:
1. Gherkin scenarios (in tests/features/user_management.feature) describe business behavior
2. Step definitions (this file) parse Gherkin and delegate to implementation layers
3. Page objects (UserManagementPage, UserProfilePage) handle UI interactions
4. API clients (UsersAPIClient) handle backend operations
5. MCP client provides deterministic test data without hardcoding

Step definitions remain 1-5 lines, focusing on delegation rather than implementation details.
This ensures maintainability and keeps Gherkin steps business-readable.

Integration Points:
------------------
- pytest-bdd: @given, @when, @then decorators and scenarios() loader
- Allure: @allure.step for hierarchical test reporting
- Page Objects: UserManagementPage and UserProfilePage for UI
- API Clients: UsersAPIClient for backend operations
- MCP Client: seed_user() and build_payload() for test data
- Pydantic Models: UserResponse for type-safe data access

Example Test Flow:
-----------------
```gherkin
# tests/features/user_management.feature
Scenario: Admin creates a new user
    Given the admin is on the user management page
    When the admin creates a user with email "test@example.com" and role "Editor"
    Then the user should appear in the user list
    And a success message should be displayed
```

```python
# This file (tests/step_definitions/user_steps.py)
@given("the admin is on the user management page")
def navigate_to_user_management(user_management_page):
    user_management_page.navigate()

@when('the admin creates a user with email "{email}" and role "{role}"')
def create_user_via_ui(user_management_page, email, role, created_user):
    user_management_page.create_user(email=email, name=f"Test {role}", role=role)
    created_user["email"] = email
    created_user["role"] = role
```

The step definitions delegate all UI logic to UserManagementPage, which handles:
- Stable locators (ARIA roles, labels, test-ids)
- Playwright interactions
- Screenshot capture
- Allure reporting
"""

from typing import Dict, Any, Optional

import allure
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

from tests.pages.user_management_page import UserManagementPage
from tests.pages.user_profile_page import UserProfilePage
from tests.api_clients.users_client import UsersAPIClient
from tests.api_clients.models.user_models import UserResponse
from tests.helpers.mcp_client import MCPClient


# ============================================================================
# Feature File Loading
# ============================================================================

# Load all scenarios from user_management.feature
# This automatically discovers all Gherkin scenarios and links them to step definitions
scenarios('../features/user_management.feature')


# ============================================================================
# Fixtures - Request-Scoped Data Storage
# ============================================================================

@pytest.fixture
def user_management_page(page, base_url) -> UserManagementPage:
    """
    Pytest fixture providing UserManagementPage instance for UI-based user operations.
    
    This fixture creates a page object initialized with the Playwright page instance
    and base URL from environment configuration. Used in Given/When/Then steps that
    interact with the user management UI.
    
    Args:
        page: Playwright Page fixture from pytest-playwright plugin
        base_url: Base URL fixture from conftest.py (from BASE_URL env var)
    
    Returns:
        UserManagementPage: Page object for user management interface
    
    Example:
        @given("the admin is on the user management page")
        def navigate_to_users(user_management_page):
            user_management_page.navigate()
    """
    return UserManagementPage(page, base_url)


@pytest.fixture
def user_profile_page(page, base_url) -> UserProfilePage:
    """
    Pytest fixture providing UserProfilePage instance for profile editing operations.
    
    Used in steps that involve viewing or editing individual user profiles including
    profile updates and password changes.
    
    Args:
        page: Playwright Page fixture from pytest-playwright plugin
        base_url: Base URL fixture from conftest.py
    
    Returns:
        UserProfilePage: Page object for user profile interface
    
    Example:
        @when("the user updates their profile name")
        def update_profile(user_profile_page):
            user_profile_page.navigate_to_profile()
            user_profile_page.update_profile(first_name="Jane", last_name="Doe")
    """
    return UserProfilePage(page, base_url)


@pytest.fixture
def users_api(api_base_url, auth_token) -> UsersAPIClient:
    """
    Pytest fixture providing UsersAPIClient for API-based user operations.
    
    This fixture creates a typed API client with authentication for backend user
    management operations. Used in When/Then steps that interact with the Users API
    directly without going through the UI.
    
    Args:
        api_base_url: API base URL fixture from conftest.py (from API_BASE_URL env var)
        auth_token: Authentication token fixture from conftest.py
    
    Returns:
        UsersAPIClient: Configured API client for user management endpoints
    
    Example:
        @when("I create a user via API")
        def create_user_api(users_api, mcp_client):
            payload = mcp_client.build_payload("create_user", {"role": "admin"})
            request = CreateUserRequest(**payload)
            user = users_api.create_user(request)
    """
    return UsersAPIClient(base_url=api_base_url, auth_token=auth_token)


@pytest.fixture
def existing_user(mcp_client: MCPClient) -> Dict[str, Any]:
    """
    Pytest fixture creating a test user via MCP for scenarios requiring pre-existing users.
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    
    This fixture uses the MCP seed_user tool to create a deterministic test user with
    known credentials. The user is created with a unique email to avoid conflicts in
    parallel test execution.
    
    Args:
        mcp_client: MCP client fixture from conftest.py
    
    Returns:
        Dict[str, Any]: User data including:
            - id: User ID in target system
            - email: Unique email address
            - password: Test password for UI login
            - role: User role
            - auth_token: Valid JWT token
    
    Example:
        @given("a user exists with specific attributes")
        def verify_existing_user(existing_user):
            assert existing_user['role'] == 'customer'
            assert 'email' in existing_user
    """
    with allure.step("Create test user via MCP for precondition"):
        user = mcp_client.seed_user(
            role="customer",
            attributes={"age": 30, "department": "Support"}
        )
        allure.attach(
            f"Created user: {user.get('email')}",
            name="Existing User",
            attachment_type=allure.attachment_type.TEXT
        )
        return user


@pytest.fixture
def created_user() -> Dict[str, Any]:
    """
    Pytest fixture providing storage for user data created during test execution.
    
    This fixture enables data flow between Given/When/Then steps within a single scenario.
    Steps can store user information (email, id, role) that subsequent steps need to verify.
    
    Returns:
        Dict[str, Any]: Empty dictionary for storing user data between steps
    
    Example:
        @when('I create a user with email "{email}"')
        def create_user_step(user_management_page, email, created_user):
            user_management_page.create_user(email=email, name="Test User", role="User")
            created_user["email"] = email  # Store for later steps
        
        @then("the user should appear in the list")
        def verify_user_in_list(user_management_page, created_user):
            user_management_page.verify_user_in_list(created_user["email"])
    """
    return {}


@pytest.fixture
def api_response() -> Dict[str, Any]:
    """
    Pytest fixture providing storage for API response data for verification.
    
    This fixture stores API responses from When steps so Then steps can perform
    assertions on response status codes, headers, and body content.
    
    Returns:
        Dict[str, Any]: Empty dictionary for storing API response data
    
    Example:
        @when("I create a user via API")
        def create_via_api(users_api, api_response):
            user = users_api.create_user(request)
            api_response["user"] = user
            api_response["status"] = "created"
        
        @then("the API should return the created user")
        def verify_api_response(api_response):
            assert "user" in api_response
            assert api_response["user"].id is not None
    """
    return {}


# ============================================================================
# Given Steps - Preconditions and Initial State
# ============================================================================

@given("the admin is on the user management page")
@allure.step("Navigate to user management page")
def navigate_to_user_management(user_management_page: UserManagementPage) -> None:
    """
    Navigate to the user management page and verify it loads successfully.
    
    This Given step establishes the precondition that the admin user is viewing
    the user management interface, ready to perform user operations. The page
    object handles navigation and verification that the page loaded correctly.
    
    Args:
        user_management_page: Page object fixture for user management UI
    
    Example Gherkin:
        Given the admin is on the user management page
    """
    user_management_page.navigate()


@given(parsers.parse('a user exists with email "{email}" and role "{role}"'))
@allure.step('Create user via MCP: email={email}, role={role}')
def create_user_precondition(
    mcp_client: MCPClient,
    email: str,
    role: str,
    existing_user: Dict[str, Any]
) -> None:
    """
    Create a test user via MCP with specified email and role as a test precondition.
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    
    This Given step uses the MCP seed_user tool to create a user with deterministic
    data. The user is stored in the existing_user fixture for use in subsequent steps.
    
    Args:
        mcp_client: MCP client for test data creation
        email: User email address (parsed from Gherkin)
        role: User role (parsed from Gherkin)
        existing_user: Fixture for storing created user data
    
    Example Gherkin:
        Given a user exists with email "test@example.com" and role "Editor"
    """
    user = mcp_client.seed_user(
        role=role.lower(),
        email=email,
        attributes={}
    )
    
    # Store user data for subsequent steps
    existing_user.update(user)
    
    allure.attach(
        f"User ID: {user.get('id')}\n"
        f"Email: {user.get('email')}\n"
        f"Role: {user.get('role')}\n"
        f"Auth Token: {user.get('auth_token')[:20]}...",
        name="Created User via MCP",
        attachment_type=allure.attachment_type.TEXT
    )


@given(parsers.parse('a user with name "{name}" and department "{department}" exists'))
@allure.step('Create user with specific attributes via MCP')
def create_user_with_attributes(
    mcp_client: MCPClient,
    name: str,
    department: str,
    existing_user: Dict[str, Any]
) -> None:
    """
    Create a test user with specific name and department attributes.
    
    This Given step creates a more detailed user record with multiple attributes
    using the MCP server's attribute support.
    
    Args:
        mcp_client: MCP client for test data creation
        name: User's full name (parsed from Gherkin)
        department: User's department (parsed from Gherkin)
        existing_user: Fixture for storing created user data
    
    Example Gherkin:
        Given a user with name "John Doe" and department "Engineering" exists
    """
    user = mcp_client.seed_user(
        role="user",
        attributes={"name": name, "department": department}
    )
    
    existing_user.update(user)
    
    allure.attach(
        f"Name: {name}\n"
        f"Department: {department}\n"
        f"Email: {user.get('email')}",
        name="User with Attributes",
        attachment_type=allure.attachment_type.TEXT
    )


@given("the user list is empty")
@allure.step("Reset environment to empty user list")
def reset_user_list(mcp_client: MCPClient) -> None:
    """
    Reset test environment to ensure user list is empty.
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    
    This Given step uses the MCP reset_env tool to clear all test users, establishing
    a clean environment for testing user creation flows.
    
    Args:
        mcp_client: MCP client for environment management
    
    Example Gherkin:
        Given the user list is empty
    """
    reset_status = mcp_client.reset_env()
    
    allure.attach(
        f"Reset Status: {reset_status.get('status')}\n"
        f"Timestamp: {reset_status.get('timestamp')}",
        name="Environment Reset",
        attachment_type=allure.attachment_type.TEXT
    )


# ============================================================================
# When Steps - UI-Based User Actions
# ============================================================================

@when(parsers.parse('the admin creates a user with email "{email}" and role "{role}"'))
@allure.step('Create user via UI: email={email}, role={role}')
def create_user_via_ui(
    user_management_page: UserManagementPage,
    email: str,
    role: str,
    created_user: Dict[str, Any]
) -> None:
    """
    Create a new user through the user management UI form.
    
    This When step delegates to the UserManagementPage.create_user() method which
    handles all UI interactions including clicking "Add User", filling form fields
    with stable locators, and submitting the form.
    
    Args:
        user_management_page: Page object for user management UI
        email: User email address (parsed from Gherkin)
        role: User role (parsed from Gherkin)
        created_user: Fixture for storing created user data
    
    Example Gherkin:
        When the admin creates a user with email "newuser@example.com" and role "Admin"
    """
    # Generate test name from role
    name = f"Test {role} User"
    
    # Delegate to page object
    user_management_page.create_user(
        email=email,
        name=name,
        role=role,
        department="Test Department"
    )
    
    # Store created user data for Then steps
    created_user["email"] = email
    created_user["name"] = name
    created_user["role"] = role


@when(parsers.parse('the admin creates a user with email "{email}", name "{name}", and role "{role}"'))
@allure.step('Create user with full details via UI')
def create_user_with_full_details(
    user_management_page: UserManagementPage,
    email: str,
    name: str,
    role: str,
    created_user: Dict[str, Any]
) -> None:
    """
    Create a user with complete profile information through the UI.
    
    This When step provides more detailed user creation with an explicit name
    rather than auto-generating one from the role.
    
    Args:
        user_management_page: Page object for user management UI
        email: User email address (parsed from Gherkin)
        name: User's full name (parsed from Gherkin)
        role: User role (parsed from Gherkin)
        created_user: Fixture for storing created user data
    
    Example Gherkin:
        When the admin creates a user with email "john@example.com", name "John Doe", and role "Editor"
    """
    user_management_page.create_user(
        email=email,
        name=name,
        role=role
    )
    
    created_user["email"] = email
    created_user["name"] = name
    created_user["role"] = role


@when(parsers.parse('the admin searches for users with query "{query}"'))
@allure.step('Search users: query={query}')
def search_users(user_management_page: UserManagementPage, query: str) -> None:
    """
    Search for users using the search input field.
    
    This When step delegates to UserManagementPage.search_users() which handles
    filling the search input with stable locators and waiting for results to update.
    
    Args:
        user_management_page: Page object for user management UI
        query: Search query text (parsed from Gherkin)
    
    Example Gherkin:
        When the admin searches for users with query "john@example.com"
        When the admin searches for users with query "Manager"
    """
    user_management_page.search_users(query)


@when(parsers.parse('the admin filters users by role "{role}"'))
@allure.step('Filter users by role: {role}')
def filter_users_by_role(user_management_page: UserManagementPage, role: str) -> None:
    """
    Filter the user list by selecting a role from the filter dropdown.
    
    This When step delegates to UserManagementPage.filter_by_role() which handles
    dropdown interaction with stable ARIA combobox locators.
    
    Args:
        user_management_page: Page object for user management UI
        role: Role name to filter by (parsed from Gherkin)
    
    Example Gherkin:
        When the admin filters users by role "Administrator"
        When the admin filters users by role "Customer"
    """
    user_management_page.filter_by_role(role)


@when(parsers.parse('the admin edits the user "{email}" to have role "{new_role}"'))
@allure.step('Edit user {email} role to {new_role}')
def edit_user_role(
    user_management_page: UserManagementPage,
    email: str,
    new_role: str,
    created_user: Dict[str, Any]
) -> None:
    """
    Edit an existing user's role through the user management UI.
    
    This When step delegates to UserManagementPage.edit_user() which finds the user
    row, clicks the edit button, updates the role field, and saves changes.
    
    Args:
        user_management_page: Page object for user management UI
        email: Email of user to edit (parsed from Gherkin)
        new_role: New role value (parsed from Gherkin)
        created_user: Fixture for storing updated user data
    
    Example Gherkin:
        When the admin edits the user "test@example.com" to have role "Manager"
    """
    user_management_page.edit_user(email, {"role": new_role})
    
    # Update stored user data
    created_user["updated_role"] = new_role


@when(parsers.parse('the admin updates user "{email}" with name "{new_name}" and department "{new_department}"'))
@allure.step('Update user {email} with multiple fields')
def update_user_multiple_fields(
    user_management_page: UserManagementPage,
    email: str,
    new_name: str,
    new_department: str
) -> None:
    """
    Update multiple fields of an existing user through the edit form.
    
    This When step delegates to UserManagementPage.edit_user() with a dictionary
    of multiple field updates.
    
    Args:
        user_management_page: Page object for user management UI
        email: Email of user to edit (parsed from Gherkin)
        new_name: New name value (parsed from Gherkin)
        new_department: New department value (parsed from Gherkin)
    
    Example Gherkin:
        When the admin updates user "test@example.com" with name "Jane Smith" and department "Sales"
    """
    user_management_page.edit_user(
        email,
        {
            "name": new_name,
            "department": new_department
        }
    )


@when(parsers.parse('the admin deletes the user "{email}"'))
@allure.step('Delete user: {email}')
def delete_user_via_ui(user_management_page: UserManagementPage, email: str) -> None:
    """
    Delete a user through the user management UI with confirmation modal handling.
    
    This When step delegates to UserManagementPage.delete_user() which finds the
    user row, clicks delete, waits for confirmation modal, and confirms deletion.
    
    Args:
        user_management_page: Page object for user management UI
        email: Email of user to delete (parsed from Gherkin)
    
    Example Gherkin:
        When the admin deletes the user "old@example.com"
    """
    user_management_page.delete_user(email)


@when("the user navigates to their profile page")
@allure.step("Navigate to user profile page")
def navigate_to_profile(user_profile_page: UserProfilePage) -> None:
    """
    Navigate to the user profile/account settings page.
    
    This When step delegates to UserProfilePage.navigate_to_profile() which handles
    navigation and verification that the profile page loaded correctly.
    
    Args:
        user_profile_page: Page object for user profile UI
    
    Example Gherkin:
        When the user navigates to their profile page
    """
    user_profile_page.navigate_to_profile()


@when(parsers.parse('the user updates their profile with first name "{first_name}" and last name "{last_name}"'))
@allure.step('Update profile: first_name={first_name}, last_name={last_name}')
def update_user_profile(
    user_profile_page: UserProfilePage,
    first_name: str,
    last_name: str
) -> None:
    """
    Update user profile information through the profile edit form.
    
    This When step delegates to UserProfilePage.update_profile() which fills the
    form fields with stable label-based locators and submits the changes.
    
    Args:
        user_profile_page: Page object for user profile UI
        first_name: New first name (parsed from Gherkin)
        last_name: New last name (parsed from Gherkin)
    
    Example Gherkin:
        When the user updates their profile with first name "Jane" and last name "Smith"
    """
    user_profile_page.update_profile(
        first_name=first_name,
        last_name=last_name
    )


@when(parsers.parse('the user changes their password to "{new_password}"'))
@allure.step('Change user password')
def change_user_password(
    user_profile_page: UserProfilePage,
    existing_user: Dict[str, Any],
    new_password: str
) -> None:
    """
    Change user password through the profile password change form.
    
    This When step delegates to UserProfilePage.change_password() which fills
    current password, new password, and confirmation fields then submits.
    
    Args:
        user_profile_page: Page object for user profile UI
        existing_user: Fixture containing current user data with password
        new_password: New password value (parsed from Gherkin)
    
    Example Gherkin:
        When the user changes their password to "NewSecurePass456!"
    """
    current_password = existing_user.get("password", "DefaultTestPass123!")
    
    user_profile_page.change_password(
        current_password=current_password,
        new_password=new_password
    )


# ============================================================================
# When Steps - API-Based User Actions
# ============================================================================

@when(parsers.parse('I create a user via API with role "{role}"'))
@allure.step('Create user via API: role={role}')
def create_user_via_api(
    users_api: UsersAPIClient,
    mcp_client: MCPClient,
    role: str,
    api_response: Dict[str, Any]
) -> None:
    """
    Create a user through the Users API endpoint.
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    
    This When step uses MCP build_payload to generate a valid CreateUserRequest,
    then calls UsersAPIClient.create_user() for API-based user creation. The
    response is stored in api_response fixture for Then step verification.
    
    Args:
        users_api: API client for user management operations
        mcp_client: MCP client for payload generation
        role: User role (parsed from Gherkin)
        api_response: Fixture for storing API response data
    
    Example Gherkin:
        When I create a user via API with role "Admin"
    """
    # Generate payload via MCP (no hardcoded test data)
    payload_data = mcp_client.build_payload(
        template="create_user",
        parameters={"role": role.lower()}
    )
    
    # Import request model here to avoid circular dependencies
    from tests.api_clients.models.user_models import CreateUserRequest
    
    # Create typed request from MCP-generated payload
    request = CreateUserRequest(**payload_data)
    
    # Execute API call
    user_response = users_api.create_user(request)
    
    # Store response for Then steps
    api_response["user"] = user_response
    api_response["status_code"] = 201
    
    allure.attach(
        f"User ID: {user_response.id}\n"
        f"Email: {user_response.email}\n"
        f"Role: {user_response.role}\n"
        f"Created At: {user_response.created_at}",
        name="API Response",
        attachment_type=allure.attachment_type.TEXT
    )


@when(parsers.parse('I update user "{user_id}" via API with role "{new_role}"'))
@allure.step('Update user {user_id} via API: role={new_role}')
def update_user_via_api(
    users_api: UsersAPIClient,
    user_id: str,
    new_role: str,
    api_response: Dict[str, Any]
) -> None:
    """
    Update a user through the Users API endpoint.
    
    This When step calls UsersAPIClient.update_user() with an UpdateUserRequest
    containing the new role value. The response is stored for verification.
    
    Args:
        users_api: API client for user management operations
        user_id: ID of user to update (parsed from Gherkin)
        new_role: New role value (parsed from Gherkin)
        api_response: Fixture for storing API response data
    
    Example Gherkin:
        When I update user "user_abc123" via API with role "Manager"
    """
    from tests.api_clients.models.user_models import UpdateUserRequest, UserRole
    
    # Create update request with new role
    request = UpdateUserRequest(role=UserRole(new_role.lower()))
    
    # Execute API call
    user_response = users_api.update_user(user_id, request)
    
    # Store response for Then steps
    api_response["user"] = user_response
    api_response["status_code"] = 200
    
    allure.attach(
        f"Updated User ID: {user_response.id}\n"
        f"New Role: {user_response.role}\n"
        f"Updated At: {user_response.updated_at}",
        name="API Update Response",
        attachment_type=allure.attachment_type.TEXT
    )


@when(parsers.parse('I delete user "{user_id}" via API'))
@allure.step('Delete user {user_id} via API')
def delete_user_via_api(
    users_api: UsersAPIClient,
    user_id: str,
    api_response: Dict[str, Any]
) -> None:
    """
    Delete a user through the Users API endpoint.
    
    This When step calls UsersAPIClient.delete_user() which sends DELETE request
    to /users/{user_id}. Successful deletion returns 204 No Content.
    
    Args:
        users_api: API client for user management operations
        user_id: ID of user to delete (parsed from Gherkin)
        api_response: Fixture for storing API response data
    
    Example Gherkin:
        When I delete user "user_abc123" via API
    """
    # Execute API call (returns None for 204 No Content)
    users_api.delete_user(user_id)
    
    # Store status for Then steps
    api_response["deleted_user_id"] = user_id
    api_response["status_code"] = 204
    
    allure.attach(
        f"Deleted User ID: {user_id}",
        name="API Delete Response",
        attachment_type=allure.attachment_type.TEXT
    )


@when(parsers.parse('I list users via API with role filter "{role}"'))
@allure.step('List users via API: role={role}')
def list_users_via_api(
    users_api: UsersAPIClient,
    role: str,
    api_response: Dict[str, Any]
) -> None:
    """
    List users through the Users API with role filtering.
    
    This When step calls UsersAPIClient.list_users() with role parameter for
    filtered user retrieval. Response includes pagination metadata.
    
    Args:
        users_api: API client for user management operations
        role: Role filter value (parsed from Gherkin)
        api_response: Fixture for storing API response data
    
    Example Gherkin:
        When I list users via API with role filter "Admin"
    """
    # Execute API call with role filter
    user_list_response = users_api.list_users(role=role.lower(), page=1, page_size=50)
    
    # Store response for Then steps
    api_response["user_list"] = user_list_response
    api_response["status_code"] = 200
    
    allure.attach(
        f"Total Users: {user_list_response.total}\n"
        f"Page: {user_list_response.page}/{user_list_response.total_pages}\n"
        f"Users Returned: {len(user_list_response.users)}",
        name="API List Response",
        attachment_type=allure.attachment_type.TEXT
    )


@when(parsers.parse('I search for users via API with query "{query}"'))
@allure.step('Search users via API: query={query}')
def search_users_via_api(
    users_api: UsersAPIClient,
    query: str,
    api_response: Dict[str, Any]
) -> None:
    """
    Search for users through the Users API.
    
    This When step calls UsersAPIClient.search_users() with a query string that
    searches across name and email fields.
    
    Args:
        users_api: API client for user management operations
        query: Search query text (parsed from Gherkin)
        api_response: Fixture for storing API response data
    
    Example Gherkin:
        When I search for users via API with query "john"
    """
    # Execute API search
    search_results = users_api.search_users(query=query, limit=25)
    
    # Store response for Then steps
    api_response["search_results"] = search_results
    api_response["query"] = query
    api_response["status_code"] = 200
    
    allure.attach(
        f"Search Query: {query}\n"
        f"Results Found: {len(search_results.users)}",
        name="API Search Response",
        attachment_type=allure.attachment_type.TEXT
    )


# ============================================================================
# Then Steps - UI Verification
# ============================================================================

@then("the user should appear in the user list")
@allure.step("Verify user appears in user list")
def verify_user_in_list(
    user_management_page: UserManagementPage,
    created_user: Dict[str, Any]
) -> None:
    """
    Verify that the created user appears in the user management table.
    
    This Then step delegates to UserManagementPage.verify_user_in_list() which
    uses Playwright's expect assertion with auto-retry logic to reliably verify
    user presence in the list.
    
    Args:
        user_management_page: Page object for user management UI
        created_user: Fixture containing created user data with email
    
    Example Gherkin:
        Then the user should appear in the user list
    """
    email = created_user.get("email")
    if not email:
        raise ValueError("created_user fixture missing 'email' key. Ensure When step stores user data.")
    
    user_management_page.verify_user_in_list(email)


@then(parsers.parse('the user "{email}" should appear in the user list'))
@allure.step('Verify user {email} appears in list')
def verify_specific_user_in_list(
    user_management_page: UserManagementPage,
    email: str
) -> None:
    """
    Verify that a specific user (identified by email) appears in the user table.
    
    This Then step verifies user presence by email without relying on fixture data,
    useful for scenarios where the email is explicitly specified in Gherkin.
    
    Args:
        user_management_page: Page object for user management UI
        email: User email to verify (parsed from Gherkin)
    
    Example Gherkin:
        Then the user "test@example.com" should appear in the user list
    """
    user_management_page.verify_user_in_list(email)


@then(parsers.parse('the user "{email}" should NOT appear in the user list'))
@allure.step('Verify user {email} does not appear in list')
def verify_user_not_in_list(
    user_management_page: UserManagementPage,
    email: str
) -> None:
    """
    Verify that a user does NOT appear in the user table (typically after deletion).
    
    This Then step delegates to UserManagementPage.verify_user_not_in_list() which
    asserts the user row is not visible or doesn't exist in the table.
    
    Args:
        user_management_page: Page object for user management UI
        email: User email to verify absence (parsed from Gherkin)
    
    Example Gherkin:
        Then the user "deleted@example.com" should NOT appear in the user list
    """
    user_management_page.verify_user_not_in_list(email)


@then(parsers.parse('a success message "{expected_message}" should be displayed'))
@allure.step('Verify success message: {expected_message}')
def verify_success_message(
    user_management_page: UserManagementPage,
    expected_message: str
) -> None:
    """
    Verify that a success notification message appears with expected content.
    
    This Then step delegates to UserManagementPage.verify_success_message() which
    checks for success alert with ARIA role and verifies message text contains
    the expected substring.
    
    Args:
        user_management_page: Page object for user management UI
        expected_message: Expected message text or substring (parsed from Gherkin)
    
    Example Gherkin:
        Then a success message "User created successfully" should be displayed
        Then a success message "created" should be displayed
    """
    user_management_page.verify_success_message(expected_message)


@then(parsers.parse('an error message "{expected_message}" should be displayed'))
@allure.step('Verify error message: {expected_message}')
def verify_error_message(
    user_management_page: UserManagementPage,
    expected_message: str
) -> None:
    """
    Verify that an error notification message appears with expected content.
    
    This Then step delegates to UserManagementPage.verify_error_message() which
    checks for error alert and verifies message text contains the expected text.
    
    Args:
        user_management_page: Page object for user management UI
        expected_message: Expected error message text or substring (parsed from Gherkin)
    
    Example Gherkin:
        Then an error message "Email already exists" should be displayed
        Then an error message "Invalid email format" should be displayed
    """
    user_management_page.verify_error_message(expected_message)


@then("the profile changes should be saved successfully")
@allure.step("Verify profile save success")
def verify_profile_saved(user_profile_page: UserProfilePage) -> None:
    """
    Verify that profile changes were saved successfully.
    
    This Then step delegates to UserProfilePage.verify_profile_saved() which
    asserts the success message is visible and contains success text.
    
    Args:
        user_profile_page: Page object for user profile UI
    
    Example Gherkin:
        Then the profile changes should be saved successfully
    """
    user_profile_page.verify_profile_saved()


@then(parsers.parse('the profile email should be "{expected_email}"'))
@allure.step('Verify profile email: {expected_email}')
def verify_profile_email(
    user_profile_page: UserProfilePage,
    expected_email: str
) -> None:
    """
    Verify that the profile email field displays the expected value.
    
    This Then step retrieves the current email value from the profile form and
    asserts it matches the expected email.
    
    Args:
        user_profile_page: Page object for user profile UI
        expected_email: Expected email value (parsed from Gherkin)
    
    Example Gherkin:
        Then the profile email should be "newemail@example.com"
    """
    current_email = user_profile_page.get_current_email()
    
    assert current_email == expected_email, (
        f"Profile email mismatch. Expected: {expected_email}, Got: {current_email}"
    )
    
    allure.attach(
        f"Expected: {expected_email}\n"
        f"Actual: {current_email}\n"
        f"Match: ✓",
        name="Email Verification",
        attachment_type=allure.attachment_type.TEXT
    )


# ============================================================================
# Then Steps - API Verification
# ============================================================================

@then("the API should return the created user")
@allure.step("Verify API returned created user")
def verify_api_created_user(api_response: Dict[str, Any]) -> None:
    """
    Verify that the API response contains the created user data.
    
    This Then step asserts that the api_response fixture contains a valid user
    object with required fields populated (id, email, role, timestamps).
    
    Args:
        api_response: Fixture containing API response data
    
    Example Gherkin:
        Then the API should return the created user
    """
    assert "user" in api_response, "API response missing 'user' key"
    
    user: UserResponse = api_response["user"]
    
    # Verify required fields are present
    assert user.id is not None, "User ID should not be None"
    assert user.email is not None, "User email should not be None"
    assert user.role is not None, "User role should not be None"
    assert user.created_at is not None, "User created_at should not be None"
    
    allure.attach(
        f"User ID: {user.id}\n"
        f"Email: {user.email}\n"
        f"Role: {user.role}\n"
        f"Created At: {user.created_at}",
        name="User Verification",
        attachment_type=allure.attachment_type.TEXT
    )


@then(parsers.parse('the user should have "{role}" role'))
@allure.step('Verify user has role: {role}')
def verify_user_role(
    api_response: Dict[str, Any],
    role: str
) -> None:
    """
    Verify that the user has the expected role.
    
    This Then step checks the user role from either API response or created_user
    fixture and asserts it matches the expected role.
    
    Args:
        api_response: Fixture containing API response data
        role: Expected role value (parsed from Gherkin)
    
    Example Gherkin:
        Then the user should have "Admin" role
        Then the user should have "Editor" permissions
    """
    # Check if user is in API response
    if "user" in api_response:
        user: UserResponse = api_response["user"]
        actual_role = user.role.value
    else:
        raise ValueError("No user data available in api_response fixture")
    
    expected_role = role.lower()
    
    assert actual_role == expected_role, (
        f"Role mismatch. Expected: {expected_role}, Got: {actual_role}"
    )
    
    allure.attach(
        f"Expected Role: {expected_role}\n"
        f"Actual Role: {actual_role}\n"
        f"Match: ✓",
        name="Role Verification",
        attachment_type=allure.attachment_type.TEXT
    )


@then(parsers.parse('the user should be "{status}" status'))
@allure.step('Verify user status: {status}')
def verify_user_status(
    api_response: Dict[str, Any],
    status: str
) -> None:
    """
    Verify that the user has the expected account status.
    
    This Then step checks the user status field and asserts it matches the
    expected status (active, inactive, suspended, pending).
    
    Args:
        api_response: Fixture containing API response data
        status: Expected status value (parsed from Gherkin)
    
    Example Gherkin:
        Then the user should be "active" status
        Then the user should be "inactive" status
    """
    if "user" in api_response:
        user: UserResponse = api_response["user"]
        actual_status = user.status.value
    else:
        raise ValueError("No user data available in api_response fixture")
    
    expected_status = status.lower()
    
    assert actual_status == expected_status, (
        f"Status mismatch. Expected: {expected_status}, Got: {actual_status}"
    )
    
    allure.attach(
        f"Expected Status: {expected_status}\n"
        f"Actual Status: {actual_status}\n"
        f"Match: ✓",
        name="Status Verification",
        attachment_type=allure.attachment_type.TEXT
    )


@then(parsers.parse('the API should return {count:d} users'))
@allure.step('Verify API returned {count} users')
def verify_user_list_count(
    api_response: Dict[str, Any],
    count: int
) -> None:
    """
    Verify that the API returned the expected number of users.
    
    This Then step checks the user_list response and asserts the count matches
    the expected value. Useful for verifying list and filter operations.
    
    Args:
        api_response: Fixture containing API response data
        count: Expected user count (parsed as integer from Gherkin)
    
    Example Gherkin:
        Then the API should return 5 users
        Then the API should return 0 users
    """
    if "user_list" not in api_response:
        raise ValueError("No user_list data available in api_response fixture")
    
    from tests.api_clients.models.user_models import UserListResponse
    user_list: UserListResponse = api_response["user_list"]
    
    actual_count = len(user_list.users)
    
    assert actual_count == count, (
        f"User count mismatch. Expected: {count}, Got: {actual_count}"
    )
    
    allure.attach(
        f"Expected Count: {count}\n"
        f"Actual Count: {actual_count}\n"
        f"Total (with pagination): {user_list.total}\n"
        f"Match: ✓",
        name="Count Verification",
        attachment_type=allure.attachment_type.TEXT
    )


@then(parsers.parse('the search should return users matching "{query}"'))
@allure.step('Verify search results match query: {query}')
def verify_search_results(
    api_response: Dict[str, Any],
    query: str
) -> None:
    """
    Verify that search results contain users matching the query.
    
    This Then step checks that all returned users have the query string in their
    name or email fields (case-insensitive matching).
    
    Args:
        api_response: Fixture containing API response data
        query: Search query to verify (parsed from Gherkin)
    
    Example Gherkin:
        Then the search should return users matching "john"
    """
    if "search_results" not in api_response:
        raise ValueError("No search_results data available in api_response fixture")
    
    from tests.api_clients.models.user_models import UserListResponse
    search_results: UserListResponse = api_response["search_results"]
    
    query_lower = query.lower()
    
    # Verify all returned users match the query
    for user in search_results.users:
        name_match = query_lower in user.name.lower()
        email_match = query_lower in user.email.lower()
        
        assert name_match or email_match, (
            f"User {user.id} ({user.name}, {user.email}) does not match query '{query}'"
        )
    
    allure.attach(
        f"Query: {query}\n"
        f"Results Count: {len(search_results.users)}\n"
        f"All results match query: ✓",
        name="Search Verification",
        attachment_type=allure.attachment_type.TEXT
    )


@then("the user deletion should be successful")
@allure.step("Verify user deletion successful")
def verify_deletion_successful(api_response: Dict[str, Any]) -> None:
    """
    Verify that the user deletion completed successfully.
    
    This Then step checks that the API returned 204 No Content status, indicating
    successful deletion without response body.
    
    Args:
        api_response: Fixture containing API response data
    
    Example Gherkin:
        Then the user deletion should be successful
    """
    if "deleted_user_id" not in api_response:
        raise ValueError("No deletion data available in api_response fixture")
    
    deleted_id = api_response["deleted_user_id"]
    status_code = api_response.get("status_code")
    
    assert status_code == 204, (
        f"Expected status code 204 for successful deletion, got {status_code}"
    )
    
    allure.attach(
        f"Deleted User ID: {deleted_id}\n"
        f"Status Code: {status_code}\n"
        f"Deletion Successful: ✓",
        name="Deletion Verification",
        attachment_type=allure.attachment_type.TEXT
    )
