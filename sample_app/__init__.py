"""
Sample Application Package

This package provides a demonstration Flask web application for testing the
pytest-based test automation framework. It serves as a concrete target for:

- UI testing with Playwright (login, dashboard, profile pages)
- API testing with httpx (REST endpoints for users and authentication)
- BDD testing with Gherkin scenarios (business-readable test cases)
- Integration testing combining UI and API interactions

The sample application implements:
- Session-based authentication for testing login flows
- CRUD operations on users for API testing
- Stable HTML elements with ARIA roles and test-ids for reliable locators
- In-memory data storage for test isolation and reset capabilities
- CORS-enabled API endpoints for cross-origin testing

Package Structure:
    sample_app/
    ├── __init__.py          # This file - package initialization and exports
    ├── app.py               # Main Flask application with web routes
    ├── api/                 # REST API endpoints
    │   ├── __init__.py
    │   └── routes.py        # User management and auth API
    ├── templates/           # Jinja2 HTML templates
    │   ├── login.html
    │   ├── dashboard.html
    │   └── user_profile_page.html
    └── static/              # Static assets (CSS, JS, images)
        └── css/
            └── styles.css

Usage Examples:
    # Import the Flask application instance directly
    from sample_app import app
    
    # Run the application
    app.run(host='0.0.0.0', port=5000)
    
    # Use in tests
    from sample_app import app
    client = app.test_client()
    response = client.get('/login')
    
    # Check package version
    from sample_app import __version__
    print(f"Sample App Version: {__version__}")

Integration with Test Framework:
    The sample_app is designed specifically for the test automation framework:
    
    1. Playwright UI Tests:
       - Navigate to http://localhost:5000/login
       - Use Page Object Pattern with stable locators
       - Test authentication flows and navigation
    
    2. httpx API Tests:
       - Make requests to http://localhost:5000/api/users
       - Test CRUD operations with typed API clients
       - Verify request/response payloads
    
    3. BDD Gherkin Scenarios:
       - Write business-readable scenarios
       - Use step definitions that call page objects and API clients
       - Combine UI and API interactions in integration tests
    
    4. MCP Server Integration:
       - Use MCP seed_user tool to create test users
       - Use MCP reset_env tool to reset application state
       - Use MCP build_payload tool to generate valid API requests

Environment Variables:
    - BASE_URL: Base URL for the application (default: http://localhost:5000)
    - SECRET_KEY: Flask secret key for session management
    - FLASK_ENV: Environment mode (development, testing, production)
    - FLASK_DEBUG: Enable debug mode (true/false)
    - HOST: Host to bind to (default: 0.0.0.0)
    - PORT: Port to listen on (default: 5000)

Notes:
    - This is a demonstration application, not production-ready
    - Data is stored in-memory and will be lost on restart
    - Authentication is basic and should not be used for real security
    - CORS is wide-open for testing convenience
    - The /reset endpoint allows resetting state between tests
"""

# Package version following semantic versioning
# Format: MAJOR.MINOR.PATCH
# - MAJOR: Incompatible API changes
# - MINOR: Backwards-compatible functionality additions
# - PATCH: Backwards-compatible bug fixes
__version__ = "0.1.0"

# Import and re-export the main Flask application instance
# This enables convenient imports: `from sample_app import app`
# Instead of the longer: `from sample_app.app import app`
from sample_app.app import app

# Explicit export list for `from sample_app import *`
# Following PEP 8 guidelines for package-level exports
__all__ = [
    '__version__',  # Package version string
    'app',          # Flask application instance
]

# Package-level metadata for introspection
__author__ = "Test Automation Framework Team"
__license__ = "MIT"
__description__ = "Sample Flask application for test automation framework demonstration"

# Application information accessible at package level
__app_name__ = "sample_app"
__app_description__ = "Demonstration web application for Playwright + pytest testing"
