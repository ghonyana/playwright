"""
FastAPI MCP (Model Context Protocol) Server Package

This package implements a FastAPI-based Model Context Protocol server that provides
deterministic test data management tools for the pytest automation framework.

Overview
--------
The FastAPI MCP server exposes JSON-RPC style endpoints that enable tests to:
- Create deterministic test users with specific roles and attributes
- Build valid request payloads from predefined templates
- Reset test environment state between test runs
- Query current environment state for debugging and verification

This server is designed to run alongside pytest tests in CI/CD pipelines and local
development environments to ensure tests start from known-good states and remain
isolated, deterministic, and parallel-friendly.

Architecture
-----------
The package follows a clean architecture pattern with clear separation of concerns:

    ├── main.py           - FastAPI application entry point and server initialization
    ├── config.py         - Environment-based configuration management
    ├── models.py         - Pydantic request/response models for tool endpoints
    ├── routers/          - API endpoint route handlers
    │   ├── tools.py      - MCP tool endpoints (seed_user, build_payload, etc.)
    │   └── health.py     - Health check endpoint for monitoring
    ├── services/         - Business logic for test data operations
    │   ├── user_service.py      - User creation and management
    │   ├── payload_service.py   - Template-based payload generation
    │   └── state_service.py     - Environment state management
    ├── database/         - Data persistence layer (optional)
    │   ├── connection.py - Database connection management
    │   └── models.py     - Database models
    └── auth/             - Authentication and authorization
        └── bearer.py     - Bearer token validation

MCP Tools Exposed
----------------
1. seed_user
   - Creates a test user in the target application
   - Accepts: role (ADMIN, EDITOR, VIEWER), email, name, custom attributes
   - Returns: user_id, email, generated password, creation timestamp
   - Use case: Ensure tests have specific users available without hardcoding

2. build_payload
   - Generates valid request bodies from templates
   - Accepts: template_name, parameters dictionary
   - Returns: Complete JSON payload ready for API requests
   - Use case: Avoid hardcoded test data, ensure payload validity

3. reset_env
   - Clears test data and resets environment to clean state
   - Accepts: scope (all, users, projects, data)
   - Returns: success status and count of items deleted
   - Use case: Ensure test isolation, run tests from known state

4. query_state
   - Inspects current environment state for debugging
   - Accepts: resource_type, optional filters
   - Returns: count and list of matching resources
   - Use case: Debug test failures, verify environment state

Usage
-----
Starting the server locally:
    
    $ cd mcp_servers/fastapi_mcp
    $ python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Or using the convenience script:
    
    $ ./mcp_servers/scripts/start_fastapi_mcp.sh

In CI/CD (GitHub Actions):
    
    services:
      fastapi-mcp:
        image: python:3.11
        env:
          AUTH_SECRET_KEY: ${{ secrets.MCP_TOKEN }}
          APP_BASE_URL: http://localhost:3000
          APP_API_URL: http://localhost:3000/api
        ports:
          - 8000:8000
        cmd: |
          pip install -r mcp_servers/fastapi_mcp/requirements.txt
          python -m mcp_servers.fastapi_mcp.main

From pytest tests:
    
    from tests.helpers.mcp_client import MCPClient
    
    @pytest.fixture(scope="session")
    def mcp_client():
        return MCPClient(
            base_url=os.getenv("FASTAPI_MCP_URL", "http://localhost:8000"),
            token=os.getenv("FASTAPI_MCP_TOKEN")
        )
    
    def test_with_admin_user(mcp_client):
        # Create a deterministic admin user
        user = mcp_client.seed_user(role="ADMIN", email="admin@test.local")
        
        # Build a valid payload for creating a project
        payload = mcp_client.build_payload("create_project", {
            "owner_id": user.user_id,
            "name": "Test Project"
        })
        
        # Run test with seeded data...

Configuration
------------
The server is configured via environment variables (loaded from .env file):

Required:
    - AUTH_SECRET_KEY: Secret key for JWT token generation/validation
    - APP_BASE_URL: Base URL of the application under test (e.g., http://localhost:3000)
    - APP_API_URL: API endpoint URL of the application under test

Optional:
    - HOST: Server host address (default: 0.0.0.0)
    - PORT: Server port (default: 8000)
    - RELOAD: Enable auto-reload on code changes (default: False)
    - AUTH_ALGORITHM: JWT algorithm (default: HS256)
    - AUTH_TOKEN_EXPIRE_MINUTES: Token expiration time (default: 60)
    - APP_ADMIN_EMAIL: Admin user email for privileged operations
    - APP_ADMIN_PASSWORD: Admin user password
    - DATABASE_URL: Optional database connection string for state persistence

Security
--------
The MCP server implements bearer token authentication to prevent unauthorized access:
- All tool endpoints require a valid JWT token in the Authorization header
- Tokens are generated using the AUTH_SECRET_KEY configuration
- Health check endpoint is public for monitoring purposes
- CORS is configured to allow test framework origins

Integration Points
-----------------
This package integrates with:
- **pytest**: Tests import MCPClient helper to call tool endpoints
- **Target Application**: Server makes HTTP requests to seed data and query state
- **CI/CD**: GitHub Actions starts this server as a service before running tests
- **Database (optional)**: SQLAlchemy for persistent test data state management

Version History
--------------
0.1.0 (2024-01) - Initial implementation
    - Core MCP tool endpoints (seed_user, build_payload, reset_env, query_state)
    - FastAPI application with CORS and authentication
    - Pydantic models for request/response validation
    - Service layer for business logic
    - Health check endpoint

Dependencies
-----------
See requirements.txt for complete dependency list. Key dependencies:
- fastapi==0.118.0: Web framework
- uvicorn==0.34.0: ASGI server
- pydantic==2.10.5: Data validation
- pydantic-settings==2.7.0: Configuration management
- python-jose==3.3.0: JWT token handling
- passlib==1.7.4: Password hashing

Development
----------
To work on this package:

1. Install dependencies:
   $ pip install -r mcp_servers/fastapi_mcp/requirements.txt

2. Set up environment:
   $ cp .env.example .env
   $ # Edit .env with your configuration

3. Run tests:
   $ pytest mcp_servers/fastapi_mcp/tests/

4. Run the server with auto-reload:
   $ python -m uvicorn mcp_servers.fastapi_mcp.main:app --reload

5. View API documentation:
   - OpenAPI/Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

Contributing
-----------
When extending this package:
- Add new tool endpoints in routers/tools.py
- Implement business logic in services/
- Define Pydantic models in models.py for request/response validation
- Update this documentation with new tools and their usage
- Ensure all tools follow MCP JSON-RPC patterns
- Write tests for new functionality
- Update the API documentation with examples

License
-------
See LICENSE file in repository root for licensing information.

Notes
-----
- This package is part of the larger pytest automation framework
- Designed for deterministic test execution in CI/CD pipelines
- Production-ready with comprehensive error handling and logging
- Supports both local development and CI/CD deployment scenarios
- Integrates with Playwright MCP server (optional, for LLM-driven exploration)

For detailed documentation, see docs/mcp_servers.md in the repository root.
"""

__version__ = "0.1.0"
__author__ = "Test Automation Team"
__license__ = "See LICENSE file"

# Package components are available via explicit imports:
# Example usage:
#   from mcp_servers.fastapi_mcp.main import app
#   from mcp_servers.fastapi_mcp.config import settings
#   from mcp_servers.fastapi_mcp.models import UserRole, SeedUserRequest
