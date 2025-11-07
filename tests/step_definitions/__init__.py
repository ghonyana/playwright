"""
pytest-bdd Step Definitions Package

This package contains step definition modules that implement Gherkin Given/When/Then
steps for BDD test scenarios. Step definitions serve as the bridge between high-level,
business-readable Gherkin scenarios and the underlying test automation implementation.

Architecture:
-------------
Step definitions delegate to page objects and API clients while maintaining high-level,
business-readable semantics. This separation ensures that Gherkin scenarios remain
stable and focused on business logic, while implementation details are encapsulated
in page objects and API clients.

Key Principles:
---------------
1. **Business-Readable Steps**: Steps use plain language understandable by non-technical
   stakeholders, avoiding implementation details like CSS selectors or API endpoints.

2. **High-Level Abstraction**: Steps describe WHAT should happen, not HOW it happens.
   Example: "When the user logs in with valid credentials" (not "When I click the login button")

3. **Delegation Pattern**: Step definitions delegate to:
   - Page Objects: For UI interactions (tests/pages/)
   - API Clients: For REST API calls (tests/api_clients/)
   - MCP Client: For test data management (tests/helpers/mcp_client.py)

4. **Reusability**: Common steps are centralized in common_steps.py to avoid duplication
   across feature-specific step modules.

5. **Isolation**: Steps should not maintain state between scenarios. Each scenario
   starts with a fresh browser context and clean test data.

Step Definition Modules:
------------------------
- **auth_steps**: Authentication and authorization scenarios (login, logout, permissions)
- **user_steps**: User management operations (create, read, update, delete users)
- **api_steps**: REST API endpoint testing (HTTP requests, response validation)
- **common_steps**: Reusable cross-cutting steps (navigation, assertions, waits)

pytest-bdd Discovery:
--------------------
pytest-bdd automatically discovers step definitions through module scanning at test
execution time. This __init__.py file marks the directory as a Python package,
enabling proper import resolution without requiring explicit imports.

Usage Example:
--------------
Step definitions are automatically discovered when pytest executes feature files:

    # tests/features/authentication.feature
    Feature: User Authentication
        Scenario: Successful login
            Given the user is on the login page
            When the user logs in with valid credentials
            Then the user should see the dashboard

    # tests/step_definitions/auth_steps.py
    from pytest_bdd import given, when, then
    
    @given("the user is on the login page")
    def go_to_login_page(login_page):
        login_page.navigate()
    
    @when("the user logs in with valid credentials")
    def login_with_credentials(login_page, mcp_client):
        user = mcp_client.seed_user(role="customer")
        login_page.login(user.email, user.password)
    
    @then("the user should see the dashboard")
    def verify_dashboard(dashboard_page):
        dashboard_page.verify_loaded()

Best Practices:
---------------
1. Keep step definitions thin - delegate to page objects and clients
2. Use fixtures for dependency injection (page objects, API clients, MCP client)
3. Avoid hardcoded test data - use MCP client for data generation
4. Write steps at the business level, not the UI implementation level
5. Group related steps in domain-specific modules (auth, user, api)
6. Use common_steps.py for frequently reused steps across features

Integration Points:
-------------------
- **pytest-bdd**: Automatic step discovery and Gherkin parsing
- **Page Objects** (tests/pages/): UI interaction implementation
- **API Clients** (tests/api_clients/): REST API interaction implementation
- **MCP Client** (tests/helpers/mcp_client.py): Test data management
- **Allure Reporting**: Step execution captured in test reports
- **conftest.py**: Fixture injection for dependencies

For more information:
---------------------
- pytest-bdd documentation: https://pytest-bdd.readthedocs.io/
- Gherkin syntax reference: https://cucumber.io/docs/gherkin/reference/
- Project documentation: docs/writing_tests.md
"""

__version__ = "1.0.0"

# Explicit module exports for step definition discovery
# Note: pytest-bdd automatically discovers steps without explicit imports,
# but __all__ provides clear documentation of available modules
__all__ = [
    "auth_steps",
    "user_steps",
    "api_steps",
    "common_steps",
]
