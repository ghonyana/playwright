"""
Database module for FastAPI MCP server optional persistence layer.

This package provides SQLAlchemy-based database components for test data lifecycle
management in the FastAPI MCP server. The database layer is optional and supports
both in-memory (CI/CD) and file-based (local development) SQLite configurations.

Components:
    - models: SQLAlchemy ORM models (TestUser, PayloadTemplate, TestSession)
    - connection: DatabaseManager for async session management and schema operations

Usage:
    from mcp_servers.fastapi_mcp.database.connection import DatabaseManager
    from mcp_servers.fastapi_mcp.database.models import TestUser, PayloadTemplate, TestSession

The database layer supports:
    - Ephemeral test data storage with rapid reset capabilities
    - Async SQLAlchemy 2.0+ patterns with aiosqlite adapter
    - Deterministic test execution through environment state management
    - Concurrent access with connection pooling and transaction isolation
"""
