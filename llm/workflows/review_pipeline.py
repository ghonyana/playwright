"""
Human Review Workflow Pipeline for LLM-Generated Gherkin Scenarios

This module implements a comprehensive human-in-the-loop review process for LLM-generated
test scenarios, ensuring business alignment and quality control before scenarios enter
the test suite. The pipeline automates Git branch creation, GitHub Pull Request submission,
review tracking, and automatic step definition stub generation upon approval.

Key Features:
- Automatic Git branch creation for LLM-generated scenarios
- GitHub Pull Request submission with comprehensive review checklist
- LLM-powered edge case suggestion for reviewers
- Review status tracking and metadata persistence
- Automatic step definition stub generation on PR approval
- Support for both local Git and GitHub remote operations

Workflow:
    1. LLM generates Gherkin scenario from exploration session
    2. submit_for_review() creates feature branch and commits scenario
    3. LLM analyzes scenario and suggests edge cases
    4. GitHub PR created with review checklist and edge case suggestions
    5. Human reviewer validates business logic, technical quality, and coverage
    6. Upon PR approval, generate_step_stubs() creates implementation templates
    7. Developers implement step definitions with page objects and MCP tools

Environment Variables:
    GITHUB_TOKEN: GitHub API token for Pull Request creation (optional for local-only)
    GITHUB_REPOSITORY_OWNER: Repository owner name (e.g., "myorg")
    GITHUB_REPOSITORY: Repository name (e.g., "playwright")

Usage Example:
    >>> from llm.workflows.review_pipeline import submit_for_review
    >>> 
    >>> # Submit LLM-generated scenario for review
    >>> feature_file = "tests/features/generated/login_scenario.feature"
    >>> pr_url = submit_for_review(feature_file)
    >>> print(f"Review PR: {pr_url}")
    >>> 
    >>> # After PR approval, generate step stubs
    >>> from llm.workflows.review_pipeline import generate_step_stubs
    >>> stubs_file = generate_step_stubs(feature_file)
    >>> print(f"Step definitions template: {stubs_file}")

Integration Points:
    - llm/client.py: Uses get_llm_client() for edge case suggestions
    - pytest-bdd: Parses feature files for step stub generation
    - Git: Local branch creation, commits, and remote push
    - GitHub API: Pull Request creation and label management
    - File system: Metadata persistence in tests/features/generated/.metadata/
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import httpx

from llm.client import get_llm_client


@dataclass
class ReviewMetadata:
    """
    Metadata container for LLM-generated scenario review tracking.
    
    This dataclass stores all relevant information about a generated scenario's lifecycle,
    from initial generation through human review to final approval. Metadata is persisted
    to disk as JSON for status tracking and audit trail purposes.
    
    Attributes:
        feature_file: Path to the generated .feature file (relative to repository root)
        generation_date: ISO 8601 timestamp of scenario generation
        llm_provider: LLM provider used for generation ('ollama' or 'openai')
        llm_model: Specific model used (e.g., 'llama2', 'gpt-4')
        objective: Human-readable description of test objective
        status: Current review status - one of:
            - 'DRAFT': Initial generation, not yet submitted
            - 'PENDING_REVIEW': PR created, awaiting human review
            - 'APPROVED': PR merged, ready for implementation
            - 'REJECTED': PR closed without merge, needs revision
        reviewer: GitHub username of reviewer (populated on review completion)
        review_date: ISO 8601 timestamp of review completion
        pr_url: GitHub Pull Request URL for tracking
        branch_name: Git feature branch name
    
    Usage:
        >>> metadata = ReviewMetadata(
        ...     feature_file="tests/features/login.feature",
        ...     generation_date=datetime.utcnow().isoformat(),
        ...     llm_provider="ollama",
        ...     llm_model="llama2",
        ...     objective="Test user login with valid credentials",
        ...     status="DRAFT"
        ... )
        >>> print(metadata.status)
        'DRAFT'
    """
    feature_file: str
    generation_date: str
    llm_provider: str
    llm_model: str
    objective: str
    status: str  # DRAFT, PENDING_REVIEW, APPROVED, REJECTED
    reviewer: Optional[str] = None
    review_date: Optional[str] = None
    pr_url: Optional[str] = None
    branch_name: Optional[str] = None


class ReviewPipeline:
    """
    Human review workflow orchestrator for LLM-generated test scenarios.
    
    This class implements the complete workflow from scenario generation to approval,
    including Git operations, GitHub API integration, LLM-powered edge case suggestions,
    and metadata tracking. It ensures human oversight and quality control for all
    LLM-generated content before it enters the production test suite.
    
    Workflow Steps:
        1. Create feature branch (e.g., llm-generated/login-scenario-20240115-143022)
        2. Commit scenario file with descriptive message
        3. Generate edge case suggestions via LLM
        4. Push branch to remote repository
        5. Create GitHub Pull Request with review checklist
        6. Track review status and metadata
        7. Generate step definition stubs upon PR approval
    
    Attributes:
        github_token: GitHub API authentication token
        repo_owner: GitHub repository owner name
        repo_name: GitHub repository name
        github_client: httpx Client for GitHub API v3 requests
    
    Design Patterns:
        - Builder: Constructs comprehensive PR descriptions with multiple sections
        - Template Method: Defines workflow skeleton, customizable steps
        - Strategy: Git operations abstract local vs remote repository differences
    
    Error Handling:
        - Git command failures raise subprocess.CalledProcessError with stderr
        - GitHub API errors raise httpx.HTTPStatusError with response details
        - Missing configuration (GITHUB_TOKEN) logs warnings, degrades gracefully
        - File I/O errors bubble up as OSError with clear context
    
    Usage:
        >>> pipeline = ReviewPipeline(
        ...     github_token="ghp_...",
        ...     repo_owner="myorg",
        ...     repo_name="test-automation"
        ... )
        >>> metadata = ReviewMetadata(
        ...     feature_file="tests/features/login.feature",
        ...     generation_date=datetime.utcnow().isoformat(),
        ...     llm_provider="ollama",
        ...     llm_model="llama2",
        ...     objective="User login with valid credentials",
        ...     status="DRAFT"
        ... )
        >>> pr_url = pipeline.submit_for_review("tests/features/login.feature", metadata)
        >>> print(f"Review at: {pr_url}")
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None
    ):
        """
        Initialize review pipeline with GitHub configuration.
        
        Configuration is typically sourced from environment variables to support
        different deployment environments (local dev, CI/CD, production).
        
        Args:
            github_token: GitHub API token (defaults to GITHUB_TOKEN env var)
                Format: ghp_... (classic token) or github_pat_... (fine-grained token)
                Required permissions: repo (full control of private repositories)
            repo_owner: GitHub repository owner (defaults to GITHUB_REPOSITORY_OWNER env var)
                Example: "myorg" for https://github.com/myorg/repo
            repo_name: GitHub repository name (defaults to GITHUB_REPOSITORY env var)
                Example: "test-automation" for https://github.com/myorg/test-automation
        
        Raises:
            No exceptions raised during initialization. Missing GitHub configuration
            results in warnings and graceful degradation (local Git operations only).
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.repo_owner = repo_owner or os.getenv("GITHUB_REPOSITORY_OWNER")
        self.repo_name = repo_name or os.getenv("GITHUB_REPOSITORY")
        
        # Initialize GitHub API client if token is available
        if self.github_token:
            self.github_client = httpx.Client(
                base_url="https://api.github.com",
                headers={
                    "Authorization": f"Bearer {self.github_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=30.0
            )
        else:
            self.github_client = None
            print("⚠ Warning: GITHUB_TOKEN not configured - PR creation will be skipped")
    
    def submit_for_review(self, feature_file: str, metadata: ReviewMetadata) -> str:
        """
        Submit LLM-generated scenario for human review via GitHub Pull Request.
        
        This is the main entry point for the review workflow. It orchestrates all steps
        from Git branch creation through PR submission, including LLM-powered edge case
        suggestions and comprehensive review checklist generation.
        
        Args:
            feature_file: Path to generated .feature file (relative to repository root)
                Example: "tests/features/generated/login_scenario.feature"
            metadata: Review metadata with generation details
        
        Returns:
            Pull Request URL for tracking (e.g., "https://github.com/myorg/repo/pull/42")
            If GitHub is not configured, returns branch name instead
        
        Raises:
            subprocess.CalledProcessError: If Git commands fail (e.g., conflicts, network issues)
            httpx.HTTPStatusError: If GitHub API requests fail (e.g., auth errors, rate limits)
            FileNotFoundError: If feature_file does not exist
            ValueError: If metadata is incomplete or invalid
        
        Side Effects:
            - Creates and checks out new Git branch
            - Commits feature file to Git
            - Pushes branch to remote origin
            - Creates GitHub Pull Request
            - Saves metadata JSON file to .metadata/ directory
            - Updates metadata.status to 'PENDING_REVIEW'
        
        Example:
            >>> pipeline = ReviewPipeline()
            >>> metadata = ReviewMetadata(
            ...     feature_file="tests/features/login.feature",
            ...     generation_date="2024-01-15T14:30:22Z",
            ...     llm_provider="ollama",
            ...     llm_model="llama2",
            ...     objective="Test login with valid credentials",
            ...     status="DRAFT"
            ... )
            >>> pr_url = pipeline.submit_for_review("tests/features/login.feature", metadata)
            >>> print(pr_url)
            'https://github.com/myorg/test-automation/pull/42'
        """
        # Step 1: Create Git branch
        branch_name = self._create_feature_branch(metadata.objective)
        metadata.branch_name = branch_name
        
        # Step 2: Commit scenario
        self._commit_scenario(feature_file, metadata)
        
        # Step 3: Generate edge case suggestions via LLM
        edge_cases = self._generate_edge_cases(feature_file)
        
        # Step 4: Push to remote
        try:
            self._push_branch(branch_name)
        except subprocess.CalledProcessError as e:
            print(f"⚠ Warning: Failed to push branch: {e}")
            print("  Branch created locally. Push manually with: git push -u origin {branch_name}")
        
        # Step 5: Create GitHub PR (if configured)
        if self.github_client:
            pr_url = self._create_pull_request(branch_name, feature_file, metadata, edge_cases)
            metadata.pr_url = pr_url
            metadata.status = "PENDING_REVIEW"
        else:
            pr_url = f"git branch: {branch_name}"
            metadata.status = "DRAFT"
        
        # Step 6: Save metadata
        self._save_metadata(metadata)
        
        print(f"✓ Review workflow complete: {pr_url}")
        return pr_url
    
    def _create_feature_branch(self, objective: str) -> str:
        """
        Create Git feature branch for LLM-generated scenario.
        
        Branch naming convention: llm-generated/<objective-slug>-<timestamp>
        This ensures uniqueness and traceability for all LLM-generated content.
        
        Args:
            objective: Human-readable test objective
        
        Returns:
            Branch name (e.g., "llm-generated/login-scenario-20240115-143022")
        
        Raises:
            subprocess.CalledProcessError: If git checkout command fails
        """
        # Generate timestamp for uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        
        # Convert objective to URL-safe slug
        branch_slug = objective.lower().replace(" ", "-").replace("/", "-")
        # Limit slug length to avoid overly long branch names
        branch_slug = branch_slug[:40].rstrip("-")
        
        branch_name = f"llm-generated/{branch_slug}-{timestamp}"
        
        # Create and checkout branch
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"✓ Created branch: {branch_name}")
        return branch_name
    
    def _commit_scenario(self, feature_file: str, metadata: ReviewMetadata):
        """
        Commit scenario file with descriptive message containing generation metadata.
        
        The commit message follows conventional commit format and includes all relevant
        generation details for audit trail and Git history readability.
        
        Args:
            feature_file: Path to .feature file to commit
            metadata: Generation metadata for commit message
        
        Raises:
            subprocess.CalledProcessError: If git add or git commit fails
        """
        commit_message = f"""feat: Add LLM-generated scenario - {metadata.objective}

Generated by: {metadata.llm_provider}/{metadata.llm_model}
Generation Date: {metadata.generation_date}
Status: DRAFT - Requires human review

This scenario was automatically generated by LLM exploration and requires:
- Business logic validation
- Step definition implementation
- Edge case coverage verification
- Locator strategy review

Before merging:
1. Review Gherkin for business accuracy
2. Validate step definitions are high-level
3. Consider suggested edge cases
4. Ensure test data will use MCP tools
"""
        
        # Stage the feature file
        subprocess.run(
            ["git", "add", feature_file],
            check=True,
            capture_output=True,
            text=True
        )
        
        # Commit with detailed message
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=True,
            capture_output=True,
            text=True
        )
        
        print(f"✓ Committed: {feature_file}")
    
    def _generate_edge_cases(self, feature_file: str) -> List[str]:
        """
        Generate edge case suggestions using LLM analysis of scenario.
        
        This method uses the LLM client's suggest_edge_cases() capability to identify
        boundary conditions, error scenarios, and test variations that human reviewers
        should consider for comprehensive test coverage.
        
        Args:
            feature_file: Path to .feature file containing Gherkin scenario
        
        Returns:
            List of edge case descriptions (human-readable strings)
        
        Raises:
            FileNotFoundError: If feature_file does not exist
            ConnectionError: If LLM provider API is unreachable
            ValueError: If scenario parsing fails
        
        Example:
            >>> edge_cases = pipeline._generate_edge_cases("tests/features/login.feature")
            >>> for case in edge_cases:
            ...     print(f"- {case}")
            - Test login with email exceeding 320 characters
            - Test login with SQL injection in password field
            - Test login with expired session token
        """
        # Read feature file content
        try:
            with open(feature_file, "r", encoding="utf-8") as f:
                scenario_text = f.read()
        except FileNotFoundError:
            print(f"⚠ Warning: Feature file not found: {feature_file}")
            return []
        
        # Get LLM client and request edge case suggestions
        try:
            llm = get_llm_client()
            edge_cases = llm.suggest_edge_cases(scenario_text)
            
            print(f"✓ Generated {len(edge_cases)} edge case suggestions")
            return edge_cases
        
        except Exception as e:
            print(f"⚠ Warning: Failed to generate edge cases: {e}")
            print("  Continuing without edge case suggestions")
            return []
    
    def _push_branch(self, branch_name: str):
        """
        Push feature branch to remote origin.
        
        Args:
            branch_name: Git branch name to push
        
        Raises:
            subprocess.CalledProcessError: If git push fails (network, auth, etc.)
        """
        subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✓ Pushed branch: {branch_name}")
    
    def _create_pull_request(
        self,
        branch_name: str,
        feature_file: str,
        metadata: ReviewMetadata,
        edge_cases: List[str]
    ) -> str:
        """
        Create GitHub Pull Request with comprehensive review checklist.
        
        The PR includes:
        - Generated Gherkin scenario in code block
        - Review checklist covering business logic, technical quality, and coverage
        - LLM-suggested edge cases for reviewer consideration
        - Next steps for implementation
        - Automatic labels for categorization
        
        Args:
            branch_name: Git feature branch name
            feature_file: Path to .feature file
            metadata: Generation metadata
            edge_cases: LLM-generated edge case suggestions
        
        Returns:
            Pull Request HTML URL
        
        Raises:
            httpx.HTTPStatusError: If GitHub API request fails
            ValueError: If repo_owner or repo_name not configured
        """
        if not self.github_client:
            print("⚠ Warning: GitHub client not configured - skipping PR creation")
            return f"git branch: {branch_name}"
        
        if not self.repo_owner or not self.repo_name:
            raise ValueError(
                "GitHub repository not configured. Set GITHUB_REPOSITORY_OWNER "
                "and GITHUB_REPOSITORY environment variables."
            )
        
        # Build comprehensive PR description
        pr_body = self._build_pr_description(feature_file, metadata, edge_cases)
        
        # Create PR via GitHub API v3
        try:
            response = self.github_client.post(
                f"/repos/{self.repo_owner}/{self.repo_name}/pulls",
                json={
                    "title": f"LLM-Generated Scenario: {metadata.objective}",
                    "body": pr_body,
                    "head": branch_name,
                    "base": "main",
                    "draft": False
                }
            )
            response.raise_for_status()
            pr_data = response.json()
            pr_url = pr_data["html_url"]
            pr_number = pr_data["number"]
            
            # Add labels for filtering and categorization
            self._add_pr_labels(pr_number, ["llm-generated", "needs-review", "test-automation"])
            
            print(f"✓ Created Pull Request: {pr_url}")
            return pr_url
        
        except httpx.HTTPStatusError as e:
            print(f"⚠ Error creating PR: {e.response.status_code} {e.response.text}")
            raise
    
    def _build_pr_description(
        self,
        feature_file: str,
        metadata: ReviewMetadata,
        edge_cases: List[str]
    ) -> str:
        """
        Build comprehensive PR description with review checklist and edge cases.
        
        The description follows a structured template ensuring consistent reviews
        across all LLM-generated scenarios.
        
        Args:
            feature_file: Path to .feature file
            metadata: Generation metadata
            edge_cases: LLM-suggested edge cases
        
        Returns:
            Markdown-formatted PR description
        """
        # Read feature content
        try:
            with open(feature_file, "r", encoding="utf-8") as f:
                feature_content = f.read()
        except FileNotFoundError:
            feature_content = "(Feature file not found)"
        
        # Extract Gherkin (remove metadata comments if present)
        lines = feature_content.split("\n")
        gherkin_lines = [line for line in lines if not line.strip().startswith("#")]
        gherkin = "\n".join(gherkin_lines).strip()
        
        # Build structured PR description
        description = f"""## LLM-Generated Test Scenario

**Objective:** {metadata.objective}  
**Generated by:** {metadata.llm_provider}/{metadata.llm_model}  
**Generation Date:** {metadata.generation_date}  
**File:** `{feature_file}`

### Generated Gherkin Scenario

```gherkin
{gherkin}
```

### Review Checklist

Please review the following before approval:

#### Business Logic
- [ ] Scenario accurately represents intended business behavior
- [ ] Given/When/Then steps are clear and unambiguous
- [ ] Scenario covers the happy path thoroughly
- [ ] Business terminology is accurate

#### Technical Quality
- [ ] Steps are high-level (no UI implementation details)
- [ ] Locator strategies will use ARIA roles/labels/test-ids
- [ ] Scenario is deterministic and repeatable
- [ ] No hardcoded test data (will use MCP server)

#### Coverage
- [ ] Core user flow is covered
- [ ] Edge cases identified below are addressed or planned
- [ ] Error handling scenarios considered

### LLM-Suggested Edge Cases

The LLM identified the following edge cases to consider:

"""
        
        # Add edge cases (numbered list)
        if edge_cases:
            for i, edge_case in enumerate(edge_cases, 1):
                description += f"{i}. {edge_case}\n"
        else:
            description += "_No edge cases suggested_\n"
        
        description += """
### Next Steps

1. **Review**: Human review of scenario accuracy and completeness
2. **Approve**: Merge this PR to accept the scenario
3. **Implement**: Auto-generate step definition stubs (on merge)
4. **Enhance**: Add edge case scenarios if needed

### Implementation Notes

- Step definitions will be generated in `tests/step_definitions/`
- Page objects may need creation/updates in `tests/pages/`
- MCP server should provide test data via `seed_user` and `build_payload` tools

---

**⚠️ This scenario requires human review and approval before use in test suite.**
"""
        
        return description
    
    def _add_pr_labels(self, pr_number: int, labels: List[str]):
        """
        Add labels to Pull Request for categorization and filtering.
        
        Args:
            pr_number: GitHub Pull Request number
            labels: List of label names to add
        
        Raises:
            httpx.HTTPStatusError: If GitHub API request fails
        """
        if not self.github_client:
            return
        
        try:
            response = self.github_client.post(
                f"/repos/{self.repo_owner}/{self.repo_name}/issues/{pr_number}/labels",
                json={"labels": labels}
            )
            response.raise_for_status()
            print(f"✓ Added labels: {', '.join(labels)}")
        except httpx.HTTPStatusError as e:
            print(f"⚠ Warning: Failed to add labels: {e.response.status_code}")
    
    def _save_metadata(self, metadata: ReviewMetadata):
        """
        Save review metadata to JSON file for status tracking.
        
        Metadata is stored in tests/features/generated/.metadata/ directory
        with filename matching the feature file stem.
        
        Args:
            metadata: ReviewMetadata instance to persist
        
        Raises:
            OSError: If directory creation or file writing fails
        """
        metadata_dir = Path("tests/features/generated/.metadata")
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        filename = Path(metadata.feature_file).stem + ".json"
        metadata_path = metadata_dir / filename
        
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.__dict__, f, indent=2)
        
        print(f"✓ Saved metadata: {metadata_path}")


def submit_for_review(feature_file: str) -> str:
    """
    Convenience function: Submit generated scenario for review.
    
    This is a simplified interface to the ReviewPipeline that automatically
    parses metadata from the feature file header and creates the pipeline
    with default configuration.
    
    Args:
        feature_file: Path to generated .feature file (relative to repository root)
    
    Returns:
        Pull Request URL or branch name if GitHub not configured
    
    Raises:
        FileNotFoundError: If feature_file does not exist
        subprocess.CalledProcessError: If Git commands fail
        httpx.HTTPStatusError: If GitHub API requests fail
    
    Usage:
        >>> from llm.workflows.review_pipeline import submit_for_review
        >>> 
        >>> # After LLM generates a feature file
        >>> pr_url = submit_for_review("tests/features/generated/login.feature")
        >>> print(f"Review PR: {pr_url}")
        'https://github.com/myorg/test-automation/pull/42'
    """
    # Parse metadata from feature file header
    metadata = _parse_metadata_from_file(feature_file)
    
    # Create pipeline and submit
    pipeline = ReviewPipeline()
    pr_url = pipeline.submit_for_review(feature_file, metadata)
    
    return pr_url


def _parse_metadata_from_file(feature_file: str) -> ReviewMetadata:
    """
    Parse review metadata from feature file header comments.
    
    This function extracts generation metadata from specially formatted comments
    at the top of the feature file. If metadata comments are not present,
    it provides sensible defaults based on the filename and current timestamp.
    
    Expected header format:
        # LLM Provider: ollama
        # LLM Model: llama2
        # Objective: Test user login with valid credentials
        # Generation Date: 2024-01-15T14:30:22Z
    
    Args:
        feature_file: Path to .feature file
    
    Returns:
        ReviewMetadata instance with parsed or default values
    
    Raises:
        FileNotFoundError: If feature_file does not exist
    """
    try:
        with open(feature_file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        # If file doesn't exist, create minimal metadata
        return ReviewMetadata(
            feature_file=feature_file,
            generation_date=datetime.utcnow().isoformat(),
            llm_provider=os.getenv("LLM_PROVIDER", "ollama"),
            llm_model=os.getenv("LLM_MODEL", "unknown"),
            objective=Path(feature_file).stem.replace("_", " ").title(),
            status="DRAFT"
        )
    
    # Extract metadata from header comments
    lines = content.split("\n")
    metadata_dict = {
        "feature_file": feature_file,
        "generation_date": datetime.utcnow().isoformat(),
        "llm_provider": os.getenv("LLM_PROVIDER", "ollama"),
        "llm_model": os.getenv("LLM_MODEL", "unknown"),
        "objective": Path(feature_file).stem.replace("_", " ").title(),
        "status": "DRAFT"
    }
    
    # Parse header comments
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# LLM Provider:"):
            metadata_dict["llm_provider"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("# LLM Model:"):
            metadata_dict["llm_model"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("# Objective:"):
            metadata_dict["objective"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("# Generation Date:"):
            metadata_dict["generation_date"] = stripped.split(":", 1)[1].strip()
    
    return ReviewMetadata(**metadata_dict)


def generate_step_stubs(feature_file: str, output_dir: str = "tests/step_definitions") -> str:
    """
    Generate step definition stubs for approved scenario.
    
    This function parses the approved Gherkin feature file and generates Python
    step definition stubs with proper pytest-bdd decorators. The stubs serve as
    implementation templates that developers fill in with page object calls and
    MCP tool usage.
    
    This function is typically called automatically when a PR is merged/approved,
    but can also be invoked manually for local development.
    
    Args:
        feature_file: Path to .feature file (relative to repository root)
        output_dir: Directory for step definition files (default: tests/step_definitions)
    
    Returns:
        Path to generated step definition file
    
    Raises:
        FileNotFoundError: If feature_file does not exist
        ValueError: If feature file has invalid Gherkin syntax
        OSError: If output directory creation or file writing fails
    
    Usage:
        >>> from llm.workflows.review_pipeline import generate_step_stubs
        >>> 
        >>> # After PR approval/merge
        >>> stubs_file = generate_step_stubs("tests/features/login.feature")
        >>> print(f"Implement steps in: {stubs_file}")
        'tests/step_definitions/login_steps.py'
    
    Generated stub format:
        ```python
        @given("the user is on the login page")
        def step_user_on_login_page():
            '''TODO: Implement step definition.'''
            raise NotImplementedError
        ```
    """
    try:
        from pytest_bdd.parser import Feature
    except ImportError as e:
        raise ImportError(
            "Step stub generation requires pytest-bdd. "
            "Install with: pip install pytest-bdd"
        ) from e
    
    # Verify feature file exists
    if not Path(feature_file).exists():
        raise FileNotFoundError(f"Feature file not found: {feature_file}")
    
    # Parse feature file with pytest-bdd
    try:
        feature = Feature.parse(feature_file)
    except Exception as e:
        raise ValueError(f"Failed to parse feature file: {e}") from e
    
    # Create output directory
    output_path_obj = Path(output_dir)
    output_path_obj.mkdir(parents=True, exist_ok=True)
    
    # Generate output filename
    feature_stem = Path(feature_file).stem
    output_file = output_path_obj / f"{feature_stem}_steps.py"
    
    # Collect unique steps across all scenarios
    unique_steps: Dict[str, Dict[str, str]] = {}  # step_text -> {keyword, function_name}
    
    for scenario in feature.scenarios:
        for step in scenario.steps:
            step_text = step.name
            if step_text not in unique_steps:
                # Generate function name from step text
                func_name = _generate_step_function_name(step_text)
                unique_steps[step_text] = {
                    "keyword": step.keyword.lower().strip(),
                    "function_name": func_name
                }
    
    # Generate stub file
    with open(output_file, "w", encoding="utf-8") as f:
        # File header
        f.write(f'"""\n')
        f.write(f"Step definitions for {feature_file}\n")
        f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
        f.write(f"\n")
        f.write(f"This file contains stub implementations for Gherkin steps.\n")
        f.write(f"Replace NotImplementedError with actual implementations using:\n")
        f.write(f"- Page objects from tests/pages/\n")
        f.write(f"- API clients from tests/api_clients/\n")
        f.write(f"- MCP tools from tests/helpers/mcp_client.py\n")
        f.write(f'"""\n\n')
        
        # Imports
        f.write("from pytest_bdd import given, when, then, parsers\n")
        f.write("import pytest\n\n")
        f.write("# Import page objects and helpers as needed:\n")
        f.write("# from tests.pages.login_page import LoginPage\n")
        f.write("# from tests.helpers.mcp_client import MCPClient\n\n\n")
        
        # Generate stubs for each unique step
        for step_text, step_info in sorted(unique_steps.items()):
            keyword = step_info["keyword"]
            func_name = step_info["function_name"]
            
            # Step decorator
            f.write(f'@{keyword}("{step_text}")\n')
            
            # Function definition
            f.write(f"def {func_name}():\n")
            f.write(f'    """\n')
            f.write(f'    TODO: Implement step definition.\n')
            f.write(f'    \n')
            f.write(f'    Example implementation:\n')
            f.write(f'        # For UI steps:\n')
            f.write(f'        # login_page.navigate()\n')
            f.write(f'        # login_page.enter_credentials(username, password)\n')
            f.write(f'        \n')
            f.write(f'        # For API steps:\n')
            f.write(f'        # response = api_client.post("/endpoint", json=payload)\n')
            f.write(f'        # assert response.status_code == 200\n')
            f.write(f'        \n')
            f.write(f'        # For MCP data:\n')
            f.write(f'        # user = mcp_client.seed_user(role="admin")\n')
            f.write(f'    """\n')
            f.write(f"    raise NotImplementedError(\n")
            f.write(f'        "Step definition not yet implemented. "\n')
            f.write(f'        "See docstring for implementation guidance."\n')
            f.write(f"    )\n\n\n")
    
    print(f"✓ Generated step stubs: {output_file}")
    return str(output_file)


def _generate_step_function_name(step_text: str) -> str:
    """
    Generate valid Python function name from Gherkin step text.
    
    Converts step text to snake_case, removes special characters, and limits length.
    
    Args:
        step_text: Gherkin step text (e.g., "the user clicks the login button")
    
    Returns:
        Valid Python function name (e.g., "step_user_clicks_login_button")
    """
    # Convert to lowercase and replace spaces with underscores
    func_name = step_text.lower()
    
    # Remove special characters (keep only alphanumeric and underscores)
    func_name = "".join(c if c.isalnum() or c == " " else "" for c in func_name)
    func_name = func_name.replace(" ", "_")
    
    # Remove consecutive underscores
    while "__" in func_name:
        func_name = func_name.replace("__", "_")
    
    # Add step_ prefix
    func_name = f"step_{func_name}"
    
    # Limit length to 60 characters
    if len(func_name) > 60:
        func_name = func_name[:60].rstrip("_")
    
    return func_name
