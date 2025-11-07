"""
Health Check Router for FastAPI MCP Server

This module provides health check endpoints for liveness and readiness probes
used in CI/CD pipelines, Kubernetes deployments, and monitoring systems.

The health endpoint is intentionally lightweight with minimal dependencies to
ensure it remains operational even during service degradation or dependency failures.

Usage:
    - CI/CD Healthcheck: curl -f http://localhost:8000/health || exit 1
    - Kubernetes Liveness: livenessProbe.httpGet.path: /health
    - Monitoring Systems: Poll /health endpoint for service availability
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse


# Initialize router with empty prefix (mounted at root level)
# Tags ensure proper grouping in OpenAPI/Swagger documentation
router = APIRouter(
    prefix="",
    tags=["health"],
    responses={
        200: {
            "description": "Service is healthy and operational",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "fastapi_mcp",
                        "timestamp": "2024-01-15T10:30:00.000000"
                    }
                }
            }
        }
    }
)


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Health Check Endpoint",
    description="""
    Returns the operational status of the FastAPI MCP server.
    
    This endpoint is designed for:
    - **CI/CD Pipelines**: Validate service startup before running tests
    - **Kubernetes Probes**: Liveness and readiness probe target
    - **Monitoring Systems**: Uptime and availability checks
    - **Load Balancers**: Health check for traffic routing decisions
    
    **Important**: This endpoint does NOT require authentication to ensure
    health checks succeed even when auth systems are experiencing issues.
    
    **Response Fields**:
    - `status`: Always "healthy" when service is responding
    - `service`: Service identifier for multi-service deployments
    - `timestamp`: UTC timestamp for clock drift detection and logging
    """,
    response_description="Service health status with timestamp"
)
async def health_check() -> Dict[str, Any]:
    """
    Perform health check and return service status.
    
    This endpoint performs a minimal health check to verify the service
    is running and capable of handling requests. It intentionally avoids
    checking external dependencies (databases, external APIs) to prevent
    cascading failures where health checks fail due to downstream issues.
    
    For deeper health checks including dependency validation, consider
    implementing a separate /health/ready endpoint.
    
    Returns:
        dict: Health status response containing:
            - status (str): "healthy" indicating service is operational
            - service (str): "fastapi_mcp" service identifier
            - timestamp (str): ISO 8601 formatted UTC timestamp
            
    Example Response:
        {
            "status": "healthy",
            "service": "fastapi_mcp",
            "timestamp": "2024-01-15T10:30:00.123456"
        }
    """
    # Generate current UTC timestamp in ISO 8601 format
    # Using utcnow() for consistency with CI/CD and monitoring systems
    current_timestamp = datetime.utcnow().isoformat()
    
    # Return minimal health status response
    # Status is always "healthy" if the endpoint is reachable
    # Service identifier helps in multi-service logging and monitoring
    # Timestamp enables clock drift detection and request correlation
    return {
        "status": "healthy",
        "service": "fastapi_mcp",
        "timestamp": current_timestamp
    }
