Feature: API Operations
  As a system administrator
  I want to manage resources through the API
  So that I can integrate with external systems and automate workflows

  Background:
    Given the API service is available and accepting requests
    And I have valid authentication credentials

  Scenario: Create a new user resource via API
    Given the system is ready to accept new users
    When a new user is created through the API with valid information
    Then the user is successfully registered in the system
    And the user information can be retrieved
    And the user appears in the active users list

  Scenario: Retrieve existing user data
    Given a user account exists in the system with email "testuser@example.com"
    When the user information is requested through the API
    Then the complete user profile is returned
    And the data matches the expected format
    And all required fields are present

  Scenario: Update user profile information
    Given a user account exists with username "johndoe"
    When the user profile is updated with new contact information
    Then the changes are successfully applied
    And the updated data is immediately available
    And the modification timestamp is updated

  Scenario: Delete a user account
    Given a user account exists with email "deleteme@example.com"
    When the user account is deleted through the API
    Then the account is removed from the system
    And subsequent retrieval attempts fail gracefully
    And the user no longer appears in search results

  Scenario: API rejects invalid input data
    Given the system enforces data validation rules
    When invalid user data is submitted through the API with missing required fields
    Then the request is rejected with a validation error
    And an appropriate error message is returned
    And the error details specify which fields are invalid

  Scenario: Retrieve paginated user list
    Given multiple users exist in the system with at least 50 accounts
    When the user list is requested with pagination parameters
    Then the results are returned in the requested page size
    And navigation metadata is included for next and previous pages
    And the total count of users is provided

  Scenario: API enforces authentication requirements
    Given an API endpoint requires valid authentication
    When a request is made without authentication credentials
    Then access is denied to the protected resource
    And an authentication prompt is returned
    And no sensitive data is exposed

  Scenario: Bulk user creation via API
    Given the system supports batch operations
    When multiple users are submitted in a single API request
    Then all valid users are created successfully
    And any invalid entries are reported with details
    And the response includes success count and failure count

  Scenario: Search users by criteria
    Given multiple users exist with different roles and attributes
    When a search is performed with specific filter criteria
    Then only users matching the criteria are returned
    And the results are sorted by the specified field
    And search metadata includes filter information

  Scenario: API handles concurrent user updates
    Given a user account exists with current version information
    When two concurrent update requests are made to the same user
    Then the first update is applied successfully
    And the second update is rejected due to version conflict
    And the response indicates the data has changed

  Scenario: Retrieve user activity history
    Given a user has performed multiple actions in the system
    When the user activity history is requested
    Then a chronological list of activities is returned
    And each activity includes timestamp and action type
    And the history can be filtered by date range

  Scenario: API rate limiting protects system resources
    Given the API has rate limiting configured
    When excessive requests are made within a short time period
    Then requests are throttled after exceeding the limit
    And the response indicates rate limit exceeded
    And retry-after information is provided

  Scenario: Partial update of user attributes
    Given a user account exists with multiple attributes
    When a partial update is requested for specific fields only
    Then only the specified fields are modified
    And unchanged fields retain their original values
    And the update does not affect related data

  Scenario: API returns error for non-existent resource
    Given no user exists with identifier "nonexistent-user-id"
    When user information is requested for that identifier
    Then the operation fails gracefully
    And an appropriate not found message is returned
    And the response suggests valid actions

  Scenario: Export user data in specified format
    Given users exist in the system with complete profile data
    When a data export is requested in a specific format
    Then the user data is returned in the requested format
    And all requested fields are included
    And the export includes metadata about the data set
