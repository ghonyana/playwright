# Feature: User Authentication
#
# This feature covers core authentication workflows including login, logout,
# password management, and role-based access control. All scenarios are written
# in business-readable language focusing on user actions and outcomes.
#
# Business Value:
# - Ensures secure access to the application
# - Validates proper credential handling
# - Confirms role-based permissions work correctly
# - Verifies password recovery mechanisms

Feature: User Authentication
  As a registered user of the application
  I want to securely authenticate and manage my account
  So that I can access features appropriate to my role

  Background:
    Given the application is running and accessible
    And the test environment has been reset to a clean state

  @smoke @authentication @happy-path
  Scenario: Successful login with valid credentials
    Given a user account exists with role "customer"
    When the user logs in with valid credentials
    Then the user is successfully authenticated
    And the user sees the welcome dashboard
    And the user's session is active

  @authentication @error-handling
  Scenario: Login fails with incorrect password
    Given a user account exists with role "customer"
    When the user attempts to log in with an incorrect password
    Then the system displays an authentication error message
    And the user remains on the login page
    And no session is created

  @authentication @error-handling
  Scenario: Login fails with non-existent username
    Given no account exists for username "nonexistent@example.com"
    When the user attempts to log in with that username
    Then the system displays an authentication error message
    And the user remains on the login page

  @authentication @security
  Scenario: Account lockout after multiple failed login attempts
    Given a user account exists with role "customer"
    When the user attempts to log in with incorrect password 5 times
    Then the account is temporarily locked
    And the system displays an account locked message
    And further login attempts are blocked

  @smoke @authentication
  Scenario: Successful logout terminates user session
    Given a user is logged in with role "customer"
    When the user logs out of the application
    Then the user session is terminated
    And the user is redirected to the login page
    And the user cannot access protected pages

  @authentication @password-management
  Scenario: User requests password reset for forgotten password
    Given a user account exists with email "user@example.com"
    When the user requests a password reset
    Then the system sends a password reset email
    And the reset link is valid for 24 hours
    And the system displays a confirmation message

  @authentication @password-management
  Scenario: User successfully resets password using reset link
    Given a user has requested a password reset
    And the user has received a valid reset link
    When the user follows the reset link
    And the user enters a new valid password
    Then the password is successfully updated
    And the user can log in with the new password

  @authentication @password-management
  Scenario: Password reset link expires after time limit
    Given a user has requested a password reset
    And the reset link was generated more than 24 hours ago
    When the user attempts to use the expired reset link
    Then the system displays an expired link error
    And the user must request a new reset link

  @authentication @authorization @role-based
  Scenario: Admin user can access administrative features
    Given a user account exists with role "admin"
    When the user logs in with valid credentials
    Then the user is successfully authenticated
    And the user sees the admin dashboard
    And administrative features are available

  @authentication @authorization @role-based
  Scenario: Regular user cannot access admin features
    Given a user account exists with role "customer"
    When the user logs in with valid credentials
    And the user attempts to access admin features
    Then access is denied
    And the user sees an insufficient permissions message

  @authentication @authorization @role-based
  Scenario: Manager user has access to team management features
    Given a user account exists with role "manager"
    When the user logs in with valid credentials
    Then the user is successfully authenticated
    And the user sees the manager dashboard
    And team management features are available
    And administrative features are not available

  @authentication @session-management
  Scenario: User session persists across page navigation
    Given a user is logged in with role "customer"
    When the user navigates to different pages in the application
    Then the user remains authenticated on all pages
    And the session information is maintained

  @authentication @session-management
  Scenario: Inactive session expires after timeout period
    Given a user is logged in with role "customer"
    When the user remains inactive for more than 30 minutes
    Then the user session expires automatically
    And the user is redirected to the login page
    And the user must log in again to continue

  @authentication @security
  Scenario: User cannot reuse same session token after logout
    Given a user is logged in with role "customer"
    And the user's session token has been captured
    When the user logs out of the application
    And the user attempts to use the previous session token
    Then the request is rejected as unauthorized
    And the user must log in again

  @authentication @validation
  Scenario: Login form validates required fields
    Given the user is on the login page
    When the user attempts to log in without entering credentials
    Then the system displays field validation errors
    And the login form highlights required fields
    And no authentication attempt is made

  @authentication @security
  Scenario: Password field content is masked during entry
    Given the user is on the login page
    When the user enters their password
    Then the password characters are masked
    And the password is not visible in plain text

  @authentication @multi-factor
  Scenario: Two-factor authentication for admin users
    Given a user account exists with role "admin"
    And two-factor authentication is enabled for the account
    When the user logs in with valid credentials
    Then the system prompts for a two-factor code
    And the user enters the correct verification code
    And the user is successfully authenticated
    And the user sees the admin dashboard

  @authentication @multi-factor
  Scenario: Two-factor authentication fails with incorrect code
    Given a user account exists with role "admin"
    And two-factor authentication is enabled for the account
    When the user logs in with valid credentials
    And the user enters an incorrect verification code
    Then authentication fails
    And the user is prompted to retry the verification code
    And no session is created
