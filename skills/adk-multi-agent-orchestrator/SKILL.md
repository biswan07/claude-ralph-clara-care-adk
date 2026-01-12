---
name: adk-multi-agent-orchestrator
description: Create Google ADK Multi-Agent Systems - complex hierarchical agent architectures combining LlmAgent, SequentialAgent, LoopAgent, and ParallelAgent. Use when user says "multi-agent system", "agent hierarchy", "orchestrator", "complex workflow", or needs to combine multiple agent types.
---

# ADK Multi-Agent Orchestrator Skill

## Purpose
Create complex multi-agent systems that combine LlmAgent, SequentialAgent, LoopAgent, and ParallelAgent into hierarchical architectures. Perfect for sophisticated workflows like competitor analysis, research pipelines, automated content generation, and enterprise automation.

## When to Activate
Activate when user mentions:
- "multi-agent system", "agent hierarchy", "orchestrator"
- "complex workflow", "enterprise automation"
- "combine agents", "agent architecture"
- "root agent with sub-agents", "agent delegation"

## Multi-Agent Architecture Overview

### Hierarchy Pattern
```
                    ┌─────────────────────┐
                    │     Root Agent      │
                    │     (LlmAgent)      │
                    │  - Orchestrates     │
                    │  - Delegates        │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌───────────────┐    ┌─────────────────┐    ┌───────────────┐
│ AgentTool     │    │ SequentialAgent │    │ Sub-Agent 3   │
│ (Specialist)  │    │   (Pipeline)    │    │               │
└───────────────┘    └────────┬────────┘    └───────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Step 1   │   │ Step 2   │   │ LoopAgent│
        │ LlmAgent │   │ Parallel │   │ (QA)     │
        └──────────┘   └──────────┘   └──────────┘
```

## Creation Workflow

### Step 1: Gather Requirements
Ask the user:
1. What is the overall goal of the system?
2. What are the major phases/stages?
3. Which tasks can run in parallel?
4. What needs iterative refinement?
5. How should agents communicate?

### Step 2: Design the Architecture

**Map requirements to agent types:**

| Requirement | Agent Type |
|-------------|------------|
| Human-like reasoning, decision making | LlmAgent |
| Ordered multi-step workflow | SequentialAgent |
| Independent concurrent tasks | ParallelAgent |
| Quality assurance, refinement | LoopAgent |
| Specialist called on-demand | AgentTool |

### Step 3: Create Directory Structure
```
apps/<system-name>/
├── <system_package>/
│   ├── __init__.py
│   ├── agent.py              # Root agent definition
│   ├── config.py             # Configuration
│   ├── tools.py              # Custom tools
│   └── sub_agents/
│       ├── __init__.py       # Export all sub-agents
│       ├── planner/
│       │   ├── __init__.py
│       │   └── agent.py
│       ├── research_pipeline/
│       │   ├── __init__.py
│       │   └── agent.py      # SequentialAgent
│       ├── data_gatherer/
│       │   ├── __init__.py
│       │   └── agent.py      # ParallelAgent
│       ├── quality_loop/
│       │   ├── __init__.py
│       │   └── agent.py      # LoopAgent
│       ├── evaluator/
│       │   └── agent.py
│       ├── escalation_checker/
│       │   └── agent.py
│       └── report_composer/
│           └── agent.py
├── scripts/
│   └── agent_engine_app.py
├── pyproject.toml
└── .env.example
```

### Step 4: Create Configuration (config.py)
```python
"""Configuration management for the multi-agent system."""

from typing import Any
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SystemConfig(BaseSettings):
    """Configuration for the multi-agent system."""

    model_config = SettingsConfigDict(
        env_file=[".env", ".env.local"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Google Cloud Configuration
    google_cloud_project: str = Field(default="", description="Google Cloud project ID")
    google_cloud_location: str = Field(default="us-central1", description="Location")

    # Agent Configuration
    agent_name: str = Field(default="orchestrator", description="Root agent name")
    model: str = Field(default="gemini-2.5-flash", description="AI model")

    # Workflow Configuration
    max_iterations: int = Field(default=3, description="Max loop iterations")

    def fail_fast_validation(self) -> None:
        """Validate required configuration."""
        # Add validation as needed
        pass


config = SystemConfig()
config.fail_fast_validation()
```

### Step 5: Create Sub-Agents

#### Planner Agent (sub_agents/planner/agent.py)
```python
"""Planner agent - creates execution plans."""

from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.adk.tools import google_search
from google.genai import types as genai_types

from ...config import config

planner_agent = LlmAgent(
    name="planner",
    model=config.model,
    description="Creates detailed execution plans",
    tools=[google_search],
    output_key="execution_plan",
    planner=BuiltInPlanner(
        thinking_config=genai_types.ThinkingConfig(include_thoughts=True)
    ),
    instruction="""
You are a strategic planner.

## CONTEXT
{research_context}

## YOUR TASK
Create a detailed execution plan for the workflow.

## OUTPUT
Provide a structured plan with clear steps.
""",
)
```

#### Data Gatherer - ParallelAgent (sub_agents/data_gatherer/agent.py)
```python
"""Parallel data gathering from multiple sources."""

from google.adk.agents import ParallelAgent, LlmAgent
from google.adk.tools import google_search

from ...config import config

# Individual source agents
source1_agent = LlmAgent(
    name="source1",
    model=config.model,
    tools=[google_search],
    output_key="source1_data",
    instruction="Gather data from source type 1...",
)

source2_agent = LlmAgent(
    name="source2",
    model=config.model,
    tools=[google_search],
    output_key="source2_data",
    instruction="Gather data from source type 2...",
)

# Parallel gatherer
data_gatherer = ParallelAgent(
    name="data_gatherer",
    description="Gathers data from multiple sources in parallel",
    sub_agents=[source1_agent, source2_agent],
)
```

#### Quality Loop - LoopAgent (sub_agents/quality_loop/agent.py)
```python
"""Quality assurance loop for iterative refinement."""

from google.adk.agents import LoopAgent

from ...config import config
from ..evaluator.agent import evaluator_agent
from ..escalation_checker.agent import escalation_checker
from ..enhancer.agent import enhancer_agent

quality_loop = LoopAgent(
    name="quality_loop",
    description="Iterative quality improvement: evaluate -> check -> enhance",
    max_iterations=config.max_iterations,
    sub_agents=[
        evaluator_agent,     # 1. Evaluate current quality
        escalation_checker,  # 2. Check if should exit
        enhancer_agent,      # 3. Improve if continuing
    ],
)
```

#### Research Pipeline - SequentialAgent (sub_agents/research_pipeline/agent.py)
```python
"""Sequential research pipeline orchestrating the full workflow."""

from google.adk.agents import SequentialAgent

from ..planner.agent import planner_agent
from ..data_gatherer.agent import data_gatherer
from ..quality_loop.agent import quality_loop
from ..report_composer.agent import report_composer_agent

research_pipeline = SequentialAgent(
    name="research_pipeline",
    description="Full research workflow: plan -> gather -> validate -> report",
    sub_agents=[
        planner_agent,         # 1. Create execution plan
        data_gatherer,         # 2. Gather data in parallel
        quality_loop,          # 3. Quality assurance loop
        report_composer_agent, # 4. Generate final report
    ],
)
```

### Step 6: Create Root Agent (agent.py)
```python
"""Root orchestrator agent for the multi-agent system."""

from google.adk.agents import LlmAgent
from google.adk.tools import ToolContext
from google.adk.tools.agent_tool import AgentTool

from .config import config
from .sub_agents import planner_agent, research_pipeline
from .utils.callbacks import prep_state_callback


def save_context(context: str, tool_context: ToolContext) -> str:
    """
    Save context to session state for sub-agents.

    Args:
        context (str): Context information to save
        tool_context (ToolContext): ADK context (ALWAYS LAST)

    Returns:
        Confirmation message
    """
    tool_context.state["research_context"] = context
    return "Context saved successfully."


orchestrator = LlmAgent(
    name="orchestrator",
    model=config.model,
    description="Root orchestrator for the multi-agent system",
    sub_agents=[research_pipeline],  # Can delegate to pipeline
    tools=[
        AgentTool(planner_agent),    # Can call planner as tool
        save_context,                 # Custom tool
    ],
    before_agent_callback=prep_state_callback,
    instruction="""
You are the master orchestrator for a sophisticated multi-agent system.

## YOUR ROLE
- Understand user requirements
- Gather necessary context
- Delegate to specialized agents
- Coordinate the workflow

## WORKFLOW

### PHASE 1: INFORMATION GATHERING
Ask clarifying questions to understand:
- What is the goal?
- What context is needed?
- Any specific requirements?

### PHASE 2: CONTEXT PREPARATION
Once you have information:
1. Use `save_context` to store the context
2. Use `planner` tool to create an execution plan

### PHASE 3: EXECUTION
After planning:
1. Delegate to `research_pipeline` for full execution
2. The pipeline will:
   - Gather data in parallel
   - Run quality assurance loop
   - Generate final report

### PHASE 4: DELIVERY
Present the final results to the user.

## KEY GUIDELINES
- Always gather context before delegating
- Use save_context to share data with sub-agents
- Let specialized agents handle their domains
- Synthesize results for the user

Current Date: {current_date}
""",
)

# Export for ADK system
root_agent = orchestrator
```

### Step 7: Create Sub-Agents Init (sub_agents/__init__.py)
```python
"""Export all sub-agents for the system."""

from .planner.agent import planner_agent
from .data_gatherer.agent import data_gatherer
from .quality_loop.agent import quality_loop
from .research_pipeline.agent import research_pipeline
from .evaluator.agent import evaluator_agent
from .escalation_checker.agent import escalation_checker
from .report_composer.agent import report_composer_agent

__all__ = [
    "planner_agent",
    "data_gatherer",
    "quality_loop",
    "research_pipeline",
    "evaluator_agent",
    "escalation_checker",
    "report_composer_agent",
]
```

## Real-World Example: Competitor Analysis System

```python
# agent.py - Root Orchestrator
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from .sub_agents import plan_generator_agent, research_pipeline

root_agent = LlmAgent(
    name="competitor_analysis_agent",
    model="gemini-2.5-flash",
    sub_agents=[research_pipeline],
    tools=[AgentTool(plan_generator_agent), save_research_context],
    instruction="""
    Interactive competitor analysis agent.
    1. Gather business context from user
    2. Generate research plan
    3. Delegate to research_pipeline
    """,
)

# research_pipeline/agent.py - Sequential Pipeline
research_pipeline = SequentialAgent(
    name="research_pipeline",
    sub_agents=[
        section_planner_agent,    # Break into sections
        section_researcher_agent, # Research each section
        iterative_refinement_loop,# Quality loop
        report_composer_agent,    # Generate report
    ],
)

# iterative_refinement_loop/agent.py - Quality Loop
iterative_refinement_loop = LoopAgent(
    name="iterative_refinement_loop",
    max_iterations=3,
    sub_agents=[
        research_evaluator_agent,      # Evaluate quality
        escalation_checker,            # Check exit condition
        enhanced_search_executor_agent,# Improve if needed
    ],
)
```

## Communication Patterns

### 1. Session State Flow
```python
# Root saves context
tool_context.state["research_context"] = context

# Sub-agent reads context
instruction="Based on: {research_context}"

# Sub-agent saves output
output_key="research_plan"

# Next agent reads output
instruction="Execute plan: {research_plan}"
```

### 2. AgentTool for On-Demand Delegation
```python
# Wrap specialist agent
specialist_tool = AgentTool(specialist_agent)

# Root can call as needed
root = LlmAgent(
    tools=[specialist_tool],
    instruction="Use specialist when needed...",
)
```

### 3. Sub-Agent Delegation
```python
# Direct delegation via sub_agents
root = LlmAgent(
    sub_agents=[pipeline],  # Can hand off to pipeline
    instruction="Delegate to pipeline when ready...",
)
```

## Architecture Patterns

### Pattern 1: Hub and Spoke
```
         Orchestrator
        /     |     \
    Agent1  Agent2  Agent3
```

### Pattern 2: Pipeline with Branches
```
    Start -> [Parallel] -> Process -> [Loop] -> End
                |
            [Branch1, Branch2]
```

### Pattern 3: Hierarchical Delegation
```
    Orchestrator
         |
    SequentialAgent
    /       |       \
Step1   ParallelAgent   Step3
          /    \
      Fetch1  Fetch2
```

## Best Practices

1. **Clear hierarchy**: Root orchestrates, sub-agents specialize
2. **State management**: Use output_key and {placeholder} consistently
3. **Loose coupling**: Agents communicate via session state only
4. **Single responsibility**: Each agent does one thing well
5. **Error isolation**: Failures in sub-agents don't crash root

## Common Pitfalls

1. **Circular dependencies**: Agent A depends on B which depends on A
2. **State collisions**: Multiple agents using same output_key
3. **Over-orchestration**: Root doing too much, not delegating
4. **Missing context**: Sub-agents don't have required state

## Success Criteria
- Clear agent hierarchy with root orchestrator
- Appropriate agent types for each task
- Session state flows correctly between agents
- AgentTool used for on-demand specialists
- System exports `root_agent` for ADK
