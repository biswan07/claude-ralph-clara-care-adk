---
name: adk-sessions
description: Configure Google ADK session management and state patterns for agent communication. Use when user says "session management", "state management", "session service", "agent memory", or needs to manage data flow between agents.
---

# ADK Sessions & State Management Skill

## Purpose
Configure session services and implement state management patterns for ADK agents. Sessions enable agents to maintain context, share data, and persist information across interactions.

## When to Activate
Activate when user mentions:
- "session management", "state management"
- "session service", "agent memory"
- "output_key", "session state"
- "data flow between agents"
- "persist agent data", "agent context"

## Session Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Session Service                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    Session                           │    │
│  │  ┌─────────────────────────────────────────────┐    │    │
│  │  │              Session State                   │    │    │
│  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐     │    │    │
│  │  │  │ key1    │  │ key2    │  │ key3    │     │    │    │
│  │  │  │ value1  │  │ value2  │  │ value3  │     │    │    │
│  │  │  └─────────┘  └─────────┘  └─────────┘     │    │    │
│  │  └─────────────────────────────────────────────┘    │    │
│  │                                                      │    │
│  │  user_id: "user123"                                 │    │
│  │  session_id: "sess_abc"                             │    │
│  │  app_name: "my_agent"                               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Session Service Types

| Service | Persistence | Best For | Performance |
|---------|-------------|----------|-------------|
| **InMemorySessionService** | None (RAM only) | Development, testing | Fastest |
| **SqliteSessionService** | Local file | Local development | Fast |
| **DatabaseSessionService** | PostgreSQL/MySQL | Production (self-managed) | Good |
| **VertexAiSessionService** | Google Cloud | Production (managed) | Good |

---

## Session Service Configuration

### 1. InMemorySessionService (Development)
```python
"""In-memory sessions for development and testing."""

from google.adk.sessions import InMemorySessionService

# Simple initialization - no persistence
session_service = InMemorySessionService()

# Usage with runner
from google.adk.runners import Runner

runner = Runner(
    agent=root_agent,
    session_service=session_service,
    app_name="my_agent",
)
```

**Characteristics:**
- Data lost on restart
- No setup required
- Perfect for testing
- Fast performance

---

### 2. SqliteSessionService (Local Persistence)
```python
"""SQLite sessions for local development with persistence."""

from google.adk.sessions import SqliteSessionService

# Persists to local SQLite file
session_service = SqliteSessionService(
    db_path="sessions.db",  # Local file path
)

# Or use in-memory SQLite (for testing with SQL features)
session_service = SqliteSessionService(
    db_path=":memory:",
)
```

**Characteristics:**
- Persists across restarts
- Single file, portable
- Good for local development
- No external dependencies

---

### 3. DatabaseSessionService (Production)
```python
"""PostgreSQL/MySQL sessions for production."""

from google.adk.sessions import DatabaseSessionService

# PostgreSQL connection
session_service = DatabaseSessionService(
    connection_string="postgresql://user:pass@host:5432/dbname",
)

# MySQL connection
session_service = DatabaseSessionService(
    connection_string="mysql://user:pass@host:3306/dbname",
)
```

**Characteristics:**
- Full production persistence
- Scalable across instances
- Requires database setup
- Transaction support

---

### 4. VertexAiSessionService (Google Cloud)
```python
"""Vertex AI sessions for Google Cloud production."""

from google.adk.sessions import VertexAiSessionService

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"

session_service = VertexAiSessionService(
    project=PROJECT_ID,
    location=LOCATION,
)

# The app_name should be the Reasoning Engine ID
REASONING_ENGINE_APP_NAME = (
    f"projects/{PROJECT_ID}/locations/{LOCATION}/"
    f"reasoningEngines/your-engine-id"
)
```

**Characteristics:**
- Fully managed by Google
- Integrates with Agent Engine
- Automatic scaling
- Built-in monitoring

---

## State Management Patterns

### Pattern 1: output_key (Automatic State Saving)

```python
from google.adk.agents import LlmAgent

# Agent automatically saves its final output to session state
agent = LlmAgent(
    name="researcher",
    output_key="research_findings",  # Saves output here
    instruction="Research the given topic...",
)

# After agent runs, state["research_findings"] contains the output
```

**How it works:**
1. Agent completes its task
2. Final text output is automatically saved to `state[output_key]`
3. Subsequent agents can read via `{output_key}` placeholder

---

### Pattern 2: {placeholder} (Reading from State)

```python
from google.adk.agents import LlmAgent

# Agent reads from session state using placeholder syntax
agent = LlmAgent(
    name="writer",
    instruction="""
    Based on the research findings: {research_findings}

    Write a comprehensive article...
    """,
)

# {research_findings} is replaced with state["research_findings"]
```

**Placeholder rules:**
- Use `{key_name}` syntax in instructions
- Key must exist in session state
- Replaced before agent execution
- Works in any string field

---

### Pattern 3: ToolContext (Manual State Access)

```python
from google.adk.tools import ToolContext


def save_analysis(
    data: str,
    category: str,
    tool_context: ToolContext,  # ALWAYS LAST
) -> str:
    """Save analysis data to session state."""
    # Write to state
    tool_context.state["analysis_data"] = data
    tool_context.state["analysis_category"] = category

    # Read from state
    previous = tool_context.state.get("previous_analysis", "None")

    return f"Saved analysis. Previous: {previous}"
```

**ToolContext capabilities:**
- Read any state key: `tool_context.state.get("key")`
- Write any state key: `tool_context.state["key"] = value`
- Check key exists: `"key" in tool_context.state`
- Delete key: `del tool_context.state["key"]`

---

### Pattern 4: Callbacks (State Preparation)

```python
from google.adk.agents.callback_context import CallbackContext
from datetime import datetime, timezone


def prepare_state(callback_context: CallbackContext) -> None:
    """Prepare session state before agent runs."""
    # Add computed values
    callback_context.state["current_date"] = (
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    callback_context.state["current_time"] = (
        datetime.now(timezone.utc).strftime("%H:%M:%S")
    )

    # Initialize defaults if not present
    if "iteration_count" not in callback_context.state:
        callback_context.state["iteration_count"] = 0


agent = LlmAgent(
    name="my_agent",
    before_agent_callback=prepare_state,
    instruction="Today is {current_date}...",
)
```

---

## Multi-Agent State Flow

### Sequential State Flow
```python
from google.adk.agents import SequentialAgent, LlmAgent

# Agent 1: Saves to state
agent1 = LlmAgent(
    name="step1",
    output_key="step1_result",
    instruction="Analyze the input...",
)

# Agent 2: Reads from state, saves new result
agent2 = LlmAgent(
    name="step2",
    output_key="step2_result",
    instruction="Process step1 result: {step1_result}",
)

# Agent 3: Reads multiple state keys
agent3 = LlmAgent(
    name="step3",
    output_key="final_result",
    instruction="""
    Combine results:
    - Step 1: {step1_result}
    - Step 2: {step2_result}
    """,
)

pipeline = SequentialAgent(
    name="pipeline",
    sub_agents=[agent1, agent2, agent3],
)
```

**State flow:**
```
Initial State: {}
After Agent1: {"step1_result": "..."}
After Agent2: {"step1_result": "...", "step2_result": "..."}
After Agent3: {"step1_result": "...", "step2_result": "...", "final_result": "..."}
```

---

### Parallel State Flow
```python
from google.adk.agents import ParallelAgent, LlmAgent

# Each parallel agent writes to UNIQUE key
fetcher1 = LlmAgent(
    name="fetcher1",
    output_key="source1_data",  # Unique key
    instruction="Fetch from source 1...",
)

fetcher2 = LlmAgent(
    name="fetcher2",
    output_key="source2_data",  # Unique key
    instruction="Fetch from source 2...",
)

fetcher3 = LlmAgent(
    name="fetcher3",
    output_key="source3_data",  # Unique key
    instruction="Fetch from source 3...",
)

parallel = ParallelAgent(
    name="parallel_fetch",
    sub_agents=[fetcher1, fetcher2, fetcher3],
)

# Gatherer reads all parallel results
gatherer = LlmAgent(
    name="gatherer",
    instruction="""
    Combine all sources:
    - Source 1: {source1_data}
    - Source 2: {source2_data}
    - Source 3: {source3_data}
    """,
)
```

**Critical:** Each parallel agent MUST use unique `output_key` to avoid conflicts.

---

### Loop State Flow
```python
from google.adk.agents import LoopAgent, LlmAgent

# Action agent reads feedback from previous iteration
action = LlmAgent(
    name="action",
    output_key="action_result",
    instruction="""
    Previous feedback: {evaluation_feedback}

    Improve based on feedback...
    """,
)

# Evaluator provides feedback for next iteration
evaluator = LlmAgent(
    name="evaluator",
    output_key="evaluation_feedback",
    instruction="""
    Evaluate: {action_result}

    Provide specific improvement feedback.
    """,
)

loop = LoopAgent(
    name="refinement_loop",
    max_iterations=3,
    sub_agents=[action, evaluator, checker],
)
```

**Loop state persists across iterations:**
```
Iteration 1: action writes → evaluator reads/writes → checker checks
Iteration 2: action reads feedback → improves → evaluator re-evaluates
...continues until exit condition or max_iterations
```

---

## Session Management Operations

### Creating Sessions
```python
async def create_user_session():
    session = await session_service.create_session(
        app_name="my_agent",
        user_id="user123",
        state={
            "preferences": {"language": "en"},
            "context": "customer_support",
        },
    )
    return session
```

### Retrieving Sessions
```python
async def get_session():
    session = await session_service.get_session(
        app_name="my_agent",
        user_id="user123",
        session_id="session_abc",
    )
    return session
```

### Updating Session State
```python
async def update_session_state():
    await session_service.update_session_state(
        app_name="my_agent",
        user_id="user123",
        session_id="session_abc",
        state={"new_key": "new_value"},
    )
```

### Listing User Sessions
```python
async def list_user_sessions():
    sessions = await session_service.list_sessions(
        app_name="my_agent",
        user_id="user123",
    )
    return sessions
```

---

## Environment-Based Configuration

```python
"""Session service configuration based on environment."""

import os
from google.adk.sessions import (
    InMemorySessionService,
    SqliteSessionService,
    DatabaseSessionService,
    VertexAiSessionService,
)


def get_session_service():
    """Get appropriate session service for environment."""
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "development":
        # Fast, no persistence needed
        return InMemorySessionService()

    elif environment == "local":
        # Local persistence for debugging
        return SqliteSessionService(db_path="sessions.db")

    elif environment == "staging":
        # Database for staging
        db_url = os.getenv("DATABASE_URL")
        return DatabaseSessionService(connection_string=db_url)

    elif environment == "production":
        # Vertex AI for production
        return VertexAiSessionService(
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        )

    else:
        raise ValueError(f"Unknown environment: {environment}")


session_service = get_session_service()
```

---

## State Best Practices

### 1. Descriptive Key Names
```python
# Good - Clear purpose
output_key="competitor_analysis_results"
output_key="user_preferences"
output_key="validation_errors"

# Bad - Vague
output_key="data"
output_key="result"
output_key="temp"
```

### 2. Structured Data
```python
# Store structured data for complex information
tool_context.state["analysis"] = {
    "score": 0.85,
    "findings": ["finding1", "finding2"],
    "timestamp": "2025-01-12T10:00:00Z",
}
```

### 3. Namespace Keys
```python
# Use prefixes for multi-agent systems
output_key="research_agent_findings"
output_key="validation_agent_errors"
output_key="report_agent_output"
```

### 4. Clean Up Temporary State
```python
def cleanup_temp_state(callback_context: CallbackContext) -> None:
    """Clean up temporary keys after processing."""
    temp_keys = [k for k in callback_context.state if k.startswith("temp_")]
    for key in temp_keys:
        del callback_context.state[key]
```

---

## Pattern 5: Frontend Integration State (Production Pattern)

When building agents that serve frontend applications (PWA, mobile, web), store query results in session state for external retrieval via the Agent Engine REST API.

### Use Case

- Frontend needs structured data (receipts, products, results) alongside the text response
- Agent Engine only returns text response from streaming query
- Frontend fetches session state separately to get structured data

### Implementation Pattern

```python
"""Store results in session state for frontend retrieval."""

from google.adk.tools import ToolContext


def execute_query(
    query: str,
    tool_context: ToolContext,
) -> str:
    """Execute query and store results for frontend."""
    # Execute the query
    results = perform_database_query(query)

    # Store in session state for frontend retrieval
    # Use consistent, documented key names
    tool_context.state["last_results"] = results
    tool_context.state["query_type"] = "sql"  # or "vector", "related"
    tool_context.state["result_count"] = len(results)

    # Return text for LLM response
    return format_results_for_llm(results)
```

### Recommended State Keys

| Key | Type | Description |
| --- | ---- | ----------- |
| `last_receipts` | `list[dict]` | Array of receipt/product objects |
| `query_type` | `str` | Query method: "sql", "vector", "related" |
| `receipt_count` | `int` | Number of results found |
| `search_query` | `str` | Original search terms (for vector) |
| `reference_product` | `str` | Reference item (for related queries) |

### Frontend Retrieval (Agent Engine REST API)

```javascript
// After query completes, fetch session state
async function getSessionState(userId, sessionId) {
  const token = await getAccessToken();
  const url = `${BASE_URL}/${RESOURCE_NAME}/sessions/${sessionId}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
  });

  const sessionData = await response.json();
  return sessionData.state || {};
}

// Usage after agent query
const state = await getSessionState(userId, sessionId);
const receipts = state.last_receipts || [];
const queryType = state.query_type || 'unknown';
```

### Complete Tool Example (Vector Search)

```python
def vector_search(
    query_text: str,
    limit: int = 10,
    tool_context: ToolContext,
) -> str:
    """Search receipts by semantic similarity.

    Results are stored in session state for frontend retrieval.
    """
    user_id = tool_context.state.get("user_id")

    # Generate embedding and search
    embedding = generate_embedding(query_text)
    results = supabase.rpc(
        "vector_search",
        {"query_embedding": embedding, "user_id": user_id, "limit": limit}
    ).execute()

    # Store for frontend (CRITICAL for PWA integration)
    tool_context.state["last_receipts"] = results.data
    tool_context.state["query_type"] = "vector"
    tool_context.state["receipt_count"] = len(results.data)
    tool_context.state["search_query"] = query_text

    # Return formatted text for LLM
    if not results.data:
        return "No matching receipts found."
    return format_receipts_as_text(results.data)
```

### Why This Pattern Works

1. **Separation of concerns**: LLM gets text, frontend gets structured data
2. **No response parsing**: Frontend doesn't need to parse natural language
3. **Consistent format**: Same state keys across all query types
4. **Graceful degradation**: If state fetch fails, text answer still works

---

## Common Pitfalls

1. **Key collisions**: Multiple agents using same `output_key`
2. **Missing keys**: Referencing `{key}` that doesn't exist
3. **Wrong service**: Using InMemory in production
4. **Large state**: Storing too much data in state
5. **No cleanup**: Accumulating stale data
6. **Forgetting frontend state**: Not storing results for external consumers

---

## Debugging State

### Print Current State
```python
def debug_state(tool_context: ToolContext) -> str:
    """Debug tool to inspect session state."""
    import json
    state_copy = dict(tool_context.state)
    return json.dumps(state_copy, indent=2, default=str)
```

### Log State Changes
```python
def prepare_state_with_logging(callback_context: CallbackContext) -> None:
    """Log state before agent runs."""
    import logging
    logging.info(f"State before agent: {dict(callback_context.state)}")
```

---

## Success Criteria
- Appropriate session service for environment
- Unique `output_key` for each agent
- `{placeholder}` syntax used correctly
- State flows documented
- No key collisions in parallel agents
