---
name: adk-llm-agent
description: Create Google ADK LlmAgent - the core AI-powered agent that uses LLMs for reasoning, planning, and task execution. Use when user says "create llm agent", "create adk agent", "new agent", or wants to build an AI agent.
---

# ADK LlmAgent Creation Skill

## Purpose

Create LlmAgent instances - the fundamental building block of Google ADK that uses Large Language Models for intelligent decision-making, natural language understanding, and dynamic tool usage.

## When to Activate

Activate when user mentions:

- "create llm agent", "create adk agent", "new agent"
- "build an AI agent", "make an agent"
- "agent with tools", "agent with instructions"
- "single agent", "specialized agent"

---

## LlmAgent Architecture

### Core Components

```python
from google.adk.agents import LlmAgent
from google.adk.tools import google_search, ToolContext
from google.adk.planners import BuiltInPlanner
from google.genai import types as genai_types

agent = LlmAgent(
    name="agent_name",                    # Required: Unique identifier
    model="gemini-2.5-flash",             # Required: LLM model to use
    description="What this agent does",   # Required: Used for agent delegation
    instruction="Detailed instructions",  # Required: Agent behavior/persona
    tools=[tool1, tool2],                 # Optional: Available tools
    output_key="result_key",              # Optional: Save output to session state
    sub_agents=[agent1, agent2],          # Optional: Child agents for delegation
    planner=BuiltInPlanner(...),          # Optional: Enable thinking/planning
    before_agent_callback=callback_fn,    # Optional: Pre-execution hook
)
```

---

## CRITICAL: Prompt Caching Optimization

### Why It Matters

Gemini automatically caches repeated prompt content, reducing latency by **20-30%** after the first few queries. Proper instruction structure is essential for production agents.

### The Pattern: Static FIRST, Dynamic LAST

```python
# config.py

# STATIC CONTENT (will be cached by Gemini)
SQL_AGENT_STATIC_INSTRUCTION = """You are a PostgreSQL expert.

## DATABASE SCHEMA
{SCHEMA_CONTEXT}

## RULES
- Only SELECT queries allowed
- Use ILIKE for case-insensitive matching
- NEVER include user_id - RLS handles it

## EXAMPLES
Query: "What did I buy in 2024?"
SQL: SELECT * FROM receipts WHERE purchase_date >= '2024-01-01'

Query: "Total spent at Amazon"
SQL: SELECT SUM(amount) FROM receipts WHERE store_name ILIKE '%amazon%'
"""

# DYNAMIC CONTENT - Append at END
def build_sql_agent_instruction() -> str:
    """Build instruction with dynamic date at END for optimal caching."""
    from datetime import date
    today = date.today().strftime("%d %B %Y")

    return f"""{SQL_AGENT_STATIC_INSTRUCTION}

---
CURRENT DATE CONTEXT: Today is {today}. Use CURRENT_DATE in SQL queries.
"""
```

### Using Builder Functions in Agents

```python
# agent.py
from .config import build_sql_agent_instruction

sql_agent = LlmAgent(
    name="sql_agent",
    model=config.model,
    instruction=build_sql_agent_instruction(),  # Dynamic date at END
    ...
)
```

### What Gets Cached

| Content Type | Position | Cached? |
|--------------|----------|---------|
| Schema context | Beginning | Yes |
| Rules and examples | Middle | Yes |
| System instructions | Middle | Yes |
| Today's date | END | No (changes daily) |
| User query | END | No (changes each request) |

### Performance Impact

| Scenario | First Query | Subsequent Queries |
|----------|-------------|-------------------|
| Without optimization | 6-8s | 6-8s |
| With caching (static first) | 6-8s | 4-6s |
| With pre-warming | N/A (hidden) | 4-6s |

---

## Creation Workflow

### Step 1: Gather Requirements

Ask the user:

1. What is the agent's purpose/goal?
2. What tools does it need? (search, database, custom functions)
3. Does it need to save output for other agents? (output_key)
4. Does it need sub-agents for delegation?
5. What static content can be cached? (schema, examples, rules)

### Step 2: Create Directory Structure

```
apps/<agent-name>/
├── <agent_package>/
│   ├── __init__.py           # Export root_agent
│   ├── agent.py              # Main agent definition
│   ├── config.py             # Config + instruction builders
│   ├── tools/                # Custom tools
│   │   ├── __init__.py
│   │   └── my_tools.py
│   └── sub_agents/           # Sub-agents (if needed)
│       └── __init__.py
├── scripts/
│   ├── deploy_to_agent_engine.py
│   └── test_deployed_agent.py
├── tests/
│   └── test_agent.py
├── pyproject.toml
├── requirements.txt
└── .env.example
```

### Step 3: Create Configuration with Instruction Builders

```python
"""Configuration and instruction builders for optimal caching."""

from datetime import date
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Agent configuration from environment variables."""

    model: str = "gemini-2.5-flash"

    # Database
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Embeddings
    openai_api_key: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


config = Config()


def get_today_date() -> str:
    """Get current date for instructions."""
    return date.today().strftime("%d %B %Y")


# =============================================================================
# STATIC INSTRUCTION CONTENT (CACHEABLE)
# =============================================================================

SCHEMA_CONTEXT = """
CREATE TABLE receipts (
    id UUID PRIMARY KEY,
    purchase_date DATE,
    product_description TEXT,
    brand_name TEXT,
    amount NUMERIC,
    store_name TEXT,
    category TEXT
);
"""

AGENT_STATIC_INSTRUCTION = f"""You are a helpful receipt assistant.

## DATABASE SCHEMA
{SCHEMA_CONTEXT}

## YOUR CAPABILITIES
1. Search receipts by product, brand, or store
2. Calculate spending totals and averages
3. Track warranty expiration dates
4. Answer questions about purchase history

## RESPONSE FORMAT
- Be concise but thorough
- Include specific details (amounts, dates, stores)
- Format currency as $X,XXX.XX AUD
"""


# =============================================================================
# DYNAMIC INSTRUCTION BUILDERS (date at END)
# =============================================================================

def build_agent_instruction() -> str:
    """Build instruction with current date at END for caching."""
    return f"""{AGENT_STATIC_INSTRUCTION}

---
CURRENT DATE: Today is {get_today_date()}.
"""


# Legacy export for backward compatibility
AGENT_INSTRUCTION = build_agent_instruction()
```

### Step 4: Create Agent with Builder

```python
"""Main agent definition."""

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext

from .config import config, build_agent_instruction
from .tools import execute_sql, vector_search


def validate_user(callback_context: CallbackContext) -> None:
    """Ensure user_id is set before agent runs."""
    if not callback_context.state.get("user_id"):
        raise ValueError("user_id must be set in session state")


agent = LlmAgent(
    name="receipt_assistant",
    model=config.model,
    description="AI assistant for managing receipts and warranties",
    instruction=build_agent_instruction(),  # Uses builder for caching
    before_agent_callback=validate_user,
    tools=[execute_sql, vector_search],
    output_key="assistant_response",
)

# REQUIRED: Export for ADK discovery
root_agent = agent
```

### Step 5: Create __init__.py

```python
"""Receipt Assistant Agent."""

from .agent import root_agent

__all__ = ["root_agent"]
__version__ = "0.1.0"
```

---

## Key Patterns

### 1. Session State with output_key

```python
# Agent saves its final output to session state automatically
agent = LlmAgent(
    name="researcher",
    output_key="research_results",  # Other agents access via {research_results}
    ...
)
```

### 2. Reading Session State in Instructions

```python
# Use {placeholder} syntax to read from session state
instruction="""
Based on the previous research: {research_results}
Now analyze the findings...
"""
```

### 3. Tools with ToolContext (ALWAYS LAST)

```python
def my_tool(
    param1: str,
    param2: int,
    tool_context: ToolContext,  # MUST be last parameter
) -> str:
    """Tool description for LLM."""
    # Access session state
    user_id = tool_context.state.get("user_id")
    tool_context.state["new_key"] = "value"
    return "result"
```

### 4. Agent as Tool (AgentTool)

```python
from google.adk.tools import AgentTool

# Wrap an agent to be called as a tool by another agent
parent_agent = LlmAgent(
    name="parent",
    tools=[AgentTool(child_agent)],
    ...
)
```

### 5. Built-in Planner with Thinking

```python
from google.adk.planners import BuiltInPlanner
from google.genai import types as genai_types

agent = LlmAgent(
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    ...
)
```

### 6. Callbacks for User Validation

```python
from google.adk.agents.callback_context import CallbackContext
import os

DEFAULT_TEST_USER_ID = os.getenv("TEST_USER_ID", "")


def validate_user(callback_context: CallbackContext) -> None:
    """Prepare user context before agent runs."""
    if not callback_context.state.get("user_id"):
        if DEFAULT_TEST_USER_ID:
            callback_context.state["user_id"] = DEFAULT_TEST_USER_ID
            print(f"[DEV MODE] Using test user_id")
        else:
            raise ValueError("user_id must be set in session state")


agent = LlmAgent(
    before_agent_callback=validate_user,
    ...
)
```

---

## Multi-Agent with AutoFlow

### Orchestrator Pattern

```python
"""Orchestrator that delegates to specialist agents."""

from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool

from .sub_agents import sql_agent, vector_agent, hybrid_agent
from .tools import lookup_brand_derivatives

# Wrap a specialist as a tool (for explicit calling)
brand_search_tool = AgentTool(agent=brand_search_agent)

orchestrator = LlmAgent(
    name="orchestrator",
    model=config.model,
    description="Routes queries to specialist agents",
    instruction=build_orchestrator_instruction(),
    # AutoFlow: LLM decides which sub-agent to use
    sub_agents=[sql_agent, vector_agent, hybrid_agent],
    # Tools available directly to orchestrator
    tools=[lookup_brand_derivatives, brand_search_tool],
    output_key="final_response",
)

root_agent = orchestrator
```

### Specialist Agent Example

```python
"""SQL specialist agent."""

sql_agent = LlmAgent(
    name="sql_agent",
    model=config.model,
    description="""SQL expert for structured queries.

    USE FOR:
    - Date filtering ("purchases in 2024")
    - Store queries ("from JB Hi-Fi")
    - Aggregations ("total spent", "count")
    - Warranty calculations
    """,
    instruction=build_sql_agent_instruction(),
    output_key="sql_result",
    tools=[execute_sql],
)
```

---

## Available Models

| Model | Speed | Capability | Best For |
|-------|-------|------------|----------|
| `gemini-2.5-flash` | Fast | Good | Most use cases (recommended) |
| `gemini-2.5-pro` | Slower | Better | Complex reasoning |
| `gemini-2.0-flash` | Fast | Good | Legacy compatibility |

---

## Best Practices

### DO

- Use instruction builders with static content FIRST
- Put dynamic content (dates) at END of instructions
- Set `output_key` for agents that pass data to others
- Use `before_agent_callback` to validate user context
- Export as `root_agent` for ADK discovery
- Include schema context in SQL agent instructions

### DON'T

- Put dates/timestamps at the beginning of instructions
- Hardcode credentials in code
- Forget to export `root_agent`
- Put `ToolContext` anywhere except LAST in tool signatures
- Mix static and dynamic content randomly

---

## Testing Locally

```bash
# Navigate to agent directory
cd apps/<agent-name>

# Run in terminal mode
uv run adk run <agent_package>

# Run with web UI
uv run adk web

# Run tests
uv run pytest tests/ -v
```

---

## Success Criteria

- [ ] Agent file created with proper structure
- [ ] Instruction builder separates static/dynamic content
- [ ] Static content placed FIRST for caching
- [ ] Dynamic content (dates) at END
- [ ] `before_agent_callback` validates user context
- [ ] Custom tools have `ToolContext` as LAST parameter
- [ ] `root_agent` exported from `__init__.py`
- [ ] Clear instructions with examples
