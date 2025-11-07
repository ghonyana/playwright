"""
SQLAlchemy async database connection manager for FastAPI MCP server.

This module provides the DatabaseManager class for managing async database connections
using SQLAlchemy 2.0+ with SQLite backend. Supports both in-memory (CI/CD) and file-based
(local development) database configurations with automatic async adapter conversion.

Key Features:
    - Async SQLAlchemy 2.0+ engine with aiosqlite adapter
    - Async session factory with automatic transaction management
    - Schema initialization via create_tables() for server startup
    - Complete database reset via reset_database() for reset_env tool
    - Connection pooling with concurrent access support
    - Context manager pattern for safe session lifecycle

Environment Configurations:
    - CI/CD Mode: sqlite:///:memory: (in-memory, ephemeral)
    - Development Mode: sqlite:///./mcp_test.db (file-based, persistent)

Example:
    # Initialize database manager
    db_manager = DatabaseManager(database_url="sqlite:///./test.db")
    
    # Create schema on startup
    await db_manager.create_tables()
    
    # Use session in MCP tool endpoints
    async with db_manager.get_session() as session:
        user = TestUser(email="test@example.com", role="admin")
        session.add(user)
        # Auto-commits on success, rolls back on exception
    
    # Reset database for test isolation
    await db_manager.reset_database()
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.exc import SQLAlchemyError

from mcp_servers.fastapi_mcp.database.models import Base


# Configure module logger
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages async database connections and schema operations for FastAPI MCP server.
    
    This class provides a high-level interface for SQLAlchemy async operations with
    automatic URL conversion for SQLite async support, connection pooling configuration,
    and transactional session management via async context managers.
    
    Attributes:
        engine (AsyncEngine): SQLAlchemy async database engine
        async_session_factory (async_sessionmaker): Configured session factory
        database_url (str): Original database URL (converted internally to async format)
    
    Thread Safety:
        Configured with check_same_thread=False for SQLite to support concurrent
        access from multiple pytest workers and asyncio tasks.
    
    Transaction Management:
        Sessions created via get_session() automatically commit on successful exit
        and rollback on exceptions, ensuring consistent database state.
    """
    
    def __init__(self, database_url: str):
        """
        Initialize DatabaseManager with async engine and session factory.
        
        Automatically converts standard SQLite URLs to async format by replacing
        'sqlite://' with 'sqlite+aiosqlite://' to enable async database operations.
        
        Args:
            database_url (str): Database connection string. Examples:
                - "sqlite:///:memory:" (in-memory, CI/CD mode)
                - "sqlite:///./mcp_test.db" (file-based, development mode)
                - "sqlite+aiosqlite:///./test.db" (explicit async format)
        
        Configuration:
            - echo=False: Disables SQL query logging for performance
            - check_same_thread=False: Allows multi-threaded access to SQLite
            - expire_on_commit=False: Prevents attribute expiration after commit
              for better async performance
        
        Raises:
            SQLAlchemyError: If engine creation fails due to invalid URL or
                connection issues
        """
        # Store original URL for reference
        self.database_url = database_url
        
        # Convert standard SQLite URL to async format if needed
        # This enables aiosqlite adapter for async operations
        if database_url.startswith("sqlite://") and not database_url.startswith("sqlite+aiosqlite://"):
            async_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
            logger.info(f"Converted database URL to async format: {database_url} -> {async_url}")
        else:
            async_url = database_url
        
        try:
            # Create async SQLAlchemy engine with SQLite-specific configuration
            # connect_args passed directly to the underlying driver (aiosqlite)
            self.engine: AsyncEngine = create_async_engine(
                async_url,
                echo=False,  # Disable SQL query logging for performance
                connect_args={"check_same_thread": False}  # Allow concurrent SQLite access
            )
            
            logger.info(f"Created async database engine for: {async_url}")
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
        
        # Initialize async session factory with optimal async configuration
        # Sessions created from this factory are used by MCP tool endpoints
        self.async_session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,  # Use async session class
            expire_on_commit=False,  # Prevent attribute expiration for async performance
        )
        
        logger.debug("Initialized async session factory")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Async context manager for database session lifecycle with automatic transaction handling.
        
        Provides a fresh AsyncSession for each MCP tool request with automatic commit
        on successful completion and rollback on exceptions. Ensures clean transaction
        boundaries and prevents partial state updates.
        
        Yields:
            AsyncSession: Active database session for ORM operations
        
        Transaction Behavior:
            - Success: Automatically commits all pending changes on context exit
            - Exception: Automatically rolls back transaction and propagates exception
            - Always closes session to prevent connection leaks
        
        Usage:
            async with db_manager.get_session() as session:
                user = TestUser(email="test@example.com", role="admin")
                session.add(user)
                await session.flush()  # Optional: flush to get auto-generated IDs
                # Automatic commit happens here on success
        
        Raises:
            SQLAlchemyError: Database operation errors (propagated after rollback)
            Exception: Any other exceptions (propagated after rollback)
        
        Thread Safety:
            Each call creates an independent session, safe for concurrent use across
            multiple pytest workers and asyncio tasks.
        """
        # Create new session from factory
        session: AsyncSession = self.async_session_factory()
        
        try:
            logger.debug("Created new database session")
            
            # Yield session to caller for use in async with block
            yield session
            
            # Commit transaction on successful completion
            await session.commit()
            logger.debug("Committed database transaction")
            
        except SQLAlchemyError as e:
            # Rollback on database errors
            await session.rollback()
            logger.error(f"Database error, rolled back transaction: {e}")
            raise
            
        except Exception as e:
            # Rollback on any other exceptions
            await session.rollback()
            logger.error(f"Unexpected error, rolled back transaction: {e}")
            raise
            
        finally:
            # Always close session to release connection back to pool
            await session.close()
            logger.debug("Closed database session")
    
    async def create_tables(self) -> None:
        """
        Create all database tables defined in ORM models on server startup.
        
        Executes Base.metadata.create_all() via async connection to initialize
        the database schema. This method is idempotent - calling it multiple times
        will not recreate existing tables (SQLAlchemy checks table existence first).
        
        Creates tables for:
            - TestUser: Seeded test users with credentials
            - PayloadTemplate: Request payload templates
            - TestSession: Test session tracking metadata
        
        Usage:
            # Call once during FastAPI MCP server startup
            db_manager = DatabaseManager(database_url)
            await db_manager.create_tables()
        
        Raises:
            SQLAlchemyError: If table creation fails due to permissions,
                invalid schema, or database connection issues
        
        Note:
            For in-memory databases (sqlite:///:memory:), tables must be created
            every time the server starts since the database is ephemeral.
        """
        try:
            # Begin async connection and run sync metadata operation
            async with self.engine.begin() as conn:
                # run_sync executes synchronous SQLAlchemy operations in async context
                # Base.metadata.create_all creates all tables defined in models.py
                await conn.run_sync(Base.metadata.create_all)
                
            logger.info("Successfully created all database tables")
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    async def reset_database(self) -> None:
        """
        Completely reset database by dropping and recreating all tables.
        
        Executes Base.metadata.drop_all() followed by Base.metadata.create_all()
        to provide a clean database state. This is used by the reset_env MCP tool
        to ensure deterministic test execution with no residual state.
        
        WARNING:
            This operation is DESTRUCTIVE and will delete all data in the database.
            Only use in test environments, never in production.
        
        Reset Process:
            1. Drop all tables (TestUser, PayloadTemplate, TestSession)
            2. Drop all associated indexes and constraints
            3. Recreate all tables with fresh schema
            4. Return empty database ready for new test data
        
        Usage:
            # Called by reset_env MCP tool before each test suite
            async with db_manager.get_session() as session:
                await db_manager.reset_database()
            
            # Or directly from MCP tool endpoint
            await db_manager.reset_database()
        
        Raises:
            SQLAlchemyError: If drop or create operations fail
        
        Performance:
            Very fast for SQLite (typically <100ms). In-memory databases
            reset nearly instantly since data exists only in RAM.
        """
        try:
            async with self.engine.begin() as conn:
                # First, drop all existing tables
                # This removes all data, indexes, and constraints
                await conn.run_sync(Base.metadata.drop_all)
                logger.info("Dropped all database tables")
                
                # Then, recreate all tables with clean schema
                # This ensures database structure matches current ORM models
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Recreated all database tables")
            
            logger.info("Successfully reset database to clean state")
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to reset database: {e}")
            raise
    
    async def dispose(self) -> None:
        """
        Dispose of database engine and close all connections.
        
        Cleanly shuts down the async engine, closing all active connections
        and releasing resources. Should be called during FastAPI server shutdown.
        
        Usage:
            # FastAPI lifespan context manager
            @asynccontextmanager
            async def lifespan(app: FastAPI):
                await db_manager.create_tables()
                yield
                await db_manager.dispose()
        
        Raises:
            SQLAlchemyError: If engine disposal encounters errors
        """
        try:
            await self.engine.dispose()
            logger.info("Disposed database engine and closed all connections")
        except SQLAlchemyError as e:
            logger.error(f"Error disposing database engine: {e}")
            raise

