# LLM Integration Guide

## Overview

This guide covers the integration of Large Language Models (LLMs) with the test automation framework to accelerate test authoring and improve test coverage through AI-assisted scenario generation.

### Purpose

The LLM integration serves as an **authoring assistant** to help QA engineers:
- Generate business-readable Gherkin scenarios from browser exploration sessions
- Discover edge cases and test variations that might be overlooked
- Draft initial test scenarios that humans review and refine
- Accelerate the test authoring process while maintaining quality standards

### Philosophy: Human-in-the-Loop

**Critical Principle**: LLMs are assistants, not autonomous executors.

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  LLM Agent  │  →    │   Generate  │  →    │   Human     │  →    │   Commit    │
│  Explores   │       │   Draft     │       │   Review &  │       │   to VCS    │
│  Browser    │       │   Gherkin   │       │   Approve   │       │             │
└─────────────┘       └─────────────┘       └─────────────┘       └─────────────┘
```

**What LLMs DO**:
- Explore web applications via Playwright MCP server
- Generate draft Gherkin scenarios based on observations
- Suggest edge cases and test variations
- Identify gaps in existing test coverage

**What LLMs DO NOT DO**:
- Execute tests autonomously without human oversight
- Modify production code or test infrastructure
- Make decisions about test strategy or coverage goals
- Commit code directly to version control

### Workflow Summary

1. **Configure** LLM provider (Ollama local or OpenAI-compatible hosted)
2. **Start** Playwright MCP server for browser control
3. **Explore** application with LLM-driven browser automation
4. **Generate** draft Gherkin scenarios from exploration log
5. **Review** generated scenarios for accuracy and business readability
6. **Implement** step definitions for new scenarios
7. **Validate** scenarios pass when executed with pytest
8. **Commit** approved scenarios and step definitions to repository

---

## Supported LLM Providers

The framework supports two primary LLM provider types, each with distinct advantages:

### Ollama (Local Development)

**Best for**: Development, experimentation, unlimited usage without API costs

**Advantages**:
- ✅ No API costs - unlimited requests
- ✅ No internet connectivity required
- ✅ Full data privacy - no data leaves your machine
- ✅ Fast iteration during development
- ✅ Support for multiple open-source models

**Requirements**:
- Local installation of Ollama: https://ollama.ai
- Recommended: NVIDIA GPU with 8GB+ VRAM for optimal performance
- Minimum: 16GB system RAM for CPU-only usage

**Supported Models**:
- `llama2` - General purpose, good for exploration and generation
- `codellama` - Optimized for code-related tasks
- `mistral` - Fast and efficient, good balance of speed and quality
- `mixtral` - High quality, larger model for complex scenarios
- `gemma` - Google's open model, good for structured output

**Installation**:
```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Install Ollama (Windows)
# Download from https://ollama.ai/download/windows

# Pull a model
ollama pull llama2

# Verify installation
ollama list
```

**Configuration**:
```bash
# .env file
LLM_PROVIDER=ollama
LLM_MODEL=llama2
LLM_BASE_URL=http://localhost:11434  # Default Ollama endpoint
```

**Performance Considerations**:
- GPU acceleration significantly improves response time (2-5s vs 30-60s)
- Larger models (70B parameters) require more resources but produce better results
- Smaller models (7B-13B parameters) sufficient for most test generation tasks

### OpenAI-Compatible APIs (Hosted)

**Best for**: Production-quality generation, team environments, CI/CD integration

**Advantages**:
- ✅ Highest quality output (GPT-4, Claude 3)
- ✅ No local resource requirements
- ✅ Consistent performance across team
- ✅ Support for very large context windows
- ✅ Access to latest model improvements

**Supported Providers**:

#### OpenAI
- Models: `gpt-4-turbo-preview`, `gpt-4`, `gpt-3.5-turbo`
- API endpoint: `https://api.openai.com/v1`
- Authentication: API key

#### Azure OpenAI Service
- Models: GPT-4, GPT-3.5-turbo (deployed models)
- API endpoint: `https://<your-resource>.openai.azure.com`
- Authentication: API key or Azure AD

#### Anthropic Claude (via OpenAI-compatible endpoint)
- Models: `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- Requires OpenAI-compatible proxy or direct Anthropic SDK

**Configuration**:
```bash
# .env file for OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
LLM_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx
LLM_BASE_URL=https://api.openai.com/v1  # Optional: defaults to OpenAI

# .env file for Azure OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=your-azure-api-key
LLM_BASE_URL=https://your-resource.openai.azure.com
LLM_API_VERSION=2024-02-15-preview  # Azure-specific
```

**Cost Considerations**:
- GPT-4: ~$0.03 per 1K input tokens, ~$0.06 per 1K output tokens
- GPT-3.5-turbo: ~$0.0005 per 1K input tokens, ~$0.0015 per 1K output tokens
- Typical scenario generation: 2,000-5,000 tokens = $0.15-$0.50 per session (GPT-4)
- Use token counting to estimate costs before exploration

### Provider Selection Guide

| Criterion | Ollama (Local) | OpenAI (Hosted) |
|-----------|----------------|-----------------|
| **Cost** | Free (hardware investment) | Pay per token |
| **Quality** | Good (7B-70B models) | Excellent (GPT-4) |
| **Speed** | Fast with GPU | Very fast |
| **Privacy** | Complete (local) | Shared with provider |
| **Setup Complexity** | Medium | Low |
| **Best Use Case** | Development, experimentation | Production, team use |

**Recommendation**:
- Start with **Ollama + llama2** for learning and experimentation
- Upgrade to **OpenAI GPT-4** for production-quality scenario generation
- Use **GPT-3.5-turbo** for cost-effective bulk generation

---

## Environment Configuration

### Required Environment Variables

Create a `.env` file in the project root or export these variables:

```bash
# LLM Provider Configuration
LLM_PROVIDER=ollama              # Options: 'ollama', 'openai'
LLM_MODEL=llama2                 # Model name (provider-specific)
LLM_API_KEY=                     # Required for hosted providers (OpenAI, Azure)
LLM_BASE_URL=                    # Optional: custom endpoint URL
LLM_TEMPERATURE=0.7              # Optional: creativity (0.0-1.0, default 0.7)
LLM_MAX_TOKENS=2048              # Optional: max output tokens (default 2048)

# Playwright MCP Server Configuration
PLAYWRIGHT_MCP_URL=http://localhost:8001  # Playwright MCP server endpoint
PLAYWRIGHT_MCP_TIMEOUT=300                # Exploration timeout in seconds

# FastAPI MCP Server Configuration (if using for test data)
FASTAPI_MCP_URL=http://localhost:8000
FASTAPI_MCP_TOKEN=your-mcp-auth-token
```

### Configuration Examples

#### Local Development with Ollama
```bash
# .env
LLM_PROVIDER=ollama
LLM_MODEL=mistral
LLM_BASE_URL=http://localhost:11434
PLAYWRIGHT_MCP_URL=http://localhost:8001
```

#### Team Environment with OpenAI
```bash
# .env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
LLM_API_KEY=${OPENAI_API_KEY}  # From environment or secrets manager
LLM_TEMPERATURE=0.5             # Lower for more deterministic output
PLAYWRIGHT_MCP_URL=http://localhost:8001
```

### Loading Configuration in Python

```python
# llm/config.py (example)
from pydantic_settings import BaseSettings

class LLMSettings(BaseSettings):
    llm_provider: str = "ollama"
    llm_model: str = "llama2"
    llm_api_key: str | None = None
    llm_base_url: str | None = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = LLMSettings()
```

---

## LLM Client Architecture

### Component Overview

```
llm/
├── client.py                    # Abstract LLM client interface
├── providers/
│   ├── ollama.py               # Ollama provider implementation
│   └── openai.py               # OpenAI-compatible provider
├── prompts/
│   ├── gherkin_generation.py   # Prompts for scenario generation
│   └── edge_case_suggestions.py # Prompts for edge case discovery
└── workflows/
    ├── scenario_generator.py   # End-to-end exploration workflow
    └── review_pipeline.py      # Human review integration
```

### Abstract LLM Client

The `LLMClient` class provides a provider-agnostic interface:

```python
# llm/client.py (conceptual)
from abc import ABC, abstractmethod

class LLMClient(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate text completion from prompt."""
        pass
    
    @abstractmethod
    def generate_streaming(self, prompt: str, **kwargs):
        """Generate text with streaming response."""
        pass
    
    def generate_scenarios(self, context: dict) -> str:
        """Generate Gherkin scenarios from exploration context."""
        prompt = self._build_scenario_prompt(context)
        return self.generate(prompt)
    
    def suggest_edge_cases(self, feature: str, existing_scenarios: list) -> list:
        """Suggest edge cases not covered by existing scenarios."""
        prompt = self._build_edge_case_prompt(feature, existing_scenarios)
        response = self.generate(prompt)
        return self._parse_edge_cases(response)
```

### Provider Implementations

#### Ollama Provider

```python
# llm/providers/ollama.py (conceptual)
import ollama

class OllamaProvider(LLMClient):
    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.client = ollama.Client(host=base_url)
    
    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            temperature=kwargs.get("temperature", 0.7),
            options={"num_predict": kwargs.get("max_tokens", 2048)}
        )
        return response['response']
```

#### OpenAI Provider

```python
# llm/providers/openai.py (conceptual)
from openai import OpenAI

class OpenAIProvider(LLMClient):
    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)
    
    def generate(self, prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 2048)
        )
        return response.choices[0].message.content
```

### Factory Pattern for Provider Selection

```python
# llm/factory.py (conceptual)
def create_llm_client(provider: str, **config) -> LLMClient:
    """Factory function to create appropriate LLM client."""
    if provider == "ollama":
        return OllamaProvider(
            model=config.get("model", "llama2"),
            base_url=config.get("base_url", "http://localhost:11434")
        )
    elif provider == "openai":
        return OpenAIProvider(
            model=config["model"],
            api_key=config["api_key"],
            base_url=config.get("base_url")
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
```

---

## Exploration and Scenario Generation Workflow

### Complete 8-Step Process

#### Step 1: Start Playwright MCP Server

The Playwright MCP server enables LLM agents to control a real browser for exploration.

```bash
# Terminal 1: Start Playwright MCP server
cd mcp_servers/playwright_mcp
python -m uvicorn main:app --port 8001 --reload

# Verify server is running
curl http://localhost:8001/health
```

**What this provides**:
- Browser automation tools accessible via JSON-RPC
- Session management for multiple concurrent explorations
- Screenshot and page structure capture
- Gherkin generation from exploration history

#### Step 2: Configure LLM Provider

```bash
# Set environment variables
export LLM_PROVIDER=ollama
export LLM_MODEL=llama2
export PLAYWRIGHT_MCP_URL=http://localhost:8001

# Or create .env file
cat > .env << EOF
LLM_PROVIDER=ollama
LLM_MODEL=llama2
PLAYWRIGHT_MCP_URL=http://localhost:8001
EOF
```

#### Step 3: Run Exploration Workflow

```python
# explore_app.py (example script)
from llm.workflows.scenario_generator import explore_and_generate

# Provide high-level exploration goal
result = explore_and_generate(
    url='https://app.example.com/register',
    objective='Explore user registration flow and identify validation rules and edge cases',
    max_interactions=20,  # Limit exploration depth
    focus_areas=['form validation', 'error messages', 'success flows']
)

print(f"Generated feature file: {result['feature_file']}")
print(f"Scenarios created: {len(result['scenarios'])}")
print(f"Assumptions: {result['assumptions']}")
print(f"Open questions: {result['open_questions']}")
```

#### Step 4: LLM Exploration Process

The LLM agent performs these actions automatically:

**4a. Navigate to Target URL**
```python
# LLM calls via MCP client
mcp.call_tool("navigate", {"url": "https://app.example.com/register"})
```

**4b. Analyze Page Structure**
```python
# Get semantic structure of the page
page_structure = mcp.call_tool("get_page_structure", {})
# Returns: DOM with ARIA roles, labels, form fields, buttons
```

**4c. Identify Interactive Elements**
- Form fields (email, password, name, etc.)
- Submit buttons
- Validation messages
- Navigation links
- Modal dialogs

**4d. Perform Exploration Interactions**
```python
# Example exploration sequence
mcp.call_tool("type", {"selector": "input[name='email']", "text": "test@example.com"})
mcp.call_tool("type", {"selector": "input[name='password']", "text": "short"})
mcp.call_tool("click", {"selector": "button[type='submit']"})
mcp.call_tool("screenshot", {"name": "validation_error"})
```

**4e. Observe Responses and State Changes**
- Validation error messages displayed
- Form field highlighting (red borders, error icons)
- Success messages and redirects
- Network requests (API calls logged)

**4f. Test Edge Cases Dynamically**
- Invalid email formats
- Short/long passwords
- Special characters in fields
- Empty required fields
- Boundary values (e.g., 1000-character input)

**4g. Capture Evidence**
- Screenshot at each significant state
- HTML snapshots of error messages
- Network request/response logs
- Console errors and warnings

#### Step 5: Gherkin Generation

After exploration, the LLM analyzes the log and generates structured scenarios:

**5a. Parse Exploration Log**
```python
exploration_log = [
    {"action": "navigate", "url": "https://app.example.com/register"},
    {"action": "type", "selector": "input[name='email']", "value": "invalid-email"},
    {"action": "click", "selector": "button[type='submit']"},
    {"observation": "error_message", "text": "Please enter a valid email address"},
    # ... more interactions
]
```

**5b. Generate High-Level Gherkin**

The LLM converts low-level interactions into business-readable steps:

```gherkin
# Generated by: llama2 v0.2
# Timestamp: 2024-01-15 14:30:00 UTC
# Model temperature: 0.7
# Exploration session: exp-abc123
# Assumptions:
#   - Email validation follows RFC 5322 standard
#   - Password minimum length is 8 characters (observed in validation)
#   - Password must contain at least one uppercase, one lowercase, one digit
#   - Username is optional during registration
# Open Questions:
#   - Does registration send a confirmation email?
#   - Are there rate limits on registration attempts?
#   - Is there a maximum password length?
#   - Does the system check for password breaches (HaveIBeenPwned)?

Feature: User Registration
  As a new user
  I want to register for an account
  So that I can access the application features

  Background:
    Given the user is on the registration page

  Scenario: Successful registration with valid credentials
    When the user provides a valid email address
    And the user provides a strong password
    And the user submits the registration form
    Then the user account should be created successfully
    And the user should be redirected to the dashboard
    And a welcome message should be displayed

  Scenario: Registration fails with invalid email format
    When the user provides an email address with invalid format
      | invalid_email        |
      | notanemail           |
      | @missinglocal.com    |
      | missing@domain       |
    And the user submits the registration form
    Then an email validation error should be displayed
    And the registration form should remain visible
    And the account should not be created

  Scenario: Registration fails with weak password
    When the user provides a valid email address
    And the user provides a password that is too short
    And the user submits the registration form
    Then a password strength error should be displayed
    And the error should explain password requirements

  Scenario Outline: Password validation rules
    When the user provides a valid email address
    And the user provides password "<password>"
    And the user submits the registration form
    Then validation result should be "<result>"
    And error message should contain "<message_fragment>"

    Examples:
      | password      | result  | message_fragment        |
      | short         | invalid | at least 8 characters   |
      | alllowercase1 | invalid | uppercase letter        |
      | ALLUPPERCASE1 | invalid | lowercase letter        |
      | NoDigitsHere  | invalid | contain a digit         |
      | Valid123Pass  | valid   |                         |

  Scenario: Registration with already registered email
    Given a user account already exists with email "existing@example.com"
    When the user provides email "existing@example.com"
    And the user provides a valid password
    And the user submits the registration form
    Then an error indicating email already exists should be displayed
    And the user should be prompted to login instead

  Scenario: Registration form field validation on blur
    When the user enters an invalid email in the email field
    And the user focuses on another field
    Then real-time validation error should appear below the email field
    And the email field should be highlighted with error styling
```

**5c. Add Metadata and Context**

Each generated feature includes:
- **Model information**: Which LLM and version generated it
- **Timestamp**: When the exploration occurred
- **Assumptions**: What the LLM inferred about business rules
- **Open questions**: Gaps that require human clarification
- **Session ID**: Link back to exploration log for traceability

#### Step 6: Human Review Process

**6a. Review Checklist**

Developers should validate:

✅ **Business Readability**
- Can a non-technical stakeholder understand the scenarios?
- Are steps at the appropriate abstraction level?
- Is domain language used (not technical jargon)?

✅ **Step Granularity**
- Are steps too low-level (e.g., "click button at coordinates")?
- Are steps too high-level (e.g., "complete entire workflow")?
- Do steps map to reusable step definitions?

✅ **Coverage Completeness**
- Are happy paths covered?
- Are edge cases and error scenarios included?
- Are boundary conditions tested (min/max values)?
- Are integration points validated?

✅ **Assumption Accuracy**
- Do the stated assumptions match actual business rules?
- Are there unstated assumptions that should be documented?
- Do assumptions need validation from product owners?

✅ **Scenario Uniqueness**
- Does this duplicate existing test coverage?
- Does it provide value beyond current tests?
- Should it replace an existing brittle test?

**6b. Common Refinements**

| Issue | Example | Refinement |
|-------|---------|------------|
| **Too technical** | "When the user clicks button with ID 'submit-btn'" | "When the user submits the form" |
| **Too vague** | "When the user does the thing" | "When the user enters their payment details" |
| **Implementation detail** | "When the API returns status code 201" | "When the account is created successfully" |
| **Brittle selector** | "When the user clicks the third button" | "When the user clicks the Save button" |

**6c. Review Workflow**

```bash
# 1. Review generated feature file
vim tests/features/user_registration.feature

# 2. Check for existing coverage
grep -r "registration" tests/features/

# 3. Validate assumptions with product owner (if needed)
# Document in feature file or team wiki

# 4. Refine Gherkin to match team conventions
# Ensure consistency with existing feature files
```

#### Step 7: Step Definition Implementation

**7a. Identify Missing Step Definitions**

```bash
# Run pytest-bdd to see which steps are undefined
pytest tests/features/user_registration.feature --collect-only

# Output will show:
# StepDefinitionNotFoundError: Step definition not found for step:
#   "Given the user is on the registration page"
```

**7b. Implement Step Definitions**

```python
# tests/step_definitions/registration_steps.py
from pytest_bdd import given, when, then, parsers
from tests.pages.registration_page import RegistrationPage

@given("the user is on the registration page")
def user_on_registration_page(registration_page: RegistrationPage):
    """Navigate to registration page."""
    registration_page.navigate()

@when("the user provides a valid email address")
def user_provides_valid_email(registration_page: RegistrationPage, faker):
    """Enter a valid email address using Faker."""
    email = faker.email()
    registration_page.enter_email(email)

@when(parsers.parse('the user provides password "{password}"'))
def user_provides_password(registration_page: RegistrationPage, password: str):
    """Enter the specified password."""
    registration_page.enter_password(password)

@when("the user submits the registration form")
def user_submits_form(registration_page: RegistrationPage):
    """Click submit button."""
    registration_page.submit()

@then("the user account should be created successfully")
def account_created_successfully(dashboard_page: DashboardPage):
    """Verify redirect to dashboard."""
    dashboard_page.wait_for_page_load()
    assert dashboard_page.is_displayed()
```

**7c. Delegate to Page Objects**

```python
# tests/pages/registration_page.py
from playwright.sync_api import Page
from tests.pages.base_page import BasePage

class RegistrationPage(BasePage):
    # Stable locators using ARIA roles and test IDs
    EMAIL_INPUT = "input[name='email']"
    PASSWORD_INPUT = "input[name='password']"
    SUBMIT_BUTTON = "button[type='submit']"
    ERROR_MESSAGE = "[data-testid='error-message']"
    
    def navigate(self):
        """Navigate to registration page."""
        self.page.goto(f"{self.base_url}/register")
        self.wait_for_page_load()
    
    def enter_email(self, email: str):
        """Enter email address."""
        self.page.fill(self.EMAIL_INPUT, email)
    
    def enter_password(self, password: str):
        """Enter password."""
        self.page.fill(self.PASSWORD_INPUT, password)
    
    def submit(self):
        """Submit the registration form."""
        self.page.click(self.SUBMIT_BUTTON)
    
    def get_error_message(self) -> str:
        """Get validation error message."""
        return self.page.text_content(self.ERROR_MESSAGE)
```

**7d. Use MCP Tools for Test Data**

```python
# Use FastAPI MCP server for test data
@given("a user account already exists with email \"existing@example.com\"")
def existing_user_account(mcp_client):
    """Seed a test user via MCP."""
    mcp_client.seed_user(
        email="existing@example.com",
        password="ExistingPass123",
        role="customer"
    )
```

#### Step 8: Validate and Commit

**8a. Run Tests Locally**

```bash
# Run the new feature file
pytest tests/features/user_registration.feature -v

# Run with Allure reporting
pytest tests/features/user_registration.feature --alluredir=allure-results

# View Allure report
allure serve allure-results
```

**8b. Fix Failures**

- Debug failing steps with Playwright traces
- Refine selectors if elements not found
- Adjust assertions if expectations incorrect
- Update page objects for missing methods

**8c. Commit to Version Control**

```bash
# Stage the new files
git add tests/features/user_registration.feature
git add tests/step_definitions/registration_steps.py
git add tests/pages/registration_page.py  # If new

# Commit with descriptive message
git commit -m "Add LLM-generated user registration test scenarios

- Covers happy path and validation edge cases
- Includes password strength validation
- Tests duplicate email handling
- Generated by llama2, reviewed and refined by [Your Name]
- All scenarios passing locally"

# Push to remote
git push origin feature/registration-tests
```

**8d. Create Pull Request**

In the PR description, document:
- LLM model used for generation
- Manual refinements made during review
- New page objects or step definitions added
- Coverage improvements (e.g., "Added 6 new scenarios covering password validation")

---

## LLM Capabilities

### 1. Gherkin Scenario Generation

**Input**: Browser exploration log with interactions and observations

**Output**: Business-readable Gherkin feature file with scenarios

**Prompt Strategy**:
```python
# llm/prompts/gherkin_generation.py (conceptual)
GHERKIN_GENERATION_PROMPT = """
You are an experienced QA engineer writing behavior-driven tests.

Based on the browser exploration log below, generate Gherkin scenarios that:
- Use high-level business language (no CSS selectors, coordinates, or technical details)
- Focus on user actions and outcomes, not implementation
- Follow Given/When/Then structure strictly
- Include both happy path and edge cases observed
- Use Scenario Outline for data-driven cases with multiple examples
- Keep steps reusable and composable

IMPORTANT RULES:
- DO NOT include: CSS selectors, XPath, element IDs, pixel coordinates
- DO include: Business actions, user goals, expected outcomes
- Write for non-technical stakeholders to understand
- Each scenario should be independently executable

EXPLORATION LOG:
{exploration_log}

GENERATE:
A Feature file with 3-7 scenarios covering the observed behavior.
Include a metadata comment block with:
- Model and version
- Timestamp
- Assumptions made about business rules
- Open questions requiring human clarification
"""
```

**Example Usage**:
```python
from llm.client import create_llm_client
from llm.prompts.gherkin_generation import build_gherkin_prompt

llm = create_llm_client(provider="ollama", model="llama2")
prompt = build_gherkin_prompt(exploration_log=exploration_data)
feature_content = llm.generate(prompt, temperature=0.7)

# Save to file
with open("tests/features/generated_login.feature", "w") as f:
    f.write(feature_content)
```

### 2. Edge Case Suggestions

**Purpose**: Analyze existing test coverage and suggest missing edge cases

**Input**: 
- Feature name or user story
- Existing Gherkin scenarios
- Application domain knowledge

**Output**: List of edge case scenarios not yet covered

**Implementation**:
```python
# llm/workflows/edge_case_suggester.py (conceptual)
from llm.client import create_llm_client
from llm.prompts.edge_case_suggestions import build_edge_case_prompt

def suggest_edge_cases(feature: str, existing_scenarios_path: str) -> list[str]:
    """
    Analyze existing scenarios and suggest uncovered edge cases.
    
    Args:
        feature: Feature name or user story
        existing_scenarios_path: Path to existing .feature file
    
    Returns:
        List of suggested edge case descriptions
    """
    llm = create_llm_client()
    
    # Load existing scenarios
    with open(existing_scenarios_path, 'r') as f:
        existing_content = f.read()
    
    # Build prompt
    prompt = build_edge_case_prompt(
        feature_name=feature,
        existing_scenarios=existing_content
    )
    
    # Generate suggestions
    response = llm.generate(prompt, temperature=0.8)  # Higher creativity
    
    # Parse edge cases from response
    edge_cases = _parse_edge_cases(response)
    
    return edge_cases

# Example usage
edge_cases = suggest_edge_cases(
    feature='User Login',
    existing_scenarios_path='tests/features/authentication.feature'
)

for i, case in enumerate(edge_cases, 1):
    print(f"{i}. {case}")

# Output:
# 1. User attempts login with correct password but account is locked
# 2. User attempts login during system maintenance window
# 3. User attempts login with expired session token
# 4. User attempts login from blocked IP address
# 5. User attempts login with SQL injection in password field
```

**Edge Case Prompt Template**:
```python
EDGE_CASE_PROMPT = """
Analyze the following test scenarios for the "{feature_name}" feature.

EXISTING SCENARIOS:
{existing_scenarios}

As an experienced QA engineer, identify edge cases and boundary conditions that are NOT currently covered.

Focus on:
- Boundary values (min/max, empty, null)
- Error conditions and exceptional flows
- Concurrency and race conditions
- Security concerns (injection, auth bypass)
- Performance degradation scenarios
- Integration failure points
- Unexpected user behavior

Provide 5-10 edge case suggestions as a numbered list.
For each, briefly explain the scenario and why it's important to test.
"""
```

### 3. Test Variation Recommendations

**Purpose**: Suggest variations of existing tests for different contexts

**Use Cases**:
- Cross-browser variations (Chromium, Firefox, WebKit)
- Cross-platform variations (Desktop, Mobile, Tablet)
- Localization variations (Different languages/locales)
- User role variations (Admin, User, Guest)
- Data volume variations (Empty state, Large datasets)

**Example**:
```python
# Generate mobile-specific variations
from llm.workflows.variation_generator import generate_variations

variations = generate_variations(
    base_scenario='tests/features/authentication.feature',
    variation_type='mobile',
    contexts=['iOS Safari', 'Android Chrome', 'Responsive breakpoints']
)

# Output: Mobile-specific scenarios like
# - Login with on-screen keyboard behavior
# - Password manager integration on mobile
# - Biometric authentication (Touch ID, Face ID)
# - App backgrounding during login flow
```

### 4. Scenario Prioritization

**Purpose**: Analyze and rank test scenarios by business impact and risk

**Implementation**:
```python
def prioritize_scenarios(feature_file: str) -> list[dict]:
    """
    Analyze scenarios and assign priority scores.
    
    Returns: List of scenarios with priority metadata
    [
        {
            "scenario": "User login with valid credentials",
            "priority": "CRITICAL",
            "rationale": "Happy path for authentication, blocks all user flows",
            "risk_level": "HIGH",
            "execution_frequency": "Every CI run"
        },
        ...
    ]
    """
    llm = create_llm_client()
    # Implementation details...
```

---

## Prompt Engineering Best Practices

### Effective Prompt Construction

**1. Provide Clear Objectives**

❌ Bad:
```python
prompt = "Generate tests for login"
```

✅ Good:
```python
prompt = """
Generate Gherkin scenarios for the user login feature that cover:
- Successful login with valid credentials
- Failed login with incorrect password
- Account lockout after multiple failed attempts
- Password reset flow
- "Remember me" functionality
- Session timeout handling

Focus on business-readable steps without implementation details.
"""
```

**2. Include Context and Constraints**

❌ Bad:
```python
prompt = "Write test for user registration"
```

✅ Good:
```python
prompt = """
Application: E-commerce platform
Authentication: OAuth2 with email/password
Constraints:
- Password must be 8-20 characters
- Email must be unique in system
- CAPTCHA required after 3 failed attempts

Generate registration test scenarios covering validation rules and edge cases.
Use Given/When/Then format at business level.
"""
```

**3. Use Few-Shot Examples**

Provide 1-2 example scenarios to establish format and style:

```python
# llm/prompts/gherkin_generation.py
GHERKIN_TEMPLATE = """
Generate Gherkin scenarios following this format:

EXAMPLE 1:
Feature: Shopping Cart
  Scenario: Add item to empty cart
    Given the user is logged in
    And the shopping cart is empty
    When the user adds a product to the cart
    Then the cart should contain 1 item
    And the cart total should match the product price

EXAMPLE 2:
Feature: Shopping Cart
  Scenario: Remove item from cart
    Given the user has 2 items in the cart
    When the user removes one item
    Then the cart should contain 1 item
    And the cart total should be updated

Now generate similar scenarios for: {feature_description}
"""
```

**4. Specify Output Format**

Be explicit about structure:

```python
prompt = """
Generate output in this exact format:

# Metadata (comment block)
# Model: [model name]
# Timestamp: [ISO 8601]
# Assumptions: [bullet list]
# Open Questions: [bullet list]

Feature: [Feature Name]
  [Feature description]

  Background:
    [Shared preconditions]

  Scenario: [Scenario name]
    Given [precondition]
    When [action]
    Then [expected outcome]
"""
```

### Prompt Templates Library

```python
# llm/prompts/templates.py
TEMPLATES = {
    "gherkin_generation": {
        "system": "You are an expert QA engineer writing BDD scenarios.",
        "user": """
        Based on this exploration log, generate Gherkin scenarios:
        
        EXPLORATION LOG:
        {exploration_log}
        
        REQUIREMENTS:
        - Business-readable language
        - No technical implementation details
        - Include happy path and edge cases
        - Use Scenario Outline for data-driven tests
        
        OUTPUT: Complete Feature file with 3-7 scenarios
        """
    },
    
    "edge_case_discovery": {
        "system": "You are a security and quality expert finding edge cases.",
        "user": """
        Analyze these scenarios and find uncovered edge cases:
        
        FEATURE: {feature_name}
        EXISTING SCENARIOS:
        {existing_scenarios}
        
        Suggest 5-10 edge cases covering:
        - Boundary conditions
        - Error scenarios
        - Security concerns
        - Race conditions
        - Integration failures
        """
    },
    
    "step_definition_generation": {
        "system": "You are a test automation engineer writing step definitions.",
        "user": """
        Generate pytest-bdd step definitions for these Gherkin steps:
        
        STEPS:
        {gherkin_steps}
        
        REQUIREMENTS:
        - Use @given, @when, @then decorators
        - Delegate to page object methods
        - Include type hints
        - Add docstrings
        
        OUTPUT: Python code for tests/step_definitions/
        """
    }
}
```

### Token Counting and Optimization

**Why Token Counting Matters**:
- Control API costs (for hosted providers)
- Stay within model context limits
- Optimize prompt efficiency

**Implementation**:
```python
# llm/utils/token_counter.py (conceptual)
import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text for a specific model.
    
    Args:
        text: Input text
        model: Model name (e.g., "gpt-4", "gpt-3.5-turbo")
    
    Returns:
        Token count
    """
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def estimate_cost(prompt: str, expected_output_tokens: int, model: str) -> float:
    """
    Estimate API cost for a generation request.
    
    Args:
        prompt: Input prompt
        expected_output_tokens: Estimated response length
        model: Model name
    
    Returns:
        Estimated cost in USD
    """
    PRICING = {
        "gpt-4-turbo-preview": {"input": 0.01 / 1000, "output": 0.03 / 1000},
        "gpt-3.5-turbo": {"input": 0.0005 / 1000, "output": 0.0015 / 1000}
    }
    
    input_tokens = count_tokens(prompt, model)
    rates = PRICING.get(model, PRICING["gpt-4-turbo-preview"])
    
    cost = (input_tokens * rates["input"]) + (expected_output_tokens * rates["output"])
    return cost

# Usage example
prompt = build_gherkin_prompt(exploration_log)
tokens = count_tokens(prompt, "gpt-4")
estimated_cost = estimate_cost(prompt, expected_output_tokens=1500, model="gpt-4-turbo-preview")

print(f"Prompt tokens: {tokens}")
print(f"Estimated cost: ${estimated_cost:.4f}")

# Output:
# Prompt tokens: 3,245
# Estimated cost: $0.0774
```

**Optimization Strategies**:

1. **Compress Exploration Logs**
   - Remove duplicate observations
   - Summarize repetitive interactions
   - Keep only significant state changes

2. **Use Truncation for Large Pages**
   ```python
   def truncate_page_structure(html: str, max_tokens: int = 1000) -> str:
       """Keep only interactive elements, remove decorative content."""
       # Extract forms, buttons, inputs, links
       # Discard styling, scripts, static content
   ```

3. **Stream Responses**
   - For long generations, use streaming to show progress
   - Early termination if output quality is poor

---

## LLM Integration with CI/CD

### Development vs. CI/CD Behavior

**Key Principle**: LLM generation is a **development-time activity**, not a runtime requirement.

```
┌─────────────────────┐         ┌─────────────────────┐
│   DEVELOPMENT       │         │   CI/CD PIPELINE    │
├─────────────────────┤         ├─────────────────────┤
│ ✅ LLM enabled      │         │ ❌ No LLM required  │
│ ✅ Playwright MCP   │         │ ❌ No Playwright    │
│    server running   │         │    MCP needed       │
│ ✅ Exploration and  │         │ ✅ Execute pytest   │
│    generation       │         │    tests only       │
│ ✅ Human review     │         │ ✅ FastAPI MCP for  │
│ ✅ Commit scenarios │         │    test data        │
└─────────────────────┘         └─────────────────────┘
```

### CI/CD Pipeline Configuration

**GitHub Actions Workflow** (excerpt):

```yaml
# .github/workflows/test.yml
name: Test Execution

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      # Only FastAPI MCP server in CI (for test data)
      fastapi-mcp:
        image: python:3.11-slim
        env:
          DATABASE_URL: ${{ secrets.TEST_DB_URL }}
          MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
        ports:
          - 8000:8000
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium
      
      # NO LLM-related steps in CI
      # Tests run against committed .feature files
      
      - name: Run pytest tests
        env:
          BASE_URL: ${{ secrets.TEST_BASE_URL }}
          API_BASE_URL: ${{ secrets.TEST_API_BASE_URL }}
          FASTAPI_MCP_URL: http://localhost:8000
          FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
          # NO LLM_PROVIDER, NO PLAYWRIGHT_MCP_URL
        run: |
          pytest tests/ \
            --alluredir=allure-results \
            --browser=chromium \
            --headed=false \
            -n auto
      
      - name: Generate Allure Report
        if: always()
        run: allure generate allure-results -o allure-report
      
      - name: Publish Allure Report
        if: always()
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./allure-report
```

### Optional: LLM-Powered PR Comments

For teams wanting LLM assistance in CI, consider:

**Scenario**: LLM analyzes failed tests and suggests fixes

```yaml
# .github/workflows/llm-analysis.yml (optional)
name: LLM Test Analysis

on:
  workflow_run:
    workflows: ["Test Execution"]
    types:
      - completed

jobs:
  analyze-failures:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    
    steps:
      - name: Download test results
        uses: actions/download-artifact@v3
        with:
          name: test-results
      
      - name: Analyze with LLM
        env:
          LLM_PROVIDER: openai
          LLM_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python scripts/analyze_failures.py \
            --results test-results/ \
            --output analysis.md
      
      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const analysis = fs.readFileSync('analysis.md', 'utf8');
            
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## LLM Test Failure Analysis\n\n${analysis}`
            });
```

**Important**: This is opt-in and should be carefully reviewed before enabling.

---

## Best Practices

### 1. Always Review LLM-Generated Content

**Why**: LLMs can hallucinate business rules or miss context that humans understand.

**Review Checklist**:
- [ ] Scenarios align with actual business requirements
- [ ] No invented features or behaviors
- [ ] Assumptions documented and validated
- [ ] Steps are reusable and at correct abstraction level
- [ ] No security-sensitive data in examples

### 2. Include Metadata in Generated Features

**Template**:
```gherkin
# LLM Metadata
# Generated by: gpt-4-turbo-preview
# Timestamp: 2024-01-15T14:30:00Z
# Session ID: exp-abc123def456
# Human reviewer: jane.doe@company.com
# Reviewed on: 2024-01-15T15:45:00Z
# Assumptions:
#   - Email validation uses RFC 5322
#   - Password requires 8+ chars, mixed case, digit
# Open Questions:
#   - Confirm password reset email template
#   - Validate account lockout policy (3 attempts?)

Feature: User Registration
  # ... scenarios ...
```

**Benefits**:
- Traceability: Link back to exploration session
- Accountability: Know who reviewed and approved
- Context: Understand assumptions for future maintainers
- Debugging: Investigate if scenarios fail unexpectedly

### 3. Start Simple, Increase Complexity Gradually

**Phase 1: Single Page Exploration**
```python
# Start with a single form
explore_and_generate(
    url='https://app.example.com/login',
    objective='Test login form validation'
)
```

**Phase 2: Multi-Step Flows**
```python
# Expand to complete user journey
explore_and_generate(
    url='https://app.example.com/register',
    objective='Complete registration and first-time setup wizard'
)
```

**Phase 3: Complex Scenarios**
```python
# Advanced workflows with state dependencies
explore_and_generate(
    url='https://app.example.com/checkout',
    objective='Complete purchase flow with coupon code and guest checkout',
    preconditions={'cart_items': 3, 'user_type': 'guest'}
)
```

### 4. Use Local Ollama for Experimentation

**Benefits**:
- Zero API costs during learning phase
- Fast iteration on prompt engineering
- No data privacy concerns
- Unlimited usage for testing

**When to Switch to GPT-4**:
- Scenarios require high quality (customer-facing features)
- Complex business logic needs accurate interpretation
- Team collaboration requires consistent output quality
- Budget allows for API costs

### 5. Version Control Prompt Templates

**Why**: Reproducibility and continuous improvement

**Structure**:
```
llm/prompts/
├── README.md              # Documentation of prompt versions
├── v1_gherkin_basic.py    # Initial version
├── v2_gherkin_with_metadata.py  # Added metadata requirements
└── v3_gherkin_edge_cases.py     # Enhanced edge case coverage
```

**Track Performance**:
```python
# Document prompt effectiveness
PROMPT_VERSION = "v3_gherkin_edge_cases"
PROMPT_METRICS = {
    "acceptance_rate": 0.85,  # 85% of generated scenarios accepted
    "manual_edits": 2.3,       # Average edits per scenario
    "coverage_improvement": 0.35  # 35% more edge cases found
}
```

### 6. Track LLM-Generated vs. Human-Authored Tests

**Tagging Strategy**:
```gherkin
@llm-generated @reviewed
Feature: User Registration
  # ... scenarios ...

@human-authored
Feature: Payment Processing
  # ... scenarios ...
```

**Benefits**:
- Measure LLM contribution to test suite
- Analyze which scenarios tend to fail (LLM vs. human)
- Identify areas where LLM excels or struggles
- Report on ROI of LLM integration

### 7. Maintain a Human Review Workflow

**Process**:
1. LLM generates draft → Save to `features/drafts/`
2. Developer reviews → Refine and move to `features/`
3. Implement step definitions → Run tests locally
4. Tests pass → Create PR with review checklist
5. Team review → Approve and merge
6. Track metrics → Acceptance rate, edit count, time saved

**Review Template**:
```markdown
## LLM-Generated Scenario Review

**Feature**: User Registration
**Generated by**: llama2
**Date**: 2024-01-15
**Reviewer**: Jane Doe

### Review Checklist
- [x] Business readability verified
- [x] Assumptions validated with product owner
- [x] Steps match team conventions
- [x] No duplicate coverage
- [x] Step definitions implemented
- [x] Tests passing locally

### Changes Made
- Refined step: "user clicks submit" → "user submits the registration form"
- Added missing edge case: "registration with existing email"
- Corrected assumption: Password length is 8-20, not 8-16

### Approval
✅ Approved for merge
```

---

## Limitations and Constraints

### LLM Cannot Execute Tests Autonomously

**Limitation**: LLMs generate scenarios but do not run pytest or validate results.

**Why**: 
- Test execution requires deterministic environment setup
- Results must be reliable and reproducible
- LLMs lack access to test infrastructure (browsers, APIs, databases)

**Implication**: Human developers must implement step definitions and validate tests pass.

### Generated Scenarios Require Human Approval

**Limitation**: LLMs may misunderstand business logic or hallucinate requirements.

**Example Issues**:
- Inventing features that don't exist
- Misinterpreting validation rules
- Creating scenarios that conflict with existing tests
- Using incorrect domain terminology

**Mitigation**: Mandatory human review before committing to version control.

### LLM May Misunderstand Complex Business Logic

**Limitation**: LLMs lack deep domain knowledge and may oversimplify.

**Examples**:
- Financial calculations with tax rules
- Compliance workflows (GDPR, HIPAA)
- Multi-tenant authorization logic
- Complex state machines

**Mitigation**:
- Provide domain context in prompts
- Include business rules documentation in exploration context
- Have domain experts review generated scenarios
- Use LLM for happy path, manually author complex edge cases

### Exploration Limited to Publicly Accessible Pages

**Limitation**: Playwright MCP server can only access pages the browser can reach.

**Cannot Explore**:
- Pages requiring authentication (unless credentials provided)
- Pages behind VPN or firewall
- Internal admin interfaces
- Development/staging environments without public access

**Workarounds**:
- Provide test credentials for authenticated exploration
- Run Playwright MCP server within VPN
- Use local development environment for exploration
- Manually author scenarios for inaccessible pages

### Token Limits May Restrict Large Application Exploration

**Limitation**: LLMs have maximum context window sizes.

**Context Limits**:
- GPT-4-turbo: 128K tokens (~96,000 words)
- GPT-3.5-turbo: 16K tokens
- Llama2: 4K tokens

**Impact**:
- Large exploration logs may exceed limits
- Complex page structures consume many tokens
- Long scenarios may be truncated

**Mitigation**:
- Break exploration into smaller sessions
- Compress page structures (remove styling, scripts)
- Summarize interactions before sending to LLM
- Use models with larger context windows (GPT-4-turbo)

---

## Security Considerations

### API Keys Stored in Environment Variables

**Rule**: Never commit API keys to version control.

**Enforcement**:
```bash
# .gitignore
.env
.env.local
*.key
secrets/
```

**Best Practices**:
- Use environment variables or secrets managers (AWS Secrets Manager, Azure Key Vault)
- Rotate API keys regularly
- Use separate keys for dev/staging/prod
- Monitor API key usage for anomalies

### Ollama Runs Locally with No External API Calls

**Security Benefit**: Complete data privacy for exploration sessions.

**Advantages**:
- Sensitive application data never leaves your infrastructure
- No compliance concerns (GDPR, HIPAA, SOC2)
- No risk of API key leakage
- Full control over model and data

**Recommendation**: Use Ollama for applications with sensitive data or strict compliance requirements.

### Playwright MCP Server Development-Only

**Security Posture**: Playwright MCP server should NOT be exposed to the internet.

**Why**:
- Provides browser automation capabilities (potential security risk)
- No authentication in default configuration
- Could be abused for scraping or automation attacks

**Best Practices**:
```yaml
# docker-compose.yml (example)
services:
  playwright-mcp:
    image: playwright-mcp:latest
    ports:
      - "127.0.0.1:8001:8001"  # Bind to localhost only
    environment:
      - REQUIRE_AUTH=true
      - AUTH_TOKEN=${PLAYWRIGHT_MCP_TOKEN}
```

### Review Generated Scenarios for Sensitive Data Exposure

**Risk**: LLM may capture and include sensitive data in generated scenarios.

**Examples**:
- Real email addresses or usernames
- Passwords or API keys
- PII (names, addresses, phone numbers)
- Credit card numbers

**Mitigation**:
```gherkin
# ❌ BAD: Real data in examples
Scenario: Login with credentials
  When the user enters email "john.doe@realcompany.com"
  And the user enters password "ActualPassword123!"

# ✅ GOOD: Sanitized examples
Scenario: Login with credentials
  When the user enters email "test.user@example.com"
  And the user enters password "<secure_password>"
```

**Review Checklist**:
- [ ] No real email addresses or usernames
- [ ] No actual passwords or secrets
- [ ] No real credit card or payment info
- [ ] No PII from production data
- [ ] Example data clearly marked as test data

---

## Monitoring and Observability

### Log All LLM Requests/Responses

**Purpose**: Debugging, auditing, cost tracking

**Implementation**:
```python
# llm/logger.py (conceptual)
import logging
from datetime import datetime

llm_logger = logging.getLogger("llm_integration")

def log_llm_request(provider: str, model: str, prompt: str, **kwargs):
    """Log LLM API request."""
    llm_logger.info(
        f"LLM Request",
        extra={
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider,
            "model": model,
            "prompt_length": len(prompt),
            "prompt_tokens": count_tokens(prompt, model),
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 2048)
        }
    )

def log_llm_response(provider: str, model: str, response: str, duration: float):
    """Log LLM API response."""
    llm_logger.info(
        f"LLM Response",
        extra={
            "timestamp": datetime.utcnow().isoformat(),
            "provider": provider,
            "model": model,
            "response_length": len(response),
            "response_tokens": count_tokens(response, model),
            "duration_seconds": duration
        }
    )
```

### Track Token Usage for Cost Management

**Monitoring Dashboard**:
```python
# llm/metrics.py (conceptual)
class LLMMetrics:
    def __init__(self):
        self.total_requests = 0
        self.total_tokens = 0
        self.total_cost = 0.0
    
    def record_usage(self, provider: str, model: str, input_tokens: int, output_tokens: int):
        """Record token usage and estimated cost."""
        self.total_requests += 1
        self.total_tokens += (input_tokens + output_tokens)
        
        cost = calculate_cost(model, input_tokens, output_tokens)
        self.total_cost += cost
    
    def report(self):
        """Generate usage report."""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 2),
            "average_cost_per_request": round(self.total_cost / max(self.total_requests, 1), 4)
        }

# Usage
metrics = LLMMetrics()
# ... after each LLM call ...
print(metrics.report())

# Output:
# {
#   "total_requests": 15,
#   "total_tokens": 47250,
#   "total_cost_usd": 1.42,
#   "average_cost_per_request": 0.0947
# }
```

### Measure Scenario Quality (Acceptance Rate)

**Quality Metrics**:
```python
# track_quality.py (conceptual)
class ScenarioQualityTracker:
    def __init__(self):
        self.generated_count = 0
        self.accepted_count = 0
        self.rejected_count = 0
        self.edits_per_scenario = []
    
    def record_review(self, scenario_id: str, accepted: bool, edit_count: int):
        """Record human review outcome."""
        self.generated_count += 1
        
        if accepted:
            self.accepted_count += 1
            self.edits_per_scenario.append(edit_count)
        else:
            self.rejected_count += 1
    
    def acceptance_rate(self) -> float:
        """Calculate percentage of accepted scenarios."""
        if self.generated_count == 0:
            return 0.0
        return (self.accepted_count / self.generated_count) * 100
    
    def average_edits(self) -> float:
        """Calculate average manual edits required."""
        if not self.edits_per_scenario:
            return 0.0
        return sum(self.edits_per_scenario) / len(self.edits_per_scenario)

# Usage
tracker = ScenarioQualityTracker()

tracker.record_review("scenario-001", accepted=True, edit_count=2)
tracker.record_review("scenario-002", accepted=True, edit_count=1)
tracker.record_review("scenario-003", accepted=False, edit_count=0)

print(f"Acceptance Rate: {tracker.acceptance_rate():.1f}%")
print(f"Average Edits: {tracker.average_edits():.1f}")

# Output:
# Acceptance Rate: 66.7%
# Average Edits: 1.5
```

**Target Metrics**:
- **Acceptance Rate**: 70%+ (scenarios approved with minor edits)
- **Average Edits**: <3 per scenario (minimal manual refinement)
- **Time Saved**: 50%+ reduction in test authoring time

### Monitor Time Saved vs. Manual Authoring

**Time Tracking**:
```python
# Time comparison study
MANUAL_AUTHORING_TIME = {
    "simple_scenario": 15,  # minutes
    "complex_scenario": 45,
    "edge_case_discovery": 60
}

LLM_ASSISTED_TIME = {
    "simple_scenario": 5,   # minutes (generation + review)
    "complex_scenario": 20,
    "edge_case_discovery": 15
}

def calculate_time_savings():
    scenarios = {
        "simple": 10,
        "complex": 5,
        "edge_cases": 3
    }
    
    manual_time = (
        scenarios["simple"] * MANUAL_AUTHORING_TIME["simple_scenario"] +
        scenarios["complex"] * MANUAL_AUTHORING_TIME["complex_scenario"] +
        scenarios["edge_cases"] * MANUAL_AUTHORING_TIME["edge_case_discovery"]
    )
    
    llm_time = (
        scenarios["simple"] * LLM_ASSISTED_TIME["simple_scenario"] +
        scenarios["complex"] * LLM_ASSISTED_TIME["complex_scenario"] +
        scenarios["edge_cases"] * LLM_ASSISTED_TIME["edge_case_discovery"]
    )
    
    time_saved = manual_time - llm_time
    percentage = (time_saved / manual_time) * 100
    
    return {
        "manual_hours": manual_time / 60,
        "llm_assisted_hours": llm_time / 60,
        "time_saved_hours": time_saved / 60,
        "percentage_saved": percentage
    }

print(calculate_time_savings())

# Output:
# {
#   "manual_hours": 7.75,
#   "llm_assisted_hours": 2.42,
#   "time_saved_hours": 5.33,
#   "percentage_saved": 68.8
# }
```

---

## Troubleshooting

### Issue: LLM Generates Low-Quality Scenarios

**Symptoms**:
- Scenarios too technical (CSS selectors, element IDs)
- Missing business context
- Unrealistic edge cases
- Poor Gherkin structure

**Solutions**:

1. **Refine Prompts**:
   - Add more context about business domain
   - Include example scenarios in prompt
   - Specify output format explicitly
   - Increase temperature for creativity (edge cases) or decrease for consistency

2. **Improve Exploration Log**:
   - Capture more observations (error messages, success states)
   - Include screenshots with descriptions
   - Log user journey with business context

3. **Switch Models**:
   - Upgrade from llama2 (7B) to mixtral (8x7B) or GPT-4
   - Try different model versions
   - Experiment with model-specific parameters

**Example Fix**:
```python
# Before: Generic prompt
prompt = "Generate test scenarios for login page"

# After: Detailed prompt with context
prompt = """
Application: Healthcare patient portal
Feature: User authentication
Business Rules:
- Doctors use email + password
- Patients use email + password OR SSN + DOB
- Account locks after 5 failed attempts (30 min cooldown)
- MFA required for doctor accounts

Generate Gherkin scenarios covering:
1. Successful login for each user type
2. Failed login with incorrect credentials
3. Account lockout flow
4. MFA challenges for doctors

Use business language, not technical details.
"""
```

### Issue: Token Limit Exceeded

**Symptoms**:
- `Error: This model's maximum context length is 4096 tokens`
- Truncated responses
- Incomplete scenarios

**Solutions**:

1. **Reduce Exploration Log Size**:
   ```python
   def compress_log(exploration_log: list) -> list:
       """Keep only significant interactions."""
       compressed = []
       for entry in exploration_log:
           # Skip redundant observations
           if entry.get("action") in ["mouse_move", "scroll"]:
               continue
           # Summarize page structures
           if "page_structure" in entry:
               entry["page_structure"] = summarize_dom(entry["page_structure"])
           compressed.append(entry)
       return compressed
   ```

2. **Use Models with Larger Context**:
   - Switch from llama2 (4K) to GPT-4-turbo (128K)
   - Use claude-3-opus (200K context)

3. **Break Exploration into Sessions**:
   ```python
   # Instead of one long exploration
   explore_and_generate(url="/checkout", max_interactions=100)
   
   # Break into phases
   explore_and_generate(url="/checkout", objective="Add items to cart", max_interactions=20)
   explore_and_generate(url="/checkout", objective="Enter shipping info", max_interactions=20)
   explore_and_generate(url="/checkout", objective="Complete payment", max_interactions=20)
   ```

### Issue: Ollama Performance Too Slow

**Symptoms**:
- 30-60 second response times
- High CPU usage
- System freezes during generation

**Solutions**:

1. **Enable GPU Acceleration**:
   ```bash
   # Check if NVIDIA GPU detected
   nvidia-smi
   
   # Ollama automatically uses GPU if available
   # Verify GPU usage during generation
   watch -n 1 nvidia-smi
   ```

2. **Use Smaller Models**:
   ```bash
   # Instead of mixtral (8x7B)
   ollama pull mixtral
   
   # Use mistral (7B) - faster
   ollama pull mistral
   ```

3. **Optimize Ollama Settings**:
   ```bash
   # Reduce context window for faster inference
   curl http://localhost:11434/api/generate -d '{
     "model": "llama2",
     "prompt": "...",
     "options": {
       "num_ctx": 2048  # Reduce from default 4096
     }
   }'
   ```

4. **Upgrade Hardware**:
   - Minimum: 16GB RAM, 8-core CPU
   - Recommended: NVIDIA GPU with 8GB+ VRAM
   - Optimal: NVIDIA RTX 3090/4090 (24GB VRAM)

### Issue: OpenAI Rate Limits

**Symptoms**:
- `Error: Rate limit exceeded`
- 429 Too Many Requests
- Slow response during peak hours

**Solutions**:

1. **Implement Exponential Backoff**:
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=60)
   )
   def generate_with_retry(prompt: str):
       return llm.generate(prompt)
   ```

2. **Request Rate Limit Increase**:
   - Contact OpenAI support
   - Upgrade to higher tier (Scale plan)
   - Provide use case justification

3. **Batch Requests**:
   ```python
   # Instead of 10 separate requests
   for feature in features:
       generate_scenarios(feature)
   
   # Batch into one prompt
   generate_scenarios_batch(features)  # Single request with multiple outputs
   ```

4. **Use Alternative Provider**:
   - Switch to Azure OpenAI (separate rate limits)
   - Try Anthropic Claude
   - Fall back to Ollama for development

---

## Summary

This guide covered the complete LLM integration for test automation:

- **Supported Providers**: Ollama (local, free) and OpenAI-compatible APIs (hosted, high-quality)
- **Workflow**: 8-step process from exploration to committed scenarios
- **Capabilities**: Gherkin generation, edge case discovery, test variation suggestions
- **Best Practices**: Human review, metadata tracking, prompt engineering, cost management
- **Security**: API key management, data privacy, Playwright MCP isolation
- **Monitoring**: Token usage, quality metrics, time savings tracking
- **Troubleshooting**: Common issues and solutions

### Key Takeaways

1. **LLMs are assistants, not replacements** for human QA engineers
2. **Always review and refine** LLM-generated scenarios before committing
3. **Start with Ollama** for learning, **upgrade to GPT-4** for production
4. **Track metrics** to measure ROI and quality improvements
5. **LLM integration is development-only** - CI/CD runs committed tests without LLM dependencies

### Next Steps

1. **Set up Ollama** and run your first exploration
2. **Generate a draft feature file** and review it
3. **Implement step definitions** and validate tests pass
4. **Measure time savings** and acceptance rate
5. **Iterate on prompts** to improve scenario quality
6. **Share learnings** with your team and establish review workflows

For additional support, see:
- [Getting Started Guide](getting_started.md)
- [Writing Tests Guide](writing_tests.md)
- [MCP Servers Documentation](mcp_servers.md)
- [Troubleshooting Guide](troubleshooting.md)
