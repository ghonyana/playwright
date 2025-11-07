"""
OpenAI Provider Implementation for Test Automation LLM Integration

This module implements the OpenAIProvider class, a concrete implementation of the LLMClient
abstract interface for hosted OpenAI API access. It provides superior quality Gherkin scenario
generation and advanced edge case discovery compared to local LLM options.

Key Features:
- High-quality Gherkin generation using GPT-4 or GPT-3.5-turbo models
- Advanced reasoning for comprehensive edge case discovery
- Support for OpenAI API and OpenAI-compatible endpoints (Azure OpenAI, Anthropic)
- Production-ready test scenario authoring with consistent output quality
- Comprehensive error handling and validation

Supported Providers:
- OpenAI (GPT-4, GPT-4-turbo, GPT-3.5-turbo)
- Azure OpenAI (custom deployment endpoints)
- Anthropic Claude (via OpenAI-compatible API)
- Other OpenAI-compatible services

Environment Configuration:
    LLM_MODEL: Model name (default: 'gpt-4')
        Options: gpt-4, gpt-4-turbo, gpt-3.5-turbo, claude-3-opus
    LLM_API_KEY: API key for authentication (REQUIRED)
    LLM_BASE_URL: Custom API endpoint (optional)
        Default: https://api.openai.com/v1
        Azure: https://<resource>.openai.azure.com/openai/deployments/<deployment>
        Anthropic: https://api.anthropic.com/v1

Usage Example:
    >>> import os
    >>> os.environ['LLM_API_KEY'] = 'sk-proj-...'
    >>> os.environ['LLM_MODEL'] = 'gpt-4'
    >>> 
    >>> from llm.providers.openai import OpenAIProvider
    >>> provider = OpenAIProvider()
    >>> 
    >>> # Generate Gherkin from exploration log
    >>> exploration = '''{"events": [{"action": "navigate", "url": "/login"}]}'''
    >>> feature = provider.generate_gherkin(exploration)
    >>> print(feature)
    >>> 
    >>> # Suggest edge cases for scenario
    >>> scenario = '''
    >>> Scenario: User login
    >>>   Given the user is on the login page
    >>>   When the user enters credentials
    >>>   Then the user should see the dashboard
    >>> '''
    >>> edge_cases = provider.suggest_edge_cases(scenario)
    >>> for case in edge_cases:
    >>>     print(f"- {case}")

Integration Points:
- Inherits from llm.client.LLMClient abstract interface
- Used by llm.client.get_llm_client() factory when LLM_PROVIDER='openai'
- Called by llm.workflows.scenario_generator for Gherkin generation
- Called by llm.workflows.review_pipeline for edge case discovery

Architecture Notes:
- Implements Strategy pattern as concrete strategy for LLM operations
- Uses OpenAI Chat Completions API for all generation tasks
- Follows BDD best practices in prompt engineering
- Provides deterministic, business-readable test scenario output
"""

import os
import re
from typing import List

from openai import OpenAI

from llm.client import LLMClient


class OpenAIProvider(LLMClient):
    """
    Hosted OpenAI LLM client for superior test scenario generation quality.
    
    This provider leverages OpenAI's GPT-4 and GPT-3.5-turbo models to generate
    high-quality, business-readable Gherkin scenarios from browser exploration logs
    and suggest comprehensive edge cases for existing test scenarios.
    
    Advantages over local LLMs:
    - Superior reasoning capabilities for complex scenario analysis
    - Consistent, production-ready output quality
    - Advanced edge case discovery with security focus
    - Support for latest GPT-4 capabilities and instruction following
    
    Attributes:
        model (str): OpenAI model identifier (e.g., 'gpt-4', 'gpt-3.5-turbo')
        api_key (str): OpenAI API authentication key
        base_url (str): API endpoint URL (for OpenAI-compatible services)
        client (OpenAI): Configured OpenAI client instance
    
    Environment Variables:
        LLM_MODEL: Model name (default: 'gpt-4')
        LLM_API_KEY: API key (REQUIRED)
        LLM_BASE_URL: Custom endpoint (optional)
    
    Raises:
        ValueError: If LLM_API_KEY is not provided
        RuntimeError: If API calls fail or return invalid responses
    """
    
    def __init__(self, model: str = None, api_key: str = None, base_url: str = None):
        """
        Initialize OpenAI provider with authentication and configuration.
        
        Args:
            model: Model name (defaults to LLM_MODEL env var or 'gpt-4')
                Options: gpt-4, gpt-4-turbo, gpt-3.5-turbo, claude-3-opus
            api_key: API key (defaults to LLM_API_KEY env var, REQUIRED)
            base_url: API endpoint (defaults to LLM_BASE_URL env var or OpenAI default)
                Use for Azure OpenAI or Anthropic endpoints
        
        Raises:
            ValueError: If API key is not provided via parameter or environment variable
        
        Example:
            >>> # Using environment variables (recommended)
            >>> import os
            >>> os.environ['LLM_API_KEY'] = 'sk-proj-...'
            >>> provider = OpenAIProvider()
            >>> 
            >>> # Explicit configuration
            >>> provider = OpenAIProvider(
            ...     model='gpt-4-turbo',
            ...     api_key='sk-proj-...',
            ...     base_url='https://api.openai.com/v1'
            ... )
        """
        # Resolve configuration from parameters or environment variables
        self.model = model or os.getenv("LLM_MODEL", "gpt-4")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        
        # Validate required API key
        if not self.api_key:
            raise ValueError(
                "LLM_API_KEY environment variable required for OpenAI provider. "
                "Obtain an API key from https://platform.openai.com/api-keys and set it: "
                "export LLM_API_KEY=sk-proj-..."
            )
        
        # Initialize OpenAI client with configuration
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        self.client = OpenAI(**client_kwargs)
        
        # Call parent constructor with base configuration
        super().__init__(model=self.model, base_url=self.base_url)
    
    def generate_gherkin(self, exploration_log: str) -> str:
        """
        Generate business-readable Gherkin scenario from browser exploration log using GPT-4.
        
        This method leverages OpenAI's advanced language understanding to convert low-level
        browser automation events (navigate, click, type, assertions) into high-level,
        business-readable Gherkin scenarios that non-technical stakeholders can understand.
        
        The generated Gherkin follows BDD best practices:
        - High-level steps focused on business actions, not UI implementation details
        - Clear Given/When/Then structure
        - Appropriate tags (@smoke, @api, @ui, @regression)
        - Business domain language, avoiding technical jargon
        
        Args:
            exploration_log: JSON string containing Playwright MCP exploration session data
                with navigation events, clicks, form fills, and assertions.
                
                Example structure:
                {
                    "session_id": "abc123",
                    "start_time": "2024-01-15T10:30:00Z",
                    "events": [
                        {"action": "navigate", "url": "/login", "timestamp": "..."},
                        {"action": "type", "selector": "input[name='username']", 
                         "text": "user@example.com", "timestamp": "..."},
                        {"action": "click", "selector": "button[type='submit']", 
                         "timestamp": "..."},
                        {"action": "assert", "type": "url_contains", 
                         "expected": "/dashboard", "timestamp": "..."}
                    ]
                }
        
        Returns:
            Gherkin feature text with complete Feature and Scenario structure.
            
            Example:
                Feature: User Authentication
                  As a registered user
                  I want to log in to the application
                  So that I can access my account and protected resources
                  
                  @smoke @ui
                  Scenario: Successful login with valid credentials
                    Given the user is on the login page
                    And a user with role "customer" exists
                    When the user logs in with valid credentials
                    Then the user is redirected to the dashboard
                    And the user sees a personalized welcome message
        
        Raises:
            RuntimeError: If OpenAI API call fails or returns invalid response
        
        Example:
            >>> provider = OpenAIProvider(api_key="sk-proj-...")
            >>> log = '{\"actions\": [{\"type\": \"navigate\", \"url\": \"/login\"}, ...]}'
            >>> gherkin = provider.generate_gherkin(log)
            >>> print(gherkin)
        """
        try:
            # Call OpenAI Chat Completions API with specialized prompt
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert test automation engineer and BDD specialist.

Your expertise:
- Writing business-readable Gherkin scenarios for stakeholder communication
- Translating technical browser interactions into high-level behavioral steps
- Following BDD best practices (Given/When/Then pattern, declarative language)
- Creating maintainable test scenarios that focus on WHAT, not HOW

Guidelines:
1. Feature: Include business value statement (As a...I want...So that...)
2. Scenario: Clear, descriptive title from user perspective
3. Given: Preconditions and setup (use MCP tools like "a user with role X exists")
4. When: User actions at behavior level (avoid UI selectors/implementation)
5. Then: Expected outcomes and assertions (business-observable results)
6. Tags: @smoke for critical paths, @ui for browser tests, @api for API tests
7. Language: Business terminology, not technical jargon

Focus on creating high-level, maintainable scenarios that remain valid even if UI implementation changes."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze the following browser exploration log and generate a Gherkin scenario.

EXPLORATION LOG:
{exploration_log}

Generate a complete Gherkin feature with:
- Feature description with business value (As a...I want...So that...)
- One or more scenarios covering the observed behavior
- High-level Given/When/Then steps (no CSS selectors, no XPath, no implementation details)
- Appropriate tags for test categorization

Return ONLY the Gherkin text, no explanations or additional commentary."""
                    }
                ],
                temperature=0.7,  # Balanced creativity and consistency
                max_tokens=1500,
                top_p=0.9
            )
            
            # Extract generated Gherkin from response
            gherkin_text = response.choices[0].message.content.strip()
            
            return gherkin_text
        
        except Exception as e:
            error_msg = f"Error generating Gherkin with OpenAI: {e}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg) from e
    
    def suggest_edge_cases(self, scenario: str) -> List[str]:
        """
        Suggest edge cases and test variations using OpenAI's advanced reasoning capabilities.
        
        This method analyzes a Gherkin scenario and suggests comprehensive edge cases covering:
        - Boundary conditions (empty inputs, maximum lengths, special characters)
        - Security vulnerabilities (injection attacks, authentication bypass)
        - Error scenarios (timeouts, network failures, invalid states)
        - Data validation edge cases (format, encoding, type mismatches)
        - Concurrency issues (race conditions, simultaneous actions)
        - Business logic violations (expired states, permissions, limits)
        
        The suggestions help achieve comprehensive test coverage by identifying scenarios
        that testers might not consider during initial test design.
        
        Args:
            scenario: Existing Gherkin scenario text to analyze.
            
            Example:
                Feature: User Login
                  Scenario: Successful login
                    Given the user is on the login page
                    When the user enters valid credentials
                    Then the user is logged in
        
        Returns:
            List of 8-12 specific, actionable edge case descriptions.
            Each description is detailed enough for immediate test implementation.
            
            Example:
                [
                    'Test login with email exceeding maximum length (255+ chars)',
                    'Test login with SQL injection pattern in email field',
                    'Test login with account locked after 5 failed attempts',
                    'Test login with expired session token (24+ hours old)',
                    'Test concurrent login attempts from different devices',
                    'Test login with Unicode emoji in password (🔒🎉)',
                    'Test login after password reset with old password',
                    'Test login rate limiting (>10 attempts per minute)',
                    'Test login with empty email field',
                    'Test login with malformed email (missing @ symbol)',
                    'Test login when auth service returns HTTP 503',
                    'Test login with XSS payload in email field'
                ]
        
        Raises:
            RuntimeError: If OpenAI API call fails or response parsing fails
        
        Example:
            >>> provider = OpenAIProvider(api_key="sk-proj-...")
            >>> scenario = '''
            ... Feature: User Login
            ...   Scenario: Successful login
            ...     Given the user is on the login page
            ...     When the user enters valid credentials
            ...     Then the user is logged in
            ... '''
            >>> edge_cases = provider.suggest_edge_cases(scenario)
            >>> for case in edge_cases:
            ...     print(f"- {case}")
        """
        try:
            # Call OpenAI Chat Completions API with edge case discovery prompt
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a QA engineer specializing in edge case discovery, boundary testing, and security analysis.

Your expertise:
- Identifying edge cases and boundary conditions
- Security testing (injection attacks, authentication bypass, XSS, CSRF)
- Data validation and input sanitization testing
- Concurrency and race condition scenarios
- Error handling and failure mode analysis
- Negative testing and unhappy path scenarios
- Business logic edge cases and rule violations

Focus areas:
1. Boundary values (empty, null, maximum length, special characters, numeric limits)
2. Security vulnerabilities (SQL injection, XSS, CSRF, authentication issues, path traversal)
3. Error scenarios (timeouts, network failures, invalid states, service unavailability)
4. Data validation (format violations, encoding issues, type mismatches)
5. Concurrency (race conditions, simultaneous actions, resource locking)
6. Business logic (expired states, permissions, rate limits, quota exhaustion)

Be specific with concrete values (e.g., "255+ characters" not just "long input")."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze the following test scenario and suggest comprehensive edge cases.

SCENARIO:
{scenario}

Provide 8-12 specific edge cases that should be tested, covering:
- Boundary conditions and limits
- Security concerns
- Error scenarios
- Data validation edge cases
- Concurrent/race conditions if applicable
- Business rule violations

Format: Return ONLY a numbered list, one edge case per line.
Be specific with details (e.g., "maximum length of 255 chars" not just "long input").

Generate edge cases now:"""
                    }
                ],
                temperature=0.8,  # Higher creativity for diverse suggestions
                max_tokens=800,
                top_p=0.9
            )
            
            # Extract generated content
            content = response.choices[0].message.content.strip()
            
            # Parse numbered list into array
            edge_cases = []
            for line in content.split('\n'):
                line = line.strip()
                # Match lines starting with number and period/dash/bullet
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove numbering/bullets and clean up
                    clean_line = re.sub(r'^\d+\.\s*', '', line)
                    clean_line = re.sub(r'^[-•]\s*', '', clean_line)
                    if clean_line:
                        edge_cases.append(clean_line.strip())
            
            # If parsing failed, return raw lines as fallback
            if not edge_cases:
                edge_cases = [line.strip() for line in content.split('\n') if line.strip()]
            
            return edge_cases
        
        except Exception as e:
            error_msg = f"Error suggesting edge cases with OpenAI: {e}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg) from e
    
    def __repr__(self) -> str:
        """
        String representation for debugging (masks API key for security).
        
        Returns:
            String representation showing model, masked API key, and base URL.
            The API key is masked to show only first 8 and last 4 characters.
        
        Example:
            >>> provider = OpenAIProvider(api_key="sk-proj-1234567890abcdefghij")
            >>> print(repr(provider))
            OpenAIProvider(model='gpt-4', api_key='sk-proj-...ghij', base_url='default')
        """
        # Mask API key for security (show first 8 and last 4 chars)
        if self.api_key and len(self.api_key) > 12:
            masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}"
        elif self.api_key:
            masked_key = f"{self.api_key[:4]}..."
        else:
            masked_key = "None"
        
        # Display base URL or 'default' if using OpenAI default
        base_url_display = self.base_url if self.base_url else "default"
        
        return f"OpenAIProvider(model='{self.model}', api_key='{masked_key}', base_url='{base_url_display}')"


# Export the OpenAIProvider class for external use
__all__ = ["OpenAIProvider"]

