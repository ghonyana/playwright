"""Test Helper Utilities Package.

This package provides reusable utility functions and classes for the test automation
framework, including:

- **MCP Client** (`mcp_client.py`): Client wrapper for interacting with Model Context
  Protocol (MCP) servers to manage test data, build payloads, and reset test environments.

- **Allure Utilities** (`allure_utils.py`): Helper functions for enhanced Allure reporting,
  including custom steps, attachments, and metadata management.

- **Data Generators** (`data_generators.py`): Test data generation utilities for creating
  realistic test data using Faker and custom generators.

- **Assertions** (`assertions.py`): Custom assertion helpers that provide business-readable
  assertion messages and integrate with Allure reporting.

- **Wait Conditions** (`wait_conditions.py`): Custom wait condition helpers for robust
  synchronization in UI and API tests.

Usage Examples
--------------

Import specific utilities::

    from tests.helpers.mcp_client import MCPClient
    from tests.helpers.allure_utils import allure_step
    from tests.helpers.data_generators import generate_user_data

Use in test files::

    def test_user_creation(mcp_client: MCPClient):
        # Use MCP client to seed test data
        user = mcp_client.seed_user(role="admin")
        assert user.email is not None

Use in conftest.py::

    from tests.helpers.mcp_client import MCPClient

    @pytest.fixture(scope="session")
    def mcp_client():
        return MCPClient(
            base_url=os.getenv("FASTAPI_MCP_URL"),
            token=os.getenv("FASTAPI_MCP_TOKEN")
        )

Design Principles
-----------------

All helper utilities in this package follow these principles:

1. **Reusability**: Functions and classes are designed to be used across multiple tests
   without duplication.

2. **Maintainability**: Clear naming conventions, comprehensive docstrings, and type hints
   ensure code is easy to understand and modify.

3. **Testability**: Utilities are designed with dependency injection to support mocking
   and unit testing.

4. **Integration**: Seamless integration with pytest fixtures, Allure reporting, and
   the MCP server ecosystem.

5. **Type Safety**: Full type hints for IDE support and static analysis with mypy.

Package Structure
-----------------

tests/helpers/
├── __init__.py           # This file - package marker and documentation
├── mcp_client.py         # MCP server client wrapper
├── allure_utils.py       # Allure reporting helpers
├── data_generators.py    # Test data generation utilities
├── assertions.py         # Custom assertion helpers
└── wait_conditions.py    # Custom wait condition helpers

Notes
-----

- This package marker file enables Python to recognize `tests/helpers/` as a package.
- All utilities are designed to work with pytest fixtures and can be injected as
  test function parameters.
- For detailed usage of individual utilities, refer to their respective module docstrings.

"""

# This file intentionally contains only the package docstring.
# Individual utilities are imported directly from their respective modules:
#   from tests.helpers.mcp_client import MCPClient
#   from tests.helpers.allure_utils import allure_step
#   from tests.helpers.data_generators import generate_user_data
#   from tests.helpers.assertions import assert_response_status
#   from tests.helpers.wait_conditions import wait_for_condition

# Explicit package marker per PEP 420 for maximum compatibility
__all__ = []
