"""
SQLAlchemy ORM models for FastAPI MCP server optional persistent state storage.

This module defines database schema for test data lifecycle management with support
for deterministic test execution, environment reset operations, and state queries.

Models:
    - TestUser: Seeded test users with email, role, and password hash
    - PayloadTemplate: Request payload templates for build_payload tool
    - TestSession: Test session tracking with environment configuration

All tables are designed for rapid creation/deletion via reset_env tool with
datetime tracking for lifecycle management. Supports both in-memory (CI) and
file-based (dev) SQLite configurations via async SQLAlchemy 2.0+ patterns.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base


# Create declarative base for all ORM models
# This Base object provides metadata registry for table creation/deletion
# and is used by connection.py for create_all() and drop_all() operations
Base = declarative_base()


class TestUser(Base):
    """
    ORM model for tracking seeded test users created by seed_user MCP tool.
    
    Stores user credentials and metadata for deterministic test execution.
    Users are created fresh for each test suite and cleared via reset_env.
    
    Attributes:
        id: Auto-incrementing primary key
        email: Unique email address for user identification and login
        role: User role (e.g., 'admin', 'customer', 'guest') for permission testing
        password_hash: Hashed password for secure credential storage
        created_at: UTC timestamp when user was seeded
        metadata: Flexible JSON field for custom user attributes (e.g., org_id, permissions)
    
    Example:
        user = TestUser(
            email="test@example.com",
            role="customer",
            password_hash="hashed_value",
            metadata={"org_id": "123", "tier": "premium"}
        )
    """
    __tablename__ = "test_users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    role = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata = Column(JSON, nullable=True)
    
    def __repr__(self) -> str:
        """String representation for debugging and logging."""
        return f"<TestUser(id={self.id}, email='{self.email}', role='{self.role}')>"


class PayloadTemplate(Base):
    """
    ORM model for storing request payload templates used by build_payload MCP tool.
    
    Templates define reusable JSON schemas for API request bodies, ensuring
    consistent test data structure across test executions.
    
    Attributes:
        id: Auto-incrementing primary key
        template_name: Unique identifier for template (e.g., 'create_user', 'update_product')
        template_schema: JSON schema defining payload structure with default values
        created_at: UTC timestamp when template was registered
    
    Example:
        template = PayloadTemplate(
            template_name="create_user",
            template_schema={
                "email": "{{email}}",
                "password": "{{password}}",
                "role": "customer",
                "profile": {
                    "first_name": "{{first_name}}",
                    "last_name": "{{last_name}}"
                }
            }
        )
    """
    __tablename__ = "payload_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String, unique=True, nullable=False, index=True)
    template_schema = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        """String representation for debugging and logging."""
        return f"<PayloadTemplate(id={self.id}, template_name='{self.template_name}')>"


class TestSession(Base):
    """
    ORM model for tracking test session metadata and environment configuration.
    
    Records test execution sessions for state management and environment isolation.
    Each session maintains configuration snapshot for reproducible test execution.
    
    Attributes:
        id: Auto-incrementing primary key
        session_id: Unique session identifier (UUID or timestamp-based)
        started_at: UTC timestamp when test session began
        environment_config: JSON snapshot of environment variables and settings
    
    Example:
        session = TestSession(
            session_id="test-run-20240101-123456",
            environment_config={
                "BASE_URL": "http://localhost:3000",
                "API_BASE_URL": "http://localhost:8000",
                "HEADLESS": True,
                "database_state": "reset"
            }
        )
    """
    __tablename__ = "test_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, unique=True, nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    environment_config = Column(JSON, nullable=True)
    
    def __repr__(self) -> str:
        """String representation for debugging and logging."""
        return f"<TestSession(id={self.id}, session_id='{self.session_id}', started_at='{self.started_at}')>"
