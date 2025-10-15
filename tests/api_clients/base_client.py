"""
Base API Client Module

Provides foundation classes for all API clients with comprehensive HTTP functionality:
- BaseAPIClient: Synchronous HTTP client with httpx
- AsyncBaseAPIClient: Asynchronous HTTP client for concurrent testing

Features:
- Automatic Pydantic request/response validation
- Retry logic with exponential backoff for transient failures
- Allure test report integration with request/response attachments
- Configurable timeouts and connection limits
- Bearer token authentication support
- Context manager protocol for resource cleanup
- Event hooks for request/response logging

Usage:
    # Synchronous client
    with BaseAPIClient(base_url="https://api.example.com", auth_token="token") as client:
        response = client.get("/users/123", response_model=UserResponse)
    
    # Asynchronous client for concurrent operations
    async with AsyncBaseAPIClient(base_url="https://api.example.com") as client:
        response = await client.get("/users/123", response_model=UserResponse)
"""

import httpx
from pydantic import BaseModel, ValidationError
from typing import Optional, Type, TypeVar, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import allure
import json
import os

# Type variable for generic Pydantic model returns
T = TypeVar('T', bound=BaseModel)


class BaseAPIClient:
    """
    Base HTTP client with Pydantic validation and Allure integration.
    
    Provides typed HTTP methods (GET, POST, PUT, PATCH, DELETE) with automatic:
    - Request/response validation using Pydantic models
    - Retry logic for transient network failures
    - Allure report attachments for debugging
    - Bearer token authentication
    - Connection pooling and timeout management
    
    This class serves as the foundation for all API clients (AuthAPIClient, UsersAPIClient)
    ensuring consistent error handling, logging, and retry behavior across all endpoints.
    
    Attributes:
        base_url (str): API base URL from API_BASE_URL env var or constructor
        timeout (float): Request timeout in seconds (default: 30.0)
        max_retries (int): Maximum retry attempts for transient failures (default: 3)
        client (httpx.Client): Underlying HTTP client instance
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize API client with base configuration.
        
        Args:
            base_url: API base URL (defaults to API_BASE_URL env var or http://localhost:3000/api)
            auth_token: Bearer token for authentication (optional)
            timeout: Request timeout in seconds (default: 30.0)
            max_retries: Maximum retry attempts for transient failures (default: 3)
        
        Example:
            # With environment variable API_BASE_URL
            client = BaseAPIClient(auth_token="jwt_token_here")
            
            # With explicit base URL
            client = BaseAPIClient(
                base_url="https://api.example.com",
                auth_token="jwt_token_here",
                timeout=60.0
            )
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:3000/api")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Default headers for JSON API communication
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add Bearer token if provided
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Initialize httpx client with connection pooling and event hooks
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers=headers,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            ),
            event_hooks={
                "request": [self._log_request],
                "response": [self._log_response]
            }
        )
    
    def _log_request(self, request: httpx.Request):
        """
        Log HTTP request to Allure report.
        
        Captures request method, URL, headers, and body for debugging.
        Automatically called via httpx event hooks before each request.
        
        Args:
            request: httpx Request object from event hook
        """
        request_details = {
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": request.content.decode('utf-8', errors='replace') if request.content else None
        }
        allure.attach(
            json.dumps(request_details, indent=2),
            name=f"Request: {request.method} {request.url.path}",
            attachment_type=allure.attachment_type.JSON
        )
    
    def _log_response(self, response: httpx.Response):
        """
        Log HTTP response to Allure report.
        
        Captures status code, headers, body (truncated), and elapsed time.
        Automatically called via httpx event hooks after each response.
        
        Args:
            response: httpx Response object from event hook
        """
        # Safely get elapsed time (may not be available in all contexts)
        try:
            elapsed_ms = response.elapsed.total_seconds() * 1000
        except (AttributeError, RuntimeError):
            elapsed_ms = None
        
        # Read response body safely (handles streaming responses)
        try:
            # Ensure response content is read before accessing text
            if not response.is_closed:
                response.read()
            body_text = response.text[:1000] if response.text else None
        except (httpx.ResponseNotRead, RuntimeError, AttributeError):
            # If we can't read the response (e.g., already consumed), use empty body
            body_text = "<response body not available>"
        
        response_details = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": body_text,  # Truncate large responses
            "elapsed_ms": elapsed_ms
        }
        allure.attach(
            json.dumps(response_details, indent=2),
            name=f"Response: {response.status_code}",
            attachment_type=allure.attachment_type.JSON
        )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.TransportError)
    )
    def get(
        self,
        endpoint: str,
        response_model: Type[T],
        params: Optional[Dict[str, Any]] = None
    ) -> T:
        """
        Execute GET request with response validation.
        
        Automatically retries on transient network failures (httpx.TransportError)
        with exponential backoff (2s, 4s, 8s).
        
        Args:
            endpoint: API endpoint path (e.g., "/users/123")
            response_model: Pydantic model class for response validation
            params: Optional query parameters
            
        Returns:
            Validated Pydantic response model instance
            
        Raises:
            httpx.HTTPError: For HTTP errors (404, 500, etc.)
            ValidationError: For response validation failures
            httpx.TransportError: For network failures after retries exhausted
        
        Example:
            user = client.get("/users/123", response_model=UserResponse)
            users = client.get("/users", response_model=UserListResponse, params={"role": "admin"})
        """
        response = self.client.get(endpoint, params=params)
        response.raise_for_status()
        
        # Handle API responses that wrap data in {"data": ..., "status": "success"} format
        response_json = response.json()
        if isinstance(response_json, dict) and "data" in response_json and "status" in response_json:
            # Unwrap the data field for endpoints that use this format
            response_json = response_json["data"]
        
        return response_model(**response_json)
    
    def post(
        self,
        endpoint: str,
        request_model: Optional[BaseModel] = None,
        response_model: Optional[Type[T]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Optional[T]:
        """
        Execute POST request with request/response validation.
        
        Supports both Pydantic model payloads and raw JSON dictionaries.
        Can be used for creation operations or RPC-style endpoints.
        
        Args:
            endpoint: API endpoint path
            request_model: Optional Pydantic model for request body (preferred)
            response_model: Optional Pydantic model for response validation
            json: Optional raw JSON dict (if not using request_model)
            
        Returns:
            Validated Pydantic response model, raw JSON dict, or None (for 204 responses)
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValidationError: For request or response validation failures
        
        Example:
            # With Pydantic models
            user = client.post(
                "/users",
                request_model=CreateUserRequest(email="test@example.com"),
                response_model=UserResponse
            )
            
            # With raw JSON (e.g., for MCP-generated payloads)
            user = client.post(
                "/users",
                json={"email": "test@example.com", "role": "admin"},
                response_model=UserResponse
            )
        """
        payload = request_model.model_dump(exclude_none=True) if request_model else json
        response = self.client.post(endpoint, json=payload)
        response.raise_for_status()
        
        # Handle different response scenarios
        if response_model and response.text:
            # Handle API responses that wrap data in {"data": ..., "status": "success"} format
            response_json = response.json()
            if isinstance(response_json, dict) and "data" in response_json and "status" in response_json:
                # Unwrap the data field for endpoints that use this format
                response_json = response_json["data"]
            return response_model(**response_json)
        elif response.text:
            return response.json()
        else:
            return None  # 204 No Content
    
    def put(
        self,
        endpoint: str,
        request_model: BaseModel,
        response_model: Type[T]
    ) -> T:
        """
        Execute PUT request with request/response validation.
        
        Used for full resource updates (replacing entire resource).
        
        Args:
            endpoint: API endpoint path
            request_model: Pydantic model for request body
            response_model: Pydantic model for response validation
            
        Returns:
            Validated Pydantic response model instance
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValidationError: For validation failures
        
        Example:
            updated_user = client.put(
                "/users/123",
                request_model=UpdateUserRequest(email="new@example.com", role="editor"),
                response_model=UserResponse
            )
        """
        payload = request_model.model_dump(exclude_none=True)
        response = self.client.put(endpoint, json=payload)
        response.raise_for_status()
        
        # Handle API responses that wrap data in {"data": ..., "status": "success"} format
        response_json = response.json()
        if isinstance(response_json, dict) and "data" in response_json and "status" in response_json:
            # Unwrap the data field for endpoints that use this format
            response_json = response_json["data"]
        
        return response_model(**response_json)
    
    def patch(
        self,
        endpoint: str,
        request_model: BaseModel,
        response_model: Type[T]
    ) -> T:
        """
        Execute PATCH request for partial updates.
        
        Used for partial resource updates (modifying specific fields).
        
        Args:
            endpoint: API endpoint path
            request_model: Pydantic model for request body (only changed fields)
            response_model: Pydantic model for response validation
            
        Returns:
            Validated Pydantic response model instance
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValidationError: For validation failures
        
        Example:
            # Only update email, leave other fields unchanged
            updated_user = client.patch(
                "/users/123",
                request_model=UpdateUserRequest(email="new@example.com"),
                response_model=UserResponse
            )
        """
        payload = request_model.model_dump(exclude_none=True)
        response = self.client.patch(endpoint, json=payload)
        response.raise_for_status()
        
        # Handle API responses that wrap data in {"data": ..., "status": "success"} format
        response_json = response.json()
        if isinstance(response_json, dict) and "data" in response_json and "status" in response_json:
            # Unwrap the data field for endpoints that use this format
            response_json = response_json["data"]
        
        return response_model(**response_json)
    
    def delete(self, endpoint: str) -> None:
        """
        Execute DELETE request.
        
        Args:
            endpoint: API endpoint path
            
        Raises:
            httpx.HTTPError: For HTTP errors (404 if resource not found, 403 if forbidden)
        
        Example:
            client.delete("/users/123")
        """
        response = self.client.delete(endpoint)
        response.raise_for_status()
    
    def set_auth_token(self, token: str) -> None:
        """
        Update authentication token for subsequent requests.
        
        Useful for tests that need to switch between different user contexts
        or refresh expired tokens.
        
        Args:
            token: New Bearer token string
        
        Example:
            # Login and get new token
            login_response = auth_client.login("user@example.com", "password")
            client.set_auth_token(login_response.access_token)
        """
        self.client.headers["Authorization"] = f"Bearer {token}"
    
    def close(self) -> None:
        """
        Close HTTP client connection and release resources.
        
        Should be called when client is no longer needed to free connection pool.
        Automatically called when using context manager.
        
        Example:
            client = BaseAPIClient()
            try:
                # Use client
                pass
            finally:
                client.close()
        """
        self.client.close()
    
    def __enter__(self):
        """
        Context manager entry - returns self for use in 'with' statement.
        
        Example:
            with BaseAPIClient(auth_token="token") as client:
                response = client.get("/users", response_model=UserListResponse)
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit - ensures client is closed even if exception occurs.
        
        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred
        """
        self.close()


class AsyncBaseAPIClient:
    """
    Asynchronous HTTP client for concurrent API testing.
    
    Provides async/await support for parallel test execution using httpx.AsyncClient.
    Useful for load testing, concurrent user scenarios, or tests that make multiple
    API calls that can be parallelized.
    
    Attributes:
        base_url (str): API base URL from API_BASE_URL env var or constructor
        timeout (float): Request timeout in seconds (default: 30.0)
        client (httpx.AsyncClient): Underlying async HTTP client instance
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize async API client with base configuration.
        
        Args:
            base_url: API base URL (defaults to API_BASE_URL env var)
            auth_token: Bearer token for authentication (optional)
            timeout: Request timeout in seconds (default: 30.0)
        
        Example:
            client = AsyncBaseAPIClient(
                base_url="https://api.example.com",
                auth_token="jwt_token_here"
            )
        """
        self.base_url = base_url or os.getenv("API_BASE_URL", "http://localhost:3000/api")
        self.timeout = timeout
        
        # Default headers for JSON API communication
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add Bearer token if provided
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Initialize httpx async client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            headers=headers,
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            )
        )
    
    async def get(
        self,
        endpoint: str,
        response_model: Type[T],
        params: Optional[Dict[str, Any]] = None
    ) -> T:
        """
        Execute async GET request with response validation.
        
        Args:
            endpoint: API endpoint path
            response_model: Pydantic model class for response validation
            params: Optional query parameters
            
        Returns:
            Validated Pydantic response model instance
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValidationError: For response validation failures
        
        Example:
            user = await client.get("/users/123", response_model=UserResponse)
        """
        response = await self.client.get(endpoint, params=params)
        response.raise_for_status()
        return response_model(**response.json())
    
    async def post(
        self,
        endpoint: str,
        request_model: Optional[BaseModel] = None,
        response_model: Optional[Type[T]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Optional[T]:
        """
        Execute async POST request with request/response validation.
        
        Args:
            endpoint: API endpoint path
            request_model: Optional Pydantic model for request body
            response_model: Optional Pydantic model for response validation
            json: Optional raw JSON dict
            
        Returns:
            Validated Pydantic response model, raw JSON dict, or None
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValidationError: For validation failures
        
        Example:
            user = await client.post(
                "/users",
                request_model=CreateUserRequest(email="test@example.com"),
                response_model=UserResponse
            )
        """
        payload = request_model.model_dump(exclude_none=True) if request_model else json
        response = await self.client.post(endpoint, json=payload)
        response.raise_for_status()
        
        # Handle different response scenarios
        if response_model and response.text:
            return response_model(**response.json())
        elif response.text:
            return response.json()
        else:
            return None  # 204 No Content
    
    async def put(
        self,
        endpoint: str,
        request_model: BaseModel,
        response_model: Type[T]
    ) -> T:
        """
        Execute async PUT request with request/response validation.
        
        Args:
            endpoint: API endpoint path
            request_model: Pydantic model for request body
            response_model: Pydantic model for response validation
            
        Returns:
            Validated Pydantic response model instance
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValidationError: For validation failures
        """
        payload = request_model.model_dump(exclude_none=True)
        response = await self.client.put(endpoint, json=payload)
        response.raise_for_status()
        return response_model(**response.json())
    
    async def patch(
        self,
        endpoint: str,
        request_model: BaseModel,
        response_model: Type[T]
    ) -> T:
        """
        Execute async PATCH request for partial updates.
        
        Args:
            endpoint: API endpoint path
            request_model: Pydantic model for request body
            response_model: Pydantic model for response validation
            
        Returns:
            Validated Pydantic response model instance
            
        Raises:
            httpx.HTTPError: For HTTP errors
            ValidationError: For validation failures
        """
        payload = request_model.model_dump(exclude_none=True)
        response = await self.client.patch(endpoint, json=payload)
        response.raise_for_status()
        return response_model(**response.json())
    
    async def delete(self, endpoint: str) -> None:
        """
        Execute async DELETE request.
        
        Args:
            endpoint: API endpoint path
            
        Raises:
            httpx.HTTPError: For HTTP errors
        """
        response = await self.client.delete(endpoint)
        response.raise_for_status()
    
    def set_auth_token(self, token: str) -> None:
        """
        Update authentication token for subsequent requests.
        
        Args:
            token: New Bearer token string
        """
        self.client.headers["Authorization"] = f"Bearer {token}"
    
    async def close(self) -> None:
        """
        Close async HTTP client connection and release resources.
        
        Should be called when client is no longer needed.
        Automatically called when using async context manager.
        
        Example:
            client = AsyncBaseAPIClient()
            try:
                # Use client
                pass
            finally:
                await client.close()
        """
        await self.client.aclose()
    
    async def __aenter__(self):
        """
        Async context manager entry - returns self for use in 'async with' statement.
        
        Example:
            async with AsyncBaseAPIClient(auth_token="token") as client:
                response = await client.get("/users", response_model=UserListResponse)
        """
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit - ensures client is closed.
        
        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred
        """
        await self.close()
