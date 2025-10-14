"""
Sample Flask application for test automation framework demonstration.

This application serves as a concrete testing target for the Playwright + pytest
test automation framework. It provides:
- Web UI pages (login, dashboard, profile) for Playwright UI testing
- REST API endpoints (via api_bp Blueprint) for httpx API testing
- Session-based authentication for testing login flows
- Stable HTML elements with ARIA roles and test-ids for reliable locators
- Business-readable page states for BDD Gherkin scenarios

The application uses in-memory storage for simplicity and is designed
specifically for demonstrating test automation patterns, not production use.
"""

import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Import API Blueprint from sample_app/api/routes.py
from sample_app.api.routes import api_bp

# Load environment variables from .env file (if present)
load_dotenv()

# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

def create_app():
    """
    Application factory pattern for Flask app creation.
    
    Creates and configures the Flask application with all necessary settings,
    blueprints, routes, and error handlers. This pattern enables:
    - Testing with different configurations
    - Running multiple app instances
    - Cleaner configuration management
    
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
        static_url_path='/static'
    )
    
    # ========================================================================
    # CONFIGURATION
    # ========================================================================
    
    # Secret key for session management (cryptographically secure)
    # Falls back to secure random token if not provided in environment
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
    
    # Base URL for the application (used in redirects and links)
    app.config['BASE_URL'] = os.getenv('BASE_URL', 'http://localhost:5000')
    
    # Environment (development, testing, production)
    app.config['ENV'] = os.getenv('FLASK_ENV', 'development')
    
    # Debug mode (should be False in production)
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'true').lower() in ('true', '1', 'yes')
    
    # Session configuration
    app.config['SESSION_COOKIE_NAME'] = 'sample_app_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # Database URL (optional, for future persistence)
    app.config['DATABASE_URL'] = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    
    # ========================================================================
    # CORS CONFIGURATION
    # ========================================================================
    
    # Enable CORS for API endpoints to support httpx-based API testing
    # from different origins (e.g., running tests from different port)
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": os.getenv('CORS_ORIGINS', '*').split(','),
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
                "expose_headers": ["Content-Type", "X-Processing-Time"],
                "supports_credentials": True,
                "max_age": 3600
            }
        }
    )
    
    # ========================================================================
    # BLUEPRINT REGISTRATION
    # ========================================================================
    
    # Register API Blueprint for /api/* routes
    # This blueprint provides REST API endpoints for httpx-based API testing
    app.register_blueprint(api_bp)
    
    # ========================================================================
    # WEB UI ROUTES (for Playwright testing)
    # ========================================================================
    
    @app.route('/')
    def index():
        """
        GET / - Root route redirects to login or dashboard based on authentication.
        
        Returns:
            redirect: To /dashboard if authenticated, /login otherwise
        """
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """
        GET /login - Display login page with stable test-friendly elements.
        POST /login - Handle login form submission with session creation.
        
        The login page uses:
        - ARIA roles and labels for stable Playwright locators
        - data-testid attributes for reliable element identification
        - Business-readable element names for Page Object Pattern
        
        POST Request Body (form data):
            email: User email address
            password: User password
            
        Returns:
            GET: Rendered login.html template
            POST: Redirect to dashboard on success, re-render with error on failure
        """
        if request.method == 'POST':
            # Extract form data
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()
            
            # Basic validation
            if not email or not password:
                return render_template(
                    'login.html',
                    error='Email and password are required',
                    email=email
                )
            
            # Import users from API routes module for authentication
            from sample_app.api.routes import _users, _data_lock
            
            # Authenticate user
            with _data_lock:
                user = None
                for u in _users.values():
                    if u['email'].lower() == email.lower() and u['password'] == password:
                        user = u
                        break
                
                if user:
                    # Create session
                    session['user_id'] = user['id']
                    session['user_email'] = user['email']
                    session['user_name'] = user['name']
                    session['user_role'] = user['role']
                    session.permanent = True
                    
                    # Redirect to dashboard
                    return redirect(url_for('dashboard'))
                else:
                    # Authentication failed
                    return render_template(
                        'login.html',
                        error='Invalid email or password',
                        email=email
                    )
        
        # GET request - display login form
        # Check if already authenticated
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        
        return render_template('login.html')
    
    @app.route('/dashboard')
    def dashboard():
        """
        GET /dashboard - Display dashboard page (requires authentication).
        
        The dashboard is the main page after successful login. It uses:
        - Stable ARIA landmarks for navigation testing
        - data-testid attributes for element identification
        - User session data display for verification testing
        
        Returns:
            Rendered dashboard.html template if authenticated
            Redirect to login if not authenticated
        """
        # Require authentication
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Get user info from session
        user_data = {
            'id': session.get('user_id'),
            'email': session.get('user_email'),
            'name': session.get('user_name'),
            'role': session.get('user_role')
        }
        
        return render_template('dashboard.html', user=user_data)
    
    @app.route('/profile')
    def profile():
        """
        GET /profile - Display user profile page (requires authentication).
        
        Shows detailed user information with editable fields for testing
        form interactions and data updates.
        
        Returns:
            Rendered user_profile_page.html template if authenticated
            Redirect to login if not authenticated
        """
        # Require authentication
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # Import users data for full profile information
        from sample_app.api.routes import _users, _data_lock
        
        with _data_lock:
            user = _users.get(session['user_id'])
            
            if not user:
                # User deleted or session stale
                session.clear()
                return redirect(url_for('login'))
            
            # Remove sensitive data
            user_data = {
                'id': user['id'],
                'email': user['email'],
                'name': user['name'],
                'role': user['role'],
                'created_at': user.get('created_at', 'N/A')
            }
        
        return render_template('user_profile_page.html', user=user_data)
    
    @app.route('/logout', methods=['GET', 'POST'])
    def logout():
        """
        GET/POST /logout - Clear session and redirect to login page.
        
        Supports both GET (direct link navigation) and POST (form submission)
        for flexible testing scenarios.
        
        Returns:
            Redirect to login page with session cleared
        """
        session.clear()
        return redirect(url_for('login'))
    
    # ========================================================================
    # HEALTH CHECK AND UTILITY ROUTES
    # ========================================================================
    
    @app.route('/health')
    def health():
        """
        GET /health - Health check endpoint for monitoring and CI/CD.
        
        Returns basic application health status. Useful for:
        - CI/CD pipeline readiness checks
        - Monitoring systems
        - Load balancer health probes
        
        Returns:
            JSON response with status and application info
        """
        return jsonify({
            'status': 'healthy',
            'app': 'sample_app',
            'version': '1.0.0',
            'environment': app.config['ENV']
        })
    
    @app.route('/reset', methods=['POST'])
    def reset_data():
        """
        POST /reset - Reset application data to initial state.
        
        This endpoint is useful for test isolation - allowing tests to
        reset the application to a known state between test runs.
        
        WARNING: This should only be enabled in test/development environments.
        
        Returns:
            JSON response confirming reset
        """
        # Only allow in non-production environments
        if app.config['ENV'] == 'production':
            return jsonify({'error': 'Not allowed in production'}), 403
        
        # Clear sessions
        session.clear()
        
        # Re-initialize user data
        from sample_app.api.routes import _initialize_mock_data
        _initialize_mock_data()
        
        return jsonify({
            'status': 'success',
            'message': 'Application data reset to initial state'
        })
    
    # ========================================================================
    # ERROR HANDLERS
    # ========================================================================
    
    @app.errorhandler(404)
    def not_found_error(error):
        """
        Handle 404 Not Found errors.
        
        Provides different responses for API vs web UI requests:
        - API requests get JSON error response
        - Web UI requests get rendered error page
        
        Args:
            error: Flask error object
            
        Returns:
            JSON response or rendered template with 404 status
        """
        if request.path.startswith('/api'):
            # API request - return JSON
            return jsonify({
                'error': 'not_found',
                'message': 'Resource not found',
                'status': 404
            }), 404
        else:
            # Web UI request - render template
            return render_template('error.html', error_code=404, error_message='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """
        Handle 500 Internal Server Error.
        
        Provides different responses for API vs web UI requests:
        - API requests get JSON error response
        - Web UI requests get rendered error page
        
        Args:
            error: Flask error object
            
        Returns:
            JSON response or rendered template with 500 status
        """
        if request.path.startswith('/api'):
            # API request - return JSON
            return jsonify({
                'error': 'internal_error',
                'message': 'Internal server error',
                'status': 500
            }), 500
        else:
            # Web UI request - render template
            return render_template('error.html', error_code=500, error_message='Internal server error'), 500
    
    # ========================================================================
    # REQUEST HOOKS
    # ========================================================================
    
    @app.before_request
    def before_request_handler():
        """
        Execute before each request to the application.
        
        This hook can be used for:
        - Request logging
        - Authentication state verification
        - Request ID generation for tracing
        - Timing start for performance monitoring
        """
        # Add request timestamp for monitoring
        from datetime import datetime
        request.start_time = datetime.utcnow()
        
        # Log request (in production, use proper logging)
        if app.config['DEBUG']:
            print(f"[{request.method}] {request.path}")
    
    @app.after_request
    def after_request_handler(response):
        """
        Execute after each request to the application.
        
        This hook can be used for:
        - Response logging
        - Adding custom headers
        - Performance timing
        - Security headers
        
        Args:
            response: Flask response object
            
        Returns:
            Modified response object
        """
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Add processing time header for monitoring
        if hasattr(request, 'start_time'):
            from datetime import datetime
            duration = (datetime.utcnow() - request.start_time).total_seconds()
            response.headers['X-Processing-Time'] = f'{duration:.3f}'
        
        return response
    
    return app


# ============================================================================
# APPLICATION INSTANCE CREATION
# ============================================================================

# Create the Flask application instance
# This is the main app object that will be imported and used by tests
app = create_app()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    """
    Main entry point for running the application directly.
    
    Reads configuration from environment variables:
    - HOST: Host to bind to (default: 0.0.0.0)
    - PORT: Port to listen on (default: 5000)
    - FLASK_DEBUG: Enable debug mode (default: true)
    
    Usage:
        python sample_app/app.py
        
    For production, use a WSGI server:
        gunicorn sample_app.app:app
        uwsgi --http :5000 --wsgi-file sample_app/app.py --callable app
    """
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() in ('true', '1', 'yes')
    
    print(f"""
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                   Sample App - Test Automation                   ║
    ║                      Framework Demonstration                      ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Server: http://{host}:{port}                                  ║
    ║  Environment: {app.config['ENV']}                                    ║
    ║  Debug Mode: {debug}                                            ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Web UI:                                                          ║
    ║    • Login:     http://{host}:{port}/login                      ║
    ║    • Dashboard: http://{host}:{port}/dashboard                  ║
    ║    • Profile:   http://{host}:{port}/profile                    ║
    ║                                                                   ║
    ║  API Endpoints:                                                   ║
    ║    • Users:     http://{host}:{port}/api/users                  ║
    ║    • Auth:      http://{host}:{port}/api/auth/login             ║
    ║    • Health:    http://{host}:{port}/health                     ║
    ╠═══════════════════════════════════════════════════════════════════╣
    ║  Default Test Users:                                              ║
    ║    • admin@example.com / admin123                                 ║
    ║    • customer@example.com / customer123                           ║
    ║    • moderator@example.com / mod123                               ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host=host, port=port, debug=debug)

