---
name: adk-sequential-agent
description: Create Google ADK SequentialAgent - orchestrates multiple agents in a specific order for multi-step workflows. Use when user says "create pipeline", "sequential workflow", "step-by-step agent", or needs ordered agent execution.
---

# ADK SequentialAgent Creation Skill

## Purpose
Create SequentialAgent instances that execute sub-agents in a specific, predetermined order. Perfect for multi-step workflows, data pipelines, and processes where each step depends on the previous one.

## When to Activate
Activate when user mentions:
- "create pipeline", "sequential workflow", "step-by-step"
- "ordered execution", "multi-step process"
- "workflow agent", "data pipeline"
- "execute agents in order", "chain agents"

## SequentialAgent Architecture

### Core Structure
```python
from google.adk.agents import SequentialAgent, LlmAgent

# Define sub-agents that will run in order
step1_agent = LlmAgent(
    name="step1",
    output_key="step1_result",  # Save output for next agent
    ...
)

step2_agent = LlmAgent(
    name="step2",
    instruction="Use the result from step 1: {step1_result}",  # Read from state
    output_key="step2_result",
    ...
)

step3_agent = LlmAgent(
    name="step3",
    instruction="Combine {step1_result} and {step2_result}",
    ...
)

# Create the sequential pipeline
pipeline = SequentialAgent(
    name="my_pipeline",
    description="Executes step1 -> step2 -> step3 in order",
    sub_agents=[step1_agent, step2_agent, step3_agent],
)
```

## Creation Workflow

### Step 1: Gather Requirements
Ask the user:
1. What are the steps in your workflow?
2. What does each step produce?
3. How does data flow between steps?
4. Are there any conditional paths or just linear execution?

### Step 2: Design Data Flow
Map out the session state flow:
```
Agent1 --output_key="data_a"--> state["data_a"]
                                      |
Agent2 <--{data_a}--- reads state["data_a"]
       --output_key="data_b"--> state["data_b"]
                                      |
Agent3 <--{data_a}, {data_b}--- reads both
```

### Step 3: Create Directory Structure
```
apps/<pipeline-name>/
├── <pipeline_package>/
│   ├── __init__.py
│   ├── agent.py              # Main pipeline definition
│   ├── config.py             # Configuration
│   └── sub_agents/
│       ├── __init__.py
│       ├── step1/
│       │   ├── __init__.py
│       │   └── agent.py
│       ├── step2/
│       │   ├── __init__.py
│       │   └── agent.py
│       └── step3/
│           ├── __init__.py
│           └── agent.py
├── pyproject.toml
└── .env.example
```

### Step 4: Create Sub-Agent Template
Each sub-agent in `sub_agents/<step>/agent.py`:
```python
"""Step N agent for the pipeline."""

from google.adk.agents import LlmAgent
from ...config import config


step_n_agent = LlmAgent(
    name="step_n_name",
    model=config.model,
    description="Performs step N: [specific task]",
    output_key="step_n_result",  # CRITICAL: Save output for next step
    instruction="""
You are responsible for step N of the pipeline.

## INPUT (from previous steps)
- Previous result: {previous_step_result}

## YOUR TASK
[Describe what this step does]

## OUTPUT REQUIREMENTS
[Describe expected output format]

## IMPORTANT
- Read input from session state using {placeholder} syntax
- Your output will be saved to "step_n_result" automatically
""",
)
```

### Step 5: Create Main Pipeline (agent.py)
```python
"""Main sequential pipeline definition."""

from google.adk.agents import SequentialAgent

from .sub_agents.step1.agent import step1_agent
from .sub_agents.step2.agent import step2_agent
from .sub_agents.step3.agent import step3_agent


# Create the sequential pipeline
my_pipeline = SequentialAgent(
    name="my_pipeline",
    description="Multi-step workflow: Step1 -> Step2 -> Step3",
    sub_agents=[
        step1_agent,   # 1. First step - initializes the workflow
        step2_agent,   # 2. Second step - processes step1 output
        step3_agent,   # 3. Third step - finalizes the workflow
    ],
)

# Export for ADK system
root_agent = my_pipeline
```

## Real-World Example: Content Pipeline

```python
from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.tools import google_search

# Step 1: Research
research_agent = LlmAgent(
    name="researcher",
    model="gemini-2.5-flash",
    description="Researches topics using web search",
    tools=[google_search],
    output_key="research_data",
    instruction="""
You are a research specialist.

## TASK
Research the given topic thoroughly using google_search.

## OUTPUT
Provide comprehensive research findings with sources.
""",
)

# Step 2: Write
writer_agent = LlmAgent(
    name="writer",
    model="gemini-2.5-flash",
    description="Writes content based on research",
    output_key="draft_content",
    instruction="""
You are a content writer.

## INPUT
Research data: {research_data}

## TASK
Write a comprehensive article based on the research.

## OUTPUT
A well-structured draft article.
""",
)

# Step 3: Edit
editor_agent = LlmAgent(
    name="editor",
    model="gemini-2.5-flash",
    description="Edits and polishes content",
    output_key="final_content",
    instruction="""
You are a professional editor.

## INPUT
Draft content: {draft_content}

## TASK
Edit and polish the draft for publication.

## OUTPUT
A polished, publication-ready article.
""",
)

# Create the pipeline
content_pipeline = SequentialAgent(
    name="content_pipeline",
    description="Research -> Write -> Edit content pipeline",
    sub_agents=[research_agent, writer_agent, editor_agent],
)

root_agent = content_pipeline
```

## Key Patterns

### 1. State Passing Between Agents
```python
# Agent 1 saves output
agent1 = LlmAgent(
    output_key="step1_output",  # Saves to state["step1_output"]
    ...
)

# Agent 2 reads from state
agent2 = LlmAgent(
    instruction="Process this: {step1_output}",  # Reads state["step1_output"]
    output_key="step2_output",
    ...
)
```

### 2. Nested SequentialAgents
```python
# Sub-pipeline for validation
validation_pipeline = SequentialAgent(
    name="validation",
    sub_agents=[validator, reviewer, approver],
)

# Main pipeline includes nested pipeline
main_pipeline = SequentialAgent(
    name="main",
    sub_agents=[processor, validation_pipeline, finalizer],
)
```

### 3. Mixed Agent Types in Sequence
```python
from google.adk.agents import SequentialAgent, ParallelAgent, LoopAgent

# Combine different agent types
hybrid_pipeline = SequentialAgent(
    name="hybrid_pipeline",
    sub_agents=[
        data_collector,              # LlmAgent
        parallel_processors,         # ParallelAgent
        quality_loop,                # LoopAgent
        report_generator,            # LlmAgent
    ],
)
```

## Common Use Cases

### 1. Data Processing Pipeline
```
Input -> Validate -> Transform -> Enrich -> Output
```

### 2. Document Generation
```
Research -> Outline -> Draft -> Review -> Publish
```

### 3. Analysis Workflow
```
Gather Data -> Analyze -> Evaluate -> Report
```

### 4. Customer Service Flow
```
Classify Issue -> Research Solution -> Generate Response -> Quality Check
```

## Best Practices

1. **Always use output_key**: Every sub-agent should save its output to session state
2. **Clear naming**: Use descriptive names for output_key (e.g., `research_findings`, `analysis_result`)
3. **Document data flow**: Comment what each agent expects as input and produces as output
4. **Handle failures**: Consider what happens if a step fails
5. **Keep steps focused**: Each agent should do one thing well

## Success Criteria
- SequentialAgent created with proper sub-agent order
- Each sub-agent has `output_key` defined
- Instructions reference previous outputs using `{placeholder}` syntax
- Data flow is clearly documented
- Pipeline exports `root_agent` for ADK system
