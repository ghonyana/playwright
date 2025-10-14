#!/usr/bin/env bash

################################################################################
# Playwright MCP Server Startup Script (Unix/Linux/macOS)
#
# Purpose: Start the Playwright MCP server for LLM-driven browser exploration
#          and automated Gherkin scenario generation
#
# Usage:
#   ./start_playwright_mcp.sh              # Start with default settings
#   ./start_playwright_mcp.sh --port 9001  # Start with custom port
#
# Environment Variables:
#   PLAYWRIGHT_MCP_ENABLED - Must be 'true' to start server (development-only)
#   PLAYWRIGHT_MCP_PORT    - Server port (default: 8001)
#   PLAYWRIGHT_MCP_URL     - Full server URL (optional)
#   BASE_URL               - Target application URL for testing
#   HEADLESS               - Browser headless mode (default: true)
#   LOG_LEVEL              - Logging level (default: info)
#
# Note: This server is intended for DEVELOPMENT ONLY, not CI/CD pipelines
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default configuration
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8001"
DEFAULT_LOG_LEVEL="info"
RELOAD_FLAG="--reload"

# Server configuration
HOST="${PLAYWRIGHT_MCP_HOST:-$DEFAULT_HOST}"
PORT="${PLAYWRIGHT_MCP_PORT:-$DEFAULT_PORT}"
LOG_LEVEL="${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}"

################################################################################
# Function: print_banner
# Display startup banner with development-only warning
################################################################################
print_banner() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  ${GREEN}Playwright MCP Server - LLM Exploration Mode${NC}            ${BLUE}║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  WARNING: This is a DEVELOPMENT-ONLY server${NC}"
    echo -e "${YELLOW}   NOT intended for CI/CD pipelines or production use${NC}"
    echo -e "${YELLOW}   For CI/CD testing, use the FastAPI MCP server instead${NC}"
    echo ""
}

################################################################################
# Function: log_info
# Print informational message
################################################################################
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

################################################################################
# Function: log_warn
# Print warning message
################################################################################
log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

################################################################################
# Function: log_error
# Print error message and exit
################################################################################
log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

################################################################################
# Function: load_environment
# Load environment variables from .env file if it exists
################################################################################
load_environment() {
    local env_file="${PROJECT_ROOT}/.env"
    
    if [[ -f "$env_file" ]]; then
        log_info "Loading environment from .env file..."
        # Export variables from .env, ignoring comments and empty lines
        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a
        log_info "Environment variables loaded successfully"
    else
        log_warn ".env file not found at ${env_file}"
        log_info "Using system environment variables only"
    fi
}

################################################################################
# Function: check_enabled_flag
# Verify PLAYWRIGHT_MCP_ENABLED is set to true
################################################################################
check_enabled_flag() {
    local enabled="${PLAYWRIGHT_MCP_ENABLED:-false}"
    
    if [[ "${enabled,,}" != "true" ]]; then
        echo ""
        log_error "Playwright MCP is disabled. Set PLAYWRIGHT_MCP_ENABLED=true in .env to enable.

To enable LLM exploration mode:
  1. Copy .env.example to .env (if not exists): cp .env.example .env
  2. Add or update: PLAYWRIGHT_MCP_ENABLED=true
  3. Run this script again

Note: This server is for development exploration only, not for CI/CD."
    fi
    
    log_info "Playwright MCP is enabled for LLM exploration"
}

################################################################################
# Function: check_python
# Verify Python 3.9+ is installed and available
################################################################################
check_python() {
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        log_error "Python is not installed or not in PATH. Please install Python 3.9 or higher."
    fi
    
    local python_cmd="python3"
    if ! command -v python3 &> /dev/null; then
        python_cmd="python"
    fi
    
    local python_version
    python_version=$($python_cmd --version 2>&1 | awk '{print $2}')
    local major_version
    major_version=$(echo "$python_version" | cut -d. -f1)
    local minor_version
    minor_version=$(echo "$python_version" | cut -d. -f2)
    
    if [[ $major_version -lt 3 ]] || [[ $major_version -eq 3 && $minor_version -lt 9 ]]; then
        log_error "Python 3.9 or higher is required. Found: $python_version"
    fi
    
    log_info "Python version: $python_version ✓"
}

################################################################################
# Function: check_playwright_installed
# Verify Playwright Python package is installed
################################################################################
check_playwright_installed() {
    local python_cmd="python3"
    if ! command -v python3 &> /dev/null; then
        python_cmd="python"
    fi
    
    if ! $python_cmd -c "import playwright" 2>/dev/null; then
        log_error "Playwright Python package is not installed.

Install it with:
  pip install playwright

Or install all project dependencies:
  pip install -r requirements.txt"
    fi
    
    log_info "Playwright Python package is installed ✓"
}

################################################################################
# Function: check_playwright_browsers
# Verify Playwright browser binaries are installed
################################################################################
check_playwright_browsers() {
    local python_cmd="python3"
    if ! command -v python3 &> /dev/null; then
        python_cmd="python"
    fi
    
    # Check if playwright.sync_api is importable
    if ! $python_cmd -c "from playwright.sync_api import sync_playwright" 2>/dev/null; then
        log_error "Playwright sync_api is not available. Please reinstall Playwright:
  pip install --force-reinstall playwright"
    fi
    
    log_info "Playwright sync_api is available ✓"
    
    # Check for browser binaries
    local browsers_check
    browsers_check=$($python_cmd -c "
from playwright.sync_api import sync_playwright
import sys
try:
    with sync_playwright() as p:
        # Try to get browser, this will fail if not installed
        try:
            p.chromium.executable_path
            print('chromium', end='')
        except:
            pass
    sys.exit(0)
except Exception as e:
    sys.exit(1)
" 2>&1) || true
    
    if [[ -z "$browsers_check" ]]; then
        log_warn "Playwright browsers may not be installed"
        log_warn "Install them with: python -m playwright install"
        log_warn "Or install with dependencies: python -m playwright install --with-deps"
        echo ""
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Aborting. Please install Playwright browsers first."
        fi
    else
        log_info "Playwright browser binaries are available ✓"
    fi
}

################################################################################
# Function: check_dependencies
# Verify all required dependencies are installed
################################################################################
check_dependencies() {
    local python_cmd="python3"
    if ! command -v python3 &> /dev/null; then
        python_cmd="python"
    fi
    
    # Check for uvicorn
    if ! $python_cmd -c "import uvicorn" 2>/dev/null; then
        log_error "uvicorn is not installed. Install it with:
  pip install uvicorn[standard]

Or install all MCP server dependencies:
  pip install -r mcp_servers/playwright_mcp/requirements.txt"
    fi
    
    # Check for FastAPI
    if ! $python_cmd -c "import fastapi" 2>/dev/null; then
        log_error "FastAPI is not installed. Install it with:
  pip install fastapi

Or install all MCP server dependencies:
  pip install -r mcp_servers/playwright_mcp/requirements.txt"
    fi
    
    log_info "All required dependencies are installed ✓"
}

################################################################################
# Function: parse_arguments
# Parse command line arguments
################################################################################
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                PORT="$2"
                shift 2
                ;;
            --host)
                HOST="$2"
                shift 2
                ;;
            --no-reload)
                RELOAD_FLAG=""
                shift
                ;;
            --log-level)
                LOG_LEVEL="$2"
                shift 2
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown argument: $1

Use --help for usage information"
                ;;
        esac
    done
}

################################################################################
# Function: print_usage
# Display usage information
################################################################################
print_usage() {
    cat << EOF
Playwright MCP Server Startup Script

Usage:
  $0 [OPTIONS]

Options:
  --port PORT          Server port (default: 8001)
  --host HOST          Server host (default: 0.0.0.0)
  --no-reload          Disable auto-reload on file changes
  --log-level LEVEL    Logging level: debug|info|warning|error (default: info)
  -h, --help           Display this help message

Environment Variables:
  PLAYWRIGHT_MCP_ENABLED   Must be 'true' to start server (required)
  PLAYWRIGHT_MCP_PORT      Server port (default: 8001)
  BASE_URL                 Target application URL for testing
  HEADLESS                 Browser headless mode (default: true)
  LOG_LEVEL                Logging level (default: info)

Examples:
  # Start with default settings
  ./start_playwright_mcp.sh

  # Start on custom port
  ./start_playwright_mcp.sh --port 9001

  # Start without auto-reload
  ./start_playwright_mcp.sh --no-reload

Note: This server is for DEVELOPMENT ONLY, not CI/CD pipelines.
EOF
}

################################################################################
# Function: setup_signal_handlers
# Set up graceful shutdown on SIGINT/SIGTERM
################################################################################
setup_signal_handlers() {
    trap 'echo ""; log_info "Shutting down Playwright MCP server..."; exit 0' SIGINT SIGTERM
}

################################################################################
# Function: validate_server_module
# Verify the Playwright MCP server module exists
################################################################################
validate_server_module() {
    local mcp_module_path="${PROJECT_ROOT}/mcp_servers/playwright_mcp/main.py"
    
    if [[ ! -f "$mcp_module_path" ]]; then
        log_error "Playwright MCP server module not found at: $mcp_module_path

Please ensure the mcp_servers/playwright_mcp/main.py file exists."
    fi
    
    log_info "Playwright MCP server module found ✓"
}

################################################################################
# Function: display_startup_info
# Show server configuration and startup information
################################################################################
display_startup_info() {
    echo ""
    log_info "Server Configuration:"
    echo "  • Host: ${HOST}"
    echo "  • Port: ${PORT}"
    echo "  • Log Level: ${LOG_LEVEL}"
    echo "  • Auto-reload: $(if [[ -n "$RELOAD_FLAG" ]]; then echo "Enabled"; else echo "Disabled"; fi)"
    echo "  • Base URL: ${BASE_URL:-Not set}"
    echo "  • Headless Mode: ${HEADLESS:-true}"
    echo ""
    log_info "Starting Playwright MCP server..."
    log_info "Server will be available at: http://${HOST}:${PORT}"
    log_info "API documentation: http://${HOST}:${PORT}/docs"
    echo ""
    log_info "Press Ctrl+C to stop the server"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

################################################################################
# Function: start_server
# Start the uvicorn server
################################################################################
start_server() {
    # Change to project root for proper module resolution
    cd "$PROJECT_ROOT"
    
    local python_cmd="python3"
    if ! command -v python3 &> /dev/null; then
        python_cmd="python"
    fi
    
    # Build uvicorn command
    local uvicorn_cmd=(
        "$python_cmd" -m uvicorn
        "mcp_servers.playwright_mcp.main:app"
        --host "$HOST"
        --port "$PORT"
        --log-level "$LOG_LEVEL"
    )
    
    # Add reload flag if enabled
    if [[ -n "$RELOAD_FLAG" ]]; then
        uvicorn_cmd+=("$RELOAD_FLAG")
    fi
    
    # Execute uvicorn
    exec "${uvicorn_cmd[@]}"
}

################################################################################
# Main Execution
################################################################################
main() {
    # Parse command line arguments first
    parse_arguments "$@"
    
    # Display banner
    print_banner
    
    # Load environment variables
    load_environment
    
    # Check if server is enabled
    check_enabled_flag
    
    # Validate environment
    log_info "Validating environment..."
    check_python
    check_playwright_installed
    check_playwright_browsers
    check_dependencies
    validate_server_module
    
    log_info "All validations passed ✓"
    echo ""
    
    # Set up signal handlers for graceful shutdown
    setup_signal_handlers
    
    # Display startup information
    display_startup_info
    
    # Start the server
    start_server
}

# Run main function with all script arguments
main "$@"
