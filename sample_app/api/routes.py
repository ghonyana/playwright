"""
REST API route definitions for the sample application.

Provides /api/users CRUD operations (GET, POST, PUT, DELETE) and /api/auth 
authentication endpoints (login, logout) to demonstrate httpx-based API testing 
patterns with JSON request/response handling.

This module implements a lightweight REST API using Flask Blueprint with in-memory
storage for demonstrating API testing capabilities. All endpoints follow REST
conventions and provide typed request/response structures for use with Pydantic
validation in tests.
"""

from datetime import datetime, timedelta
from threading import Lock
from typing import Dict, List, Optional, Any
from uuid import uuid4

from flask import Blueprint, request, jsonify

# Initialize Flask Blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

# In-memory data storage (thread-safe for concurrent test execution)
_data_lock = Lock()
_users: Dict[str, Dict[str, Any]] = {}
_tokens: Dict[str, Dict[str, Any]] = {}  # token -> {user_id, expires_at}

# Token expiration duration (1 hour for demo purposes)
TOKEN_EXPIRATION = timedelta(hours=1)


def _initialize_mock_data():
    """
    Initialize in-memory storage with sample users for testing.
    
    Creates a set of mock users with different roles to support various
    test scenarios. This function is called once when the module is loaded.
    """
    with _data_lock:
        if not _users:  # Only initialize if empty
            _users.update({
                'user-1': {
                    'id': 'user-1',
                    'email': 'admin@example.com',
                    'name': 'Admin User',
                    'role': 'admin',
                    'password': 'admin123',  # Note: Plain text for demo only
                    'created_at': datetime.utcnow().isoformat()
                },
                'user-2': {
                    'id': 'user-2',
                    'email': 'customer@example.com',
                    'name': 'Customer User',
                    'role': 'customer',
                    'password': 'customer123',
                    'created_at': datetime.utcnow().isoformat()
                },
                'user-3': {
                    'id': 'user-3',
                    'email': 'moderator@example.com',
                    'name': 'Moderator User',
                    'role': 'moderator',
                    'password': 'mod123',
                    'created_at': datetime.utcnow().isoformat()
                }
            })


def _sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive fields from user object before returning in responses.
    
    Args:
        user: User dictionary with all fields
        
    Returns:
        User dictionary without password field
    """
    sanitized = user.copy()
    sanitized.pop('password', None)
    return sanitized


def _validate_token(token: str) -> Optional[str]:
    """
    Validate Bearer token and return associated user_id if valid.
    
    Args:
        token: Bearer token string
        
    Returns:
        user_id if token is valid and not expired, None otherwise
    """
    with _data_lock:
        token_data = _tokens.get(token)
        if not token_data:
            return None
        
        # Check expiration
        if datetime.utcnow() > token_data['expires_at']:
            # Token expired, remove it
            del _tokens[token]
            return None
        
        return token_data['user_id']


def _get_bearer_token() -> Optional[str]:
    """
    Extract Bearer token from Authorization header.
    
    Returns:
        Token string if present and valid format, None otherwise
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]


def _error_response(message: str, status: int, error_code: Optional[str] = None) -> tuple:
    """
    Create standardized error response.
    
    Args:
        message: Human-readable error message
        status: HTTP status code
        error_code: Optional machine-readable error code
        
    Returns:
        Tuple of (response, status_code) for Flask
    """
    response = {
        'error': error_code or 'error',
        'message': message,
        'status': status
    }
    return jsonify(response), status


def _success_response(data: Any, status: int = 200) -> tuple:
    """
    Create standardized success response.
    
    Args:
        data: Response data
        status: HTTP status code (default: 200)
        
    Returns:
        Tuple of (response, status_code) for Flask
    """
    response = {
        'data': data,
        'status': 'success'
    }
    return jsonify(response), status


# ============================================================================
# USER MANAGEMENT ENDPOINTS (CRUD)
# ============================================================================

@api_bp.route('/users', methods=['GET'])
def list_users():
    """
    GET /api/users - List all users with pagination support.
    
    Query Parameters:
        page (int): Page number (default: 1)
        limit (int): Items per page (default: 10, max: 100)
        
    Returns:
        200: JSON object with users array, total count, and page info
        
    Example Response:
        {
            "data": {
                "users": [...],
                "total": 3,
                "page": 1,
                "limit": 10
            },
            "status": "success"
        }
    """
    # Parse pagination parameters
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
    except ValueError:
        return _error_response('Invalid pagination parameters', 400, 'invalid_parameters')
    
    # Validate pagination parameters
    if page < 1:
        return _error_response('Page must be >= 1', 400, 'invalid_page')
    if limit < 1 or limit > 100:
        return _error_response('Limit must be between 1 and 100', 400, 'invalid_limit')
    
    with _data_lock:
        # Get all users and sanitize
        all_users = [_sanitize_user(user) for user in _users.values()]
        
        # Calculate pagination
        total = len(all_users)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        # Slice for current page
        page_users = all_users[start_idx:end_idx]
        
        return _success_response({
            'users': page_users,
            'total': total,
            'page': page,
            'limit': limit
        })


@api_bp.route('/users', methods=['POST'])
def create_user():
    """
    POST /api/users - Create a new user.
    
    Request Body:
        {
            "email": "user@example.com",
            "name": "User Name",
            "role": "customer|admin|moderator",
            "password": "password123"
        }
        
    Returns:
        201: Created user object with Location header
        400: Validation error
        
    Example Response:
        {
            "data": {
                "id": "user-uuid",
                "email": "user@example.com",
                "name": "User Name",
                "role": "customer",
                "created_at": "2024-01-01T00:00:00"
            },
            "status": "success"
        }
    """
    # Parse request body
    if not request.is_json:
        return _error_response('Content-Type must be application/json', 400, 'invalid_content_type')
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['email', 'name', 'role', 'password']
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    
    if missing_fields:
        return _error_response(
            f"Missing required fields: {', '.join(missing_fields)}", 
            400, 
            'missing_fields'
        )
    
    # Validate role
    valid_roles = ['customer', 'admin', 'moderator']
    if data['role'] not in valid_roles:
        return _error_response(
            f"Role must be one of: {', '.join(valid_roles)}", 
            400, 
            'invalid_role'
        )
    
    # Check email uniqueness
    with _data_lock:
        for user in _users.values():
            if user['email'].lower() == data['email'].lower():
                return _error_response('Email already exists', 400, 'duplicate_email')
        
        # Create new user
        user_id = str(uuid4())
        new_user = {
            'id': user_id,
            'email': data['email'],
            'name': data['name'],
            'role': data['role'],
            'password': data['password'],  # Note: Plain text for demo only
            'created_at': datetime.utcnow().isoformat()
        }
        
        _users[user_id] = new_user
        
        # Return sanitized user
        response_data = _sanitize_user(new_user)
        response = jsonify({'data': response_data, 'status': 'success'})
        response.status_code = 201
        response.headers['Location'] = f'/api/users/{user_id}'
        
        return response


@api_bp.route('/users/<user_id>', methods=['GET'])
def get_user(user_id: str):
    """
    GET /api/users/<id> - Get user by ID.
    
    Path Parameters:
        user_id: User identifier
        
    Returns:
        200: User object
        404: User not found
        
    Example Response:
        {
            "data": {
                "id": "user-uuid",
                "email": "user@example.com",
                "name": "User Name",
                "role": "customer",
                "created_at": "2024-01-01T00:00:00"
            },
            "status": "success"
        }
    """
    with _data_lock:
        user = _users.get(user_id)
        
        if not user:
            return _error_response(f'User not found: {user_id}', 404, 'user_not_found')
        
        return _success_response(_sanitize_user(user))


@api_bp.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id: str):
    """
    PUT /api/users/<id> - Update existing user (partial updates allowed).
    
    Path Parameters:
        user_id: User identifier
        
    Request Body (all fields optional):
        {
            "email": "newemail@example.com",
            "name": "New Name",
            "role": "admin"
        }
        
    Returns:
        200: Updated user object
        400: Validation error
        404: User not found
        
    Example Response:
        {
            "data": {
                "id": "user-uuid",
                "email": "newemail@example.com",
                "name": "New Name",
                "role": "admin",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-02T00:00:00"
            },
            "status": "success"
        }
    """
    # Parse request body
    if not request.is_json:
        return _error_response('Content-Type must be application/json', 400, 'invalid_content_type')
    
    data = request.get_json()
    
    # Validate role if provided
    if 'role' in data:
        valid_roles = ['customer', 'admin', 'moderator']
        if data['role'] not in valid_roles:
            return _error_response(
                f"Role must be one of: {', '.join(valid_roles)}", 
                400, 
                'invalid_role'
            )
    
    with _data_lock:
        user = _users.get(user_id)
        
        if not user:
            return _error_response(f'User not found: {user_id}', 404, 'user_not_found')
        
        # Check email uniqueness if email is being updated
        if 'email' in data and data['email'].lower() != user['email'].lower():
            for other_user in _users.values():
                if other_user['id'] != user_id and other_user['email'].lower() == data['email'].lower():
                    return _error_response('Email already exists', 400, 'duplicate_email')
        
        # Update fields (partial update)
        if 'email' in data:
            user['email'] = data['email']
        if 'name' in data:
            user['name'] = data['name']
        if 'role' in data:
            user['role'] = data['role']
        if 'password' in data:
            user['password'] = data['password']
        
        # Add updated timestamp
        user['updated_at'] = datetime.utcnow().isoformat()
        
        return _success_response(_sanitize_user(user))


@api_bp.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id: str):
    """
    DELETE /api/users/<id> - Delete user.
    
    Path Parameters:
        user_id: User identifier
        
    Returns:
        204: No content (success)
        404: User not found
    """
    with _data_lock:
        if user_id not in _users:
            return _error_response(f'User not found: {user_id}', 404, 'user_not_found')
        
        # Delete user
        del _users[user_id]
        
        # Also invalidate any active tokens for this user
        tokens_to_delete = [token for token, data in _tokens.items() if data['user_id'] == user_id]
        for token in tokens_to_delete:
            del _tokens[token]
        
        # Return 204 No Content
        return '', 204


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@api_bp.route('/auth/login', methods=['POST'])
def login():
    """
    POST /api/auth/login - API authentication with Bearer token generation.
    
    Request Body:
        {
            "email": "user@example.com",
            "password": "password123"
        }
        
    Returns:
        200: Authentication token and user info
        400: Missing credentials
        401: Invalid credentials
        
    Example Response:
        {
            "data": {
                "token": "uuid-token-string",
                "user": {
                    "id": "user-uuid",
                    "email": "user@example.com",
                    "name": "User Name",
                    "role": "customer"
                },
                "expires_in": 3600
            },
            "status": "success"
        }
    """
    # Parse request body
    if not request.is_json:
        return _error_response('Content-Type must be application/json', 400, 'invalid_content_type')
    
    data = request.get_json()
    
    # Validate required fields
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return _error_response('Email and password are required', 400, 'missing_credentials')
    
    # Find user by email
    with _data_lock:
        user = None
        for u in _users.values():
            if u['email'].lower() == email.lower():
                user = u
                break
        
        if not user or user['password'] != password:
            # Note: In production, use constant-time comparison for passwords
            return _error_response('Invalid email or password', 401, 'invalid_credentials')
        
        # Generate authentication tokens
        access_token = str(uuid4())
        refresh_token = str(uuid4())
        expires_at = datetime.utcnow() + TOKEN_EXPIRATION
        
        _tokens[access_token] = {
            'user_id': user['id'],
            'expires_at': expires_at,
            'token_type': 'access'
        }
        
        _tokens[refresh_token] = {
            'user_id': user['id'],
            'expires_at': expires_at + timedelta(days=7),  # Refresh token lasts longer
            'token_type': 'refresh'
        }
        
        # Return response compatible with test expectations
        response_data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': int(TOKEN_EXPIRATION.total_seconds()),
            'expires_at': expires_at.isoformat() + 'Z',
            'user_id': user['id'],
            'email': user['email'],
            'role': user['role']
        }
        
        return jsonify(response_data), 200


@api_bp.route('/auth/logout', methods=['POST'])
def logout():
    """
    POST /api/auth/logout - API logout (invalidate token).
    
    Request Headers:
        Authorization: Bearer <token>
        
    Returns:
        200: Logout successful
        401: Unauthorized (missing or invalid token)
        
    Example Response:
        {
            "data": {
                "message": "Logged out successfully"
            },
            "status": "success"
        }
    """
    # Extract and validate token
    token = _get_bearer_token()
    
    if not token:
        return _error_response('Missing or invalid Authorization header', 401, 'missing_token')
    
    user_id = _validate_token(token)
    
    if not user_id:
        return _error_response('Invalid or expired token', 401, 'invalid_token')
    
    # Remove token
    with _data_lock:
        _tokens.pop(token, None)
    
    return _success_response({'message': 'Logged out successfully'})


@api_bp.route('/auth/refresh', methods=['POST'])
def refresh_token():
    """
    POST /api/auth/refresh - Refresh access token using refresh token.
    
    Request Body:
        {
            "refresh_token": "uuid-refresh-token-string"
        }
        
    Returns:
        200: New access token generated
        400: Missing refresh token
        401: Invalid or expired refresh token
        
    Example Response:
        {
            "access_token": "new-uuid-token",
            "refresh_token": "new-refresh-token (if rotation enabled)",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": "2024-01-15T12:30:00Z"
        }
    """
    # Parse request body
    if not request.is_json:
        return _error_response('Content-Type must be application/json', 400, 'invalid_content_type')
    
    data = request.get_json()
    refresh_token = data.get('refresh_token')
    
    if not refresh_token:
        return _error_response('Refresh token is required', 400, 'missing_token')
    
    # Validate refresh token
    with _data_lock:
        token_data = _tokens.get(refresh_token)
        
        if not token_data or token_data.get('token_type') != 'refresh':
            return _error_response('Invalid refresh token', 401, 'invalid_token')
        
        # Check expiration
        if datetime.utcnow() > token_data['expires_at']:
            del _tokens[refresh_token]
            return _error_response('Refresh token has expired', 401, 'expired_token')
        
        # Generate new access token
        user_id = token_data['user_id']
        user = _users.get(user_id)
        
        if not user:
            return _error_response('User not found', 401, 'user_not_found')
        
        new_access_token = str(uuid4())
        new_expires_at = datetime.utcnow() + TOKEN_EXPIRATION
        
        _tokens[new_access_token] = {
            'user_id': user_id,
            'expires_at': new_expires_at,
            'token_type': 'access'
        }
        
        response_data = {
            'access_token': new_access_token,
            'token_type': 'Bearer',
            'expires_in': int(TOKEN_EXPIRATION.total_seconds()),
            'expires_at': new_expires_at.isoformat() + 'Z'
        }
        
        return jsonify(response_data), 200


@api_bp.route('/auth/password-reset', methods=['POST'])
def password_reset_request():
    """
    POST /api/auth/password-reset - Request password reset email.
    
    Request Body:
        {
            "email": "user@example.com"
        }
        
    Returns:
        200: Password reset email sent (always returns success for security)
        400: Missing email
        
    Example Response:
        {
            "message": "Password reset email sent",
            "email": "user@example.com"
        }
    """
    if not request.is_json:
        return _error_response('Content-Type must be application/json', 400, 'invalid_content_type')
    
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return _error_response('Email is required', 400, 'missing_email')
    
    # For security, always return success even if user doesn't exist
    # In a real app, this would send an email with a reset link
    response_data = {
        'message': 'Password reset email sent',
        'email': email,
        'reset_token_expires_in': 3600  # 1 hour expiration
    }
    
    return jsonify(response_data), 200


@api_bp.route('/auth/verify-token', methods=['POST'])
def verify_token():
    """
    POST /api/auth/verify-token - Verify if a token is valid.
    
    Request Body:
        {
            "token": "uuid-token-string"
        }
        
    Returns:
        200: Token is valid
        400: Missing token
        401: Token is invalid or expired
        
    Example Response (valid):
        {
            "valid": true,
            "user_id": "user-123",
            "expires_at": "2024-01-15T12:30:00Z"
        }
        
    Example Response (invalid):
        {
            "valid": false
        }
    """
    if not request.is_json:
        return _error_response('Content-Type must be application/json', 400, 'invalid_content_type')
    
    data = request.get_json()
    token = data.get('token')
    
    if not token:
        return _error_response('Token is required', 400, 'missing_token')
    
    # Validate token
    with _data_lock:
        token_data = _tokens.get(token)
        
        if not token_data:
            response_data = {'valid': False}
            return jsonify(response_data), 200
        
        # Check expiration
        if datetime.utcnow() > token_data['expires_at']:
            del _tokens[token]
            response_data = {'valid': False}
            return jsonify(response_data), 200
        
        response_data = {
            'valid': True,
            'user_id': token_data['user_id'],
            'expires_at': token_data['expires_at'].isoformat() + 'Z'
        }
        
        return jsonify(response_data), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================
# Note: Blueprint error handlers only catch errors within blueprint routes.
# For app-wide error handling, these handlers should be registered on the
# main Flask app object using @app.errorhandler decorators.
# These are kept here as a pattern/example but may need app-level registration.

@api_bp.app_errorhandler(404)
def handle_not_found(error):
    """
    Handle 404 errors for API endpoints.
    
    Uses app_errorhandler to catch 404 errors throughout the application
    when this blueprint is registered.
    """
    # Only handle if the request path starts with /api
    if request.path.startswith('/api'):
        return _error_response('Resource not found', 404, 'not_found')
    # Let Flask handle non-API 404s normally
    return error


@api_bp.app_errorhandler(405)
def handle_method_not_allowed(error):
    """
    Handle 405 Method Not Allowed errors.
    
    Uses app_errorhandler to catch 405 errors throughout the application
    when this blueprint is registered.
    """
    # Only handle if the request path starts with /api
    if request.path.startswith('/api'):
        return _error_response('Method not allowed', 405, 'method_not_allowed')
    # Let Flask handle non-API 405s normally
    return error


@api_bp.app_errorhandler(500)
def handle_internal_error(error):
    """
    Handle 500 Internal Server errors.
    
    Uses app_errorhandler to catch 500 errors throughout the application
    when this blueprint is registered.
    """
    # Only handle if the request path starts with /api
    if request.path.startswith('/api'):
        return _error_response('Internal server error', 500, 'internal_error')
    # Let Flask handle non-API 500s normally
    return error


# ============================================================================
# BLUEPRINT HOOKS
# ============================================================================

@api_bp.before_request
def before_request_handler():
    """
    Execute before each request to API endpoints.
    
    This hook can be used for:
    - Request logging
    - Global authentication checks
    - Request ID generation
    - Timing start for performance monitoring
    """
    # Example: Add request timestamp for logging/monitoring
    request.start_time = datetime.utcnow()


@api_bp.after_request
def after_request_handler(response):
    """
    Execute after each request to API endpoints.
    
    This hook can be used for:
    - Response logging
    - CORS headers (already handled in main app.py)
    - Performance timing
    - Request completion logging
    
    Args:
        response: Flask response object
        
    Returns:
        Modified response object
    """
    # Example: Add processing time header
    if hasattr(request, 'start_time'):
        duration = (datetime.utcnow() - request.start_time).total_seconds()
        response.headers['X-Processing-Time'] = f'{duration:.3f}'
    
    return response


# Initialize mock data when module is imported
_initialize_mock_data()

