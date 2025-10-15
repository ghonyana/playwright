@echo off
REM ==============================================================================
REM FastAPI MCP Server Startup Script (Windows)
REM ==============================================================================
REM Purpose: Start FastAPI MCP server for deterministic test data management
REM Environment: Development and CI/CD compatible
REM Port: 8001 (default) - Configurable via command-line argument
REM ==============================================================================

setlocal enabledelayedexpansion

REM ==============================================================================
REM Configuration
REM ==============================================================================

REM Default server configuration
set DEFAULT_HOST=0.0.0.0
set DEFAULT_PORT=8001
set DEFAULT_LOG_LEVEL=info
set DEFAULT_RELOAD=true

REM Parse command-line arguments
set PRODUCTION_MODE=false
set CUSTOM_PORT=
for %%A in (%*) do (
    set ARG=%%A
    if /i "!ARG!"=="/production" (
        set PRODUCTION_MODE=true
    )
    if "!ARG:~0,6!"=="/port:" (
        set CUSTOM_PORT=!ARG:~6!
    )
)

REM ==============================================================================
REM Display Startup Banner
REM ==============================================================================

echo.
echo ========================================================================
echo    FastAPI MCP Server - Test Data Management
echo ========================================================================
echo.
echo    Provides deterministic test data management for pytest automation:
echo      - seed_user:      Create test users with specific roles
echo      - build_payload:  Generate API request payloads
echo      - reset_env:      Reset test environment state
echo      - query_state:    Query environment resources
echo.
if "%PRODUCTION_MODE%"=="true" (
    echo    Mode: PRODUCTION ^(no auto-reload^)
) else (
    echo    Mode: DEVELOPMENT ^(auto-reload enabled^)
)
echo.
echo ========================================================================
echo.

REM ==============================================================================
REM Load Environment Variables from .env File
REM ==============================================================================

echo [INFO] Loading environment configuration...

REM Find .env file (check current directory and repository root)
set ENV_FILE=
if exist ".env" (
    set ENV_FILE=.env
) else if exist "..\..\..\.env" (
    set ENV_FILE=..\..\..\.env
) else if exist "%~dp0..\..\..\.env" (
    set ENV_FILE=%~dp0..\..\..\.env
)

if not defined ENV_FILE (
    echo [WARNING] .env file not found. Using default configuration.
    echo [INFO] Create .env file in repository root to customize settings.
    echo [INFO] Copy .env.example to .env and configure required variables.
) else (
    echo [INFO] Found .env file: %ENV_FILE%
    
    REM Parse .env file and set environment variables
    for /f "usebackq tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        set LINE=%%A
        REM Skip comments and empty lines
        if not "!LINE:~0,1!"=="#" (
            if not "%%A"=="" (
                if not "%%B"=="" (
                    REM Remove quotes from value
                    set VALUE=%%B
                    set VALUE=!VALUE:"=!
                    set %%A=!VALUE!
                )
            )
        )
    )
    echo [SUCCESS] Environment variables loaded
)

REM ==============================================================================
REM Validate Required Environment Variables
REM ==============================================================================

echo [INFO] Validating required configuration...

set CONFIG_ERRORS=0

REM Check AUTH_SECRET_KEY
if not defined AUTH_SECRET_KEY (
    echo [ERROR] AUTH_SECRET_KEY is not set.
    echo [INFO] Generate a secure key with: python -c "import secrets; print(secrets.token_hex(32))"
    set CONFIG_ERRORS=1
) else (
    REM Check minimum key length (should be at least 32 characters)
    set KEY=%AUTH_SECRET_KEY%
    set KEY_LEN=0
    for /l %%i in (0,1,100) do if not "!KEY:~%%i,1!"=="" set /a KEY_LEN=%%i+1
    if !KEY_LEN! lss 32 (
        echo [WARNING] AUTH_SECRET_KEY should be at least 32 characters long.
        echo [INFO] Current length: !KEY_LEN! characters
    ) else (
        echo [SUCCESS] AUTH_SECRET_KEY is configured
    )
)

REM Check APP_BASE_URL
if not defined APP_BASE_URL (
    echo [WARNING] APP_BASE_URL is not set.
    set APP_BASE_URL=http://localhost:3000
    echo [INFO] Using default: %APP_BASE_URL%
) else (
    echo [SUCCESS] APP_BASE_URL: %APP_BASE_URL%
)

REM Check APP_API_URL
if not defined APP_API_URL (
    echo [WARNING] APP_API_URL is not set.
    set APP_API_URL=http://localhost:3000/api
    echo [INFO] Using default: %APP_API_URL%
) else (
    echo [SUCCESS] APP_API_URL: %APP_API_URL%
)

REM Exit if critical configuration errors
if %CONFIG_ERRORS% gtr 0 (
    echo.
    echo [ERROR] Configuration validation failed.
    echo [INFO] Please set required environment variables in .env file.
    echo.
    echo Required variables:
    echo   - AUTH_SECRET_KEY: JWT signing secret (min 32 chars)
    echo   - APP_BASE_URL: Base URL of application under test
    echo   - APP_API_URL: Base URL of REST API
    echo.
    echo Optional variables:
    echo   - DATABASE_URL: Database connection string
    echo   - APP_ADMIN_EMAIL: Admin user email
    echo   - APP_ADMIN_PASSWORD: Admin user password
    echo   - FASTAPI_MCP_PORT: Custom port (default: 8001)
    echo   - LOG_LEVEL: Logging level (default: info)
    echo.
    exit /b 1
)

REM ==============================================================================
REM Validate Python Installation
REM ==============================================================================

echo [INFO] Validating Python installation...

where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo.
    echo Please install Python 3.9 or higher:
    echo     https://www.python.org/downloads/
    echo.
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set PYTHON_VERSION=%%V
echo [INFO] Python version: %PYTHON_VERSION%

REM Validate Python version is 3.9+
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% lss 3 (
    echo [ERROR] Python 3.9+ required, found: %PYTHON_VERSION%
    exit /b 1
)

if %MAJOR% equ 3 (
    if %MINOR% lss 9 (
        echo [ERROR] Python 3.9+ required, found: %PYTHON_VERSION%
        exit /b 1
    )
)

echo [SUCCESS] Python version is compatible

REM ==============================================================================
REM Validate uvicorn Installation
REM ==============================================================================

echo [INFO] Validating uvicorn installation...

python -c "import uvicorn" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] uvicorn is not installed.
    echo.
    echo Please install server dependencies:
    echo     pip install uvicorn fastapi
    echo.
    echo Or install from requirements file:
    echo     pip install -r mcp_servers\fastapi_mcp\requirements.txt
    echo.
    exit /b 1
)

echo [SUCCESS] uvicorn is installed

REM ==============================================================================
REM Validate FastAPI Installation
REM ==============================================================================

echo [INFO] Validating FastAPI installation...

python -c "import fastapi" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] FastAPI is not installed.
    echo.
    echo Please install server dependencies:
    echo     pip install -r mcp_servers\fastapi_mcp\requirements.txt
    echo.
    exit /b 1
)

echo [SUCCESS] FastAPI is installed

REM ==============================================================================
REM Validate pydantic Installation
REM ==============================================================================

echo [INFO] Validating pydantic installation...

python -c "import pydantic" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] pydantic is not installed.
    echo.
    echo Please install server dependencies:
    echo     pip install -r mcp_servers\fastapi_mcp\requirements.txt
    echo.
    exit /b 1
)

echo [SUCCESS] pydantic is installed

REM ==============================================================================
REM Check Optional Dependencies
REM ==============================================================================

echo [INFO] Checking optional dependencies...

REM Check SQLAlchemy (for database support)
python -c "import sqlalchemy" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] SQLAlchemy not installed (database features disabled)
) else (
    echo [SUCCESS] SQLAlchemy is installed (database features available)
)

REM ==============================================================================
REM Determine Server Port
REM ==============================================================================

if defined CUSTOM_PORT (
    set SERVER_PORT=%CUSTOM_PORT%
    echo [INFO] Using custom port from command-line: %SERVER_PORT%
) else if defined FASTAPI_MCP_PORT (
    set SERVER_PORT=%FASTAPI_MCP_PORT%
    echo [INFO] Using port from environment: %SERVER_PORT%
) else (
    set SERVER_PORT=%DEFAULT_PORT%
    echo [INFO] Using default port: %SERVER_PORT%
)

REM ==============================================================================
REM Determine Log Level
REM ==============================================================================

if defined LOG_LEVEL (
    set SERVER_LOG_LEVEL=%LOG_LEVEL%
) else (
    set SERVER_LOG_LEVEL=%DEFAULT_LOG_LEVEL%
)

echo [INFO] Log level: %SERVER_LOG_LEVEL%

REM ==============================================================================
REM Determine Reload Setting
REM ==============================================================================

if "%PRODUCTION_MODE%"=="true" (
    set SERVER_RELOAD=false
    echo [INFO] Auto-reload: DISABLED (production mode)
) else (
    if defined RELOAD (
        set SERVER_RELOAD=%RELOAD%
    ) else (
        set SERVER_RELOAD=%DEFAULT_RELOAD%
    )
    echo [INFO] Auto-reload: ENABLED (development mode)
)

REM ==============================================================================
REM Change to FastAPI MCP Directory
REM ==============================================================================

echo [INFO] Navigating to FastAPI MCP server directory...

REM Determine the script directory
set SCRIPT_DIR=%~dp0

REM Navigate to fastapi_mcp directory (relative to script location)
pushd "%SCRIPT_DIR%..\fastapi_mcp" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Could not find fastapi_mcp directory.
    echo.
    echo Expected location: %SCRIPT_DIR%..\fastapi_mcp
    echo.
    echo Please ensure the directory structure is correct:
    echo     mcp_servers\
    echo       fastapi_mcp\
    echo         main.py
    echo       scripts\
    echo         start_fastapi_mcp.bat
    echo.
    exit /b 1
)

echo [SUCCESS] Changed to directory: %CD%

REM Verify main.py exists
if not exist "main.py" (
    echo [ERROR] main.py not found in current directory.
    echo.
    echo Current directory: %CD%
    echo.
    echo Please ensure main.py exists in mcp_servers\fastapi_mcp\
    echo.
    popd
    exit /b 1
)

echo [SUCCESS] Found main.py

REM ==============================================================================
REM Display Server Configuration Summary
REM ==============================================================================

echo.
echo ========================================================================
echo    Server Configuration
echo ========================================================================
echo    Host:          %DEFAULT_HOST%
echo    Port:          %SERVER_PORT%
echo    Log Level:     %SERVER_LOG_LEVEL%
echo    Reload:        %SERVER_RELOAD%
echo    Base URL:      %APP_BASE_URL%
echo    API URL:       %APP_API_URL%
if defined DATABASE_URL (
    echo    Database:      Configured
) else (
    echo    Database:      In-memory (no persistence)
)
echo ========================================================================
echo.
echo    Server URL:    http://%DEFAULT_HOST%:%SERVER_PORT%
echo    Documentation: http://%DEFAULT_HOST%:%SERVER_PORT%/docs
echo    Health Check:  http://%DEFAULT_HOST%:%SERVER_PORT%/health
echo ========================================================================
echo.

REM ==============================================================================
REM Start FastAPI MCP Server
REM ==============================================================================

echo [INFO] Starting FastAPI MCP Server...
echo [INFO] Press Ctrl+C to stop the server
echo.

REM Build uvicorn command based on reload setting
if "%SERVER_RELOAD%"=="true" (
    python -m uvicorn main:app --host %DEFAULT_HOST% --port %SERVER_PORT% --log-level %SERVER_LOG_LEVEL% --reload
) else (
    python -m uvicorn main:app --host %DEFAULT_HOST% --port %SERVER_PORT% --log-level %SERVER_LOG_LEVEL%
)

REM Capture exit code
set EXIT_CODE=%ERRORLEVEL%

REM Return to original directory
popd

REM ==============================================================================
REM Handle Server Exit
REM ==============================================================================

if %EXIT_CODE% neq 0 (
    echo.
    echo [ERROR] FastAPI MCP Server exited with error code: %EXIT_CODE%
    echo.
    echo Common issues:
    echo   - Port %SERVER_PORT% is already in use
    echo   - Missing dependencies (run: pip install -r mcp_servers\fastapi_mcp\requirements.txt)
    echo   - Configuration errors (check AUTH_SECRET_KEY, APP_BASE_URL, APP_API_URL)
    echo   - Database connection issues (check DATABASE_URL if configured)
    echo.
    echo Check the error messages above for details.
    echo.
    exit /b %EXIT_CODE%
)

echo.
echo [INFO] FastAPI MCP Server stopped gracefully.
echo.

exit /b 0
