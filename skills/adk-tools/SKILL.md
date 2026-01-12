---
name: adk-tools
description: Create custom tools for Google ADK agents including function tools, MCP integration, and third-party tool adapters. Use when user says "create tool", "custom tool", "add tool", "MCP integration", or needs to extend agent capabilities.
---

# ADK Tools Creation Skill

## Purpose
Create custom tools that extend ADK agent capabilities. Tools allow agents to interact with external systems, APIs, databases, and perform specialized tasks beyond LLM reasoning.

## When to Activate
Activate when user mentions:
- "create tool", "custom tool", "add tool"
- "function tool", "agent tool"
- "MCP integration", "model context protocol"
- "google search tool", "code execution"
- "extend agent capabilities"

## Tool Types Overview

| Tool Type | Use Case | Example |
|-----------|----------|---------|
| **Function Tool** | Custom Python functions | Database queries, API calls |
| **Built-in Tool** | Google-provided tools | `google_search`, `BuiltInCodeExecutor` |
| **MCP Tool** | Model Context Protocol | Notion, Slack, external services |
| **AgentTool** | Agent as a tool | Specialist agent delegation |
| **Third-party** | External libraries | LangChain, LlamaIndex tools |

---

## Function Tools (Most Common)

### Basic Structure
```python
from google.adk.tools import ToolContext


def my_tool(
    param1: str,
    param2: int,
    tool_context: ToolContext,  # MUST be LAST parameter
) -> str:
    """
    Brief description of what the tool does.

    Args:
        param1 (str): Description of param1
        param2 (int): Description of param2
        tool_context (ToolContext): ADK context for state access (ALWAYS LAST)

    Returns:
        Description of what is returned
    """
    # Tool implementation
    result = f"Processed {param1} with value {param2}"

    # Optionally access/modify session state
    tool_context.state["last_result"] = result

    return result
```

### Critical Rules for Function Tools

1. **ToolContext MUST be last parameter** - ADK injects it automatically
2. **Type hints required** - All parameters need type annotations
3. **Docstring required** - LLM uses it to understand the tool
4. **Return string** - Return value should be string for LLM consumption

---

## Tool Creation Workflow

### Step 1: Gather Requirements
Ask the user:
1. What capability does the agent need?
2. What external systems will it interact with?
3. What parameters are needed?
4. Should it read/write session state?

### Step 2: Design the Tool Interface
```python
# Define clear input/output contract
def tool_name(
    required_param: str,           # Required parameters first
    optional_param: str = "default", # Optional with defaults
    tool_context: ToolContext,     # ALWAYS LAST
) -> str:
    """Clear description for the LLM."""
    pass
```

### Step 3: Create Tools File
```
<agent_package>/
├── __init__.py
├── agent.py
├── config.py
└── tools.py          # All custom tools here
```

---

## Function Tool Examples

### 1. Session State Tool
```python
"""Tools for managing session state."""

from google.adk.tools import ToolContext


def save_data(
    key: str,
    value: str,
    tool_context: ToolContext,
) -> str:
    """
    Save data to session state for later use.

    Args:
        key (str): The key to store the data under
        value (str): The value to store
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        Confirmation message
    """
    tool_context.state[key] = value
    return f"Successfully saved data to '{key}'."


def get_data(
    key: str,
    tool_context: ToolContext,
) -> str:
    """
    Retrieve data from session state.

    Args:
        key (str): The key to retrieve data from
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        The stored value or error message
    """
    value = tool_context.state.get(key)
    if value is not None:
        return str(value)
    return f"No data found for key '{key}'."


def list_keys(tool_context: ToolContext) -> str:
    """
    List all keys in session state.

    Args:
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        Comma-separated list of keys
    """
    keys = list(tool_context.state.keys())
    if keys:
        return f"Available keys: {', '.join(keys)}"
    return "Session state is empty."
```

### 2. API Integration Tool
```python
"""Tools for external API integration."""

import httpx
from google.adk.tools import ToolContext


async def fetch_weather(
    city: str,
    tool_context: ToolContext,
) -> str:
    """
    Fetch current weather for a city.

    Args:
        city (str): City name to get weather for
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        Weather information or error message
    """
    api_key = tool_context.state.get("weather_api_key", "")
    if not api_key:
        return "Error: Weather API key not configured."

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.weather.com/v1/current",
                params={"city": city, "key": api_key},
            )
            response.raise_for_status()
            data = response.json()
            return f"Weather in {city}: {data['temp']}°F, {data['condition']}"
    except httpx.HTTPError as e:
        return f"Error fetching weather: {e}"
```

### 3. Database Tool
```python
"""Tools for database operations."""

from google.adk.tools import ToolContext


def query_database(
    query: str,
    tool_context: ToolContext,
) -> str:
    """
    Execute a read-only database query.

    Args:
        query (str): SQL SELECT query to execute
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        Query results as formatted string
    """
    # Validate query is read-only
    if not query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries are allowed."

    db_url = tool_context.state.get("database_url")
    if not db_url:
        return "Error: Database not configured."

    try:
        # Execute query (pseudocode - use your DB library)
        # results = execute_query(db_url, query)
        results = [{"id": 1, "name": "Example"}]  # Placeholder

        if not results:
            return "Query returned no results."

        # Format results for LLM
        formatted = "\n".join([str(row) for row in results])
        return f"Query results:\n{formatted}"
    except Exception as e:
        return f"Database error: {e}"
```

### 4. File Processing Tool
```python
"""Tools for file operations."""

import json
from pathlib import Path
from google.adk.tools import ToolContext


def read_json_file(
    file_path: str,
    tool_context: ToolContext,
) -> str:
    """
    Read and parse a JSON file.

    Args:
        file_path (str): Path to the JSON file
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        JSON content as formatted string
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"

        if not path.suffix == ".json":
            return "Error: Only JSON files are supported."

        with open(path) as f:
            data = json.load(f)

        # Store in session for later use
        tool_context.state["last_file_data"] = data

        return json.dumps(data, indent=2)
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}"
    except Exception as e:
        return f"Error reading file: {e}"
```

### 5. Structured Output Tool
```python
"""Tools that return structured data."""

import json
from google.adk.tools import ToolContext
from pydantic import BaseModel


class AnalysisResult(BaseModel):
    """Structured analysis result."""
    score: float
    category: str
    findings: list[str]
    recommendations: list[str]


def analyze_text(
    text: str,
    analysis_type: str,
    tool_context: ToolContext,
) -> str:
    """
    Analyze text and return structured results.

    Args:
        text (str): Text to analyze
        analysis_type (str): Type of analysis (sentiment, topic, quality)
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        JSON-formatted analysis results
    """
    # Perform analysis (placeholder logic)
    result = AnalysisResult(
        score=0.85,
        category=analysis_type,
        findings=["Finding 1", "Finding 2"],
        recommendations=["Recommendation 1"],
    )

    # Store structured result in state
    tool_context.state["last_analysis"] = result.model_dump()

    # Return as JSON for LLM
    return result.model_dump_json(indent=2)
```

### 6. Frontend Integration Tool (Production Pattern)

```python
"""Tools that store results for frontend/external retrieval.

When Agent Engine serves a frontend (PWA, mobile, web), the frontend often
needs structured data alongside the text response. Store query results in
session state so frontends can fetch them via the session API.
"""

import json
from google.adk.tools import ToolContext


def execute_sql(
    query: str,
    tool_context: ToolContext,
) -> str:
    """
    Execute SQL and store results for frontend retrieval.

    Results are stored in session state with consistent keys that
    the frontend can retrieve after the query completes.

    Args:
        query (str): SQL SELECT query to execute
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        Formatted query results for LLM
    """
    user_id = tool_context.state.get("user_id")

    # Validate query
    if not query.strip().upper().startswith("SELECT"):
        return "Error: Only SELECT queries allowed."

    # Execute query with RLS
    result = supabase.rpc(
        "exec_sql_secure",
        {"param_sql": query, "user_id": user_id}
    ).execute()

    # CRITICAL: Store in session state for frontend retrieval
    # Only store if result contains actual data (not just aggregations)
    if result.data and isinstance(result.data, list) and len(result.data) > 0:
        first_item = result.data[0] if isinstance(result.data[0], dict) else {}
        # Check if this looks like receipt/product data
        if "id" in first_item or "product_description" in first_item:
            tool_context.state["last_receipts"] = result.data
            tool_context.state["query_type"] = "sql"
            tool_context.state["receipt_count"] = len(result.data)

    # Return formatted text for LLM response
    return json.dumps(result.data, indent=2, default=str)
```

**Key Points:**

1. **Dual output**: Return text for LLM, store structured data in state
2. **Consistent keys**: Use documented keys (`last_receipts`, `query_type`, etc.)
3. **Frontend fetches state**: After query, frontend calls session API to get data
4. **Graceful degradation**: If state storage fails, text response still works

See `adk-sessions/SKILL.md` Pattern 5 for complete frontend integration details.

---

## Built-in Tools

### Google Search
```python
from google.adk.tools import google_search

agent = LlmAgent(
    name="researcher",
    tools=[google_search],
    instruction="Use google_search to find information...",
)
```

### Code Execution
```python
from google.adk.code_executors import BuiltInCodeExecutor

agent = LlmAgent(
    name="coder",
    code_executor=BuiltInCodeExecutor(),
    instruction="You can write and execute Python code...",
)
```

### Google Search Tool Class
```python
from google.adk.tools.google_search_tool import GoogleSearchTool

# With custom configuration
search_tool = GoogleSearchTool(
    bypass_multi_tools_limit=True,  # Convert to function tool
)

agent = LlmAgent(
    tools=[search_tool, my_custom_tool],  # Mix with custom tools
)
```

---

## MCP (Model Context Protocol) Tools

### Basic MCP Integration
```python
from google.adk.tools import McpToolset
from mcp import StdioServerParameters

# Connect to MCP server
mcp_tools = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@notionhq/notion-mcp-server"],
        env={"OPENAPI_MCP_HEADERS": notion_headers},
    )
)

agent = LlmAgent(
    name="notion_assistant",
    tools=[mcp_tools],
    instruction="Use the Notion tools to manage pages...",
)
```

### MCP with SSE (Server-Sent Events)
```python
from google.adk.tools import McpToolset
from mcp import SseServerParameters

mcp_tools = McpToolset(
    connection_params=SseServerParameters(
        url="https://your-mcp-server.com/sse",
        headers={"Authorization": f"Bearer {token}"},
    )
)
```

### Popular MCP Servers
| Server | Purpose | Package |
|--------|---------|---------|
| Notion | Workspace management | `@notionhq/notion-mcp-server` |
| Slack | Team communication | `@anthropic/mcp-server-slack` |
| GitHub | Repository management | `@anthropic/mcp-server-github` |
| Filesystem | File operations | `@anthropic/mcp-server-filesystem` |

---

## AgentTool - Agent as Tool

### Wrapping an Agent
```python
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

# Specialist agent
search_specialist = LlmAgent(
    name="search_specialist",
    model="gemini-2.5-flash",
    tools=[google_search],
    description="Expert at web research",
    instruction="You are a search specialist...",
)

# Wrap as tool
search_tool = AgentTool(agent=search_specialist)

# Parent agent uses specialist as tool
coordinator = LlmAgent(
    name="coordinator",
    tools=[search_tool],  # Can call search_specialist
    instruction="Use search_specialist when you need web research...",
)
```

### Multiple AgentTools
```python
from google.adk.tools.agent_tool import AgentTool

# Multiple specialists
tools = [
    AgentTool(agent=search_agent),
    AgentTool(agent=coding_agent),
    AgentTool(agent=analysis_agent),
]

root_agent = LlmAgent(
    name="orchestrator",
    tools=tools,
    instruction="Delegate to specialists as needed...",
)
```

---

## Third-Party Tool Integration

### LangChain Tools
```python
from langchain.tools import DuckDuckGoSearchRun
from google.adk.tools import wrap_langchain_tool

# Wrap LangChain tool for ADK
ddg_search = wrap_langchain_tool(DuckDuckGoSearchRun())

agent = LlmAgent(
    tools=[ddg_search],
)
```

### LlamaIndex Tools
```python
from llama_index.tools import QueryEngineTool
from google.adk.tools import wrap_llamaindex_tool

# Wrap LlamaIndex tool
query_tool = wrap_llamaindex_tool(QueryEngineTool(...))

agent = LlmAgent(
    tools=[query_tool],
)
```

---

## Tool Best Practices

### 1. Clear Docstrings
```python
def my_tool(param: str, tool_context: ToolContext) -> str:
    """
    One-line summary of what the tool does.

    Use this tool when you need to [specific use case].
    Do NOT use this tool for [anti-patterns].

    Args:
        param (str): Detailed description of the parameter
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        What the tool returns and in what format

    Example:
        Input: "example input"
        Output: "example output"
    """
```

### 2. Error Handling
```python
def safe_tool(param: str, tool_context: ToolContext) -> str:
    """Tool with proper error handling."""
    try:
        # Validate input
        if not param:
            return "Error: Parameter cannot be empty."

        # Perform operation
        result = do_something(param)
        return f"Success: {result}"

    except ValueError as e:
        return f"Validation error: {e}"
    except ConnectionError as e:
        return f"Connection error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"
```

### 3. Input Validation
```python
from typing import Literal

def validated_tool(
    action: Literal["create", "read", "update", "delete"],
    resource_id: str,
    tool_context: ToolContext,
) -> str:
    """Tool with type-validated inputs."""
    # Literal type ensures only valid actions
    if not resource_id.isalnum():
        return "Error: Invalid resource ID format."

    # Proceed with validated inputs
    ...
```

### 4. Async Tools
```python
async def async_tool(
    url: str,
    tool_context: ToolContext,
) -> str:
    """Async tool for I/O operations."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

---

## Registering Tools with Agents

### Single Tool
```python
agent = LlmAgent(
    tools=[my_tool],
)
```

### Multiple Tools
```python
agent = LlmAgent(
    tools=[tool1, tool2, tool3],
)
```

### Mixed Tool Types
```python
agent = LlmAgent(
    tools=[
        google_search,           # Built-in
        my_custom_tool,          # Function tool
        AgentTool(specialist),   # Agent as tool
        mcp_toolset,             # MCP tools
    ],
)
```

---

## Common Pitfalls

1. **ToolContext not last**: Always put `tool_context: ToolContext` as the last parameter
2. **Missing type hints**: All parameters need type annotations
3. **Missing docstring**: LLM needs docstring to understand the tool
4. **Returning non-string**: Always return string for LLM consumption
5. **Not handling errors**: Always catch and return friendly error messages

---

## Success Criteria
- Tool function has proper signature (ToolContext last)
- Type hints on all parameters
- Clear docstring with Args and Returns
- Error handling with friendly messages
- Tool registered with agent via `tools=[]`
