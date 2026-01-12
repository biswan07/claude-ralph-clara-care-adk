---
name: adk-parallel-agent
description: Create Google ADK ParallelAgent - executes multiple agents concurrently for independent tasks. Use when user says "parallel execution", "concurrent agents", "fan-out", "run simultaneously", or needs to execute multiple independent tasks at once.
---

# ADK ParallelAgent Creation Skill

## Purpose
Create ParallelAgent instances that execute multiple sub-agents concurrently. Perfect for fan-out/gather patterns, independent data fetching, parallel processing, and scenarios where multiple tasks don't depend on each other.

## When to Activate
Activate when user mentions:
- "parallel execution", "concurrent agents", "run simultaneously"
- "fan-out pattern", "gather pattern", "fan-out/gather"
- "independent tasks", "parallel processing"
- "multiple sources", "concurrent fetching"

## ParallelAgent Architecture

### Core Structure
```python
from google.adk.agents import ParallelAgent, LlmAgent

# Define agents that will run concurrently
fetch_source1 = LlmAgent(
    name="source1_fetcher",
    output_key="source1_data",  # Each saves to different key
    ...
)

fetch_source2 = LlmAgent(
    name="source2_fetcher",
    output_key="source2_data",
    ...
)

fetch_source3 = LlmAgent(
    name="source3_fetcher",
    output_key="source3_data",
    ...
)

# Create the parallel agent
parallel_fetcher = ParallelAgent(
    name="parallel_fetcher",
    description="Fetches data from multiple sources concurrently",
    sub_agents=[fetch_source1, fetch_source2, fetch_source3],
)
```

## Key Characteristics

1. **Isolated Execution**: Each sub-agent runs independently
2. **No Communication**: Sub-agents cannot communicate during execution
3. **Shared State**: All sub-agents can write to session state
4. **Concurrent Speed**: Faster than sequential for independent tasks

## Creation Workflow

### Step 1: Gather Requirements
Ask the user:
1. What independent tasks need to run concurrently?
2. What does each task produce?
3. How will the results be combined afterward?
4. Are the tasks truly independent (no dependencies)?

### Step 2: Design the Pattern

**Common Patterns:**

1. **Fan-Out/Gather**
```
                    ┌─────────────┐
                    │   Parallel  │
                    │   Agent     │
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ Fetcher1 │    │ Fetcher2 │    │ Fetcher3 │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         ▼               ▼               ▼
    state["d1"]    state["d2"]    state["d3"]
                         │
                    ┌────┴────┐
                    │ Gatherer│ (reads all)
                    └─────────┘
```

2. **Parallel Validation**
```
    ┌─────────────────────────────────────┐
    │         ParallelAgent               │
    │  ┌──────────┐  ┌──────────┐        │
    │  │ Validate │  │ Validate │  ...   │
    │  │ Aspect 1 │  │ Aspect 2 │        │
    │  └──────────┘  └──────────┘        │
    └─────────────────────────────────────┘
```

3. **Multi-Source Research**
```
    ┌─────────────────────────────────────┐
    │         ParallelAgent               │
    │  ┌──────────┐  ┌──────────┐        │
    │  │ Search   │  │ Search   │  ...   │
    │  │ Google   │  │ Academic │        │
    │  └──────────┘  └──────────┘        │
    └─────────────────────────────────────┘
```

### Step 3: Create Directory Structure
```
apps/<parallel-name>/
├── <parallel_package>/
│   ├── __init__.py
│   ├── agent.py              # Main agent with parallel + gatherer
│   ├── config.py
│   └── sub_agents/
│       ├── __init__.py
│       ├── fetcher1/
│       │   └── agent.py
│       ├── fetcher2/
│       │   └── agent.py
│       ├── fetcher3/
│       │   └── agent.py
│       └── gatherer/
│           └── agent.py      # Combines parallel results
├── pyproject.toml
└── .env.example
```

### Step 4: Create Parallel Sub-Agents
Each fetcher in `sub_agents/fetcherN/agent.py`:
```python
"""Fetcher N - retrieves data from source N."""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from ...config import config


fetcher_n_agent = LlmAgent(
    name="fetcher_n",
    model=config.model,
    description="Fetches data from source N",
    tools=[google_search],
    output_key="source_n_data",  # CRITICAL: Unique key for each fetcher
    instruction="""
You are a data fetcher for source N.

## YOUR TASK
[Describe what data to fetch from this source]

## SEARCH FOCUS
[Specific queries or patterns for this source]

## OUTPUT FORMAT
Provide structured data:
- Key findings
- Source citations
- Relevant quotes
""",
)
```

### Step 5: Create Gatherer Agent
`sub_agents/gatherer/agent.py`:
```python
"""Gatherer - combines results from all parallel fetchers."""

from google.adk.agents import LlmAgent
from ...config import config


gatherer_agent = LlmAgent(
    name="gatherer",
    model=config.model,
    description="Combines and synthesizes parallel fetch results",
    output_key="combined_result",
    instruction="""
You are a data synthesizer.

## INPUTS FROM PARALLEL FETCHERS
- Source 1 data: {source_1_data}
- Source 2 data: {source_2_data}
- Source 3 data: {source_3_data}

## YOUR TASK
Combine and synthesize all the parallel results into a unified output.

## OUTPUT FORMAT
Provide a comprehensive synthesis:
1. Combined findings
2. Cross-source insights
3. Conflicting information (if any)
4. Overall summary
""",
)
```

### Step 6: Create Main Agent (agent.py)
```python
"""Main agent with parallel fetching and gathering."""

from google.adk.agents import SequentialAgent, ParallelAgent

from .sub_agents.fetcher1.agent import fetcher_1_agent
from .sub_agents.fetcher2.agent import fetcher_2_agent
from .sub_agents.fetcher3.agent import fetcher_3_agent
from .sub_agents.gatherer.agent import gatherer_agent


# Create the parallel fetcher
parallel_fetcher = ParallelAgent(
    name="parallel_fetcher",
    description="Fetches data from multiple sources concurrently",
    sub_agents=[
        fetcher_1_agent,
        fetcher_2_agent,
        fetcher_3_agent,
    ],
)

# Combine parallel + gatherer in sequence
fetch_and_gather = SequentialAgent(
    name="fetch_and_gather",
    description="Parallel fetch then gather results",
    sub_agents=[
        parallel_fetcher,  # 1. Fetch all sources in parallel
        gatherer_agent,    # 2. Combine the results
    ],
)

# Export for ADK system
root_agent = fetch_and_gather
```

## Real-World Example: Multi-Source Research

```python
from google.adk.agents import SequentialAgent, ParallelAgent, LlmAgent
from google.adk.tools import google_search

# Web search agent
web_researcher = LlmAgent(
    name="web_researcher",
    model="gemini-2.5-flash",
    tools=[google_search],
    output_key="web_findings",
    instruction="""
Search the web for information on the topic.
Focus on recent news and articles.
Provide findings with sources.
""",
)

# Academic search agent
academic_researcher = LlmAgent(
    name="academic_researcher",
    model="gemini-2.5-flash",
    tools=[google_search],
    output_key="academic_findings",
    instruction="""
Search for academic and research papers on the topic.
Focus on peer-reviewed sources and studies.
Provide findings with citations.
""",
)

# Industry search agent
industry_researcher = LlmAgent(
    name="industry_researcher",
    model="gemini-2.5-flash",
    tools=[google_search],
    output_key="industry_findings",
    instruction="""
Search for industry reports and expert opinions.
Focus on market analysis and trends.
Provide findings with sources.
""",
)

# Parallel research
parallel_research = ParallelAgent(
    name="parallel_research",
    description="Research from web, academic, and industry sources",
    sub_agents=[web_researcher, academic_researcher, industry_researcher],
)

# Synthesizer
synthesizer = LlmAgent(
    name="synthesizer",
    model="gemini-2.5-flash",
    output_key="research_synthesis",
    instruction="""
Synthesize all research findings:

Web findings: {web_findings}
Academic findings: {academic_findings}
Industry findings: {industry_findings}

Create a comprehensive research report combining all sources.
Highlight agreements, disagreements, and key insights.
""",
)

# Complete workflow
research_workflow = SequentialAgent(
    name="research_workflow",
    sub_agents=[parallel_research, synthesizer],
)

root_agent = research_workflow
```

## Key Patterns

### 1. Unique Output Keys
```python
# Each parallel agent MUST have unique output_key
agent1 = LlmAgent(output_key="result_1", ...)
agent2 = LlmAgent(output_key="result_2", ...)
agent3 = LlmAgent(output_key="result_3", ...)
```

### 2. Fan-Out/Gather with Sequential
```python
# Always wrap parallel in sequential if gathering needed
workflow = SequentialAgent(
    sub_agents=[
        ParallelAgent(sub_agents=[...]),  # Fan-out
        gatherer_agent,                    # Gather
    ],
)
```

### 3. Nested Parallel Agents
```python
# You can nest parallel agents
region_parallel = ParallelAgent(
    sub_agents=[
        ParallelAgent(sub_agents=[us_east, us_west]),  # US region
        ParallelAgent(sub_agents=[eu_east, eu_west]),  # EU region
    ],
)
```

### 4. Mixed Workloads
```python
# Mix different agent types in parallel
parallel_processing = ParallelAgent(
    sub_agents=[
        data_validator,      # LlmAgent
        security_checker,    # LlmAgent
        performance_analyzer # LlmAgent
    ],
)
```

## Common Use Cases

### 1. Multi-Source Data Fetching
```python
ParallelAgent(sub_agents=[
    api1_fetcher,
    api2_fetcher,
    database_fetcher,
])
```

### 2. Parallel Validation
```python
ParallelAgent(sub_agents=[
    syntax_validator,
    semantic_validator,
    security_validator,
])
```

### 3. Competitive Analysis
```python
ParallelAgent(sub_agents=[
    competitor1_analyzer,
    competitor2_analyzer,
    competitor3_analyzer,
])
```

### 4. Multi-Language Translation
```python
ParallelAgent(sub_agents=[
    english_translator,
    spanish_translator,
    french_translator,
])
```

## Best Practices

1. **Unique output_key per agent**: Avoid state collisions
2. **Truly independent tasks**: No dependencies between parallel agents
3. **Always gather after**: Use SequentialAgent to combine results
4. **Balance workload**: Similar complexity across parallel tasks
5. **Error handling**: Each agent should handle its own errors

## Common Pitfalls

1. **State conflicts**: Using same output_key for multiple agents
2. **Dependencies**: Parallel agents shouldn't depend on each other
3. **No gathering**: Forgetting to combine parallel results
4. **Imbalanced work**: One slow agent delays everything

## Success Criteria
- ParallelAgent created with independent sub-agents
- Each sub-agent has unique `output_key`
- Gatherer agent combines all parallel results
- Sequential wrapper if gathering is needed
- Workflow exports `root_agent` for ADK system
