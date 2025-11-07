Feature: User Management
  As an administrator and user
  I want to manage user accounts and profiles
  So that I can control access and maintain accurate user information

  Background:
    Given the system is ready for user management operations

  Scenario: Create a new user account
    Given an administrator is logged into the system
    When the administrator creates a new user with email "john.doe@example.com"
    Then the new user account is successfully created
    And a welcome email is sent to "john.doe@example.com"
    And the user appears in the user directory

  Scenario: Update user profile information
    Given a user "jane.smith@example.com" is logged in
    When the user updates their profile with new phone number "555-0123"
    And the user updates their display name to "Jane Smith"
    Then the system confirms the profile changes were saved
    And the updated information is displayed on the user profile
    And the profile modification timestamp is updated

  Scenario: Assign role to existing user
    Given an administrator is managing user accounts
    And a user "bob.jones@example.com" exists with "Member" role
    When the administrator assigns the "Manager" role to "bob.jones@example.com"
    Then the user's role is updated to "Manager"
    And the role permissions are immediately active
    And the user receives a notification about the role change

  Scenario: Deactivate inactive user account
    Given an administrator needs to deactivate a user account
    And a user "inactive.user@example.com" exists in the system
    When the administrator deactivates the account for "inactive.user@example.com"
    Then the user account is marked as inactive
    And the user cannot log in with their credentials
    And the user's active sessions are terminated

  Scenario: Search for users by email
    Given an administrator is viewing the user management interface
    And multiple users exist in the system
    When the administrator searches for users with email containing "smith"
    Then all users with "smith" in their email are displayed
    And the search results show username, email, and status
    And the results are sorted alphabetically by email

  Scenario: Update email address with verification
    Given a user "current.email@example.com" is logged in
    When the user updates their email address to "new.email@example.com"
    And the user confirms the email change request
    Then a verification email is sent to "new.email@example.com"
    And the old email "current.email@example.com" remains active
    And the user receives a notification at the old email address

  Scenario: Reactivate deactivated user account
    Given an administrator is managing user accounts
    And a user "reactivate.user@example.com" has an inactive account
    When the administrator reactivates the account for "reactivate.user@example.com"
    Then the user account is marked as active
    And the user can log in with their credentials
    And an account reactivation email is sent to the user

  Scenario: View user profile details
    Given an administrator is logged into the system
    When the administrator views the profile of user "detail.user@example.com"
    Then the user's full name is displayed
    And the user's email address is displayed
    And the user's current role is displayed
    And the user's account status is displayed
    And the account creation date is displayed

  Scenario: Bulk user role assignment
    Given an administrator is managing user accounts
    And users "user1@example.com", "user2@example.com", and "user3@example.com" exist
    When the administrator assigns the "Contributor" role to all three users
    Then all three users receive the "Contributor" role
    And role change notifications are sent to all affected users

  Scenario: Change user password
    Given a user "password.user@example.com" is logged in
    When the user changes their password to a new secure password
    And the user confirms the password change
    Then the system confirms the password was updated successfully
    And the user receives a password change confirmation email
    And the user can log in with the new password

  Scenario: Delete user account permanently
    Given an administrator needs to permanently remove a user
    And a user "delete.user@example.com" has been deactivated
    When the administrator permanently deletes the account for "delete.user@example.com"
    And the administrator confirms the deletion action
    Then the user account is permanently removed from the system
    And all associated user data is marked for deletion
    And the email address becomes available for reuse

  Scenario: Search users by role
    Given an administrator is viewing the user management interface
    And users with various roles exist in the system
    When the administrator filters users by "Manager" role
    Then only users with the "Manager" role are displayed
    And the total count of managers is shown
    And each result displays the user's name and email

  Scenario: Update user account status
    Given an administrator is managing a user account
    And a user "status.user@example.com" has an active account
    When the administrator changes the account status to "Suspended"
    And the administrator provides a suspension reason
    Then the user account is marked as suspended
    And the user cannot access the system
    And the user receives a suspension notification email

  Scenario: Assign multiple roles to user
    Given an administrator is managing user permissions
    And a user "multi.role@example.com" exists with "Member" role
    When the administrator assigns additional roles "Contributor" and "Reviewer"
    Then the user has all three roles: "Member", "Contributor", and "Reviewer"
    And the user has combined permissions from all roles
    And the role assignment is logged in the audit trail

  Scenario: Remove role from user
    Given an administrator is managing user permissions
    And a user "remove.role@example.com" has roles "Member" and "Manager"
    When the administrator removes the "Manager" role
    Then the user retains only the "Member" role
    And the manager permissions are immediately revoked
    And the user receives a notification about the role removal

  Scenario: View user activity history
    Given an administrator is reviewing user activities
    When the administrator views the activity history for "active.user@example.com"
    Then the user's recent login history is displayed
    And the user's profile modification history is shown
    And the user's role change history is displayed
    And all activities show timestamps and initiating users
