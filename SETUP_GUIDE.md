# Test Automation Framework - Setup Guide

## Infrastructure Setup Status

This document describes the infrastructure setup performed by the setup agent to enable test execution.

## Created Infrastructure Files

### 1. FastAPI MCP Server Main Entry Point
**File**: `mcp_servers/fastapi_mcp/main.py`
- FastAPI application entry point for Model Context Protocol server
- Provides deterministic test data management tools
- Runs on port 8001 by default

### 2. FastAPI MCP Server Tools Router
**File**: `mcp_servers/fastapi_mcp/routers/tools.py`
- Implements MCP tool endpoints: seed_user, build_payload, reset_env, query_state
- Handles test data creation and environment management
- Integrates with authentication and service layers

### 3. Environment Configuration
**File**: `.env`
- Local development environment variables
- Configures application URLs, MCP endpoints, and test settings
- **Note**: This file is .gitignored and should not be committed

### 4. FastAPI MCP Config Update
**File**: `mcp_servers/fastapi_mcp/config.py` (modified)
- Changed default port from 8000 to 8001 to avoid conflicts with sample_app API
- Sample app runs on port 5000, its API on port 5000/api/v1

## Starting the Infrastructure

### Prerequisites
- Python 3.12.3 (installed and active in venv)
- All dependencies installed (pytest, playwright, fastapi, httpx, etc.)
- Virtual environment activated: `source venv/bin/activate`

### Option 1: Manual Startup (Recommended for Development)

#### Terminal 1: Start Sample Application (Target App)
```bash
cd /tmp/blitzy/playwright/blitzyb243c5b13
source venv/bin/activate
export PYTHONPATH=$PWD:$PYTHONPATH
python sample_app/app.py
```

Sample app will start on: http://localhost:5000
- Web UI: http://localhost:5000/login
- API: http://localhost:5000/api/v1

#### Terminal 2: Start FastAPI MCP Server
```bash
cd /tmp/blitzy/playwright/blitzyb243c5b13
source venv/bin/activate
export PYTHONPATH=$PWD:$PYTHONPATH
python mcp_servers/fastapi_mcp/main.py
```

MCP server will start on: http://localhost:8001
- API Docs: http://localhost:8001/docs
- MCP Tools: http://localhost:8001/tools/*

#### Terminal 3: Run Tests
```bash
cd /tmp/blitzy/playwright/blitzyb243c5b13
source venv/bin/activate
export PYTHONPATH=$PWD:$PYTHONPATH

# Run all tests
pytest tests/

# Run specific test categories
pytest tests/ui/              # UI tests only
pytest tests/api/             # API tests only
pytest tests/features/        # BDD tests only

# Run with Allure reporting
pytest tests/ --alluredir=allure-results
allure serve allure-results
```

### Option 2: Background Startup (For CI/CD-like Testing)

```bash
cd /tmp/blitzy/playwright/blitzyb243c5b13
source venv/bin/activate
export PYTHONPATH=$PWD:$PYTHONPATH

# Start sample app in background
python sample_app/app.py > logs/sample_app.log 2>&1 &
SAMPLE_APP_PID=$!

# Start MCP server in background
python mcp_servers/fastapi_mcp/main.py > logs/mcp_server.log 2>&1 &
MCP_SERVER_PID=$!

# Wait for servers to start
sleep 3

# Run tests
pytest tests/

# Cleanup
kill $SAMPLE_APP_PID $MCP_SERVER_PID
```

## Environment Variables

Key environment variables configured in `.env`:

### Application URLs
- `BASE_URL=http://localhost:5000` - Web UI base URL
- `API_BASE_URL=http://localhost:5000/api/v1` - REST API base URL

### FastAPI MCP Server
- `FASTAPI_MCP_URL=http://localhost:8001` - MCP server endpoint
- `FASTAPI_MCP_TOKEN=<generated-token>` - Authentication token
- `AUTH_SECRET_KEY=<generated-secret>` - JWT signing key
- `APP_BASE_URL=http://localhost:5000` - Target app URL (for MCP server)
- `APP_API_URL=http://localhost:5000/api/v1` - Target API URL (for MCP server)

### Playwright Configuration
- `HEADLESS=true` - Run browser in headless mode
- `BROWSER=chromium` - Default browser engine
- `TIMEOUT=30000` - Default operation timeout (ms)

## Verification

### Verify Sample App
```bash
curl http://localhost:5000/health
# Expected: {"status": "healthy"}
```

### Verify MCP Server
```bash
curl http://localhost:8001/health
# Expected: {"status": "healthy"}
```

### Verify Tests Can Collect
```bash
pytest --collect-only tests/
# Should list all discovered tests without errors
```

## Test Default Users (Sample App)

The sample app comes with pre-configured test users:
- **Admin**: admin@example.com / admin123
- **Customer**: customer@example.com / customer123
- **Moderator**: moderator@example.com / mod123

## Known Issues and Limitations

### Tests Blocked by Infrastructure (Before Setup)
**Issue**: Validation agent reported tests blocked due to missing MCP server
**Resolution**: Created `main.py` and `tools.py` files, MCP server now operational

### FastAPI Deprecation Warnings
**Issue**: FastAPI shows deprecation warnings for `@app.on_event()` decorators
**Impact**: Cosmetic only, does not affect functionality
**Future**: Will be updated to use lifespan event handlers in future iterations

### Module Import Paths
**Important**: Always set `PYTHONPATH` to project root before running servers or tests:
```bash
export PYTHONPATH=/tmp/blitzy/playwright/blitzyb243c5b13:$PYTHONPATH
```

## Next Steps

1. **Validation Agent**: Previously fixed critical BDD step definition mismatch
2. **Setup Agent** (Current): Created missing infrastructure files, verified startup
3. **Future Agents**: Will implement remaining features and fix any code-level issues

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Test Execution                          │
│                   (pytest + Playwright)                     │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
      ┌───────────▼──────────┐  ┌────────▼──────────────┐
      │   Sample App (Flask)  │  │  FastAPI MCP Server   │
      │   Port: 5000          │  │  Port: 8001           │
      │                       │  │                       │
      │  • Web UI             │  │  • seed_user          │
      │  • REST API           │  │  • build_payload      │
      │  • Mock Users         │  │  • reset_env          │
      │  • Session Auth       │  │  • query_state        │
      └───────────────────────┘  └───────────────────────┘
```

## Troubleshooting

### Port Already in Use
```bash
# Find process using port
lsof -i :5000
lsof -i :8001

# Kill process
kill -9 <PID>
```

### Module Not Found Errors
```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/tmp/blitzy/playwright/blitzyb243c5b13:$PYTHONPATH

# Verify Python can import modules
python -c "import mcp_servers.fastapi_mcp.main"
python -c "import sample_app.app"
```

### Database Errors (MCP Server)
```bash
# Remove test database and restart
rm -f test_data.db
python mcp_servers/fastapi_mcp/main.py
```

## Summary

✅ **Infrastructure Setup Complete**
- FastAPI MCP server operational on port 8001
- Sample application operational on port 5000
- Environment configuration file created
- Both services verified to start successfully
- Ready for test execution

🔧 **Configuration Status**
- All dependencies installed correctly
- Python 3.12.3 virtual environment active
- Environment variables configured
- Module import paths resolved

📋 **Ready for Testing**
- pytest can collect all tests
- Infrastructure services functional
- Test data management available via MCP server
- Sample app provides testing target
