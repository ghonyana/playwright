@echo off
REM ==============================================================================
REM Playwright MCP Server Startup Script (Windows)
REM ==============================================================================
REM Purpose: Start Playwright MCP server for LLM-driven browser exploration
REM Environment: DEVELOPMENT ONLY - Not intended for CI/CD pipelines
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

REM Custom port from command-line argument
set CUSTOM_PORT=
for %%A in (%*) do (
    set ARG=%%A
    if "!ARG:~0,6!"=="/port:" (
        set CUSTOM_PORT=!ARG:~6!
    )
)

REM ==============================================================================
REM Display Development Warning
REM ==============================================================================

echo.
echo ========================================================================
echo    Playwright MCP Server - DEVELOPMENT ONLY
echo ========================================================================
echo.
echo    LLM Exploration Mode - Not for CI/CD
echo.
echo    This server enables LLM agents to control browsers for:
echo      - Exploratory testing
echo      - Test scenario discovery
echo      - Automated Gherkin generation
echo.
echo    WARNING: This service should NOT run in production or CI pipelines
echo             Use FastAPI MCP server for CI/CD test data management
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
)

REM ==============================================================================
REM Check PLAYWRIGHT_MCP_ENABLED Flag
REM ==============================================================================

echo [INFO] Checking Playwright MCP enabled status...

if not defined PLAYWRIGHT_MCP_ENABLED (
    echo.
    echo [ERROR] Playwright MCP Server is not enabled.
    echo.
    echo To enable LLM-driven browser exploration, add to your .env file:
    echo.
    echo     PLAYWRIGHT_MCP_ENABLED=true
    echo.
    echo This server is for development and exploration only.
    echo For CI/CD test data management, use the FastAPI MCP server instead.
    echo.
    exit /b 1
)

if /i not "%PLAYWRIGHT_MCP_ENABLED%"=="true" (
    if /i not "%PLAYWRIGHT_MCP_ENABLED%"=="1" (
        echo.
        echo [ERROR] Playwright MCP Server is disabled.
        echo.
        echo Current setting: PLAYWRIGHT_MCP_ENABLED=%PLAYWRIGHT_MCP_ENABLED%
        echo.
        echo To enable, set in your .env file:
        echo     PLAYWRIGHT_MCP_ENABLED=true
        echo.
        exit /b 1
    )
)

echo [SUCCESS] Playwright MCP is enabled

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

REM ==============================================================================
REM Validate Playwright Installation
REM ==============================================================================

echo [INFO] Validating Playwright installation...

python -c "import playwright" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Playwright is not installed.
    echo.
    echo Please install Playwright:
    echo     pip install playwright
    echo.
    exit /b 1
)

echo [SUCCESS] Playwright Python module is installed

REM ==============================================================================
REM Check Playwright Browser Binaries
REM ==============================================================================

echo [INFO] Checking Playwright browser binaries...

set PLAYWRIGHT_CACHE=%USERPROFILE%\AppData\Local\ms-playwright

if not exist "%PLAYWRIGHT_CACHE%" (
    echo [WARNING] Playwright browsers cache not found at:
    echo           %PLAYWRIGHT_CACHE%
    echo.
    echo [ACTION REQUIRED] Install Playwright browsers:
    echo.
    echo     python -m playwright install
    echo.
    echo For CI/CD, use:
    echo     python -m playwright install --with-deps
    echo.
    exit /b 1
)

REM Check for Chromium installation (primary browser for testing)
set CHROMIUM_FOUND=0
for /f %%F in ('dir /b "%PLAYWRIGHT_CACHE%" 2^>nul') do (
    echo %%F | findstr /i "chromium" >nul
    if !ERRORLEVEL! equ 0 set CHROMIUM_FOUND=1
)

if %CHROMIUM_FOUND% equ 0 (
    echo [WARNING] Chromium browser not found in cache.
    echo.
    echo [ACTION REQUIRED] Install browsers:
    echo     python -m playwright install chromium
    echo.
    echo For all browsers (chromium, firefox, webkit):
    echo     python -m playwright install
    echo.
    exit /b 1
)

echo [SUCCESS] Playwright browsers are installed

REM ==============================================================================
REM Validate playwright.sync_api Module
REM ==============================================================================

echo [INFO] Validating Playwright sync API...

python -c "from playwright.sync_api import sync_playwright" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Playwright sync_api module is not available.
    echo.
    echo This may indicate a corrupted installation.
    echo Reinstall Playwright:
    echo     pip install --force-reinstall playwright
    echo     python -m playwright install
    echo.
    exit /b 1
)

echo [SUCCESS] Playwright sync API is available

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
    echo     pip install -r mcp_servers\playwright_mcp\requirements.txt
    echo.
    exit /b 1
)

echo [SUCCESS] uvicorn is installed

REM ==============================================================================
REM Determine Server Port
REM ==============================================================================

if defined CUSTOM_PORT (
    set SERVER_PORT=%CUSTOM_PORT%
    echo [INFO] Using custom port from command-line: %SERVER_PORT%
) else if defined PLAYWRIGHT_MCP_PORT (
    set SERVER_PORT=%PLAYWRIGHT_MCP_PORT%
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
REM Set Additional Environment Variables
REM ==============================================================================

REM Set BASE_URL if not already set
if not defined BASE_URL (
    set BASE_URL=http://localhost:3000
    echo [INFO] BASE_URL not set, using default: %BASE_URL%
)

REM Set HEADLESS mode if not already set
if not defined HEADLESS (
    set HEADLESS=false
    echo [INFO] HEADLESS not set, using default: %HEADLESS% (visible browser)
)

echo [INFO] Base URL: %BASE_URL%
echo [INFO] Headless mode: %HEADLESS%

REM ==============================================================================
REM Change to Playwright MCP Directory
REM ==============================================================================

echo [INFO] Navigating to Playwright MCP server directory...

REM Determine the script directory
set SCRIPT_DIR=%~dp0

REM Navigate to playwright_mcp directory (relative to script location)
pushd "%SCRIPT_DIR%..\playwright_mcp" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Could not find playwright_mcp directory.
    echo.
    echo Expected location: %SCRIPT_DIR%..\playwright_mcp
    echo.
    echo Please ensure the directory structure is correct:
    echo     mcp_servers\
    echo       playwright_mcp\
    echo         main.py
    echo       scripts\
    echo         start_playwright_mcp.bat
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
    echo Please ensure main.py exists in mcp_servers\playwright_mcp\
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
echo    Base URL:      %BASE_URL%
echo    Headless:      %HEADLESS%
echo    Reload:        Enabled (development mode)
echo ========================================================================
echo.

REM ==============================================================================
REM Start Playwright MCP Server
REM ==============================================================================

echo [INFO] Starting Playwright MCP Server...
echo [INFO] Press Ctrl+C to stop the server
echo.

REM Start uvicorn with reload enabled for development
python -m uvicorn main:app --host %DEFAULT_HOST% --port %SERVER_PORT% --log-level %SERVER_LOG_LEVEL% --reload

REM Capture exit code
set EXIT_CODE=%ERRORLEVEL%

REM Return to original directory
popd

REM ==============================================================================
REM Handle Server Exit
REM ==============================================================================

if %EXIT_CODE% neq 0 (
    echo.
    echo [ERROR] Playwright MCP Server exited with error code: %EXIT_CODE%
    echo.
    echo Common issues:
    echo   - Port %SERVER_PORT% is already in use
    echo   - Missing dependencies (run: pip install -r mcp_servers\playwright_mcp\requirements.txt)
    echo   - Configuration errors in main.py
    echo.
    echo Check the error messages above for details.
    echo.
    exit /b %EXIT_CODE%
)

echo.
echo [INFO] Playwright MCP Server stopped gracefully.
echo.

exit /b 0
