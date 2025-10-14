"""
FastAPI MCP Server Configuration Module

This module provides environment-based configuration management for the FastAPI
Model Context Protocol (MCP) server using pydantic-settings. It handles server
parameters, authentication settings, application under test URLs, and optional
database connections.

Configuration is loaded from environment variables and .env files with automatic
validation and type conversion. All settings are exposed through a singleton
instance for application-wide access.

Environment Variables:
    Server Configuration:
        - HOST: Server bind address (default: 0.0.0.0)
        - PORT: Server port (default: 8000)
        - RELOAD: Enable auto-reload on code changes (default: False)
    
    Authentication Configuration:
        - AUTH_SECRET_KEY: JWT signing secret (required)
        - AUTH_ALGORITHM: JWT algorithm (default: HS256)
        - AUTH_TOKEN_EXPIRE_MINUTES: Token expiration time (default: 60)
    
    Application Under Test Configuration:
        - APP_BASE_URL: Base URL of web application (required)
        - APP_API_URL: Base URL of REST API (required)
        - APP_ADMIN_EMAIL: Admin user email for privileged operations (optional)
        - APP_ADMIN_PASSWORD: Admin user password (optional)
    
    Database Configuration:
        - DATABASE_URL: Database connection string (optional)

Example .env file:
    AUTH_SECRET_KEY=your-secret-key-here
    APP_BASE_URL=http://localhost:3000
    APP_API_URL=http://localhost:3000/api
    APP_ADMIN_EMAIL=admin@example.com
    APP_ADMIN_PASSWORD=secure-password
    DATABASE_URL=postgresql://user:pass@localhost/testdb

Usage:
    from mcp_servers.fastapi_mcp.config import settings
    
    # Access configuration values
    print(f"Server starting on {settings.host}:{settings.port}")
    print(f"Testing application at {settings.app_base_url}")
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    FastAPI MCP Server configuration settings.
    
    This class uses pydantic-settings to automatically load and validate
    configuration from environment variables and .env files. All settings
    are type-checked and validated at application startup.
    
    Attributes:
        host: Server bind address. Use 0.0.0.0 to listen on all interfaces,
            or 127.0.0.1 for localhost only.
        port: Server port number. Should be > 1024 for non-root execution.
        reload: Enable uvicorn auto-reload during development. Set to False
            in production for better performance.
        
        auth_secret_key: Secret key for JWT token signing. Must be a strong,
            random string. Generate with: openssl rand -hex 32
        auth_algorithm: JWT signing algorithm. HS256 is recommended for
            symmetric key signing.
        auth_token_expire_minutes: JWT token validity duration in minutes.
            Shorter values improve security but require more frequent re-auth.
        
        app_base_url: Base URL of the web application under test. Used by
            Playwright for UI automation. Should include protocol and port.
        app_api_url: Base URL of the REST API under test. Used by httpx
            for API testing. Typically app_base_url + /api path.
        app_admin_email: Optional admin user email for privileged test
            operations that require elevated permissions.
        app_admin_password: Optional admin user password for authentication
            in privileged test scenarios.
        
        database_url: Optional database connection string for test data
            management and state tracking. Supports PostgreSQL, MySQL, SQLite.
            Format: dialect://user:pass@host:port/database
    """
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    # Authentication Configuration (required for security)
    auth_secret_key: str  # No default - must be provided via environment
    auth_algorithm: str = "HS256"
    auth_token_expire_minutes: int = 60
    
    # Application Under Test Configuration (required for test execution)
    app_base_url: str  # No default - must be provided via environment
    app_api_url: str  # No default - must be provided via environment
    
    # Optional Admin Credentials (for privileged test operations)
    app_admin_email: Optional[str] = None
    app_admin_password: Optional[str] = None
    
    # Optional Database Configuration (for test data management)
    database_url: Optional[str] = None
    
    # Pydantic Settings Configuration
    model_config = SettingsConfigDict(
        # Load configuration from .env file in project root
        env_file=".env",
        
        # Use UTF-8 encoding for .env file reading
        env_file_encoding="utf-8",
        
        # Case-insensitive environment variable matching
        # Allows HOST, host, Host to all map to the 'host' field
        case_sensitive=False,
        
        # Allow extra fields in environment without raising validation errors
        # This prevents issues when other applications share the same .env file
        extra="ignore"
    )
    
    def get_server_url(self) -> str:
        """
        Construct the full server URL from host and port.
        
        Returns:
            Complete server URL (e.g., "http://0.0.0.0:8000")
        
        Example:
            >>> settings.get_server_url()
            "http://0.0.0.0:8000"
        """
        return f"http://{self.host}:{self.port}"
    
    def is_admin_configured(self) -> bool:
        """
        Check if admin credentials are configured.
        
        Returns:
            True if both admin email and password are set, False otherwise.
        
        Example:
            >>> if settings.is_admin_configured():
            ...     # Perform privileged operations
            ...     pass
        """
        return self.app_admin_email is not None and self.app_admin_password is not None
    
    def is_database_configured(self) -> bool:
        """
        Check if database connection is configured.
        
        Returns:
            True if database_url is set, False otherwise.
        
        Example:
            >>> if settings.is_database_configured():
            ...     # Initialize database connection
            ...     pass
        """
        return self.database_url is not None
    
    def validate_required_settings(self) -> list[str]:
        """
        Validate that all required settings are properly configured.
        
        Returns:
            List of validation error messages. Empty list if all valid.
        
        Example:
            >>> errors = settings.validate_required_settings()
            >>> if errors:
            ...     for error in errors:
            ...         print(f"Configuration error: {error}")
        """
        errors = []
        
        # Validate auth_secret_key strength
        if len(self.auth_secret_key) < 32:
            errors.append(
                "auth_secret_key must be at least 32 characters for security. "
                "Generate with: openssl rand -hex 32"
            )
        
        # Validate URLs have proper format
        if not self.app_base_url.startswith(("http://", "https://")):
            errors.append(
                f"app_base_url must start with http:// or https://, "
                f"got: {self.app_base_url}"
            )
        
        if not self.app_api_url.startswith(("http://", "https://")):
            errors.append(
                f"app_api_url must start with http:// or https://, "
                f"got: {self.app_api_url}"
            )
        
        # Validate port range
        if not (1 <= self.port <= 65535):
            errors.append(
                f"port must be between 1 and 65535, got: {self.port}"
            )
        
        # Validate token expiration is reasonable
        if self.auth_token_expire_minutes < 1:
            errors.append(
                f"auth_token_expire_minutes must be at least 1, "
                f"got: {self.auth_token_expire_minutes}"
            )
        
        return errors


# Singleton instance for application-wide configuration access
# This instance is created once when the module is imported and reused
# throughout the application lifecycle
settings = Settings()
