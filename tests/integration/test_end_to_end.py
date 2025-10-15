"""
End-to-End Integration Test Module

This module provides comprehensive integration tests that combine UI interactions (Playwright),
API calls (httpx), and MCP server test data management to validate complete user workflows
across multiple system layers.

Per Agent Action Plan Section 0.5.1 Group 6.8, these tests demonstrate:
- Integration between page objects, API clients, and MCP server
- Complete user lifecycle workflows (registration, login, profile management)
- Cross-layer data consistency validation (UI changes persist in API)
- Deterministic test execution with MCP-generated test data
- Isolated, parallel-friendly test design (new context per test)

Key Integration Patterns:
------------------------
1. MCP Server: Deterministic test data generation (seed_user, build_payload)
2. Page Objects: UI automation with stable ARIA-based locators
3. API Clients: Backend validation with type-safe httpx clients
4. Playwright: Browser automation with per-test isolated contexts
5. Allure: Comprehensive test reporting with step-by-step execution

Test Coverage:
--------------
- Complete user registration and login flow
- Profile management with UI/API verification
- Cross-layer data consistency validation
- API-first user creation with UI verification
- Error handling integration (API errors in UI)
- Session management and logout workflows

User Directives Compliance:
---------------------------
Per Agent Action Plan Section 0.1.2:
- "Use MCP tools for data/state (don't hard-code test data)" ✓
- "Keep tests deterministic, isolated, and parallel-friendly" ✓
- "Implement steps via page objects" ✓
- "Prefer role/name/test-id" stable locators ✓

Example Usage:
--------------
```bash
# Run all integration tests
pytest tests/integration/test_end_to_end.py -v

# Run with Allure reporting
pytest tests/integration/test_end_to_end.py --alluredir=allure-results

# Run specific test
pytest tests/integration/test_end_to_end.py::test_complete_user_registration_login_profile_flow
```
"""

import re
from typing import TYPE_CHECKING

import pytest
import allure
from playwright.sync_api import Page, expect

# Page Object imports - UI automation layer
from tests.pages.login_page import LoginPage
from tests.pages.dashboard_page import DashboardPage
from tests.pages.user_profile_page import UserProfilePage

# API Client imports - Backend validation layer
from tests.api_clients.auth_client import AuthAPIClient
from tests.api_clients.users_client import UsersAPIClient
from tests.api_clients.models.user_models import CreateUserRequest

# Helper imports - Test data management
from tests.helpers.mcp_client import MCPClient


# ======================================================================================
# END-TO-END INTEGRATION TESTS
# ======================================================================================
# These tests validate complete user workflows across UI, API, and MCP layers


@allure.feature("User Management")
@allure.story("Complete User Lifecycle")
@allure.severity(allure.severity_level.CRITICAL)
def test_complete_user_registration_login_profile_flow(
    page: Page,
    mcp_client: MCPClient,
    auth_api: AuthAPIClient,
    users_api: UsersAPIClient
) -> None:
    """
    End-to-end test validating complete user journey from creation to profile update.
    
    This integration test demonstrates the full integration between all framework layers:
    1. MCP creates test user with deterministic data (no hardcoded credentials)
    2. User logs in via UI using Playwright page objects
    3. User updates profile via UI form submission
    4. API validates profile changes persisted correctly
    5. User logs out via UI
    
    Integration Patterns Demonstrated:
    - MCP server (deterministic test data)
    - Page objects (UI automation)
    - API clients (backend validation)
    - Cross-layer data consistency verification
    
    Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
    Per user directive: "Keep tests deterministic, isolated, and parallel-friendly"
    """
    
    # Step 1: Create test user via MCP (deterministic data)
    with allure.step("Create test user via MCP server"):
        user_data = mcp_client.seed_user(
            role="viewer",
            attributes={"first_name": "Integration", "last_name": "Test"}
        )
        test_email = user_data["email"]
        test_password = user_data["password"]
        user_id = user_data["user_id"]
        
        allure.attach(
            f"Created user: {test_email}\nUser ID: {user_id}\nRole: customer",
            name="Test User Data",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 2: Login via UI (Playwright page objects)
    with allure.step("User logs in via UI"):
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(email=test_email, password=test_password)
        
        # Verify successful login
        dashboard_page = DashboardPage(page)
        dashboard_page.verify_dashboard_loaded()
        welcome_text = dashboard_page.get_welcome_message()
        assert "Integration" in welcome_text, f"Welcome message doesn't contain user name: {welcome_text}"
        
        allure.attach(
            f"Welcome message: {welcome_text}",
            name="Dashboard Welcome",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 3: Update profile via UI
    with allure.step("User updates profile information via UI"):
        profile_page = UserProfilePage(page)
        profile_page.navigate_to_profile()
        
        new_first_name = "Updated Integration"
        new_last_name = "Test Updated"
        profile_page.update_profile(
            first_name=new_first_name,
            last_name=new_last_name,
            email=test_email
        )
        profile_page.verify_profile_saved()
        
        allure.attach(
            f"Updated name to: {new_first_name} {new_last_name}",
            name="Profile Update",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 4: Verify profile changes via API (cross-layer validation)
    with allure.step("Verify profile changes persisted via API"):
        # Login via API to get auth token
        login_response = auth_api.login(email=test_email, password=test_password, remember_me=False)
        users_api.set_auth_token(login_response.access_token)
        
        # Fetch user via API
        api_user = users_api.get_user(user_id)
        
        # Validate API data matches UI changes
        assert api_user.name == f"{new_first_name} {new_last_name}", \
            f"API name '{api_user.name}' doesn't match UI update '{new_first_name} {new_last_name}'"
        assert api_user.email == test_email, \
            f"API email '{api_user.email}' doesn't match expected '{test_email}'"
        
        allure.attach(
            f"API User Data:\n"
            f"  ID: {api_user.id}\n"
            f"  Name: {api_user.name}\n"
            f"  Email: {api_user.email}\n"
            f"  Role: {api_user.role}",
            name="API Verification",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 5: Logout via UI
    with allure.step("User logs out via UI"):
        dashboard_page.logout()
        
        # Verify redirect to login page
        expect(page).to_have_url(re.compile(r".*/login.*"))
        
        allure.attach(
            f"Redirected to: {page.url}",
            name="Logout Redirect",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("User Management")
@allure.story("API-to-UI Integration")
@allure.severity(allure.severity_level.NORMAL)
def test_api_created_user_can_login_via_ui(
    page: Page,
    mcp_client: MCPClient,
    auth_api: AuthAPIClient,
    users_api: UsersAPIClient
) -> None:
    """
    Test API-to-UI integration: Admin creates user via API, new user logs in via UI.
    
    This test validates that users created through the API can immediately authenticate
    via the UI, ensuring synchronization between backend API and frontend authentication.
    
    Flow:
    1. Admin authenticates and gets API token
    2. Admin creates new user via API with MCP-generated payload
    3. New user logs in via UI using credentials from API response
    4. UI displays correct user information from API-created user
    
    Integration Patterns:
    - MCP server for admin credentials and payload generation
    - API client for user creation
    - Page objects for UI login verification
    - Cross-layer validation (API → UI)
    """
    
    # Step 1: Admin authentication
    with allure.step("Authenticate as admin"):
        admin_user = mcp_client.seed_user(role="admin")
        # Login via API to get auth token
        admin_login = auth_api.login(email=admin_user["email"], password=admin_user["password"], remember_me=False)
        users_api.set_auth_token(admin_login.access_token)
        
        allure.attach(
            f"Admin user: {admin_user['email']}",
            name="Admin Credentials",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 2: Create new user via API with MCP payload
    with allure.step("Admin creates new user via API"):
        payload = mcp_client.build_payload(
            template="create_user",
            parameters={"role": "editor", "name": "API Created User"}
        )
        
        create_request = CreateUserRequest(**payload)
        new_user = users_api.create_user(create_request)
        
        # Store credentials for UI login
        user_email = new_user.email
        # Password from payload (MCP generates it)
        user_password = payload["password"]
        
        allure.attach(
            f"Created user via API:\n"
            f"  ID: {new_user.id}\n"
            f"  Email: {user_email}\n"
            f"  Name: {new_user.name}\n"
            f"  Role: {new_user.role}",
            name="API User Creation",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 3: New user logs in via UI
    with allure.step("New user logs in via UI"):
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(email=user_email, password=user_password)
        
        dashboard_page = DashboardPage(page)
        dashboard_page.verify_dashboard_loaded()
        
        # Verify UI shows correct user info from API
        welcome = dashboard_page.get_welcome_message()
        assert "API Created" in welcome, \
            f"Welcome message doesn't contain expected name. Got: {welcome}"
        
        allure.attach(
            f"UI Welcome Message: {welcome}",
            name="UI Verification",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Data Consistency")
@allure.story("UI-API Synchronization")
@allure.severity(allure.severity_level.CRITICAL)
def test_ui_changes_immediately_visible_via_api(
    page: Page,
    mcp_client: MCPClient,
    auth_api: AuthAPIClient,
    users_api: UsersAPIClient
) -> None:
    """
    Validate data consistency between UI and API layers.
    
    This test ensures that changes made through the UI are immediately visible
    via API calls, validating that there are no caching issues or synchronization
    delays between the frontend and backend.
    
    Flow:
    1. Create and login user
    2. Fetch baseline profile via API
    3. Update profile via UI
    4. Verify API immediately reflects UI changes
    5. Validate timestamps indicate update occurred
    
    Critical Assertions:
    - UI changes are immediately visible in API (no cache staleness)
    - Timestamps reflect the update (updated_at > created_at)
    - No data loss or corruption during UI → API sync
    
    Per user directive: "Keep tests deterministic, isolated, and parallel-friendly"
    """
    
    # Setup: Create and login user
    with allure.step("Setup: Create test user and login via UI"):
        user_data = mcp_client.seed_user(role="viewer")
        # Login via API to get auth token for API calls
        login_response = auth_api.login(email=user_data["email"], password=user_data["password"], remember_me=False)
        users_api.set_auth_token(login_response.access_token)
        
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(user_data["email"], user_data["password"])
        
        allure.attach(
            f"Test user: {user_data['email']}",
            name="Test User",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Baseline: Verify current profile via API
    with allure.step("Fetch baseline profile via API"):
        baseline_profile = users_api.get_user(user_data["user_id"])
        original_name = baseline_profile.name
        baseline_updated_at = baseline_profile.updated_at
        
        allure.attach(
            f"Baseline Profile:\n"
            f"  Name: {original_name}\n"
            f"  Email: {baseline_profile.email}\n"
            f"  Updated At: {baseline_updated_at}",
            name="Baseline Profile",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Action: Update profile via UI
    with allure.step("Update profile via UI"):
        profile_page = UserProfilePage(page)
        profile_page.navigate_to_profile()
        
        updated_name_parts = original_name.split() if original_name else ["Test"]
        updated_first_name = f"{updated_name_parts[0]} Modified"
        updated_last_name = updated_name_parts[1] if len(updated_name_parts) > 1 else "User"
        
        profile_page.update_profile(
            first_name=updated_first_name,
            last_name=updated_last_name,
            email=baseline_profile.email
        )
        profile_page.verify_profile_saved()
        
        allure.attach(
            f"Updated name to: {updated_first_name} {updated_last_name}",
            name="UI Update",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Verification: API immediately reflects UI changes
    with allure.step("Verify API reflects UI changes immediately"):
        updated_profile = users_api.get_user(user_data["user_id"])
        
        # Assert name was updated
        expected_full_name = f"{updated_first_name} {updated_last_name}"
        assert updated_profile.name == expected_full_name, \
            f"UI change not reflected in API - possible caching issue. " \
            f"Expected: {expected_full_name}, Got: {updated_profile.name}"
        
        # Assert timestamp was updated (validates update occurred)
        assert updated_profile.updated_at > baseline_updated_at, \
            f"Timestamp not updated after profile change. " \
            f"Baseline: {baseline_updated_at}, Current: {updated_profile.updated_at}"
        
        allure.attach(
            f"Updated Profile (API):\n"
            f"  Name: {updated_profile.name}\n"
            f"  Email: {updated_profile.email}\n"
            f"  Updated At: {updated_profile.updated_at}\n"
            f"  Baseline Updated At: {baseline_updated_at}\n"
            f"  Time Difference: {updated_profile.updated_at - baseline_updated_at}",
            name="API Verification Success",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Error Handling")
@allure.story("UI-API Error Synchronization")
@allure.severity(allure.severity_level.NORMAL)
def test_api_validation_errors_displayed_in_ui(
    page: Page,
    mcp_client: MCPClient
) -> None:
    """
    Validate error handling across layers: API validation errors are properly displayed in UI.
    
    This test ensures that backend API validation errors are correctly propagated to
    the frontend UI and displayed in a user-friendly manner. This validates the
    complete error handling integration between API and UI layers.
    
    Flow:
    1. Create and login test user
    2. Create second user with existing email
    3. Attempt to change first user's email to second user's email (duplicate)
    4. Verify UI displays appropriate validation error message
    
    Integration Patterns:
    - MCP server for creating multiple test users without conflicts
    - Page objects for UI interaction and error verification
    - Validation of error propagation from backend to frontend
    
    Per user directive: "Implement steps via page objects; avoid brittle CSS/xpath"
    """
    
    # Setup: Create first user and login
    with allure.step("Setup: Create primary test user and login"):
        user_data = mcp_client.seed_user(role="viewer")
        
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(user_data["email"], user_data["password"])
        
        allure.attach(
            f"Primary user: {user_data['email']}",
            name="Primary User",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Setup: Create second user to cause email conflict
    with allure.step("Create second user with different email"):
        existing_user = mcp_client.seed_user(role="viewer")
        existing_email = existing_user["email"]
        
        allure.attach(
            f"Second user (for conflict): {existing_email}",
            name="Conflict User",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Action: Attempt invalid profile update (duplicate email)
    with allure.step("Attempt profile update with duplicate email"):
        profile_page = UserProfilePage(page)
        profile_page.navigate_to_profile()
        
        # Try to change email to existing user's email (should fail)
        profile_page.update_profile(
            first_name="Test",
            last_name="User",
            email=existing_email  # This will cause duplicate email validation error
        )
        
        allure.attach(
            f"Attempted to change email to: {existing_email}",
            name="Invalid Update Attempt",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Verification: Error message displayed in UI
    with allure.step("Verify validation error displayed in UI"):
        # Verify error message is displayed for the email field
        error_message = profile_page.verify_validation_error(
            field="email",
            expected_error="Email already in use"
        )
        
        # Additional assertion to ensure error is meaningful
        assert len(error_message) > 0, "Error message should not be empty"
        assert "email" in error_message.lower() or "already" in error_message.lower(), \
            f"Error message should mention email or already exists. Got: {error_message}"
        
        allure.attach(
            f"Error message displayed: {error_message}",
            name="Validation Error Success",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Session Management")
@allure.story("Multi-Session Workflow")
@allure.severity(allure.severity_level.NORMAL)
def test_multiple_users_parallel_sessions(
    page: Page,
    mcp_client: MCPClient,
    users_api: UsersAPIClient
) -> None:
    """
    Test parallel user sessions to validate isolation and concurrent access.
    
    This test validates that the test framework can handle multiple user sessions
    concurrently without interference, demonstrating the parallel-friendly design.
    
    Flow:
    1. Create User A and User B via MCP (isolated, non-conflicting)
    2. User A logs in and updates profile
    3. Verify User A's changes don't affect User B
    4. Verify User B can still access their original profile
    
    Per user directive: "Keep tests deterministic, isolated, and parallel-friendly"
    This test demonstrates the isolation guarantees provided by MCP-generated data.
    """
    
    # Step 1: Create two isolated users
    with allure.step("Create two isolated test users"):
        user_a = mcp_client.seed_user(
            role="viewer",
            attributes={"first_name": "User", "last_name": "Alpha"}
        )
        user_b = mcp_client.seed_user(
            role="viewer",
            attributes={"first_name": "User", "last_name": "Beta"}
        )
        
        allure.attach(
            f"User A: {user_a['email']}\n"
            f"User B: {user_b['email']}",
            name="Test Users",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 2: User A logs in and updates profile
    with allure.step("User A logs in and updates profile"):
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(user_a["email"], user_a["password"])
        
        dashboard_page = DashboardPage(page)
        dashboard_page.verify_dashboard_loaded()
        
        profile_page = UserProfilePage(page)
        profile_page.navigate_to_profile()
        profile_page.update_profile(
            first_name="Modified Alpha",
            last_name="User",
            email=user_a["email"]
        )
        profile_page.verify_profile_saved()
        
        allure.attach(
            "User A updated name to: Modified Alpha User",
            name="User A Update",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 3: Verify User B unaffected via API
    with allure.step("Verify User B profile unchanged via API"):
        users_api.set_auth_token(user_b["auth_token"])
        user_b_profile = users_api.get_user(user_b["id"])
        
        # User B's profile should be unchanged
        assert "Beta" in user_b_profile.name, \
            f"User B's profile was affected by User A's changes: {user_b_profile.name}"
        assert user_b_profile.email == user_b["email"], \
            f"User B's email was affected: {user_b_profile.email}"
        
        allure.attach(
            f"User B Profile (Verified Unchanged):\n"
            f"  Name: {user_b_profile.name}\n"
            f"  Email: {user_b_profile.email}",
            name="User B Isolation Verified",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 4: Logout User A and verify User B can still login
    with allure.step("Logout User A and verify User B can login"):
        # Logout User A
        dashboard_page.logout()
        expect(page).to_have_url(re.compile(r".*/login.*"))
        
        # User B logs in successfully
        login_page.navigate_to_login()
        login_page.login(user_b["email"], user_b["password"])
        
        dashboard_page.verify_dashboard_loaded()
        welcome_b = dashboard_page.get_welcome_message()
        
        # Verify User B sees their own name
        assert "Beta" in welcome_b, \
            f"User B should see their own name in welcome message. Got: {welcome_b}"
        
        allure.attach(
            f"User B logged in successfully. Welcome: {welcome_b}",
            name="User B Login Success",
            attachment_type=allure.attachment_type.TEXT
        )


@allure.feature("Authentication")
@allure.story("Token-Based Authentication Workflow")
@allure.severity(allure.severity_level.CRITICAL)
def test_authentication_token_workflow(
    page: Page,
    mcp_client: MCPClient,
    auth_api: AuthAPIClient,
    users_api: UsersAPIClient
) -> None:
    """
    Comprehensive authentication workflow test integrating UI login, API token management.
    
    This test validates the complete authentication flow including:
    1. User creation via MCP
    2. UI login to obtain session
    3. API authentication with JWT tokens
    4. Token refresh mechanics
    5. Logout and session invalidation
    
    Integration Patterns:
    - MCP server: Deterministic user credentials
    - Page objects: UI authentication flow
    - Auth API client: Token-based API authentication
    - Users API client: Authenticated API operations
    
    This demonstrates the authentication integration across all system layers.
    """
    
    # Step 1: Create test user
    with allure.step("Create test user via MCP"):
        user_data = mcp_client.seed_user(
            role="editor",
            attributes={"first_name": "Auth", "last_name": "Test"}
        )
        test_email = user_data["email"]
        test_password = user_data["password"]
        user_id = user_data["user_id"]
        
        allure.attach(
            f"Test user: {test_email}\nRole: editor",
            name="User Credentials",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 2: Authenticate via API and get tokens
    with allure.step("Authenticate via API to obtain JWT tokens"):
        login_response = auth_api.login(
            email=test_email,
            password=test_password,
            remember_me=True
        )
        
        access_token = login_response.access_token
        refresh_token = login_response.refresh_token
        
        assert access_token, "Access token should be present in login response"
        assert refresh_token, "Refresh token should be present in login response"
        assert login_response.token_type == "Bearer", \
            f"Token type should be Bearer, got: {login_response.token_type}"
        
        allure.attach(
            f"Token Type: {login_response.token_type}\n"
            f"Expires In: {login_response.expires_in} seconds\n"
            f"User ID: {login_response.user_id}\n"
            f"Role: {login_response.role}",
            name="Authentication Success",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 3: Use access token for API operations
    with allure.step("Perform authenticated API operations"):
        users_api.set_auth_token(access_token)
        
        # Fetch user profile via API
        user_profile = users_api.get_user(user_id)
        
        assert user_profile.id == user_id, \
            f"User ID mismatch: expected {user_id}, got {user_profile.id}"
        assert user_profile.email == test_email, \
            f"Email mismatch: expected {test_email}, got {user_profile.email}"
        # Note: MCP server maps editor -> moderator in the sample app
        assert user_profile.role.value == "moderator", \
            f"Role mismatch: expected moderator (mapped from editor), got {user_profile.role.value}"
        
        allure.attach(
            f"API Profile Fetch Successful:\n"
            f"  ID: {user_profile.id}\n"
            f"  Name: {user_profile.name}\n"
            f"  Email: {user_profile.email}\n"
            f"  Role: {user_profile.role.value}",
            name="Authenticated API Operation",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 4: Login via UI with same credentials
    with allure.step("Login via UI to verify dual authentication paths"):
        login_page = LoginPage(page)
        login_page.navigate_to_login()
        login_page.login(email=test_email, password=test_password)
        
        # Verify successful UI login
        dashboard_page = DashboardPage(page)
        dashboard_page.verify_dashboard_loaded()
        
        welcome_message = dashboard_page.get_welcome_message()
        assert "Auth" in welcome_message, \
            f"Welcome message should contain user name. Got: {welcome_message}"
        
        allure.attach(
            f"UI Login Successful. Welcome: {welcome_message}",
            name="UI Authentication",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 5: Refresh token workflow
    with allure.step("Test token refresh workflow"):
        refreshed_response = auth_api.refresh_token(refresh_token)
        
        new_access_token = refreshed_response.access_token
        assert new_access_token, "New access token should be present"
        assert new_access_token != access_token, \
            "Refreshed token should be different from original"
        
        # Use new token for API operation
        users_api.set_auth_token(new_access_token)
        refreshed_profile = users_api.get_user(user_id)
        assert refreshed_profile.email == test_email, \
            "Refreshed token should work for API operations"
        
        allure.attach(
            f"Token refresh successful\n"
            f"New token expires in: {refreshed_response.expires_in} seconds",
            name="Token Refresh",
            attachment_type=allure.attachment_type.TEXT
        )
    
    # Step 6: Logout and verify session invalidation
    with allure.step("Logout and verify session termination"):
        # Logout via API
        auth_api.set_auth_token(new_access_token)
        auth_api.logout()
        
        # Logout via UI
        dashboard_page.logout()
        expect(page).to_have_url(re.compile(r".*/login.*"))
        
        allure.attach(
            "Logout successful via both API and UI",
            name="Session Termination",
            attachment_type=allure.attachment_type.TEXT
        )


# ======================================================================================
# INTEGRATION TEST CONFIGURATION
# ======================================================================================

# pytest configuration for this module
pytestmark = [
    pytest.mark.integration,  # Mark all tests in this file as integration tests
    pytest.mark.slow,  # Integration tests typically take longer than unit tests
]

"""
Running these integration tests:
--------------------------------

1. Run all integration tests:
   pytest tests/integration/test_end_to_end.py -v

2. Run with Allure reporting:
   pytest tests/integration/test_end_to_end.py --alluredir=allure-results
   allure serve allure-results

3. Run specific test:
   pytest tests/integration/test_end_to_end.py::test_complete_user_registration_login_profile_flow -v

4. Run with browser headed (visible):
   pytest tests/integration/test_end_to_end.py --headed

5. Run with specific browser:
   pytest tests/integration/test_end_to_end.py --browser firefox

6. Run in parallel (faster execution):
   pytest tests/integration/test_end_to_end.py -n auto

Test Dependencies:
------------------
These tests require the following fixtures from conftest.py:
- page: Playwright Page instance with isolated browser context
- mcp_client: MCPClient instance connected to FastAPI MCP server
- auth_api: AuthAPIClient instance for authentication operations
- users_api: UsersAPIClient instance for user management operations

Environment Variables Required:
-------------------------------
- BASE_URL: Web application base URL (e.g., http://localhost:3000)
- API_BASE_URL: REST API base URL (e.g., http://localhost:8000/api)
- FASTAPI_MCP_URL: MCP server URL (e.g., http://localhost:8001)
- FASTAPI_MCP_TOKEN: MCP server authentication token
- HEADLESS: Boolean flag for headless browser execution (default: true)

MCP Server Requirement:
-----------------------
The FastAPI MCP server must be running before executing these tests.
In CI/CD, the server is started as a service. For local development:

```bash
cd mcp_servers/fastapi_mcp
python -m uvicorn main:app --port 8001
```

Framework Architecture Notes:
-----------------------------
These integration tests demonstrate the complete framework architecture:

1. Test Data Layer (MCP):
   - Deterministic, non-conflicting test data
   - Parallel-friendly user generation
   - No hardcoded credentials

2. UI Automation Layer (Playwright + Page Objects):
   - Stable ARIA-based locators
   - Business-readable page object methods
   - Isolated browser contexts per test

3. API Validation Layer (httpx + Type-safe Clients):
   - Pydantic request/response validation
   - Typed API operations
   - Cross-layer data verification

4. Reporting Layer (Allure):
   - Hierarchical test step visualization
   - Screenshot and attachment capture
   - Business-readable test documentation

This architecture ensures:
- Tests are maintainable (stable locators, clear abstractions)
- Tests are reliable (deterministic data, isolated contexts)
- Tests are fast (parallel execution, no wait times)
- Tests are readable (business domain language, clear intent)
"""
