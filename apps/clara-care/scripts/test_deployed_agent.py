"""Test the deployed ClaraCare agent on Vertex AI Agent Engine.

Usage:
    uv run python scripts/test_deployed_agent.py [RESOURCE_ID]
"""

import argparse
import os
import sys

from vertexai import agent_engines
import vertexai

# The latest deployed resource ID
# The latest deployed resource ID
DEFAULT_RESOURCE_ID = "projects/73252715699/locations/us-central1/reasoningEngines/1304798145263173632"

def main():
    parser = argparse.ArgumentParser(description="Test deployed ClaraCare agent")
    parser.add_argument(
        "resource_id",
        nargs="?",
        default=DEFAULT_RESOURCE_ID,
        help="Vertex AI Agent Engine Resource ID (optional, uses default if not provided)"
    )
    parser.add_argument(
        "--project",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        help="Google Cloud Project ID"
    )
    parser.add_argument(
        "--location",
        default="us-central1",
        help="Google Cloud Location"
    )
    args = parser.parse_args()

    project_id = args.project
    if not project_id:
        # Fallback to hardcoded project ID for convenience if not set
        project_id = "smart-receipts-anz"
    
    if not project_id and args.resource_id.startswith("projects/"):
         # Only as a last resort, infer from resource ID (though numbers can cause 403s)
         try:
             project_id = args.resource_id.split("/")[1]
         except IndexError:
             pass

    if not project_id:
        print("Error: Could not determine Google Cloud Project ID.")
        print("Please set GOOGLE_CLOUD_PROJECT env var or pass --project argument.")
        return 1

    print(f"Initializing Vertex AI (Project: {project_id}, Location: {args.location})...")
    
    # Configure logging to see underlying errors
    # import logging
    # logging.basicConfig(level=logging.INFO)
    
    # Verify credentials
    import google.auth
    credentials, auth_project = google.auth.default()
    print(f"Credentials: {credentials}")
    print(f"Auth Project: {auth_project}")
    if hasattr(credentials, "quota_project_id"):
        print(f"Quota Project ID: {credentials.quota_project_id}")
    
    vertexai.init(project=project_id, location=args.location)

    resource_id = args.resource_id

    print(f"Connecting to Agent Engine: {resource_id}...")
    try:
        agent = agent_engines.get(resource_id)
    except Exception as e:
        print(f"Error connecting to agent: {e}")
        return 1

    print("Agent connected successfully.")
    
    query_text = "WC-94E635"
    payload = {
        "message": {
            "role": "user",
            "parts": [{"text": query_text}]
        },
        "user_id": "test-user-001"
    }
    
    print(f"\nSending Payload: {payload}")
    print("-" * 40)

    try:
        # Prioritize stream_query for ADK apps
        if hasattr(agent, "stream_query"):
            print("Calling agent.stream_query()...")
            try:
                response_stream = agent.stream_query(**payload)
                print("\nStreaming Response:")
                for chunk in response_stream:
                    print(chunk)
                return 0
            except Exception as e:
                print(f"stream_query failed: {e}")
                print("Falling back to query()...")

        # Fallback to standard query
        if hasattr(agent, "query"):
            print("Calling agent.query()...")
            response = agent.query(**payload)
            print("\nResponse:")
            print(response)
            return 0
        
        print("\nERROR: Agent has neither 'query' nor 'stream_query' methods, or both failed.")
        print("Available attributes:", dir(agent))
        if hasattr(agent, "_operation_schemas"):
            print("Operation Schemas:", agent._operation_schemas)
        return 1

    except Exception as e:
        print(f"\nError querying agent: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    main()
