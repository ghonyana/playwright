"""
Ollama Provider Implementation for Local LLM Execution

This module implements the OllamaProvider class, which provides local, cost-free LLM execution
for test scenario generation without external API dependencies or internet connectivity.

Key Features:
- Privacy-sensitive: All data stays on local machine, no external API calls
- Cost-free: No API charges for test generation
- Offline operation: No internet dependency after model download
- Multiple model support: llama2, codellama, mistral, mixtral, and other Ollama models
- Business-readable Gherkin generation from browser exploration logs
- Edge case discovery for comprehensive test coverage

Environment Variables:
    LLM_MODEL: Ollama model name (default: 'llama2')
        Options: llama2, llama2:13b, codellama, mistral, mixtral, etc.
        Example: export LLM_MODEL=mistral
    
    LLM_BASE_URL: Ollama server endpoint (default: 'http://localhost:11434')
        Example: export LLM_BASE_URL=http://ollama-server:11434

Prerequisites:
    1. Install Ollama: https://ollama.ai
    2. Pull desired model: ollama pull llama2
    3. Verify Ollama is running: curl http://localhost:11434/api/tags

Usage Example:
    >>> from llm.providers.ollama import OllamaProvider
    >>> 
    >>> # Initialize provider with default configuration
    >>> provider = OllamaProvider()
    >>> 
    >>> # Generate Gherkin from exploration log
    >>> exploration_log = '''
    >>> {
    >>>     "session_id": "test-123",
    >>>     "events": [
    >>>         {"action": "navigate", "url": "/login"},
    >>>         {"action": "type", "selector": "input[name='email']", "text": "user@example.com"},
    >>>         {"action": "click", "selector": "button[type='submit']"}
    >>>     ]
    >>> }
    >>> '''
    >>> feature = provider.generate_gherkin(exploration_log)
    >>> print(feature)
    >>> 
    >>> # Suggest edge cases for existing scenario
    >>> scenario = '''
    >>> Scenario: User login
    >>>   Given the user is on the login page
    >>>   When the user enters valid credentials
    >>>   Then the user is redirected to the dashboard
    >>> '''
    >>> edge_cases = provider.suggest_edge_cases(scenario)
    >>> for case in edge_cases:
    >>>     print(f"- {case}")

Integration Points:
    - llm/client.py: Inherits from LLMClient abstract interface
    - llm/workflows/scenario_generator.py: Uses generate_gherkin() for scenario creation
    - llm/workflows/review_pipeline.py: Uses suggest_edge_cases() for test enhancement
    - get_llm_client() factory: Instantiated when LLM_PROVIDER='ollama'

Advantages over OpenAI Provider:
    - No API costs for unlimited test generation
    - Privacy-sensitive data stays on local infrastructure
    - No internet dependency for offline development
    - Customizable models for specific test authoring needs
"""

import os
import re
from typing import List

import ollama

from llm.client import LLMClient
from llm.prompts.edge_case_suggestions import ANALYZE_SCENARIO_PROMPT


class OllamaProvider(LLMClient):
    """
    Local Ollama LLM client for privacy-sensitive, cost-free test scenario generation.
    
    This provider connects to a local Ollama instance for LLM-powered test automation
    capabilities without requiring external API keys or incurring usage costs. It is
    ideal for:
    - Development and testing environments where privacy is paramount
    - CI/CD pipelines requiring reproducible test generation
    - Organizations with data privacy requirements
    - Cost-sensitive projects needing unlimited test generation
    
    The provider supports two primary operations:
    1. Gherkin scenario generation from browser exploration logs
    2. Edge case suggestion for existing test scenarios
    
    Environment Variables:
        LLM_MODEL: Ollama model name (default: 'llama2')
            Common options:
                - llama2: General purpose, 7B parameters (fastest)
                - llama2:13b: Better quality, 13B parameters
                - llama2:70b: Best quality, 70B parameters (slowest)
                - mistral: High performance, efficient
                - codellama: Code-optimized, good for technical scenarios
                - mixtral: Mixture of experts, excellent reasoning
        
        LLM_BASE_URL: Ollama server endpoint (default: 'http://localhost:11434')
            Use custom URL for:
                - Remote Ollama server: http://ollama-host:11434
                - Non-standard port: http://localhost:8080
                - Docker container: http://ollama-container:11434
    
    Attributes:
        model (str): The Ollama model name to use for generation
        base_url (str): The Ollama server endpoint URL
        client (ollama.Client): The initialized Ollama client instance
    
    Raises:
        RuntimeError: If Ollama server is unreachable or model is not available
        ValueError: If exploration log or scenario format is invalid
    """
    
    def __init__(self, model: str = None, base_url: str = None):
        """
        Initialize Ollama provider with model configuration.
        
        This constructor sets up the Ollama client connection and verifies that the
        specified model is available locally. If the model is not found, a warning
        is displayed with instructions to pull the model.
        
        Args:
            model: Ollama model name (defaults to LLM_MODEL env var or 'llama2')
                If None, reads from LLM_MODEL environment variable
                If LLM_MODEL is not set, defaults to 'llama2'
            base_url: Ollama server URL (defaults to LLM_BASE_URL env var or 'http://localhost:11434')
                If None, reads from LLM_BASE_URL environment variable
                If LLM_BASE_URL is not set, defaults to 'http://localhost:11434'
        
        Example:
            >>> # Use defaults from environment
            >>> provider = OllamaProvider()
            >>> 
            >>> # Override with specific model
            >>> provider = OllamaProvider(model="mistral")
            >>> 
            >>> # Override with custom server
            >>> provider = OllamaProvider(base_url="http://ollama-server:11434")
        """
        # Determine model from parameter, environment, or default
        self.model = model or os.getenv("LLM_MODEL", "llama2")
        
        # Determine base URL from parameter, environment, or default
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434")
        
        # Call parent constructor
        super().__init__(model=self.model, base_url=self.base_url)
        
        # Initialize Ollama client with configured endpoint
        try:
            self.client = ollama.Client(host=self.base_url)
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize Ollama client at {self.base_url}. "
                f"Ensure Ollama is running and accessible. Error: {e}"
            ) from e
        
        # Verify model availability and provide helpful guidance if not found
        self._verify_model_availability()
    
    def _verify_model_availability(self):
        """
        Verify that the specified Ollama model is available locally.
        
        This method checks if the configured model exists in the local Ollama
        installation. If the model is not found, it prints a helpful warning
        message with instructions to pull the model using the Ollama CLI.
        
        The verification is non-blocking - the provider will still initialize
        even if the model is not found, but generation attempts will fail with
        clear error messages.
        
        Raises:
            No exceptions are raised - warnings are printed to console
            If Ollama server is unreachable, a warning is displayed
        
        Example Output:
            ⚠️  Warning: Model 'llama2' not found locally.
               Run: ollama pull llama2
               Available models: mistral, codellama
        """
        try:
            # Query Ollama for list of available models
            available_models = self.client.list()
            
            # Extract model names from response
            # Response format: {"models": [{"name": "llama2:latest", ...}, ...]}
            model_names = [m.get('name', '') for m in available_models.get('models', [])]
            
            # Check if our configured model exists (exact or prefix match)
            # Handle both "llama2" and "llama2:latest" formats
            model_found = any(
                self.model in name or name.startswith(f"{self.model}:")
                for name in model_names
            )
            
            if not model_found:
                print(f"⚠️  Warning: Model '{self.model}' not found locally.")
                print(f"   Run: ollama pull {self.model}")
                if model_names:
                    print(f"   Available models: {', '.join(model_names)}")
                else:
                    print("   No models found. Pull a model first: ollama pull llama2")
        
        except Exception as e:
            # Non-fatal warning if we can't verify model availability
            print(f"⚠️  Warning: Could not verify Ollama model availability: {e}")
            print(f"   Ensure Ollama is running at {self.base_url}")
            print(f"   Test connection: curl {self.base_url}/api/tags")
    
    def generate_gherkin(self, exploration_log: str) -> str:
        """
        Generate business-readable Gherkin scenario from browser exploration log.
        
        This method analyzes a JSON-formatted exploration log from the Playwright MCP
        server and generates a high-level, business-readable Gherkin feature file.
        The generated scenario focuses on WHAT the user does (business actions) rather
        than HOW it's implemented (UI details).
        
        The method uses carefully crafted prompts to instruct the LLM to:
        - Extract business intent from low-level browser actions
        - Write clear Given/When/Then steps
        - Use business domain language, avoiding technical jargon
        - Add appropriate test tags (@smoke, @ui, @api)
        - Follow BDD best practices
        
        Args:
            exploration_log: JSON string containing Playwright MCP exploration session.
                Required structure:
                {
                    "session_id": "unique-id",
                    "events": [
                        {"action": "navigate", "url": "/path"},
                        {"action": "type", "selector": "input", "text": "value"},
                        {"action": "click", "selector": "button"},
                        {"action": "assert", "type": "url_contains", "expected": "/result"}
                    ]
                }
        
        Returns:
            Gherkin feature text with complete Feature and Scenario structure.
            Format:
                Feature: Feature Name
                  Business value statement
                
                @tags
                Scenario: Scenario Name
                  Given preconditions
                  When actions
                  Then assertions
        
        Raises:
            ValueError: If exploration_log is empty or malformed JSON
            RuntimeError: If Ollama generation fails (model not found, server unreachable)
            TimeoutError: If generation takes longer than expected (handled by Ollama client)
        
        Example:
            >>> provider = OllamaProvider()
            >>> log = '''
            >>> {
            >>>     "events": [
            >>>         {"action": "navigate", "url": "/login"},
            >>>         {"action": "type", "selector": "input[name='email']", "text": "user@example.com"},
            >>>         {"action": "type", "selector": "input[name='password']", "text": "password"},
            >>>         {"action": "click", "selector": "button[type='submit']"},
            >>>         {"action": "assert", "type": "url_contains", "expected": "/dashboard"}
            >>>     ]
            >>> }
            >>> '''
            >>> gherkin = provider.generate_gherkin(log)
            >>> print(gherkin)
            Feature: User Authentication
              As a registered user
              I want to log in to the application
              So that I can access my dashboard
            
            @smoke @ui
            Scenario: Successful login with valid credentials
              Given the user is on the login page
              When the user enters valid credentials
              And the user submits the login form
              Then the user is redirected to the dashboard
        """
        # Validate input
        if not exploration_log or not exploration_log.strip():
            raise ValueError("Exploration log cannot be empty")
        
        # Construct prompt for Gherkin generation with detailed instructions
        prompt = f"""You are an expert test automation engineer specializing in Behavior-Driven Development (BDD).

Your task is to analyze the following browser exploration log and generate a business-readable Gherkin scenario.

EXPLORATION LOG:
{exploration_log}

REQUIREMENTS:
1. Feature: Write a clear feature description from business perspective
   - Include "As a [role], I want [goal], So that [benefit]" format
   - Focus on business value, not technical implementation

2. Scenario: Create a descriptive scenario title
   - Use active voice and present tense
   - Describe the user's goal or action
   - Example: "Successful login with valid credentials"

3. Steps: Write high-level Given/When/Then steps
   - Focus on WHAT the user does, not HOW (no UI implementation details)
   - Use business language understandable by non-technical stakeholders
   - Keep steps at behavior level (e.g., "the user logs in", not "the user clicks button at #login-btn")
   - Use proper Gherkin keywords: Given (preconditions), When (actions), Then (expected outcomes)
   - Use And/But for multiple steps of same type

4. Tags: Add appropriate tags
   - @smoke for critical user paths
   - @ui for UI interaction tests
   - @api for API-focused tests
   - @regression for regression test suite
   - Add domain-specific tags (e.g., @authentication, @payment)

EXAMPLE FORMAT:
Feature: User Authentication
  As a registered user
  I want to log in to the application
  So that I can access protected resources

  @smoke @ui @authentication
  Scenario: Successful login with valid credentials
    Given the user is on the login page
    And a test user with role "customer" exists
    When the user enters valid credentials
    And the user submits the login form
    Then the user is redirected to the dashboard
    And the user sees a welcome message

Generate the Gherkin scenario now (output ONLY the Feature and Scenario, no additional commentary):"""
        
        try:
            # Call Ollama API with optimized parameters for Gherkin generation
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.7,  # Balanced creativity - not too random, not too deterministic
                    "top_p": 0.9,        # Nucleus sampling for diverse but focused output
                    "top_k": 40,         # Limit vocabulary to most likely tokens
                    "num_predict": 1000  # Maximum tokens to generate (Gherkin scenarios are typically 100-500 tokens)
                }
            )
            
            # Extract generated text from response
            gherkin_text = response.get('response', '').strip()
            
            # Validate that we got a non-empty response
            if not gherkin_text:
                raise RuntimeError(
                    "Ollama returned empty response. "
                    f"Verify model '{self.model}' is working: ollama run {self.model}"
                )
            
            return gherkin_text
        
        except Exception as e:
            error_msg = f"Error generating Gherkin with Ollama model '{self.model}': {e}"
            print(f"❌ {error_msg}")
            print(f"   Troubleshooting:")
            print(f"   1. Verify Ollama is running: curl {self.base_url}/api/tags")
            print(f"   2. Verify model exists: ollama list")
            print(f"   3. Pull model if needed: ollama pull {self.model}")
            raise RuntimeError(error_msg) from e
    
    def suggest_edge_cases(self, scenario: str) -> List[str]:
        """
        Suggest edge cases and test variations for existing Gherkin scenario.
        
        This method analyzes a Gherkin scenario and uses LLM reasoning to suggest
        additional test cases covering:
        - Boundary conditions (empty inputs, max lengths, special characters)
        - Security vulnerabilities (SQL injection, XSS, auth bypass)
        - Error scenarios (network failures, invalid states, timeouts)
        - Data validation edge cases (format errors, type mismatches)
        - Concurrency issues (race conditions, simultaneous updates)
        - Business logic edge cases (expired states, permission boundaries)
        
        The suggestions are specific, actionable, and prioritized by risk/impact.
        They help testers achieve comprehensive test coverage by identifying scenarios
        that might not be obvious during initial test design.
        
        Args:
            scenario: Existing Gherkin scenario text to analyze.
                Can include Feature, Scenario, and steps, or just the Scenario.
                Example:
                    Scenario: User creates account
                      Given the user is on the registration page
                      When the user fills in the registration form
                      And the user submits the form
                      Then a new account should be created
        
        Returns:
            List of human-readable edge case descriptions.
            Each description is specific, actionable, and focused on a distinct risk.
            Typically returns 8-12 edge cases covering diverse failure modes.
            
            Example:
                [
                    "Test registration with email exceeding maximum length of 255 characters",
                    "Test registration with SQL injection pattern in username field (e.g., admin' OR '1'='1--)",
                    "Test concurrent registrations with same email from two browser tabs",
                    "Test registration with XSS payload in name field (<script>alert('XSS')</script>)",
                    "Test registration when email verification service returns HTTP 503",
                    ...
                ]
        
        Raises:
            ValueError: If scenario is empty or doesn't contain valid Gherkin structure
            RuntimeError: If Ollama generation fails (model not found, server unreachable)
        
        Example:
            >>> provider = OllamaProvider()
            >>> scenario = '''
            >>> Scenario: User login
            >>>   Given the user is on the login page
            >>>   When the user enters valid credentials
            >>>   Then the user is redirected to the dashboard
            >>> '''
            >>> edge_cases = provider.suggest_edge_cases(scenario)
            >>> for case in edge_cases:
            >>>     print(f"- {case}")
            - Test login with email exceeding 255 characters
            - Test login with SQL injection in email field
            - Test login with account locked after 5 failed attempts
            ...
        """
        # Validate input
        if not scenario or not scenario.strip():
            raise ValueError("Scenario cannot be empty")
        
        # Construct prompt using the centralized template from llm/prompts/edge_case_suggestions.py
        # The ANALYZE_SCENARIO_PROMPT template contains comprehensive instructions for edge case discovery
        prompt = ANALYZE_SCENARIO_PROMPT.format(scenario=scenario)
        
        try:
            # Call Ollama API with higher temperature for creative edge case discovery
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={
                    "temperature": 0.8,  # Higher creativity for diverse edge case suggestions
                    "top_p": 0.95,       # Allow more diverse token selection
                    "top_k": 50,         # Broader vocabulary for varied suggestions
                    "num_predict": 800   # Sufficient tokens for 8-12 detailed edge cases
                }
            )
            
            # Extract generated text from response
            content = response.get('response', '').strip()
            
            if not content:
                raise RuntimeError(
                    "Ollama returned empty response for edge case suggestions. "
                    f"Verify model '{self.model}' is working: ollama run {self.model}"
                )
            
            # Parse numbered list into array
            # Expected format from LLM:
            # 1. Edge case description
            # 2. Another edge case description
            # ...
            edge_cases = []
            
            for line in content.split('\n'):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Skip "Assumptions:" section if present
                if line.lower().startswith('assumptions'):
                    break
                
                # Match lines starting with number and period (e.g., "1. ", "2. ")
                # or lines starting with dash/bullet (e.g., "- ", "• ")
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•') or line.startswith('*')):
                    # Remove leading numbering/bullets and clean up
                    clean_line = line
                    
                    # Remove numbered list format: "1. ", "2. ", etc.
                    clean_line = re.sub(r'^\d+\.\s*', '', clean_line)
                    # Remove dash/bullet format: "- ", "• ", "* "
                    clean_line = re.sub(r'^[-•*]\s*', '', clean_line)
                    
                    # Only add non-empty cleaned lines
                    if clean_line:
                        edge_cases.append(clean_line.strip())
            
            # If parsing failed (no structured list found), fall back to splitting by lines
            # This handles cases where LLM doesn't follow exact format
            if not edge_cases:
                edge_cases = [
                    line.strip()
                    for line in content.split('\n')
                    if line.strip() and not line.lower().startswith('assumptions')
                ]
            
            # Validate we got meaningful results
            if not edge_cases:
                raise RuntimeError(
                    "Failed to parse edge cases from LLM response. "
                    "Response may be in unexpected format."
                )
            
            return edge_cases
        
        except Exception as e:
            error_msg = f"Error suggesting edge cases with Ollama model '{self.model}': {e}"
            print(f"❌ {error_msg}")
            print(f"   Troubleshooting:")
            print(f"   1. Verify Ollama is running: curl {self.base_url}/api/tags")
            print(f"   2. Verify model exists: ollama list")
            print(f"   3. Pull model if needed: ollama pull {self.model}")
            raise RuntimeError(error_msg) from e
    
    def __repr__(self) -> str:
        """
        String representation of OllamaProvider for debugging and logging.
        
        Returns:
            String representation showing configured model and base URL.
            Format: "OllamaProvider(model='llama2', base_url='http://localhost:11434')"
        
        Example:
            >>> provider = OllamaProvider()
            >>> print(provider)
            OllamaProvider(model='llama2', base_url='http://localhost:11434')
            >>> repr(provider)
            "OllamaProvider(model='llama2', base_url='http://localhost:11434')"
        """
        return f"OllamaProvider(model='{self.model}', base_url='{self.base_url}')"


# Export OllamaProvider for external use
__all__ = ["OllamaProvider"]


