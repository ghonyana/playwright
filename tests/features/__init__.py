"""
Gherkin Feature Files for BDD Test Scenarios.

This package contains business-readable test scenarios written in Gherkin format
using Given/When/Then syntax. Feature files in this directory are automatically
discovered and executed by the pytest-bdd plugin during test runs.

Structure:
----------
- Each .feature file contains one or more scenarios
- Scenarios describe application behavior from a user perspective
- Steps are high-level and business-readable (not implementation-focused)
- Step definitions are implemented in tests/step_definitions/

Integration:
-----------
- pytest.ini configures: bdd_features_base_dir = tests/features
- pytest-bdd plugin parses .feature files and matches them to step definitions
- Scenarios can use Scenario Outlines for data-driven testing
- Background sections define common preconditions across scenarios

Best Practices:
--------------
- Keep Gherkin steps at business level (avoid UI implementation details)
- Use ARIA roles and accessible patterns in step implementations
- Maintain scenario independence (each scenario should work in isolation)
- Prefer declarative scenarios over imperative step-by-step instructions

Example Feature File:
--------------------
Feature: User Authentication
  As a registered user
  I want to log into the application
  So that I can access my personalized dashboard

  Scenario: Successful login with valid credentials
    Given a user account exists with email "user@example.com"
    When the user logs in with valid credentials
    Then the user should see their personalized dashboard
    And the user should see a welcome message

For more information on writing effective Gherkin scenarios, see:
docs/writing_tests.md
"""
