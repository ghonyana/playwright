"""API Test Module Package.

This package contains traditional pytest-based API integration tests, complementing
the BDD feature tests with direct API endpoint testing.

Test Structure:
    - test_auth_api.py: Authentication and authorization API tests
    - test_users_api.py: User management API tests

These tests use httpx clients from tests/api_clients/ and can leverage MCP server
tools for deterministic test data management via tests/helpers/mcp_client.py.

Example Usage:
    Run all API tests:
        pytest tests/api/

    Run specific API test module:
        pytest tests/api/test_users_api.py

    Run with parallel execution:
        pytest tests/api/ -n auto

Integration:
    - Imports API clients from tests/api_clients/
    - Uses MCP client fixtures from tests/conftest.py
    - Generates Allure reports via allure-pytest plugin
    - Executes in CI/CD via GitHub Actions workflows
"""
