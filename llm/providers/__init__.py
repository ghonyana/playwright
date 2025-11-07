"""
LLM Providers Module for Test Automation Framework

This package contains concrete implementations of the LLMClient abstract interface,
enabling flexible LLM provider switching via environment configuration. The framework
supports both local (Ollama) and hosted (OpenAI) LLM execution for test scenario
generation and edge case discovery.

Available Providers:
-------------------
- OllamaProvider: Local LLM execution for cost-free, privacy-sensitive test generation
  * No API costs for unlimited Gherkin scenario generation
  * All data stays on local infrastructure (privacy-compliant)
  * No internet dependency after model download (offline development)
  * Supported models: llama2, mistral, codellama, mixtral, and others
  * Ideal for: Development, CI/CD, privacy-sensitive environments

- OpenAIProvider: Hosted API for superior quality test generation
  * High-quality Gherkin scenarios using GPT-4/GPT-3.5-turbo
  * Advanced reasoning for comprehensive edge case discovery
  * Consistent, production-ready output quality
  * OpenAI-compatible endpoints supported (Azure OpenAI, Anthropic)
  * Ideal for: Production test authoring, complex scenario generation

Architecture Overview:
---------------------
The provider pattern enables runtime selection of LLM implementation based on
environment configuration without changing test code. Both providers implement
the LLMClient abstract interface with two primary methods:

1. generate_gherkin(exploration_log: str) -> str
   Converts browser exploration logs from Playwright MCP server into business-readable
   Gherkin scenarios following BDD best practices

2. suggest_edge_cases(scenario: str) -> List[str]
   Analyzes existing test scenarios to suggest comprehensive edge cases covering
   boundary conditions, security vulnerabilities, and failure modes

Factory Pattern Integration:
---------------------------
The llm/client.py module provides a factory function that dynamically selects the
appropriate provider based on the LLM_PROVIDER environment variable:

    from llm.client import get_llm_client
    
    # Returns OllamaProvider or OpenAIProvider based on LLM_PROVIDER env var
    client = get_llm_client()
    
    # Generate Gherkin from exploration
    gherkin = client.generate_gherkin(exploration_log)
    
    # Suggest edge cases for scenario
    edge_cases = client.suggest_edge_cases(scenario_text)

Direct Import Usage:
-------------------
For explicit provider selection, import directly from this package:

    # Local LLM execution (Ollama)
    from llm.providers import OllamaProvider
    provider = OllamaProvider(model="mistral")
    
    # Hosted API execution (OpenAI)
    from llm.providers import OpenAIProvider
    provider = OpenAIProvider(model="gpt-4", api_key="sk-proj-...")

Environment Configuration:
-------------------------
Provider selection and configuration via environment variables:

LLM_PROVIDER (determines which provider to use):
    - 'ollama': Use local Ollama execution (default)
    - 'openai': Use hosted OpenAI API

For OllamaProvider:
    LLM_MODEL: Model name (default: 'llama2')
        Options: llama2, llama2:13b, mistral, codellama, mixtral
    LLM_BASE_URL: Ollama server endpoint (default: 'http://localhost:11434')

For OpenAIProvider:
    LLM_MODEL: Model name (default: 'gpt-4')
        Options: gpt-4, gpt-4-turbo, gpt-3.5-turbo, claude-3-opus
    LLM_API_KEY: API key for authentication (REQUIRED)
    LLM_BASE_URL: Custom endpoint for Azure OpenAI or Anthropic (optional)

Example Configurations:
----------------------

Development with Local Ollama:
    export LLM_PROVIDER=ollama
    export LLM_MODEL=mistral
    export LLM_BASE_URL=http://localhost:11434

Production with OpenAI:
    export LLM_PROVIDER=openai
    export LLM_MODEL=gpt-4
    export LLM_API_KEY=sk-proj-1234567890abcdef...

CI/CD with Cost Optimization:
    export LLM_PROVIDER=openai
    export LLM_MODEL=gpt-3.5-turbo  # Lower cost alternative
    export LLM_API_KEY=${{ secrets.OPENAI_API_KEY }}

Integration Points:
------------------
This package integrates with the following framework components:

1. llm/client.py
   - get_llm_client() factory function imports providers from this package
   - LLMClient abstract base class defines interface contract
   - Provider selection logic based on LLM_PROVIDER environment variable

2. llm/workflows/scenario_generator.py
   - Uses generate_gherkin() to create .feature files from browser exploration
   - Converts low-level Playwright events into high-level Gherkin scenarios
   - Writes generated scenarios to tests/features/ directory

3. llm/workflows/review_pipeline.py
   - Uses suggest_edge_cases() to enhance test coverage
   - Presents LLM suggestions for human review and approval
   - Generates additional test scenarios based on approved edge cases

4. mcp_servers/playwright_mcp/gherkin/generator.py
   - Calls generate_gherkin() with exploration session logs
   - Provides structured JSON exploration data to LLM
   - Implements Gherkin validation and formatting

Usage Examples:
--------------

Example 1: Generate Gherkin from Exploration Log
    from llm.providers import OllamaProvider
    
    provider = OllamaProvider()
    
    exploration_log = '''
    {
        "session_id": "test-123",
        "events": [
            {"action": "navigate", "url": "/login"},
            {"action": "type", "selector": "input[name='email']", 
             "text": "user@example.com"},
            {"action": "type", "selector": "input[name='password']", 
             "text": "password123"},
            {"action": "click", "selector": "button[type='submit']"},
            {"action": "assert", "type": "url_contains", "expected": "/dashboard"}
        ]
    }
    '''
    
    feature = provider.generate_gherkin(exploration_log)
    print(feature)
    # Output:
    # Feature: User Authentication
    #   As a registered user
    #   I want to log in to the application
    #   So that I can access my dashboard
    # 
    #   @smoke @ui
    #   Scenario: Successful login with valid credentials
    #     Given the user is on the login page
    #     When the user enters valid credentials
    #     And the user submits the login form
    #     Then the user is redirected to the dashboard

Example 2: Suggest Edge Cases for Existing Scenario
    from llm.providers import OpenAIProvider
    
    provider = OpenAIProvider(api_key="sk-proj-...")
    
    scenario = '''
    Feature: User Registration
      Scenario: User creates new account
        Given the user is on the registration page
        When the user fills in the registration form
        And the user submits the form
        Then a new account should be created
    '''
    
    edge_cases = provider.suggest_edge_cases(scenario)
    for case in edge_cases:
        print(f"- {case}")
    # Output:
    # - Test registration with email exceeding 255 characters
    # - Test registration with SQL injection in username field
    # - Test concurrent registrations with same email
    # - Test registration with XSS payload in name field
    # - Test registration when email service returns HTTP 503
    # ...

Example 3: Factory Pattern with Environment Configuration
    import os
    from llm.client import get_llm_client
    
    # Set provider via environment
    os.environ['LLM_PROVIDER'] = 'ollama'
    os.environ['LLM_MODEL'] = 'mistral'
    
    # Factory returns appropriate provider
    client = get_llm_client()
    print(type(client))  # <class 'llm.providers.ollama.OllamaProvider'>
    
    # Use provider transparently
    gherkin = client.generate_gherkin(exploration_log)

Best Practices:
--------------
1. Use factory pattern (get_llm_client) for production code
   - Enables easy provider switching via environment variables
   - Maintains consistent interface across provider implementations
   - Simplifies testing with provider mocks

2. Use direct imports only for explicit provider requirements
   - When specific provider features are needed (e.g., Ollama's offline mode)
   - For provider-specific testing or benchmarking
   - When implementing custom provider configurations

3. Validate generated Gherkin before committing
   - Parse with pytest-bdd to ensure syntax correctness
   - Review for business readability and accuracy
   - Verify steps align with existing step definitions

4. Handle LLM failures gracefully
   - Implement retry logic for transient API failures
   - Provide fallback mechanisms for offline scenarios
   - Log LLM responses for debugging and quality assurance

5. Optimize for cost and performance
   - Use gpt-3.5-turbo for development/testing (lower cost)
   - Use gpt-4 for production scenario generation (higher quality)
   - Use Ollama for unlimited local development and CI/CD

Security Considerations:
-----------------------
- Never commit LLM_API_KEY to version control
- Store API keys in secure environment variables or secrets management
- Mask API keys in logs and error messages (OpenAIProvider does this automatically)
- Validate and sanitize LLM-generated output before execution
- Implement rate limiting to prevent API quota exhaustion
- Use least-privilege API keys with minimal scopes

Module Exports:
--------------
This package exports two concrete LLM provider implementations:

- OllamaProvider: Local LLM execution via Ollama
- OpenAIProvider: Hosted API execution via OpenAI-compatible endpoints

Both classes are available for direct import:
    from llm.providers import OllamaProvider, OpenAIProvider

Or via factory pattern:
    from llm.client import get_llm_client
"""

# Import concrete provider implementations from submodules
from llm.providers.ollama import OllamaProvider
from llm.providers.openai import OpenAIProvider

# Export provider classes for external use
# This enables clean imports: from llm.providers import OllamaProvider, OpenAIProvider
__all__ = [
    "OllamaProvider",
    "OpenAIProvider",
]
