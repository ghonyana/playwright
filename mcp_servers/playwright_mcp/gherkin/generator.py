"""
Gherkin Scenario Generator for Playwright MCP Server

This module converts browser exploration logs from Playwright MCP sessions into
business-readable Gherkin scenarios using LLM assistance. It transforms low-level
browser actions (navigate, click, type) into high-level Given/When/Then steps that
describe user behavior without implementation details.

Key Features:
- LLM-assisted scenario generation (Ollama local or OpenAI hosted)
- Template-based fallback when LLM unavailable
- Enforcement of Gherkin best practices (no selectors, business language)
- Generation metadata for human review workflow
- Semantic action extraction from exploration logs

Per Technical Specification Section 0.7.2:
- Generated Gherkin is business-readable, focusing on WHAT not HOW
- No CSS selectors, XPath expressions, or DOM coordinates in output
- High-level steps using domain language stakeholders understand
- Feature descriptions include business value statements

Per Technical Specification Section 0.7.8:
- All generated scenarios include metadata for human review
- Assumptions and open questions documented for reviewer validation
- Generation timestamp, model, and session tracking for audit trail

Integration Points:
- mcp_servers/playwright_mcp/routers/tools.py: Exposes generate_gherkin endpoint
- llm/client.py: Provides LLMClient interface for multiple providers
- llm/prompts/gherkin_generation.py: Contains expert-engineered prompts
- tests/features/: Target directory for approved generated scenarios

Usage Example:
    >>> from mcp_servers.playwright_mcp.gherkin.generator import GherkinGenerator
    >>> from llm.client import get_llm_client
    >>> 
    >>> # Initialize with LLM client
    >>> llm_client = get_llm_client()
    >>> generator = GherkinGenerator(llm_client)
    >>> 
    >>> # Generate from exploration log
    >>> exploration_log = [
    >>>     {"action": "navigate", "details": {"url": "/login", "title": "Login Page"}},
    >>>     {"action": "type", "details": {"label": "Email", "value": "user@example.com"}},
    >>>     {"action": "click", "details": {"text": "Sign In"}}
    >>> ]
    >>> 
    >>> feature = await generator.generate_from_exploration(
    >>>     feature_name="User Authentication",
    >>>     exploration_goal="User logs in with valid credentials",
    >>>     exploration_log=exploration_log,
    >>>     session_id="session-123"
    >>> )
    >>> 
    >>> # Write to feature file
    >>> with open("tests/features/authentication.feature", "w") as f:
    >>>     f.write(feature)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
import logging

# LLM integration for scenario generation
try:
    from llm.client import LLMClient
    from llm.prompts.gherkin_generation import USER_PROMPT_TEMPLATE
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    # Fallback to template-based generation if LLM not available

logger = logging.getLogger(__name__)


class GherkinGenerator:
    """Generate Gherkin scenarios from Playwright MCP exploration logs.
    
    Converts browser exploration action logs into business-readable BDD scenarios
    using LLM assistance (Ollama local or OpenAI hosted). Enforces Gherkin best
    practices: high-level steps, business language, no implementation details.
    
    Per Technical Specification Section 0.7.2:
    - Generates business-readable scenarios (no CSS selectors, XPath, coordinates)
    - Uses high-level Given/When/Then steps focusing on WHAT, not HOW
    - Includes Feature descriptions with business value statements
    - Adds metadata for human review workflow
    
    Attributes:
        llm_client (Optional[LLMClient]): LLM client for intelligent scenario generation
        model_name (Optional[str]): Model identifier for generation metadata
        assumptions (List[str]): Generation assumptions for human review
        open_questions (List[str]): Questions requiring reviewer clarification
    """
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """Initialize Gherkin generator with optional LLM client.
        
        Args:
            llm_client: LLM client for scenario generation. If None, attempts
                       to create from environment configuration (LLM_PROVIDER).
        """
        self.llm_client = llm_client
        self.model_name: Optional[str] = None
        self.assumptions: List[str] = []
        self.open_questions: List[str] = []
        
        # Initialize LLM client if not provided and available
        if self.llm_client is None and LLM_AVAILABLE:
            try:
                from llm.client import get_llm_client
                self.llm_client = get_llm_client()
                self.model_name = getattr(self.llm_client, 'model', 'unknown')
                logger.info(f"GherkinGenerator initialized with LLM: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM client: {e}. Using template-based generation.")
                self.llm_client = None
        elif self.llm_client is not None:
            self.model_name = getattr(self.llm_client, 'model', 'unknown')
            logger.info(f"GherkinGenerator initialized with provided LLM client: {self.model_name}")
        
        if self.llm_client is None:
            logger.info("GherkinGenerator using template-based generation (no LLM)")
    
    async def generate_from_exploration(
        self,
        feature_name: str,
        exploration_goal: str,
        exploration_log: List[Dict[str, Any]],
        session_id: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Gherkin feature file from exploration log.
        
        Args:
            feature_name: Name of the feature being tested
            exploration_goal: High-level goal of the exploration session
            exploration_log: List of exploration actions (navigate, click, type, etc.)
            session_id: Unique session identifier for tracking
            additional_context: Optional additional context (accessibility tree, etc.)
        
        Returns:
            Complete .feature file content with metadata, Feature, and Scenarios
        
        Raises:
            ValueError: If exploration_log is empty or invalid
        """
        if not exploration_log:
            raise ValueError("Exploration log cannot be empty")
        
        # Reset state for new generation
        self.assumptions = []
        self.open_questions = []
        
        # Build human-readable exploration context
        exploration_context = self._build_exploration_context(exploration_log)
        
        # Generate scenarios using LLM or template
        if self.llm_client and LLM_AVAILABLE:
            scenarios_content = await self._generate_with_llm(
                feature_name=feature_name,
                exploration_goal=exploration_goal,
                exploration_context=exploration_context,
                additional_context=additional_context
            )
        else:
            scenarios_content = self._generate_with_template(
                feature_name=feature_name,
                exploration_goal=exploration_goal,
                exploration_log=exploration_log
            )
        
        # Format complete .feature file with metadata
        feature_content = self._format_feature_file(
            feature_name=feature_name,
            scenarios_content=scenarios_content,
            metadata={
                "session_id": session_id,
                "model": self.model_name or "template-based",
                "exploration_actions": len(exploration_log),
                "generated_at": datetime.utcnow().isoformat(),
                "assumptions": self.assumptions,
                "open_questions": self.open_questions
            }
        )
        
        return feature_content
    
    async def _generate_with_llm(
        self,
        feature_name: str,
        exploration_goal: str,
        exploration_context: str,
        additional_context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate scenarios using LLM client.
        
        Uses prompts from llm/prompts/gherkin_generation.py to instruct LLM
        on Gherkin best practices and business-readable scenario generation.
        
        Args:
            feature_name: Name of the feature
            exploration_goal: High-level exploration objective
            exploration_context: Human-readable action sequence
            additional_context: Optional page structure or accessibility data
        
        Returns:
            Generated Gherkin scenarios (without metadata header)
        
        Raises:
            Exception: If LLM generation fails
        """
        # Build comprehensive exploration log for LLM
        exploration_log_text = f"""
Feature Goal: {exploration_goal}
Feature Name: {feature_name}

Exploration Actions:
{exploration_context}
"""
        
        if additional_context:
            exploration_log_text += f"\n\nAdditional Context:\n{json.dumps(additional_context, indent=2)}"
        
        # Generate scenarios via LLM using the generate_gherkin method
        try:
            response = await self._call_llm_generate(exploration_log_text)
            
            # Extract assumptions and questions from response
            self._extract_metadata(response)
            
            return response
        except Exception as e:
            logger.error(f"LLM generation failed: {e}. Falling back to template-based generation.")
            # Fallback to template if LLM fails
            return self._generate_with_template(
                feature_name=feature_name,
                exploration_goal=exploration_goal,
                exploration_log=[]  # Will trigger basic template
            )
    
    async def _call_llm_generate(self, exploration_log: str) -> str:
        """Call LLM client's generate_gherkin method with error handling.
        
        Args:
            exploration_log: Formatted exploration context for LLM
        
        Returns:
            Generated Gherkin text
        
        Raises:
            Exception: If LLM call fails
        """
        if self.llm_client is None:
            raise ValueError("LLM client is not available")
        
        # The LLMClient.generate_gherkin() method is abstract and may be sync or async
        # depending on the provider. Try async first, fall back to sync.
        try:
            if hasattr(self.llm_client.generate_gherkin, '__call__'):
                # Check if method is async
                import inspect
                if inspect.iscoroutinefunction(self.llm_client.generate_gherkin):
                    result = await self.llm_client.generate_gherkin(exploration_log)
                else:
                    result = self.llm_client.generate_gherkin(exploration_log)
                return result
            else:
                raise AttributeError("generate_gherkin method not found on LLM client")
        except Exception as e:
            logger.error(f"Error calling LLM generate_gherkin: {e}")
            raise
    
    def _generate_with_template(
        self,
        feature_name: str,
        exploration_goal: str,
        exploration_log: List[Dict[str, Any]]
    ) -> str:
        """Generate basic scenarios using templates (fallback without LLM).
        
        Creates simple Gherkin structure from exploration log without LLM assistance.
        Less sophisticated but ensures functionality when LLM unavailable.
        
        Args:
            feature_name: Feature name for Feature header
            exploration_goal: Goal description for scenario title
            exploration_log: List of exploration actions
        
        Returns:
            Basic Gherkin feature content
        """
        scenarios = []
        
        # Extract key actions from log if available
        pages_visited = [a for a in exploration_log if a.get("action") == "navigate"]
        interactions = [a for a in exploration_log if a.get("action") in ["click", "type", "fill"]]
        
        # Generate Feature header
        feature_header = f"""Feature: {feature_name}
  As a user
  I want to {exploration_goal.lower()}
  So that I can accomplish my goals

"""
        
        # Generate basic scenario from exploration
        scenario = f"""  @generated @needs-review
  Scenario: {exploration_goal}
    Given the user navigates to the application
"""
        
        # Add interaction steps (limit to first 5 for readability)
        for interaction in interactions[:5]:
            action_type = interaction.get("action")
            details = interaction.get("details", {})
            
            if action_type == "click":
                element_text = details.get("text", details.get("element_text", "element"))
                scenario += f"    When the user clicks '{element_text}'\n"
            elif action_type in ["type", "fill"]:
                element_label = details.get("label", details.get("element_label", "field"))
                value = details.get("value", details.get("text", "data"))
                # Mask sensitive data
                if "password" in element_label.lower():
                    value = "***"
                scenario += f"    And the user enters '{value}' into the {element_label}\n"
        
        scenario += "    Then the action should complete successfully\n"
        
        scenarios.append(scenario)
        
        # Add note about template generation
        self.assumptions.append("Scenario generated using template (LLM unavailable)")
        self.assumptions.append("Steps are generic and require refinement for production use")
        self.open_questions.append("Should business language be refined for stakeholder readability?")
        self.open_questions.append("Are there additional assertions or validations needed?")
        
        return feature_header + "\n".join(scenarios)
    
    def _build_exploration_context(self, exploration_log: List[Dict[str, Any]]) -> str:
        """Build human-readable context from exploration action log.
        
        Converts technical browser actions into descriptive text for LLM processing.
        Filters out low-level details (selectors, coordinates) per Section 0.7.2.
        
        Args:
            exploration_log: List of exploration actions with action type and details
        
        Returns:
            Multi-line string describing the exploration session in business terms
        """
        context_lines = []
        
        for i, action in enumerate(exploration_log, 1):
            action_type = action.get("action", "unknown")
            details = action.get("details", {})
            timestamp = action.get("timestamp", "")
            
            if action_type == "navigate":
                url = details.get("url", "unknown URL")
                title = details.get("title", "")
                context_lines.append(f"{i}. Navigated to: {url}")
                if title:
                    context_lines.append(f"   Page title: {title}")
            
            elif action_type == "click":
                # Extract semantic information, avoid selectors
                element_text = details.get("text", details.get("element_text"))
                element_role = details.get("role", details.get("element_role"))
                if element_text:
                    context_lines.append(f"{i}. Clicked: {element_text}")
                elif element_role:
                    context_lines.append(f"{i}. Clicked: {element_role} element")
                else:
                    context_lines.append(f"{i}. Clicked element")
            
            elif action_type in ["type", "fill"]:
                element_label = details.get("label", details.get("element_label"))
                value = details.get("value", details.get("text"))
                if element_label and value:
                    # Mask sensitive data
                    masked_value = "***" if "password" in element_label.lower() else value
                    context_lines.append(f"{i}. Entered '{masked_value}' into {element_label}")
                elif element_label:
                    context_lines.append(f"{i}. Entered text into {element_label}")
                else:
                    context_lines.append(f"{i}. Entered text into input field")
            
            elif action_type == "screenshot":
                context_lines.append(f"{i}. Captured screenshot")
            
            elif action_type == "get_accessibility_tree":
                context_lines.append(f"{i}. Analyzed page structure")
            
            elif action_type == "assert":
                assertion_type = details.get("type", "condition")
                expected = details.get("expected", "")
                if expected:
                    context_lines.append(f"{i}. Verified: {assertion_type} - {expected}")
                else:
                    context_lines.append(f"{i}. Verified: {assertion_type}")
            
            else:
                context_lines.append(f"{i}. Performed: {action_type}")
        
        return "\n".join(context_lines)
    
    def _extract_metadata(self, content: str):
        """Extract assumptions and open questions from LLM response.
        
        Parses LLM-generated content for metadata comments per Section 0.7.8
        human review workflow requirements.
        
        Args:
            content: Generated Gherkin content potentially containing metadata
        """
        lines = content.split("\n")
        
        for line in lines:
            line = line.strip()
            
            # Extract assumptions
            if line.startswith("# Assumption:"):
                assumption = line[14:].strip()
                if assumption:
                    self.assumptions.append(assumption)
            
            # Extract open questions
            elif line.startswith("# Question:") or line.startswith("# Open Question:"):
                question = line.split(":", 1)[1].strip() if ":" in line else ""
                if question:
                    self.open_questions.append(question)
    
    def _format_feature_file(
        self,
        feature_name: str,
        scenarios_content: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Format complete .feature file with metadata header.
        
        Per Technical Specification Section 0.7.8, includes generation metadata
        for human review workflow.
        
        Args:
            feature_name: Name of the feature
            scenarios_content: Generated Gherkin scenarios
            metadata: Generation metadata (session_id, model, timestamp, etc.)
        
        Returns:
            Complete .feature file content with header and scenarios
        """
        # Build metadata header
        header = f"""# Feature: {feature_name}
#
# ========================================
# GENERATED SCENARIO - REQUIRES REVIEW
# ========================================
#
# Generated by: {metadata['model']}
# Session ID: {metadata['session_id']}
# Generated at: {metadata['generated_at']}
# Exploration actions: {metadata['exploration_actions']}
#
# IMPORTANT: This scenario was AI-generated and requires human review.
# Please validate:
# - Business language accuracy and stakeholder readability
# - Step granularity and appropriate abstraction level
# - Coverage completeness for the explored functionality
# - Assumptions and open questions listed below
#
"""
        
        # Add assumptions if present
        if metadata.get("assumptions"):
            header += "# Assumptions:\n"
            for assumption in metadata["assumptions"]:
                header += f"#   - {assumption}\n"
            header += "#\n"
        
        # Add open questions if present
        if metadata.get("open_questions"):
            header += "# Open Questions for Review:\n"
            for question in metadata["open_questions"]:
                header += f"#   - {question}\n"
            header += "#\n"
        
        header += "# ========================================\n\n"
        
        # Combine header and scenarios
        return header + scenarios_content
    
    def count_scenarios(self, feature_content: str) -> int:
        """Count number of scenarios in feature content.
        
        Args:
            feature_content: Complete .feature file content
        
        Returns:
            Number of Scenario and Scenario Outline instances
        """
        return feature_content.count("Scenario:") + feature_content.count("Scenario Outline:")
    
    def validate_gherkin_syntax(self, feature_content: str) -> bool:
        """Basic Gherkin syntax validation.
        
        Checks for required keywords and detects anti-patterns per Section 0.7.2.
        
        Args:
            feature_content: Complete .feature file content to validate
        
        Returns:
            True if basic syntax appears valid, False otherwise
        """
        # Check for required keywords
        has_feature = "Feature:" in feature_content
        has_scenario = "Scenario:" in feature_content or "Scenario Outline:" in feature_content
        
        # Check for anti-patterns per Section 0.7.2
        has_css_selectors = "." in feature_content and "[" in feature_content
        has_xpath = "//" in feature_content and "[" in feature_content
        has_coordinates = "click at (" in feature_content.lower()
        
        if has_css_selectors or has_xpath or has_coordinates:
            logger.warning("Generated Gherkin contains implementation details (selectors/coordinates)")
            self.open_questions.append("Generated Gherkin may contain low-level implementation details")
        
        return has_feature and has_scenario


# Module exports
__all__ = [
    "GherkinGenerator",
]

