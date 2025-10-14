"""
LLM Prompt Templates for Gherkin Scenario Generation

This module contains carefully engineered prompts for LLM-driven test scenario generation.
The prompts enforce BDD best practices, ensuring generated Gherkin scenarios are:
- Business-readable and stakeholder-friendly
- High-level behavioral descriptions (WHAT, not HOW)
- Free from implementation details (no CSS selectors, XPath, coordinates)
- Maintainable and focused on user actions and outcomes

Integration Points:
- llm/providers/ollama.py: Uses these prompts with local Ollama models
- llm/providers/openai.py: Uses these prompts with OpenAI-compatible APIs
- llm/workflows/scenario_generator.py: Orchestrates end-to-end Gherkin generation
- mcp_servers/playwright_mcp/gherkin/generator.py: Converts browser exploration to scenarios

Key Design Decisions:
1. SYSTEM_PROMPT establishes consistent LLM persona across all providers
2. USER_PROMPT_TEMPLATE accepts dynamic exploration log data
3. Prompts explicitly prohibit technical implementation details
4. Example-driven approach shows desired output format
5. Temperature guidance (0.7) balances creativity with consistency
"""

# ============================================================================
# SYSTEM PROMPT: Establishes LLM Persona as BDD Expert
# ============================================================================

SYSTEM_PROMPT = """You are an expert test automation engineer and Behavior-Driven Development (BDD) specialist.

Your expertise includes:
- Writing business-readable Gherkin scenarios that non-technical stakeholders can understand
- Translating technical browser interactions into high-level behavioral steps
- Following BDD best practices using the Given/When/Then pattern
- Creating maintainable test scenarios that focus on WHAT the system does, not HOW it's implemented

CRITICAL GUIDELINES FOR GHERKIN GENERATION:

1. Feature Description:
   - Always include a business value statement using the format:
     "As a [role], I want [feature], So that [benefit]"
   - Write from the user's perspective, not the developer's perspective
   - Focus on business capabilities, not technical implementation

2. Scenario Structure:
   - Use clear, descriptive scenario titles from the user's perspective
   - Keep scenarios focused on a single user flow or business rule
   - Limit scenarios to 3-7 steps for optimal readability

3. Given Steps (Preconditions):
   - Describe the initial state or context
   - Use high-level language like "a user with role 'admin' exists"
   - Reference test data setup through MCP tools (users, data states)
   - NEVER include UI implementation details

4. When Steps (User Actions):
   - Describe user actions at the behavior level
   - Use business language: "the user logs in" NOT "the user clicks the login button"
   - Focus on intent, not implementation
   - NEVER mention CSS selectors, XPath, or DOM elements

5. Then Steps (Expected Outcomes):
   - Assert business-observable results
   - Use clear, unambiguous language
   - Focus on what the user sees or experiences
   - NEVER reference HTTP status codes, API responses, or technical details

6. Tags for Organization:
   - @smoke: Critical happy-path scenarios that must always pass
   - @ui: Scenarios involving browser-based user interface testing
   - @api: Scenarios focused on API-level testing
   - @integration: Scenarios testing multiple system components together
   - Use custom domain tags like @authentication, @user-management as needed

7. Language Requirements:
   - Use business terminology that stakeholders understand
   - Avoid technical jargon, programming terms, or implementation details
   - Write in present tense
   - Be specific but avoid over-specification

STRICT PROHIBITIONS - NEVER include in Gherkin:
- CSS selectors (.btn-primary, #login-button, .form-control)
- XPath expressions (//div[@class='container'], //button[text()='Submit'])
- DOM coordinates (click at x=100, y=200)
- HTTP status codes (assert 200 OK, check for 404)
- API implementation details (POST /api/users, JSON response body)
- Programming constructs (if statements, loops, variables)
- Technical architecture details (database queries, caching, etc.)

Remember: Gherkin describes the WHAT (business behavior), not the HOW (technical implementation).
Step definitions will handle the implementation details using page objects and API clients.
"""

# ============================================================================
# USER PROMPT TEMPLATE: Instructs LLM to Generate Gherkin from Exploration
# ============================================================================

USER_PROMPT_TEMPLATE = """Analyze the following browser exploration session and generate a complete Gherkin feature file with business-readable scenarios.

EXPLORATION LOG:
{exploration_log}

INSTRUCTIONS:

1. Review the exploration log, which contains:
   - Page navigation events (URLs visited)
   - User interactions (clicks, text input, form submissions)
   - Page state observations (elements found, content displayed)
   - Any assertions or validations performed

2. Generate a complete Gherkin feature that includes:
   - A Feature description with business value statement (As a...I want...So that...)
   - One or more Scenarios covering the observed behavior
   - Appropriate tags for test categorization (@smoke, @ui, @api, etc.)

3. Apply BDD best practices:
   - Use high-level Given/When/Then steps that describe user actions and outcomes
   - Focus on WHAT the user does and sees, not HOW the UI is implemented
   - Keep steps business-readable (understandable by non-technical stakeholders)
   - Limit scenarios to 3-7 steps for clarity

4. STRICTLY AVOID in generated Gherkin:
   - CSS selectors (e.g., .btn-primary, #login-form, input[type='password'])
   - XPath expressions (e.g., //button[@id='submit'], //div[@class='error'])
   - Element coordinates (e.g., click at position x, y)
   - HTTP status codes (e.g., verify 200 response, check 404 error)
   - API endpoints or JSON structures (e.g., POST /api/login, response.data.token)
   - Technical implementation details of any kind

5. Example of GOOD Gherkin (high-level, business-readable):
   ```gherkin
   Feature: User Authentication
     As a registered user
     I want to log in to the application
     So that I can access my personalized dashboard

     @smoke @ui
     Scenario: Successful login with valid credentials
       Given the user is on the login page
       And a user with role "customer" and email "test@example.com" exists
       When the user logs in with valid credentials
       Then the user is redirected to the dashboard
       And the user sees a welcome message with their name
       And the user can access their account settings
   ```

6. Example of BAD Gherkin (too technical, implementation-focused):
   ```gherkin
   # DON'T DO THIS - Too much implementation detail
   Scenario: Login
     Given I navigate to "https://example.com/login"
     When I type "test@example.com" in "#email-input"
     And I type "password123" in "input[name='password']"
     And I click the button at coordinates (150, 300)
     Then the HTTP response code is 200
     And the JSON response contains {"status": "success"}
   ```

OUTPUT REQUIREMENTS:
- Return ONLY the Gherkin feature text
- Do NOT include any explanations, comments, or metadata outside the Gherkin syntax
- Do NOT wrap the output in markdown code blocks
- Start with "Feature:" and follow standard Gherkin syntax
- Use proper indentation (2 spaces for scenario body, 4 spaces for steps)

Generate the Gherkin feature now:
"""

# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "SYSTEM_PROMPT",
    "USER_PROMPT_TEMPLATE",
]
