"""
Playwright MCP Server Configuration

Pydantic Settings-based configuration management for the Playwright MCP server.
Loads environment variables for server host/port, browser preferences, WebSocket settings,
LLM integration endpoints, and development-mode toggles.

Provides type-safe configuration with validation and .env file support.

Environment Variables:
    PLAYWRIGHT_MCP_HOST: Server bind address (default: 0.0.0.0)
    PLAYWRIGHT_MCP_PORT: Server port (default: 8001)
    PLAYWRIGHT_MCP_RELOAD: Auto-reload on code changes (default: False)
    PLAYWRIGHT_MCP_DEFAULT_BROWSER: Browser type (default: chromium)
    PLAYWRIGHT_MCP_HEADLESS: Run browsers in headless mode (default: False)
    PLAYWRIGHT_MCP_LLM_PROVIDER: LLM provider (ollama/openai)
    PLAYWRIGHT_MCP_LLM_MODEL: LLM model name
    PLAYWRIGHT_MCP_LLM_API_KEY: LLM API key for OpenAI
    ... and many more (see PlaywrightMCPSettings fields)

Example:
    from mcp_servers.playwright_mcp.config import settings
    
    # Access configuration
    print(f"Server running on {settings.host}:{settings.port}")
    
    # Get browser launch options
    launch_opts = settings.get_browser_launch_options()
    browser = await playwright.chromium.launch(**launch_opts)
"""

from typing import Any, Dict, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PlaywrightMCPSettings(BaseSettings):
    """
    Configuration settings for Playwright MCP server.
    
    Loads configuration from environment variables with PLAYWRIGHT_MCP_ prefix
    and optional .env file. Provides type-safe access to all server settings
    with validation and helper methods for Playwright and Uvicorn configuration.
    """
    
    # ==================== Server Configuration ====================
    
    host: str = Field(
        default='0.0.0.0',
        description='Server bind address for Playwright MCP server'
    )
    
    port: int = Field(
        default=8001,
        description='Server port (8001 to avoid conflict with FastAPI MCP on 8000)'
    )
    
    reload: bool = Field(
        default=False,
        description='Auto-reload on code changes (development only)'
    )
    
    workers: int = Field(
        default=1,
        description='Uvicorn worker processes (keep at 1 for session state)'
    )
    
    log_level: str = Field(
        default='INFO',
        description='Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)'
    )
    
    # ==================== Browser Configuration ====================
    
    default_browser: str = Field(
        default='chromium',
        description='Default browser type (chromium, firefox, webkit)'
    )
    
    headless: bool = Field(
        default=False,
        description='Run browsers in headless mode (False for LLM visibility during exploration)'
    )
    
    viewport_width: int = Field(
        default=1920,
        description='Default viewport width in pixels'
    )
    
    viewport_height: int = Field(
        default=1080,
        description='Default viewport height in pixels'
    )
    
    slow_mo: int = Field(
        default=0,
        description='Slow down operations by N milliseconds for observation (0 = no slowdown)'
    )
    
    # ==================== WebSocket Configuration ====================
    
    enable_websocket: bool = Field(
        default=True,
        description='Enable WebSocket for real-time streaming to LLM clients'
    )
    
    websocket_ping_interval: int = Field(
        default=20,
        description='WebSocket ping interval in seconds to keep connection alive'
    )
    
    websocket_ping_timeout: int = Field(
        default=20,
        description='WebSocket ping timeout in seconds before considering connection dead'
    )
    
    # ==================== Session Management ====================
    
    max_sessions: int = Field(
        default=10,
        description='Maximum concurrent browser sessions allowed'
    )
    
    session_timeout_minutes: int = Field(
        default=60,
        description='Session idle timeout in minutes before auto-cleanup'
    )
    
    auto_cleanup_sessions: bool = Field(
        default=True,
        description='Automatically cleanup idle sessions after timeout'
    )
    
    # ==================== Exploration Logging ====================
    
    log_exploration_actions: bool = Field(
        default=True,
        description='Log all browser actions for Gherkin generation'
    )
    
    max_log_entries_per_session: int = Field(
        default=1000,
        description='Maximum action log entries per session to prevent memory issues'
    )
    
    exploration_log_dir: str = Field(
        default='exploration_logs',
        description='Directory for storing exploration action logs'
    )
    
    # ==================== LLM Integration (Optional) ====================
    
    llm_provider: Optional[str] = Field(
        default=None,
        description='LLM provider for Gherkin generation (ollama/openai/none)'
    )
    
    llm_model: Optional[str] = Field(
        default='llama2',
        description='LLM model name (e.g., llama2, gpt-4, gpt-3.5-turbo)'
    )
    
    llm_api_key: Optional[str] = Field(
        default=None,
        description='LLM API key (required for OpenAI and other hosted providers)'
    )
    
    llm_base_url: Optional[str] = Field(
        default='http://localhost:11434',
        description='LLM base URL (Ollama default or OpenAI-compatible endpoint)'
    )
    
    # ==================== Application Under Test ====================
    
    default_app_url: Optional[str] = Field(
        default=None,
        description='Default application URL for explorations (e.g., http://localhost:3000)'
    )
    
    # ==================== Security (Optional) ====================
    
    require_auth: bool = Field(
        default=False,
        description='Require authentication for MCP endpoints (set True for production)'
    )
    
    auth_secret_key: Optional[str] = Field(
        default=None,
        description='Secret key for JWT token generation if authentication enabled'
    )
    
    # ==================== Pydantic Settings Configuration ====================
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        env_prefix='PLAYWRIGHT_MCP_',
        extra='ignore'
    )
    
    # ==================== Validation Methods ====================
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """
        Validate that port is in valid range for network services.
        
        Args:
            v: Port number to validate
            
        Returns:
            Validated port number
            
        Raises:
            ValueError: If port is outside valid range (1024-65535)
        """
        if not 1024 <= v <= 65535:
            raise ValueError(
                f'Port must be between 1024 and 65535 (unprivileged ports). Got: {v}'
            )
        return v
    
    @field_validator('default_browser')
    @classmethod
    def validate_browser(cls, v: str) -> str:
        """
        Validate that browser type is supported by Playwright.
        
        Args:
            v: Browser type string
            
        Returns:
            Validated browser type in lowercase
            
        Raises:
            ValueError: If browser type is not supported
        """
        valid_browsers = ['chromium', 'firefox', 'webkit']
        browser_lower = v.lower()
        
        if browser_lower not in valid_browsers:
            raise ValueError(
                f'Browser must be one of {valid_browsers}. Got: {v}'
            )
        
        return browser_lower
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate that log level is a recognized logging level.
        
        Args:
            v: Log level string
            
        Returns:
            Validated log level in uppercase
            
        Raises:
            ValueError: If log level is not recognized
        """
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        level_upper = v.upper()
        
        if level_upper not in valid_levels:
            raise ValueError(
                f'Log level must be one of {valid_levels}. Got: {v}'
            )
        
        return level_upper
    
    @field_validator('llm_provider')
    @classmethod
    def validate_llm_provider(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate LLM provider if specified.
        
        Args:
            v: LLM provider string or None
            
        Returns:
            Validated provider in lowercase or None
            
        Raises:
            ValueError: If provider is not supported
        """
        if v is None:
            return None
        
        valid_providers = ['ollama', 'openai']
        provider_lower = v.lower()
        
        if provider_lower not in valid_providers:
            raise ValueError(
                f'LLM provider must be one of {valid_providers}. Got: {v}'
            )
        
        return provider_lower
    
    @model_validator(mode='after')
    def validate_cross_field_requirements(self) -> 'PlaywrightMCPSettings':
        """
        Validate cross-field dependencies and requirements.
        
        Ensures that:
        - If require_auth is True, auth_secret_key must be provided
        - If llm_provider is 'openai', llm_api_key must be provided
        - Viewport dimensions are positive
        - Session limits are reasonable
        
        Returns:
            Self after validation
            
        Raises:
            ValueError: If cross-field requirements are not met
        """
        # Authentication requirement check
        if self.require_auth and not self.auth_secret_key:
            raise ValueError(
                'auth_secret_key is required when require_auth is True'
            )
        
        # OpenAI API key requirement check
        if self.llm_provider == 'openai' and not self.llm_api_key:
            raise ValueError(
                'llm_api_key is required when llm_provider is "openai"'
            )
        
        # Viewport dimension validation
        if self.viewport_width <= 0:
            raise ValueError(f'viewport_width must be positive. Got: {self.viewport_width}')
        
        if self.viewport_height <= 0:
            raise ValueError(f'viewport_height must be positive. Got: {self.viewport_height}')
        
        # Session limits validation
        if self.max_sessions <= 0:
            raise ValueError(f'max_sessions must be positive. Got: {self.max_sessions}')
        
        if self.session_timeout_minutes <= 0:
            raise ValueError(
                f'session_timeout_minutes must be positive. Got: {self.session_timeout_minutes}'
            )
        
        if self.max_log_entries_per_session <= 0:
            raise ValueError(
                f'max_log_entries_per_session must be positive. Got: {self.max_log_entries_per_session}'
            )
        
        # Slow motion validation
        if self.slow_mo < 0:
            raise ValueError(f'slow_mo cannot be negative. Got: {self.slow_mo}')
        
        return self
    
    # ==================== Helper Methods ====================
    
    def get_browser_launch_options(self) -> Dict[str, Any]:
        """
        Generate Playwright browser.launch() options from configuration.
        
        Returns dictionary of options to pass to playwright.[browser].launch(**options).
        
        Returns:
            Dictionary with Playwright browser launch options
            
        Example:
            settings = PlaywrightMCPSettings()
            launch_opts = settings.get_browser_launch_options()
            browser = await playwright.chromium.launch(**launch_opts)
        """
        options: Dict[str, Any] = {
            'headless': self.headless,
        }
        
        # Add slow_mo only if specified (non-zero)
        if self.slow_mo > 0:
            options['slow_mo'] = self.slow_mo
        
        return options
    
    def get_context_options(self) -> Dict[str, Any]:
        """
        Generate Playwright browser.new_context() options from configuration.
        
        Returns dictionary of options to pass to browser.new_context(**options).
        
        Returns:
            Dictionary with Playwright browser context options
            
        Example:
            settings = PlaywrightMCPSettings()
            context_opts = settings.get_context_options()
            context = await browser.new_context(**context_opts)
        """
        options: Dict[str, Any] = {
            'viewport': {
                'width': self.viewport_width,
                'height': self.viewport_height
            },
            # Enable video recording for exploration sessions
            'record_video_dir': self.exploration_log_dir if self.log_exploration_actions else None,
        }
        
        return options
    
    def get_uvicorn_config(self) -> Dict[str, Any]:
        """
        Generate Uvicorn server configuration from settings.
        
        Returns dictionary of options to pass to uvicorn.run(**config).
        
        Returns:
            Dictionary with Uvicorn configuration options
            
        Example:
            settings = PlaywrightMCPSettings()
            config = settings.get_uvicorn_config()
            uvicorn.run("main:app", **config)
        """
        config: Dict[str, Any] = {
            'host': self.host,
            'port': self.port,
            'reload': self.reload,
            'workers': self.workers,
            'log_level': self.log_level.lower(),
        }
        
        # Add WebSocket ping settings if WebSocket is enabled
        if self.enable_websocket:
            config['ws_ping_interval'] = self.websocket_ping_interval
            config['ws_ping_timeout'] = self.websocket_ping_timeout
        
        return config
    
    def is_development_mode(self) -> bool:
        """
        Check if server is running in development mode.
        
        Development mode is indicated by reload=True, which enables
        auto-reload on code changes and other development conveniences.
        
        Returns:
            True if in development mode, False otherwise
            
        Example:
            if settings.is_development_mode():
                print("Running in development mode")
                # Enable additional debugging features
        """
        return self.reload


# ==================== Module-Level Singleton ====================

# Global settings instance - import this in other modules
# Example: from mcp_servers.playwright_mcp.config import settings
settings = PlaywrightMCPSettings()
