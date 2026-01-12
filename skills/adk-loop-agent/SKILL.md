---
name: adk-loop-agent
description: Create Google ADK LoopAgent - iteratively executes sub-agents until a condition is met. Use when user says "create loop", "iterative refinement", "quality assurance loop", "repeat until", or needs iterative processing with exit conditions.
---

# ADK LoopAgent Creation Skill

## Purpose
Create LoopAgent instances that execute sub-agents iteratively until a termination condition is met or max iterations is reached. Perfect for quality assurance, iterative refinement, validation loops, and retry patterns.

## When to Activate
Activate when user mentions:
- "create loop", "iterative refinement", "repeat until"
- "quality assurance loop", "validation loop"
- "action-critic pattern", "refinement cycle"
- "retry pattern", "iterative improvement"

## LoopAgent Architecture

### Core Structure
```python
from google.adk.agents import LoopAgent, LlmAgent

# Define sub-agents that run each iteration
action_agent = LlmAgent(name="action", ...)
evaluator_agent = LlmAgent(name="evaluator", ...)
escalation_checker = EscalationChecker(name="checker")  # Custom agent

# Create the loop
refinement_loop = LoopAgent(
    name="refinement_loop",
    description="Iterative refinement: action -> evaluate -> check exit",
    max_iterations=5,  # Safety limit
    sub_agents=[
        action_agent,        # 1. Perform the action
        evaluator_agent,     # 2. Evaluate the result
        escalation_checker,  # 3. Check if should exit loop
    ],
)
```

## Loop Termination

### Method 1: EventActions.escalate (Recommended)
```python
from collections.abc import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions


class EscalationChecker(BaseAgent):
    """Controls loop termination based on quality criteria."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Check if loop should terminate."""
        evaluation = ctx.session.state.get("evaluation_result")

        should_exit = False
        if evaluation and evaluation.get("grade") == "pass":
            should_exit = True

        if should_exit:
            # Exit the loop
            yield Event(
                author=self.name,
                actions=EventActions(escalate=True),
            )
        else:
            # Continue looping
            yield Event(author=self.name)


escalation_checker = EscalationChecker(name="escalation_checker")
```

### Method 2: Max Iterations Safety
```python
# Loop automatically stops after max_iterations
loop = LoopAgent(
    name="loop",
    max_iterations=3,  # Will stop after 3 iterations regardless
    sub_agents=[...],
)
```

## Creation Workflow

### Step 1: Gather Requirements
Ask the user:
1. What is being refined/validated each iteration?
2. What criteria determines when to stop?
3. What is the maximum number of iterations?
4. What agents run each iteration?

### Step 2: Design the Loop Pattern

**Common Patterns:**

1. **Action-Critic-Checker** (Most Common)
```
┌──────────────────────────────────────────────┐
│                  LOOP                         │
│  ┌─────────┐  ┌──────────┐  ┌─────────────┐  │
│  │ Action  │→ │ Critic   │→ │ Checker     │  │
│  │ Agent   │  │ Agent    │  │ (escalate?) │  │
│  └─────────┘  └──────────┘  └─────────────┘  │
│       ↑                            │          │
│       └────────────────────────────┘          │
│              (if not escalated)               │
└──────────────────────────────────────────────┘
```

2. **Generate-Validate**
```
┌──────────────────────────────────────────────┐
│  ┌───────────┐  ┌────────────┐  ┌─────────┐  │
│  │ Generator │→ │ Validator  │→ │ Checker │  │
│  └───────────┘  └────────────┘  └─────────┘  │
└──────────────────────────────────────────────┘
```

3. **Research-Evaluate-Enhance**
```
┌──────────────────────────────────────────────┐
│  ┌──────────┐  ┌──────────┐  ┌───────────┐   │
│  │ Research │→ │ Evaluate │→ │ Enhance   │   │
│  └──────────┘  └──────────┘  └───────────┘   │
│                                     │        │
│  ┌─────────────────────────────────┐│        │
│  │ Checker (quality met?)          ││        │
│  └─────────────────────────────────┘│        │
└──────────────────────────────────────────────┘
```

### Step 3: Create Directory Structure
```
apps/<loop-name>/
├── <loop_package>/
│   ├── __init__.py
│   ├── agent.py              # Main loop definition
│   ├── config.py
│   └── sub_agents/
│       ├── __init__.py
│       ├── action/
│       │   └── agent.py
│       ├── evaluator/
│       │   └── agent.py
│       └── escalation_checker/
│           └── agent.py      # Custom BaseAgent for loop control
├── pyproject.toml
└── .env.example
```

### Step 4: Create the Escalation Checker
`sub_agents/escalation_checker/agent.py`:
```python
"""Escalation checker for controlling loop termination."""

from collections.abc import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions


class EscalationChecker(BaseAgent):
    """Custom agent for controlling loop termination based on quality criteria."""

    def __init__(self, name: str):
        super().__init__(name=name)

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Check if quality meets standards and control loop escalation."""
        # Read evaluation from session state
        evaluation = ctx.session.state.get("evaluation_result")

        should_escalate = False
        escalation_reason = ""

        # Define your exit conditions
        if evaluation:
            if evaluation.get("grade") == "pass":
                should_escalate = True
                escalation_reason = "Quality standards met"
            elif evaluation.get("score", 0) >= 0.9:
                should_escalate = True
                escalation_reason = "Score threshold reached"

        if should_escalate:
            ctx.session.state["escalation_reason"] = escalation_reason
            yield Event(
                author=self.name,
                actions=EventActions(escalate=True),
            )
        else:
            # Continue loop - LoopAgent handles max_iterations
            yield Event(author=self.name)


escalation_checker = EscalationChecker(name="escalation_checker")
```

### Step 5: Create Action Agent
`sub_agents/action/agent.py`:
```python
"""Action agent that performs the main task each iteration."""

from google.adk.agents import LlmAgent
from google.adk.tools import google_search
from ...config import config


action_agent = LlmAgent(
    name="action_agent",
    model=config.model,
    description="Performs the main action each iteration",
    tools=[google_search],
    output_key="action_result",
    instruction="""
You are responsible for performing the main action in the refinement loop.

## PREVIOUS FEEDBACK (if any)
Evaluation feedback: {evaluation_feedback}

## YOUR TASK
[Describe the action to perform]

## IMPROVEMENT FOCUS
If there was previous feedback, address those specific issues.

## OUTPUT
Provide your result for evaluation.
""",
)
```

### Step 6: Create Evaluator Agent
`sub_agents/evaluator/agent.py`:
```python
"""Evaluator agent that assesses quality each iteration."""

from google.adk.agents import LlmAgent
from ...config import config


evaluator_agent = LlmAgent(
    name="evaluator_agent",
    model=config.model,
    description="Evaluates quality of the action result",
    output_key="evaluation_result",
    instruction="""
You are a quality evaluator.

## INPUT TO EVALUATE
Action result: {action_result}

## EVALUATION CRITERIA
1. [Criterion 1]
2. [Criterion 2]
3. [Criterion 3]

## OUTPUT FORMAT
Provide a structured evaluation:
```json
{
    "grade": "pass" or "fail",
    "score": 0.0-1.0,
    "feedback": "Specific improvement suggestions",
    "issues": ["issue1", "issue2"]
}
```

Be strict but fair in your evaluation.
""",
)
```

### Step 7: Create Main Loop (agent.py)
```python
"""Main iterative refinement loop definition."""

from google.adk.agents import LoopAgent

from .config import config
from .sub_agents.action.agent import action_agent
from .sub_agents.evaluator.agent import evaluator_agent
from .sub_agents.escalation_checker.agent import escalation_checker


# Create the refinement loop
refinement_loop = LoopAgent(
    name="refinement_loop",
    description="Quality assurance through iterative improvement: action -> evaluate -> check",
    max_iterations=config.max_iterations,
    sub_agents=[
        action_agent,        # 1. Perform the action
        evaluator_agent,     # 2. Evaluate the quality
        escalation_checker,  # 3. Check if should exit loop
    ],
)

# Export for ADK system
root_agent = refinement_loop
```

## Real-World Example: Research Quality Loop

```python
from google.adk.agents import LoopAgent, LlmAgent
from google.adk.tools import google_search

# Research agent - gathers information
researcher = LlmAgent(
    name="researcher",
    model="gemini-2.5-flash",
    tools=[google_search],
    output_key="research_data",
    instruction="""
Research the topic thoroughly.

Previous feedback to address: {evaluation_feedback}

Provide comprehensive findings with sources.
""",
)

# Evaluator - checks research quality
evaluator = LlmAgent(
    name="evaluator",
    model="gemini-2.5-flash",
    output_key="evaluation_result",
    instruction="""
Evaluate the research quality: {research_data}

Criteria:
1. Completeness - covers all aspects?
2. Accuracy - sources are reliable?
3. Depth - sufficient detail?

Output:
{
    "grade": "pass" or "fail",
    "score": 0.0-1.0,
    "feedback": "What's missing or needs improvement"
}
""",
)

# Checker - controls loop exit
class QualityChecker(BaseAgent):
    async def _run_async_impl(self, ctx):
        eval_result = ctx.session.state.get("evaluation_result", {})
        if eval_result.get("grade") == "pass":
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            # Save feedback for next iteration
            ctx.session.state["evaluation_feedback"] = eval_result.get("feedback", "")
            yield Event(author=self.name)

# Assemble the loop
research_loop = LoopAgent(
    name="research_quality_loop",
    max_iterations=3,
    sub_agents=[researcher, evaluator, QualityChecker(name="checker")],
)
```

## Key Patterns

### 1. Passing Feedback Between Iterations
```python
# Evaluator saves feedback
evaluator = LlmAgent(
    output_key="evaluation_feedback",
    ...
)

# Action agent reads feedback next iteration
action = LlmAgent(
    instruction="Address this feedback: {evaluation_feedback}",
    ...
)
```

### 2. Iteration Counter
```python
class IterationTracker(BaseAgent):
    async def _run_async_impl(self, ctx):
        count = ctx.session.state.get("iteration_count", 0) + 1
        ctx.session.state["iteration_count"] = count
        yield Event(author=self.name)
```

### 3. Quality Score Tracking
```python
class ScoreChecker(BaseAgent):
    async def _run_async_impl(self, ctx):
        score = ctx.session.state.get("quality_score", 0)
        if score >= 0.9:  # 90% quality threshold
            yield Event(author=self.name, actions=EventActions(escalate=True))
        else:
            yield Event(author=self.name)
```

## Best Practices

1. **Always set max_iterations**: Prevent infinite loops
2. **Clear exit conditions**: Define what "done" means
3. **Preserve context**: Pass feedback between iterations
4. **Track progress**: Store iteration count and scores
5. **Fail gracefully**: Handle max iterations reached

## Common Pitfalls

1. **Infinite loops**: Always use `max_iterations`
2. **Lost context**: Use session state to preserve data
3. **No exit condition**: Must have an escalation checker
4. **Vague evaluation**: Use specific, measurable criteria

## Success Criteria
- LoopAgent created with appropriate `max_iterations`
- Custom EscalationChecker implements exit logic
- Sub-agents pass data via session state
- Evaluation criteria are clear and measurable
- Loop exports `root_agent` for ADK system
