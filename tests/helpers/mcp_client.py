"""
MCP (Model Context Protocol) Server Client Wrapper

This module provides a Python client for interacting with the FastAPI MCP server,
enabling deterministic test data management and environment state control.

Per Agent Action Plan Section 0.4.2 and user directive:
"Use MCP tools for data/state (don't hard-code test data)"

The MCPClient eliminates hardcoded test data and ensures parallel-friendly test
execution by providing tools for:
- seed_user: Create test users with unique, non-conflicting emails
- build_payload: Generate API request bodies from templates
- reset_env: Reset test environment to known-good state
- query_state: Inspect current test data for verification

This is a FOUNDATIONAL file used by:
- tests/conftest.py (provides mcp_client fixture)
- All test files requiring test data
- Step definitions in tests/step_definitions/
"""

import httpx
import os
from typing import Dict, Any, Optional


class MCPClient:
    """
    Client for FastAPI MCP server providing deterministic test data management.
    
    This client wraps the MCP server's JSON-RPC endpoints with a clean Python API,
    handling authentication, connection management, and error reporting.
    
    Per Agent Action Plan Section 5.4.2: "Data Management and MCP Integration"
    
    Attributes:
        base_url (str): MCP server base URL (e.g., "http://localhost:8000")
        client (httpx.Client): Configured HTTP client with authentication headers
    
    Example:
        >>> client = MCPClient("http://localhost:8000", "secret-token")
        >>> user = client.seed_user(role="admin")
        >>> print(user['email'])  # admin-a3f9d82@test.local
    """
    
    def __init__(self, base_url: str, token: str):
        """
        Initialize MCP client with server URL and authentication token.
        
        Args:
            base_url: MCP server base URL (e.g., "http://localhost:8000")
            token: Authentication token from FASTAPI_MCP_TOKEN env var
                   Used as Bearer token in Authorization header
        
        Raises:
            ValueError: If base_url or token is empty/None
        """
        if not base_url:
            raise ValueError("base_url cannot be empty")
        if not token:
            raise ValueError("token cannot be empty")
        
        self.base_url = base_url.rstrip('/')  # Normalize URL
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,  # 30 second timeout for all requests
            follow_redirects=True
        )
    
    def health_check(self) -> dict[str, Any]:
        """
        Verify MCP server is available and responding.
        
        This method should be called before test execution to ensure the MCP
        server is ready. Per CI/CD integration requirements, tests should
        wait for this endpoint to succeed before proceeding.
        
        Returns:
            dict: Health status response, typically:
                {
                    "status": "healthy",
                    "version": "1.0.0",
                    "timestamp": "2024-01-15T10:30:00Z"
                }
        
        Raises:
            httpx.HTTPError: If server is unavailable or returns error status
            httpx.ConnectError: If unable to connect to server
            httpx.TimeoutException: If server doesn't respond within timeout
        
        Example:
            >>> try:
            ...     status = client.health_check()
            ...     print(f"MCP server is {status['status']}")
            ... except httpx.HTTPError as e:
            ...     print(f"MCP server unavailable: {e}")
        """
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.ConnectError as e:
            raise httpx.ConnectError(
                f"Cannot connect to MCP server at {self.base_url}. "
                f"Ensure the FastAPI MCP server is running. Error: {e}"
            ) from e
        except httpx.TimeoutException as e:
            raise httpx.TimeoutException(
                f"MCP server at {self.base_url} timed out after 30 seconds. "
                f"Server may be overloaded or unresponsive. Error: {e}"
            ) from e
    
    def seed_user(
        self,
        role: str,
        email: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Create test user via MCP server with deterministic, non-conflicting data.
        
        Per user directive: "Use MCP tools for data/state (don't hard-code test data)"
        
        The MCP server generates unique email addresses and passwords to avoid
        conflicts in parallel test execution. Each user is created in the target
        application and a valid authentication token is returned.
        
        Args:
            role: User role (e.g., "admin", "customer", "guest")
                  Determines permissions and capabilities of the test user
            email: Optional email address. If not provided, MCP generates unique
                   email like "admin-a3f9d82@test.local" to avoid conflicts
            attributes: Optional additional user attributes like:
                       {"age": 30, "country": "US", "subscription": "premium"}
        
        Returns:
            dict: Created user data including:
                - id (int): User ID in target system
                - email (str): Email address (auto-generated if not provided)
                - role (str): User role
                - password (str): Generated password for UI login
                - auth_token (str): Valid JWT token for API requests
                - attributes (dict): Any additional attributes provided
        
        Raises:
            httpx.HTTPError: If user creation fails (e.g., invalid role,
                            target application unavailable)
        
        Example:
            >>> # Create admin user with auto-generated email
            >>> admin = client.seed_user(role="admin")
            >>> print(admin)
            {
                "id": 123,
                "email": "admin-a3f9d82@test.local",
                "role": "admin",
                "password": "Test123!",
                "auth_token": "eyJhbGc..."
            }
            
            >>> # Create customer with specific email and attributes
            >>> customer = client.seed_user(
            ...     role="customer",
            ...     email="john@example.com",
            ...     attributes={"age": 30, "country": "US"}
            ... )
        """
        # Build payload with proper field names expected by MCP server
        payload = {
            "role": role
        }
        
        if email:
            payload["email"] = email
        
        # Extract first_name and last_name from attributes if provided
        if attributes:
            if "first_name" in attributes:
                payload["first_name"] = attributes["first_name"]
            if "last_name" in attributes:
                payload["last_name"] = attributes["last_name"]
            
            # Any other attributes go into custom_attributes
            custom_attrs = {k: v for k, v in attributes.items() 
                          if k not in ("first_name", "last_name")}
            if custom_attrs:
                payload["custom_attributes"] = custom_attrs
        
        try:
            response = self.client.post("/tools/seed_user", json=payload)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to seed user with role '{role}'. "
                f"Status: {e.response.status_code}, "
                f"Response: {e.response.text}"
            ) from e
    
    def build_payload(
        self,
        template: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Generate API request payload from template with realistic test data.
        
        Per Agent Action Plan Section 5.4.2.2: "Build Operation - Request Payload Generation"
        
        The MCP server maintains payload templates for common API operations and
        fills them with realistic, non-conflicting test data. This ensures API
        tests don't hardcode request bodies and can run in parallel.
        
        Args:
            template: Payload template name corresponding to an API operation:
                     - "create_user": User creation payload
                     - "update_profile": Profile update payload
                     - "create_order": Order creation payload
                     - "update_settings": Settings update payload
            parameters: Optional template parameter overrides:
                       {"role": "customer", "age": 30, "country": "US"}
                       These values override the template defaults
        
        Returns:
            dict: Generated payload with realistic data ready for API request
        
        Raises:
            httpx.HTTPError: If payload generation fails (e.g., invalid template,
                            missing required parameters)
        
        Example:
            >>> # Generate user creation payload with defaults
            >>> payload = client.build_payload("create_user")
            >>> print(payload)
            {
                "email": "user-9b2ef71@test.local",
                "name": "Test User",
                "role": "customer",
                "age": 25
            }
            
            >>> # Generate with parameter overrides
            >>> payload = client.build_payload(
            ...     "create_user",
            ...     {"role": "admin", "age": 35}
            ... )
            >>> print(payload)
            {
                "email": "admin-c4d1a92@test.local",
                "name": "Admin User",
                "role": "admin",
                "age": 35
            }
        """
        payload = {
            "template_name": template,
            "params": parameters or {}
        }
        
        try:
            response = self.client.post("/tools/build_payload", json=payload)
            response.raise_for_status()
            result = response.json()
            
            # MCP server returns {"payload": {...}}, extract the payload
            if isinstance(result, dict) and "payload" in result:
                return result["payload"]  # type: ignore[no-any-return]
            return result  # type: ignore[no-any-return]
            
        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to build payload from template '{template}'. "
                f"Status: {e.response.status_code}, "
                f"Response: {e.response.text}"
            ) from e
    
    def reset_env(self) -> dict[str, Any]:
        """
        Reset test environment to known-good state.
        
        Per Agent Action Plan Section 5.4.2.2: "Reset Operation - Environment State Management"
        
        This operation should be called before test suites to ensure a clean
        environment. The MCP server performs:
        1. Truncate test database tables
        2. Reset sequences and auto-increment counters
        3. Seed default/required data (system admin, configurations)
        4. Clear caches and temporary storage
        
        Per user directive: "Keep tests deterministic, isolated, and parallel-friendly"
        
        Returns:
            dict: Environment reset status:
                {
                    "status": "reset_complete",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "operations": ["truncate_tables", "reset_sequences", "seed_defaults"]
                }
        
        Raises:
            httpx.HTTPError: If environment reset fails (e.g., database connection
                            error, permission issues)
        
        Warning:
            This operation is DESTRUCTIVE and will delete all test data.
            Only use in test environments, never in production.
        
        Example:
            >>> # Reset before test suite
            >>> status = client.reset_env()
            >>> print(f"Environment reset at {status['timestamp']}")
            
            >>> # Use in pytest fixture
            >>> @pytest.fixture(scope="session", autouse=True)
            ... def reset_environment(mcp_client):
            ...     mcp_client.reset_env()
        """
        try:
            response = self.client.post("/tools/reset_env")
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to reset test environment. "
                f"Status: {e.response.status_code}, "
                f"Response: {e.response.text}. "
                f"Ensure MCP server has database permissions."
            ) from e
    
    def query_state(
        self,
        entity_type: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Query current test environment state for verification.
        
        This method allows tests to inspect the current state of test data
        without direct database access. Useful for assertions and debugging.
        
        Args:
            entity_type: Type of entity to query:
                        - "users": Query user accounts
                        - "products": Query product catalog
                        - "orders": Query order records
                        - "sessions": Query active sessions
            filters: Optional query filters:
                    {"role": "admin", "status": "active"}
                    All filters must match (AND logic)
        
        Returns:
            dict: Query results:
                {
                    "entities": [
                        {"id": 1, "email": "admin@test.local", "role": "admin"},
                        {"id": 2, "email": "user@test.local", "role": "customer"}
                    ],
                    "count": 2,
                    "entity_type": "users",
                    "filters": {"role": "admin"}
                }
        
        Raises:
            httpx.HTTPError: If query fails (e.g., invalid entity_type,
                            unsupported filter)
        
        Example:
            >>> # Query all admin users
            >>> result = client.query_state("users", {"role": "admin"})
            >>> assert result['count'] >= 1, "At least one admin should exist"
            
            >>> # Query active orders for a user
            >>> orders = client.query_state(
            ...     "orders",
            ...     {"user_id": 123, "status": "active"}
            ... )
            >>> print(f"Found {orders['count']} active orders")
        """
        payload = {
            "entity_type": entity_type,
            "filters": filters or {}
        }
        
        try:
            response = self.client.post("/tools/query_state", json=payload)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            raise httpx.HTTPError(
                f"Failed to query state for entity_type '{entity_type}'. "
                f"Status: {e.response.status_code}, "
                f"Response: {e.response.text}"
            ) from e
    
    def close(self) -> None:
        """
        Close underlying HTTP client connection.
        
        This method releases connection pool resources. Always call this when
        done with the client, or use the context manager pattern.
        
        Example:
            >>> client = MCPClient("http://localhost:8000", "token")
            >>> try:
            ...     client.seed_user(role="admin")
            ... finally:
            ...     client.close()
            
            >>> # Better: use context manager
            >>> with MCPClient("http://localhost:8000", "token") as client:
            ...     client.seed_user(role="admin")
        """
        self.client.close()
    
    def __enter__(self) -> "MCPClient":
        """
        Context manager entry point.
        
        Returns:
            MCPClient: This client instance
        
        Example:
            >>> with MCPClient("http://localhost:8000", "token") as client:
            ...     user = client.seed_user(role="admin")
            ...     # client.close() called automatically
        """
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Context manager exit point - ensures connection cleanup.
        
        Args:
            exc_type: Exception type if raised in context
            exc_val: Exception value if raised in context
            exc_tb: Exception traceback if raised in context
        
        Returns:
            None: Does not suppress exceptions
        """
        self.close()
        # Return None to propagate any exceptions
        return None


def get_mcp_client() -> MCPClient:
    """
    Factory function to create MCP client from environment variables.
    
    This is the recommended way to instantiate MCPClient in tests, as it
    automatically reads configuration from the environment per user directive:
    "Base URLs via env: BASE_URL, API_BASE_URL, HEADLESS=true"
    
    Environment Variables:
        FASTAPI_MCP_URL: MCP server base URL
                        Default: "http://localhost:8000"
                        CI: Set to service URL (e.g., "http://fastapi-mcp:8000")
        FASTAPI_MCP_TOKEN: Authentication token (REQUIRED)
                          Generated by MCP server on startup
                          Store in .env file or CI secrets
    
    Returns:
        MCPClient: Configured and validated MCP client instance
    
    Raises:
        ValueError: If FASTAPI_MCP_TOKEN environment variable is not set
        httpx.HTTPError: If MCP server is unavailable at the configured URL
        httpx.ConnectError: If unable to connect to MCP server
    
    Example:
        >>> # In tests/conftest.py
        >>> @pytest.fixture(scope="session")
        ... def mcp_client():
        ...     client = get_mcp_client()
        ...     yield client
        ...     client.close()
        
        >>> # In test files
        >>> def test_user_creation(mcp_client):
        ...     user = mcp_client.seed_user(role="customer")
        ...     assert user['role'] == "customer"
    
    Note:
        Per Agent Action Plan Section 0.4.7: "CI/CD Integration Points",
        in CI the MCP server runs as a service and tests wait for the
        health check to succeed before execution.
    """
    # Read configuration from environment
    mcp_url = os.getenv("FASTAPI_MCP_URL", "http://localhost:8000")
    mcp_token = os.getenv("FASTAPI_MCP_TOKEN")
    
    # Validate required configuration
    if not mcp_token:
        raise ValueError(
            "FASTAPI_MCP_TOKEN environment variable is required. "
            "This token is generated by the FastAPI MCP server on startup. "
            "Set it in your .env file or export it:\n"
            "  export FASTAPI_MCP_TOKEN=your_token_here\n"
            "For CI, add it to your repository secrets."
        )
    
    # Create client instance
    try:
        client = MCPClient(mcp_url, mcp_token)
    except ValueError as e:
        raise ValueError(
            f"Failed to create MCP client: {e}. "
            f"Check FASTAPI_MCP_URL (currently: {mcp_url})"
        ) from e
    
    # Verify server availability with informative error messages
    try:
        health_status = client.health_check()
        # Log successful connection (useful for debugging CI issues)
        print(f"✓ MCP server connected successfully at {mcp_url}")
        print(f"  Status: {health_status.get('status', 'unknown')}")
        if 'version' in health_status:
            print(f"  Version: {health_status['version']}")
    except httpx.ConnectError as e:
        client.close()
        raise httpx.ConnectError(
            f"Cannot connect to MCP server at {mcp_url}.\n"
            f"Troubleshooting steps:\n"
            f"1. Ensure FastAPI MCP server is running:\n"
            f"   python -m mcp_servers.fastapi_mcp.main\n"
            f"2. Check FASTAPI_MCP_URL environment variable\n"
            f"3. Verify network connectivity and firewall rules\n"
            f"4. In CI, ensure MCP service is started before tests\n"
            f"Original error: {e}"
        ) from e
    except httpx.TimeoutException as e:
        client.close()
        raise httpx.TimeoutException(
            f"MCP server at {mcp_url} timed out after 30 seconds.\n"
            f"The server may be overloaded or experiencing issues.\n"
            f"Check server logs for errors.\n"
            f"Original error: {e}"
        ) from e
    except httpx.HTTPStatusError as e:
        client.close()
        raise httpx.HTTPError(
            f"MCP server at {mcp_url} returned error status.\n"
            f"Status: {e.response.status_code}\n"
            f"Response: {e.response.text}\n"
            f"Check server logs and ensure FASTAPI_MCP_TOKEN is valid."
        ) from e
    
    return client
