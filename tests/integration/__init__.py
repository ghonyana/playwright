"""Integration tests package for the test automation framework.

This package contains end-to-end integration tests that validate complete
workflows combining UI (Playwright), API (httpx), and MCP server components.

Integration tests verify the interaction between multiple system components,
ensuring that the framework functions correctly as a cohesive whole. These
tests typically:

- Combine UI and API interactions in realistic user scenarios
- Validate data flow between UI, API, and backend systems
- Test MCP server integration with test data seeding and state management
- Verify Playwright browser automation with real application workflows
- Ensure proper test isolation and parallel execution capabilities

Test Organization:
-----------------
- test_end_to_end.py: Complete user journey scenarios
- Additional integration test modules as the framework expands

Usage:
------
Integration tests can be run with pytest:
    pytest tests/integration/
    pytest tests/integration/test_end_to_end.py
    pytest tests/integration/ -n auto  # Parallel execution

These tests are designed to be deterministic, isolated, and parallel-friendly,
following the framework's core principles for reliable test automation.
"""

__all__ = []  # No public API to export from this package marker
