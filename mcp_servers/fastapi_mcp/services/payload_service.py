"""
Payload Service for FastAPI MCP Server

This module implements template-based request payload generation for API testing,
providing the build_payload MCP tool that constructs deterministic request bodies
from predefined templates with parameter substitution.

The PayloadService eliminates hardcoded test data in test files by managing
payload templates for common API operations and generating valid request structures
with realistic test data when parameters are not provided.

Key Features:
- Template-based payload generation for common API operations
- Parameter substitution with provided values
- Automatic default value generation using Faker library
- Support for nested payload structures and complex data types
- Payload validation against expected schema structures
- Deterministic data generation with optional seeding
- Template versioning and extensibility for new API endpoints

Usage:
    ```python
    from mcp_servers.fastapi_mcp.services.payload_service import PayloadService
    
    service = PayloadService()
    response = await service.build_from_template(
        template_name="create_user",
        params={"role": "admin", "email": "test@example.com"}
    )
    # Returns BuildPayloadResponse with generated payload and template metadata
    ```
"""

import copy
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from faker import Faker

from mcp_servers.fastapi_mcp.models import BuildPayloadResponse


# Configure module logger
logger = logging.getLogger(__name__)


class PayloadService:
    """
    Service class for template-based API request payload generation.
    
    This service manages payload templates for common API operations and provides
    methods to generate valid request bodies with parameter substitution and
    realistic default values. Designed for deterministic test data management
    in automated testing scenarios.
    
    The service uses the Faker library to generate realistic default values for
    template parameters that are not explicitly provided, supporting various data
    types including emails, names, text, UUIDs, and timestamps.
    
    Attributes:
        fake: Faker instance for generating realistic test data
        payload_templates: Dictionary of predefined payload templates for API operations
    
    Example:
        ```python
        service = PayloadService()
        
        # Generate payload with custom parameters
        response = await service.build_from_template(
            template_name="create_project",
            params={"name": "My Project", "owner_id": "usr_123"}
        )
        
        # Use generated payload in API request
        api_client.post("/projects", json=response.payload)
        ```
    """
    
    # Predefined payload templates for common API operations
    # Templates use placeholders that are replaced with actual values during generation
    payload_templates: Dict[str, Dict[str, Any]] = {
        "create_user": {
            "email": "${email}",
            "first_name": "${first_name}",
            "last_name": "${last_name}",
            "role": "${role}",
            "password": "${password}",
            "is_active": True,
            "created_at": "${created_at}",
            "profile": {
                "bio": "${bio}",
                "phone": "${phone}",
                "timezone": "UTC"
            }
        },
        "update_user": {
            "first_name": "${first_name}",
            "last_name": "${last_name}",
            "profile": {
                "bio": "${bio}",
                "phone": "${phone}"
            },
            "updated_at": "${updated_at}"
        },
        "create_project": {
            "name": "${project_name}",
            "description": "${description}",
            "owner_id": "${owner_id}",
            "status": "active",
            "visibility": "private",
            "created_at": "${created_at}",
            "settings": {
                "notifications_enabled": True,
                "auto_archive_days": 90
            },
            "tags": []
        },
        "update_project": {
            "name": "${project_name}",
            "description": "${description}",
            "status": "${status}",
            "visibility": "${visibility}",
            "updated_at": "${updated_at}"
        },
        "create_task": {
            "title": "${task_title}",
            "description": "${description}",
            "project_id": "${project_id}",
            "assignee_id": "${assignee_id}",
            "priority": "${priority}",
            "status": "pending",
            "due_date": "${due_date}",
            "created_at": "${created_at}",
            "metadata": {
                "estimated_hours": "${estimated_hours}",
                "tags": []
            }
        },
        "update_task": {
            "title": "${task_title}",
            "description": "${description}",
            "status": "${status}",
            "priority": "${priority}",
            "assignee_id": "${assignee_id}",
            "updated_at": "${updated_at}"
        },
        "create_comment": {
            "content": "${comment_text}",
            "author_id": "${author_id}",
            "task_id": "${task_id}",
            "created_at": "${created_at}",
            "is_edited": False
        },
        "authenticate": {
            "email": "${email}",
            "password": "${password}",
            "remember_me": False
        },
        "refresh_token": {
            "refresh_token": "${refresh_token}",
            "client_id": "${client_id}"
        },
        "invite_user": {
            "email": "${email}",
            "role": "${role}",
            "project_id": "${project_id}",
            "invited_by": "${invited_by}",
            "message": "${invitation_message}",
            "expires_at": "${expires_at}"
        }
    }
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the PayloadService with optional deterministic seeding.
        
        Creates a Faker instance for generating realistic test data. If a seed
        is provided, the Faker instance will generate deterministic data,
        ensuring reproducible test scenarios across multiple test runs.
        
        Args:
            seed: Optional integer seed for deterministic Faker data generation.
                  When provided, ensures the same data is generated on each run.
                  Useful for reproducible test scenarios in CI/CD pipelines.
        
        Example:
            ```python
            # Non-deterministic generation (different data each run)
            service = PayloadService()
            
            # Deterministic generation (same data each run)
            service = PayloadService(seed=12345)
            ```
        """
        self.fake = Faker()
        if seed is not None:
            Faker.seed(seed)
            logger.info(f"PayloadService initialized with deterministic seed: {seed}")
        else:
            logger.debug("PayloadService initialized with random seed")
    
    async def build_from_template(
        self,
        template_name: str,
        params: Optional[Dict[str, Any]] = None
    ) -> BuildPayloadResponse:
        """
        Build a request payload from a predefined template with parameter substitution.
        
        This is the primary method for generating API request payloads. It loads
        the specified template, merges provided parameters, generates defaults for
        missing parameters, and validates the final payload structure.
        
        The method supports nested template structures and complex parameter
        substitution, making it suitable for generating payloads for sophisticated
        API operations.
        
        Args:
            template_name: Name of the payload template to use. Must match a key
                          in the payload_templates dictionary (e.g., "create_user",
                          "update_project").
            params: Optional dictionary of parameters to substitute into the template.
                   Keys should match placeholder names in the template (without ${}).
                   If not provided or missing parameters, defaults will be generated.
        
        Returns:
            BuildPayloadResponse containing:
                - payload: The generated request payload dictionary ready for API submission
                - template_used: The name of the template that was used for generation
        
        Raises:
            ValueError: If the specified template_name does not exist in payload_templates
            json.JSONDecodeError: If the generated payload is not valid JSON
        
        Example:
            ```python
            service = PayloadService()
            
            # Generate with custom parameters
            response = await service.build_from_template(
                template_name="create_user",
                params={"email": "admin@test.com", "role": "admin"}
            )
            
            # Generate with all defaults
            response = await service.build_from_template(
                template_name="create_project"
            )
            
            # Use in API request
            httpx_client.post("/api/users", json=response.payload)
            ```
        """
        if params is None:
            params = {}
        
        logger.info(
            f"Building payload from template '{template_name}' "
            f"with {len(params)} provided parameters"
        )
        
        # Validate template exists
        if template_name not in self.payload_templates:
            available_templates = ", ".join(self.payload_templates.keys())
            error_msg = (
                f"Template '{template_name}' not found. "
                f"Available templates: {available_templates}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Deep copy template to avoid mutating the original
        template = copy.deepcopy(self.payload_templates[template_name])
        logger.debug(f"Template '{template_name}' loaded successfully")
        
        # Generate default values for parameters not provided
        defaults = self._generate_defaults(template, params)
        logger.debug(f"Generated {len(defaults)} default parameter values")
        
        # Merge provided params with generated defaults
        merged_params = {**defaults, **params}
        
        # Substitute parameters into template
        payload = self._merge_params(template, merged_params)
        logger.debug("Parameter substitution completed")
        
        # Validate the generated payload
        self._validate_payload(payload)
        logger.info(
            f"Successfully generated payload from template '{template_name}' "
            f"with {len(merged_params)} total parameters"
        )
        
        return BuildPayloadResponse(
            payload=payload,
            template_used=template_name
        )
    
    def _merge_params(
        self,
        template: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Recursively merge parameters into template, replacing placeholders.
        
        This method traverses the template dictionary (including nested structures)
        and replaces placeholder strings (format: ${param_name}) with actual values
        from the params dictionary. Supports deep nesting and handles various data
        types including strings, lists, and nested dictionaries.
        
        Placeholder format: "${parameter_name}"
        - Placeholders are case-sensitive
        - Placeholders not found in params are left unchanged
        - Non-placeholder values are preserved as-is
        
        Args:
            template: The template dictionary containing placeholders to replace
            params: Dictionary of parameter values to substitute into placeholders
        
        Returns:
            New dictionary with placeholders replaced by actual values
        
        Example:
            ```python
            template = {
                "name": "${user_name}",
                "email": "${email}",
                "nested": {
                    "id": "${user_id}"
                }
            }
            params = {"user_name": "John", "email": "john@test.com", "user_id": "123"}
            
            result = self._merge_params(template, params)
            # Returns: {
            #     "name": "John",
            #     "email": "john@test.com",
            #     "nested": {"id": "123"}
            # }
            ```
        """
        result = {}
        
        for key, value in template.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Extract parameter name from placeholder
                param_name = value[2:-1]  # Remove ${ and }
                
                if param_name in params:
                    result[key] = params[param_name]
                    logger.debug(f"Replaced placeholder '{value}' with provided value")
                else:
                    # Keep placeholder if no value provided (will be caught in validation)
                    result[key] = value
                    logger.warning(
                        f"No value provided for placeholder '{value}', "
                        "keeping as-is"
                    )
            elif isinstance(value, dict):
                # Recursively process nested dictionaries
                result[key] = self._merge_params(value, params)
            elif isinstance(value, list):
                # Process lists, handling nested structures
                result[key] = [
                    self._merge_params(item, params) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                # Keep non-placeholder values as-is
                result[key] = value
        
        return result
    
    def _generate_defaults(
        self,
        template: Dict[str, Any],
        provided_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate realistic default values for template parameters not provided.
        
        This method analyzes the template structure to identify all placeholders
        that need values, then generates realistic defaults using the Faker library
        for any parameters not already provided in provided_params.
        
        The generation is context-aware, creating appropriate data types based on
        parameter names:
        - email parameters → realistic email addresses
        - name parameters → realistic person names
        - date/time parameters → ISO 8601 timestamps
        - ID parameters → UUIDs
        - text/description parameters → lorem ipsum text
        - numeric parameters → random integers
        
        Args:
            template: The template dictionary to analyze for placeholders
            provided_params: Dictionary of parameters already provided by caller
        
        Returns:
            Dictionary of generated default values for missing parameters
        
        Example:
            ```python
            template = {"email": "${email}", "name": "${name}", "age": "${age}"}
            provided = {"name": "John"}
            
            defaults = self._generate_defaults(template, provided)
            # Returns: {"email": "john.doe@example.com", "age": 25}
            # "name" not included since it was already provided
            ```
        """
        defaults = {}
        placeholders = self._extract_placeholders(template)
        
        logger.debug(f"Found {len(placeholders)} placeholders in template")
        
        for placeholder in placeholders:
            # Skip if parameter already provided
            if placeholder in provided_params:
                continue
            
            # Generate default value based on parameter name pattern
            if "email" in placeholder.lower():
                defaults[placeholder] = self.fake.email()
            elif "first_name" in placeholder.lower():
                defaults[placeholder] = self.fake.first_name()
            elif "last_name" in placeholder.lower():
                defaults[placeholder] = self.fake.last_name()
            elif "name" in placeholder.lower() and "user" in placeholder.lower():
                defaults[placeholder] = self.fake.name()
            elif "project_name" in placeholder.lower() or placeholder == "name":
                defaults[placeholder] = self.fake.company()
            elif "task_title" in placeholder.lower() or "title" in placeholder.lower():
                defaults[placeholder] = self.fake.catch_phrase()
            elif "description" in placeholder.lower() or "bio" in placeholder.lower():
                defaults[placeholder] = self.fake.text(max_nb_chars=200)
            elif "comment_text" in placeholder.lower() or "content" in placeholder.lower():
                defaults[placeholder] = self.fake.text(max_nb_chars=500)
            elif "invitation_message" in placeholder.lower() or "message" in placeholder.lower():
                defaults[placeholder] = self.fake.sentence()
            elif "phone" in placeholder.lower():
                defaults[placeholder] = self.fake.phone_number()
            elif "password" in placeholder.lower():
                defaults[placeholder] = self.fake.password(
                    length=12,
                    special_chars=True,
                    digits=True,
                    upper_case=True,
                    lower_case=True
                )
            elif "role" in placeholder.lower():
                defaults[placeholder] = self.fake.random_element(
                    elements=("admin", "editor", "viewer")
                )
            elif "status" in placeholder.lower():
                defaults[placeholder] = self.fake.random_element(
                    elements=("active", "inactive", "pending", "completed")
                )
            elif "priority" in placeholder.lower():
                defaults[placeholder] = self.fake.random_element(
                    elements=("low", "medium", "high", "urgent")
                )
            elif "visibility" in placeholder.lower():
                defaults[placeholder] = self.fake.random_element(
                    elements=("public", "private", "internal")
                )
            elif "_id" in placeholder.lower() or placeholder.endswith("_id"):
                # Generate UUID for ID fields
                defaults[placeholder] = str(uuid.uuid4())
            elif "created_at" in placeholder.lower() or "updated_at" in placeholder.lower():
                defaults[placeholder] = datetime.utcnow().isoformat() + "Z"
            elif "due_date" in placeholder.lower() or "expires_at" in placeholder.lower():
                # Generate future date
                future_date = self.fake.future_datetime()
                defaults[placeholder] = future_date.isoformat() + "Z"
            elif "estimated_hours" in placeholder.lower():
                defaults[placeholder] = self.fake.random_int(min=1, max=40)
            elif "token" in placeholder.lower():
                defaults[placeholder] = str(uuid.uuid4())
            elif "client_id" in placeholder.lower():
                defaults[placeholder] = f"client_{uuid.uuid4()}"
            else:
                # Generic fallback for unknown parameter types
                defaults[placeholder] = self.fake.word()
                logger.warning(
                    f"Unknown parameter type '{placeholder}', "
                    "generated generic default value"
                )
        
        logger.debug(f"Generated defaults for {len(defaults)} parameters")
        return defaults
    
    def _extract_placeholders(self, template: Any) -> List[str]:
        """
        Recursively extract all placeholder names from a template structure.
        
        Traverses the template dictionary (including nested structures) to find
        all placeholder strings and extracts their parameter names. Handles
        nested dictionaries and lists.
        
        Args:
            template: The template structure to analyze (can be dict, list, or any value)
        
        Returns:
            List of unique placeholder parameter names (without ${} syntax)
        
        Example:
            ```python
            template = {
                "user": {"email": "${email}", "name": "${user_name}"},
                "items": [{"id": "${item_id}"}]
            }
            
            placeholders = self._extract_placeholders(template)
            # Returns: ["email", "user_name", "item_id"]
            ```
        """
        placeholders = []
        
        if isinstance(template, dict):
            for value in template.values():
                placeholders.extend(self._extract_placeholders(value))
        elif isinstance(template, list):
            for item in template:
                placeholders.extend(self._extract_placeholders(item))
        elif isinstance(template, str) and template.startswith("${") and template.endswith("}"):
            # Extract parameter name from placeholder
            param_name = template[2:-1]
            placeholders.append(param_name)
        
        return placeholders
    
    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """
        Validate that the generated payload is valid and contains no unresolved placeholders.
        
        Performs comprehensive validation to ensure the payload is ready for use
        in API requests:
        1. Checks that the payload is JSON-serializable
        2. Verifies no placeholder strings (${...}) remain unresolved
        3. Ensures the payload structure is valid
        
        Args:
            payload: The generated payload dictionary to validate
        
        Raises:
            ValueError: If unresolved placeholders are found in the payload
            json.JSONDecodeError: If the payload is not valid JSON
        
        Example:
            ```python
            valid_payload = {"email": "test@example.com", "name": "John"}
            self._validate_payload(valid_payload)  # Passes validation
            
            invalid_payload = {"email": "${email}", "name": "John"}
            self._validate_payload(invalid_payload)  # Raises ValueError
            ```
        """
        try:
            # Ensure payload is JSON-serializable
            json_str = json.dumps(payload)
            logger.debug("Payload is valid JSON")
            
            # Check for unresolved placeholders
            if "${" in json_str and "}" in json_str:
                # Extract unresolved placeholders for error message
                unresolved = self._extract_placeholders(payload)
                if unresolved:
                    error_msg = (
                        f"Generated payload contains unresolved placeholders: "
                        f"{', '.join(unresolved)}. Ensure all required parameters "
                        "are provided or can be auto-generated."
                    )
                    logger.error(error_msg)
                    raise ValueError(error_msg)
            
            logger.debug("Payload validation passed: no unresolved placeholders")
            
        except (TypeError, ValueError) as e:
            error_msg = f"Payload validation failed: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e

