"""
API Models Package

This package contains Pydantic model definitions for API request/response validation
in the test automation framework. Models provide type-safe data structures with
runtime validation, JSON schema generation, and full mypy compatibility.

Package Structure:
    - auth_models.py: Authentication endpoint models (LoginRequest, LoginResponse, etc.)
    - user_models.py: User management endpoint models (CreateUserRequest, UserResponse, etc.)

Usage Examples:
    # Import authentication models
    from tests.api_clients.models.auth_models import LoginRequest, LoginResponse
    
    # Import user management models
    from tests.api_clients.models.user_models import CreateUserRequest, UserResponse
    
    # Use in API client methods
    def test_authentication(auth_client: AuthAPIClient):
        request = LoginRequest(email="test@example.com", password="SecurePass123!")
        response = auth_client.login(request)
        assert isinstance(response, LoginResponse)
        assert response.token_type == "Bearer"

Integration Points:
    - tests/api_clients/auth_client.py: Uses authentication models for type-safe API calls
    - tests/api_clients/users_client.py: Uses user models for type-safe user management
    - tests/conftest.py: Imports models for fixture definitions
    - tests/step_definitions/*.py: Uses models for BDD step implementations

Notes:
    - All models use Pydantic v2 for enhanced performance and validation
    - Models include Field constraints for comprehensive validation
    - JSON schema examples provided for API documentation
    - Custom validators enforce business rules (password strength, email format, etc.)
    - Extra fields are forbidden by default to catch API contract violations

Per Agent Action Plan Section 0.2.2: Package marker enabling modular organization
of Pydantic model definitions for API testing with httpx per Section 0.4.3.
"""
