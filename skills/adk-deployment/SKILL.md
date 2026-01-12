---
name: adk-deployment
description: Deploy Google ADK agents to production environments including Vertex AI Agent Engine, Cloud Run, and local development. Use when user says "deploy agent", "production deployment", "agent engine", "cloud run", or wants to deploy their ADK agent.
---

# ADK Deployment Skill

## Purpose
Deploy Google ADK agents to various environments: Vertex AI Agent Engine (recommended for production), Google Cloud Run, or local development servers. This skill covers the complete deployment workflow from configuration to production.

## When to Activate
Activate when user mentions:
- "deploy agent", "production deployment"
- "vertex ai agent engine", "agent engine"
- "cloud run deployment", "deploy to cloud"
- "local development server", "adk web", "adk run"

## Deployment Options Overview

| Environment | Best For | Command |
|-------------|----------|---------|
| **Vertex AI Agent Engine** | Production, fully managed | Python SDK deployment |
| **Cloud Run** | Custom containers, APIs | `gcloud run deploy` |
| **Local Development** | Testing, debugging | `adk web` or `adk run` |

---

## CRITICAL: Agent Engine Authentication

### The #1 Deployment Error
```
ValueError: Project/location and API key are mutually exclusive in the client initializer.
```

**Root Cause**: Agent Engine uses Vertex AI session service internally, which conflicts with `GOOGLE_API_KEY`.

**Solution**: ALWAYS use Vertex AI authentication for Agent Engine:
```python
ENV_VARS = {
    # CRITICAL: Must use Vertex AI, NOT API key
    "GOOGLE_GENAI_USE_VERTEXAI": "1",  # Required for Agent Engine

    # DO NOT include GOOGLE_API_KEY - it will cause conflicts
}
```

### Authentication Matrix

| Environment | Auth Method | Environment Variable |
|-------------|-------------|---------------------|
| Local Dev | Google API Key | `GOOGLE_API_KEY=AIza...` |
| Agent Engine | Vertex AI | `GOOGLE_GENAI_USE_VERTEXAI=1` |
| Cloud Run | Service Account | Attached to service |

---

## Deployment Option 1: Vertex AI Agent Engine (Recommended)

### Prerequisites
```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# 2. Set project
gcloud config set project YOUR_PROJECT_ID

# 3. Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable secretmanager.googleapis.com

# 4. Create GCS bucket for staging
gsutil mb -l us-central1 gs://YOUR_PROJECT_ID-staging
```

### Store Secrets in Secret Manager
```bash
# Create secrets (NEVER hardcode in code)
echo -n "https://your-project.supabase.co" | \
  gcloud secrets create SUPABASE_URL --data-file=-

echo -n "your-service-role-key" | \
  gcloud secrets create SUPABASE_SERVICE_ROLE_KEY --data-file=-

echo -n "sk-your-openai-key" | \
  gcloud secrets create OPENAI_API_KEY --data-file=-
```

### Python SDK Deployment Script (RECOMMENDED)

Create `scripts/deploy_to_agent_engine.py`:

```python
"""Deploy agent to Vertex AI Agent Engine.

Usage:
    cd apps/<agent-name>
    uv run python scripts/deploy_to_agent_engine.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines

# Configuration
PROJECT_ID = "your-project-id"
LOCATION = "us-central1"
STAGING_BUCKET = f"gs://{PROJECT_ID}-staging"
DISPLAY_NAME = "your-agent-name"

# Environment variables with Secret Manager references
# Format: {"secret": "SECRET_NAME", "version": "latest"} for secrets
ENV_VARS = {
    # Secrets from Secret Manager
    "SUPABASE_URL": {"secret": "SUPABASE_URL", "version": "latest"},
    "SUPABASE_SERVICE_ROLE_KEY": {"secret": "SUPABASE_SERVICE_ROLE_KEY", "version": "latest"},
    "OPENAI_API_KEY": {"secret": "OPENAI_API_KEY", "version": "latest"},

    # CRITICAL: Use Vertex AI for Gemini (required for Agent Engine)
    "GOOGLE_GENAI_USE_VERTEXAI": "1",

    # Optional: Test user for development
    "TEST_USER_ID": "your-test-user-uuid",
}


def main():
    """Deploy the agent to Agent Engine."""
    print(f"Initializing Vertex AI...")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Staging Bucket: {STAGING_BUCKET}")

    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET,
    )

    print(f"\nImporting agent...")
    from your_agent_package import root_agent
    print(f"  Agent: {root_agent.name}")

    print(f"\nCreating AdkApp wrapper...")
    adk_app = reasoning_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,  # Enable Cloud Trace for observability
    )

    print(f"\nDeploying to Agent Engine...")
    print(f"  Display Name: {DISPLAY_NAME}")
    print(f"  Environment Variables: {len(ENV_VARS)} configured")

    # Deploy with environment variables
    remote_app = agent_engines.create(
        agent_engine=adk_app,
        display_name=DISPLAY_NAME,
        requirements=[
            "google-adk>=0.3.0",
            "google-genai>=1.24.0",
            "google-cloud-aiplatform[adk,agent_engines]",
            "openai>=1.0.0",
            "supabase>=2.0.0",
            "pydantic-settings>=2.0.0",
        ],
        extra_packages=[
            "./your_agent_package",  # Your agent package directory
        ],
        env_vars=ENV_VARS,
    )

    print(f"\n{'='*60}")
    print(f"DEPLOYMENT SUCCESSFUL!")
    print(f"{'='*60}")
    print(f"Resource Name: {remote_app.resource_name}")
    print(f"\nView in Cloud Console:")
    print(f"  https://console.cloud.google.com/vertex-ai/agents/agent-engines?project={PROJECT_ID}")

    return remote_app


if __name__ == "__main__":
    remote_app = main()
```

### Test Deployed Agent Script

Create `scripts/test_deployed_agent.py`:

```python
"""Test deployed agent with async streaming.

Usage:
    uv run python scripts/test_deployed_agent.py
    uv run python scripts/test_deployed_agent.py "Your custom query"
    uv run python scripts/test_deployed_agent.py --benchmark
"""

import argparse
import asyncio
import time
from dataclasses import dataclass

import vertexai
from vertexai import agent_engines

# Configuration - UPDATE AFTER DEPLOYMENT
PROJECT_ID = "your-project-id"
LOCATION = "us-central1"
RESOURCE_ID = "your-resource-id"  # From deployment output
PROJECT_NUMBER = "your-project-number"
RESOURCE_NAME = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{RESOURCE_ID}"

USER_ID = "your-test-user-uuid"
PREWARM_QUERY = "ready"  # Lightweight query to prime cache

DEFAULT_QUERIES = [
    "What did I buy in 2024?",
    "How much did I spend at JB Hi-Fi?",
]


@dataclass
class QueryResult:
    query: str
    success: bool
    response: str = ""
    error: str = ""
    latency_ms: float = 0.0


def extract_final_response(events: list) -> str:
    """Extract text from streaming events."""
    final_texts = []
    for event in events:
        if isinstance(event, dict):
            content = event.get("content", {})
            if isinstance(content, dict):
                parts = content.get("parts", [])
                for part in parts:
                    if isinstance(part, dict) and "text" in part:
                        final_texts.append(part["text"])
    return "\n".join(final_texts) if final_texts else "No response"


async def run_query(remote_app, session_id: str, query: str) -> QueryResult:
    """Run query and return result with timing."""
    start = time.perf_counter()
    events = []

    try:
        async for event in remote_app.async_stream_query(
            user_id=USER_ID,
            session_id=session_id,
            message=query,
        ):
            events.append(event)

        latency_ms = (time.perf_counter() - start) * 1000
        return QueryResult(
            query=query,
            success=True,
            response=extract_final_response(events),
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start) * 1000
        return QueryResult(query=query, success=False, error=str(e), latency_ms=latency_ms)


async def main(queries: list[str] = None, benchmark: bool = False):
    queries = queries or DEFAULT_QUERIES

    print(f"Project: {PROJECT_ID}")
    print(f"Resource ID: {RESOURCE_ID}")

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    remote_app = agent_engines.get(RESOURCE_NAME)

    # Create session
    session = remote_app.create_session(user_id=USER_ID)
    session_id = session.get("id") if isinstance(session, dict) else session.id
    print(f"Session: {session_id}")

    # Pre-warm cache
    print(f"\n[PRE-WARM] Sending: '{PREWARM_QUERY}'")
    prewarm = await run_query(remote_app, session_id, PREWARM_QUERY)
    print(f"[PRE-WARM] Done in {prewarm.latency_ms:.0f}ms")

    # Run queries
    results = []
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] {query}")
        result = await run_query(remote_app, session_id, query)
        results.append(result)
        print(f"  {'PASS' if result.success else 'FAIL'} - {result.latency_ms:.0f}ms")
        if result.success and not benchmark:
            print(f"  {result.response[:200]}...")

    # Summary
    if benchmark:
        successful = [r for r in results if r.success]
        if successful:
            latencies = [r.latency_ms for r in successful]
            print(f"\n--- BENCHMARK ---")
            print(f"Queries: {len(results)}, Passed: {len(successful)}")
            print(f"Avg: {sum(latencies)/len(latencies):.0f}ms")
            print(f"Min: {min(latencies):.0f}ms, Max: {max(latencies):.0f}ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("queries", nargs="*", help="Custom queries")
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()

    asyncio.run(main(
        queries=args.queries if args.queries else None,
        benchmark=args.benchmark,
    ))
```

### Verify Deployment
```bash
# List deployed agents
gcloud ai reasoning-engines list --region=us-central1

# Get agent details
gcloud ai reasoning-engines describe RESOURCE_ID --region=us-central1
```

---

## Deployment Option 2: Google Cloud Run

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY <agent_package>/ <agent_package>/

# Install dependencies
RUN uv sync

EXPOSE 8080

CMD ["uv", "run", "adk", "api_server", "--port", "8080", "<agent_package>"]
```

### Deploy to Cloud Run
```bash
gcloud run deploy my-agent-service \
  --source . \
  --region us-central1 \
  --project $GOOGLE_CLOUD_PROJECT \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=1"
```

---

## Deployment Option 3: Local Development

### Run with Web UI
```bash
cd apps/<agent-name>
uv run adk web
# Opens at http://localhost:8000
```

### Run in Terminal
```bash
uv run adk run <agent_package>
```

### Local Environment (.env)
```bash
# For local dev, use API key
GOOGLE_API_KEY=AIza...

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key

# OpenAI
OPENAI_API_KEY=sk-...
```

---

## Prompt Caching Optimization

### Why It Matters
Gemini automatically caches repeated prompt content, reducing latency by 20-30% after the first few queries.

### How to Optimize

1. **Static content FIRST, dynamic content LAST**:
```python
# config.py

# STATIC: Schema, examples, rules (will be cached)
SQL_AGENT_STATIC_INSTRUCTION = """You are a PostgreSQL expert.

{SCHEMA_CONTEXT}

RULES:
- Only SELECT queries
- Use ILIKE for text matching
...
"""

# DYNAMIC: Append at END
def build_sql_agent_instruction() -> str:
    return f"""{SQL_AGENT_STATIC_INSTRUCTION}

---
CURRENT DATE: Today is {get_today_date()}. Use CURRENT_DATE in SQL.
"""
```

2. **Use builder functions in agents**:
```python
# agent.py
from .config import build_orchestrator_instruction

orchestrator = LlmAgent(
    name="orchestrator",
    instruction=build_orchestrator_instruction(),  # Dynamic date at END
    ...
)
```

### Pre-Warming Sessions
Send a lightweight query after session creation to prime the cache:
```python
PREWARM_QUERY = "ready"

async def prewarm_session(remote_app, session_id):
    async for _ in remote_app.async_stream_query(
        user_id=USER_ID,
        session_id=session_id,
        message=PREWARM_QUERY,
    ):
        pass
    print("Cache primed")
```

---

## Performance Benchmarks

### Expected Latencies (Agent Engine, us-central1)

| Query Type | Latency Range |
|------------|---------------|
| Simple SQL | 3-5s |
| Complex SQL | 5-8s |
| Vector Search | 5-7s |
| Hybrid Query | 7-10s |
| Pre-warm | 4-6s |

### Optimization Checklist
- [ ] Static instructions placed FIRST
- [ ] Dynamic content (dates) at END
- [ ] Pre-warming enabled
- [ ] Appropriate region selected (us-central1 recommended)
- [ ] Cloud Trace enabled for monitoring

---

## Common Issues and Solutions

### Issue: "Project/location and API key are mutually exclusive"
**Cause**: Using `GOOGLE_API_KEY` with Agent Engine
**Fix**: Set `GOOGLE_GENAI_USE_VERTEXAI=1`, remove `GOOGLE_API_KEY`

### Issue: Session creation fails
**Cause**: Agent Engine uses Vertex AI session service
**Fix**: Ensure `GOOGLE_GENAI_USE_VERTEXAI=1` is set

### Issue: "Module not found" during deployment
**Cause**: Package not in `extra_packages`
**Fix**: Add `"./your_package"` to `extra_packages` list

### Issue: Secrets not accessible
**Cause**: Service account lacks Secret Manager access
**Fix**: Grant `roles/secretmanager.secretAccessor` to Compute Engine service account

```bash
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Issue: High latency on first query
**Cause**: Cold start + no cache
**Fix**: Implement pre-warming, optimize prompt structure

---

## Deployment Checklist

### Before Deployment
- [ ] `root_agent` exported from `__init__.py`
- [ ] All dependencies in `requirements` list
- [ ] Secrets stored in Secret Manager
- [ ] `GOOGLE_GENAI_USE_VERTEXAI=1` set (NOT API key)
- [ ] Staging bucket created
- [ ] Required APIs enabled

### After Deployment
- [ ] Note Resource ID from output
- [ ] Update test script with new Resource ID
- [ ] Run test queries
- [ ] Run benchmark
- [ ] Check Cloud Trace for errors
- [ ] Monitor logs: `gcloud logging read "resource.type=reasoning_engine"`

---

## Success Criteria

- [ ] Agent deployed without errors
- [ ] Test queries returning expected results
- [ ] Latency within acceptable range (< 10s average)
- [ ] No authentication errors
- [ ] Secrets properly loaded
- [ ] Pre-warming working
