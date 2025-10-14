"""Test package for the Playwright test automation framework.

This package marker enables Python to recognize the tests/ directory as a package,
allowing for:
- pytest test discovery and collection
- Relative imports between test modules (e.g., from tests.pages import LoginPage)
- Import of page objects, API clients, and helpers from test files
- Package-level namespace for shared test constants or utilities

Organization:
- tests/features/: Gherkin BDD feature files
- tests/step_definitions/: pytest-bdd step implementations
- tests/pages/: Page Object Pattern implementations
- tests/api_clients/: Typed API client wrappers
- tests/helpers/: Test utility functions and fixtures
- tests/ui/: UI-specific test cases
- tests/api/: API-specific test cases
- tests/integration/: End-to-end integration tests

The package follows pytest best practices for test organization and supports
BDD workflows with pytest-bdd, Playwright browser automation, and httpx API testing.
"""

__all__ = []
