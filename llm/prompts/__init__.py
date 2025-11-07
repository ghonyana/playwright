"""
LLM Prompt Templates Package

This package provides centralized, production-ready LLM prompt templates for the
test automation framework's AI-assisted features. The prompts enable:

1. **Gherkin Scenario Generation**: Converts browser exploration logs into 
   business-readable BDD scenarios using structured prompts that enforce 
   high-level behavioral steps without implementation details.

2. **Edge Case Discovery**: Analyzes existing test scenarios to suggest 
   comprehensive edge cases covering security, boundaries, concurrency, 
   and business logic testing.

Architecture Overview:
---------------------
The prompts package follows a modular design where each prompt type has its own
dedicated module, and this __init__.py provides a clean, unified namespace for
importing prompts across the framework.

Module Structure:
    llm/prompts/
    ├── __init__.py                    # This file - package exports
    ├── gherkin_generation.py          # Gherkin scenario generation prompts
    └── edge_case_suggestions.py       # Edge case discovery prompts

Integration Points:
-------------------
This package integrates with multiple framework components:

1. **LLM Provider Implementations**:
   - llm/providers/ollama.py: Uses prompts for local Ollama models
   - llm/providers/openai.py: Uses prompts for OpenAI-compatible APIs
   Both providers consume these prompts to ensure consistent behavior across
   different LLM backends.

2. **Test Generation Workflows**:
   - llm/workflows/scenario_generator.py: Orchestrates Gherkin generation
   - llm/workflows/review_pipeline.py: Human review of LLM outputs
   Workflows use prompts to drive end-to-end test authoring pipelines.

3. **MCP Server Integration**:
   - mcp_servers/playwright_mcp/gherkin/generator.py: Converts browser 
     exploration sessions into Gherkin scenarios using these prompts
   The Playwright MCP server enables LLM agents to control browsers and 
   generate test scenarios from exploration.

Usage Examples:
---------------

Example 1: Importing for Gherkin Generation
```python
from llm.prompts import GHERKIN_SYSTEM_PROMPT, GHERKIN_USER_TEMPLATE

# Configure LLM with system prompt
llm_client.set_system_prompt(GHERKIN_SYSTEM_PROMPT)

# Generate scenario from exploration log
exploration_log = "User navigated to /login, entered credentials, clicked submit..."
user_prompt = GHERKIN_USER_TEMPLATE.format(exploration_log=exploration_log)
gherkin_scenario = llm_client.generate(user_prompt, temperature=0.7)
```

Example 2: Importing for Edge Case Discovery
```python
from llm.prompts import ANALYZE_SCENARIO_PROMPT

# Analyze existing scenario for edge cases
existing_scenario = '''
Scenario: User login with valid credentials
    Given the user is on the login page
    When the user logs in with valid credentials
    Then the user is redirected to the dashboard
'''

prompt = ANALYZE_SCENARIO_PROMPT.format(scenario=existing_scenario)
edge_cases = llm_client.generate(prompt, temperature=0.8)
```

Example 3: Alternative Direct Import Style
```python
# Import directly from submodules if preferred
from llm.prompts.gherkin_generation import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from llm.prompts.edge_case_suggestions import ANALYZE_SCENARIO_PROMPT
```

Design Principles:
------------------
1. **Provider Agnostic**: Prompts work with any OpenAI-compatible API or Ollama
2. **Deterministic Output**: Carefully engineered to produce consistent results
3. **Business Readable**: Generated scenarios use plain language, not tech jargon
4. **Security Conscious**: Explicitly prohibit injection vulnerabilities in output
5. **Maintainable**: Centralized prompt management prevents prompt sprawl

Prompt Engineering Best Practices:
-----------------------------------
- System prompts establish consistent LLM persona across all providers
- User prompt templates use {placeholder} format for dynamic content injection
- Explicit prohibitions prevent LLM hallucination of implementation details
- Temperature recommendations tuned for each use case (0.7 for generation, 0.8 for exploration)
- Example-driven prompts show desired output format to guide LLM behavior

Configuration Requirements:
----------------------------
The prompts integrate with framework configuration via environment variables:
- LLM_PROVIDER: 'ollama' or 'openai' (determines which provider uses these prompts)
- LLM_MODEL: Model name (e.g., 'llama3', 'gpt-4', 'gpt-3.5-turbo')
- LLM_API_KEY: API key for hosted providers (OpenAI, Anthropic, Azure)
- LLM_BASE_URL: Custom endpoint for OpenAI-compatible APIs

Technical Specification Compliance:
------------------------------------
Per Agent Action Plan Section 0.2.2, this module:
- Serves as Python package marker enabling llm.prompts imports
- Provides clean namespace for centralized prompt template management
- Supports consistent LLM prompt behavior across Ollama and OpenAI providers
- Enforces "business-readable Gherkin" with "high-level steps" (Section 0.7.2)
- Prohibits CSS selectors, XPath, or coordinates in generated scenarios

Version Information:
--------------------
Compatible with:
- OpenAI Python SDK >= 1.59.8
- Ollama Python SDK >= 0.4.8
- LangChain >= 0.3.20 (optional, for advanced orchestration)
"""

# ============================================================================
# Import Prompt Templates from Submodules
# ============================================================================

# Gherkin generation prompts - used to convert browser exploration into BDD scenarios
from llm.prompts.gherkin_generation import (
    SYSTEM_PROMPT as GHERKIN_SYSTEM_PROMPT,  # LLM persona as BDD expert
    USER_PROMPT_TEMPLATE as GHERKIN_USER_TEMPLATE,  # Template for exploration logs
)

# Edge case discovery prompts - used to analyze scenarios and suggest additional tests
from llm.prompts.edge_case_suggestions import (
    ANALYZE_SCENARIO_PROMPT,  # QA engineer persona for comprehensive testing
)

# ============================================================================
# Public API - Explicit Exports
# ============================================================================

__all__ = [
    # Gherkin Generation Exports
    "GHERKIN_SYSTEM_PROMPT",  # System prompt establishing LLM as BDD expert
    "GHERKIN_USER_TEMPLATE",  # User prompt template with {exploration_log} placeholder
    
    # Edge Case Discovery Exports
    "ANALYZE_SCENARIO_PROMPT",  # Prompt for discovering edge cases from scenarios
]

# ============================================================================
# Module Metadata
# ============================================================================

__version__ = "1.0.0"
__author__ = "Blitzy Test Automation Framework"
__description__ = "Centralized LLM prompt templates for test scenario generation and edge case discovery"
