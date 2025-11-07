#!/bin/bash

################################################################################
# FastAPI MCP Server Startup Script (Linux/Mac)
################################################################################
# Purpose: Start FastAPI MCP server for deterministic test data management
#
# This script provides a convenient way to start the FastAPI MCP server with
# proper environment configuration, dependency validation, and error handling.
# It supports both development and production modes and is compatible with
# CI/CD pipelines.
#
# MCP Tools Provided:
#   - seed_user       : Create deterministic test users with specific roles
#   - build_payload   : Generate valid API request payloads from templates
#   - reset_env       : Reset test environment to known-good state
#   - query_state     : Query current environment state for verification
#
# Usage:
#   Development mode (with auto-reload):
#     ./start_fastapi_mcp.sh
#
#   Production mode (without reload):
#     ./start_fastapi_mcp.sh --production
#
#   Custom port:
#     ./start_fastapi_mcp.sh --port 9000
#
#   Background execution (CI/CD):
#     nohup ./start_fastapi_mcp.sh --production > mcp_server.log 2>&1 &
#
# Environment Variables:
#   Required:
#     - APP_BASE_URL        : Base URL of web application under test
#     - APP_API_URL         : Base URL of REST API under test
#     - AUTH_SECRET_KEY     : JWT signing secret (min 32 chars)
#
#   Optional:
#     - FASTAPI_MCP_PORT    : Server port (default: 8001)
#     - PORT                : Alternative port variable (fallback)
#     - HOST                : Bind address (default: 0.0.0.0)
#     - LOG_LEVEL           : Logging level (default: INFO)
#     - RELOAD              : Enable auto-reload (default: true)
#     - FASTAPI_MCP_TOKEN   : Authentication token for MCP access
#     - DATABASE_URL        : Database connection string (optional)
#
# Requirements:
#   - Python 3.9 or higher
#   - uvicorn (ASGI server)
#   - All packages in mcp_servers/fastapi_mcp/requirements.txt
#
# Exit Codes:
#   0   : Successful execution
#   1   : General error (missing dependencies, invalid config, etc.)
#   130 : User interrupt (Ctrl+C)
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

################################################################################
# COLOR CODES FOR OUTPUT
################################################################################
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# UTILITY FUNCTIONS
################################################################################

# Print error message in red and exit
error_exit() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

# Print warning message in yellow
warn() {
    echo -e "${YELLOW}WARNING: $1${NC}" >&2
}

# Print info message in blue
info() {
    echo -e "${BLUE}INFO: $1${NC}"
}

# Print success message in green
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Print section header
section() {
    echo ""
    echo "================================================================================"
    echo "$1"
    echo "================================================================================"
}

################################################################################
# SCRIPT INITIALIZATION
################################################################################

# Determine script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
MCP_SERVER_DIR="$PROJECT_ROOT/mcp_servers/fastapi_mcp"

info "FastAPI MCP Server Startup Script"
info "Script directory: $SCRIPT_DIR"
info "Project root: $PROJECT_ROOT"
info "MCP server directory: $MCP_SERVER_DIR"

################################################################################
# COMMAND-LINE ARGUMENT PARSING
################################################################################

# Default values
PRODUCTION_MODE=false
CUSTOM_PORT=""
SHOW_HELP=false

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --production)
            PRODUCTION_MODE=true
            shift
            ;;
        --port)
            CUSTOM_PORT="$2"
            shift 2
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            warn "Unknown option: $1"
            SHOW_HELP=true
            shift
            ;;
    esac
done

# Display help if requested or invalid arguments provided
if [ "$SHOW_HELP" = true ]; then
    cat << EOF

FastAPI MCP Server Startup Script

Usage:
    $0 [OPTIONS]

Options:
    --production          Run in production mode (disable auto-reload)
    --port PORT           Custom port number (default: 8001)
    --help, -h            Show this help message

Examples:
    # Development mode with auto-reload
    $0

    # Production mode
    $0 --production

    # Custom port
    $0 --port 9000

    # Background execution (CI/CD)
    nohup $0 --production > mcp_server.log 2>&1 &

Environment Variables:
    Required:
        APP_BASE_URL        Base URL of web application under test
        APP_API_URL         Base URL of REST API under test
        AUTH_SECRET_KEY     JWT signing secret (min 32 chars)

    Optional:
        FASTAPI_MCP_PORT    Server port (default: 8001)
        HOST                Bind address (default: 0.0.0.0)
        LOG_LEVEL           Logging level (default: INFO)
        RELOAD              Enable auto-reload (default: true in dev)

EOF
    exit 0
fi

################################################################################
# ENVIRONMENT VARIABLE LOADING
################################################################################

section "Loading Environment Configuration"

# Check for .env file in project root
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    info "Loading environment variables from: $ENV_FILE"
    
    # Source .env file safely (ignore comments and blank lines)
    set -a  # Automatically export all variables
    # shellcheck disable=SC1090
    source <(grep -v '^#' "$ENV_FILE" | grep -v '^[[:space:]]*$' | sed 's/\r$//')
    set +a  # Disable automatic export
    
    success "Environment variables loaded from .env"
else
    warn ".env file not found at: $ENV_FILE"
    info "Using environment variables from current shell or defaults"
    info "To create .env file, copy from: $PROJECT_ROOT/.env.example"
fi

################################################################################
# PYTHON VERSION VALIDATION
################################################################################

section "Validating Python Installation"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    error_exit "Python 3 is not installed. Please install Python 3.9 or higher."
fi

# Get Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

info "Found Python version: $PYTHON_VERSION"

# Validate minimum Python version (3.9+)
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]; }; then
    error_exit "Python 3.9 or higher is required. Found: $PYTHON_VERSION"
fi

success "Python version is compatible (>= 3.9)"

################################################################################
# DEPENDENCY VALIDATION
################################################################################

section "Validating Dependencies"

# Check if uvicorn is installed
if ! python3 -c "import uvicorn" 2>/dev/null; then
    error_exit "uvicorn is not installed. Install with: pip install uvicorn[standard]"
fi

success "uvicorn is installed"

# Check if FastAPI is installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    error_exit "FastAPI is not installed. Install with: pip install -r mcp_servers/fastapi_mcp/requirements.txt"
fi

success "FastAPI is installed"

# Validate all requirements from requirements.txt
REQUIREMENTS_FILE="$MCP_SERVER_DIR/requirements.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    error_exit "Requirements file not found: $REQUIREMENTS_FILE"
fi

info "Checking packages from: $REQUIREMENTS_FILE"

# Read requirements and check each package (ignore version constraints, comments, and blank lines)
MISSING_PACKAGES=()
while IFS= read -r line; do
    # Skip comments and blank lines
    line=$(echo "$line" | sed 's/#.*//' | xargs)
    [ -z "$line" ] && continue
    
    # Extract package name (before ==, >=, <=, etc.)
    PACKAGE_NAME=$(echo "$line" | sed 's/\[.*\]//' | sed 's/[<>=!].*//' | xargs)
    
    # Skip if package name is empty
    [ -z "$PACKAGE_NAME" ] && continue
    
    # Convert package name to module name (hyphens to underscores)
    MODULE_NAME=$(echo "$PACKAGE_NAME" | tr '-' '_')
    
    # Special case for packages with different import names
    case "$MODULE_NAME" in
        python_jose) MODULE_NAME="jose" ;;
        python_multipart) MODULE_NAME="multipart" ;;
        pydantic_settings) MODULE_NAME="pydantic_settings" ;;
    esac
    
    # Check if package is installed
    if ! python3 -c "import ${MODULE_NAME}" 2>/dev/null; then
        MISSING_PACKAGES+=("$PACKAGE_NAME")
    fi
done < "$REQUIREMENTS_FILE"

# Report missing packages
if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    error_exit "Missing required packages: ${MISSING_PACKAGES[*]}\nInstall with: pip install -r $REQUIREMENTS_FILE"
fi

success "All required dependencies are installed"

################################################################################
# ENVIRONMENT VARIABLE VALIDATION
################################################################################

section "Validating Configuration"

# Check required environment variables
REQUIRED_VARS=("APP_BASE_URL" "APP_API_URL" "AUTH_SECRET_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var:-}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    warn "Missing required environment variables: ${MISSING_VARS[*]}"
    warn "These can be set in .env file or exported in shell"
    warn ""
    warn "Example .env configuration:"
    warn "  APP_BASE_URL=http://localhost:3000"
    warn "  APP_API_URL=http://localhost:3000/api/v1"
    warn "  AUTH_SECRET_KEY=\$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
    warn ""
    error_exit "Cannot start server without required configuration"
fi

success "Required environment variables are set"

# Validate AUTH_SECRET_KEY length (minimum 32 characters for security)
if [ ${#AUTH_SECRET_KEY} -lt 32 ]; then
    warn "AUTH_SECRET_KEY is shorter than recommended 32 characters"
    warn "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
fi

################################################################################
# SERVER CONFIGURATION
################################################################################

section "Configuring Server"

# Determine host (default to 0.0.0.0 for network access)
HOST="${HOST:-0.0.0.0}"
info "Host: $HOST"

# Determine port (check CUSTOM_PORT, then FASTAPI_MCP_PORT, then PORT, then default 8001)
if [ -n "$CUSTOM_PORT" ]; then
    SERVER_PORT="$CUSTOM_PORT"
    info "Using custom port from command line: $SERVER_PORT"
elif [ -n "${FASTAPI_MCP_PORT:-}" ]; then
    SERVER_PORT="$FASTAPI_MCP_PORT"
    info "Using port from FASTAPI_MCP_PORT: $SERVER_PORT"
elif [ -n "${PORT:-}" ]; then
    SERVER_PORT="$PORT"
    info "Using port from PORT variable: $SERVER_PORT"
else
    SERVER_PORT=8001
    info "Using default port: $SERVER_PORT"
fi

# Validate port number
if ! [[ "$SERVER_PORT" =~ ^[0-9]+$ ]] || [ "$SERVER_PORT" -lt 1 ] || [ "$SERVER_PORT" -gt 65535 ]; then
    error_exit "Invalid port number: $SERVER_PORT (must be 1-65535)"
fi

# Check if port is already in use
if lsof -Pi :"$SERVER_PORT" -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    warn "Port $SERVER_PORT is already in use"
    warn "Another process is listening on this port"
    warn "Either stop the other process or use a different port with --port option"
    error_exit "Port $SERVER_PORT is not available"
fi

success "Port $SERVER_PORT is available"

# Determine reload setting (production mode disables reload)
# Note: uvicorn only accepts --reload to enable; omit flag to disable
if [ "$PRODUCTION_MODE" = true ]; then
    RELOAD_FLAG=""
    RELOAD_STATUS="disabled (production mode)"
else
    # Check RELOAD environment variable, default to enabled for development
    if [ "${RELOAD:-true}" = "true" ]; then
        RELOAD_FLAG="--reload"
        RELOAD_STATUS="enabled (development mode)"
    else
        RELOAD_FLAG=""
        RELOAD_STATUS="disabled (via RELOAD env var)"
    fi
fi

info "Auto-reload: $RELOAD_STATUS"

# Determine log level (from LOG_LEVEL env var, default to INFO)
LOG_LEVEL="${LOG_LEVEL:-INFO}"
LOG_LEVEL=$(echo "$LOG_LEVEL" | tr '[:upper:]' '[:lower:]')  # Convert to lowercase for uvicorn

# Validate log level
case "$LOG_LEVEL" in
    critical|error|warning|info|debug|trace)
        info "Log level: $LOG_LEVEL"
        ;;
    *)
        warn "Invalid LOG_LEVEL: $LOG_LEVEL, defaulting to 'info'"
        LOG_LEVEL="info"
        ;;
esac

# Display server URL
SERVER_URL="http://${HOST}:${SERVER_PORT}"
info "Server URL: $SERVER_URL"

# Display configuration summary
info "Target application: ${APP_BASE_URL}"
info "Target API: ${APP_API_URL}"

success "Server configuration complete"

################################################################################
# DIRECTORY NAVIGATION
################################################################################

section "Preparing Server Startup"

# Change to MCP server directory for proper module imports
if [ ! -d "$MCP_SERVER_DIR" ]; then
    error_exit "MCP server directory not found: $MCP_SERVER_DIR"
fi

info "Changing to MCP server directory: $MCP_SERVER_DIR"
cd "$PROJECT_ROOT" || error_exit "Failed to change to project root directory"

# Verify main.py exists
MAIN_MODULE="mcp_servers/fastapi_mcp/main.py"
if [ ! -f "$MAIN_MODULE" ]; then
    error_exit "FastAPI application not found: $MAIN_MODULE"
fi

success "FastAPI application module located"

################################################################################
# SIGNAL HANDLING FOR GRACEFUL SHUTDOWN
################################################################################

# Trap SIGINT (Ctrl+C) and SIGTERM for graceful shutdown
trap 'echo -e "\n${YELLOW}Received shutdown signal. Stopping server...${NC}"; exit 130' INT TERM

################################################################################
# SERVER STARTUP
################################################################################

section "Starting FastAPI MCP Server"

# Display startup banner
cat << EOF

╔════════════════════════════════════════════════════════════════════════════╗
║                       FastAPI MCP Server                                   ║
║                  Deterministic Test Data Management                        ║
╚════════════════════════════════════════════════════════════════════════════╝

Server Configuration:
  • URL             : $SERVER_URL
  • Host            : $HOST
  • Port            : $SERVER_PORT
  • Mode            : $([ "$PRODUCTION_MODE" = true ] && echo "Production" || echo "Development")
  • Auto-reload     : $([ "$RELOAD_FLAG" = "--reload" ] && echo "Enabled" || echo "Disabled")
  • Log Level       : $LOG_LEVEL

Target Application:
  • Web UI          : ${APP_BASE_URL}
  • REST API        : ${APP_API_URL}

Available MCP Tools:
  • POST /tools/seed_user       - Create deterministic test users
  • POST /tools/build_payload   - Generate API request payloads
  • POST /tools/reset_env       - Reset test environment state
  • POST /tools/query_state     - Query environment resources

Documentation:
  • OpenAPI Docs    : ${SERVER_URL}/docs
  • ReDoc           : ${SERVER_URL}/redoc
  • Health Check    : ${SERVER_URL}/health

════════════════════════════════════════════════════════════════════════════

EOF

info "Starting uvicorn ASGI server..."
info "Press Ctrl+C to stop the server"
echo ""

# Export configuration as environment variables for uvicorn
export HOST
export PORT="$SERVER_PORT"

# Start uvicorn with configured settings
# Use module import path to enable reload functionality
python3 -m uvicorn mcp_servers.fastapi_mcp.main:app \
    --host "$HOST" \
    --port "$SERVER_PORT" \
    --log-level "$LOG_LEVEL" \
    --access-log \
    $RELOAD_FLAG

# Capture exit code
EXIT_CODE=$?

################################################################################
# SHUTDOWN CLEANUP
################################################################################

section "Server Stopped"

if [ $EXIT_CODE -eq 0 ]; then
    success "FastAPI MCP Server stopped successfully"
else
    warn "Server exited with code: $EXIT_CODE"
fi

exit $EXIT_CODE
