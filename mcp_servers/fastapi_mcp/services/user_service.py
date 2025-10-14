"""
User Service for FastAPI MCP Server

This module implements test user seeding, password generation, and user creation
in the application under test. It provides deterministic user creation via the
seed_user MCP tool, generates secure random passwords, and creates test users
through application API operations.

The UserService abstracts application-specific user management details from
FastAPI MCP routes, enabling repeatable test scenarios with known-good user
credentials. It supports role-based user creation, realistic test data generation,
and user lifecycle management for test cleanup.

Key Features:
- Secure password generation using cryptographic random sources
- Realistic test user attribute generation via Faker library
- Async user creation through application API endpoints
- Admin authentication for privileged operations
- User tracking for cleanup coordination
- Comprehensive error handling and logging

Usage:
    from mcp_servers.fastapi_mcp.services.user_service import UserService
    from mcp_servers.fastapi_mcp.models import UserRole
    
    user_service = UserService()
    
    # Create a test admin user
    user = await user_service.create_test_user(
        role=UserRole.ADMIN,
        email="test.admin@example.com"
    )
    
    print(f"Created user {user.user_id} with password {user.password}")
"""

import asyncio
import json
import logging
import secrets
import string
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
from faker import Faker

from mcp_servers.fastapi_mcp.config import settings
from mcp_servers.fastapi_mcp.models import SeedUserResponse, UserRole


# Configure module logger for user service operations
logger = logging.getLogger(__name__)


class UserService:
    """
    Service for managing test user creation and lifecycle.
    
    This class provides methods for creating test users in the application
    under test via API calls, generating secure credentials, and tracking
    user state for cleanup operations. It integrates with the application's
    authentication system and supports role-based access control.
    
    The service uses httpx AsyncClient for non-blocking API communication,
    enabling concurrent test user creation during parallel test execution.
    Admin credentials from settings are used to authenticate privileged
    user creation operations.
    
    Attributes:
        _faker: Faker instance for generating realistic test data
        _created_users: Internal tracking of created user IDs for cleanup
        _admin_token: Cached admin authentication token
    
    Example:
        ```python
        service = UserService()
        
        # Create multiple test users concurrently
        users = await asyncio.gather(
            service.create_test_user(role=UserRole.ADMIN),
            service.create_test_user(role=UserRole.EDITOR),
            service.create_test_user(role=UserRole.VIEWER)
        )
        
        # List all created users
        test_users = await service.list_test_users()
        
        # Cleanup
        for user_id in [u.user_id for u in users]:
            await service.delete_user(user_id)
        ```
    """
    
    def __init__(self) -> None:
        """
        Initialize the UserService with Faker for test data generation.
        
        Sets up the Faker instance with optional seeding for reproducible
        test data generation. Initializes internal state for tracking
        created users and caching authentication tokens.
        """
        # Initialize Faker with fixed seed for deterministic test data
        # Remove seed parameter for truly random data in production
        self._faker = Faker()
        
        # Track created test users for cleanup coordination
        # Maps user_id to creation timestamp for audit trail
        self._created_users: Dict[str, datetime] = {}
        
        # Cache admin authentication token to avoid repeated login
        self._admin_token: Optional[str] = None
        
        logger.info("UserService initialized successfully")
    
    def generate_password(self, length: int = 16) -> str:
        """
        Generate a secure random password for test authentication.
        
        Creates a cryptographically strong password containing uppercase,
        lowercase, digits, and special characters to meet typical application
        security requirements. Uses the secrets module for secure random
        number generation suitable for security-sensitive applications.
        
        Args:
            length: Desired password length (default: 16 characters)
        
        Returns:
            Secure random password string meeting complexity requirements
        
        Raises:
            ValueError: If length is less than 8 characters
        
        Example:
            >>> service = UserService()
            >>> password = service.generate_password()
            >>> len(password)
            16
            >>> # Password contains mixed case, digits, and special chars
        """
        if length < 8:
            raise ValueError("Password length must be at least 8 characters for security")
        
        # Define character pools for password complexity requirements
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?"
        
        # Ensure password contains at least one character from each pool
        password_chars = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special_chars)
        ]
        
        # Fill remaining length with random characters from all pools
        all_chars = lowercase + uppercase + digits + special_chars
        password_chars.extend(
            secrets.choice(all_chars) for _ in range(length - 4)
        )
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password_chars)
        
        password = ''.join(password_chars)
        logger.debug(f"Generated secure password of length {length}")
        
        return password
    
    def generate_first_name(self) -> str:
        """
        Generate a realistic first name for test user profiles.
        
        Uses the Faker library to generate culturally appropriate first names
        suitable for test scenarios. Names are randomly selected from Faker's
        extensive database of real-world names.
        
        Returns:
            Randomly generated first name string
        
        Example:
            >>> service = UserService()
            >>> first_name = service.generate_first_name()
            >>> isinstance(first_name, str)
            True
        """
        first_name = self._faker.first_name()
        logger.debug(f"Generated first name: {first_name}")
        return first_name
    
    def generate_last_name(self) -> str:
        """
        Generate a realistic last name for test user profiles.
        
        Uses the Faker library to generate culturally appropriate last names
        suitable for test scenarios. Names are randomly selected from Faker's
        extensive database of real-world surnames.
        
        Returns:
            Randomly generated last name string
        
        Example:
            >>> service = UserService()
            >>> last_name = service.generate_last_name()
            >>> isinstance(last_name, str)
            True
        """
        last_name = self._faker.last_name()
        logger.debug(f"Generated last name: {last_name}")
        return last_name
    
    async def _get_admin_token(self, client: httpx.AsyncClient) -> str:
        """
        Authenticate as admin and retrieve authentication token.
        
        Uses admin credentials from settings to authenticate with the
        application under test. Caches the token to avoid repeated
        authentication requests. Falls back to re-authentication if
        cached token is invalid.
        
        Args:
            client: httpx AsyncClient for API communication
        
        Returns:
            JWT authentication token for admin operations
        
        Raises:
            RuntimeError: If admin credentials are not configured
            httpx.HTTPError: If authentication request fails
        """
        # Check if admin credentials are configured
        if not settings.is_admin_configured():
            raise RuntimeError(
                "Admin credentials not configured. Set APP_ADMIN_EMAIL and "
                "APP_ADMIN_PASSWORD environment variables for user creation operations."
            )
        
        # Return cached token if available
        if self._admin_token:
            return self._admin_token
        
        # Authenticate with admin credentials
        login_url = f"{settings.app_api_url}/auth/login"
        login_payload = {
            "email": settings.app_admin_email,
            "password": settings.app_admin_password
        }
        
        try:
            response = await client.post(
                login_url,
                json=login_payload,
                timeout=10.0
            )
            response.raise_for_status()
            
            # Parse token from response
            auth_data = response.json()
            token: Optional[str] = auth_data.get("access_token") or auth_data.get("token")
            
            if not token:
                raise RuntimeError(
                    f"Authentication response missing token. Response: {auth_data}"
                )
            
            # Cache token for reuse
            self._admin_token = token
            logger.info("Successfully authenticated as admin")
            
            return token
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Admin authentication failed with status {e.response.status_code}: "
                f"{e.response.text}"
            )
            raise RuntimeError(f"Admin authentication failed: {e.response.text}")
        except httpx.RequestError as e:
            logger.error(f"Admin authentication request error: {str(e)}")
            raise RuntimeError(f"Failed to connect to application API: {str(e)}")
    
    async def create_test_user(
        self,
        role: UserRole,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        custom_attributes: Optional[Dict[str, Any]] = None
    ) -> SeedUserResponse:
        """
        Create a test user in the application under test.
        
        This is the primary method for the seed_user MCP tool. It creates a
        new user account in the target application with specified role and
        profile attributes. If optional fields are not provided, realistic
        values are auto-generated using Faker.
        
        The method performs the following steps:
        1. Generate missing profile attributes (email, names)
        2. Generate secure password
        3. Authenticate as admin
        4. Call application API to create user
        5. Track created user for cleanup
        6. Return complete user details with credentials
        
        Args:
            role: User authorization role (ADMIN, EDITOR, or VIEWER)
            email: Optional email address (auto-generated if not provided)
            first_name: Optional first name (auto-generated if not provided)
            last_name: Optional last name (auto-generated if not provided)
            custom_attributes: Optional dict of additional user attributes
        
        Returns:
            SeedUserResponse with user_id, credentials, and profile info
        
        Raises:
            RuntimeError: If user creation fails or admin auth unavailable
            httpx.HTTPError: If API communication fails
        
        Example:
            >>> service = UserService()
            >>> user = await service.create_test_user(
            ...     role=UserRole.ADMIN,
            ...     email="test@example.com"
            ... )
            >>> print(f"User {user.user_id} created with password {user.password}")
        """
        # Generate missing attributes with realistic test data
        if not email:
            # Generate unique email with timestamp to avoid collisions
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            username = self._faker.user_name()
            email = f"test.{username}.{timestamp}@example.com"
        
        if not first_name:
            first_name = self.generate_first_name()
        
        if not last_name:
            last_name = self.generate_last_name()
        
        # Generate secure password for test authentication
        password = self.generate_password()
        
        logger.info(
            f"Creating test user: email={email}, role={role.value}, "
            f"first_name={first_name}, last_name={last_name}"
        )
        
        # Create httpx client with timeout and retry configuration
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True
        ) as client:
            # Authenticate as admin to create user
            admin_token = await self._get_admin_token(client)
            
            # Prepare user creation payload
            # Note: Sample app expects "name" field (single field), not first_name/last_name
            full_name = f"{first_name} {last_name}" if first_name and last_name else (first_name or last_name or "Test User")
            
            # Map MCP roles to sample app roles
            # MCP: admin, editor, viewer -> Sample App: admin, moderator, customer
            role_mapping = {
                "admin": "admin",
                "editor": "moderator",
                "viewer": "customer"
            }
            app_role = role_mapping.get(role.value.lower(), "customer")
            
            user_payload = {
                "email": email,
                "password": password,
                "name": full_name,
                "role": app_role
            }
            
            # Merge custom attributes if provided
            if custom_attributes:
                user_payload.update(custom_attributes)
            
            # Call application API to create user
            create_url = f"{settings.app_api_url}/users"
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json"
            }
            
            try:
                response = await client.post(
                    create_url,
                    json=user_payload,
                    headers=headers,
                    timeout=15.0
                )
                response.raise_for_status()
                
                # Parse created user data
                # Sample app returns: {"data": {"id": "...", ...}, "status": "success"}
                response_json = response.json()
                user_data = response_json.get("data", response_json)  # Handle both nested and flat responses
                user_id = user_data.get("id") or user_data.get("user_id")
                
                if not user_id:
                    raise RuntimeError(
                        f"User creation response missing ID. Response: {response_json}"
                    )
                
                # Track created user for cleanup
                creation_time = datetime.utcnow()
                self._created_users[user_id] = creation_time
                
                logger.info(
                    f"Successfully created test user: user_id={user_id}, "
                    f"email={email}, role={app_role} (requested: {role.value})"
                )
                
                # Return SeedUserResponse with all user details
                # Note: Return app_role (mapped role) not the original MCP role
                return SeedUserResponse(
                    user_id=user_id,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=app_role,  # Return the actual role in the application
                    created_at=creation_time
                )
                
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text
                logger.error(
                    f"User creation failed with status {e.response.status_code}: "
                    f"{error_detail}"
                )
                
                # Provide specific error messages for common failures
                if e.response.status_code == 409:
                    raise RuntimeError(
                        f"User with email {email} already exists. "
                        "Use a different email or delete the existing user first."
                    )
                elif e.response.status_code == 401:
                    # Clear cached token and retry once
                    self._admin_token = None
                    logger.warning("Admin token expired, retrying authentication")
                    raise RuntimeError(
                        "Admin authentication expired. Operation will be retried."
                    )
                elif e.response.status_code == 403:
                    raise RuntimeError(
                        "Admin user lacks permissions to create users. "
                        "Verify admin role configuration."
                    )
                else:
                    raise RuntimeError(
                        f"User creation failed: {error_detail}"
                    )
                    
            except httpx.RequestError as e:
                logger.error(f"User creation request error: {str(e)}")
                raise RuntimeError(
                    f"Failed to communicate with application API: {str(e)}"
                )
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a test user from the application under test.
        
        Removes a user account from the target application via API call.
        This method is used for test cleanup operations to reset the
        environment to a known state between test runs.
        
        The user is removed from internal tracking after successful deletion.
        If the user doesn't exist in the application, the operation is
        considered successful (idempotent deletion).
        
        Args:
            user_id: Unique identifier of the user to delete
        
        Returns:
            True if user was successfully deleted, False otherwise
        
        Raises:
            RuntimeError: If admin authentication fails
            httpx.HTTPError: If API communication fails
        
        Example:
            >>> service = UserService()
            >>> user = await service.create_test_user(role=UserRole.VIEWER)
            >>> success = await service.delete_user(user.user_id)
            >>> assert success
        """
        logger.info(f"Deleting test user: user_id={user_id}")
        
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True
        ) as client:
            try:
                # Authenticate as admin to delete user
                admin_token = await self._get_admin_token(client)
                
                # Call application API to delete user
                delete_url = f"{settings.app_api_url}/users/{user_id}"
                headers = {
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
                
                response = await client.delete(
                    delete_url,
                    headers=headers,
                    timeout=15.0
                )
                
                # 204 No Content or 200 OK indicate success
                # 404 Not Found is acceptable (idempotent deletion)
                if response.status_code in (200, 204, 404):
                    # Remove from internal tracking
                    if user_id in self._created_users:
                        del self._created_users[user_id]
                    
                    logger.info(f"Successfully deleted test user: user_id={user_id}")
                    return True
                
                # Log unexpected status codes but don't raise
                logger.warning(
                    f"Unexpected status code {response.status_code} when deleting "
                    f"user {user_id}: {response.text}"
                )
                return False
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"User deletion failed with status {e.response.status_code}: "
                    f"{e.response.text}"
                )
                
                # 404 is acceptable for idempotent deletion
                if e.response.status_code == 404:
                    if user_id in self._created_users:
                        del self._created_users[user_id]
                    return True
                
                # Clear token cache on auth errors
                if e.response.status_code == 401:
                    self._admin_token = None
                
                raise RuntimeError(
                    f"Failed to delete user {user_id}: {e.response.text}"
                )
                
            except httpx.RequestError as e:
                logger.error(f"User deletion request error: {str(e)}")
                raise RuntimeError(
                    f"Failed to communicate with application API: {str(e)}"
                )
    
    async def list_test_users(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List all test users currently in the application under test.
        
        Queries the application API to retrieve all user accounts, optionally
        filtered by criteria such as role, email domain, or creation date.
        This method is useful for test state inspection, debugging test
        failures, and cleanup verification.
        
        Returns both tracked users (created by this service) and any other
        users present in the system. The response includes user IDs, emails,
        roles, and profile information.
        
        Args:
            filters: Optional dictionary of filter criteria
                    Examples: {"role": "admin"}, {"email_domain": "example.com"}
        
        Returns:
            List of user dictionaries with id, email, role, and profile data
        
        Raises:
            RuntimeError: If admin authentication fails or query fails
            httpx.HTTPError: If API communication fails
        
        Example:
            >>> service = UserService()
            >>> # Create some test users
            >>> await service.create_test_user(role=UserRole.ADMIN)
            >>> await service.create_test_user(role=UserRole.EDITOR)
            >>> 
            >>> # List all users
            >>> users = await service.list_test_users()
            >>> print(f"Total users: {len(users)}")
            >>> 
            >>> # List admin users only
            >>> admins = await service.list_test_users(filters={"role": "admin"})
            >>> print(f"Admin users: {len(admins)}")
        """
        logger.info(f"Listing test users with filters: {filters}")
        
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True
        ) as client:
            try:
                # Authenticate as admin to query users
                admin_token = await self._get_admin_token(client)
                
                # Build query URL with optional filters
                list_url = f"{settings.app_api_url}/users"
                headers = {
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json"
                }
                
                # Add filter parameters to query string
                params = {}
                if filters:
                    # Convert filters to query parameters
                    for key, value in filters.items():
                        if isinstance(value, (list, tuple)):
                            params[key] = ",".join(str(v) for v in value)
                        else:
                            params[key] = str(value)
                
                response = await client.get(
                    list_url,
                    headers=headers,
                    params=params,
                    timeout=15.0
                )
                response.raise_for_status()
                
                # Parse user list from response
                data = response.json()
                
                # Handle different response formats
                # API may return {"users": [...]} or just [...]
                if isinstance(data, dict):
                    users = data.get("users", data.get("data", []))
                elif isinstance(data, list):
                    users = data
                else:
                    logger.warning(f"Unexpected response format: {type(data)}")
                    users = []
                
                logger.info(f"Retrieved {len(users)} test users")
                
                # Normalize user data structure
                normalized_users = []
                for user in users:
                    normalized_user = {
                        "user_id": user.get("id") or user.get("user_id"),
                        "email": user.get("email"),
                        "role": user.get("role"),
                        "first_name": user.get("first_name"),
                        "last_name": user.get("last_name"),
                        "created_at": user.get("created_at"),
                        "is_tracked": user.get("id", user.get("user_id")) in self._created_users
                    }
                    normalized_users.append(normalized_user)
                
                return normalized_users
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"User list query failed with status {e.response.status_code}: "
                    f"{e.response.text}"
                )
                
                # Clear token cache on auth errors
                if e.response.status_code == 401:
                    self._admin_token = None
                
                raise RuntimeError(
                    f"Failed to query user list: {e.response.text}"
                )
                
            except httpx.RequestError as e:
                logger.error(f"User list request error: {str(e)}")
                raise RuntimeError(
                    f"Failed to communicate with application API: {str(e)}"
                )
    
    def get_tracked_users(self) -> Dict[str, datetime]:
        """
        Get dictionary of users created by this service instance.
        
        Returns a mapping of user IDs to their creation timestamps for
        audit trail and selective cleanup operations. Only includes users
        created through this service's create_test_user method.
        
        Returns:
            Dictionary mapping user_id to creation datetime
        
        Example:
            >>> service = UserService()
            >>> await service.create_test_user(role=UserRole.ADMIN)
            >>> tracked = service.get_tracked_users()
            >>> print(f"Tracked {len(tracked)} users")
        """
        return self._created_users.copy()
    
    async def delete_all_tracked_users(self) -> Tuple[int, int]:
        """
        Delete all users created by this service instance.
        
        Performs cleanup of all tracked test users in parallel for efficiency.
        This method is useful for test teardown and environment reset
        operations. Uses asyncio.gather to delete users concurrently.
        
        Returns:
            Tuple of (successful_deletions, failed_deletions) counts
        
        Example:
            >>> service = UserService()
            >>> # Create multiple test users
            >>> await service.create_test_user(role=UserRole.ADMIN)
            >>> await service.create_test_user(role=UserRole.EDITOR)
            >>> 
            >>> # Clean up all at once
            >>> success, failed = await service.delete_all_tracked_users()
            >>> print(f"Deleted {success} users, {failed} failures")
        """
        user_ids = list(self._created_users.keys())
        
        if not user_ids:
            logger.info("No tracked users to delete")
            return (0, 0)
        
        logger.info(f"Deleting {len(user_ids)} tracked test users")
        
        # Delete all users concurrently for efficiency
        results = await asyncio.gather(
            *[self.delete_user(user_id) for user_id in user_ids],
            return_exceptions=True
        )
        
        # Count successes and failures
        successful = sum(1 for r in results if r is True)
        failed = len(results) - successful
        
        logger.info(
            f"Batch deletion complete: {successful} successful, {failed} failed"
        )
        
        return (successful, failed)
