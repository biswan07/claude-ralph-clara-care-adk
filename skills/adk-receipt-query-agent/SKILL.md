---
name: adk-receipt-query-agent
description: Build an ADK agent that answers user receipt queries using Gemini 2.5. Provides clean, composable tools and lets the LLM reason about how to answer queries. Use when building the Smart Receipts query agent.
---

# ADK Receipt Query Agent Skill

## Purpose
Build a production-ready ADK agent that answers natural language queries about a user's receipts. The agent uses Gemini 2.5 Flash/Pro to reason about queries and decide which tools to use, including combining multiple tools when needed.

## Design Philosophy

**Let the LLM think.** Don't force rigid categories or decision trees. Provide clean, composable tools with clear docstrings, and let Gemini reason about:
- Which tool(s) to use
- What parameters to pass
- How to combine results
- When to ask for clarification

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Architecture                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User Query → Gemini 2.5 Flash/Pro → Reasoning → Tools      │
│                                                              │
│  The LLM reads tool docstrings and decides:                 │
│  • "This needs semantic search" → search_receipts           │
│  • "This needs exact filters" → list_receipts               │
│  • "This needs calculation" → aggregate_receipts            │
│  • "This needs both" → search + aggregate (chained)         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
apps/receipt-query-agent/
├── receipt_query_agent/
│   ├── __init__.py           # Export root_agent
│   ├── agent.py              # Agent definition
│   ├── config.py             # Settings
│   └── tools.py              # 3 composable tools
├── tests/
│   └── test_queries.py       # Test suite
├── pyproject.toml
└── .env.example
```

---

## Implementation

### 1. Configuration (config.py)

```python
"""Configuration for Receipt Query Agent."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Agent configuration from environment."""

    # Model - Gemini 2.5 for strong reasoning
    model: str = "gemini-2.5-flash"

    # Embeddings - OpenAI text-embedding-3-small (384 dimensions)
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Search defaults
    similarity_threshold: float = 0.3
    default_limit: int = 25

    class Config:
        env_file = ".env"
        extra = "ignore"


config = Config()
```

---

### 2. Tools (tools.py) - Clean & Composable

Three tools that can be used independently or combined:

```python
"""
Receipt Query Tools - Clean, composable tools for the LLM to use.

Design principles:
1. Each tool does ONE thing well
2. Clear docstrings guide the LLM
3. Tools can be chained for complex queries
4. All tools respect user_id for data isolation
"""

import json
from typing import Literal

from google.adk.tools import ToolContext
from openai import OpenAI
from supabase import create_client, Client

from .config import config

# Initialize clients
supabase: Client = create_client(
    config.supabase_url,
    config.supabase_service_role_key,
)
openai_client = OpenAI(api_key=config.openai_api_key)


def _get_user_id(tool_context: ToolContext) -> str | None:
    """Get user_id from session state."""
    return tool_context.state.get("user_id")


# =============================================================================
# Tool 1: Semantic Search
# =============================================================================

def search_receipts(
    query: str,
    limit: int = 25,
    tool_context: ToolContext = None,
) -> str:
    """
    Search receipts using natural language. Finds items by meaning, not just
    exact text matches.

    Good for finding:
    - Products by name or description ("vacuum cleaner", "gaming laptop")
    - Brands ("Apple", "Samsung", "Sony")
    - Categories ("electronics", "kitchen appliances")
    - Similar items ("wireless audio devices" finds headphones, speakers, etc.)

    Args:
        query: What to search for - be descriptive
        limit: Max results to return (default 25)
        tool_context: ADK context

    Returns:
        JSON array of matching receipts with: merchant, date, amount,
        product_name, brand, category, warranty info
    """
    user_id = _get_user_id(tool_context)
    if not user_id:
        return json.dumps({"error": "User not authenticated"})

    # Generate embedding using OpenAI text-embedding-3-small (384 dimensions)
    embedding_response = openai_client.embeddings.create(
        model=config.embedding_model,
        input=query,
        dimensions=config.embedding_dimensions,
    )
    query_embedding = embedding_response.data[0].embedding

    # Vector search
    response = supabase.rpc(
        "vector_search",
        {
            "query_embedding": query_embedding,
            "user_id_filter": user_id,
            "match_threshold": config.similarity_threshold,
            "match_count": limit,
        },
    ).execute()

    if not response.data:
        return json.dumps({"message": f"No receipts found matching '{query}'"})

    return json.dumps(response.data, indent=2, default=str)


# =============================================================================
# Tool 2: Filter & List
# =============================================================================

def list_receipts(
    merchant: str | None = None,
    category: str | None = None,
    year: int | None = None,
    month: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 15,
    tool_context: ToolContext = None,
) -> str:
    """
    List receipts with filters. Use for exact matching and date-based queries.

    Good for:
    - Time periods ("purchases in 2024", "bought in October")
    - Specific stores ("from JB Hi-Fi", "at Amazon")
    - Date ranges

    Date shortcuts:
    - Use year=2024 for all of 2024
    - Use year=2024, month=10 for October 2024
    - Use date_from/date_to for custom ranges (YYYY-MM-DD format)

    Args:
        merchant: Store name (partial match)
        category: Category filter
        year: Filter by year (e.g., 2024)
        month: Filter by month 1-12 (requires year)
        date_from: Start date YYYY-MM-DD
        date_to: End date YYYY-MM-DD
        limit: Max results (default 15)
        tool_context: ADK context

    Returns:
        JSON array of receipts matching filters
    """
    user_id = _get_user_id(tool_context)
    if not user_id:
        return json.dumps({"error": "User not authenticated"})

    # Build date range from year/month
    if year and not date_from:
        if month:
            date_from = f"{year}-{month:02d}-01"
            if month == 12:
                date_to = f"{year + 1}-01-01"
            else:
                date_to = f"{year}-{month + 1:02d}-01"
        else:
            date_from = f"{year}-01-01"
            date_to = f"{year + 1}-01-01"

    response = supabase.rpc(
        "sql_list",
        {
            "user_id_filter": user_id,
            "merchant_filter": merchant,
            "category_filter": category,
            "date_start": date_from,
            "date_end": date_to,
            "limit_count": limit,
        },
    ).execute()

    if not response.data:
        return json.dumps({"message": "No receipts found matching your criteria"})

    return json.dumps(response.data, indent=2, default=str)


# =============================================================================
# Tool 3: Aggregate & Calculate
# =============================================================================

def aggregate_receipts(
    operation: Literal["sum", "count", "average", "min", "max"],
    merchant: str | None = None,
    category: str | None = None,
    year: int | None = None,
    month: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    tool_context: ToolContext = None,
) -> str:
    """
    Calculate totals, counts, and averages on receipts.

    Operations:
    - sum: Total amount spent
    - count: Number of purchases
    - average: Average purchase amount
    - min: Smallest purchase
    - max: Largest purchase

    Good for:
    - "How much did I spend at JB Hi-Fi?"
    - "Total spending in 2024"
    - "How many items did I buy?"
    - "Average purchase amount"
    - "What was my biggest purchase?"

    Args:
        operation: sum, count, average, min, or max
        merchant: Filter by store
        category: Filter by category
        year: Filter by year
        month: Filter by month (requires year)
        date_from: Start date YYYY-MM-DD
        date_to: End date YYYY-MM-DD
        tool_context: ADK context

    Returns:
        The calculated result with context
    """
    user_id = _get_user_id(tool_context)
    if not user_id:
        return json.dumps({"error": "User not authenticated"})

    # Build date range
    if year and not date_from:
        if month:
            date_from = f"{year}-{month:02d}-01"
            if month == 12:
                date_to = f"{year + 1}-01-01"
            else:
                date_to = f"{year}-{month + 1:02d}-01"
        else:
            date_from = f"{year}-01-01"
            date_to = f"{year + 1}-01-01"

    # Map operation name
    op_map = {"average": "AVG", "sum": "SUM", "count": "COUNT", "min": "MIN", "max": "MAX"}

    response = supabase.rpc(
        "sql_aggregate",
        {
            "user_id_filter": user_id,
            "operation": op_map.get(operation, operation.upper()),
            "merchant_filter": merchant,
            "category_filter": category,
            "date_start": date_from,
            "date_end": date_to,
        },
    ).execute()

    result = response.data[0] if response.data else {}
    # sql_aggregate returns: operation_type, count_value, aggregate_value
    if operation == "count":
        value = result.get("count_value", 0)
    else:
        value = result.get("aggregate_value", 0)

    # Format response
    context_parts = []
    if merchant:
        context_parts.append(f"at {merchant}")
    if category:
        context_parts.append(f"in {category}")
    if year:
        if month:
            context_parts.append(f"in {month}/{year}")
        else:
            context_parts.append(f"in {year}")

    context = " ".join(context_parts) if context_parts else "total"

    if operation == "count":
        return f"{int(value)} purchases {context}"
    elif operation in ["sum", "average", "min", "max"]:
        return f"${value:,.2f} ({operation} {context})"
    else:
        return str(value)
```

---

### 3. Agent Definition (agent.py)

```python
"""Receipt Query Agent - Let the LLM think."""

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext

from .config import config
from .tools import search_receipts, list_receipts, aggregate_receipts


def validate_user(callback_context: CallbackContext) -> None:
    """Ensure user_id is set before agent runs."""
    if not callback_context.state.get("user_id"):
        raise ValueError("user_id must be set in session state")


INSTRUCTION = """
You are a helpful assistant that answers questions about the user's receipts
and purchase history.

You have three tools available:

1. **search_receipts** - Semantic search for products, brands, descriptions
2. **list_receipts** - Filter by date, store, price, etc.
3. **aggregate_receipts** - Calculate totals, counts, averages

Think about what the user is asking, then decide:
- Need to find items by name/description? → search_receipts
- Need to filter by date/store/price? → list_receipts
- Need totals or counts? → aggregate_receipts
- Complex query? → Use multiple tools

Examples of your reasoning:
- "Show me Apple products" → search for "Apple"
- "What did I buy in 2024?" → list with year=2024
- "How much at JB Hi-Fi?" → aggregate sum with merchant="JB Hi-Fi"
- "Samsung products under $500" → search "Samsung", then filter results
- "Total spent on electronics in 2024" → aggregate with category + year

Always:
- Give clear, helpful answers
- Include relevant details (date, price, store)
- If results are empty, suggest alternatives
- Ask clarifying questions if the query is ambiguous

Currency is AUD (Australian Dollars).
"""

receipt_query_agent = LlmAgent(
    name="receipt_query_agent",
    model=config.model,
    description="Answers questions about receipts, purchases, spending, and warranties",
    instruction=INSTRUCTION,
    before_agent_callback=validate_user,
    tools=[
        search_receipts,
        list_receipts,
        aggregate_receipts,
    ],
)

root_agent = receipt_query_agent
```

---

### 4. Package Init (__init__.py)

```python
"""Receipt Query Agent."""

from .agent import root_agent

__all__ = ["root_agent"]
```

---

### 5. REST Integration

```python
"""Running the agent from a REST endpoint."""

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from receipt_query_agent import root_agent

session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    session_service=session_service,
    app_name="receipt_query_agent",
)


async def query(user_id: str, question: str, session_id: str | None = None):
    """
    Handle a user query.

    Args:
        user_id: Authenticated user's UUID
        question: Natural language question
        session_id: Optional for conversation continuity
    """
    # Create/get session with user_id
    if session_id:
        session = await session_service.get_session(
            app_name="receipt_query_agent",
            user_id=user_id,
            session_id=session_id,
        )
    else:
        session = await session_service.create_session(
            app_name="receipt_query_agent",
            user_id=user_id,
            state={"user_id": user_id},  # Required for tools
        )

    # Run agent
    response_text = []
    async for event in runner.run_async(
        session_id=session.id,
        user_id=user_id,
        new_message=Content(role="user", parts=[Part(text=question)]),
    ):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if hasattr(part, "text"):
                    response_text.append(part.text)

    return {
        "answer": "\n".join(response_text),
        "session_id": session.id,
    }
```

---

### 6. Dependencies (pyproject.toml)

```toml
[project]
name = "receipt-query-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "google-adk>=0.3.0",
    "google-genai>=1.24.0",
    "openai>=1.0.0",
    "supabase>=2.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.23.0"]
```

---

## Test Queries

Use these to validate the agent handles diverse queries:

```python
TEST_QUERIES = [
    # Product/brand (semantic search)
    "vacuum cleaner",
    "Apple products",
    "Samsung devices",
    "gaming console",
    "Bluetooth headphones",

    # Time-based (list with filters)
    "what did I buy in 2024?",
    "purchases in October 2024",
    "show me purchases from last year",

    # Store-based (list with merchant)
    "what did I buy at JB Hi-Fi?",
    "purchases from Amazon",

    # Spending (aggregation)
    "how much did I spend in 2024?",
    "total spent at JB Hi-Fi",
    "how many items did I purchase?",
    "average purchase amount",

    # Complex (LLM chains tools)
    "Apple products under $200",
    "Samsung devices I bought in 2024 and total cost",
    "show me electronics from JB Hi-Fi with prices",
    "have I purchased any PlayStation, when and for how much?",

    # Warranty-related
    "items with warranty",
    "what is the warranty on my Samsung monitor?",
]
```

---

## Why This Design Works

| Aspect | Benefit |
|--------|---------|
| **3 clean tools** | Easy for LLM to understand and use |
| **Clear docstrings** | Guide LLM's tool selection |
| **No rigid routing** | LLM reasons about complex queries |
| **Composable** | LLM can chain tools naturally |
| **Simple instruction** | Doesn't over-constrain the model |

The Gemini 2.5 model will:
1. Read the query
2. Consider which tool(s) help
3. Call tools with appropriate parameters
4. Combine results if needed
5. Format a helpful response

**Trust the model to think.**
