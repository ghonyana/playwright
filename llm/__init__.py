"""
LLM Integration Package for Test Automation Framework

This package provides a unified interface for integrating Large Language Models (LLMs)
into the test automation framework, enabling AI-assisted test scenario generation,
edge case discovery, and automated Gherkin feature authoring.

Key Capabilities:
- Business-readable Gherkin scenario generation from browser exploration logs
- Comprehensive edge case suggestion for existing test scenarios
- Support for multiple LLM providers (Ollama local, OpenAI hosted)
- Environment-based provider configuration for flexible deployment
- Production-ready test authoring with human review workflow

Module Structure:
    llm.client: Abstract LLMClient interface and factory function
    llm.providers.ollama: Local, cost-free LLM execution with privacy focus
    llm.providers.openai: Hosted LLM service with superior quality generation
    llm.prompts: Prompt templates for Gherkin generation and edge case discovery
    llm.workflows: End-to-end workflows for test scenario creation and review

Usage Examples:

    Example 1: Get configured LLM client (environment-driven provider selection)
    >>> from llm import get_llm_client
    >>> 
    >>> # Factory selects provider based on LLM_PROVIDER env var
    >>> # Returns OllamaProvider if LLM_PROVIDER='ollama' (default)
    >>> # Returns OpenAIProvider if LLM_PROVIDER='openai'
    >>> client = get_llm_client()
    >>> 
    >>> # Generate Gherkin from exploration log
    >>> exploration_log = '''
    >>> {
    >>>     "session_id": "test-abc123",
    >>>     "events": [
    >>>         {"action": "navigate", "url": "/login"},
    >>>         {"action": "type", "selector": "input[name='email']", "text": "user@example.com"},
    >>>         {"action": "click", "selector": "button[type='submit']"},
    >>>         {"action": "assert", "type": "url_contains", "expected": "/dashboard"}
    >>>     ]
    >>> }
    >>> '''
    >>> feature = client.generate_gherkin(exploration_log)
    >>> print(feature)
    >>> # Outputs business-readable Gherkin feature file

    Example 2: Suggest edge cases for existing scenario
    >>> from llm import get_llm_client
    >>> 
    >>> client = get_llm_client()
    >>> scenario = '''
    >>> Scenario: User creates account
    >>>   Given the user is on the registration page
    >>>   When the user fills in the registration form
    >>>   And the user submits the form
    >>>   Then a new account should be created
    >>> '''
    >>> edge_cases = client.suggest_edge_cases(scenario)
    >>> for case in edge_cases:
    >>>     print(f"- {case}")
    >>> # Outputs 8-12 specific edge case suggestions

    Example 3: Explicit provider instantiation (bypassing factory)
    >>> from llm import OllamaProvider, OpenAIProvider
    >>> 
    >>> # Use local Ollama for development (no API key needed)
    >>> local_provider = OllamaProvider(model="mistral")
    >>> 
    >>> # Use OpenAI for production quality (requires API key)
    >>> import os
    >>> os.environ['LLM_API_KEY'] = 'sk-proj-...'
    >>> hosted_provider = OpenAIProvider(model="gpt-4")
    >>> 
    >>> # Both implement the same LLMClient interface
    >>> feature1 = local_provider.generate_gherkin(exploration_log)
    >>> feature2 = hosted_provider.generate_gherkin(exploration_log)

Environment Configuration:
    LLM_PROVIDER: Provider selection - 'ollama' or 'openai' (default: 'ollama')
        Controls which provider the get_llm_client() factory returns
        
    LLM_MODEL: Model identifier specific to chosen provider
        Ollama options: llama2, llama2:13b, mistral, codellama, mixtral
        OpenAI options: gpt-4, gpt-4-turbo, gpt-3.5-turbo
        Defaults:
            - Ollama: 'llama2'
            - OpenAI: 'gpt-4'
    
    LLM_API_KEY: Authentication token for hosted provider
        Required for: OpenAI provider
        Optional for: Ollama (local instance typically has no auth)
    
    LLM_BASE_URL: Custom API endpoint URL
        Use cases:
            - Self-hosted Ollama on non-default port
            - Azure OpenAI endpoints
            - OpenAI-compatible services (Anthropic, Together.ai)
        Defaults:
            - Ollama: 'http://localhost:11434'
            - OpenAI: 'https://api.openai.com/v1'

Integration Points:
    - Playwright MCP Server: Provides exploration logs for Gherkin generation
    - FastAPI MCP Server: Uses generated scenarios for test data preparation
    - Test Step Definitions: Generated Gherkin scenarios guide step implementation
    - CI/CD Workflows: Automated scenario generation in test pipeline
    - Developer Scripts: Interactive test authoring with LLM assistance

Architecture Notes:
    This package follows the Strategy pattern, where:
    - LLMClient is the abstract strategy interface
    - OllamaProvider and OpenAIProvider are concrete strategy implementations
    - get_llm_client() factory acts as the context selector
    
    Benefits:
    - Test code depends on LLMClient abstraction, not specific providers
    - Provider can be swapped via environment configuration without code changes
    - New providers can be added by implementing LLMClient interface
    - Unit tests can mock LLMClient for deterministic testing

Best Practices:
    1. Use get_llm_client() factory for environment-driven provider selection
    2. Default to Ollama for local development (no API costs, privacy-focused)
    3. Use OpenAI for CI/CD and production (consistent quality)
    4. Always review LLM-generated scenarios before committing to test suite
    5. Store approved scenarios in tests/features/ with metadata tracking
    6. Use edge case suggestions as input for comprehensive test planning
    7. Configure retry logic and timeout handling for production reliability

Prerequisites:
    Ollama Provider:
        1. Install Ollama: https://ollama.ai
        2. Pull desired model: ollama pull llama2
        3. Verify running: curl http://localhost:11434/api/tags
    
    OpenAI Provider:
        1. Obtain API key: https://platform.openai.com/api-keys
        2. Set environment: export LLM_API_KEY=sk-proj-...
        3. Install package: pip install openai

See Also:
    - docs/llm_integration.md: Comprehensive LLM integration guide
    - llm/workflows/scenario_generator.py: End-to-end scenario generation workflow
    - llm/workflows/review_pipeline.py: Human review workflow for LLM output
    - tests/features/: Directory containing approved Gherkin scenarios
"""

# Import abstract interface and factory function from client module
from llm.client import LLMClient, get_llm_client

# Import concrete provider implementations
from llm.providers.ollama import OllamaProvider
from llm.providers.openai import OpenAIProvider

# Define public API for clean namespace management
# These are the only symbols that will be exported when using "from llm import *"
__all__ = [
    # Abstract interface (for type hints and custom implementations)
    "LLMClient",
    
    # Factory function (recommended entry point for provider-agnostic code)
    "get_llm_client",
    
    # Concrete providers (for explicit provider selection when needed)
    "OllamaProvider",
    "OpenAIProvider",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "Test Automation Framework Team"
__description__ = "LLM integration for AI-assisted test scenario generation"
