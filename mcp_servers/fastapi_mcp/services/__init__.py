"""
FastAPI MCP Server Services Package

This package contains the business logic layer for the FastAPI-based Model Context Protocol (MCP)
server that provides deterministic test data management for the test automation framework.

Services:
--------
- UserService: Test user seeding, password generation, and user management in the application
  under test. Provides the seed_user MCP tool for creating deterministic test users.
  
- PayloadService: Template-based request payload generation for API testing. Provides the
  build_payload MCP tool for constructing valid request bodies without hardcoded test data.
  
- StateService: Environment reset and state management for test isolation. Provides reset_env
  and query_state MCP tools for ensuring tests start from known-good states.

Architecture:
------------
The services layer abstracts application-specific integration details from the FastAPI routers,
implementing the dependency injection pattern. Each service is instantiated and injected into
router endpoints via FastAPI's Depends() mechanism, enabling:

- Clean separation of business logic from HTTP handling
- Testable service layer with mockable dependencies  
- Reusable service methods across multiple endpoints
- Centralized error handling and logging

Usage in Routers:
----------------
```python
from mcp_servers.fastapi_mcp.services.user_service import UserService
from mcp_servers.fastapi_mcp.services.payload_service import PayloadService
from mcp_servers.fastapi_mcp.services.state_service import StateService

@router.post("/tools/seed_user")
async def seed_user_tool(
    request: SeedUserRequest,
    user_service: UserService = Depends()
):
    return await user_service.create_test_user(
        role=request.role,
        email=request.email
    )
```

Integration Points:
------------------
- Application Under Test API: Services communicate with the target application via httpx
- Database Layer: StateService may use direct database access via mcp_servers.fastapi_mcp.database
- Configuration: All services access settings from mcp_servers.fastapi_mcp.config
- Models: Request/response validation via mcp_servers.fastapi_mcp.models

This package marker enables imports like:
  from mcp_servers.fastapi_mcp.services.user_service import UserService
"""
