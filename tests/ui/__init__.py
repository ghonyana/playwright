"""UI Tests Package

This package contains traditional pytest-based UI tests (non-BDD) for the test automation framework.

Purpose:
    - Marks tests/ui/ as a Python package for pytest test discovery
    - Enables relative imports between UI test modules
    - Provides namespace for UI-specific test utilities and fixtures
    
Structure:
    - test_*.py files in this directory contain UI test cases
    - Tests use Playwright for browser automation
    - Page objects from tests/pages/ are imported for UI interactions
    - Tests follow pytest conventions and can run in parallel

Note:
    This package is for traditional pytest tests. BDD/Gherkin-based tests
    are located in tests/features/ and tests/step_definitions/.
"""
