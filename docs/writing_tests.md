# Writing Tests

This guide covers how to write effective, maintainable, and deterministic tests for this test automation framework. Follow these principles and patterns to create business-readable tests that execute reliably in both local and CI environments.

## Table of Contents

1. [Test Authoring Philosophy](#test-authoring-philosophy)
2. [Writing Gherkin Scenarios](#writing-gherkin-scenarios)
3. [Writing Step Definitions](#writing-step-definitions)
4. [Writing API Tests](#writing-api-tests)
5. [Using MCP Tools for Test Data](#using-mcp-tools-for-test-data)
6. [Pytest Fixtures Usage](#pytest-fixtures-usage)
7. [Test Organization](#test-organization)
8. [Parallel Execution Considerations](#parallel-execution-considerations)
9. [Allure Reporting Integration](#allure-reporting-integration)
10. [Best Practices](#best-practices)
11. [Common Testing Patterns](#common-testing-patterns)
12. [Debugging Tests](#debugging-tests)
13. [Test Data Management](#test-data-management)
14. [Writing Maintainable Tests](#writing-maintainable-tests)
15. [Performance Optimization](#performance-optimization)
16. [Test Coverage Goals](#test-coverage-goals)

---

## Test Authoring Philosophy

### Core Principles

**1. Business-Readable Tests (WHAT, Not HOW)**
Tests should describe **what** the application does from a user's perspective, not **how** the implementation works.

```gherkin
# Good: Business-level step
When the user logs in with their credentials

# Bad: Implementation-level step
When the user enters "test@example.com" into the CSS selector "#email-input"
And the user clicks the button at coordinates (120, 450)
```

**2. High-Level Gherkin Scenarios**
Gherkin should be understandable by non-technical stakeholders (product managers, business analysts, QA managers).

```gherkin
# Good: Clear business intent
Feature: User Authentication
  Scenario: Successful login redirects to dashboard
    Given a test user with role "customer" exists
    When the user logs in with their credentials
    Then the user should see their dashboard
```

**3. Deterministic Tests with Known-Good States**
Every test starts from a predictable, consistent state using MCP tools for data management.

```python
# Good: Deterministic user creation
@given('a test user with role "customer" exists')
def create_test_user(mcp_client):
    user = mcp_client.seed_user(role='customer', email='test@example.com')
    return user

# Bad: Hardcoded, non-repeatable data
user_email = "test@example.com"  # May already exist, causing failures
```

**4. Isolated Tests with No Shared State**
Each test receives a fresh browser context and operates independently.

```python
# Good: Each test gets new context
@pytest.fixture
def browser_context(browser):
    context = browser.new_context()
    yield context
    context.close()

# Bad: Reusing same context across tests
# Tests may fail due to shared cookies or storage
```

**5. Maintainable Tests Using Stable Locators**
Use ARIA roles, accessible names, and test IDs instead of brittle CSS selectors.

```python
# Good: Stable, semantic locator
page.get_by_role('button', name='Sign In').click()

# Bad: Brittle CSS selector
page.locator('.btn-primary.auth-submit').click()
```

### Test Authoring Time Target

**Goal**: Complete test authoring in **under 30 minutes** from scenario conception to green test.

**Breakdown**:
- 5 minutes: Write Gherkin scenario
- 10 minutes: Implement step definitions (delegate to page objects)
- 10 minutes: Create/update page objects with stable locators
- 5 minutes: Run test, debug, and verify

---

## Writing Gherkin Scenarios

### Feature File Structure

Feature files use the `.feature` extension and live in `tests/features/` directory.

```gherkin
Feature: User Authentication
  As a registered user
  I want to log into my account
  So that I can access personalized features

  Background:
    Given the application is running

  @smoke @authentication
  Scenario: Successful login with valid credentials
    Given a test user with role "customer" exists
    When the user logs in with their credentials
    Then the user should see their dashboard
    And the user's name should be displayed in the header

  @negative @authentication
  Scenario: Login fails with invalid password
    Given a test user with role "customer" exists
    When the user logs in with incorrect password
    Then an error message "Invalid credentials" should be displayed
    And the user should remain on the login page
```

### Given-When-Then Pattern

**Given**: Establish preconditions and initial state
- Create test users via MCP
- Navigate to starting pages
- Set up test data

**When**: Perform the action being tested
- User interactions (click, type, submit)
- API calls
- System events

**Then**: Verify expected outcomes
- Assertions on page state
- Validation of API responses
- Error message checks

### Writing High-Level Steps

**Best Practices**:
- Use business language, not technical implementation details
- Avoid mentioning UI elements like buttons, inputs, CSS selectors
- Focus on user intent and outcomes

```gherkin
# Good: High-level, business-readable
Given a test user with role "admin" exists
When the user creates a new product
Then the product should appear in the product list

# Bad: Low-level, implementation-focused
Given I click the button with id "create-user-btn"
When I type "admin" into the field at xpath "//input[@name='role']"
Then I should see an element with class "product-item"
```

### Scenario vs. Scenario Outline

**Scenario**: Single test case with specific values

```gherkin
Scenario: Admin can access settings
  Given a test user with role "admin" exists
  When the user navigates to settings
  Then the settings page should be visible
```

**Scenario Outline**: Data-driven tests with multiple variations

```gherkin
Scenario Outline: Login validation for different roles
  Given a test user with role "<role>" exists
  When the user logs in with their credentials
  Then the user should see the "<expected_page>" page

  Examples:
    | role     | expected_page |
    | admin    | admin_panel   |
    | customer | dashboard     |
    | editor   | content_editor|
```

### Background Sections

Use `Background` for shared preconditions across all scenarios in a feature.

```gherkin
Feature: User Management

  Background:
    Given the application is running
    And a test admin user exists

  Scenario: Create new user
    When the admin creates a user with role "editor"
    Then the user should be created successfully

  Scenario: Delete existing user
    Given a test user with role "customer" exists
    When the admin deletes the user
    Then the user should be removed from the system
```

### Tags for Test Categorization

Use tags to organize and filter tests.

```gherkin
@smoke @critical
Scenario: Login with valid credentials
  ...

@regression @user_management
Scenario: Update user profile
  ...

@wip @slow
Scenario: Generate large report
  ...
```

**Running tagged tests**:
```bash
pytest -m smoke                    # Run smoke tests only
pytest -m "smoke and critical"     # Multiple tags
pytest -m "not slow"               # Exclude slow tests
```

---

## Writing Step Definitions

### Step Definition File Organization

Organize step definitions by feature area in `tests/step_definitions/`:

```
tests/step_definitions/
├── __init__.py
├── auth_steps.py          # Authentication steps
├── user_steps.py          # User management steps
├── api_steps.py           # API testing steps
└── common_steps.py        # Reusable common steps
```

### Using pytest-bdd Decorators

pytest-bdd provides decorators to map Gherkin steps to Python functions.

```python
from pytest_bdd import given, when, then, scenarios, parsers

# Import scenarios from feature file
scenarios('../features/authentication.feature')

@given('a test user with role "customer" exists')
def create_customer_user(mcp_client):
    user = mcp_client.seed_user(role='customer', email='customer@test.com')
    return user

@when('the user logs in with their credentials')
def perform_login(login_page, create_customer_user):
    user = create_customer_user
    login_page.navigate()
    login_page.login(user.email, user.password)

@then('the user should see their dashboard')
def verify_dashboard_visible(dashboard_page):
    assert dashboard_page.is_visible()
```

### Keeping Step Implementations Short (1-5 Lines)

Step definitions should **delegate** to page objects or API clients, not contain implementation logic.

```python
# Good: Delegates to page object (2 lines)
@when('the user submits the login form')
def submit_login(login_page):
    login_page.click_submit()

# Bad: Contains all implementation logic (10+ lines)
@when('the user submits the login form')
def submit_login(page):
    email_input = page.locator('#email')
    email_input.fill('test@example.com')
    password_input = page.locator('#password')
    password_input.fill('password123')
    submit_button = page.locator('button[type="submit"]')
    submit_button.click()
    page.wait_for_url('**/dashboard')
```

### Delegating to Page Objects for UI Interactions

```python
from tests.pages.login_page import LoginPage
from pytest_bdd import given, when, then

@given('the user is on the login page')
def navigate_to_login(login_page: LoginPage):
    login_page.navigate()

@when('the user enters valid credentials')
def enter_credentials(login_page: LoginPage, test_user):
    login_page.fill_email(test_user.email)
    login_page.fill_password(test_user.password)

@when('the user clicks the login button')
def click_login(login_page: LoginPage):
    login_page.click_submit()
```

### Delegating to API Clients for Backend Operations

```python
from tests.api_clients.users_client import UsersAPIClient
from pytest_bdd import given, when, then

@when('the API creates a new user')
def create_user_via_api(users_api_client: UsersAPIClient, mcp_client):
    payload = mcp_client.build_payload('create_user', {'role': 'editor'})
    response = users_api_client.create(json=payload)
    return response

@then('the user should exist in the system')
def verify_user_exists(users_api_client: UsersAPIClient, create_user_via_api):
    response = create_user_via_api
    user_id = response.json()['id']
    user = users_api_client.get_by_id(user_id)
    assert user.status_code == 200
```

### Using Fixtures for Injection

pytest-bdd steps receive fixtures just like standard pytest tests.

```python
@pytest.fixture
def login_page(page):
    return LoginPage(page)

@pytest.fixture
def test_user(mcp_client):
    return mcp_client.seed_user(role='customer')

@when('the user logs in')
def login(login_page, test_user):  # Fixtures injected automatically
    login_page.login(test_user.email, test_user.password)
```

### Parameterized Steps with Captured Groups

Use `parsers.parse` for extracting parameters from step text.

```python
from pytest_bdd import parsers, given

@given(parsers.parse('a test user with role "{role}" exists'))
def create_user_with_role(mcp_client, role):
    user = mcp_client.seed_user(role=role)
    return user

@then(parsers.parse('the page title should be "{expected_title}"'))
def verify_page_title(page, expected_title):
    assert page.title() == expected_title
```

---

## Writing API Tests

### Organizing API Tests

Place API tests in `tests/api/` directory:

```
tests/api/
├── __init__.py
├── test_auth_api.py       # Authentication endpoints
├── test_users_api.py      # User CRUD operations
└── test_products_api.py   # Product endpoints
```

### Using Typed API Clients with Pydantic Models

```python
# tests/api_clients/models/user_models.py
from pydantic import BaseModel, EmailStr

class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    role: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    created_at: str
```

```python
# tests/api_clients/users_client.py
import httpx
from tests.api_clients.models.user_models import UserResponse

class UsersAPIClient:
    def __init__(self, base_url: str, client: httpx.Client):
        self.base_url = base_url
        self.client = client

    def create(self, json: dict) -> httpx.Response:
        return self.client.post(f'{self.base_url}/users', json=json)

    def get_by_id(self, user_id: int) -> httpx.Response:
        return self.client.get(f'{self.base_url}/users/{user_id}')
    
    def get_user_model(self, user_id: int) -> UserResponse:
        response = self.get_by_id(user_id)
        response.raise_for_status()
        return UserResponse(**response.json())
```

### Building Request Payloads via MCP

```python
# tests/api/test_users_api.py
import pytest

def test_create_user_api(users_api_client, mcp_client):
    # Generate valid payload via MCP
    payload = mcp_client.build_payload('create_user', {'role': 'editor'})
    
    # Make API request
    response = users_api_client.create(json=payload)
    
    # Validate response
    assert response.status_code == 201
    data = response.json()
    assert data['role'] == 'editor'
    assert 'id' in data
    assert 'email' in data
```

### Response Validation with Assertions

```python
def test_get_user_returns_correct_data(users_api_client, mcp_client):
    # Create user via MCP
    user = mcp_client.seed_user(role='customer', email='customer@test.com')
    
    # Fetch via API
    response = users_api_client.get_by_id(user.id)
    
    # Validate status code
    assert response.status_code == 200
    
    # Validate response structure
    data = response.json()
    assert data['id'] == user.id
    assert data['email'] == user.email
    assert data['role'] == 'customer'
    
    # Validate with Pydantic model
    user_model = users_api_client.get_user_model(user.id)
    assert user_model.email == 'customer@test.com'
```

### Attaching Request/Response to Allure Reports

```python
import allure
from allure_commons.types import AttachmentType

def test_create_user_with_allure_attachment(users_api_client, mcp_client):
    payload = mcp_client.build_payload('create_user', {'role': 'admin'})
    
    # Attach request payload
    allure.attach(
        str(payload),
        name='Request Payload',
        attachment_type=AttachmentType.JSON
    )
    
    response = users_api_client.create(json=payload)
    
    # Attach response
    allure.attach(
        response.text,
        name='Response Body',
        attachment_type=AttachmentType.JSON
    )
    
    assert response.status_code == 201
```

### Error Handling and Status Code Validation

```python
def test_create_user_with_duplicate_email_returns_409(users_api_client, mcp_client):
    # Create user
    payload = mcp_client.build_payload('create_user', {'email': 'dup@test.com'})
    response1 = users_api_client.create(json=payload)
    assert response1.status_code == 201
    
    # Attempt duplicate
    response2 = users_api_client.create(json=payload)
    assert response2.status_code == 409
    assert 'already exists' in response2.json()['message'].lower()
```

---

## Using MCP Tools for Test Data

### MCP Tool Overview

The FastAPI MCP server provides deterministic test data management tools:
- `seed_user(role, email)`: Create test users
- `build_payload(template, params)`: Generate valid API request bodies
- `reset_env()`: Clean environment state
- `query_state()`: Verify current environment state

### Creating Test Users with seed_user

```python
@pytest.fixture
def customer_user(mcp_client):
    user = mcp_client.seed_user(
        role='customer',
        email='customer@test.com'
    )
    # Returns User object with: id, email, password, role
    return user

def test_customer_can_view_orders(customer_user, login_page, orders_page):
    login_page.login(customer_user.email, customer_user.password)
    orders_page.navigate()
    assert orders_page.is_visible()
```

### Building API Payloads with build_payload

```python
def test_create_product(products_api_client, mcp_client):
    # Generate valid payload from template
    payload = mcp_client.build_payload('create_product', {
        'name': 'Test Product',
        'price': 29.99,
        'category': 'electronics'
    })
    
    response = products_api_client.create(json=payload)
    assert response.status_code == 201
```

### Resetting Environment State with reset_env

```python
@pytest.fixture(scope='session', autouse=True)
def reset_test_environment(mcp_client):
    # Reset environment before test session
    mcp_client.reset_env()
    yield
    # Optionally reset after session
    mcp_client.reset_env()
```

### Querying Environment State with query_state

```python
def test_verify_user_count(mcp_client):
    # Query current users
    users = mcp_client.query_state('users', {'role': 'admin'})
    assert len(users) >= 1
    
    # Verify specific user exists
    admins = mcp_client.query_state('users', {
        'role': 'admin',
        'email': 'admin@test.com'
    })
    assert len(admins) == 1
```

### Integration with Pytest Fixtures

```python
# tests/conftest.py
import pytest
from tests.helpers.mcp_client import MCPClient
import os

@pytest.fixture(scope='session')
def mcp_client():
    return MCPClient(
        base_url=os.getenv('FASTAPI_MCP_URL', 'http://localhost:8000'),
        token=os.getenv('FASTAPI_MCP_TOKEN', 'dev_token')
    )

@pytest.fixture
def admin_user(mcp_client):
    return mcp_client.seed_user(role='admin', email='admin@test.com')

@pytest.fixture
def customer_user(mcp_client):
    return mcp_client.seed_user(role='customer', email='customer@test.com')
```

---

## Pytest Fixtures Usage

### Understanding Fixture Scopes

Fixtures have different lifetimes controlled by scope parameter:

- `function` (default): New instance per test function
- `class`: New instance per test class
- `module`: New instance per test module file
- `session`: Single instance for entire test session

```python
@pytest.fixture(scope='function')
def browser_context(browser):
    # Fresh context for each test
    context = browser.new_context()
    yield context
    context.close()

@pytest.fixture(scope='session')
def mcp_client():
    # Single MCP client for entire session
    return MCPClient(base_url=os.getenv('FASTAPI_MCP_URL'))
```

### Browser Context Fixtures for UI Tests

```python
# tests/conftest.py
import pytest

@pytest.fixture(scope='session')
def browser(playwright):
    # Launch browser once per session
    browser = playwright.chromium.launch(
        headless=os.getenv('HEADLESS', 'true').lower() == 'true'
    )
    yield browser
    browser.close()

@pytest.fixture
def browser_context(browser):
    # New isolated context per test
    context = browser.new_context(
        viewport={'width': 1920, 'height': 1080'},
        locale='en-US'
    )
    yield context
    context.close()

@pytest.fixture
def page(browser_context):
    # New page per test
    page = browser_context.new_page()
    yield page
    page.close()
```

### API Client Fixtures with Authentication

```python
@pytest.fixture(scope='session')
def httpx_client():
    client = httpx.Client(
        base_url=os.getenv('API_BASE_URL'),
        timeout=30.0,
        headers={'Content-Type': 'application/json'}
    )
    yield client
    client.close()

@pytest.fixture
def authenticated_client(httpx_client, admin_user):
    # Get auth token
    response = httpx_client.post('/auth/login', json={
        'email': admin_user.email,
        'password': admin_user.password
    })
    token = response.json()['token']
    
    # Add auth header
    httpx_client.headers['Authorization'] = f'Bearer {token}'
    
    yield httpx_client
    
    # Clean up header
    del httpx_client.headers['Authorization']
```

### MCP Client Fixture

```python
@pytest.fixture(scope='session')
def mcp_client():
    return MCPClient(
        base_url=os.getenv('FASTAPI_MCP_URL', 'http://localhost:8000'),
        token=os.getenv('FASTAPI_MCP_TOKEN')
    )
```

### Sharing Fixtures via conftest.py

`conftest.py` files make fixtures available to all tests in the directory and subdirectories.

```
tests/
├── conftest.py               # Fixtures for all tests
├── ui/
│   ├── conftest.py           # UI-specific fixtures
│   └── test_login_ui.py
└── api/
    ├── conftest.py           # API-specific fixtures
    └── test_users_api.py
```

### Fixture Dependency Injection

Fixtures can depend on other fixtures:

```python
@pytest.fixture
def login_page(page):
    # Depends on page fixture
    return LoginPage(page)

@pytest.fixture
def logged_in_user(login_page, test_user):
    # Depends on login_page and test_user fixtures
    login_page.navigate()
    login_page.login(test_user.email, test_user.password)
    return test_user

def test_profile_page(profile_page, logged_in_user):
    # Uses logged_in_user which handles login
    profile_page.navigate()
    assert profile_page.get_email() == logged_in_user.email
```

---

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures
├── features/                      # Gherkin feature files
│   ├── __init__.py
│   ├── authentication.feature
│   ├── user_management.feature
│   └── api_operations.feature
├── step_definitions/              # pytest-bdd step implementations
│   ├── __init__.py
│   ├── auth_steps.py
│   ├── user_steps.py
│   ├── api_steps.py
│   └── common_steps.py
├── ui/                            # UI-specific tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_login_ui.py
│   └── test_navigation_ui.py
├── api/                           # API-specific tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_users_api.py
│   └── test_auth_api.py
├── integration/                   # Integration tests
│   ├── __init__.py
│   └── test_end_to_end.py
├── pages/                         # Page Object Models
│   ├── __init__.py
│   ├── base_page.py
│   ├── login_page.py
│   └── dashboard_page.py
├── api_clients/                   # API client wrappers
│   ├── __init__.py
│   ├── base_client.py
│   ├── auth_client.py
│   └── users_client.py
└── helpers/                       # Utility functions
    ├── __init__.py
    ├── mcp_client.py
    ├── allure_utils.py
    └── assertions.py
```

### Naming Conventions

**Test Files**: Must match `test_*.py` or `*_test.py` pattern

```
test_login_ui.py         ✓ Valid
test_users_api.py        ✓ Valid
users_test.py            ✓ Valid
test_authentication.py   ✓ Valid
authentication.py        ✗ Invalid (missing test_ prefix)
```

**Test Functions**: Must start with `test_`

```python
def test_login_success():      ✓ Valid
def test_create_user_api():    ✓ Valid
def login_test():              ✗ Invalid (wrong prefix)
def verify_login():            ✗ Invalid (no test_ prefix)
```

### Grouping Related Tests in Classes

```python
class TestUserAuthentication:
    def test_login_success(self, login_page, customer_user):
        login_page.login(customer_user.email, customer_user.password)
        assert login_page.is_logged_in()
    
    def test_login_invalid_password(self, login_page, customer_user):
        login_page.login(customer_user.email, 'wrong_password')
        assert login_page.get_error_message() == 'Invalid credentials'
    
    def test_logout(self, login_page, logged_in_user):
        login_page.logout()
        assert not login_page.is_logged_in()
```

### Using Pytest Markers for Categorization

```python
import pytest

@pytest.mark.smoke
@pytest.mark.critical
def test_login():
    pass

@pytest.mark.regression
@pytest.mark.slow
def test_generate_large_report():
    pass

@pytest.mark.skip(reason='Known bug #123')
def test_broken_feature():
    pass

@pytest.mark.skipif(os.getenv('ENV') == 'prod', reason='Not for production')
def test_destructive_operation():
    pass
```

Register markers in `pytest.ini`:

```ini
[pytest]
markers =
    smoke: Quick smoke tests
    regression: Full regression suite
    critical: Critical functionality
    slow: Tests taking >30 seconds
    wip: Work in progress
```

---

## Parallel Execution Considerations

### Per-Test Browser Context Isolation

**Critical**: Each test must receive a fresh browser context to enable parallel execution.

```python
# Good: Function-scoped context (new per test)
@pytest.fixture
def browser_context(browser):
    context = browser.new_context()
    yield context
    context.close()

# Bad: Session-scoped context (shared across tests)
@pytest.fixture(scope='session')
def browser_context(browser):
    # DON'T DO THIS - tests will interfere with each other
    context = browser.new_context()
    yield context
    context.close()
```

### No Shared Mutable Global State

```python
# Bad: Global mutable state
CURRENT_USER = None  # Tests will interfere

def test_login():
    global CURRENT_USER
    CURRENT_USER = create_user()

# Good: Test-scoped fixture
@pytest.fixture
def current_user(mcp_client):
    return mcp_client.seed_user(role='customer')
```

### Execution Order Independence

Tests must pass regardless of execution order.

```bash
# Tests should pass in any order
pytest tests/                 # All tests
pytest --lf tests/            # Last failed first
pytest tests/ --random-order  # Random order
```

```python
# Bad: Depends on previous test
def test_create_user():
    # Creates user with ID 1
    pass

def test_update_user():
    # Assumes user ID 1 exists from previous test
    # FAILS when run alone or in different order
    pass

# Good: Each test sets up its own data
def test_create_user(mcp_client):
    user = mcp_client.seed_user(role='customer')
    assert user.id is not None

def test_update_user(mcp_client, users_api_client):
    # Creates its own user
    user = mcp_client.seed_user(role='customer')
    # Now update it
    response = users_api_client.update(user.id, {'name': 'Updated'})
    assert response.status_code == 200
```

### Using pytest-xdist for Parallel Execution

```bash
# Run tests in parallel with auto worker count
pytest -n auto

# Run with specific number of workers
pytest -n 4

# Load balance by scope (recommended for UI tests)
pytest -n auto --dist loadscope
```

### Load Balancing Strategies

```bash
# loadscope: Groups tests by module (best for UI tests)
pytest -n auto --dist loadscope

# loadfile: Groups tests by file
pytest -n auto --dist loadfile

# no: Free scheduling (fastest, but may cause issues with shared resources)
pytest -n auto --dist no
```

---

## Allure Reporting Integration

### Adding Feature and Story Decorators

```python
import allure

@allure.feature('User Authentication')
@allure.story('Login Flow')
def test_login_success(login_page, customer_user):
    login_page.login(customer_user.email, customer_user.password)
    assert login_page.is_logged_in()
```

### Using Severity for Test Prioritization

```python
import allure

@allure.severity(allure.severity_level.BLOCKER)
def test_critical_payment_flow():
    pass

@allure.severity(allure.severity_level.CRITICAL)
def test_user_registration():
    pass

@allure.severity(allure.severity_level.NORMAL)
def test_search_functionality():
    pass

@allure.severity(allure.severity_level.MINOR)
def test_footer_links():
    pass
```

### Custom Steps for Detailed Test Steps

```python
import allure

def test_checkout_flow(cart_page, checkout_page, customer_user):
    with allure.step('Add items to cart'):
        cart_page.add_item('Product A')
        cart_page.add_item('Product B')
    
    with allure.step('Proceed to checkout'):
        cart_page.click_checkout()
    
    with allure.step('Fill shipping information'):
        checkout_page.fill_shipping_address({
            'street': '123 Test St',
            'city': 'Test City',
            'zip': '12345'
        })
    
    with allure.step('Complete payment'):
        checkout_page.complete_payment()
    
    with allure.step('Verify order confirmation'):
        assert checkout_page.get_confirmation_message() == 'Order placed successfully'
```

### Automatic Screenshot Attachment on Failure

Configure in `conftest.py`:

```python
import pytest
import allure
from allure_commons.types import AttachmentType

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    
    if report.when == 'call' and report.failed:
        # Get page fixture if available
        if 'page' in item.funcargs:
            page = item.funcargs['page']
            screenshot = page.screenshot()
            allure.attach(
                screenshot,
                name='failure_screenshot',
                attachment_type=AttachmentType.PNG
            )
```

### Adding Custom Attachments

```python
import allure
from allure_commons.types import AttachmentType

def test_api_response(users_api_client):
    response = users_api_client.get_all()
    
    # Attach response body
    allure.attach(
        response.text,
        name='API Response',
        attachment_type=AttachmentType.JSON
    )
    
    # Attach custom data
    allure.attach(
        f'Status Code: {response.status_code}',
        name='Response Status',
        attachment_type=AttachmentType.TEXT
    )
    
    assert response.status_code == 200
```

---

## Best Practices

### Keep Gherkin Steps at Business Level

**Good**: Business language, no implementation details
```gherkin
When the user logs in with their credentials
Then the user should see their dashboard
```

**Bad**: Implementation details exposed
```gherkin
When the user clicks the button with ID "login-btn"
Then the user should see an element with class "dashboard-container"
```

### One Assertion Per Then Step

**Good**: Single clear assertion
```gherkin
Then the user should be logged in
And the dashboard should be visible
And the user's name should be in the header
```

**Bad**: Multiple validations in one step
```gherkin
Then the user should be logged in and see dashboard and see their name
```

### Use Background for Shared Given Steps

```gherkin
Feature: User Management

  Background:
    Given the application is running
    And an admin user is logged in

  Scenario: Create user
    When the admin creates a new user
    ...

  Scenario: Delete user
    When the admin deletes a user
    ...
```

### Avoid Hardcoded Test Data

**Good**: Data from MCP
```python
user = mcp_client.seed_user(role='customer', email='customer@test.com')
```

**Bad**: Hardcoded values
```python
email = 'test@example.com'  # May already exist, causing flakiness
password = 'password123'    # Hardcoded, not deterministic
```

### Write Self-Documenting Test Names

**Good**: Clear intent
```python
def test_login_fails_with_invalid_password()
def test_admin_can_delete_user()
def test_api_returns_404_for_nonexistent_user()
```

**Bad**: Vague or unclear
```python
def test_login()
def test_user()
def test_case_1()
```

### Add Comments for Complex Test Logic

```python
def test_complex_workflow(mcp_client, checkout_page):
    # Create user with premium membership for discount eligibility
    user = mcp_client.seed_user(role='premium_member')
    
    # Add items totaling $100 to trigger free shipping
    checkout_page.add_items_totaling(100.00)
    
    # Apply discount code (20% off for premium members)
    checkout_page.apply_discount('PREMIUM20')
    
    # Verify final price: $100 - 20% = $80
    assert checkout_page.get_total() == 80.00
```

### Use Type Hints for Maintainability

```python
from typing import Dict, List
from tests.pages.login_page import LoginPage
from tests.helpers.mcp_client import MCPClient

def test_login(login_page: LoginPage, mcp_client: MCPClient) -> None:
    user: Dict[str, str] = mcp_client.seed_user(role='customer')
    login_page.login(user['email'], user['password'])
    assert login_page.is_logged_in() is True
```

---

## Common Testing Patterns

### Login Flow with Seeded User

```python
def test_login_flow(login_page, dashboard_page, mcp_client):
    # Seed test user
    user = mcp_client.seed_user(role='customer', email='customer@test.com')
    
    # Navigate and login
    login_page.navigate()
    login_page.login(user.email, user.password)
    
    # Verify redirect to dashboard
    assert dashboard_page.is_visible()
    assert dashboard_page.get_user_name() == user.email
```

### Form Submission with Validation

```python
def test_form_validation_on_empty_fields(registration_page):
    registration_page.navigate()
    
    # Submit empty form
    registration_page.click_submit()
    
    # Verify validation errors
    assert registration_page.has_error('Email is required')
    assert registration_page.has_error('Password is required')
    assert not registration_page.is_submission_successful()
```

### Multi-Step Workflows

```python
def test_e2e_checkout_workflow(mcp_client, login_page, products_page, cart_page, checkout_page):
    # Setup: Create user
    user = mcp_client.seed_user(role='customer')
    
    # Step 1: Login
    login_page.navigate()
    login_page.login(user.email, user.password)
    
    # Step 2: Browse and add products
    products_page.navigate()
    products_page.add_to_cart('Product A')
    products_page.add_to_cart('Product B')
    
    # Step 3: View cart
    cart_page.navigate()
    assert cart_page.get_item_count() == 2
    
    # Step 4: Checkout
    cart_page.proceed_to_checkout()
    checkout_page.fill_payment_info({'card': '4242424242424242'})
    checkout_page.submit_order()
    
    # Step 5: Verify confirmation
    assert checkout_page.get_confirmation_message() == 'Order placed successfully'
```

### Error Handling and Negative Test Cases

```python
def test_login_with_nonexistent_user(login_page):
    login_page.navigate()
    login_page.login('nonexistent@test.com', 'password')
    
    assert login_page.has_error('User not found')
    assert not login_page.is_logged_in()

def test_api_returns_400_for_invalid_email(users_api_client, mcp_client):
    payload = mcp_client.build_payload('create_user', {'email': 'invalid-email'})
    response = users_api_client.create(json=payload)
    
    assert response.status_code == 400
    assert 'Invalid email format' in response.json()['message']
```

### API + UI Combined Tests

```python
def test_create_user_via_api_verify_in_ui(mcp_client, users_api_client, users_page):
    # Create user via API
    payload = mcp_client.build_payload('create_user', {'role': 'editor'})
    response = users_api_client.create(json=payload)
    assert response.status_code == 201
    user_id = response.json()['id']
    
    # Verify in UI
    users_page.navigate()
    assert users_page.user_exists(user_id)
    assert users_page.get_user_role(user_id) == 'editor'
```

---

## Debugging Tests

### Running Tests in Headed Mode

```bash
# Set environment variable
HEADLESS=false pytest tests/ui/test_login_ui.py

# Or use pytest flag
pytest --headed tests/ui/test_login_ui.py
```

### Using --headed Flag for Visual Debugging

```bash
# Run with browser visible
pytest --headed --slowmo=1000 tests/ui/

# Slow motion (1000ms between actions)
pytest --headed --slowmo=2000 tests/
```

### Capturing Screenshots

```python
def test_with_screenshot(page, login_page):
    login_page.navigate()
    
    # Capture screenshot
    page.screenshot(path='screenshots/login_page.png')
    
    login_page.login('test@example.com', 'password')
    
    # Capture after action
    page.screenshot(path='screenshots/after_login.png')
```

### Viewing Playwright Traces

```python
# Enable tracing in conftest.py
@pytest.fixture
def browser_context(browser):
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True)
    yield context
    context.tracing.stop(path='trace.zip')
    context.close()
```

```bash
# View trace
playwright show-trace trace.zip
```

### Adding Print Statements and Logging

```python
from loguru import logger

def test_with_logging(login_page, customer_user):
    logger.info(f'Testing login for user: {customer_user.email}')
    
    login_page.navigate()
    logger.debug('Navigated to login page')
    
    login_page.login(customer_user.email, customer_user.password)
    logger.debug('Submitted login form')
    
    assert login_page.is_logged_in()
    logger.info('Login successful')
```

### Using pytest --pdb for Debugging Failures

```bash
# Drop into debugger on first failure
pytest --pdb tests/

# Drop into debugger on every test
pytest --trace tests/
```

```python
def test_with_breakpoint(login_page):
    login_page.navigate()
    
    # Python debugger breakpoint
    breakpoint()
    
    login_page.login('test@example.com', 'password')
```

---

## Test Data Management

### Creating Test Users with Specific Roles

```python
@pytest.fixture
def admin_user(mcp_client):
    return mcp_client.seed_user(role='admin', email='admin@test.com')

@pytest.fixture
def customer_user(mcp_client):
    return mcp_client.seed_user(role='customer', email='customer@test.com')

@pytest.fixture
def editor_user(mcp_client):
    return mcp_client.seed_user(role='editor', email='editor@test.com')
```

### Generating Realistic Data with Faker

```python
from faker import Faker

fake = Faker()

def test_with_realistic_data(mcp_client, users_api_client):
    payload = {
        'email': fake.email(),
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
        'address': fake.address(),
        'phone': fake.phone_number()
    }
    
    response = users_api_client.create(json=payload)
    assert response.status_code == 201
```

### Cleaning Up Test Data After Execution

```python
@pytest.fixture
def test_user(mcp_client, users_api_client):
    # Create user
    user = mcp_client.seed_user(role='customer')
    yield user
    
    # Cleanup
    users_api_client.delete(user.id)
```

### Using MCP reset_env for Deterministic State

```python
@pytest.fixture(scope='session', autouse=True)
def reset_environment_before_tests(mcp_client):
    # Reset environment before all tests
    mcp_client.reset_env()
    yield
```

---

## Writing Maintainable Tests

### Avoiding Test Interdependencies

**Bad**: Tests depend on each other
```python
def test_1_create_user():
    # Creates user with ID 1
    global user_id
    user_id = create_user()

def test_2_update_user():
    # Assumes test_1_create_user ran first
    update_user(user_id)
```

**Good**: Each test is independent
```python
def test_create_user(mcp_client):
    user = mcp_client.seed_user(role='customer')
    assert user.id is not None

def test_update_user(mcp_client, users_api_client):
    user = mcp_client.seed_user(role='customer')
    response = users_api_client.update(user.id, {'name': 'Updated'})
    assert response.status_code == 200
```

### Keeping Tests Focused and Single-Purpose

**Bad**: Tests too many things at once
```python
def test_everything(login_page, profile_page, settings_page):
    # Login
    login_page.login('test@example.com', 'password')
    # Update profile
    profile_page.update_name('New Name')
    # Change settings
    settings_page.enable_notifications()
    # Logout
    login_page.logout()
```

**Good**: Focused, single-purpose tests
```python
def test_login(login_page, customer_user):
    login_page.login(customer_user.email, customer_user.password)
    assert login_page.is_logged_in()

def test_update_profile(profile_page, logged_in_user):
    profile_page.update_name('New Name')
    assert profile_page.get_name() == 'New Name'

def test_enable_notifications(settings_page, logged_in_user):
    settings_page.enable_notifications()
    assert settings_page.are_notifications_enabled()
```

### Refactoring Duplicated Code into Helpers

**Bad**: Duplicated login logic
```python
def test_a(page):
    page.goto('/login')
    page.fill('#email', 'test@example.com')
    page.fill('#password', 'password')
    page.click('button[type="submit"]')
    # test logic

def test_b(page):
    page.goto('/login')
    page.fill('#email', 'test@example.com')
    page.fill('#password', 'password')
    page.click('button[type="submit"]')
    # test logic
```

**Good**: Reusable fixture or helper
```python
@pytest.fixture
def logged_in_session(login_page, customer_user):
    login_page.navigate()
    login_page.login(customer_user.email, customer_user.password)
    return customer_user

def test_a(logged_in_session, dashboard_page):
    # test logic

def test_b(logged_in_session, profile_page):
    # test logic
```

### Updating Page Objects When UI Changes

When UI changes, update only the page object, not all tests:

```python
# Before UI change: Button ID is 'submit-btn'
class LoginPage:
    def click_submit(self):
        self.page.locator('#submit-btn').click()

# After UI change: Button ID changed to 'login-submit'
class LoginPage:
    def click_submit(self):
        self.page.locator('#login-submit').click()

# All tests using login_page.click_submit() continue to work
```

### Version Controlling .feature Files with Test Code

- Commit .feature files alongside step definitions
- Review changes to Gherkin scenarios in PRs
- Track test coverage changes over time
- Use Git tags to mark test suite versions

---

## Performance Optimization

### Running Tests in Parallel with pytest-xdist

```bash
# Automatic worker count (CPU cores)
pytest -n auto

# Specific worker count
pytest -n 4

# With load balancing
pytest -n auto --dist loadscope
```

### Minimizing Browser Context Creation Overhead

```python
# Good: Reuse browser instance across tests
@pytest.fixture(scope='session')
def browser(playwright):
    browser = playwright.chromium.launch()
    yield browser
    browser.close()

# Create new context per test (lightweight)
@pytest.fixture
def browser_context(browser):
    context = browser.new_context()
    yield context
    context.close()
```

### Reusing API Client Sessions

```python
# Good: Session-scoped httpx client
@pytest.fixture(scope='session')
def httpx_client():
    client = httpx.Client(base_url=os.getenv('API_BASE_URL'))
    yield client
    client.close()

# Bad: New client per test (expensive)
@pytest.fixture
def httpx_client():
    client = httpx.Client(base_url=os.getenv('API_BASE_URL'))
    yield client
    client.close()
```

### Caching MCP Authentication Tokens

```python
# Cache token at session scope
@pytest.fixture(scope='session')
def mcp_auth_token():
    # Authenticate once per session
    response = httpx.post(
        f'{os.getenv("FASTAPI_MCP_URL")}/auth/token',
        json={'api_key': os.getenv('FASTAPI_MCP_TOKEN')}
    )
    return response.json()['token']

@pytest.fixture(scope='session')
def mcp_client(mcp_auth_token):
    return MCPClient(
        base_url=os.getenv('FASTAPI_MCP_URL'),
        token=mcp_auth_token
    )
```

### Using pytest.mark.skip for Slow Tests

```python
import pytest

@pytest.mark.skip(reason='Slow test, run manually')
def test_generate_large_report():
    # Test taking >5 minutes
    pass

@pytest.mark.skipif(os.getenv('SKIP_SLOW') == 'true', reason='Skipping slow tests')
def test_bulk_import():
    pass
```

```bash
# Skip slow tests in CI
SKIP_SLOW=true pytest tests/

# Run slow tests locally
pytest -m slow tests/
```

---

## Test Coverage Goals

### Critical User Paths: 100% Coverage

Critical paths must have comprehensive test coverage:
- User registration and login
- Payment processing
- Data submission workflows
- Account management

```python
# Critical path example: Complete registration flow
def test_complete_registration_flow(registration_page, email_verification_page, dashboard_page, mcp_client):
    # Generate test user data
    user_data = mcp_client.build_payload('registration', {})
    
    # Register
    registration_page.navigate()
    registration_page.fill_form(user_data)
    registration_page.submit()
    
    # Verify email (mock)
    email_verification_page.verify_email(user_data['email'])
    
    # Verify redirect to dashboard
    assert dashboard_page.is_visible()
```

### Error Handling: Negative Test Cases

Test failure scenarios and error states:

```python
def test_login_with_invalid_email_format(login_page):
    login_page.login('invalid-email', 'password')
    assert login_page.has_error('Invalid email format')

def test_api_returns_422_for_missing_required_field(users_api_client):
    response = users_api_client.create(json={'email': 'test@example.com'})
    # Missing required 'password' field
    assert response.status_code == 422
```

### Cross-Browser: Chromium, Firefox, WebKit

Run tests across multiple browsers:

```bash
# Chromium
pytest --browser chromium

# Firefox
pytest --browser firefox

# WebKit (Safari)
pytest --browser webkit

# All browsers
pytest --browser chromium --browser firefox --browser webkit
```

Configure in `pytest.ini`:
```ini
[pytest]
addopts = --browser chromium --browser firefox --browser webkit
```

### Regression: Automated in CI/CD

All regression tests must run automatically in CI:

```yaml
# .github/workflows/test.yml
name: Regression Tests
on:
  push:
    branches: [main, develop]
  pull_request:
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM
```

Run regression suite:
```bash
pytest -m regression tests/
```

---

## Summary

This guide covered the complete test authoring workflow:

1. **Philosophy**: Business-readable, deterministic, isolated tests
2. **Gherkin**: High-level scenarios focusing on WHAT not HOW
3. **Step Definitions**: Short implementations delegating to page objects/API clients
4. **API Tests**: Typed clients with MCP-generated payloads
5. **MCP Tools**: Deterministic test data management
6. **Fixtures**: Proper scoping and dependency injection
7. **Organization**: Clear directory structure and naming conventions
8. **Parallel Execution**: Isolated contexts enabling safe parallelization
9. **Allure Reporting**: Rich test documentation and failure analysis
10. **Best Practices**: Maintainable, self-documenting tests

**Next Steps**:
- Review [Page Object Pattern Guide](page_objects.md) for UI testing patterns
- Explore [MCP Servers Documentation](mcp_servers.md) for data management tools
- Check [Architecture Overview](architecture.md) for system understanding
- See [Troubleshooting Guide](troubleshooting.md) for common issues

**Questions or Issues?**
- Consult [Getting Started](getting_started.md) for setup instructions
- Review example tests in `tests/ui/` and `tests/api/` directories
- Check GitHub Issues for known problems and solutions
