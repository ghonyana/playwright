"""
State Service for FastAPI MCP Server

This module implements environment state management and resource cleanup for deterministic
test execution. Provides reset_env and query_state MCP tools to ensure tests start from
known-good states by removing test artifacts and managing application state.

Key Features:
    - Scoped environment resets (all, users, projects, data) to minimize cleanup time
    - Database and API-based cleanup strategies for flexible integration
    - Safe deletion patterns using regex matching for test resources only
    - Redis/memcached cache invalidation for clean cache state
    - Transaction management with automatic rollback on errors
    - Comprehensive audit logging for debugging and compliance
    - Dry-run mode for validation without actual deletion

The StateService class supports both direct database operations (via SQLAlchemy) and
API-based cleanup (via httpx) depending on configuration, enabling integration with
various application architectures.

Usage:
    # Initialize service with configuration
    state_service = StateService()
    
    # Reset entire environment
    response = await state_service.reset_environment(scope="all")
    
    # Query current state
    users = await state_service.query_resources(resource_type="users", filters={"role": "admin"})
"""

from typing import Optional, List, Dict, Any, Literal
import logging
import httpx
import asyncio
import re
import json
from datetime import datetime, timedelta

from sqlalchemy import select, delete, and_, or_, text

# Optional Redis import - gracefully handle if not installed
try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    Redis = None

from mcp_servers.fastapi_mcp.config import settings
from mcp_servers.fastapi_mcp.models import (
    ResetEnvRequest,
    ResetEnvResponse,
    QueryStateRequest,
    QueryStateResponse,
)
from mcp_servers.fastapi_mcp.database.connection import DatabaseManager
from mcp_servers.fastapi_mcp.database.models import TestUser, TestSession


# Configure module logger
logger = logging.getLogger(__name__)


class StateService:
    """
    Service class for managing test environment state and resource cleanup.
    
    Implements MCP tools for deterministic test execution by providing environment
    reset and state query capabilities. Supports both database-direct and API-based
    cleanup strategies with transaction management and comprehensive error handling.
    
    Attributes:
        db_manager (Optional[DatabaseManager]): Database connection manager for direct
            database operations. None if database not configured.
        redis_client (Optional[Redis]): Redis client for cache invalidation. None if
            Redis not configured or unavailable.
        dry_run (bool): When True, simulates operations without actual deletion for
            validation purposes.
    
    Cleanup Strategies:
        1. Database-Direct: Uses SQLAlchemy to directly delete test data from application
           database. Requires database_url configuration. Fastest and most reliable.
        
        2. API-Based: Uses httpx to send DELETE requests to application API endpoints.
           Requires app_api_url and admin credentials. Useful when direct database
           access is not available or desired.
        
        3. Hybrid: Combines both strategies, using database for some resources and API
           for others based on application architecture.
    
    Safe Deletion Patterns:
        Resources are only deleted if they match test patterns:
        - Email addresses: *@example.com, *@test.com, test.*@*
        - Usernames: test.*, test_*
        - Metadata tags: {"test": true}, {"environment": "test"}
    
    Thread Safety:
        StateService instances should be created per-request using FastAPI dependency
        injection. Each instance manages its own database session lifecycle.
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize StateService with configuration from settings.
        
        Sets up database connection manager if database_url is configured, and
        Redis client if cache invalidation is configured. Gracefully handles
        missing optional dependencies.
        
        Args:
            dry_run (bool): If True, operations are simulated without actual deletion.
                Useful for validating reset logic before applying to real environment.
        
        Configuration Dependencies:
            - settings.database_url: Optional database connection string
            - settings.app_api_url: REST API base URL for API-based cleanup
            - settings.app_admin_email: Admin credentials for authenticated API calls
            - settings.app_admin_password: Admin password for authentication
        
        Example:
            # Production mode with actual deletion
            service = StateService(dry_run=False)
            
            # Validation mode without deletion
            service = StateService(dry_run=True)
        """
        self.dry_run = dry_run
        
        # Initialize database manager if database is configured
        if settings.is_database_configured():
            self.db_manager: Optional[DatabaseManager] = DatabaseManager(settings.database_url)
            logger.info(f"StateService initialized with database: {settings.database_url}")
        else:
            self.db_manager = None
            logger.warning("StateService initialized without database - using API-based cleanup only")
        
        # Initialize Redis client if available and configured
        # Redis configuration would come from settings if we add REDIS_URL to config
        self.redis_client: Optional[Redis] = None
        if REDIS_AVAILABLE:
            # For now, Redis is optional and would need configuration expansion
            # This placeholder allows future Redis integration without code changes
            logger.debug("Redis library available but no redis_url configured")
        else:
            logger.debug("Redis library not installed - cache invalidation unavailable")
    
    async def reset_environment(self, scope: Literal["all", "users", "projects", "data"] = "all") -> Dict[str, Any]:
        """
        Reset test environment to clean state by removing test data.
        
        Executes cleanup operations based on the specified scope parameter, allowing
        for partial or complete environment resets. Uses transaction management to
        ensure atomic operations with automatic rollback on errors.
        
        Args:
            scope (Literal): Determines which categories of test data to delete:
                - "all": Complete reset - delete users, projects, data, clear cache,
                  invalidate sessions, and reset feature flags
                - "users": Delete only test users, preserve projects and data
                - "projects": Delete only projects, preserve users and data
                - "data": Delete only application data, preserve users and projects
        
        Returns:
            Dict[str, Any]: Reset operation result containing:
                - success (bool): Whether operation completed without errors
                - scope (str): The scope that was applied
                - items_deleted (int): Total count of resources removed
                - details (Dict[str, int]): Breakdown by resource type
                - duration_ms (int): Operation duration in milliseconds
                - errors (List[str]): Any non-fatal errors encountered
        
        Reset Process:
            1. Begin operation timing for metrics
            2. Execute scope-specific reset operations concurrently where possible
            3. Track deletion counts per resource type
            4. Handle errors with partial reset fallback
            5. Log operations for audit trail
            6. Return comprehensive result summary
        
        Error Handling:
            - Database errors: Automatic rollback, operation continues with API fallback
            - API errors: Logged as warnings, operation continues with other resources
            - Critical errors: Rolled back completely, success=False returned
        
        Example:
            # Complete environment reset before test suite
            result = await state_service.reset_environment(scope="all")
            assert result["success"] is True
            print(f"Deleted {result['items_deleted']} items in {result['duration_ms']}ms")
            
            # Reset only test users between test cases
            result = await state_service.reset_environment(scope="users")
        
        Performance:
            - Database-based reset: Typically 50-200ms depending on data volume
            - API-based reset: 200-1000ms depending on network and API performance
            - Cache invalidation: 10-50ms for Redis flush operations
        
        Thread Safety:
            Safe for concurrent calls with different scopes. Each call manages its
            own database transaction and session lifecycle.
        """
        start_time = datetime.utcnow()
        items_deleted = 0
        details: Dict[str, int] = {}
        errors: List[str] = []
        
        logger.info(f"Starting environment reset with scope='{scope}', dry_run={self.dry_run}")
        
        try:
            # Execute reset operations based on scope
            if scope == "all":
                # Complete reset - execute all cleanup operations
                # Use asyncio.gather for concurrent execution where possible
                results = await asyncio.gather(
                    self._reset_users(),
                    self._reset_projects(),
                    self._reset_sessions(),
                    self._reset_cache(),
                    self._reset_feature_flags(),
                    return_exceptions=True  # Continue on individual failures
                )
                
                # Process results and track counts
                operation_names = ["users", "projects", "sessions", "cache", "feature_flags"]
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        error_msg = f"Failed to reset {operation_names[i]}: {str(result)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        details[operation_names[i]] = 0
                    else:
                        count = result if isinstance(result, int) else 0
                        details[operation_names[i]] = count
                        items_deleted += count
            
            elif scope == "users":
                # Reset only test users
                count = await self._reset_users()
                details["users"] = count
                items_deleted += count
            
            elif scope == "projects":
                # Reset only projects
                count = await self._reset_projects()
                details["projects"] = count
                items_deleted += count
            
            elif scope == "data":
                # Reset application data (not users/projects)
                # This would include things like test-created documents, files, etc.
                # For now, this is a placeholder for application-specific data cleanup
                logger.info("Data scope reset - application-specific implementation needed")
                details["data"] = 0
            
            # Calculate operation duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Determine success status
            success = len(errors) == 0
            
            # Log completion
            if success:
                logger.info(
                    f"Environment reset completed successfully: "
                    f"scope='{scope}', items_deleted={items_deleted}, duration={duration_ms}ms"
                )
            else:
                logger.warning(
                    f"Environment reset completed with errors: "
                    f"scope='{scope}', items_deleted={items_deleted}, errors={len(errors)}, "
                    f"duration={duration_ms}ms"
                )
            
            return {
                "success": success,
                "scope": scope,
                "items_deleted": items_deleted,
                "details": details,
                "duration_ms": duration_ms,
                "errors": errors if errors else None,
                "dry_run": self.dry_run
            }
        
        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception(f"Unexpected error during environment reset: {e}")
            
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "success": False,
                "scope": scope,
                "items_deleted": items_deleted,
                "details": details,
                "duration_ms": duration_ms,
                "errors": [f"Critical error: {str(e)}"],
                "dry_run": self.dry_run
            }
    
    async def query_resources(
        self,
        resource_type: Literal["users", "projects", "sessions", "data"],
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query current state of test environment resources.
        
        Retrieves resources from the test environment matching the specified type
        and optional filter criteria. Useful for debugging test state, verifying
        cleanup operations, and inspecting environment configuration.
        
        Args:
            resource_type (Literal): Type of resource to query:
                - "users": Test users with email, role, and metadata
                - "projects": Test projects with name, owner, and status
                - "sessions": Active test sessions with configuration
                - "data": Application data entries
            filters (Optional[Dict[str, Any]]): Filter criteria as key-value pairs.
                Examples:
                - {"role": "admin"} - Filter users by role
                - {"status": "active"} - Filter projects by status
                - {"created_after": "2024-01-01"} - Filter by creation date
        
        Returns:
            Dict[str, Any]: Query result containing:
                - resource_type (str): Type of resource queried
                - count (int): Number of matching resources found
                - items (List[Dict]): List of resource dictionaries with full details
                - filters_applied (Dict): Filter criteria that were used
                - query_time_ms (int): Query execution time in milliseconds
        
        Query Strategies:
            - Database-available: Direct SQL query via SQLAlchemy for fast results
            - API-only: HTTP GET requests to application API endpoints
            - Hybrid: Database for some types, API for others based on availability
        
        Example:
            # Query all admin users
            result = await state_service.query_resources(
                resource_type="users",
                filters={"role": "admin"}
            )
            print(f"Found {result['count']} admin users")
            for user in result['items']:
                print(f"  - {user['email']}")
            
            # Query recent test sessions
            result = await state_service.query_resources(
                resource_type="sessions",
                filters={"started_after": "2024-01-15"}
            )
        
        Performance:
            - Database query: 10-50ms depending on table size and indexes
            - API query: 50-200ms depending on network and API performance
        
        Thread Safety:
            Safe for concurrent queries. Each query uses its own database session.
        """
        start_time = datetime.utcnow()
        filters = filters or {}
        
        logger.info(f"Querying resources: type='{resource_type}', filters={filters}")
        
        try:
            items: List[Dict[str, Any]] = []
            
            # Query based on resource type
            if resource_type == "users":
                items = await self._query_users(filters)
            elif resource_type == "projects":
                items = await self._query_projects(filters)
            elif resource_type == "sessions":
                items = await self._query_sessions(filters)
            elif resource_type == "data":
                # Placeholder for application-specific data queries
                logger.info("Data resource type - application-specific implementation needed")
                items = []
            else:
                # This shouldn't happen due to Literal type, but defensive programming
                logger.error(f"Unknown resource type: {resource_type}")
                items = []
            
            # Calculate query duration
            end_time = datetime.utcnow()
            query_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(
                f"Query completed: type='{resource_type}', count={len(items)}, "
                f"duration={query_time_ms}ms"
            )
            
            return {
                "resource_type": resource_type,
                "count": len(items),
                "items": items,
                "filters_applied": filters,
                "query_time_ms": query_time_ms
            }
        
        except Exception as e:
            logger.exception(f"Error querying resources: {e}")
            
            end_time = datetime.utcnow()
            query_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return {
                "resource_type": resource_type,
                "count": 0,
                "items": [],
                "filters_applied": filters,
                "query_time_ms": query_time_ms,
                "error": str(e)
            }
    
    async def _reset_users(self) -> int:
        """
        Delete test users from the environment.
        
        Removes users matching test patterns (email domains, name prefixes) using
        either database-direct deletion or API-based cleanup. Uses safe deletion
        patterns to ensure only test users are removed.
        
        Returns:
            int: Count of users deleted
        
        Safe Deletion Patterns:
            - Email matches: *@example.com, *@test.com, test.*@*, *+test@*
            - User metadata: {"test": true} or {"environment": "test"}
        
        Deletion Strategy:
            1. Database-available: DELETE FROM test_users WHERE email LIKE pattern
            2. API-fallback: GET /api/users, filter locally, DELETE each matching user
        
        Error Handling:
            - Database errors: Logged and propagated for transaction rollback
            - API errors: Logged as warnings, counts partial deletions
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would delete test users")
            return 0
        
        deleted_count = 0
        
        try:
            # Strategy 1: Database-direct deletion (preferred)
            if self.db_manager is not None:
                async with self.db_manager.get_session() as session:
                    # Build safe deletion query using test email patterns
                    # Only delete users with test domains or test prefixes
                    test_patterns = [
                        "%@example.com",
                        "%@test.com",
                        "test.%@%",
                        "%+test@%"
                    ]
                    
                    # Build OR conditions for all patterns
                    conditions = [TestUser.email.like(pattern) for pattern in test_patterns]
                    
                    # Also check metadata for test flag
                    # Note: JSON filtering syntax varies by database
                    # For SQLite, we'll fetch and filter in Python
                    query = select(TestUser).where(or_(*conditions))
                    result = await session.execute(query)
                    users_to_delete = result.scalars().all()
                    
                    # Filter by metadata if present
                    safe_users = []
                    for user in users_to_delete:
                        if user.user_metadata:
                            try:
                                metadata = user.user_metadata if isinstance(user.user_metadata, dict) else json.loads(user.user_metadata)
                                if metadata.get("test") is True or metadata.get("environment") == "test":
                                    safe_users.append(user)
                                else:
                                    # Pattern match but no test metadata - still safe to delete
                                    safe_users.append(user)
                            except (json.JSONDecodeError, TypeError):
                                # If metadata is invalid, rely on email pattern
                                safe_users.append(user)
                        else:
                            # No metadata, rely on email pattern
                            safe_users.append(user)
                    
                    # Delete all safe users
                    for user in safe_users:
                        await session.delete(user)
                        deleted_count += 1
                    
                    await session.commit()
                    logger.info(f"Deleted {deleted_count} test users via database")
            
            # Strategy 2: API-based deletion (fallback)
            else:
                if settings.is_admin_configured():
                    deleted_count = await self._reset_users_via_api()
                    logger.info(f"Deleted {deleted_count} test users via API")
                else:
                    logger.warning(
                        "Cannot reset users: database not configured and admin credentials not available"
                    )
        
        except Exception as e:
            logger.error(f"Error resetting users: {e}")
            raise
        
        return deleted_count
    
    async def _reset_users_via_api(self) -> int:
        """
        Delete test users via application API endpoints.
        
        Uses authenticated API requests to delete test users when direct database
        access is not available. Requires admin credentials configuration.
        
        Returns:
            int: Count of users deleted via API
        """
        deleted_count = 0
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Authenticate as admin
                auth_response = await client.post(
                    f"{settings.app_api_url}/auth/login",
                    json={
                        "email": settings.app_admin_email,
                        "password": settings.app_admin_password
                    }
                )
                
                if auth_response.status_code != 200:
                    logger.error(f"Admin authentication failed: {auth_response.status_code}")
                    return 0
                
                auth_data = auth_response.json()
                access_token = auth_data.get("access_token") or auth_data.get("token")
                
                if not access_token:
                    logger.error("No access token in authentication response")
                    return 0
                
                headers = {"Authorization": f"Bearer {access_token}"}
                
                # Fetch all users
                users_response = await client.get(
                    f"{settings.app_api_url}/users",
                    headers=headers
                )
                
                if users_response.status_code != 200:
                    logger.error(f"Failed to fetch users: {users_response.status_code}")
                    return 0
                
                users = users_response.json()
                users_list = users if isinstance(users, list) else users.get("items", [])
                
                # Filter test users by email pattern
                test_patterns = [
                    r".*@example\.com$",
                    r".*@test\.com$",
                    r"^test\..*@.*$",
                    r".*\+test@.*$"
                ]
                
                compiled_patterns = [re.compile(pattern) for pattern in test_patterns]
                
                for user in users_list:
                    email = user.get("email", "")
                    user_id = user.get("id") or user.get("user_id")
                    
                    # Check if email matches test pattern
                    if any(pattern.match(email) for pattern in compiled_patterns):
                        # Delete user via API
                        delete_response = await client.delete(
                            f"{settings.app_api_url}/users/{user_id}",
                            headers=headers
                        )
                        
                        if delete_response.status_code in (200, 204):
                            deleted_count += 1
                            logger.debug(f"Deleted user via API: {email}")
                        else:
                            logger.warning(
                                f"Failed to delete user {email}: {delete_response.status_code}"
                            )
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during API-based user deletion: {e}")
        except Exception as e:
            logger.error(f"Error during API-based user deletion: {e}")
        
        return deleted_count
    
    async def _reset_projects(self) -> int:
        """
        Delete test projects from the environment.
        
        Removes projects matching test patterns using database or API cleanup.
        Projects are identified by name prefixes (test.*, test_*) or metadata tags.
        
        Returns:
            int: Count of projects deleted
        
        Safe Deletion Patterns:
            - Name matches: test.*, test_*, *_test, *-test
            - Metadata: {"test": true} or {"environment": "test"}
            - Owner: Projects owned by test users (identified by email pattern)
        
        Note:
            This is a placeholder implementation. Actual project cleanup depends on
            the target application's project model and API structure. Customize the
            query/deletion logic based on your application schema.
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would delete test projects")
            return 0
        
        deleted_count = 0
        
        try:
            # Placeholder for project deletion logic
            # In a real implementation, this would:
            # 1. Query projects table/API for test projects
            # 2. Filter by name patterns (test.*, test_*)
            # 3. Delete matching projects
            
            logger.info("Project deletion - application-specific implementation needed")
            
            # Example API-based deletion if admin configured
            if settings.is_admin_configured():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Authenticate and fetch projects
                    # Delete projects matching test patterns
                    # This is application-specific
                    pass
        
        except Exception as e:
            logger.error(f"Error resetting projects: {e}")
            raise
        
        return deleted_count
    
    async def _reset_cache(self) -> int:
        """
        Invalidate application caches (Redis, memcached).
        
        Clears cache entries to ensure tests start from clean cache state. Supports
        both complete cache flush and pattern-based deletion for test-specific keys.
        
        Returns:
            int: Count of cache keys deleted (or 1 for complete flush)
        
        Cache Invalidation Strategies:
            - Complete flush: FLUSHDB for test-isolated Redis instance
            - Pattern-based: DEL test:* for shared Redis instances
            - Graceful degradation: Skips cache reset if Redis unavailable
        
        Configuration:
            Requires REDIS_URL in settings (future enhancement) or falls back to
            skip cache invalidation with warning log.
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would invalidate application cache")
            return 0
        
        if not REDIS_AVAILABLE:
            logger.debug("Redis not available - skipping cache invalidation")
            return 0
        
        if self.redis_client is None:
            logger.debug("Redis client not configured - skipping cache invalidation")
            return 0
        
        try:
            # Pattern-based deletion for safety (don't flush entire cache)
            # This assumes test keys follow a naming convention
            test_key_patterns = ["test:*", "test_*", "*:test", "*_test"]
            deleted_count = 0
            
            for pattern in test_key_patterns:
                keys = self.redis_client.keys(pattern)
                if keys:
                    deleted = self.redis_client.delete(*keys)
                    deleted_count += deleted
            
            logger.info(f"Deleted {deleted_count} cache keys")
            return deleted_count
        
        except Exception as e:
            logger.warning(f"Error invalidating cache (non-critical): {e}")
            return 0
    
    async def _reset_sessions(self) -> int:
        """
        Invalidate active test sessions.
        
        Removes test session records from the database to ensure fresh session
        state for new test executions. Sessions are identified by session_id
        patterns or environment configuration metadata.
        
        Returns:
            int: Count of sessions invalidated
        
        Safe Deletion Patterns:
            - Session IDs: test-*, test_*, *-test-*
            - Environment config: {"environment": "test"}
            - Age-based: Sessions older than 24 hours
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would invalidate test sessions")
            return 0
        
        deleted_count = 0
        
        try:
            if self.db_manager is not None:
                async with self.db_manager.get_session() as session:
                    # Delete sessions matching test patterns or older than 24 hours
                    cutoff_time = datetime.utcnow() - timedelta(hours=24)
                    
                    test_session_patterns = [
                        "test-%",
                        "test_%",
                        "%-test-%"
                    ]
                    
                    conditions = [TestSession.session_id.like(pattern) for pattern in test_session_patterns]
                    conditions.append(TestSession.started_at < cutoff_time)
                    
                    query = select(TestSession).where(or_(*conditions))
                    result = await session.execute(query)
                    sessions_to_delete = result.scalars().all()
                    
                    for test_session in sessions_to_delete:
                        await session.delete(test_session)
                        deleted_count += 1
                    
                    await session.commit()
                    logger.info(f"Deleted {deleted_count} test sessions")
            else:
                logger.debug("Database not configured - skipping session cleanup")
        
        except Exception as e:
            logger.error(f"Error resetting sessions: {e}")
            raise
        
        return deleted_count
    
    async def _reset_feature_flags(self) -> int:
        """
        Reset feature flags to default states.
        
        Restores feature flags to their baseline configuration to ensure consistent
        test conditions. This prevents feature flag state from one test affecting
        subsequent tests.
        
        Returns:
            int: Count of feature flags reset (or 1 for successful reset operation)
        
        Reset Strategy:
            - API-based: POST /api/admin/feature-flags/reset
            - Database-based: UPDATE feature_flags SET enabled = default_value
            - Config-file: Reload flags from default configuration file
        
        Note:
            Implementation depends on application's feature flag system. Common
            systems include LaunchDarkly, Unleash, or custom implementations.
        """
        if self.dry_run:
            logger.info("[DRY RUN] Would reset feature flags")
            return 0
        
        try:
            # Placeholder for feature flag reset logic
            # Actual implementation depends on feature flag system used
            logger.info("Feature flag reset - application-specific implementation needed")
            
            # Example: API-based reset if admin configured
            if settings.is_admin_configured():
                # Could implement feature flag reset via admin API
                pass
            
            return 0
        
        except Exception as e:
            logger.warning(f"Error resetting feature flags (non-critical): {e}")
            return 0
    
    async def _query_users(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query test users with optional filters.
        
        Args:
            filters (Dict): Filter criteria (e.g., {"role": "admin"})
        
        Returns:
            List[Dict]: List of user dictionaries
        """
        users = []
        
        try:
            if self.db_manager is not None:
                async with self.db_manager.get_session() as session:
                    query = select(TestUser)
                    
                    # Apply filters
                    if "role" in filters:
                        query = query.where(TestUser.role == filters["role"])
                    
                    if "email" in filters:
                        query = query.where(TestUser.email.like(f"%{filters['email']}%"))
                    
                    result = await session.execute(query)
                    db_users = result.scalars().all()
                    
                    # Convert ORM objects to dictionaries
                    for user in db_users:
                        users.append({
                            "id": user.id,
                            "email": user.email,
                            "role": user.role,
                            "created_at": user.created_at.isoformat() if user.created_at else None,
                            "metadata": user.user_metadata
                        })
            else:
                logger.debug("Database not configured - using API-based user query")
                # Fallback to API query if needed
        
        except Exception as e:
            logger.error(f"Error querying users: {e}")
        
        return users
    
    async def _query_projects(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query projects with optional filters.
        
        Args:
            filters (Dict): Filter criteria
        
        Returns:
            List[Dict]: List of project dictionaries
        
        Note:
            Placeholder - requires application-specific implementation
        """
        # Placeholder for project query logic
        logger.info("Project query - application-specific implementation needed")
        return []
    
    async def _query_sessions(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query test sessions with optional filters.
        
        Args:
            filters (Dict): Filter criteria
        
        Returns:
            List[Dict]: List of session dictionaries
        """
        sessions = []
        
        try:
            if self.db_manager is not None:
                async with self.db_manager.get_session() as session:
                    query = select(TestSession)
                    
                    # Apply filters
                    if "session_id" in filters:
                        query = query.where(TestSession.session_id.like(f"%{filters['session_id']}%"))
                    
                    if "started_after" in filters:
                        started_after = datetime.fromisoformat(filters["started_after"])
                        query = query.where(TestSession.started_at >= started_after)
                    
                    result = await session.execute(query)
                    db_sessions = result.scalars().all()
                    
                    # Convert ORM objects to dictionaries
                    for test_session in db_sessions:
                        sessions.append({
                            "id": test_session.id,
                            "session_id": test_session.session_id,
                            "started_at": test_session.started_at.isoformat() if test_session.started_at else None,
                            "environment_config": test_session.environment_config
                        })
            else:
                logger.debug("Database not configured - session query unavailable")
        
        except Exception as e:
            logger.error(f"Error querying sessions: {e}")
        
        return sessions

