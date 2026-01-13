"""Deploy ClaraCare agent to Vertex AI Agent Engine.

This script deploys the ClaraCare warranty claim agent to Google Cloud's
Vertex AI Agent Engine for production use.

Prerequisites:
    1. Authenticate with Google Cloud:
       gcloud auth login
       gcloud auth application-default login

    2. Set project:
       gcloud config set project YOUR_PROJECT_ID

    3. Enable required APIs:
       gcloud services enable aiplatform.googleapis.com
       gcloud services enable storage.googleapis.com
       gcloud services enable secretmanager.googleapis.com
       gcloud services enable cloudtrace.googleapis.com

    4. Create GCS bucket for staging:
       gsutil mb -l us-central1 gs://YOUR_PROJECT_ID-staging

    5. Store secrets in Secret Manager:
       echo -n "https://xxx.supabase.co" | \\
           gcloud secrets create SUPABASE_URL --data-file=-
       echo -n "your-service-role-key" | \\
           gcloud secrets create SUPABASE_SERVICE_ROLE_KEY --data-file=-
       echo -n "sk-your-openai-key" | \\
           gcloud secrets create OPENAI_API_KEY --data-file=-

    6. Grant Secret Manager access to Compute Engine service account:
       gcloud projects add-iam-policy-binding PROJECT_ID \\
           --member="serviceAccount:PROJECT_NUMBER-compute@..." \\
           --role="roles/secretmanager.secretAccessor"

Usage:
    cd apps/clara-care
    uv run python scripts/deploy_to_agent_engine.py

    # With custom settings:
    uv run python scripts/deploy_to_agent_engine.py \\
        --project your-project-id \\
        --location us-central1 \\
        --display-name "ClaraCare Production"
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_default_project_id() -> str | None:
    """Get default project ID from gcloud config or environment."""
    # Check environment first
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if project:
        return project

    # Try to get from gcloud config
    try:
        import subprocess

        result = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            check=True,
        )
        project = result.stdout.strip()
        if project and project != "(unset)":
            return project
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return None


def create_env_vars(project_id: str) -> dict[str, Any]:
    """Create environment variables configuration with Secret Manager references.

    Args:
        project_id: Google Cloud project ID for Secret Manager references.

    Returns:
        Dictionary of environment variables for Agent Engine deployment.
    """
    return {
        # CRITICAL: Use Vertex AI for Gemini (required for Agent Engine)
        # DO NOT use GOOGLE_API_KEY - it conflicts with Agent Engine's
        # internal Vertex AI session service
        "GOOGLE_GENAI_USE_VERTEXAI": "1",
        # Google Cloud project ID for Supabase and other services
        "GOOGLE_CLOUD_PROJECT": project_id,
        # Secrets from Google Cloud Secret Manager
        # Format: {"secret": "SECRET_NAME", "version": "latest"}
        "SUPABASE_URL": {"secret": "SUPABASE_URL", "version": "latest"},
        "SUPABASE_SERVICE_ROLE_KEY": {
            "secret": "SUPABASE_SERVICE_ROLE_KEY",
            "version": "latest",
        },
        "OPENAI_API_KEY": {"secret": "OPENAI_API_KEY", "version": "latest"},
    }


def get_requirements() -> list[str]:
    """Get list of Python package requirements for Agent Engine.

    Returns:
        List of pip-installable package specifiers.
    """
    return [
        # Core ADK and Gemini
        "google-adk>=0.3.0",
        "google-genai>=1.24.0",
        "google-cloud-aiplatform[adk,agent_engines]",
        # Database and embeddings
        "supabase>=2.0.0",
        "openai>=1.0.0",
        # Configuration
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "python-dotenv>=1.0.0",
    ]


def deploy_agent(
    project_id: str,
    location: str = "us-central1",
    staging_bucket: str | None = None,
    display_name: str = "ClaraCare Warranty Agent",
) -> Any:
    """Deploy ClaraCare agent to Vertex AI Agent Engine.

    Args:
        project_id: Google Cloud project ID.
        location: GCP region for deployment (default: us-central1).
        staging_bucket: GCS bucket for staging (default: gs://PROJECT_ID-staging).
        display_name: Display name for the deployed agent.

    Returns:
        Deployed agent resource object with resource_name attribute.

    Raises:
        ImportError: If required Google Cloud packages are not installed.
        RuntimeError: If deployment fails.
    """
    # Set default staging bucket if not provided
    if staging_bucket is None:
        staging_bucket = f"gs://{project_id}-staging"

    print("=" * 60)
    print("ClaraCare Agent Engine Deployment")
    print("=" * 60)

    print("\nInitializing Vertex AI...")
    print(f"  Project:        {project_id}")
    print(f"  Location:       {location}")
    print(f"  Staging Bucket: {staging_bucket}")

    # Import Vertex AI SDK (late import to provide better error messages)
    try:
        import vertexai
        from vertexai import agent_engines
        from vertexai.preview import reasoning_engines
    except ImportError as e:
        raise ImportError(
            "Required packages not installed. Run:\n"
            "  pip install google-cloud-aiplatform[adk,agent_engines]"
        ) from e

    # Initialize Vertex AI
    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=staging_bucket,
    )

    print("\nImporting ClaraCare agent...")
    try:
        from clara_care import root_agent

        print(f"  Agent Name: {root_agent.name}")
    except ImportError as e:
        raise ImportError(
            "Could not import root_agent from clara_care. "
            "Ensure you are running from apps/clara-care directory."
        ) from e

    print("\nCreating AdkApp wrapper with Cloud Trace enabled...")
    adk_app = reasoning_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,  # Enable Cloud Trace for observability
    )

    # Prepare environment variables
    env_vars = create_env_vars(project_id)
    requirements = get_requirements()

    print("\nDeploying to Agent Engine...")
    print(f"  Display Name:  {display_name}")
    print(f"  Requirements:  {len(requirements)} packages")
    print(f"  Env Variables: {len(env_vars)} configured")

    # List requirements for visibility
    print("\n  Package requirements:")
    for req in requirements:
        print(f"    - {req}")

    print("\n  Environment variables:")
    for key, value in env_vars.items():
        if isinstance(value, dict):
            print(f"    - {key}: (Secret Manager: {value['secret']})")
        else:
            print(f"    - {key}: {value}")

    print("\nStarting deployment (this may take several minutes)...")

    # Deploy with environment variables
    # Type ignore: AdkApp is compatible but type stubs are incomplete
    remote_app = agent_engines.create(
        agent_engine=adk_app,  # type: ignore[arg-type]
        display_name=display_name,
        requirements=requirements,
        extra_packages=[
            "./clara_care",  # Include clara_care package
        ],
        env_vars=env_vars,
    )

    print(f"\n{'=' * 60}")
    print("DEPLOYMENT SUCCESSFUL!")
    print("=" * 60)
    print(f"\nResource Name: {remote_app.resource_name}")

    # Extract resource ID for convenience
    resource_parts = remote_app.resource_name.split("/")
    if len(resource_parts) >= 6:
        resource_id = resource_parts[-1]
        project_number = resource_parts[1]
        print(f"Resource ID:   {resource_id}")
        print(f"Project Number: {project_number}")

    print("\nView in Cloud Console:")
    console_url = (
        f"https://console.cloud.google.com/vertex-ai/agents/agent-engines"
        f"?project={project_id}"
    )
    print(f"  {console_url}")

    print("\nView logs:")
    print('  gcloud logging read "resource.type=reasoning_engine" --limit=50')

    print("\nNext steps:")
    print("  1. Update scripts/test_deployed_agent.py with the Resource ID above")
    print("  2. Run: uv run python scripts/test_deployed_agent.py")

    return remote_app


def main() -> int:
    """Main entry point for deployment script.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description="Deploy ClaraCare agent to Vertex AI Agent Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy with default settings (uses gcloud config)
  uv run python scripts/deploy_to_agent_engine.py

  # Deploy with explicit project
  uv run python scripts/deploy_to_agent_engine.py --project my-project-id

  # Deploy to different region
  uv run python scripts/deploy_to_agent_engine.py --location europe-west1
""",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=None,
        help="Google Cloud project ID (default: from gcloud config)",
    )
    parser.add_argument(
        "--location",
        type=str,
        default="us-central1",
        help="GCP region (default: us-central1)",
    )
    parser.add_argument(
        "--staging-bucket",
        type=str,
        default=None,
        help="GCS bucket for staging (default: gs://PROJECT_ID-staging)",
    )
    parser.add_argument(
        "--display-name",
        type=str,
        default="ClaraCare Warranty Agent",
        help="Display name for deployed agent",
    )

    args = parser.parse_args()

    # Resolve project ID
    project_id = args.project or get_default_project_id()
    if not project_id:
        print("ERROR: No project ID specified.")
        print("Please either:")
        print("  1. Set GOOGLE_CLOUD_PROJECT environment variable")
        print("  2. Run: gcloud config set project YOUR_PROJECT_ID")
        print("  3. Use --project argument")
        return 1

    try:
        deploy_agent(
            project_id=project_id,
            location=args.location,
            staging_bucket=args.staging_bucket,
            display_name=args.display_name,
        )
        return 0
    except ImportError as e:
        print(f"\nERROR: {e}")
        return 1
    except Exception as e:
        print(f"\nERROR: Deployment failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
