"""
API Clients Package for Test Automation Framework

This package provides typed HTTP client wrappers for API testing, built on httpx
with integration to the FastAPI MCP server for dynamic test data and payload generation.

Package Structure:
------------------
- base_client: BaseAPIClient with common HTTP methods and Allure integration
- auth_client: AuthAPIClient for authentication endpoints
- users_client: UsersAPIClient for user management endpoints
- models/: Pydantic models for API request/response validation

Usage in Tests:
--------------
Direct import of individual clients:
    >>> from tests.api_clients.base_client import BaseAPIClient
    >>> from tests.api_clients.auth_client import AuthAPIClient
    >>> from tests.api_clients.users_client import UsersAPIClient

Convenience imports from package root:
    >>> from tests.api_clients import AuthAPIClient, UsersAPIClient

In conftest.py fixtures:
    >>> @pytest.fixture
    >>> def auth_api(httpx_client):
    ...     from tests.api_clients import AuthAPIClient
    ...     return AuthAPIClient(base_url=os.getenv("API_BASE_URL"), client=httpx_client)

Integration Points:
------------------
- httpx: Modern async/sync HTTP client for API calls
- MCP Client: Dynamic payload generation via FastAPI MCP server
- Allure: Automatic request/response attachment for reports
- pytest: Fixture-based dependency injection

Design Principles:
-----------------
- Type safety: All request/response models use Pydantic for validation
- DRY: Common HTTP methods and configuration in BaseAPIClient
- Testability: Clients accept httpx.Client for easy mocking with pytest-httpx
- Observability: Automatic Allure attachment of API interactions
- Determinism: Use MCP build_payload tool instead of hardcoded test data

Author: Blitzy Platform
License: As per project LICENSE file
"""

# Convenience imports for cleaner test code
# These imports will be available once the corresponding modules are created
# by other Blitzy agents as part of the complete framework implementation

__all__ = [
    "BaseAPIClient",
    "AuthAPIClient",
    "UsersAPIClient",
]

# Version identifier for the API clients package
__version__ = "1.0.0"

# Package metadata for introspection
__package_name__ = "tests.api_clients"
__description__ = "Typed HTTP client wrappers for API test automation"
