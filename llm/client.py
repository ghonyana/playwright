"""
Abstract LLM Client Interface for Test Automation Framework

This module provides an abstract interface for integrating Large Language Models (LLMs)
into the test automation framework. It enables LLM-assisted test scenario generation
from browser exploration logs and edge case discovery for existing scenarios.

The module supports multiple LLM providers through a factory pattern:
- Ollama: Local, cost-free LLM execution (default)
- OpenAI: Hosted LLM service with superior quality (requires API key)

Key Features:
- Abstract interface ensuring consistent provider implementation
- Environment-based configuration for flexible deployment
- Factory function for dynamic provider selection
- Business-readable Gherkin scenario generation
- Edge case suggestion for comprehensive test coverage

Environment Variables:
    LLM_PROVIDER: 'ollama' for local or 'openai' for hosted (default: 'ollama')
    LLM_MODEL: Model name (default: 'llama2' for Ollama, 'gpt-4' for OpenAI)
    LLM_API_KEY: Required for OpenAI provider, optional for Ollama
    LLM_BASE_URL: Optional custom endpoint (Ollama default: http://localhost:11434)

Usage Example:
    >>> from llm.client import get_llm_client
    >>> 
    >>> # Get configured LLM client
    >>> client = get_llm_client()
    >>> 
    >>> # Generate Gherkin from exploration log
    >>> exploration_log = '''{"events": [{"action": "navigate", "url": "/login"}]}'''
    >>> feature = client.generate_gherkin(exploration_log)
    >>> print(feature)
    >>> 
    >>> # Suggest edge cases for existing scenario
    >>> scenario = '''
    >>> Scenario: User logs in successfully
    >>>   Given the user is on the login page
    >>>   When the user enters valid credentials
    >>>   Then the user should see the dashboard
    >>> '''
    >>> edge_cases = client.suggest_edge_cases(scenario)
    >>> for case in edge_cases:
    >>>     print(f"- {case}")

Architecture Note:
    This module follows the Strategy pattern, where LLMClient is the abstract strategy
    and specific providers (OllamaProvider, OpenAIProvider) are concrete strategies.
    The get_llm_client() factory function acts as the context selector, choosing
    the appropriate strategy based on runtime configuration.

Integration Points:
    - llm/workflows/scenario_generator.py: Uses generate_gherkin() for scenario creation
    - llm/workflows/review_pipeline.py: Uses suggest_edge_cases() for test enhancement
    - Test development scripts: Interactive scenario authoring with LLM assistance
"""

from abc import ABC, abstractmethod
import os
from typing import List, Optional


class LLMClient(ABC):
    """
    Abstract base class for LLM client implementations.
    
    This interface defines the contract that all LLM provider implementations must follow,
    ensuring consistent behavior across different LLM backends (Ollama, OpenAI, etc.).
    
    The interface focuses on two primary use cases:
    1. Generating business-readable Gherkin scenarios from browser exploration logs
    2. Suggesting edge cases and test variations for existing scenarios
    
    Concrete implementations must override all abstract methods and handle provider-specific
    details such as API authentication, request formatting, and response parsing.
    
    Attributes:
        model (str): The LLM model identifier (e.g., 'llama2', 'gpt-4', 'gpt-3.5-turbo')
        base_url (Optional[str]): Custom API endpoint URL, if different from provider default
    """
    
    def __init__(self, model: str, base_url: Optional[str] = None):
        """
        Initialize the LLM client with model configuration.
        
        Args:
            model: The LLM model identifier to use for generation tasks
            base_url: Optional custom API endpoint URL for self-hosted or alternative endpoints
        """
        self.model = model
        self.base_url = base_url
    
    @abstractmethod
    def generate_gherkin(self, exploration_log: str) -> str:
        """
        Generate business-readable Gherkin scenario from browser exploration log.
        
        This method converts low-level browser automation events (navigate, click, type, assert)
        into high-level, business-readable Gherkin scenarios that non-technical stakeholders
        can understand and validate.
        
        The generated Gherkin must follow best practices:
        - High-level steps focused on business actions, not UI implementation details
        - Clear Given/When/Then structure following BDD principles
        - Appropriate tags for test categorization (@smoke, @api, @ui, @regression)
        - Business domain language, avoiding technical jargon
        
        Args:
            exploration_log: JSON string containing Playwright MCP exploration session data.
                Structure:
                {
                    "session_id": "unique-session-id",
                    "start_time": "2024-01-15T10:30:00Z",
                    "events": [
                        {
                            "action": "navigate",
                            "url": "https://example.com/login",
                            "timestamp": "2024-01-15T10:30:01Z"
                        },
                        {
                            "action": "type",
                            "selector": "input[name='username']",
                            "text": "testuser@example.com",
                            "timestamp": "2024-01-15T10:30:05Z"
                        },
                        {
                            "action": "click",
                            "selector": "button[type='submit']",
                            "timestamp": "2024-01-15T10:30:10Z"
                        },
                        {
                            "action": "assert",
                            "type": "url_contains",
                            "expected": "/dashboard",
                            "timestamp": "2024-01-15T10:30:12Z"
                        }
                    ]
                }
        
        Returns:
            Gherkin feature text with complete Feature and Scenario structure.
            Example:
                '''
                Feature: User Authentication
                  As a registered user
                  I want to log into my account
                  So that I can access my personalized dashboard
                
                @smoke @ui @authentication
                Scenario: Successful login with valid credentials
                  Given the user is on the login page
                  When the user enters valid credentials
                  And the user clicks the login button
                  Then the user should be redirected to the dashboard
                  And the user should see a welcome message
                '''
        
        Raises:
            ValueError: If exploration_log is empty, malformed JSON, or missing required fields
            ConnectionError: If LLM provider API is unreachable
            TimeoutError: If LLM generation exceeds configured timeout
        
        Implementation Notes:
            - Implementations should include retry logic for transient API failures
            - Consider token limits and truncate exploration logs if necessary
            - Cache frequently used prompts to optimize performance
            - Validate generated Gherkin syntax before returning
        """
        pass
    
    @abstractmethod
    def suggest_edge_cases(self, scenario: str) -> List[str]:
        """
        Suggest edge cases and test variations for existing Gherkin scenario.
        
        This method analyzes a Gherkin scenario and suggests additional test cases that cover:
        - Boundary conditions (empty inputs, maximum lengths, special characters)
        - Error scenarios (invalid data, network failures, permission errors)
        - Alternative flows (different user roles, optional steps, concurrent actions)
        - Data variations (internationalization, different formats, edge data types)
        
        The suggestions help testers achieve comprehensive test coverage by identifying
        scenarios they might not have considered during initial test design.
        
        Args:
            scenario: Existing Gherkin scenario text to analyze.
                Example:
                    '''
                    Scenario: User creates a new account
                      Given the user is on the registration page
                      When the user fills in the registration form with valid data
                      And the user submits the form
                      Then a new account should be created
                      And the user should receive a confirmation email
                    '''
        
        Returns:
            List of human-readable edge case descriptions that should be considered
            for testing. Each description focuses on a specific variation or risk.
            Example:
                [
                    "Test registration with email address exceeding maximum length (320 characters)",
                    "Test registration with already-registered email address",
                    "Test registration with special characters in username (unicode, emoji)",
                    "Test registration when email service is unavailable",
                    "Test concurrent registrations with the same email address",
                    "Test registration with SQL injection attempts in input fields",
                    "Test registration with internationalized domain names (IDN)",
                    "Test registration with disabled JavaScript in browser"
                ]
        
        Raises:
            ValueError: If scenario is empty, not valid Gherkin, or missing required structure
            ConnectionError: If LLM provider API is unreachable
            TimeoutError: If suggestion generation exceeds configured timeout
        
        Implementation Notes:
            - Implementations should parse the scenario to understand business context
            - Consider domain-specific edge cases based on scenario tags
            - Prioritize suggestions by risk/impact (security, data integrity, UX)
            - Deduplicate suggestions to avoid redundant test cases
            - Format suggestions as actionable test scenario descriptions
        """
        pass


def get_llm_client() -> LLMClient:
    """
    Factory function for creating LLM client instances based on environment configuration.
    
    This function implements the Factory pattern, selecting and instantiating the appropriate
    LLM provider based on runtime configuration. It encapsulates provider-specific logic
    and provides a single entry point for LLM client creation throughout the codebase.
    
    The factory supports two primary providers:
    1. Ollama: Local LLM execution for cost-free, privacy-focused development
       - Default choice for local development and CI environments
       - No API key required
       - Supports models like llama2, mistral, codellama
       - Requires Ollama server running (default: http://localhost:11434)
    
    2. OpenAI: Hosted LLM service for production-grade quality
       - Superior generation quality and reasoning capabilities
       - Requires paid API key
       - Supports models like gpt-4, gpt-3.5-turbo, gpt-4-turbo
       - Can be configured for OpenAI-compatible endpoints (Azure, Anthropic)
    
    Environment Variables:
        LLM_PROVIDER (str): Provider selection - 'ollama' or 'openai'
            Default: 'ollama'
            Example: export LLM_PROVIDER=openai
        
        LLM_MODEL (str): Model identifier specific to chosen provider
            Defaults:
                - Ollama: 'llama2'
                - OpenAI: 'gpt-4'
            Examples:
                - export LLM_MODEL=llama2:13b
                - export LLM_MODEL=gpt-3.5-turbo
        
        LLM_API_KEY (str): Authentication token for provider API
            Required for: OpenAI provider
            Optional for: Ollama (typically no auth for local instance)
            Example: export LLM_API_KEY=sk-proj-...
        
        LLM_BASE_URL (str): Custom API endpoint URL
            Use cases:
                - Self-hosted Ollama on non-default port
                - Azure OpenAI endpoints
                - OpenAI-compatible services (Anthropic, Together.ai)
            Examples:
                - export LLM_BASE_URL=http://ollama-server:11434
                - export LLM_BASE_URL=https://api.anthropic.com/v1
    
    Returns:
        LLMClient: Configured instance of OllamaProvider or OpenAIProvider
        
    Raises:
        ValueError: In the following cases:
            - LLM_PROVIDER is not 'ollama' or 'openai'
            - LLM_API_KEY is missing when LLM_PROVIDER is 'openai'
            - LLM_MODEL is explicitly set to empty string
        ImportError: If provider-specific dependencies are not installed
            - ollama package required for OllamaProvider
            - openai package required for OpenAIProvider
    
    Usage Examples:
        >>> # Example 1: Local development with Ollama (default)
        >>> import os
        >>> os.environ['LLM_PROVIDER'] = 'ollama'
        >>> os.environ['LLM_MODEL'] = 'llama2'
        >>> client = get_llm_client()
        >>> # Returns OllamaProvider instance
        
        >>> # Example 2: Production with OpenAI
        >>> os.environ['LLM_PROVIDER'] = 'openai'
        >>> os.environ['LLM_MODEL'] = 'gpt-4'
        >>> os.environ['LLM_API_KEY'] = 'sk-proj-...'
        >>> client = get_llm_client()
        >>> # Returns OpenAIProvider instance
        
        >>> # Example 3: Azure OpenAI
        >>> os.environ['LLM_PROVIDER'] = 'openai'
        >>> os.environ['LLM_BASE_URL'] = 'https://my-resource.openai.azure.com/openai/deployments/gpt-4'
        >>> os.environ['LLM_API_KEY'] = 'azure-key-...'
        >>> client = get_llm_client()
        >>> # Returns OpenAIProvider configured for Azure
    
    Implementation Notes:
        - Provider imports are lazy-loaded to avoid unnecessary dependencies
        - Configuration validation happens at runtime, not import time
        - Provider-specific defaults are handled by provider classes
        - Thread-safe for concurrent factory calls
    """
    # Read provider configuration from environment
    provider = os.getenv("LLM_PROVIDER", "ollama").lower().strip()
    model = os.getenv("LLM_MODEL")
    base_url = os.getenv("LLM_BASE_URL")
    
    # Validate provider selection
    if provider not in ("ollama", "openai"):
        raise ValueError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Valid options are 'ollama' (local, free) or 'openai' (hosted, paid). "
            f"Set LLM_PROVIDER environment variable to one of these values."
        )
    
    # Ollama provider (local, cost-free)
    if provider == "ollama":
        try:
            from llm.providers.ollama import OllamaProvider
        except ImportError as e:
            raise ImportError(
                "OllamaProvider requires 'ollama' package. "
                "Install with: pip install ollama"
            ) from e
        
        # Use provider-specific default model if not specified
        effective_model = model or "llama2"
        
        return OllamaProvider(
            model=effective_model,
            base_url=base_url  # Will use provider default if None
        )
    
    # OpenAI provider (hosted, requires API key)
    elif provider == "openai":
        try:
            from llm.providers.openai import OpenAIProvider
        except ImportError as e:
            raise ImportError(
                "OpenAIProvider requires 'openai' package. "
                "Install with: pip install openai"
            ) from e
        
        # Validate required API key
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise ValueError(
                "LLM_API_KEY environment variable is required when using OpenAI provider. "
                "Obtain an API key from https://platform.openai.com/api-keys and set it: "
                "export LLM_API_KEY=sk-proj-..."
            )
        
        # Use provider-specific default model if not specified
        effective_model = model or "gpt-4"
        
        return OpenAIProvider(
            model=effective_model,
            api_key=api_key,
            base_url=base_url  # Will use provider default if None
        )
