---
name: adk-supabase-tools
description: Create Supabase database tools for Google ADK agents including RPC calls, vector search, CRUD operations, and user context management. Use when user says "supabase tool", "database tool", "vector search tool", "query receipts", or needs to connect ADK agents to Supabase.
---

# ADK Supabase Tools Skill

## Purpose

Create tools that connect ADK agents to Supabase for database operations, vector search, and RPC function calls. This skill covers authentication patterns, user context injection for RLS, and integration with existing Supabase functions.

## When to Activate

Activate when user mentions:

- "supabase tool", "database tool", "db tool"
- "vector search", "semantic search", "embedding search"
- "query receipts", "search receipts"
- "RPC call", "supabase function"
- "user context", "RLS", "row level security"
- "dynamic SQL", "exec_sql"

---

## CRITICAL: Dynamic SQL with RLS (exec_sql_secure)

### The Power Pattern: LLM-Generated SQL with User Isolation

Instead of creating many specialized RPC functions, use **one powerful exec_sql_secure function** that:

1. Sets user context for RLS
2. Executes LLM-generated SQL
3. Resets role after execution

### exec_sql_secure Function (Create in Supabase)

```sql
CREATE OR REPLACE FUNCTION exec_sql_secure(param_sql TEXT, user_id UUID)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    result JSONB;
BEGIN
    -- Set user context for RLS
    PERFORM set_config('app.user_id', user_id::text, true);

    -- Downgrade to authenticated role (RLS applies)
    SET LOCAL ROLE authenticated;

    -- Execute the query and return results as JSON
    EXECUTE 'SELECT COALESCE(jsonb_agg(row_to_json(t)), ''[]''::jsonb) FROM (' || param_sql || ') t'
    INTO result;

    -- Role resets automatically at transaction end
    RETURN result;
END;
$$;

-- Grant execute to service role only
GRANT EXECUTE ON FUNCTION exec_sql_secure TO service_role;
```

### RLS Policy Pattern

```sql
-- Enable RLS on table
ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;

-- Policy uses app.user_id setting
CREATE POLICY "users_own_receipts" ON receipts
    FOR SELECT USING (
        user_id = COALESCE(
            current_setting('app.user_id', true)::uuid,
            auth.uid()
        )
    );
```

### Why This Pattern is Powerful

| Approach | Pros | Cons |
|----------|------|------|
| Many RPC functions | Type-safe, predictable | Limited flexibility, maintenance burden |
| **exec_sql_secure** | Infinite flexibility, one function | Requires SQL validation |

**Best Practice**: Use exec_sql_secure for query agents where the LLM generates SQL dynamically.

---

## Tool Implementation: execute_sql

### The Core Tool for Dynamic SQL

```python
"""Dynamic SQL execution tool with RLS enforcement."""

import json
import re
from google.adk.tools import ToolContext
from supabase import Client

from .config import config


# Dangerous patterns to block
DANGEROUS_PATTERNS = [
    r'\bDROP\b',
    r'\bDELETE\b',
    r'\bUPDATE\b',
    r'\bINSERT\b',
    r'\bALTER\b',
    r'\bTRUNCATE\b',
    r'\bCREATE\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
    r'\bEXEC\b',
    r'\bEXECUTE\b',
    r'--',  # SQL comments (injection vector)
    r'/\*',  # Block comments
    r'\bINTO\b\s+\w+\s+FROM',  # SELECT INTO
]


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate SQL query for safety.

    Returns:
        Tuple of (is_valid, error_message)
    """
    sql_upper = sql.strip().upper()

    # Must start with SELECT or WITH (CTE)
    if not (sql_upper.startswith('SELECT') or sql_upper.startswith('WITH')):
        return False, "Only SELECT queries are allowed"

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, sql_upper):
            return False, f"Query contains forbidden pattern: {pattern}"

    return True, ""


def execute_sql(
    query: str,
    tool_context: ToolContext,
) -> str:
    """
    Execute a SQL SELECT query on the user's data.

    This tool runs SQL queries with automatic Row Level Security (RLS)
    enforcement. The user can only see their own data.

    IMPORTANT:
    - Only SELECT queries are allowed
    - DO NOT include user_id filters - RLS handles this automatically
    - Use ILIKE for case-insensitive text matching
    - Use date ranges: purchase_date >= '2024-01-01' AND purchase_date < '2025-01-01'

    Args:
        query (str): PostgreSQL SELECT query to execute
        tool_context (ToolContext): ADK context with user_id in state

    Returns:
        JSON string with query results or error message
    """
    # Get user_id from session state
    user_id = tool_context.state.get("user_id")
    if not user_id:
        return json.dumps({"error": "User not authenticated", "hint": "user_id must be set in session state"})

    # Validate SQL
    is_valid, error = validate_sql(query)
    if not is_valid:
        return json.dumps({"error": error, "query": query})

    try:
        # Get Supabase client
        from .supabase_client import supabase

        # Execute via exec_sql_secure RPC
        response = supabase.rpc(
            "exec_sql_secure",
            {
                "param_sql": query,
                "user_id": user_id,
            },
        ).execute()

        if response.data is not None:
            # Handle empty results
            if isinstance(response.data, list) and len(response.data) == 0:
                return json.dumps({"message": "No results found", "query": query})

            return json.dumps(response.data, indent=2, default=str)
        else:
            return json.dumps({"message": "Query executed but returned no data"})

    except Exception as e:
        error_msg = str(e)
        # Provide helpful hints for common errors
        hints = []
        if "column" in error_msg.lower() and "does not exist" in error_msg.lower():
            hints.append("Check column names against the schema")
        if "syntax error" in error_msg.lower():
            hints.append("Check SQL syntax - ensure proper quoting and operators")

        return json.dumps({
            "error": f"Query failed: {error_msg}",
            "query": query,
            "hints": hints if hints else None,
        })
```

---

## Schema Context for LLM Instructions

### Embedding Schema in Agent Instructions

The LLM needs schema context to generate valid SQL. Place this in config.py:

```python
"""Database schema context for LLM instructions."""

RECEIPTS_SCHEMA = """
-- RECEIPTS TABLE (primary data source for user purchases)
-- RLS Policy: user_id = current_setting('app.user_id')::uuid
-- The execute_sql tool automatically sets app.user_id, so queries
-- should NOT include user_id filters - RLS handles this automatically.

CREATE TABLE receipts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,              -- DO NOT filter by this - RLS handles it
    purchase_date DATE,                 -- Use for date-based queries
    product_description TEXT,           -- Main product name/description
    brand_name TEXT,                    -- Brand (Apple, Samsung, Sony, etc.)
    model_number TEXT,                  -- Product model identifier
    warranty_period TEXT,               -- e.g., "2 years", "1 year", "90 days"
    extended_warranty TEXT,             -- Additional warranty info
    amount NUMERIC,                     -- Purchase price in AUD
    store_name TEXT,                    -- Retailer (JB Hi-Fi, Amazon, etc.)
    purchase_location TEXT,             -- Physical location if applicable
    category TEXT,                      -- Product category (see allowed values)
    created_at TIMESTAMPTZ
);

-- CATEGORY ALLOWED VALUES:
-- Electronics, Appliances, Grocery, Medicine/Health, Clothing,
-- White Goods, Home & Garden, Automotive, Sports, Office,
-- Entertainment, Food & Dining, Other

-- COMMON QUERY PATTERNS:
-- 1. Date filtering: WHERE purchase_date >= '2024-01-01' AND purchase_date < '2025-01-01'
-- 2. Store filtering: WHERE store_name ILIKE '%JB Hi-Fi%'
-- 3. Brand filtering: WHERE brand_name ILIKE '%Apple%'
-- 4. Category filtering: WHERE category = 'Electronics'
-- 5. Price filtering: WHERE amount > 100 AND amount < 500
-- 6. Aggregations: SELECT SUM(amount), COUNT(*), AVG(amount)
"""


# Warranty calculation CTE template
WARRANTY_CTE_TEMPLATE = """
WITH warranty_calc AS (
    SELECT *,
        purchase_date + (
            CASE
                WHEN warranty_period ILIKE '%year%' THEN
                    (COALESCE(NULLIF(REGEXP_REPLACE(warranty_period, '[^0-9]', '', 'g'), ''), '1')::int * INTERVAL '1 year')
                WHEN warranty_period ILIKE '%month%' THEN
                    (COALESCE(NULLIF(REGEXP_REPLACE(warranty_period, '[^0-9]', '', 'g'), ''), '1')::int * INTERVAL '1 month')
                WHEN warranty_period ILIKE '%day%' THEN
                    (COALESCE(NULLIF(REGEXP_REPLACE(warranty_period, '[^0-9]', '', 'g'), ''), '30')::int * INTERVAL '1 day')
                ELSE INTERVAL '1 year'
            END
        ) as warranty_expiry_date
    FROM receipts
    WHERE warranty_period IS NOT NULL AND warranty_period != ''
)
"""
```

### Using Schema in Agent Instruction

```python
from .config import RECEIPTS_SCHEMA, WARRANTY_CTE_TEMPLATE

SQL_AGENT_INSTRUCTION = f"""You are a PostgreSQL expert for the receipts database.

{RECEIPTS_SCHEMA}

YOUR TASK:
1. Analyze the user's query to understand what data they need
2. Generate a PostgreSQL SELECT query to answer it
3. Execute it using the execute_sql tool
4. Interpret results and provide a detailed response

CRITICAL RULES:
- NEVER include user_id in queries - RLS handles this automatically
- Use ILIKE for case-insensitive text matching
- Always LIMIT results to 50 unless aggregating

WARRANTY CALCULATIONS:
Use this CTE pattern for warranty queries:

{WARRANTY_CTE_TEMPLATE}

Example warranty query:
{WARRANTY_CTE_TEMPLATE}
SELECT product_description, brand_name, warranty_expiry_date,
       warranty_expiry_date - CURRENT_DATE as days_remaining
FROM warranty_calc
WHERE warranty_expiry_date >= CURRENT_DATE
ORDER BY warranty_expiry_date
"""
```

---

## Vector Search with OpenAI Embeddings

### Tool for Semantic Search

```python
"""Vector search tool using OpenAI embeddings."""

import json
from openai import OpenAI
from google.adk.tools import ToolContext

from .config import config


def generate_embedding(text: str) -> list[float]:
    """Generate embedding using OpenAI."""
    client = OpenAI(api_key=config.openai_api_key)

    response = client.embeddings.create(
        model=config.embedding_model,  # text-embedding-3-small
        input=text,
        dimensions=config.embedding_dimensions,  # 384
    )

    return response.data[0].embedding


def vector_search(
    search_terms: str,
    similarity_threshold: float = 0.3,
    limit: int = 25,
    tool_context: ToolContext = None,
) -> str:
    """
    Search receipts using semantic similarity.

    Use this for product/brand searches where meaning matters
    more than exact keywords.

    Args:
        search_terms (str): Rich search terms (expand with synonyms)
        similarity_threshold (float): Minimum similarity (0.0-1.0)
        limit (int): Maximum results to return
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        JSON string with matching receipts and similarity scores
    """
    user_id = tool_context.state.get("user_id")
    if not user_id:
        return json.dumps({"error": "User not authenticated"})

    try:
        # Generate embedding
        embedding = generate_embedding(search_terms)

        # Get Supabase client
        from .supabase_client import supabase

        # Call vector_search RPC
        response = supabase.rpc(
            "vector_search",
            {
                "query_embedding": embedding,
                "user_id_filter": user_id,
                "match_threshold": similarity_threshold,
                "match_count": limit,
            },
        ).execute()

        if response.data:
            return json.dumps(response.data, indent=2, default=str)
        else:
            return json.dumps({"message": "No matching receipts found"})

    except Exception as e:
        return json.dumps({"error": f"Search failed: {str(e)}"})
```

### Supabase vector_search Function

```sql
CREATE OR REPLACE FUNCTION vector_search(
    query_embedding vector(384),
    user_id_filter UUID,
    match_threshold FLOAT DEFAULT 0.3,
    match_count INT DEFAULT 25
)
RETURNS TABLE (
    id UUID,
    product_description TEXT,
    brand_name TEXT,
    amount NUMERIC,
    store_name TEXT,
    purchase_date DATE,
    category TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.product_description,
        r.brand_name,
        r.amount,
        r.store_name,
        r.purchase_date,
        r.category,
        1 - (r.embedding <=> query_embedding) as similarity
    FROM receipts r
    WHERE r.user_id = user_id_filter
      AND r.embedding IS NOT NULL
      AND 1 - (r.embedding <=> query_embedding) > match_threshold
    ORDER BY r.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

---

## Configuration Pattern

### config.py

```python
"""Configuration for Supabase integration."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Agent configuration from environment variables."""

    # Model
    model: str = "gemini-2.5-flash"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # OpenAI (for embeddings)
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384

    # Search defaults
    similarity_threshold: float = 0.3
    default_limit: int = 25
    max_sql_results: int = 50

    class Config:
        env_file = ".env"
        extra = "ignore"


config = Config()
```

### supabase_client.py

```python
"""Supabase client initialization."""

from supabase import create_client, Client
from .config import config


def get_supabase_client() -> Client:
    """Get Supabase client with service role."""
    return create_client(
        config.supabase_url,
        config.supabase_service_role_key,
    )


supabase: Client = get_supabase_client()
```

---

## User Context from Session State

### Setting user_id in before_agent_callback

```python
"""Agent with user context validation."""

import os
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext


DEFAULT_TEST_USER_ID = os.getenv("TEST_USER_ID", "")


def validate_user(callback_context: CallbackContext) -> None:
    """Ensure user_id is set before agent runs."""
    if not callback_context.state.get("user_id"):
        # For dev/testing: use default test user
        if DEFAULT_TEST_USER_ID:
            callback_context.state["user_id"] = DEFAULT_TEST_USER_ID
            print(f"[DEV MODE] Using test user_id")
        else:
            raise ValueError("user_id must be set in session state")


agent = LlmAgent(
    name="receipt_agent",
    before_agent_callback=validate_user,
    tools=[execute_sql, vector_search],
    ...
)
```

### Setting user_id from REST API

```python
"""REST endpoint that sets user context."""

from fastapi import FastAPI, Header
from google.adk.runners import Runner

app = FastAPI()

@app.post("/api/query")
async def query(
    question: str,
    x_user_id: str = Header(...),  # From authenticated session
):
    runner = Runner(agent=root_agent, ...)

    # Create session with user context
    session = await runner.session_service.create_session(
        app_name="receipt_agent",
        user_id=x_user_id,
        state={"user_id": x_user_id},  # Tools read from here
    )

    # Run query
    response = await runner.run(session_id=session.id, message=question)
    return response
```

---

## Complete Tools Export Pattern

### tools/__init__.py

```python
"""Export all Supabase tools."""

from .sql_tools import execute_sql
from .embedding_tools import vector_search, generate_embedding
from .brand_tools import lookup_brand_derivatives
from .warranty_tools import get_warranty_alerts

__all__ = [
    "execute_sql",
    "vector_search",
    "generate_embedding",
    "lookup_brand_derivatives",
    "get_warranty_alerts",
]
```

---

## Best Practices Summary

### DO

- Use `exec_sql_secure` for dynamic SQL with RLS
- Embed schema context in agent instructions
- Validate SQL before execution (SELECT only, no dangerous patterns)
- Set `user_id` in session state before running agent
- Use OpenAI embeddings for vector search (text-embedding-3-small)
- Return JSON strings from all tools

### DON'T

- Include `user_id` filters in LLM-generated SQL (RLS handles it)
- Use service role for queries without setting user context
- Allow UPDATE/DELETE/INSERT in dynamic SQL
- Hardcode credentials (use environment variables)

---

## Troubleshooting

### Issue: "No results found" but data exists

**Cause**: RLS not configured or user_id not set

**Fix**:

1. Verify RLS policy exists on table
2. Check `user_id` is in session state
3. Verify exec_sql_secure sets `app.user_id`

### Issue: "permission denied for table"

**Cause**: Service role not granted execute on function

**Fix**:

```sql
GRANT EXECUTE ON FUNCTION exec_sql_secure TO service_role;
```

### Issue: Vector search returns wrong results

**Cause**: Embedding dimensions mismatch

**Fix**: Ensure embedding model dimensions match pgvector column:

```sql
-- Check column dimensions
SELECT atttypmod FROM pg_attribute
WHERE attrelid = 'receipts'::regclass AND attname = 'embedding';
-- Should match config.embedding_dimensions (e.g., 384)
```

---

## Success Criteria

- [ ] exec_sql_secure function created in Supabase
- [ ] RLS policies use `app.user_id` setting
- [ ] Tools validate SQL before execution
- [ ] user_id extracted from session state
- [ ] Vector search uses matching embedding dimensions
- [ ] Schema context embedded in agent instructions
- [ ] All tools return JSON strings
