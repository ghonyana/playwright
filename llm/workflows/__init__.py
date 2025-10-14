"""
LLM-Assisted Test Authoring Workflows Package

This package provides end-to-end workflows for LLM-assisted test scenario generation,
human review, and automated test authoring. It orchestrates the complete lifecycle from
browser exploration through Playwright MCP to human-approved Gherkin scenarios ready
for CI/CD execution.

Core Workflows:

1. **Scenario Generation Workflow** (scenario_generator.py):
   - LLM-driven browser exploration via Playwright MCP server
   - Intelligent Gherkin generation from exploration logs
   - Syntax validation before file persistence
   - Automatic feature file creation with review metadata

2. **Human Review Pipeline** (review_pipeline.py):
   - Git branch creation and commit automation
   - GitHub Pull Request submission with comprehensive checklist
   - LLM-powered edge case suggestions for reviewers
   - Review status tracking and metadata persistence
   - Automatic step definition stub generation upon approval

Package Architecture:

    Playwright MCP Server → Browser Exploration → Exploration Log
                                                         ↓
    LLM Client ← Gherkin Generation ← Exploration Log
          ↓
    Feature File (tests/features/generated/)
          ↓
    Git Branch → GitHub PR → Human Review → Approval
          ↓
    Step Definition Stubs → Implementation → Test Suite

Primary Use Cases:

    # Use Case 1: Generate scenario from browser exploration
    >>> from llm.workflows import explore_and_generate
    >>> 
    >>> feature_path = explore_and_generate(
    ...     url="https://example.com/login",
    ...     objective="Test user authentication flow"
    ... )
    >>> print(f"Generated: {feature_path}")
    
    # Use Case 2: Submit generated scenario for human review
    >>> from llm.workflows import submit_for_review
    >>> 
    >>> pr_url = submit_for_review(feature_path)
    >>> print(f"Review at: {pr_url}")
    
    # Use Case 3: Full workflow with ReviewPipeline class
    >>> from llm.workflows import ReviewPipeline
    >>> 
    >>> pipeline = ReviewPipeline()
    >>> metadata = ReviewMetadata(...)
    >>> pr_url = pipeline.submit_for_review(feature_path, metadata)

Integration Points:

    **Upstream Dependencies:**
    - llm.client: LLM provider abstraction (Ollama, OpenAI)
    - llm.prompts: Prompt templates for Gherkin generation and edge case suggestions
    - mcp_servers.playwright_mcp: WebSocket server for browser automation
    
    **Downstream Consumers:**
    - Test developers using LLM assistance for scenario authoring
    - CI/CD pipelines consuming approved scenarios
    - Step definition implementers using generated stubs
    
    **External Services:**
    - Playwright MCP Server: Browser automation (ws://localhost:8001/explore)
    - GitHub API: Pull Request creation and management
    - LLM Providers: Ollama (local) or OpenAI (hosted)

Configuration:

    Environment variables required for full functionality:
    
    # Playwright MCP Configuration
    PLAYWRIGHT_MCP_URL: WebSocket endpoint for browser automation
        Default: ws://localhost:8001/explore
        Required for: explore_and_generate()
    
    # LLM Provider Configuration
    LLM_PROVIDER: 'ollama' or 'openai'
        Default: ollama
        Required for: All Gherkin generation workflows
    
    LLM_MODEL: Model identifier
        Defaults: 'llama2' (ollama), 'gpt-4' (openai)
        Required for: All LLM operations
    
    LLM_API_KEY: API key for OpenAI provider
        Required only if: LLM_PROVIDER=openai
    
    # GitHub Integration (optional, for PR creation)
    GITHUB_TOKEN: GitHub API token with repo permissions
        Required for: submit_for_review() PR creation
        Format: ghp_... or github_pat_...
    
    GITHUB_REPOSITORY_OWNER: Repository owner name
        Required for: PR creation
        Example: "myorg" for github.com/myorg/repo
    
    GITHUB_REPOSITORY: Repository name
        Required for: PR creation
        Example: "test-automation"

Workflow Design Patterns:

    **Observer Pattern**: Review status changes trigger metadata updates
    **Strategy Pattern**: LLM provider selection (Ollama vs OpenAI)
    **Template Method**: Scenario generation workflow with customizable steps
    **Factory Pattern**: LLM client creation via get_llm_client()
    **Builder Pattern**: PR description construction with multiple sections

Quality Assurance:

    All LLM-generated scenarios undergo mandatory human review:
    - Business logic validation by domain experts
    - Technical quality review by test engineers
    - Edge case coverage assessment
    - Locator strategy verification
    
    This human-in-the-loop approach ensures:
    - High-quality test scenarios aligned with business goals
    - Maintainable Gherkin free from implementation details
    - Comprehensive coverage through LLM edge case suggestions
    - Deterministic, reliable tests using MCP data management

Per Agent Action Plan Section 0.5.1 Group 9.9:
    "Create llm/workflows/__init__.py as Python package marker per Agent Action Plan
    enabling import of workflow orchestration components"

Per Technical Specification Section 3.3.5:
    "LLM integration accelerates test scenario authoring by generating draft Gherkin
    from browser exploration logs, with human review ensuring quality and alignment"
"""

# Import core workflow functions and classes from submodules
# These imports enable simplified usage: `from llm.workflows import explore_and_generate`

from llm.workflows.scenario_generator import (
    explore_and_generate,
    generate_scenario_from_log,
)

from llm.workflows.review_pipeline import (
    submit_for_review,
    ReviewPipeline,
)


# Public API exports
# This __all__ declaration explicitly defines the public interface of this package,
# ensuring that `from llm.workflows import *` only imports intended symbols
__all__ = [
    # Scenario Generation Functions
    "explore_and_generate",         # End-to-end: Browser exploration → Gherkin feature file
    "generate_scenario_from_log",   # LLM: Exploration log → Gherkin text
    
    # Review Pipeline Functions
    "submit_for_review",            # Convenience: Submit feature file for GitHub PR review
    
    # Review Pipeline Classes
    "ReviewPipeline",               # Full review workflow orchestrator with Git/GitHub integration
]
