# Model Context Protocol (MCP) Servers

## Table of Contents

- [Overview and Purpose](#overview-and-purpose)
- [Architecture Overview](#architecture-overview)
- [FastAPI MCP Server (Production/CI)](#fastapi-mcp-server-productionci)
- [Playwright MCP Server (Development/Exploration)](#playwright-mcp-server-developmentexploration)
- [MCP Client Integration](#mcp-client-integration)
- [Authentication and Security](#authentication-and-security)
- [Error Handling](#error-handling)
- [Testing MCP Servers](#testing-mcp-servers)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Environment-Specific Behavior](#environment-specific-behavior)

## Overview and Purpose

### What is Model Context Protocol (MCP)?

Model Context Protocol (MCP) is a standardized JSON-RPC interface that enables Language Learning Models (LLMs) and automated systems to interact with external tools and services through a consistent, predictable API. In the context of test automation, MCP servers act as intelligent middleware between your test suite and the application under test.

### Why MCP Servers for Test Automation?

Traditional test automation frameworks often struggle with:

- **Hardcoded Test Data**: Test files contain brittle, static data that breaks when application requirements change
- **Non-Deterministic State**: Tests fail unpredictably due to unknown initial conditions
- **Manual Test Authoring**: Writing comprehensive test scenarios requires significant human effort
- **Environment Setup Complexity**: Each test environment requires custom initialization logic

MCP servers solve these problems by providing:

1. **Deterministic Test Data Management**: Generate valid test data programmatically via API calls
2. **Known-Good State Reset**: Return environments to baseline conditions before test execution
3. **LLM-Assisted Test Discovery**: Enable AI agents to explore applications and generate test scenarios
4. **Separation of Concerns**: Keep test logic focused on behavior verification, not data management

### Separation of Concerns: Pytest Executes Tests, MCP Manages State

**Critical Architectural Principle**: Tests execute inside pytest (fast, reliable), while MCP servers run alongside as supporting services.

```
┌──────────────────────────────────────────────────────────────┐
│                     Test Execution Layer                      │
│                                                                │
│  pytest + Playwright (UI) + httpx (API)                       │
│  ↓ Calls                                                       │
│  Test Assertions & Business Logic                             │
└──────────────────────────────────────────────────────────────┘
                              ↓
                    Requests Test Data & State
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                   MCP Supporting Services                     │
│                                                                │
│  FastAPI MCP (seed_user, build_payload, reset_env)           │
│  Playwright MCP (LLM exploration, Gherkin generation)         │
└──────────────────────────────────────────────────────────────┘
```

**Key Insight**: MCP servers are NOT the test execution engine. They provide deterministic data and exploratory capabilities, but pytest remains the test runner.

### Benefits of MCP-Driven Test Automation

| Traditional Approach | MCP-Enhanced Approach |
|---------------------|----------------------|
| Hardcoded user credentials | Dynamic user seeding via `seed_user()` |
| Copy-pasted request payloads | Generated payloads via `build_payload()` |
| Manual environment cleanup | Automated reset via `reset_env()` |
| Human-only test authoring | LLM-assisted scenario generation |
| Brittle, maintenance-heavy tests | Adaptable, data-driven tests |

## Architecture Overview

This test automation framework includes **two FastAPI-based MCP servers**, each with distinct purposes and lifecycle requirements:

### 1. FastAPI MCP Server (Production/CI)

- **Purpose**: Deterministic test data management and environment state control
- **Runs In**: All environments (CI pipelines, local development, staging)
- **Lifecycle**: Started before test suite execution, terminated after completion
- **Key Tools**: `seed_user`, `build_payload`, `reset_env`, `query_state`

### 2. Playwright MCP Server (Development/Exploration)

- **Purpose**: LLM-controlled browser automation for test scenario discovery
- **Runs In**: Development environments by default; opt-in for CI if needed
- **Lifecycle**: Long-running during development sessions; typically not in CI
- **Key Tools**: `navigate`, `click`, `type`, `screenshot`, `get_page_structure`, `generate_gherkin`

### Communication Pattern: JSON-RPC over HTTP

Both MCP servers expose **JSON-RPC 2.0 endpoints** for tool invocation:

```http
POST /tools/{tool_name}
Content-Type: application/json
Authorization: Bearer <token>

{
  "jsonrpc": "2.0",
  "method": "tool_name",
  "params": {
    "param1": "value1",
    "param2": "value2"
  },
  "id": "request-123"
}
```

**Response Format:**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "data": "tool result"
  },
  "id": "request-123"
}
```

### Bearer Token Authentication

All MCP endpoints require **Bearer token authentication** for secure access:

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Tokens are configured via environment variables:
- `FASTAPI_MCP_TOKEN`: Authentication token for FastAPI MCP server
- `PLAYWRIGHT_MCP_TOKEN`: Authentication token for Playwright MCP server (if used)

### Integration with pytest Fixtures

MCP servers are accessed in tests through **pytest fixtures** that handle connection management, authentication, and error handling:

```python
# tests/conftest.py
@pytest.fixture(scope='session')
def mcp_client():
    """Provides authenticated MCP client for test suite."""
    return MCPClient(
        base_url=os.getenv('FASTAPI_MCP_URL'),
        token=os.getenv('FASTAPI_MCP_TOKEN')
    )

# Usage in tests
def test_login_with_seeded_user(mcp_client, login_page):
    user = mcp_client.seed_user(role='admin')
    login_page.login(user.email, user.password)
    assert login_page.is_logged_in()
```

## FastAPI MCP Server (Production/CI)

### Purpose

The FastAPI MCP server provides **deterministic test data management** and **environment state control**, ensuring tests start from known-good conditions. This server runs in all environments (CI, local development, staging) and is a foundational component of the test suite.

### Location

```
mcp_servers/fastapi_mcp/
├── main.py              # FastAPI application entry point
├── config.py            # Environment-based configuration
├── models.py            # Pydantic request/response models
├── routers/
│   ├── tools.py         # MCP tool endpoint implementations
│   └── health.py        # Health check endpoint
├── services/
│   ├── user_service.py     # User seed/management
│   ├── payload_service.py  # Payload building service
│   └── state_service.py    # Environment state management
├── database/
│   ├── connection.py    # Database connection management
│   └── models.py        # Database models (optional)
└── auth/
    └── bearer.py        # Bearer token authentication
```

### Tools and Endpoints

#### 1. seed_user Tool

**Endpoint**: `POST /tools/seed_user`

**Purpose**: Creates test users with deterministic, predictable attributes. Ensures all tests use dynamically generated users rather than hardcoded credentials.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `role` | string | Yes | User role (e.g., "admin", "editor", "customer") |
| `email` | string | No | Email address (auto-generated if not provided) |
| `custom_attributes` | dict | No | Additional user properties (name, phone, etc.) |

**Returns**: User object with `id`, `email`, `password`, `role`, and any custom attributes.

**Example Usage**:

```python
# Seed a basic admin user
admin_user = mcp_client.seed_user(role='admin')
# Returns: {"id": "user-123", "email": "admin-xyz@test.com", "password": "SecurePass123!", "role": "admin"}

# Seed a customer with specific email
customer = mcp_client.seed_user(
    role='customer',
    email='john.doe@example.com',
    custom_attributes={
        'first_name': 'John',
        'last_name': 'Doe',
        'phone': '+1-555-0123'
    }
)
```

**Implementation Details**:

- Generates secure random passwords meeting application requirements
- Creates users via target application's API or directly in database
- Stores user metadata for later cleanup during `reset_env()`
- Ensures email uniqueness by appending random suffixes if needed

**When to Use**:

- ✅ All tests requiring authenticated users
- ✅ Role-based authorization testing
- ✅ User management feature tests
- ❌ Never hardcode credentials in test files

---

#### 2. build_payload Tool

**Endpoint**: `POST /tools/build_payload`

**Purpose**: Generates valid API request payloads from predefined templates. Eliminates hardcoded JSON in test files and ensures payloads match current API schema requirements.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `template_name` | string | Yes | Name of payload template (e.g., "create_user", "update_profile") |
| `params` | dict | No | Template variable substitutions and overrides |

**Returns**: Complete request body (JSON dict) ready for API client use.

**Example Usage**:

```python
# Generate payload for creating a new user
create_user_payload = mcp_client.build_payload(
    template_name='create_user',
    params={'role': 'editor', 'department': 'Marketing'}
)
# Returns: {"email": "editor-abc@test.com", "role": "editor", "department": "Marketing", "status": "active"}

# Generate payload for updating user profile
update_payload = mcp_client.build_payload(
    template_name='update_profile',
    params={'first_name': 'Jane', 'last_name': 'Smith'}
)
```

**Template Definition Example** (in payload_service.py):

```python
PAYLOAD_TEMPLATES = {
    'create_user': {
        'email': lambda params: params.get('email', f"user-{uuid.uuid4().hex[:8]}@test.com"),
        'role': lambda params: params.get('role', 'user'),
        'status': lambda params: params.get('status', 'active'),
        'created_at': lambda params: datetime.utcnow().isoformat()
    },
    'create_post': {
        'title': lambda params: params.get('title', f"Test Post {uuid.uuid4().hex[:6]}"),
        'content': lambda params: params.get('content', 'This is test content.'),
        'author_id': lambda params: params['author_id'],  # Required parameter
        'published': lambda params: params.get('published', False)
    }
}
```

**When to Use**:

- ✅ All API POST/PUT/PATCH requests in tests
- ✅ Complex nested payloads with multiple fields
- ✅ Payloads requiring timestamps, UUIDs, or computed values
- ❌ Never copy-paste JSON payloads into test files

---

#### 3. reset_env Tool

**Endpoint**: `POST /tools/reset_env`

**Purpose**: Clears all test data and restores the environment to a known-good baseline state. Essential for test isolation and deterministic execution.

**Parameters**: None (operates on entire test environment)

**Returns**: Status object with cleanup summary (users deleted, data cleared, etc.)

**Example Usage**:

```python
# Typically called in session-scoped fixture
@pytest.fixture(scope='session', autouse=True)
def reset_test_environment(mcp_client):
    """Reset environment before test suite begins."""
    result = mcp_client.reset_env()
    print(f"Environment reset: {result}")
    yield
    # Optionally reset again after tests
    mcp_client.reset_env()

# Returns: {"status": "success", "users_deleted": 15, "data_cleared": ["posts", "comments"]}
```

**What Gets Reset**:

1. **Test Users**: All users created via `seed_user()` are deleted
2. **Application Data**: Test-specific records (posts, comments, orders, etc.)
3. **Session State**: Cached tokens, sessions, temporary files
4. **Database State**: Rollback to baseline schema or seed data
5. **File Uploads**: Clean temporary upload directories

**Implementation Strategies**:

- **Database Snapshots**: Restore from known-good database backup
- **Soft Deletes**: Mark test data with `is_test_data=true` flag, delete by query
- **API Cleanup**: Call application's DELETE endpoints for each test resource
- **Transaction Rollback**: Use database transactions and rollback (for local dev only)

**When to Use**:

- ✅ Always call before test suite execution (session-scoped fixture)
- ✅ Between test classes if tests create persistent data
- ✅ After exploratory testing sessions
- ❌ Never skip reset_env() in CI pipelines

---

#### 4. query_state Tool

**Endpoint**: `POST /tools/query_state`

**Purpose**: Retrieves current environment state for validation and debugging. Useful for verifying expected conditions before or after test execution.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_type` | string | Yes | Type of entity to query ("users", "posts", "orders", etc.) |
| `filters` | dict | No | Query filters (field: value pairs) |

**Returns**: List of entities matching the query filters.

**Example Usage**:

```python
# Query all admin users
admins = mcp_client.query_state(
    entity_type='users',
    filters={'role': 'admin'}
)
assert len(admins) >= 1, "At least one admin should exist"

# Query posts by specific author
posts = mcp_client.query_state(
    entity_type='posts',
    filters={'author_id': user.id, 'published': True}
)
assert len(posts) == 3, "User should have exactly 3 published posts"

# Check environment is clean before tests
all_users = mcp_client.query_state(entity_type='users')
assert len(all_users) == 0, "Environment should be clean before tests"
```

**When to Use**:

- ✅ Verifying environment state in setup fixtures
- ✅ Debugging test failures (inspect actual vs expected state)
- ✅ Assertions about data relationships
- ❌ Not a replacement for application API tests (use dedicated API clients)

---

### Server Structure and Components

#### main.py - Application Entry Point

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcp_servers.fastapi_mcp.routers import tools, health
from mcp_servers.fastapi_mcp.config import settings

app = FastAPI(
    title="FastAPI MCP Server",
    description="Model Context Protocol server for deterministic test data management",
    version="1.0.0"
)

# CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(tools.router, prefix="/tools", tags=["tools"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### config.py - Environment Configuration

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    
    # Authentication
    MCP_TOKEN: str
    TOKEN_ALGORITHM: str = "HS256"
    
    # Target application
    TARGET_APP_API_URL: str
    TARGET_APP_ADMIN_TOKEN: str = ""
    
    # Database (optional)
    DATABASE_URL: str = ""
    
    # CORS
    ALLOWED_ORIGINS: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

#### routers/tools.py - MCP Tool Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException
from mcp_servers.fastapi_mcp.auth.bearer import verify_token
from mcp_servers.fastapi_mcp.services import user_service, payload_service, state_service
from mcp_servers.fastapi_mcp.models import (
    SeedUserRequest, SeedUserResponse,
    BuildPayloadRequest, BuildPayloadResponse,
    QueryStateRequest, QueryStateResponse
)

router = APIRouter(dependencies=[Depends(verify_token)])

@router.post("/seed_user", response_model=SeedUserResponse)
async def seed_user(request: SeedUserRequest):
    """Create a test user with deterministic attributes."""
    user = await user_service.create_test_user(
        role=request.role,
        email=request.email,
        custom_attributes=request.custom_attributes
    )
    return SeedUserResponse(**user)

@router.post("/build_payload", response_model=BuildPayloadResponse)
async def build_payload(request: BuildPayloadRequest):
    """Generate valid API request payload from template."""
    payload = payload_service.build_from_template(
        template_name=request.template_name,
        params=request.params
    )
    return BuildPayloadResponse(payload=payload)

@router.post("/reset_env")
async def reset_env():
    """Clear all test data and restore baseline state."""
    result = await state_service.reset_environment()
    return result

@router.post("/query_state", response_model=QueryStateResponse)
async def query_state(request: QueryStateRequest):
    """Query current environment state."""
    entities = await state_service.query_entities(
        entity_type=request.entity_type,
        filters=request.filters
    )
    return QueryStateResponse(entities=entities)
```

---

### Starting FastAPI MCP Server

#### Local Development

**Using uvicorn directly:**

```bash
cd mcp_servers/fastapi_mcp
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Using the provided startup script:**

```bash
# Linux/Mac
bash mcp_servers/scripts/start_fastapi_mcp.sh

# Windows
mcp_servers\scripts\start_fastapi_mcp.bat
```

**Expected Output:**

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Health Check:**

```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "version": "1.0.0"}
```

#### CI/CD with Docker

**GitHub Actions Example:**

```yaml
# .github/workflows/test.yml
name: Run Tests with MCP Server

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      fastapi-mcp:
        image: python:3.11
        env:
          MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
          TARGET_APP_API_URL: http://localhost:3000
        ports:
          - 8000:8000
        options: >-
          --health-cmd "curl -f http://localhost:8000/health || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        # Startup command
        run: |
          pip install -r mcp_servers/fastapi_mcp/requirements.txt
          uvicorn mcp_servers.fastapi_mcp.main:app --host 0.0.0.0 --port 8000
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Wait for MCP Server
        run: |
          timeout 30 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
      
      - name: Run Tests
        env:
          FASTAPI_MCP_URL: http://localhost:8000
          FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
        run: pytest -v
```

**Docker Compose Example (Local Development):**

```yaml
# docker-compose.yml
version: '3.8'

services:
  fastapi-mcp:
    build:
      context: ./mcp_servers/fastapi_mcp
    ports:
      - "8000:8000"
    environment:
      - MCP_TOKEN=${MCP_TOKEN}
      - TARGET_APP_API_URL=http://app:3000
    depends_on:
      - app
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    # Your application under test
    image: myapp:latest
    ports:
      - "3000:3000"
```

**Start with:**

```bash
docker-compose up -d
```

---

### Configuration

#### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FASTAPI_MCP_URL` | Yes | - | MCP server URL (e.g., `http://localhost:8000`) |
| `FASTAPI_MCP_TOKEN` | Yes | - | Bearer token for authentication |
| `TARGET_APP_API_URL` | Yes | - | Application under test API base URL |
| `TARGET_APP_ADMIN_TOKEN` | No | - | Admin token for application API calls |
| `DATABASE_URL` | No | - | Database connection string (if using DB state management) |
| `SERVER_HOST` | No | `0.0.0.0` | MCP server bind address |
| `SERVER_PORT` | No | `8000` | MCP server port |

#### Configuration File Example

**.env file:**

```env
# FastAPI MCP Server Configuration
FASTAPI_MCP_URL=http://localhost:8000
FASTAPI_MCP_TOKEN=your-secure-token-here

# Target Application
TARGET_APP_API_URL=http://localhost:3000
TARGET_APP_ADMIN_TOKEN=admin-api-token

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost:5432/testdb

# CORS (optional)
ALLOWED_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
```

---

## Playwright MCP Server (Development/Exploration)

### Purpose

The Playwright MCP server enables **LLM-controlled browser automation** for exploratory testing and automated test scenario discovery. This server is designed for **development environments** and provides tools for AI agents to interact with web applications, capture observations, and generate human-readable Gherkin scenarios.

**Key Use Case**: An LLM agent explores a web application by navigating, clicking, and interacting with elements. The exploration session is then converted into a formal Gherkin `.feature` file that humans can review and commit to the test suite.

### Location

```
mcp_servers/playwright_mcp/
├── main.py                 # FastAPI application with WebSocket support
├── config.py               # Server configuration
├── models.py               # Tool request/response Pydantic models
├── tools/
│   ├── navigation.py       # Navigate, back, forward, reload
│   ├── interaction.py      # Click, type, select, check
│   ├── capture.py          # Screenshot, video, trace
│   └── analysis.py         # get_page_structure, extract_text
├── session/
│   └── manager.py          # Multi-session browser context management
└── gherkin/
    └── generator.py        # Exploration to Gherkin converter
```

### Tools and Endpoints

#### 1. navigate Tool

**Endpoint**: `POST /tools/navigate`

**Purpose**: Navigate the browser to a specific URL.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | Yes | Target URL (absolute or relative to base) |
| `session_id` | string | Yes | Browser session identifier |

**Returns**: Current page title and URL after navigation.

**Example Usage**:

```python
result = playwright_mcp.navigate(
    url="https://example.com/login",
    session_id="session-123"
)
# Returns: {"title": "Login - Example App", "url": "https://example.com/login"}
```

---

#### 2. click Tool

**Endpoint**: `POST /tools/click`

**Purpose**: Click an element identified by a stable selector (ARIA role, label, test ID).

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `selector` | string | Yes | Element selector (prefer roles, labels, test IDs) |
| `session_id` | string | Yes | Browser session identifier |

**Supported Selector Strategies**:

- ARIA roles: `role=button[name="Submit"]`
- Test IDs: `data-testid=login-button`
- Labels: `text=Sign In`
- Accessible names: `getByLabel("Email address")`

**Example Usage**:

```python
# Click using ARIA role
playwright_mcp.click(
    selector='role=button[name="Login"]',
    session_id="session-123"
)

# Click using test ID
playwright_mcp.click(
    selector='data-testid=submit-form',
    session_id="session-123"
)
```

---

#### 3. type Tool

**Endpoint**: `POST /tools/type`

**Purpose**: Enter text into an input field.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `selector` | string | Yes | Input element selector |
| `text` | string | Yes | Text to enter |
| `session_id` | string | Yes | Browser session identifier |

**Example Usage**:

```python
# Type into email field
playwright_mcp.type(
    selector='getByLabel("Email")',
    text='user@example.com',
    session_id="session-123"
)

# Type into password field
playwright_mcp.type(
    selector='input[type="password"]',
    text='SecurePass123!',
    session_id="session-123"
)
```

---

#### 4. screenshot Tool

**Endpoint**: `POST /tools/screenshot`

**Purpose**: Capture a screenshot of the current page state.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Browser session identifier |
| `full_page` | boolean | No | Capture full scrollable page (default: `false`) |

**Returns**: Base64-encoded PNG image data.

**Example Usage**:

```python
screenshot_data = playwright_mcp.screenshot(
    session_id="session-123",
    full_page=True
)

# Save screenshot to file
import base64
with open("exploration_screenshot.png", "wb") as f:
    f.write(base64.b64decode(screenshot_data))
```

---

#### 5. get_page_structure Tool

**Endpoint**: `POST /tools/get_page_structure`

**Purpose**: Extract the accessibility tree structure of the current page for LLM analysis. This enables the LLM to "understand" what elements are present without visual interpretation.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Browser session identifier |

**Returns**: Structured representation of page elements with roles, labels, and relationships.

**Example Response**:

```json
{
  "page_structure": {
    "title": "Login - Example App",
    "url": "https://example.com/login",
    "elements": [
      {
        "role": "heading",
        "level": 1,
        "text": "Welcome Back",
        "selector": "h1"
      },
      {
        "role": "textbox",
        "label": "Email address",
        "selector": "input[name='email']",
        "required": true
      },
      {
        "role": "textbox",
        "label": "Password",
        "selector": "input[type='password']",
        "required": true
      },
      {
        "role": "button",
        "text": "Sign In",
        "selector": "button[type='submit']"
      },
      {
        "role": "link",
        "text": "Forgot password?",
        "href": "/reset-password"
      }
    ]
  }
}
```

**Usage by LLM**:

The LLM uses this structured data to decide which elements to interact with:

```python
# LLM reasoning process
page = playwright_mcp.get_page_structure(session_id="session-123")

# LLM identifies email input
email_input = [el for el in page['elements'] if el['label'] == 'Email address'][0]

# LLM types into email field
playwright_mcp.type(
    selector=email_input['selector'],
    text='test@example.com',
    session_id="session-123"
)
```

---

#### 6. generate_gherkin Endpoint

**Endpoint**: `POST /generate_gherkin`

**Purpose**: Convert an exploration session into a human-readable Gherkin `.feature` file.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Browser session to convert |
| `feature_name` | string | No | Feature name (auto-generated if not provided) |
| `tags` | list[string] | No | Gherkin tags (e.g., `["@smoke", "@login"]`) |

**Returns**: Generated Gherkin scenario content.

**Example Usage**:

```python
# After LLM exploration session
gherkin_content = playwright_mcp.generate_gherkin(
    session_id="session-123",
    feature_name="User Authentication",
    tags=["@smoke", "@login"]
)

# Write to feature file
with open("tests/features/generated_login.feature", "w") as f:
    f.write(gherkin_content)
```

**Generated Output Example**:

```gherkin
@smoke @login
Feature: User Authentication
  As a registered user
  I want to log into the application
  So that I can access my account

  Scenario: Successful login with valid credentials
    Given the user is on the login page
    When the user enters "test@example.com" in the email field
    And the user enters "SecurePass123!" in the password field
    And the user clicks the "Sign In" button
    Then the user should be redirected to the dashboard
    And the user should see a welcome message

  Scenario: Login fails with invalid password
    Given the user is on the login page
    When the user enters "test@example.com" in the email field
    And the user enters "wrongpassword" in the password field
    And the user clicks the "Sign In" button
    Then the user should see an error message "Invalid credentials"
    And the user should remain on the login page
```

**Gherkin Generation Algorithm**:

1. **Action Sequence Analysis**: Review all navigation, click, type actions in session
2. **Step Inference**: Convert actions to high-level Gherkin steps
3. **Assertion Detection**: Identify implicit assertions (e.g., navigation implies "Then" step)
4. **Scenario Grouping**: Cluster related actions into logical scenarios
5. **Human-Readable Phrasing**: Translate technical actions into business language

---

### Server Structure and Components

#### main.py - Application Entry Point

```python
from fastapi import FastAPI, WebSocket
from mcp_servers.playwright_mcp.routers import tools, gherkin
from mcp_servers.playwright_mcp.session.manager import SessionManager

app = FastAPI(
    title="Playwright MCP Server",
    description="LLM-controlled browser automation for test scenario discovery",
    version="1.0.0"
)

# Session manager for browser contexts
session_manager = SessionManager()

# Include routers
app.include_router(tools.router, prefix="/tools", tags=["tools"])
app.include_router(gherkin.router, prefix="/gherkin", tags=["gherkin"])

@app.on_event("startup")
async def startup_event():
    """Initialize Playwright browsers on startup."""
    await session_manager.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Close all browser sessions on shutdown."""
    await session_manager.close_all()
```

#### session/manager.py - Multi-Session Browser Management

```python
from playwright.async_api import async_playwright, Browser, BrowserContext
import asyncio

class SessionManager:
    def __init__(self):
        self.playwright = None
        self.browser: Browser = None
        self.contexts: dict[str, BrowserContext] = {}
    
    async def initialize(self):
        """Start Playwright and launch browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
    
    async def create_session(self, session_id: str) -> BrowserContext:
        """Create a new browser context for a session."""
        context = await self.browser.new_context()
        self.contexts[session_id] = context
        return context
    
    async def get_session(self, session_id: str) -> BrowserContext:
        """Get existing session or create new one."""
        if session_id not in self.contexts:
            return await self.create_session(session_id)
        return self.contexts[session_id]
    
    async def close_session(self, session_id: str):
        """Close and remove a browser context."""
        if session_id in self.contexts:
            await self.contexts[session_id].close()
            del self.contexts[session_id]
    
    async def close_all(self):
        """Close all sessions and browser."""
        for context in self.contexts.values():
            await context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
```

#### gherkin/generator.py - Exploration to Gherkin Converter

```python
class GherkinGenerator:
    def __init__(self):
        self.action_log = []
    
    def log_action(self, session_id: str, action_type: str, details: dict):
        """Record an action in the exploration session."""
        self.action_log.append({
            'session_id': session_id,
            'action_type': action_type,
            'details': details,
            'timestamp': datetime.utcnow()
        })
    
    def generate_feature(self, session_id: str, feature_name: str, tags: list[str] = None) -> str:
        """Convert action log to Gherkin feature."""
        actions = [a for a in self.action_log if a['session_id'] == session_id]
        
        # Generate feature header
        feature_content = []
        if tags:
            feature_content.append(" ".join(f"@{tag}" for tag in tags))
        
        feature_content.append(f"Feature: {feature_name}")
        feature_content.append("  # Auto-generated from exploration session\n")
        
        # Generate scenarios from action clusters
        scenarios = self._cluster_actions_into_scenarios(actions)
        for scenario in scenarios:
            feature_content.append(self._format_scenario(scenario))
        
        return "\n".join(feature_content)
    
    def _cluster_actions_into_scenarios(self, actions: list) -> list:
        """Group related actions into logical scenarios."""
        # Implementation: Analyze action sequences, detect logical breaks
        # (e.g., navigation to new page = new scenario)
        pass
    
    def _format_scenario(self, scenario: dict) -> str:
        """Format a scenario with Given/When/Then steps."""
        # Implementation: Convert actions to Gherkin steps
        pass
```

---

### Starting Playwright MCP Server

#### Local Development Only

**Using uvicorn:**

```bash
cd mcp_servers/playwright_mcp
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**Using the provided startup script:**

```bash
# Linux/Mac
bash mcp_servers/scripts/start_playwright_mcp.sh

# Windows
mcp_servers\scripts\start_playwright_mcp.bat
```

**Expected Output:**

```
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Initializing Playwright browsers...
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

---

### Configuration

#### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLAYWRIGHT_MCP_URL` | Yes | - | MCP server URL (e.g., `http://localhost:8001`) |
| `PLAYWRIGHT_MCP_TOKEN` | No | - | Authentication token (optional for local dev) |
| `BROWSER_TYPE` | No | `chromium` | Browser type: `chromium`, `firefox`, or `webkit` |
| `HEADLESS` | No | `true` | Run browser in headless mode |
| `BASE_URL` | No | - | Default base URL for relative navigation |

**.env file:**

```env
# Playwright MCP Server Configuration (Development Only)
PLAYWRIGHT_MCP_URL=http://localhost:8001
BROWSER_TYPE=chromium
HEADLESS=false  # Show browser for visual exploration
BASE_URL=http://localhost:3000
```

---

## MCP Client Integration

### Creating MCP Client Fixture

The MCP client should be available as a pytest fixture for seamless integration in tests.

**Implementation: tests/helpers/mcp_client.py**

```python
import httpx
import os
from typing import Any, Dict, Optional

class MCPClient:
    """Client for interacting with FastAPI MCP server."""
    
    def __init__(self, base_url: str, token: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {token}"}
        )
    
    def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Make JSON-RPC call to MCP tool endpoint."""
        response = self.client.post(
            f"{self.base_url}/tools/{tool_name}",
            json={
                "jsonrpc": "2.0",
                "method": tool_name,
                "params": params,
                "id": f"req-{id(params)}"
            }
        )
        response.raise_for_status()
        result = response.json()
        
        if "error" in result:
            raise MCPError(result["error"])
        
        return result.get("result", result)
    
    def seed_user(self, role: str, email: Optional[str] = None, 
                  custom_attributes: Optional[Dict] = None) -> Dict:
        """Create a test user via MCP."""
        params = {"role": role}
        if email:
            params["email"] = email
        if custom_attributes:
            params["custom_attributes"] = custom_attributes
        
        return self._call_tool("seed_user", params)
    
    def build_payload(self, template_name: str, params: Optional[Dict] = None) -> Dict:
        """Generate API request payload from template."""
        return self._call_tool("build_payload", {
            "template_name": template_name,
            "params": params or {}
        })
    
    def reset_env(self) -> Dict:
        """Reset test environment to baseline state."""
        return self._call_tool("reset_env", {})
    
    def query_state(self, entity_type: str, filters: Optional[Dict] = None) -> list:
        """Query current environment state."""
        return self._call_tool("query_state", {
            "entity_type": entity_type,
            "filters": filters or {}
        })
    
    def close(self):
        """Close HTTP client."""
        self.client.close()

class MCPError(Exception):
    """Exception raised for MCP tool execution errors."""
    pass
```

**Fixture Definition: tests/conftest.py**

```python
import pytest
import os
from tests.helpers.mcp_client import MCPClient

@pytest.fixture(scope='session')
def mcp_client():
    """Provides authenticated MCP client for test suite."""
    client = MCPClient(
        base_url=os.getenv('FASTAPI_MCP_URL', 'http://localhost:8000'),
        token=os.getenv('FASTAPI_MCP_TOKEN', 'dev-token')
    )
    yield client
    client.close()

@pytest.fixture(scope='session', autouse=True)
def reset_environment(mcp_client):
    """Reset test environment before test suite execution."""
    print("\n🔄 Resetting test environment...")
    result = mcp_client.reset_env()
    print(f"✅ Environment reset: {result}")
    yield
    # Optionally reset after tests
    print("\n🧹 Cleaning up test environment...")
    mcp_client.reset_env()
```

---

### Using MCP Client in Tests

#### Example 1: Seed User for Authentication Test

```python
def test_login_with_seeded_admin(mcp_client, login_page):
    """Test admin login using MCP-seeded user."""
    # Seed admin user via MCP
    admin_user = mcp_client.seed_user(role='admin', email='admin@test.local')
    
    # Use seeded credentials
    login_page.navigate()
    login_page.fill_email(admin_user['email'])
    login_page.fill_password(admin_user['password'])
    login_page.submit()
    
    # Verify successful login
    assert login_page.is_logged_in()
    assert login_page.get_user_role() == 'admin'
```

#### Example 2: Build Payload for API Test

```python
def test_create_user_via_api(mcp_client, users_api_client):
    """Test user creation API with MCP-generated payload."""
    # Generate valid payload via MCP
    payload = mcp_client.build_payload(
        template_name='create_user',
        params={'role': 'editor', 'department': 'Engineering'}
    )
    
    # Make API request
    response = users_api_client.create_user(json=payload)
    
    # Verify response
    assert response.status_code == 201
    assert response.json()['role'] == 'editor'
    assert response.json()['department'] == 'Engineering'
```

#### Example 3: Query State for Validation

```python
def test_user_deletion_cascades(mcp_client, users_api_client):
    """Test that deleting a user also deletes their posts."""
    # Seed user and create posts
    user = mcp_client.seed_user(role='author')
    # ... create posts via API ...
    
    # Delete user
    users_api_client.delete_user(user['id'])
    
    # Query state to verify cascade
    posts = mcp_client.query_state(
        entity_type='posts',
        filters={'author_id': user['id']}
    )
    
    assert len(posts) == 0, "Posts should be deleted when user is deleted"
```

---

## Authentication and Security

### Bearer Token Authentication

Both MCP servers use **Bearer token authentication** to secure endpoints and prevent unauthorized access.

#### Token Generation

Tokens should be:
- **Long and random**: At least 32 characters
- **Stored securely**: In environment variables or secret management systems
- **Rotated regularly**: Change tokens periodically (e.g., monthly)

**Generate Token (Linux/Mac):**

```bash
openssl rand -hex 32
# Output: a1b2c3d4e5f6... (64-character hex string)
```

**Generate Token (Python):**

```python
import secrets
token = secrets.token_hex(32)
print(token)
```

#### Token Configuration

**For Local Development (.env file):**

```env
FASTAPI_MCP_TOKEN=dev-token-replace-in-production
PLAYWRIGHT_MCP_TOKEN=dev-token-playwright
```

**For CI/CD (GitHub Secrets):**

1. Go to repository Settings → Secrets and variables → Actions
2. Add secrets:
   - `MCP_TOKEN`: Production token for FastAPI MCP server
   - `PLAYWRIGHT_MCP_TOKEN`: Token for Playwright MCP (if used in CI)

3. Reference in workflow:

```yaml
env:
  FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
```

#### Token Validation Implementation

**mcp_servers/fastapi_mcp/auth/bearer.py:**

```python
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from mcp_servers.fastapi_mcp.config import settings

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify Bearer token matches configured MCP_TOKEN."""
    if credentials.credentials != settings.MCP_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    return credentials.credentials
```

### Security Best Practices

1. **Never commit tokens to git**: Use `.env` files and add to `.gitignore`
2. **Use HTTPS in production**: Never send tokens over unencrypted HTTP
3. **Implement rate limiting**: Prevent brute-force token guessing
4. **Log authentication failures**: Monitor for suspicious activity
5. **Rotate tokens regularly**: Change tokens every 30-90 days
6. **Scope tokens appropriately**: Use different tokens for different environments

---

## Error Handling

### MCP Server Error Responses

MCP servers return structured error responses following JSON-RPC 2.0 specification:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "User creation failed",
    "data": {
      "detail": "Email address already exists",
      "email": "duplicate@example.com"
    }
  },
  "id": "request-123"
}
```

### Error Codes

| Code | Meaning | Example |
|------|---------|---------|
| `-32700` | Parse error | Invalid JSON in request |
| `-32600` | Invalid request | Missing required parameters |
| `-32601` | Method not found | Unknown tool name |
| `-32602` | Invalid params | Parameter type mismatch |
| `-32603` | Internal error | Server-side exception |
| `-32000` | Application error | Business logic error (e.g., user already exists) |

### Client-Side Error Handling

**Implement Retry Logic for Transient Failures:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class MCPClient:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """Make JSON-RPC call with automatic retry on transient errors."""
        try:
            response = self.client.post(
                f"{self.base_url}/tools/{tool_name}",
                json={"jsonrpc": "2.0", "method": tool_name, "params": params, "id": str(uuid.uuid4())}
            )
            response.raise_for_status()
            return response.json().get("result")
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                # Retry on server errors
                raise
            else:
                # Don't retry on client errors (4xx)
                raise MCPError(f"MCP tool '{tool_name}' failed: {e}")
        
        except httpx.RequestError as e:
            # Retry on network errors
            raise
```

### Timeout Configuration

**Set Appropriate Timeouts:**

```python
mcp_client = MCPClient(
    base_url="http://localhost:8000",
    token="token",
    timeout=30  # 30 seconds for most operations
)

# For long-running operations (e.g., reset_env)
mcp_client.reset_env()  # Uses default timeout

# Override timeout for specific calls
mcp_client.client.timeout = httpx.Timeout(60.0)  # 60 seconds
```

### Logging for Debugging

**Enable Debug Logging:**

```python
import logging

# Configure MCP client logging
logging.basicConfig(level=logging.DEBUG)
mcp_logger = logging.getLogger("mcp_client")

class MCPClient:
    def _call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        mcp_logger.debug(f"Calling MCP tool '{tool_name}' with params: {params}")
        
        try:
            response = self.client.post(...)
            mcp_logger.debug(f"MCP response: {response.json()}")
            return response.json().get("result")
        
        except Exception as e:
            mcp_logger.error(f"MCP tool '{tool_name}' failed: {e}")
            raise
```

---

## Testing MCP Servers

### Unit Tests for Tool Implementations

**Example: Test seed_user Tool Logic**

```python
# mcp_servers/fastapi_mcp/tests/test_user_service.py
import pytest
from mcp_servers.fastapi_mcp.services import user_service

@pytest.mark.asyncio
async def test_create_test_user_with_defaults():
    """Test user creation with default attributes."""
    user = await user_service.create_test_user(role='customer')
    
    assert user['role'] == 'customer'
    assert '@test.com' in user['email']  # Default email domain
    assert len(user['password']) >= 12   # Secure password generated
    assert 'id' in user

@pytest.mark.asyncio
async def test_create_test_user_with_custom_email():
    """Test user creation with specific email."""
    user = await user_service.create_test_user(
        role='admin',
        email='custom@example.com'
    )
    
    assert user['email'] == 'custom@example.com'
    assert user['role'] == 'admin'
```

### Integration Tests with Real Databases

**Example: Test reset_env with Database**

```python
# mcp_servers/fastapi_mcp/tests/test_state_service.py
import pytest
from mcp_servers.fastapi_mcp.services import state_service, user_service

@pytest.mark.asyncio
async def test_reset_env_clears_all_users(test_database):
    """Test that reset_env deletes all test users."""
    # Create multiple test users
    await user_service.create_test_user(role='user')
    await user_service.create_test_user(role='admin')
    await user_service.create_test_user(role='editor')
    
    # Verify users exist
    users_before = await state_service.query_entities('users', {})
    assert len(users_before) == 3
    
    # Reset environment
    result = await state_service.reset_environment()
    
    # Verify users are deleted
    users_after = await state_service.query_entities('users', {})
    assert len(users_after) == 0
    assert result['users_deleted'] == 3
```

### Mock Fixtures for MCP Client in Unit Tests

**Example: Mock MCP Client for Isolated Test**

```python
# tests/conftest.py
@pytest.fixture
def mock_mcp_client(mocker):
    """Mock MCP client for unit tests without real server."""
    mock_client = mocker.Mock(spec=MCPClient)
    
    # Mock seed_user to return predictable user
    mock_client.seed_user.return_value = {
        'id': 'user-123',
        'email': 'test@example.com',
        'password': 'TestPass123!',
        'role': 'customer'
    }
    
    # Mock build_payload to return template
    mock_client.build_payload.return_value = {
        'email': 'generated@test.com',
        'role': 'user',
        'status': 'active'
    }
    
    return mock_client

# Usage in test
def test_with_mocked_mcp(mock_mcp_client, login_page):
    """Test login using mocked MCP client."""
    user = mock_mcp_client.seed_user(role='admin')
    login_page.login(user['email'], user['password'])
    assert login_page.is_logged_in()
```

### Health Check Endpoint

**Implement Health Check for CI Readiness:**

```python
# mcp_servers/fastapi_mcp/routers/health.py
from fastapi import APIRouter
from mcp_servers.fastapi_mcp.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring and CI."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }
```

**Health Check in CI:**

```yaml
# Wait for MCP server to be ready
- name: Wait for MCP Server
  run: |
    timeout 30 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
    echo "MCP server is ready"
```

---

## Best Practices

### 1. Always Reset Environment Before Test Suites

**Why**: Ensures tests start from a known-good state, preventing flaky failures due to leftover data.

```python
# tests/conftest.py
@pytest.fixture(scope='session', autouse=True)
def reset_test_environment(mcp_client):
    """Automatically reset environment before test suite."""
    mcp_client.reset_env()
    yield
```

### 2. Use seed_user for All Test User Creation

**Why**: Eliminates hardcoded credentials and ensures users have valid attributes.

```python
# ❌ Bad: Hardcoded credentials
def test_login():
    login_page.login('admin@example.com', 'password123')

# ✅ Good: MCP-seeded user
def test_login(mcp_client, login_page):
    user = mcp_client.seed_user(role='admin')
    login_page.login(user['email'], user['password'])
```

### 3. Never Hardcode Test Data in Test Files

**Why**: Test data should be dynamic and managed by MCP server, not embedded in code.

```python
# ❌ Bad: Hardcoded API payload
def test_create_user(api_client):
    payload = {"email": "user@test.com", "role": "user", "status": "active"}
    response = api_client.post('/users', json=payload)

# ✅ Good: MCP-generated payload
def test_create_user(mcp_client, api_client):
    payload = mcp_client.build_payload('create_user', {'role': 'user'})
    response = api_client.post('/users', json=payload)
```

### 4. Keep MCP Server Logic Simple

**Why**: MCP servers provide data and state management, not complex business rules. Business logic belongs in tests.

```python
# ❌ Bad: Complex business logic in MCP server
def create_test_user_with_posts(role, num_posts):
    user = create_user(role)
    for i in range(num_posts):
        create_post(user_id=user['id'], title=f"Post {i}")
    return user

# ✅ Good: Simple data provisioning in MCP, logic in test
def test_user_with_multiple_posts(mcp_client, posts_api):
    user = mcp_client.seed_user(role='author')
    for i in range(3):
        payload = mcp_client.build_payload('create_post', {'author_id': user['id']})
        posts_api.create(json=payload)
```

### 5. MCP Servers Provide Data, Not Test Logic

**Why**: Separation of concerns—tests verify behavior, MCP servers supply inputs.

**MCP Server Responsibilities:**
- Generate valid test data
- Reset environment state
- Provide baseline configurations

**Test Responsibilities:**
- Execute actions on application
- Verify expected outcomes
- Assert business logic correctness

### 6. Use Descriptive Tool Parameters

**Why**: Makes test intent clear and logs easier to understand.

```python
# ❌ Bad: Unclear parameters
user = mcp_client.seed_user('admin')

# ✅ Good: Explicit parameters
user = mcp_client.seed_user(
    role='admin',
    email='admin.tester@company.com',
    custom_attributes={'department': 'QA', 'region': 'US'}
)
```

### 7. Implement Proper Error Handling in Tests

**Why**: MCP server failures should provide actionable error messages.

```python
def test_with_error_handling(mcp_client, login_page):
    try:
        user = mcp_client.seed_user(role='admin')
    except MCPError as e:
        pytest.fail(f"Failed to seed user: {e}")
    
    login_page.login(user['email'], user['password'])
```

---

## Troubleshooting

### Server Not Starting

**Symptom**: `uvicorn` command fails or server doesn't respond.

**Possible Causes**:
1. **Port already in use**: Another process is using port 8000/8001
2. **Missing dependencies**: Required packages not installed
3. **Python version incompatibility**: Requires Python 3.9+

**Solutions**:

```bash
# Check if port is in use
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Kill process using port
kill -9 <PID>  # Linux/Mac

# Verify Python version
python --version  # Should be 3.9+

# Reinstall dependencies
pip install -r mcp_servers/fastapi_mcp/requirements.txt
```

### Authentication Failures

**Symptom**: `401 Unauthorized` errors when calling MCP tools.

**Possible Causes**:
1. **Missing token**: `FASTAPI_MCP_TOKEN` not set
2. **Incorrect token**: Token in request doesn't match server configuration
3. **Token not in header**: Authorization header malformed

**Solutions**:

```bash
# Verify token is set
echo $FASTAPI_MCP_TOKEN

# Test with curl
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/health

# Check token in pytest
# tests/conftest.py
import os
assert os.getenv('FASTAPI_MCP_TOKEN'), "MCP token not configured"
```

### Connection Errors

**Symptom**: `Connection refused` or `Timeout` errors.

**Possible Causes**:
1. **Server not running**: MCP server hasn't started yet
2. **Wrong URL**: `FASTAPI_MCP_URL` points to incorrect address
3. **Network issues**: Firewall or proxy blocking connection

**Solutions**:

```bash
# Verify server is running
curl http://localhost:8000/health

# Check environment variable
echo $FASTAPI_MCP_URL

# Test network connectivity
ping localhost
telnet localhost 8000
```

### Tool Execution Failures

**Symptom**: MCP tool returns error response.

**Possible Causes**:
1. **Invalid parameters**: Wrong parameter types or missing required fields
2. **Target application unreachable**: Application under test not running
3. **Database connection failure**: MCP server can't access database

**Solutions**:

```bash
# Check MCP server logs
# Look for error messages in uvicorn output

# Verify target application
curl http://localhost:3000/health  # Your app

# Test database connection
# Check DATABASE_URL environment variable

# Enable debug logging in MCP client
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Slow Tool Execution

**Symptom**: MCP tools take longer than expected.

**Possible Causes**:
1. **Database performance**: Slow queries or missing indexes
2. **Network latency**: MCP server and app on different networks
3. **Resource constraints**: Server under heavy load

**Solutions**:

```bash
# Monitor server resource usage
top  # Linux/Mac
# Look for high CPU or memory usage

# Check database query performance
# Enable query logging in database

# Increase timeout in client
mcp_client = MCPClient(base_url=..., token=..., timeout=60)
```

### Browser Launch Failures (Playwright MCP)

**Symptom**: Playwright MCP server fails to start browser.

**Possible Causes**:
1. **Browsers not installed**: Playwright browsers not downloaded
2. **Missing dependencies**: System libraries required for browsers
3. **Headless mode issues**: Display server not available

**Solutions**:

```bash
# Install Playwright browsers
python -m playwright install chromium

# Install system dependencies
python -m playwright install-deps

# Check browser launch
python -c "from playwright.sync_api import sync_playwright; sync_playwright().start().chromium.launch()"

# If headless mode fails, try headed mode
# Set HEADLESS=false in .env
```

---

## Environment-Specific Behavior

### Local Development

**MCP Server Configuration**:
- **FastAPI MCP**: Always running on `http://localhost:8000`
- **Playwright MCP**: Always running on `http://localhost:8001`
- **Authentication**: Relaxed (dev tokens acceptable)
- **Logging**: Verbose debug logging enabled
- **Browser**: Headed mode for visual exploration

**.env Configuration**:

```env
# Local Development
FASTAPI_MCP_URL=http://localhost:8000
FASTAPI_MCP_TOKEN=dev-token
PLAYWRIGHT_MCP_URL=http://localhost:8001
PLAYWRIGHT_MCP_TOKEN=dev-token

# Target Application (local)
TARGET_APP_API_URL=http://localhost:3000
BASE_URL=http://localhost:3000

# Browser Settings
HEADLESS=false  # Show browser
BROWSER_TYPE=chromium
```

**Startup Sequence**:

```bash
# Terminal 1: Start FastAPI MCP
cd mcp_servers/fastapi_mcp
uvicorn main:app --reload --port 8000

# Terminal 2: Start Playwright MCP
cd mcp_servers/playwright_mcp
uvicorn main:app --reload --port 8001

# Terminal 3: Start Application Under Test
cd my_app
npm run dev  # or python app.py, etc.

# Terminal 4: Run Tests
pytest -v
```

---

### CI/CD (GitHub Actions)

**MCP Server Configuration**:
- **FastAPI MCP**: Runs as GitHub Actions service container
- **Playwright MCP**: NOT running by default (opt-in for specific jobs)
- **Authentication**: Secure tokens from GitHub Secrets
- **Logging**: Error-level logging only
- **Browser**: Headless mode only

**GitHub Actions Workflow**:

```yaml
# .github/workflows/test.yml
name: Test Suite with MCP

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      # FastAPI MCP Server (always running)
      fastapi-mcp:
        image: python:3.11
        env:
          MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
          TARGET_APP_API_URL: http://localhost:3000
          DATABASE_URL: ${{ secrets.TEST_DB_URL }}
        ports:
          - 8000:8000
        options: >-
          --health-cmd "curl -f http://localhost:8000/health || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r mcp_servers/fastapi_mcp/requirements.txt
      
      - name: Start FastAPI MCP Server
        run: |
          cd mcp_servers/fastapi_mcp
          uvicorn main:app --host 0.0.0.0 --port 8000 &
          sleep 5
      
      - name: Wait for MCP Server
        run: |
          timeout 30 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'
      
      - name: Install Playwright Browsers
        run: python -m playwright install chromium --with-deps
      
      - name: Run Tests
        env:
          FASTAPI_MCP_URL: http://localhost:8000
          FASTAPI_MCP_TOKEN: ${{ secrets.MCP_TOKEN }}
          BASE_URL: http://localhost:3000
          HEADLESS: true
        run: pytest -v --alluredir=allure-results
      
      - name: Upload Allure Results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: allure-results
          path: allure-results/
```

---

### Staging/Production Environments

**MCP Server Configuration**:
- **FastAPI MCP**: Deployed as standalone service (e.g., Docker container, cloud function)
- **Playwright MCP**: NOT deployed (development-only tool)
- **Authentication**: Strong, rotated tokens
- **Logging**: Structured JSON logs for monitoring
- **Browser**: N/A (no Playwright MCP)

**Security Hardening**:
1. **HTTPS Only**: Use TLS certificates for all MCP communication
2. **Token Rotation**: Change MCP tokens monthly
3. **Network Isolation**: MCP server accessible only from test infrastructure
4. **Rate Limiting**: Implement API rate limits to prevent abuse
5. **Audit Logging**: Log all MCP tool invocations for security review

**Deployment Example (Docker)**:

```dockerfile
# mcp_servers/fastapi_mcp/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Kubernetes Deployment:**

```yaml
# k8s/fastapi-mcp-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fastapi-mcp
  template:
    metadata:
      labels:
        app: fastapi-mcp
    spec:
      containers:
      - name: fastapi-mcp
        image: myregistry/fastapi-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: MCP_TOKEN
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: token
        - name: TARGET_APP_API_URL
          value: "https://staging-app.example.com"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
```

---

## Summary

This documentation covers the complete architecture, usage, and best practices for the MCP servers in this test automation framework:

- **FastAPI MCP Server**: Provides deterministic test data management (`seed_user`, `build_payload`, `reset_env`, `query_state`) for all test environments
- **Playwright MCP Server**: Enables LLM-driven browser exploration and Gherkin generation for development workflows
- **Integration Patterns**: pytest fixtures, error handling, authentication, and environment-specific configurations

**Key Takeaway**: MCP servers are supporting services that provide deterministic data and optional LLM exploration capabilities—they do NOT replace pytest as the test execution engine.

For additional guidance, see:
- [Getting Started Guide](getting_started.md) - Initial setup and first test
- [Writing Tests Guide](writing_tests.md) - Test authoring patterns
- [Architecture Overview](architecture.md) - System design and component relationships
- [Troubleshooting Guide](troubleshooting.md) - Common issues and solutions
