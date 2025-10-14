# Test Automation Framework Architecture

## Table of Contents

- [1. Architectural Overview](#1-architectural-overview)
- [2. Core Architectural Principles](#2-core-architectural-principles)
- [3. System Layers](#3-system-layers)
- [4. Component Catalog](#4-component-catalog)
- [5. Data Flow Patterns](#5-data-flow-patterns)
- [6. Integration Points](#6-integration-points)
- [7. Technology Foundation](#7-technology-foundation)
- [8. Architecture Diagrams](#8-architecture-diagrams)

---

## 1. Architectural Overview

This test automation framework implements a **five-layer modular architecture** designed for enterprise-grade test automation with LLM-assisted test generation capabilities. The architecture emphasizes separation of concerns, deterministic test execution, and maintainability at scale.

### 1.1 Five-Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 5: CI/CD Orchestration                    │
│              (GitHub Actions, Allure Publishing)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│              Layer 4: Optional LLM Service Layer                 │
│         (Scenario Generation, Edge Case Suggestions)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│             Layer 3: Supporting MCP Services Layer               │
│        (FastAPI MCP: Data Management, Playwright MCP:            │
│                    Browser Exploration)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 2: Test Asset Layer                       │
│     (Page Objects, API Clients, Feature Files, Step Defs)       │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                   Layer 1: Test Runner Layer                     │
│           (pytest + pytest-bdd + Playwright Core)                │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Architectural Characteristics

| Characteristic | Implementation |
|----------------|----------------|
| **Test Execution** | pytest-based (not agent-driven) |
| **Test Isolation** | Fresh browser context per test |
| **Concurrency Model** | Parallel execution with pytest-xdist |
| **Data Management** | MCP-provided deterministic test data |
| **Configuration** | Environment variable-based externalization |
| **Reporting** | Allure HTML reports with CI/CD integration |
| **LLM Role** | Optional generation assistant (not executor) |
| **Selector Strategy** | ARIA roles and semantic locators |

### 1.3 Modular Design Philosophy

**pytest and Playwright remain the primary test execution engine.** MCP servers and LLM integration serve as supporting services—they do not replace the core test runner. This architecture ensures:

- **Fast, reliable test execution** within the pytest ecosystem
- **Deterministic behavior** through MCP-managed test data
- **Optional LLM enhancement** without coupling to critical test paths
- **Clear separation** between test execution, data provisioning, and generation

---

## 2. Core Architectural Principles

### 2.1 Test Execution Primacy

**Principle**: pytest remains the sole test runner and execution engine.

**Rationale**: 
- Ensures fast, deterministic test execution
- Leverages mature pytest ecosystem and plugin architecture
- Avoids flakiness from agent-controlled test execution
- Provides predictable CI/CD behavior

**Implementation**:
- All tests execute through `pytest` command
- MCP servers provide supporting services (data seeding, payload generation)
- LLM integration assists with test authoring, not execution
- GitHub Actions invokes pytest directly, not through agents

### 2.2 Deterministic Test Design

**Principle**: Every test starts from a known-good state with predictable data.

**Rationale**:
- Eliminates test interdependencies and execution order sensitivity
- Enables reliable parallel execution
- Simplifies debugging and maintenance
- Ensures reproducible test results across environments

**Implementation**:
- Fresh Playwright browser context created per test
- MCP `seed_user` tool creates test users on-demand
- MCP `reset_env` tool clears state before test suites
- No shared mutable state between tests
- No hardcoded test data in test files

### 2.3 Separation of Concerns

**Principle**: Clear boundaries between test execution, supporting services, and generation helpers.

**Layer Responsibilities**:
- **Test Runner**: Execute tests, manage fixtures, report results
- **Test Assets**: Define test scenarios, interactions, assertions
- **MCP Services**: Provide deterministic data and optional exploration
- **LLM Integration**: Generate test scenarios with human approval
- **CI/CD**: Orchestrate environment setup and test execution

**Anti-Pattern Examples**:
- ❌ LLM directly executing tests (violates test execution primacy)
- ❌ Test data hardcoded in step definitions (violates determinism)
- ❌ Page objects directly manipulating MCP servers (violates separation)

### 2.4 Business-Readable Specifications

**Principle**: Gherkin scenarios focus on WHAT the system does, not HOW it's implemented.

**Rationale**:
- Makes tests understandable to non-technical stakeholders
- Decouples business behavior from implementation details
- Reduces test maintenance burden when UI changes
- Improves collaboration between QA, developers, and product teams

**Implementation Examples**:

**Good (High-Level)**:
```gherkin
Given a customer with an active account
When they view their order history
Then they see their last 10 orders
```

**Bad (Implementation-Focused)**:
```gherkin
Given I click the button with CSS selector ".login-btn"
When I type "user@example.com" into input[name='email']
Then the div with class "order-list" contains 10 child elements
```

### 2.5 Stable Locator Strategy

**Principle**: Prioritize semantic, accessibility-focused selectors over brittle CSS/XPath.

**Selector Priority Order**:
1. **ARIA roles and labels** - `page.get_by_role("button", name="Login")`
2. **Test IDs** - `page.get_by_test_id("submit-button")`
3. **Semantic text** - `page.get_by_text("Submit Order")`
4. **Placeholder/label** - `page.get_by_placeholder("Enter email")`
5. **CSS selectors** (last resort, stable classes only)

**Rationale**:
- ARIA roles align with accessibility best practices
- Semantic selectors survive UI redesigns
- Reduces test maintenance from CSS class churn
- Improves readability of page object methods

### 2.6 Environment-Based Configuration

**Principle**: All runtime behavior controlled via environment variables, not code.

**Configuration Categories**:
- **Application URLs**: `BASE_URL`, `API_BASE_URL`
- **Browser Behavior**: `HEADLESS`, `BROWSER_TYPE`, `SLOW_MO`
- **MCP Endpoints**: `FASTAPI_MCP_URL`, `PLAYWRIGHT_MCP_URL`
- **LLM Settings**: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`
- **Authentication**: `FASTAPI_MCP_TOKEN`, `TEST_USER_PASSWORD`

**Benefits**:
- Single codebase works across dev, staging, production
- CI/CD uses GitHub Secrets for sensitive values
- Local development uses `.env` file
- No code changes required for environment switches

### 2.7 Parallel Execution Safety

**Principle**: Tests must be isolated enough to run concurrently without conflicts.

**Implementation Requirements**:
- Each test receives a fresh browser context (not shared)
- Test data created with unique identifiers (e.g., UUID-based emails)
- No reliance on global state or execution order
- Database transactions isolated per test (if using shared database)
- MCP state management supports concurrent requests

**pytest-xdist Configuration**:
```ini
[pytest]
addopts = -n auto --dist loadscope
```

**Benefits**:
- Faster CI/CD feedback cycles
- Scalability to large test suites
- Early detection of state leakage bugs

### 2.8 Human-in-the-Loop LLM

**Principle**: LLM generates test scenarios as suggestions; humans review and approve before commit.

**Workflow**:
1. LLM explores application via Playwright MCP
2. LLM generates Gherkin scenarios based on exploration
3. **Human reviews** generated scenarios for correctness
4. **Human approves** scenarios to commit to repository
5. pytest executes approved scenarios

**Rationale**:
- LLMs can hallucinate invalid test logic
- Human expertise ensures business-relevant test coverage
- Maintains quality standards and test maintainability
- Provides audit trail of test provenance

---

## 3. System Layers

### Layer 1: Test Runner Layer

**Purpose**: Core test execution engine powered by pytest with Playwright and BDD support.

**Key Components**:

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| **pytest Core** | pytest 8.4.2 | Test discovery, execution, fixture management |
| **pytest-bdd Plugin** | pytest-bdd 8.1.0 | Gherkin parsing and step definition binding |
| **Playwright Integration** | pytest-playwright 0.6.2 | Browser automation and context management |
| **Parallel Execution** | pytest-xdist 3.6.1 | Distribute tests across worker processes |
| **Test Configuration** | pytest.ini, conftest.py | Runner settings, fixture definitions |

**Key Responsibilities**:
- Discover and execute test files matching naming patterns
- Parse `.feature` files and bind to Python step definitions
- Manage browser lifecycle (launch, contexts, cleanup)
- Inject fixtures into test functions and step definitions
- Collect test results and invoke reporter plugins
- Support parallel execution with isolated worker states

**Configuration Example (pytest.ini)**:
```ini
[pytest]
# BDD Configuration
bdd_features_base_dir = tests/features
testpaths = tests

# Playwright Configuration
base_url = ${BASE_URL:http://localhost:3000}
headed = false
browser = chromium

# Parallel Execution
addopts = -n auto --dist loadscope --alluredir=allure-results

# Test Discovery
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

**Fixture Management (conftest.py)**:
```python
import pytest
from playwright.sync_api import Page, BrowserContext

@pytest.fixture(scope="function")
def browser_context(browser) -> BrowserContext:
    """Provides isolated browser context per test."""
    context = browser.new_context()
    yield context
    context.close()

@pytest.fixture(scope="function")
def page(browser_context: BrowserContext) -> Page:
    """Provides fresh page per test."""
    page = browser_context.new_page()
    yield page
    page.close()

@pytest.fixture(scope="session")
def mcp_client():
    """Provides MCP client for test data management."""
    from tests.helpers.mcp_client import MCPClient
    return MCPClient(
        base_url=os.getenv("FASTAPI_MCP_URL"),
        token=os.getenv("FASTAPI_MCP_TOKEN")
    )
```

---

### Layer 2: Test Asset Layer

**Purpose**: Implement test scenarios, page interactions, and API operations with maintainable patterns.

#### 2.1 Page Objects

**Pattern**: Page Object Model with stable locators and business-focused methods.

**Directory Structure**:
```
tests/pages/
├── base_page.py          # Base class with common functionality
├── login_page.py         # Login page interactions
├── dashboard_page.py     # Dashboard page interactions
└── components/           # Reusable UI components
    ├── navigation.py     # Navigation bar component
    └── modal.py          # Modal dialog component
```

**Example Implementation**:
```python
# tests/pages/login_page.py
from playwright.sync_api import Page

class LoginPage:
    def __init__(self, page: Page):
        self.page = page
    
    def navigate(self):
        """Navigate to login page."""
        self.page.goto("/login")
    
    def fill_email(self, email: str):
        """Enter email using stable locator."""
        self.page.get_by_label("Email").fill(email)
    
    def fill_password(self, password: str):
        """Enter password using stable locator."""
        self.page.get_by_label("Password").fill(password)
    
    def click_login_button(self):
        """Click login button using ARIA role."""
        self.page.get_by_role("button", name="Login").click()
    
    def get_error_message(self) -> str:
        """Retrieve error message if login fails."""
        return self.page.get_by_role("alert").text_content()
```

**Locator Strategy**:
- ✅ Use ARIA roles: `get_by_role("button", name="Submit")`
- ✅ Use labels: `get_by_label("Email Address")`
- ✅ Use test IDs: `get_by_test_id("login-submit")`
- ❌ Avoid brittle CSS: `.auth-form > div:nth-child(2) > button`
- ❌ Avoid complex XPath: `//div[@class='container']//button[contains(text(), 'Submit')]`

#### 2.2 API Clients

**Pattern**: Typed httpx-based clients with Pydantic models for request/response validation.

**Directory Structure**:
```
tests/api_clients/
├── base_client.py        # Base httpx client configuration
├── auth_client.py        # Authentication API
├── users_client.py       # Users API
└── models/               # Pydantic models
    ├── auth_models.py    # Auth request/response models
    └── user_models.py    # User request/response models
```

**Example Implementation**:
```python
# tests/api_clients/users_client.py
import httpx
from typing import Dict, Any
from .models.user_models import UserCreateRequest, UserResponse

class UsersAPIClient:
    def __init__(self, base_url: str, httpx_client: httpx.Client):
        self.base_url = base_url
        self.client = httpx_client
    
    def create_user(self, request: UserCreateRequest) -> UserResponse:
        """Create a new user via API."""
        response = self.client.post(
            f"{self.base_url}/users",
            json=request.model_dump()
        )
        response.raise_for_status()
        return UserResponse(**response.json())
    
    def get_user(self, user_id: str) -> UserResponse:
        """Retrieve user by ID."""
        response = self.client.get(f"{self.base_url}/users/{user_id}")
        response.raise_for_status()
        return UserResponse(**response.json())
```

#### 2.3 Gherkin Feature Files

**Pattern**: Business-readable scenarios focusing on user behavior, not implementation.

**Directory Structure**:
```
tests/features/
├── authentication.feature      # Login, logout, password reset
├── user_management.feature     # User CRUD operations
└── api_operations.feature      # API-focused scenarios
```

**Example Feature File**:
```gherkin
# tests/features/authentication.feature
Feature: User Authentication
  As a registered user
  I want to log into the application
  So that I can access my account

  Scenario: Successful login with valid credentials
    Given a user exists with email "test@example.com"
    When the user logs in with email "test@example.com" and password "ValidPass123"
    Then the user should be on the dashboard page
    And the user should see a welcome message

  Scenario: Failed login with invalid password
    Given a user exists with email "test@example.com"
    When the user logs in with email "test@example.com" and password "WrongPassword"
    Then the user should see an error message "Invalid credentials"
    And the user should remain on the login page
```

#### 2.4 Step Definitions

**Pattern**: pytest-bdd step definitions that delegate to page objects and API clients.

**Directory Structure**:
```
tests/step_definitions/
├── auth_steps.py         # Authentication step implementations
├── user_steps.py         # User management steps
├── api_steps.py          # API testing steps
└── common_steps.py       # Reusable common steps
```

**Example Step Definitions**:
```python
# tests/step_definitions/auth_steps.py
from pytest_bdd import given, when, then, parsers
import pytest

@given(parsers.parse('a user exists with email "{email}"'))
def create_test_user(email: str, mcp_client):
    """Create test user via MCP seed_user tool."""
    user = mcp_client.seed_user(
        email=email,
        password="ValidPass123",
        role="customer"
    )
    return user

@when(parsers.parse('the user logs in with email "{email}" and password "{password}"'))
def perform_login(email: str, password: str, login_page):
    """Perform login via page object."""
    login_page.navigate()
    login_page.fill_email(email)
    login_page.fill_password(password)
    login_page.click_login_button()

@then(parsers.parse('the user should see an error message "{message}"'))
def verify_error_message(message: str, login_page):
    """Verify error message appears."""
    actual_message = login_page.get_error_message()
    assert message in actual_message
```

---

### Layer 3: Supporting MCP Services Layer

**Purpose**: Provide deterministic test data management and optional browser exploration for LLM agents.

#### 3.1 FastAPI MCP Server (Production/CI)

**Purpose**: Deterministic test data seeding, payload construction, and environment state management.

**Technology Stack**:
- FastAPI 0.118.0 (JSON-RPC endpoints)
- SQLAlchemy 2.0.38 (state management)
- Pydantic 2.10.5 (request validation)
- Bearer token authentication

**Exposed MCP Tools**:

| Tool Name | Purpose | Example Usage |
|-----------|---------|---------------|
| `seed_user` | Create test user in target system | `mcp.seed_user(email="test@ex.com", role="admin")` |
| `build_payload` | Generate valid API request body | `mcp.build_payload("create_order", {items: [...]})` |
| `reset_env` | Clear test data and reset state | `mcp.reset_env(scope="test_suite")` |
| `query_state` | Inspect current environment state | `mcp.query_state(resource="users", filter={...})` |

**Example Tool Implementation**:
```python
# mcp_servers/fastapi_mcp/routers/tools.py
from fastapi import APIRouter, Depends
from ..models import SeedUserRequest, SeedUserResponse
from ..services.user_service import UserService

router = APIRouter()

@router.post("/tools/seed_user")
async def seed_user(
    request: SeedUserRequest,
    user_service: UserService = Depends()
) -> SeedUserResponse:
    """Create a test user in the target system."""
    user = await user_service.create_test_user(
        email=request.email,
        password=request.password,
        role=request.role
    )
    return SeedUserResponse(
        user_id=user.id,
        email=user.email,
        token=user.auth_token
    )
```

**Integration in Tests**:
```python
# Test uses MCP client to seed data
def test_user_dashboard(mcp_client, page):
    # Seed user via MCP
    user = mcp_client.seed_user(email="test@example.com", role="customer")
    
    # Login with seeded user
    login_page.navigate()
    login_page.login(email=user.email, password=user.password)
    
    # Verify dashboard
    assert dashboard_page.is_loaded()
```

**Startup Configuration**:
```bash
# CI/CD startup script
uvicorn mcp_servers.fastapi_mcp.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --env-file .env.ci
```

#### 3.2 Playwright MCP Server (Development/Exploration)

**Purpose**: Enable LLM agents to control browsers for exploratory testing and Gherkin generation.

**Technology Stack**:
- Playwright 1.55.0 (browser automation)
- FastAPI 0.118.0 (MCP endpoints)
- WebSocket support (real-time streaming)

**Exposed MCP Tools**:

| Tool Name | Purpose | Example Usage |
|-----------|---------|---------------|
| `navigate` | Navigate browser to URL | `llm.call_tool("navigate", {"url": "https://app.com"})` |
| `click` | Click element by selector | `llm.call_tool("click", {"selector": "button[aria-label='Login']"})` |
| `type` | Type text into input field | `llm.call_tool("type", {"selector": "input[name='email']", "text": "test@ex.com"})` |
| `screenshot` | Capture page screenshot | `llm.call_tool("screenshot", {})` |
| `get_page_structure` | Extract page DOM structure | `llm.call_tool("get_page_structure", {})` |
| `generate_gherkin` | Convert exploration to Gherkin | `llm.call_tool("generate_gherkin", {"session_id": "abc123"})` |

**Example Tool Implementation**:
```python
# mcp_servers/playwright_mcp/tools/navigation.py
from playwright.async_api import Page

async def navigate_tool(page: Page, url: str) -> dict:
    """Navigate browser to specified URL."""
    try:
        await page.goto(url, wait_until="domcontentloaded")
        return {
            "success": True,
            "current_url": page.url,
            "title": await page.title()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Gherkin Generation Flow**:
```python
# LLM explores application
session = playwright_mcp.create_session()
playwright_mcp.navigate(url="https://app.com/login")
page_structure = playwright_mcp.get_page_structure()

# LLM analyzes structure and interacts
playwright_mcp.type(selector="input[name='email']", text="test@example.com")
playwright_mcp.click(selector="button[type='submit']")

# Generate Gherkin from exploration
feature_content = playwright_mcp.generate_gherkin(session_id=session.id)

# Human reviews and approves
# ... review workflow ...

# Commit to repository
with open("tests/features/generated_login.feature", "w") as f:
    f.write(feature_content)
```

**Environment Configuration**:
- **CI/CD**: Playwright MCP server NOT started (dev-only by default)
- **Local Dev**: Playwright MCP available at `http://localhost:8001`
- **Opt-In CI**: Set `ENABLE_PLAYWRIGHT_MCP=true` for specific scenarios

---

### Layer 4: Optional LLM Service Layer

**Purpose**: Assist with test scenario generation and edge case discovery through LLM capabilities.

**Key Components**:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM Client** | openai 1.59.8, ollama 0.4.8 | Abstract LLM provider interface |
| **Scenario Generator** | Custom | Convert exploration to Gherkin |
| **Edge Case Suggester** | Custom | Analyze scenarios for coverage gaps |
| **Review Pipeline** | Custom | Human approval workflow |

**LLM Provider Abstraction**:
```python
# llm/client.py
from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def generate_completion(self, prompt: str, context: dict) -> str:
        pass

class OllamaProvider(LLMClient):
    """Local Ollama LLM provider."""
    def __init__(self, model: str = "llama2"):
        self.client = ollama.Client()
        self.model = model
    
    def generate_completion(self, prompt: str, context: dict) -> str:
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            context=context
        )
        return response['response']

class OpenAIProvider(LLMClient):
    """OpenAI or OpenAI-compatible API provider."""
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = openai.Client(api_key=api_key)
        self.model = model
    
    def generate_completion(self, prompt: str, context: dict) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": context.get("system_prompt", "")},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
```

**Scenario Generation Workflow**:
```python
# llm/workflows/scenario_generator.py
from ..client import LLMClient
from ..prompts.gherkin_generation import GHERKIN_PROMPT_TEMPLATE

async def generate_scenarios_from_exploration(
    llm_client: LLMClient,
    exploration_session_id: str,
    playwright_mcp_url: str
) -> str:
    """Generate Gherkin scenarios from browser exploration session."""
    
    # Retrieve exploration data from Playwright MCP
    session_data = await get_exploration_session(
        playwright_mcp_url,
        exploration_session_id
    )
    
    # Build context for LLM
    context = {
        "system_prompt": "You are a QA expert generating BDD scenarios.",
        "pages_visited": session_data["urls"],
        "interactions": session_data["actions"],
        "screenshots": session_data["screenshots"]
    }
    
    # Generate Gherkin
    prompt = GHERKIN_PROMPT_TEMPLATE.format(
        application_name="Test Application",
        exploration_summary=session_data["summary"]
    )
    
    gherkin_content = llm_client.generate_completion(prompt, context)
    
    # Validate Gherkin syntax
    validate_gherkin_syntax(gherkin_content)
    
    return gherkin_content
```

**Human Review Workflow**:
1. LLM generates Gherkin scenarios
2. Scenarios saved to `tests/features/pending/` directory
3. GitHub PR created with generated scenarios
4. Human reviewer examines scenarios for:
   - Business relevance
   - Correctness of expected behavior
   - Coverage of edge cases
   - Clarity and maintainability
5. Approved scenarios moved to `tests/features/`
6. Step definitions auto-generated (stubs if new steps)

**Edge Case Suggestion**:
```python
# llm/workflows/edge_case_suggester.py
def suggest_edge_cases(llm_client: LLMClient, feature_file: str) -> list[str]:
    """Analyze feature file and suggest additional edge cases."""
    
    with open(feature_file, "r") as f:
        feature_content = f.read()
    
    prompt = f"""
    Analyze this Gherkin feature and suggest 5 edge cases not covered:
    
    {feature_content}
    
    Focus on:
    - Boundary conditions
    - Error handling
    - Concurrent operations
    - Data validation
    """
    
    suggestions = llm_client.generate_completion(prompt, {})
    return parse_edge_case_suggestions(suggestions)
```

**Configuration**:
```bash
# Local development with Ollama
LLM_PROVIDER=ollama
LLM_MODEL=llama2
OLLAMA_BASE_URL=http://localhost:11434

# Production with OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=sk-...
```

---

### Layer 5: CI/CD Orchestration Layer

**Purpose**: Automate test execution, report generation, and result publishing in continuous integration.

**Key Components**:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Test Execution Workflow** | GitHub Actions | Run pytest with Playwright |
| **Allure Report Generation** | Allure CLI | Generate HTML test reports |
| **Report Publishing** | GitHub Pages | Host reports publicly |
| **Lint Workflow** | ruff, mypy | Code quality checks |

**Test Execution Workflow (.github/workflows/test.yml)**:
```yaml
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
      fastapi-mcp:
        image: python:3.11
        env:
          FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
          DATABASE_URL: ${{ secrets.TEST_DB_URL }}
        ports:
          - 8000:8000
    
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
        browser: [chromium, firefox, webkit]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install ${{ matrix.browser }} --with-deps
      
      - name: Start FastAPI MCP Server
        run: |
          cd mcp_servers/fastapi_mcp
          pip install -r requirements.txt
          uvicorn main:app --host 0.0.0.0 --port 8000 &
          sleep 5
      
      - name: Run Tests
        env:
          BASE_URL: https://staging.example.com
          API_BASE_URL: https://api.staging.example.com
          FASTAPI_MCP_URL: http://localhost:8000
          FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
          HEADLESS: true
          BROWSER: ${{ matrix.browser }}
        run: |
          pytest -n auto --browser ${{ matrix.browser }} --alluredir=allure-results
      
      - name: Upload Allure Results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: allure-results-${{ matrix.python-version }}-${{ matrix.browser }}
          path: allure-results
      
      - name: Upload Test Traces
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: test-traces-${{ matrix.python-version }}-${{ matrix.browser }}
          path: test-results
```

**Allure Report Generation Workflow (.github/workflows/allure-report.yml)**:
```yaml
name: Allure Report

on:
  workflow_run:
    workflows: ["Test Execution"]
    types: [completed]

jobs:
  generate-report:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Download Allure Results
        uses: actions/download-artifact@v4
        with:
          path: allure-results
      
      - name: Generate Allure Report
        uses: simple-elf/allure-report-action@master
        with:
          allure_results: allure-results
          allure_report: allure-report
          allure_history: allure-history
      
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./allure-report
```

**Lint Workflow (.github/workflows/lint.yml)**:
```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      
      - name: Install dependencies
        run: pip install ruff mypy
      
      - name: Run Ruff Linter
        run: ruff check .
      
      - name: Run Ruff Formatter
        run: ruff format --check .
      
      - name: Run MyPy Type Checker
        run: mypy tests/ mcp_servers/ llm/
```

**CI/CD Configuration Strategy**:
- **FastAPI MCP Server**: Started as service container in CI
- **Playwright MCP Server**: NOT started in CI (dev-only by default)
- **Secrets Management**: GitHub Secrets for tokens, API keys, database URLs
- **Parallel Execution**: Matrix strategy for multiple Python versions and browsers
- **Artifact Retention**: Allure results and traces uploaded for debugging
- **Report Publishing**: Automatic deployment to GitHub Pages on test completion

---

## 4. Component Catalog

This section provides a comprehensive inventory of all framework components, their responsibilities, technologies, and integration characteristics.

### 4.1 Test Runner Components

| Component | Location | Technology | Responsibilities | Dependencies |
|-----------|----------|------------|------------------|--------------|
| **pytest Core** | N/A (installed package) | pytest 8.4.2 | Test discovery, execution, fixture management, result collection | Python 3.9+ |
| **pytest-bdd Plugin** | N/A (installed package) | pytest-bdd 8.1.0 | Parse `.feature` files, bind Gherkin steps to Python functions | pytest, Gherkin parser |
| **pytest-playwright** | N/A (installed package) | pytest-playwright 0.6.2 | Provide Playwright fixtures, manage browser lifecycle | pytest, playwright |
| **pytest Configuration** | pytest.ini | INI file | Configure test discovery, BDD settings, Playwright options | None |
| **Fixture Definitions** | tests/conftest.py | Python | Define shared fixtures for pages, API clients, MCP client | pytest |
| **Parallel Executor** | N/A (installed package) | pytest-xdist 3.6.1 | Distribute tests across worker processes | pytest |

### 4.2 Test Asset Components

| Component | Location | Technology | Responsibilities | Dependencies |
|-----------|----------|------------|------------------|--------------|
| **Base Page Object** | tests/pages/base_page.py | Python + Playwright | Common page methods, stable locator wrappers | playwright |
| **Login Page Object** | tests/pages/login_page.py | Python + Playwright | Login page interactions with semantic selectors | base_page.py |
| **Dashboard Page Object** | tests/pages/dashboard_page.py | Python + Playwright | Dashboard navigation and verification | base_page.py |
| **User Profile Page** | tests/pages/user_profile_page.py | Python + Playwright | User profile interactions | base_page.py |
| **Navigation Component** | tests/pages/components/navigation.py | Python + Playwright | Reusable navigation bar component | base_page.py |
| **Modal Component** | tests/pages/components/modal.py | Python + Playwright | Reusable modal dialog component | base_page.py |
| **Base API Client** | tests/api_clients/base_client.py | httpx + Pydantic | Common HTTP methods, Allure integration | httpx |
| **Auth API Client** | tests/api_clients/auth_client.py | httpx + Pydantic | Authentication API operations | base_client.py |
| **Users API Client** | tests/api_clients/users_client.py | httpx + Pydantic | User management API operations | base_client.py |
| **Auth Models** | tests/api_clients/models/auth_models.py | Pydantic | Request/response models for auth endpoints | pydantic |
| **User Models** | tests/api_clients/models/user_models.py | Pydantic | Request/response models for user endpoints | pydantic |
| **Feature Files** | tests/features/*.feature | Gherkin | Business-readable test scenarios | pytest-bdd |
| **Auth Step Definitions** | tests/step_definitions/auth_steps.py | Python + pytest-bdd | Implement authentication-related steps | pytest-bdd, page objects |
| **User Step Definitions** | tests/step_definitions/user_steps.py | Python + pytest-bdd | Implement user management steps | pytest-bdd, page objects, API clients |
| **API Step Definitions** | tests/step_definitions/api_steps.py | Python + pytest-bdd | Implement API testing steps | pytest-bdd, API clients |
| **Common Step Definitions** | tests/step_definitions/common_steps.py | Python + pytest-bdd | Reusable generic steps | pytest-bdd |

### 4.3 Helper and Utility Components

| Component | Location | Technology | Responsibilities | Dependencies |
|-----------|----------|------------|------------------|--------------|
| **MCP Client** | tests/helpers/mcp_client.py | httpx | Wrapper for FastAPI MCP server tools | httpx |
| **Allure Utilities** | tests/helpers/allure_utils.py | allure-pytest | Custom Allure steps and attachments | allure-pytest |
| **Data Generators** | tests/helpers/data_generators.py | faker | Generate realistic test data | faker |
| **Assertions** | tests/helpers/assertions.py | Python | Custom assertion helpers for common checks | None |
| **Wait Conditions** | tests/helpers/wait_conditions.py | Playwright | Custom wait conditions for complex scenarios | playwright |

### 4.4 FastAPI MCP Server Components

| Component | Location | Technology | Responsibilities | Dependencies |
|-----------|----------|------------|------------------|--------------|
| **MCP Server Main** | mcp_servers/fastapi_mcp/main.py | FastAPI | Application entry point, router registration | fastapi |
| **Server Configuration** | mcp_servers/fastapi_mcp/config.py | Pydantic Settings | Environment-based configuration | pydantic-settings |
| **MCP Models** | mcp_servers/fastapi_mcp/models.py | Pydantic | Request/response models for MCP tools | pydantic |
| **Tools Router** | mcp_servers/fastapi_mcp/routers/tools.py | FastAPI | MCP tool endpoints (seed_user, build_payload, etc.) | fastapi |
| **Health Router** | mcp_servers/fastapi_mcp/routers/health.py | FastAPI | Health check and status endpoints | fastapi |
| **User Service** | mcp_servers/fastapi_mcp/services/user_service.py | Python | Business logic for user creation and management | Target app API |
| **Payload Service** | mcp_servers/fastapi_mcp/services/payload_service.py | Python | Generate valid API request payloads | pydantic |
| **State Service** | mcp_servers/fastapi_mcp/services/state_service.py | Python | Environment reset and state queries | sqlalchemy (optional) |
| **Database Connection** | mcp_servers/fastapi_mcp/database/connection.py | SQLAlchemy | Database connection pool management | sqlalchemy |
| **Database Models** | mcp_servers/fastapi_mcp/database/models.py | SQLAlchemy | ORM models for test state management | sqlalchemy |
| **Bearer Auth** | mcp_servers/fastapi_mcp/auth/bearer.py | FastAPI Security | Token-based authentication | fastapi, python-jose |

### 4.5 Playwright MCP Server Components

| Component | Location | Technology | Responsibilities | Dependencies |
|-----------|----------|------------|------------------|--------------|
| **Playwright MCP Main** | mcp_servers/playwright_mcp/main.py | FastAPI | MCP server for browser control | fastapi, playwright |
| **MCP Configuration** | mcp_servers/playwright_mcp/config.py | Pydantic Settings | Server configuration | pydantic-settings |
| **MCP Models** | mcp_servers/playwright_mcp/models.py | Pydantic | Tool request/response models | pydantic |
| **Navigation Tools** | mcp_servers/playwright_mcp/tools/navigation.py | Playwright | Navigate, wait, reload tools | playwright |
| **Interaction Tools** | mcp_servers/playwright_mcp/tools/interaction.py | Playwright | Click, type, select tools | playwright |
| **Capture Tools** | mcp_servers/playwright_mcp/tools/capture.py | Playwright | Screenshot, video, trace tools | playwright |
| **Analysis Tools** | mcp_servers/playwright_mcp/tools/analysis.py | Playwright | Extract page structure, element properties | playwright |
| **Session Manager** | mcp_servers/playwright_mcp/session/manager.py | Python | Manage multiple concurrent browser sessions | playwright |
| **Gherkin Generator** | mcp_servers/playwright_mcp/gherkin/generator.py | Python | Convert exploration actions to Gherkin | None |

### 4.6 LLM Integration Components

| Component | Location | Technology | Responsibilities | Dependencies |
|-----------|----------|------------|------------------|--------------|
| **LLM Client Abstraction** | llm/client.py | Python ABC | Abstract interface for LLM providers | None |
| **Ollama Provider** | llm/providers/ollama.py | ollama | Local LLM integration | ollama |
| **OpenAI Provider** | llm/providers/openai.py | openai | OpenAI/compatible API integration | openai |
| **Gherkin Generation Prompts** | llm/prompts/gherkin_generation.py | Python | Prompt templates for scenario generation | None |
| **Edge Case Prompts** | llm/prompts/edge_case_suggestions.py | Python | Prompt templates for edge case discovery | None |
| **Scenario Generator** | llm/workflows/scenario_generator.py | Python | End-to-end scenario generation workflow | llm/client.py, Playwright MCP |
| **Review Pipeline** | llm/workflows/review_pipeline.py | Python | Human review and approval workflow | None |

### 4.7 CI/CD Components

| Component | Location | Technology | Responsibilities | Dependencies |
|-----------|----------|------------|------------------|--------------|
| **Test Workflow** | .github/workflows/test.yml | GitHub Actions YAML | Execute tests, manage MCP servers, collect results | GitHub Actions |
| **Allure Report Workflow** | .github/workflows/allure-report.yml | GitHub Actions YAML | Generate and publish Allure HTML reports | GitHub Actions, Allure CLI |
| **Lint Workflow** | .github/workflows/lint.yml | GitHub Actions YAML | Run ruff and mypy checks | GitHub Actions |
| **MCP Startup Scripts** | mcp_servers/scripts/*.sh, *.bat | Shell/Batch | Start MCP servers in local and CI environments | uvicorn |

### 4.8 Configuration and Documentation Components

| Component | Location | Technology | Responsibilities | Dependencies |
|-----------|----------|------------|------------------|--------------|
| **Project Configuration** | pyproject.toml | TOML | Modern Python project metadata and tool configs | None |
| **Requirements (Prod)** | requirements.txt | Pip format | Production dependencies | None |
| **Requirements (Dev)** | requirements-dev.txt | Pip format | Development dependencies | requirements.txt |
| **MCP Server Requirements** | mcp_servers/fastapi_mcp/requirements.txt | Pip format | FastAPI MCP server dependencies | None |
| **LLM Requirements** | llm/requirements.txt | Pip format | LLM integration dependencies | None |
| **Environment Template** | .env.example | Dotenv | Template for required environment variables | None |
| **Git Ignore** | .gitignore | Gitignore | Exclude build artifacts, credentials, etc. | None |
| **Python Version** | .python-version | Plaintext | Specify Python version for pyenv | None |
| **Getting Started Guide** | docs/getting_started.md | Markdown | Quick start instructions | None |
| **Architecture Documentation** | docs/architecture.md | Markdown | This document | None |
| **Writing Tests Guide** | docs/writing_tests.md | Markdown | Test authoring best practices | None |
| **Page Objects Guide** | docs/page_objects.md | Markdown | Page Object Pattern guidelines | None |
| **MCP Servers Guide** | docs/mcp_servers.md | Markdown | MCP server usage documentation | None |
| **LLM Integration Guide** | docs/llm_integration.md | Markdown | LLM-assisted test generation guide | None |
| **CI/CD Documentation** | docs/ci_cd.md | Markdown | CI/CD pipeline documentation | None |
| **Troubleshooting Guide** | docs/troubleshooting.md | Markdown | Common issues and solutions | None |

---

## 5. Data Flow Patterns

This section describes how data and control flow through the system during key operational scenarios.

### 5.1 Test Data Provisioning Flow (MCP Deterministic Pattern)

**Scenario**: Test needs a user with specific characteristics.

**Flow Diagram**:
```
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
│  pytest  │────▶│ Step Def   │────▶│  MCP Client  │────▶│ FastAPI MCP    │
│  Runner  │     │  Function  │     │  (Helper)    │     │  Server        │
└──────────┘     └────────────┘     └──────────────┘     └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │ Target App API │
                                                          │  (POST /users) │
                                                          └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │   Database     │
                                                          │ (User Record)  │
                                                          └────────────────┘
                                                                  │
                                                                  ▼
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
│  pytest  │◀────│ Step Def   │◀────│  MCP Client  │◀────│ FastAPI MCP    │
│  Runner  │     │  (user obj)│     │ (user + tkn) │     │ (Response)     │
└──────────┘     └────────────┘     └──────────────┘     └────────────────┘
```

**Detailed Steps**:

1. **pytest discovers test** and begins execution
2. **Gherkin step** `Given a user exists with email "test@example.com"` is invoked
3. **Step definition function** receives MCP client fixture
4. **MCP client** sends JSON-RPC request to FastAPI MCP server:
   ```json
   {
     "method": "seed_user",
     "params": {
       "email": "test@example.com",
       "password": "SecurePass123",
       "role": "customer"
     }
   }
   ```
5. **FastAPI MCP server** validates request and calls User Service
6. **User Service** sends POST request to target application's `/users` endpoint
7. **Target application** creates user in database
8. **User Service** retrieves auth token for created user
9. **FastAPI MCP server** returns response with user ID, email, and token
10. **MCP client** deserializes response and returns user object to step definition
11. **Step definition** stores user in pytest context for subsequent steps
12. **Test continues** with authenticated user available for login

**Key Benefits**:
- No hardcoded test data in test files
- Deterministic user creation with known state
- Automatic cleanup possible via MCP `reset_env` tool
- Parallel-safe (unique emails via UUID suffixes)

---

### 5.2 Test Result Collection Flow (Allure Reporting Pattern)

**Scenario**: Test executes and results are captured for reporting.

**Flow Diagram**:
```
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
│  pytest  │────▶│   Test     │────▶│ @allure.step │────▶│  allure-pytest │
│  Runner  │     │ Execution  │     │  Decorators  │     │    Plugin      │
└──────────┘     └────────────┘     └──────────────┘     └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │ allure-results/│
                                                          │  (JSON files)  │
                                                          └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │  Allure CLI    │
                                                          │ (allure generate)│
                                                          └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │ allure-report/ │
                                                          │  (HTML files)  │
                                                          └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │  GitHub Pages  │
                                                          │  (Published)   │
                                                          └────────────────┘
```

**Detailed Steps**:

1. **pytest runner** discovers and executes test
2. **Test function** or step definition calls page object methods
3. **@allure.step decorator** on page object methods captures:
   - Step name and parameters
   - Execution timing
   - Step outcome (passed/failed)
4. **allure-pytest plugin** listens to pytest hooks:
   - `pytest_runtest_setup`: Capture test metadata
   - `pytest_runtest_call`: Capture test execution
   - `pytest_runtest_teardown`: Capture cleanup
5. **Plugin writes JSON files** to `allure-results/` directory:
   - Test result file (passed/failed/skipped)
   - Attachments (screenshots, logs, API payloads)
   - Categories (feature, story, severity)
6. **CI/CD workflow** collects `allure-results/` as artifact
7. **Allure CLI** generates HTML report:
   ```bash
   allure generate allure-results -o allure-report
   ```
8. **GitHub Actions** publishes report to GitHub Pages
9. **Developers** access report at `https://<org>.github.io/<repo>/`

**Allure Metadata Example**:
```python
@allure.feature("Authentication")
@allure.story("User Login")
@allure.severity(allure.severity_level.CRITICAL)
def test_successful_login(login_page, mcp_client):
    """Test successful login with valid credentials."""
    
    with allure.step("Create test user"):
        user = mcp_client.seed_user(email="test@example.com")
    
    with allure.step("Navigate to login page"):
        login_page.navigate()
    
    with allure.step("Enter credentials"):
        login_page.fill_email(user.email)
        login_page.fill_password(user.password)
    
    with allure.step("Submit login form"):
        login_page.click_login_button()
    
    with allure.step("Verify successful login"):
        assert dashboard_page.is_loaded()
        allure.attach(
            page.screenshot(),
            name="Dashboard after login",
            attachment_type=allure.attachment_type.PNG
        )
```

---

### 5.3 Environment Configuration Flow (Externalized Configuration)

**Scenario**: Application needs runtime configuration from environment variables.

**Flow Diagram**:
```
┌─────────────┐     ┌────────────┐     ┌──────────────┐
│ .env File   │────▶│ python-    │────▶│   Python     │
│ (Local Dev) │     │  dotenv    │     │  os.getenv() │
└─────────────┘     └────────────┘     └──────────────┘
                                                │
                                                ▼
┌─────────────┐                        ┌──────────────┐
│  GitHub     │───────────────────────▶│   Python     │
│  Secrets    │  (CI/CD Environment)   │  os.getenv() │
└─────────────┘                        └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  pytest.ini  │
                                        │  (base_url)  │
                                        └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  conftest.py │
                                        │  (fixtures)  │
                                        └──────────────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │    Tests     │
                                        │  (Execution) │
                                        └──────────────┘
```

**Environment Variables Used**:

| Variable | Purpose | Example Value | Source |
|----------|---------|---------------|--------|
| `BASE_URL` | Web application base URL | `https://staging.example.com` | .env or GitHub Secrets |
| `API_BASE_URL` | REST API endpoint base URL | `https://api.staging.example.com` | .env or GitHub Secrets |
| `HEADLESS` | Run browsers in headless mode | `true` | .env or GitHub Secrets |
| `BROWSER_TYPE` | Browser to use for tests | `chromium` | .env or CI matrix |
| `FASTAPI_MCP_URL` | FastAPI MCP server endpoint | `http://localhost:8000` | .env or service URL |
| `FASTAPI_MCP_TOKEN` | Bearer token for MCP auth | `secret-token-123` | .env or GitHub Secrets |
| `PLAYWRIGHT_MCP_URL` | Playwright MCP server endpoint | `http://localhost:8001` | .env (dev only) |
| `LLM_PROVIDER` | LLM provider (ollama/openai) | `ollama` | .env |
| `LLM_MODEL` | LLM model name | `llama2` | .env |
| `LLM_API_KEY` | LLM API key (if needed) | `sk-...` | .env or GitHub Secrets |

**Configuration Loading (conftest.py)**:
```python
import os
from dotenv import load_dotenv

# Load .env file in local development
load_dotenv()

# Retrieve configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:3000")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080/api")
HEADLESS = os.getenv("HEADLESS", "true").lower() == "true"

@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL

@pytest.fixture(scope="session")
def api_base_url() -> str:
    return API_BASE_URL
```

---

### 5.4 UI Test Execution Flow

**Scenario**: BDD scenario executes UI test with page objects.

**Flow Diagram**:
```
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
│  pytest  │────▶│ pytest-bdd │────▶│  Step Def    │────▶│  Page Object   │
│  Runner  │     │  Parser    │     │  Function    │     │    Method      │
└──────────┘     └────────────┘     └──────────────┘     └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │   Playwright   │
                                                          │     API        │
                                                          └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │  Chrome/       │
                                                          │  Firefox/      │
                                                          │  WebKit        │
                                                          └────────────────┘
                                                                  │
                                                                  ▼
                                                          ┌────────────────┐
                                                          │   Web App      │
                                                          │  (Browser)     │
                                                          └────────────────┘
```

**Example Execution Trace**:

**Feature File**: `tests/features/authentication.feature`
```gherkin
Scenario: Successful login with valid credentials
  Given a user exists with email "test@example.com"
  When the user logs in with valid credentials
  Then the user should be on the dashboard page
```

**Execution Steps**:

1. **pytest discovers** `tests/features/authentication.feature`
2. **pytest-bdd parses** Gherkin and identifies scenario
3. **Step 1**: `Given a user exists with email "test@example.com"`
   - Calls step definition in `tests/step_definitions/auth_steps.py`
   - Step definition calls MCP client `seed_user(email="test@example.com")`
   - User created in target system via FastAPI MCP
4. **Step 2**: `When the user logs in with valid credentials`
   - Calls step definition
   - Step definition receives `login_page` fixture (LoginPage instance)
   - Calls `login_page.navigate()` → Playwright navigates to `/login`
   - Calls `login_page.fill_email(user.email)` → Playwright types email
   - Calls `login_page.fill_password(user.password)` → Playwright types password
   - Calls `login_page.click_login_button()` → Playwright clicks button
5. **Step 3**: `Then the user should be on the dashboard page`
   - Calls step definition
   - Step definition receives `dashboard_page` fixture (DashboardPage instance)
   - Calls `dashboard_page.is_loaded()` → Playwright checks URL and DOM
   - Assertion passes if dashboard is visible
6. **pytest collects result** and reports pass/fail
7. **Allure captures** steps, screenshots, and metadata

---

### 5.5 API Test Execution Flow

**Scenario**: Test executes API operations with MCP-generated payloads.

**Flow Diagram**:
```
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
│  pytest  │────▶│  Test      │────▶│  MCP Client  │────▶│  FastAPI MCP   │
│  Runner  │     │  Function  │     │ (build_payload)│    │   Server       │
└──────────┘     └────────────┘     └──────────────┘     └────────────────┘
                                                                  │
                                                                  ▼
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
│  Allure  │◀────│  API       │◀────│  httpx       │◀────│  Target API    │
│  Report  │     │  Client    │     │  (POST)      │     │  (Response)    │
└──────────┘     └────────────┘     └──────────────┘     └────────────────┘
```

**Example Execution**:

**Test File**: `tests/api/test_users_api.py`
```python
def test_create_user_via_api(users_api_client, mcp_client):
    """Test user creation via API with MCP-generated payload."""
    
    # Step 1: Get valid payload from MCP
    payload = mcp_client.build_payload(
        template="create_user",
        overrides={"role": "admin"}
    )
    
    # Step 2: Send API request
    response = users_api_client.create_user(payload)
    
    # Step 3: Validate response
    assert response.status_code == 201
    assert response.json()["email"] == payload["email"]
    assert response.json()["role"] == "admin"
    
    # Step 4: Cleanup
    user_id = response.json()["id"]
    mcp_client.cleanup_resource("user", user_id)
```

**Execution Steps**:

1. **pytest discovers** `test_create_user_via_api`
2. **Fixtures injected**: `users_api_client` (httpx wrapper), `mcp_client`
3. **Test calls** `mcp_client.build_payload("create_user", {"role": "admin"})`
4. **MCP client** sends JSON-RPC to FastAPI MCP: `POST /tools/build_payload`
5. **FastAPI MCP** returns valid payload:
   ```json
   {
     "email": "test-uuid@example.com",
     "password": "SecurePass123",
     "first_name": "Test",
     "last_name": "User",
     "role": "admin"
   }
   ```
6. **Test calls** `users_api_client.create_user(payload)`
7. **API client** sends httpx POST request to target API
8. **Target API** creates user and returns 201 response
9. **API client** attaches request/response to Allure
10. **Test asserts** on response data
11. **Test calls** `mcp_client.cleanup_resource("user", user_id)`
12. **MCP client** deletes test user via target API
13. **pytest reports** test result (pass/fail)

---

### 5.6 Parallel Execution Flow (Isolated Contexts)

**Scenario**: Multiple tests run concurrently with isolated browser contexts.

**Flow Diagram**:
```
                        ┌──────────────┐
                        │   pytest     │
                        │   (Main)     │
                        └──────────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
         ┌────────────┐ ┌────────────┐ ┌────────────┐
         │  Worker 1  │ │  Worker 2  │ │  Worker 3  │
         │ (Process)  │ │ (Process)  │ │ (Process)  │
         └────────────┘ └────────────┘ └────────────┘
                │              │              │
                ▼              ▼              ▼
         ┌────────────┐ ┌────────────┐ ┌────────────┐
         │  Browser   │ │  Browser   │ │  Browser   │
         │ Context 1  │ │ Context 2  │ │ Context 3  │
         └────────────┘ └────────────┘ └────────────┘
                │              │              │
                ▼              ▼              ▼
         ┌────────────┐ ┌────────────┐ ┌────────────┐
         │   Page 1   │ │   Page 2   │ │   Page 3   │
         └────────────┘ └────────────┘ └────────────┘
                │              │              │
                └──────────────┴──────────────┘
                               │
                               ▼
                      ┌────────────────┐
                      │   Web App      │
                      │  (Concurrent)  │
                      └────────────────┘
```

**Isolation Guarantees**:

1. **Process Isolation**: Each worker runs in separate Python process
2. **Context Isolation**: Each test gets fresh browser context (not shared)
3. **Data Isolation**: Each test creates unique users (UUID-based emails)
4. **State Isolation**: No shared mutable state between tests

**Example Configuration (pytest.ini)**:
```ini
[pytest]
# Use all available CPU cores
addopts = -n auto

# Distribute tests by module (loadscope)
# Tests in same module run on same worker
addopts = --dist loadscope

# Alternatively, distribute by file
# addopts = --dist loadfile
```

**Fixture Example (conftest.py)**:
```python
@pytest.fixture(scope="function")
def browser_context(browser):
    """Create fresh context per test for isolation."""
    context = browser.new_context()
    yield context
    context.close()  # Cleanup after test
```

**Test Execution**:
- Worker 1 executes `test_login.py::test_valid_credentials`
- Worker 2 executes `test_login.py::test_invalid_password`
- Worker 3 executes `test_user_management.py::test_create_user`
- All workers access FastAPI MCP server concurrently (thread-safe)
- Each test receives isolated browser context
- No test affects another test's execution

---

### 5.7 LLM-Assisted Test Generation Flow

**Scenario**: LLM explores application and generates Gherkin scenarios.

**Flow Diagram**:
```
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
│ Developer│────▶│  LLM CLI   │────▶│  LLM Client  │────▶│ Playwright MCP │
│ (Trigger)│     │  Command   │     │  (OpenAI/    │     │    Server      │
└──────────┘     └────────────┘     │   Ollama)    │     └────────────────┘
                                     └──────────────┘              │
                                            │                      │
                                            └──────────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │   Browser      │
                                              │ (Exploration)  │
                                              └────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │  Web App       │
                                              │  (Target)      │
                                              └────────────────┘
                                                       │
                                                       ▼
┌──────────┐     ┌────────────┐     ┌──────────────┐     ┌────────────────┐
│ Developer│◀────│  GitHub PR │◀────│  Feature     │◀────│  Gherkin       │
│ (Review) │     │  (Pending) │     │  File Draft  │     │  Generator     │
└──────────┘     └────────────┘     └──────────────┘     └────────────────┘
```

**Workflow Steps**:

1. **Developer triggers** exploration:
   ```bash
   python -m llm.workflows.scenario_generator \
       --url https://staging.example.com \
       --objective "Test user registration flow"
   ```

2. **LLM client** connects to Playwright MCP server

3. **LLM explores** application:
   - Calls `navigate(url="https://staging.example.com")`
   - Calls `get_page_structure()` → Analyzes available actions
   - Calls `click(selector="button[aria-label='Sign Up']")`
   - Calls `type(selector="input[name='email']", text="test@example.com")`
   - Calls `screenshot()` → Captures state for analysis
   - Continues exploration based on objective

4. **Playwright MCP** records all actions with timestamps and context

5. **LLM generates** Gherkin scenarios:
   ```gherkin
   Feature: User Registration
   
   Scenario: Successful registration with valid details
     Given the user is on the registration page
     When the user enters a valid email address
     And the user enters a strong password
     And the user submits the registration form
     Then the user should receive a confirmation email
     And the user should be redirected to the dashboard
   ```

6. **Gherkin Generator** validates syntax using pytest-bdd parser

7. **Feature file** written to `tests/features/pending/registration.feature`

8. **GitHub PR created** with generated scenarios

9. **Developer reviews** scenarios:
   - ✅ Approve: Move to `tests/features/` and merge
   - ✏️ Edit: Refine scenarios and commit
   - ❌ Reject: Close PR with feedback

10. **Approved scenarios** become part of test suite

**Human Review Checklist**:
- [ ] Scenarios test correct business requirements
- [ ] Steps are business-readable (no implementation details)
- [ ] Expected behavior is accurate
- [ ] Edge cases are relevant and valuable
- [ ] Scenarios don't duplicate existing tests

---

## 6. Integration Points

This section catalogs all external and internal integration points in the framework.

### 6.1 External Integration Points

#### 6.1.1 Playwright Browser Binaries

**Integration Type**: Binary dependency downloaded at installation time

**Communication Protocol**: DevTools Protocol (CDP for Chromium, WebDriver BiDi for Firefox/WebKit)

**Installation**:
```bash
# Install browsers after pip install playwright
python -m playwright install chromium firefox webkit

# With system dependencies (Linux)
python -m playwright install --with-deps chromium
```

**CI/CD Integration**:
```dockerfile
# Use official Playwright Docker image
FROM mcr.microsoft.com/playwright/python:v1.55.0

# Browsers pre-installed
```

**Version Management**:
- Playwright Python package version determines browser versions
- Browser versions updated with Playwright package updates
- Explicit version pinning via Playwright version constraint

**Integration Points in Code**:
```python
# conftest.py
@pytest.fixture(scope="session")
def browser_type(playwright):
    """Select browser type from environment."""
    browser_name = os.getenv("BROWSER", "chromium")
    return getattr(playwright, browser_name)

@pytest.fixture(scope="session")
def browser(browser_type):
    """Launch browser instance."""
    return browser_type.launch(headless=os.getenv("HEADLESS", "true") == "true")
```

---

#### 6.1.2 OpenAI API / Ollama Local LLM

**Integration Type**: HTTP REST API (OpenAI), HTTP API (Ollama)

**OpenAI Integration**:
- **Endpoint**: `https://api.openai.com/v1/chat/completions`
- **Authentication**: Bearer token (`Authorization: Bearer sk-...`)
- **Models**: GPT-4 Turbo, GPT-3.5 Turbo
- **Rate Limits**: Tier-based (check OpenAI dashboard)

**Ollama Integration**:
- **Endpoint**: `http://localhost:11434/api/generate`
- **Authentication**: None (local installation)
- **Models**: Llama 2, Mistral, CodeLlama (downloaded locally)
- **Rate Limits**: None (local resource constraints only)

**Configuration**:
```bash
# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo
OPENAI_API_KEY=sk-...

# Ollama (Local)
LLM_PROVIDER=ollama
LLM_MODEL=llama2
OLLAMA_BASE_URL=http://localhost:11434
```

**Integration in Code**:
```python
# llm/client.py
from openai import OpenAI
import ollama

def get_llm_client() -> LLMClient:
    """Factory to create appropriate LLM client."""
    provider = os.getenv("LLM_PROVIDER", "ollama")
    
    if provider == "openai":
        return OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("LLM_MODEL", "gpt-4-turbo")
        )
    elif provider == "ollama":
        return OllamaProvider(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("LLM_MODEL", "llama2")
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
```

**Error Handling**:
- OpenAI: Retry with exponential backoff for rate limits (429)
- OpenAI: Fallback to GPT-3.5 if GPT-4 quota exhausted
- Ollama: Retry if local service not responding
- Both: Graceful degradation if LLM unavailable (skip generation)

---

#### 6.1.3 GitHub Actions CI/CD Platform

**Integration Type**: Workflow automation platform

**Webhook Triggers**:
- Push to `main` or `develop` branches
- Pull request opened/updated
- Manual workflow dispatch
- Scheduled (cron) execution

**GitHub Actions Features Used**:

| Feature | Purpose | Example |
|---------|---------|---------|
| **Matrix Strategy** | Parallel tests across environments | `matrix: python-version: [3.11, 3.12]` |
| **Service Containers** | Run MCP servers during tests | `services: fastapi-mcp: ...` |
| **Artifacts** | Store test results and reports | `actions/upload-artifact@v4` |
| **GitHub Pages** | Publish Allure HTML reports | `peaceiris/actions-gh-pages@v3` |
| **Secrets** | Secure credential storage | `${{ secrets.MCP_TOKEN }}` |
| **Caching** | Speed up dependency installation | `actions/cache@v4` |

**Integration in Workflows**:
```yaml
# .github/workflows/test.yml
name: Test Execution

on:
  push:
    branches: [main, develop]
  pull_request:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      fastapi-mcp:
        image: python:3.11
        env:
          FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
        ports:
          - 8000:8000
    
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run Tests
        env:
          FASTAPI_MCP_URL: http://localhost:8000
          FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
        run: pytest -n auto
```

**Status Checks**:
- Test execution must pass before PR merge
- Lint checks must pass
- Coverage threshold must be met (if configured)

---

#### 6.1.4 Application Under Test (Web UI and REST APIs)

**Integration Type**: HTTP/HTTPS communication

**Web UI Integration**:
- **Protocol**: HTTPS (typically)
- **Access**: Playwright browser automation
- **Authentication**: Session cookies, JWT tokens, OAuth
- **Base URL Configuration**: `BASE_URL` environment variable

**REST API Integration**:
- **Protocol**: HTTP/HTTPS
- **Access**: httpx client
- **Authentication**: Bearer tokens, API keys, OAuth
- **Base URL Configuration**: `API_BASE_URL` environment variable

**Environment-Specific Endpoints**:

| Environment | Web UI Base URL | API Base URL |
|-------------|-----------------|--------------|
| **Local** | `http://localhost:3000` | `http://localhost:8080/api` |
| **Staging** | `https://staging.example.com` | `https://api.staging.example.com` |
| **Production** | `https://example.com` | `https://api.example.com` |

**Integration Configuration**:
```python
# conftest.py
@pytest.fixture(scope="session")
def base_url() -> str:
    """Web UI base URL from environment."""
    url = os.getenv("BASE_URL", "http://localhost:3000")
    # Validate URL is accessible
    response = httpx.get(f"{url}/health", timeout=5.0)
    assert response.status_code == 200, f"App not accessible at {url}"
    return url

@pytest.fixture(scope="session")
def api_base_url() -> str:
    """REST API base URL from environment."""
    url = os.getenv("API_BASE_URL", "http://localhost:8080/api")
    # Validate API is accessible
    response = httpx.get(f"{url}/health", timeout=5.0)
    assert response.status_code == 200, f"API not accessible at {url}"
    return url
```

**Authentication Handling**:
- UI tests: Login via page object, store session cookies in browser context
- API tests: Obtain token via auth endpoint, include in httpx client headers
- MCP-seeded users: Auto-generate tokens via FastAPI MCP `seed_user` tool

---

#### 6.1.5 Allure Report Server (GitHub Pages)

**Integration Type**: Static site hosting

**Publishing Mechanism**:
- GitHub Actions workflow generates Allure HTML report
- `peaceiris/actions-gh-pages@v3` action pushes to `gh-pages` branch
- GitHub Pages serves from `gh-pages` branch

**Configuration**:
```yaml
# .github/workflows/allure-report.yml
- name: Deploy to GitHub Pages
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./allure-report
    keep_files: true  # Preserve history
```

**Repository Settings**:
- Enable GitHub Pages in repository settings
- Set source to `gh-pages` branch
- Report accessible at `https://<org>.github.io/<repo>/`

**Report Retention**:
- Allure history preserved across runs via `allure-history` directory
- Trend charts show pass/fail rates over time
- Historical data helps identify flaky tests

---

### 6.2 Internal Integration Points

#### 6.2.1 conftest.py → Page Objects

**Integration Pattern**: Dependency injection via pytest fixtures

**Flow**:
```python
# conftest.py
@pytest.fixture
def page(browser_context) -> Page:
    """Provide Playwright page."""
    page = browser_context.new_page()
    yield page
    page.close()

@pytest.fixture
def login_page(page) -> LoginPage:
    """Provide LoginPage object."""
    return LoginPage(page)

# Test uses fixture
def test_login(login_page):
    login_page.navigate()
    # ...
```

**Dependencies**:
- Page objects depend on Playwright `Page` instance
- `Page` instance comes from `browser_context` fixture
- `browser_context` comes from `browser` fixture
- Fixtures form dependency chain managed by pytest

---

#### 6.2.2 Step Definitions → Page Objects

**Integration Pattern**: Gherkin steps delegate to page object methods

**Flow**:
```python
# tests/step_definitions/auth_steps.py
from pytest_bdd import when

@when("the user logs in with valid credentials")
def perform_login(login_page: LoginPage, test_user: dict):
    """Delegate to page object."""
    login_page.navigate()
    login_page.fill_email(test_user["email"])
    login_page.fill_password(test_user["password"])
    login_page.click_login_button()
```

**Benefits**:
- Step definitions stay business-focused
- Page objects encapsulate implementation details
- Changes to UI only require page object updates
- Step definitions remain stable

---

#### 6.2.3 Step Definitions → API Clients

**Integration Pattern**: Gherkin API steps use typed httpx clients

**Flow**:
```python
# tests/step_definitions/api_steps.py
from pytest_bdd import when, then

@when(parsers.parse('a POST request is sent to "{endpoint}" with valid data'))
def send_post_request(endpoint: str, users_api_client: UsersAPIClient, context: dict):
    """Use API client to send request."""
    payload = context["payload"]
    response = users_api_client.create_user(payload)
    context["response"] = response

@then(parsers.parse('the API returns status code {status_code:d}'))
def verify_status_code(status_code: int, context: dict):
    """Verify response status."""
    assert context["response"].status_code == status_code
```

---

#### 6.2.4 API Clients → MCP Client

**Integration Pattern**: API tests use MCP `build_payload` tool for request bodies

**Flow**:
```python
# tests/api/test_users_api.py
def test_create_user(users_api_client, mcp_client):
    """API test with MCP-generated payload."""
    
    # Get payload from MCP
    payload = mcp_client.build_payload("create_user", {"role": "admin"})
    
    # Use in API request
    response = users_api_client.create_user(payload)
    
    assert response.status_code == 201
```

**Benefits**:
- No hardcoded test data
- Payloads always match current API schema
- Deterministic test data generation

---

#### 6.2.5 Page Objects → MCP Client

**Integration Pattern**: UI tests use MCP `seed_user` tool for test users

**Flow**:
```python
# Test creates user via MCP, then uses in UI
def test_dashboard_access(login_page, dashboard_page, mcp_client):
    """UI test with MCP-seeded user."""
    
    # Create user via MCP
    user = mcp_client.seed_user(email="test@example.com", role="customer")
    
    # Login via UI
    login_page.navigate()
    login_page.login(user.email, user.password)
    
    # Verify dashboard
    assert dashboard_page.is_loaded()
```

---

#### 6.2.6 pytest → Allure

**Integration Pattern**: Pytest hooks capture metadata for Allure reporting

**Flow**:
```python
# conftest.py
import allure
from allure_commons.types import AttachmentType

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Attach screenshot on test failure."""
    outcome = yield
    result = outcome.get_result()
    
    if result.when == "call" and result.failed:
        if "page" in item.funcargs:
            page = item.funcargs["page"]
            screenshot = page.screenshot()
            allure.attach(
                screenshot,
                name="Failure Screenshot",
                attachment_type=AttachmentType.PNG
            )
```

**Captured Metadata**:
- Test name, description, duration
- Feature, story, severity (from decorators)
- Steps (from `@allure.step` or `with allure.step()`)
- Attachments (screenshots, logs, API payloads)
- Environment information (browser, URLs, versions)

---

#### 6.2.7 LLM Workflows → Feature Files

**Integration Pattern**: LLM-generated Gherkin written to feature files

**Flow**:
```python
# llm/workflows/scenario_generator.py
def save_generated_scenarios(feature_content: str, feature_name: str):
    """Write LLM-generated scenarios to pending directory."""
    
    # Validate syntax
    try:
        validate_gherkin_syntax(feature_content)
    except GherkinSyntaxError as e:
        raise ValueError(f"Invalid Gherkin syntax: {e}")
    
    # Write to pending directory for review
    pending_dir = Path("tests/features/pending")
    pending_dir.mkdir(exist_ok=True)
    
    feature_file = pending_dir / f"{feature_name}.feature"
    feature_file.write_text(feature_content)
    
    print(f"Generated feature file: {feature_file}")
    print("Please review and move to tests/features/ after approval.")
```

**Review Process**:
1. Generated scenarios in `tests/features/pending/`
2. Human reviews for correctness
3. Approved scenarios moved to `tests/features/`
4. pytest-bdd discovers and executes

---

#### 6.2.8 GitHub Actions → MCP Servers

**Integration Pattern**: CI pipeline starts FastAPI MCP as service container

**Flow**:
```yaml
# .github/workflows/test.yml
services:
  fastapi-mcp:
    image: python:3.11
    env:
      FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
      DATABASE_URL: ${{ secrets.TEST_DB_URL }}
    ports:
      - 8000:8000
    options: >-
      --health-cmd "curl -f http://localhost:8000/health || exit 1"
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

**Test Configuration**:
```yaml
steps:
  - name: Run Tests
    env:
      FASTAPI_MCP_URL: http://localhost:8000
      FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
    run: pytest -n auto
```

**Integration Benefits**:
- MCP server available during test execution
- Automatic cleanup after workflow completes
- Isolated per workflow run (no state leakage)

---

## 7. Technology Foundation

This section details the technology stack, version requirements, and rationale for each technology choice.

### 7.1 Python Version Requirement

**Minimum Version**: Python 3.9

**Recommended Version**: Python 3.11 or Python 3.12

**Rationale**:
- **Playwright 1.55.0** dropped Python 3.8 support, requires 3.9+
- **pytest 8.4.2** dropped Python 3.8 support
- **Modern type hints** (PEP 604 union syntax `X | Y`) require 3.10+
- **Performance improvements** in 3.11 (10-25% faster than 3.9)
- **Enhanced error messages** in 3.11+ for better debugging
- **Stable and well-supported** in CI/CD environments

**Version Specification**:
```
# .python-version (for pyenv)
3.11
```

```toml
# pyproject.toml
[project]
requires-python = ">=3.9"
```

---

### 7.2 Core Testing Framework

#### pytest 8.4.2

**Purpose**: Core test execution engine

**Key Features Used**:
- Test discovery with customizable patterns
- Fixture dependency injection
- Parametrized testing
- Plugin architecture (pytest-bdd, pytest-playwright, allure-pytest)
- Parallel execution (via pytest-xdist)

**Configuration**:
```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -n auto --alluredir=allure-results
```

**Why pytest**:
- Industry-standard Python test framework
- Rich plugin ecosystem
- Excellent fixture management
- Strong BDD support via pytest-bdd

---

#### pytest-bdd 8.1.0

**Purpose**: Gherkin/BDD support for pytest

**Key Features Used**:
- Parse `.feature` files using official Gherkin parser
- Bind Gherkin steps to Python functions via decorators
- Support for Scenario Outlines and data tables
- Feature file discovery and organization

**Usage Example**:
```python
from pytest_bdd import scenario, given, when, then

@scenario("features/authentication.feature", "Successful login")
def test_successful_login():
    pass

@given("a user exists with email \"test@example.com\"")
def create_user(mcp_client):
    return mcp_client.seed_user(email="test@example.com")
```

**Why pytest-bdd**:
- Tight integration with pytest fixture system
- Uses official Gherkin parser for spec compliance
- Supports step reuse across scenarios
- Better than behave for pytest-centric projects

---

#### playwright 1.55.0

**Purpose**: Browser automation library

**Key Features Used**:
- Cross-browser support (Chromium, Firefox, WebKit)
- Auto-wait for elements (reduces flakiness)
- Network interception and mocking
- Trace collection for debugging
- Stable locator strategies (ARIA, test IDs)

**Locator API**:
```python
# Preferred: ARIA role
page.get_by_role("button", name="Login")

# Preferred: Label association
page.get_by_label("Email Address")

# Preferred: Test ID
page.get_by_test_id("submit-button")

# Avoid: Brittle CSS
page.locator(".auth-form > button:nth-child(2)")  # ❌
```

**Why Playwright**:
- Modern API with auto-waiting (reduces test flakiness)
- Superior debugging with traces and screenshots
- Fast and reliable compared to Selenium
- Excellent Python support and documentation

---

#### pytest-playwright 0.6.2

**Purpose**: pytest integration for Playwright

**Key Features**:
- Provides `browser`, `context`, `page` fixtures
- Automatic browser lifecycle management
- CLI options for browser selection (`--browser chromium`)
- Automatic screenshot on failure
- Trace collection configuration

**Fixtures Provided**:
```python
def test_example(page):
    """Test receives page fixture automatically."""
    page.goto("https://example.com")
    assert page.title() == "Example Domain"
```

**Why pytest-playwright**:
- Official Playwright integration for pytest
- Simplifies browser lifecycle management
- Reduces boilerplate in tests

---

### 7.3 API Testing Stack

#### httpx 0.28.1

**Purpose**: Modern HTTP client for API testing

**Key Features Used**:
- Synchronous and asynchronous APIs
- HTTP/2 support
- Connection pooling and timeouts
- Request/response interceptors
- Excellent type hints

**Usage Example**:
```python
import httpx

client = httpx.Client(base_url="https://api.example.com")
response = client.post("/users", json={"email": "test@example.com"})
assert response.status_code == 201
```

**Why httpx over requests**:
- Modern async/await support
- HTTP/2 support
- Better performance with connection pooling
- Active development and maintenance
- Superior type hints for IDE support

---

#### pydantic 2.10.5

**Purpose**: Data validation and settings management

**Key Features Used**:
- Request/response model validation
- Automatic type coercion and validation
- JSON schema generation
- Settings management from environment variables
- Excellent error messages

**Usage Example**:
```python
from pydantic import BaseModel, EmailStr

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "customer"

# Automatic validation
request = UserCreateRequest(
    email="test@example.com",
    password="SecurePass123"
)
```

**Why pydantic**:
- De facto standard for data validation in Python
- Pydantic v2 offers significant performance improvements
- Integrates seamlessly with FastAPI
- Reduces boilerplate validation code

---

### 7.4 MCP Server Stack

#### FastAPI 0.118.0

**Purpose**: Web framework for MCP servers

**Key Features Used**:
- Automatic API documentation (OpenAPI/Swagger)
- Request/response validation with Pydantic
- Dependency injection system
- Async request handling
- WebSocket support (for Playwright MCP)

**Usage Example**:
```python
from fastapi import FastAPI, Depends

app = FastAPI()

@app.post("/tools/seed_user")
async def seed_user(
    request: SeedUserRequest,
    user_service: UserService = Depends()
) -> SeedUserResponse:
    user = await user_service.create_test_user(request)
    return SeedUserResponse.from_user(user)
```

**Why FastAPI**:
- Fast and modern Python web framework
- Automatic validation and serialization
- Built-in OpenAPI documentation
- Excellent async support for high concurrency
- Strong type safety with Pydantic

---

#### uvicorn 0.34.0

**Purpose**: ASGI server for running FastAPI applications

**Key Features**:
- High-performance async server
- Automatic reloading in development
- WebSocket support
- Graceful shutdown handling

**Usage**:
```bash
# Development
uvicorn mcp_servers.fastapi_mcp.main:app --reload

# Production
uvicorn mcp_servers.fastapi_mcp.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4
```

**Why uvicorn**:
- Recommended ASGI server for FastAPI
- Excellent performance
- Reliable and well-maintained

---

#### SQLAlchemy 2.0.38 (Optional)

**Purpose**: Database ORM for MCP state management

**Key Features Used**:
- Async ORM for database operations
- Migration support with Alembic
- Connection pooling
- Query builder

**Usage Example**:
```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

async def get_test_users(session: AsyncSession) -> list[User]:
    result = await session.execute(select(User).where(User.is_test == True))
    return result.scalars().all()
```

**Why SQLAlchemy 2.0**:
- Modern async support (new in 2.0)
- Industry-standard Python ORM
- Strong type hints
- Comprehensive documentation

**Note**: SQLAlchemy is optional; MCP servers can use direct API calls instead.

---

### 7.5 LLM Integration Stack

#### openai 1.59.8

**Purpose**: OpenAI API client (also works with OpenAI-compatible APIs)

**Compatible APIs**:
- OpenAI (GPT-4, GPT-3.5)
- Azure OpenAI Service
- Anthropic Claude (with adapter)
- Local models via LiteLLM

**Usage Example**:
```python
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[
        {"role": "system", "content": "You are a QA expert."},
        {"role": "user", "content": "Generate test scenarios for user login."}
    ]
)

scenarios = response.choices[0].message.content
```

**Why openai**:
- Official Python client from OpenAI
- Supports OpenAI-compatible APIs
- Strong type hints
- Async support

---

#### ollama 0.4.8

**Purpose**: Local LLM client for cost-free development

**Supported Models**:
- Llama 2 (Meta)
- Mistral (Mistral AI)
- CodeLlama (Meta, code-focused)
- Many others from Ollama library

**Usage Example**:
```python
import ollama

response = ollama.generate(
    model="llama2",
    prompt="Generate Gherkin scenarios for user registration."
)

scenarios = response['response']
```

**Why ollama**:
- Free local LLM inference
- No API costs during development
- Privacy (no data sent to external APIs)
- Easy model switching

---

### 7.6 Reporting Stack

#### allure-pytest 2.15.0

**Purpose**: Allure reporting integration for pytest

**Key Features**:
- Rich HTML reports with test history
- Test categorization (features, stories, severity)
- Screenshots and log attachments
- Trend charts and metrics
- Integration with CI/CD

**Usage Example**:
```python
import allure

@allure.feature("Authentication")
@allure.story("User Login")
@allure.severity(allure.severity_level.CRITICAL)
def test_login(login_page):
    with allure.step("Navigate to login page"):
        login_page.navigate()
    
    with allure.step("Enter credentials"):
        login_page.fill_email("test@example.com")
        login_page.fill_password("password123")
    
    with allure.step("Submit form"):
        login_page.click_login_button()
```

**Report Generation**:
```bash
# Run tests with Allure
pytest --alluredir=allure-results

# Generate HTML report
allure generate allure-results -o allure-report

# Open report
allure open allure-report
```

**Why allure-pytest**:
- Industry-standard test reporting
- Beautiful, informative HTML reports
- Excellent CI/CD integration
- Historical trend analysis

---

### 7.7 Development Tools

#### ruff 0.9.3

**Purpose**: Fast Python linter and formatter

**Features**:
- Replaces flake8, pylint, isort, black (all-in-one)
- 10-100x faster than alternatives
- Automatic code fixing
- Extensive rule set

**Configuration**:
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line too long (handled by formatter)
```

**Why ruff**:
- Significantly faster than traditional tools
- Reduces tooling complexity (replaces multiple tools)
- Active development and community support

---

#### mypy 1.14.1

**Purpose**: Static type checker for Python

**Features**:
- Catch type errors before runtime
- Improve IDE autocomplete and refactoring
- Enforce type safety across codebase
- Gradual typing support

**Configuration**:
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Why mypy**:
- De facto standard for Python type checking
- Catches bugs early in development
- Improves code maintainability

---

### 7.8 Utility Dependencies

| Package | Version | Purpose | Rationale |
|---------|---------|---------|-----------|
| **python-dotenv** | 1.0.1 | Load `.env` files | Standard for local env config |
| **faker** | 34.2.0 | Generate realistic test data | Best-in-class data generation |
| **tenacity** | 9.1.1 | Retry logic for flaky operations | Robust retry strategies |
| **loguru** | 0.7.3 | Enhanced logging | Better than stdlib logging |
| **typer** | 0.15.2 | CLI tool building | Modern CLI framework |
| **pytest-xdist** | 3.6.1 | Parallel test execution | Essential for fast CI |
| **pytest-timeout** | 2.3.1 | Test timeout management | Prevent hanging tests |
| **pytest-asyncio** | 0.25.2 | Async test support | Required for async tests |

---

### 7.9 Dependency Management Strategy

#### Requirements Files

**requirements.txt** (Production):
```
pytest==8.4.2
pytest-bdd==8.1.0
playwright==1.55.0
pytest-playwright==0.6.2
httpx==0.28.1
pydantic==2.10.5
allure-pytest==2.15.0
python-dotenv==1.0.1
```

**requirements-dev.txt** (Development):
```
-r requirements.txt
ruff==0.9.3
mypy==1.14.1
pre-commit==4.0.1
pytest-cov==6.0.0
pytest-xdist==3.6.1
faker==34.2.0
```

**pyproject.toml** (Modern Python Packaging):
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "test-automation-framework"
version = "1.0.0"
requires-python = ">=3.9"
dependencies = [
    "pytest>=8.4.2",
    "playwright>=1.55.0",
    # ... other dependencies
]

[project.optional-dependencies]
dev = [
    "ruff>=0.9.3",
    "mypy>=1.14.1",
    # ... other dev dependencies
]
```

#### Installation Commands

**Local Development Setup**:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Install Playwright browsers
python -m playwright install chromium

# Install pre-commit hooks
pre-commit install
```

**CI/CD Setup**:
```bash
# Use Playwright Docker image (browsers pre-installed)
docker pull mcr.microsoft.com/playwright/python:v1.55.0

# Or install on standard Python image
pip install -r requirements.txt
playwright install --with-deps chromium
```

#### Dependency Update Policy

- **Major versions**: Manual review and testing required
- **Minor versions**: Automated via Dependabot, reviewed in PR
- **Patch versions**: Auto-merge if tests pass
- **Security updates**: Immediate priority
- **Pin all versions**: Ensure reproducible builds

---

## 8. Architecture Diagrams

### 8.1 High-Level Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CI/CD Orchestration Layer                          │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │  GitHub Actions │──│  Allure Report  │──│   Lint & Type   │            │
│  │    Workflows    │  │   Publishing    │  │     Checks      │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                    ┌───────────┴──────────┐
                    │                      │
┌───────────────────▼──────────┐  ┌────────▼──────────────────────────────────┐
│   Optional LLM Service       │  │    Supporting MCP Services Layer          │
│                              │  │                                           │
│  ┌────────────────────────┐  │  │  ┌──────────────┐  ┌──────────────────┐  │
│  │  LLM Client (OpenAI/   │  │  │  │  FastAPI MCP │  │ Playwright MCP   │  │
│  │      Ollama)           │◄─┼──┼─▶│  Server      │  │    Server        │  │
│  └────────────────────────┘  │  │  │  (CI/Prod)   │  │  (Dev Only)      │  │
│                              │  │  └──────────────┘  └──────────────────┘  │
│  ┌────────────────────────┐  │  │         │                   │            │
│  │  Scenario Generator    │  │  │         │                   │            │
│  │  Edge Case Suggester   │  │  │         │   ┌───────────────┘            │
│  └────────────────────────┘  │  │         │   │                            │
└──────────────────────────────┘  └─────────┼───┼────────────────────────────┘
                                            │   │
                    ┌───────────────────────┴───┴────┐
                    │                                │
┌───────────────────▼──────────┐  ┌─────────────────▼──────────────────────────┐
│      Test Asset Layer        │  │       Test Runner Layer                    │
│                              │  │                                            │
│  ┌────────────────────────┐  │  │  ┌─────────────────────────────────────┐  │
│  │  Page Objects          │  │  │  │  pytest Core                        │  │
│  │  (Stable Locators)     │◄─┼──┼──│  + pytest-bdd (Gherkin)             │  │
│  └────────────────────────┘  │  │  │  + pytest-playwright (Browser)      │  │
│                              │  │  │  + pytest-xdist (Parallel)          │  │
│  ┌────────────────────────┐  │  │  └─────────────────────────────────────┘  │
│  │  API Clients           │  │  │                                            │
│  │  (httpx + Pydantic)    │◄─┼──┤                                            │
│  └────────────────────────┘  │  │  ┌─────────────────────────────────────┐  │
│                              │  │  │  Fixture Management (conftest.py)   │  │
│  ┌────────────────────────┐  │  │  │  - Browser contexts                 │  │
│  │  Gherkin Features      │  │  │  │  - Page object instances            │  │
│  │  Step Definitions      │◄─┼──┼──│  - API client instances             │  │
│  └────────────────────────┘  │  │  │  - MCP client instance              │  │
│                              │  │  └─────────────────────────────────────┘  │
└──────────────────────────────┘  └────────────────────────────────────────────┘
                                                    │
                    ┌───────────────────────────────┴──────────────────┐
                    │                                                  │
┌───────────────────▼────────────────────┐  ┌──────────────────────────▼───────┐
│    Application Under Test              │  │    Browser Binaries              │
│                                        │  │                                  │
│  ┌──────────────┐  ┌────────────────┐ │  │  ┌─────────┐  ┌──────────────┐  │
│  │   Web UI     │  │   REST APIs    │ │  │  │Chromium │  │   Firefox    │  │
│  │  (Browser)   │  │  (HTTP/JSON)   │ │  │  └─────────┘  └──────────────┘  │
│  └──────────────┘  └────────────────┘ │  │                                  │
│                                        │  │  ┌──────────────┐               │
│  ┌─────────────────────────────────┐  │  │  │   WebKit     │               │
│  │      Database / Backend         │  │  │  └──────────────┘               │
│  └─────────────────────────────────┘  │  │                                  │
└────────────────────────────────────────┘  └──────────────────────────────────┘
```

**Legend**:
- `──▶`: Data/control flow
- `◄──`: Bidirectional communication
- Boxes: System components or layers
- Vertical stacking: Layer hierarchy (top = orchestration, bottom = execution)

---

### 8.2 Test Execution Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Test Execution Lifecycle                            │
└─────────────────────────────────────────────────────────────────────────────┘

     START
       │
       ▼
┌─────────────────┐
│ pytest discovers│
│  test files     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Load conftest.py│
│ Define fixtures │
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│  pytest-bdd     │  │  pytest-        │
│  parses .feature│  │  playwright     │
│     files       │  │  launches       │
│                 │  │  browser        │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └──────────┬─────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  Test Function  │
           │   Execution     │
           └────────┬────────┘
                    │
     ┌──────────────┼──────────────┐
     │              │              │
     ▼              ▼              ▼
┌─────────┐  ┌─────────────┐  ┌────────────┐
│  Given  │  │    When     │  │    Then    │
│  Steps  │  │   Steps     │  │   Steps    │
└────┬────┘  └──────┬──────┘  └─────┬──────┘
     │              │               │
     ▼              ▼               ▼
┌─────────┐  ┌─────────────┐  ┌────────────┐
│   MCP   │  │    Page     │  │  Assertions│
│ seed_   │  │   Object    │  │  (assert)  │
│  user   │  │   Methods   │  │            │
└────┬────┘  └──────┬──────┘  └─────┬──────┘
     │              │               │
     │              ▼               │
     │       ┌─────────────┐        │
     │       │ Playwright  │        │
     │       │   Actions   │        │
     │       │ (navigate,  │        │
     │       │  click, etc)│        │
     │       └──────┬──────┘        │
     │              │               │
     │              ▼               │
     │       ┌─────────────┐        │
     │       │   Browser   │        │
     │       │ Automation  │        │
     │       └──────┬──────┘        │
     │              │               │
     └──────────────┴───────────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  Allure Plugin  │
           │  Captures Steps │
           │  & Attachments  │
           └────────┬────────┘
                    │
                    ▼
           ┌─────────────────┐
           │  Test Result    │
           │  (Pass/Fail)    │
           └────────┬────────┘
                    │
                    ▼
              COMPLETE
```

---

### 8.3 CI/CD Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GitHub Actions Pipeline                            │
└─────────────────────────────────────────────────────────────────────────────┘

       Trigger: Push to main/develop, PR opened
                         │
                         ▼
              ┌────────────────────┐
              │  Checkout Code     │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │  Set Up Python     │
              │    (3.11, 3.12)    │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Install Dependencies│
              │  (requirements.txt) │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Install Playwright │
              │    Browsers        │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Start FastAPI MCP  │
              │  Server (Service)  │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │  Run Tests         │
              │  (pytest -n auto)  │
              └──────────┬─────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌─────────────┐ ┌─────────────┐
│ Chromium Tests │ │Firefox Tests│ │WebKit Tests │
│   (Matrix)     │ │  (Matrix)   │ │  (Matrix)   │
└────────┬───────┘ └──────┬──────┘ └──────┬──────┘
         │                │               │
         └────────────────┴───────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Collect Test       │
              │ Results & Traces   │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Upload Artifacts   │
              │ (allure-results)   │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Generate Allure    │
              │  HTML Report       │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Publish to GitHub  │
              │      Pages         │
              └──────────┬─────────┘
                         │
                         ▼
                  Pipeline Complete
                  Report URL: https://<org>.github.io/<repo>/
```

---

### 8.4 MCP Server Integration Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Test Data Management via MCP                            │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐                ┌─────────────────┐                ┌─────────┐
│   pytest     │   JSON-RPC     │  FastAPI MCP    │   HTTP/API     │ Target  │
│    Test      │───Request──────▶   Server        │───Calls────────▶  App    │
│              │                │                 │                │         │
│  (Step Def)  │◀──Response─────│  (seed_user,    │◀───Response────│(Backend)│
│              │     JSON       │  build_payload, │     JSON       │         │
└──────────────┘                │   reset_env)    │                └─────────┘
                                └─────────────────┘
                                        │
                                        │ State Management
                                        ▼
                                ┌─────────────────┐
                                │   Database      │
                                │  (Test State)   │
                                └─────────────────┘

Tools Provided by FastAPI MCP:
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  seed_user(email, password, role)                                       │
│    → Creates test user in target system                                 │
│    → Returns user_id, email, auth_token                                 │
│                                                                          │
│  build_payload(template, overrides)                                     │
│    → Generates valid API request body                                   │
│    → Returns JSON payload conforming to schema                          │
│                                                                          │
│  reset_env(scope)                                                       │
│    → Clears test data for specified scope                               │
│    → Returns confirmation                                               │
│                                                                          │
│  query_state(resource, filter)                                          │
│    → Inspects current test environment state                            │
│    → Returns resource data matching filter                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

### 8.5 LLM-Assisted Test Generation Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              LLM-Driven Exploration and Scenario Generation                 │
└─────────────────────────────────────────────────────────────────────────────┘

Developer Triggers Exploration:
  $ python -m llm.workflows.scenario_generator --url <app_url>
                         │
                         ▼
              ┌────────────────────┐
              │   LLM Client       │
              │  (OpenAI/Ollama)   │
              └──────────┬─────────┘
                         │ MCP Tool Calls
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌────────────────┐ ┌─────────────┐ ┌─────────────┐
│   navigate()   │ │   click()   │ │   type()    │
│   get_page_    │ │ screenshot()│ │  analyze()  │
│   structure()  │ │             │ │             │
└────────┬───────┘ └──────┬──────┘ └──────┬──────┘
         │                │               │
         └────────────────┴───────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ Playwright MCP     │
              │     Server         │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │    Browser         │
              │  (Automated)       │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │   Web App          │
              │  (Exploration)     │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │  Gherkin Generator │
              │  (converts actions │
              │   to scenarios)    │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │  Feature File      │
              │  (Draft Scenario)  │
              │  tests/features/   │
              │     pending/       │
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │  Human Review      │
              │  (GitHub PR)       │
              └──────────┬─────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
  ┌──────────┐   ┌─────────────┐  ┌──────────┐
  │  Approve │   │    Edit     │  │  Reject  │
  └────┬─────┘   └──────┬──────┘  └────┬─────┘
       │                │              │
       ▼                ▼              ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Move to     │  │  Refine &   │  │  Close PR   │
│ tests/      │  │  Commit     │  │  w/ Feedback│
│ features/   │  │             │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
```

---

## 9. Summary and Key Takeaways

### 9.1 Architectural Principles Recap

This test automation framework is built on eight core principles:

1. **Test Execution Primacy**: pytest remains the sole test runner
2. **Deterministic Test Design**: Fresh contexts and MCP-managed data
3. **Separation of Concerns**: Clear layer boundaries
4. **Business-Readable Specifications**: High-level Gherkin scenarios
5. **Stable Locator Strategy**: ARIA roles and semantic selectors
6. **Environment-Based Configuration**: Externalized runtime settings
7. **Parallel Execution Safety**: Isolated, concurrent-friendly tests
8. **Human-in-the-Loop LLM**: Generation assistance with human approval

### 9.2 Layer Responsibilities

| Layer | Primary Responsibility | Key Technologies |
|-------|----------------------|------------------|
| **Layer 1: Test Runner** | Execute tests, manage fixtures | pytest, pytest-bdd, Playwright |
| **Layer 2: Test Assets** | Implement test logic, interactions | Page Objects, API Clients, Gherkin |
| **Layer 3: MCP Services** | Provide deterministic data, exploration | FastAPI, Playwright MCP |
| **Layer 4: LLM Integration** | Generate scenarios, suggest edge cases | OpenAI, Ollama, LangChain |
| **Layer 5: CI/CD Orchestration** | Automate execution, reporting | GitHub Actions, Allure |

### 9.3 Integration Patterns

**Data Flow Patterns**:
- Test data provisioning via MCP `seed_user` tool
- Test result collection via Allure pytest plugin
- Environment configuration via `.env` files and GitHub Secrets
- Parallel execution with isolated browser contexts

**Communication Patterns**:
- pytest fixtures inject dependencies (page objects, API clients)
- Step definitions delegate to page objects (separation of concerns)
- MCP clients abstract JSON-RPC communication
- LLM workflows orchestrate exploration and generation

### 9.4 Key Benefits

**For Developers**:
- Fast, reliable test execution with pytest
- Clear separation between test logic and implementation
- Rich debugging with Playwright traces
- Type safety with Pydantic and mypy

**For QA Engineers**:
- Business-readable Gherkin scenarios
- Stable, maintainable page objects
- Deterministic test data management
- LLM assistance for scenario generation

**For DevOps/CI Teams**:
- Automated test execution in GitHub Actions
- Beautiful Allure reports published to GitHub Pages
- Parallel execution for fast feedback
- Clear environment configuration via secrets

**For Product Teams**:
- Tests serve as living documentation
- Scenarios readable by non-technical stakeholders
- Edge cases suggested by LLM analysis
- High confidence in release quality

### 9.5 Extension Points

This architecture is designed for extensibility:

**Adding New Test Types**:
- Create new page objects in `tests/pages/`
- Add API clients in `tests/api_clients/`
- Write Gherkin scenarios in `tests/features/`
- Implement step definitions in `tests/step_definitions/`

**Adding New MCP Tools**:
- Implement tool in `mcp_servers/fastapi_mcp/services/`
- Add endpoint in `mcp_servers/fastapi_mcp/routers/tools.py`
- Update MCP client in `tests/helpers/mcp_client.py`

**Adding New LLM Providers**:
- Implement provider in `llm/providers/`
- Update factory in `llm/client.py`
- Configure via environment variables

**Adding New Browsers**:
- Update pytest.ini with browser name
- Install browser with `playwright install <browser>`
- Add to CI/CD matrix strategy

### 9.6 Maintenance Considerations

**Regular Maintenance Tasks**:
- Update dependencies monthly (security patches)
- Review and refactor flaky tests
- Update Gherkin scenarios as features change
- Clean up test data via MCP `reset_env` tool
- Review Allure trend charts for quality metrics

**When Scaling**:
- Increase pytest-xdist workers for faster execution
- Partition tests by feature area for targeted runs
- Add dedicated MCP server instances for load distribution
- Implement test result database for long-term analytics

---

## 10. Additional Resources

### 10.1 Related Documentation

- **[Getting Started Guide](./getting_started.md)**: Quick start instructions
- **[Writing Tests Guide](./writing_tests.md)**: Test authoring best practices
- **[Page Objects Guide](./page_objects.md)**: Page Object Pattern guidelines
- **[MCP Servers Guide](./mcp_servers.md)**: MCP server usage and API reference
- **[LLM Integration Guide](./llm_integration.md)**: LLM-assisted test generation
- **[CI/CD Documentation](./ci_cd.md)**: Pipeline configuration and troubleshooting
- **[Troubleshooting Guide](./troubleshooting.md)**: Common issues and solutions

### 10.2 External References

**pytest Documentation**:
- Official docs: https://docs.pytest.org/
- pytest-bdd plugin: https://pytest-bdd.readthedocs.io/

**Playwright Documentation**:
- Python guide: https://playwright.dev/python/
- Best practices: https://playwright.dev/docs/best-practices

**FastAPI Documentation**:
- Official docs: https://fastapi.tiangolo.com/
- Async patterns: https://fastapi.tiangolo.com/async/

**Allure Reporting**:
- Allure docs: https://docs.qameta.io/allure/
- pytest integration: https://docs.qameta.io/allure/#_pytest

### 10.3 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on:
- Code style and standards
- Pull request process
- Test coverage requirements
- Documentation updates

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-10  
**Maintained By**: QA Engineering Team

