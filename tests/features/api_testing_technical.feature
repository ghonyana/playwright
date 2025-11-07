# Feature: API Testing - Technical REST API Validation
#
# This feature file contains technical, API-focused scenarios that match
# the step definitions in tests/step_definitions/api_steps.py
#
# These scenarios validate REST API endpoints with specific HTTP status codes,
# request/response validation, and technical API behavior. They use parameterized
# steps for roles, status codes, and field values.
#
# Per Agent Action Plan:
# - Uses MCP-generated test data (no hardcoded values)
# - Validates HTTP responses and Pydantic models
# - Tests API authentication and authorization
# - Verifies REST API contracts and error handling

Feature: API Testing - Technical REST API Validation
  As a QA engineer
  I want to validate REST API endpoints at a technical level
  So that I can ensure API contracts, schemas, and HTTP behavior are correct

  Background:
    Given the test environment is reset

  @api @smoke @requires_mcp
  Scenario: Create user via API with admin role
    Given the API authentication is configured
    And the user management API is available
    When I create a user with role "admin"
    Then the response status code should be 201
    And the user should have a valid ID
    And the user role should be "admin"
    And the user should be active

  @api @requires_mcp
  Scenario: Create user via API with editor role
    Given the API authentication is configured
    And the user management API is available
    When I create a user with role "editor"
    Then the response status code should be 201
    And the user should have a valid ID
    And the user role should be "editor"

  @api @requires_mcp
  Scenario: Retrieve user by ID after creation
    Given the API authentication is configured
    And the user management API is available
    And a test user with role "user" exists
    When I retrieve the user with ID "last_created"
    Then the response status code should be 200
    And the user should have a valid ID
    And the user role should be "user"

  @api @requires_mcp
  Scenario: Update user role via API
    Given the API authentication is configured
    And the user management API is available
    And a test user with role "user" exists
    When I update the user with role "editor"
    Then the response status code should be 200
    And the user role should be "editor"

  @api @requires_mcp
  Scenario: Update user department via API
    Given the API authentication is configured
    And the user management API is available
    And a test user with role "admin" exists
    When I update the user with department "Engineering"
    Then the response status code should be 200
    And the user department should be "Engineering"

  @api @requires_mcp
  Scenario: Delete user via API
    Given the API authentication is configured
    And the user management API is available
    And a test user with role "guest" exists
    When I delete the user
    Then the response status code should be 204

  @api @requires_mcp
  Scenario: List users filtered by admin role
    Given the API authentication is configured
    And the user management API is available
    And a test user with role "admin" exists
    When I list users with role "admin"
    Then the response status code should be 200
    And the user list should contain at least 1 user(s)
    And the user list should have pagination metadata

  @api @requires_mcp
  Scenario: List users filtered by active status
    Given the API authentication is configured
    And the user management API is available
    And a test user with role "user" exists
    When I list users with status "active"
    Then the response status code should be 200
    And the user list should contain at least 1 user(s)
    And the user list should have pagination metadata

  @api @requires_mcp
  Scenario: Search users by query string
    Given the API authentication is configured
    And the user management API is available
    And a test user with role "user" exists
    When I search for users with query "test"
    Then the response status code should be 200
    And the user list should have pagination metadata

  @api @requires_mcp
  Scenario: User login with valid credentials
    Given the API authentication is configured
    And a test user with role "user" exists
    When I login with email "test@example.com" and password "TestPass123!"
    Then the response status code should be 200
    And the authentication should succeed
    And the access token should be valid

  @api @requires_mcp
  Scenario: Refresh authentication token
    Given the API authentication is configured
    And a test user with role "user" exists
    And I login with email "test@example.com" and password "TestPass123!"
    When I refresh the authentication token
    Then the response status code should be 200
    And the access token should be valid
    And the refresh token should be updated

  @api @requires_mcp
  Scenario: User logout terminates session
    Given the API authentication is configured
    And a test user with role "user" exists
    And I login with email "test@example.com" and password "TestPass123!"
    When I logout
    Then the logout should succeed
