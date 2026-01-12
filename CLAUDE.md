# Claude Ralph & ADK Skills - Project Instructions

This repository contains two systems:
1. **Claude Ralph** - Autonomous development loop for implementing PRDs
2. **Google ADK Skills** - Comprehensive guides for building AI agents

## Quick Skill Reference

Use the appropriate skill based on what you're trying to accomplish:

### PRD & Project Planning
| Trigger Phrases | Skill | Purpose |
|-----------------|-------|---------|
| "create a prd", "write prd for", "plan this feature", "requirements for" | `skills/prd/` | Generate comprehensive markdown PRDs |
| "convert this prd", "ralph json", "make prd.json", "turn this into ralph format" | `skills/ralph/` | Convert markdown PRD to `prd.json` |

### Creating ADK Agents
| Trigger Phrases | Skill | Purpose |
|-----------------|-------|---------|
| "create llm agent", "create adk agent", "new agent", "build an AI agent" | `skills/adk-llm-agent/` | Core LlmAgent with Gemini |
| "create pipeline", "sequential workflow", "step-by-step agent", "chain agents" | `skills/adk-sequential-agent/` | Multi-step ordered workflows |
| "parallel execution", "concurrent agents", "fan-out", "run simultaneously" | `skills/adk-parallel-agent/` | Independent concurrent tasks |
| "create loop", "iterative refinement", "quality assurance loop", "repeat until" | `skills/adk-loop-agent/` | Iterate until exit condition |
| "multi-agent system", "agent hierarchy", "orchestrator", "complex workflow" | `skills/adk-multi-agent-orchestrator/` | Combine agent types |

### Tools & Integration
| Trigger Phrases | Skill | Purpose |
|-----------------|-------|---------|
| "create tool", "custom tool", "add tool", "MCP integration", "function tool" | `skills/adk-tools/` | Custom tools, MCP, AgentTool |
| "supabase tool", "database tool", "vector search", "query receipts", "RLS" | `skills/adk-supabase-tools/` | Supabase SQL & vector search |

### State & Sessions
| Trigger Phrases | Skill | Purpose |
|-----------------|-------|---------|
| "session management", "state management", "agent memory", "output_key" | `skills/adk-sessions/` | Session services & state patterns |

### Testing & Deployment
| Trigger Phrases | Skill | Purpose |
|-----------------|-------|---------|
| "test agent", "agent testing", "unit test", "evaluate agent" | `skills/adk-testing/` | pytest, mocks, evaluation |
| "deploy agent", "agent engine", "production deployment", "cloud run" | `skills/adk-deployment/` | Vertex AI, Cloud Run, local |

### Complete Examples
| Trigger Phrases | Skill | Purpose |
|-----------------|-------|---------|
| "receipt query agent", "smart receipts", "query my receipts" | `skills/adk-receipt-query-agent/` | Full production agent example |

---

## Claude Ralph System

### Overview

Claude Ralph is a bash-based autonomous loop that spawns Claude CLI instances to implement PRD user stories iteratively. Each iteration is independent with fresh context.

### File Purposes

- `claude-ralph.sh` - Main loop script, spawns Claude instances
- `prompt.md` - Instructions given to each Claude instance
- `prd.json` - Current PRD with story completion status
- `progress.txt` - Append-only log of learnings across iterations
- `commands/ralph.md` - Interactive `/ralph` slash command

### Key Patterns

#### Completion Signal
When all stories are complete, output exactly: `RALPH_COMPLETE`

#### Story Selection
Always select the highest-priority (lowest `priority` number) story where `passes: false`.

#### Quality Gates
Before any commit:
1. Run typecheck
2. Run tests
3. Run lint

Never commit failing code.

#### Progress Logging
After each story, append to `progress.txt`:
```
---
## [Date] - [Story ID]: [Title]

### What was implemented
- [Changes]

### Learnings for future iterations
- [Patterns discovered]
```

---

## Google ADK Patterns

### Agent Architecture
```
LlmAgent (core reasoning)
├── SequentialAgent  → Step 1 → Step 2 → Step 3
├── ParallelAgent    → [Task A | Task B | Task C]
├── LoopAgent        → Iterate until exit condition
└── Multi-Agent      → Combine all patterns
```

### Critical Patterns

#### 1. Prompt Caching (20-30% latency reduction)
```python
# Static content FIRST (cached)
STATIC_INSTRUCTION = """Schema, rules, examples..."""

# Dynamic content at END (not cached)
def build_instruction():
    return f"{STATIC_INSTRUCTION}\n\nToday is {date.today()}"
```

#### 2. Session State Flow
```python
# Agent saves output
agent1 = LlmAgent(output_key="step1_result", ...)

# Next agent reads via placeholder
agent2 = LlmAgent(instruction="Process: {step1_result}", ...)
```

#### 3. Tool Context (ALWAYS LAST)
```python
def my_tool(
    param1: str,
    param2: int,
    tool_context: ToolContext,  # MUST be last
) -> str:
    user_id = tool_context.state.get("user_id")
    return "result"
```

#### 4. Agent Engine Deployment
```python
# CRITICAL: Use Vertex AI, NOT API key
ENV_VARS = {
    "GOOGLE_GENAI_USE_VERTEXAI": "1",  # Required
    # DO NOT include GOOGLE_API_KEY
}
```

#### 5. Export Root Agent
```python
# __init__.py - Required for ADK discovery
from .agent import root_agent
__all__ = ["root_agent"]
```

---

## Editing Guidelines

### Shell Scripts
Keep POSIX-compatible where possible. Use `shellcheck` for validation.

### Markdown Files
Follow consistent heading structure. Skills use specific trigger keywords in frontmatter.

### JSON Format
Maintain the exact `prd.json` schema - the loop depends on `passes`, `priority`, etc.

### Skill Files
Each skill has:
- `name:` identifier
- `description:` for CLI display
- Trigger phrases in "When to Activate" section
- Step-by-step implementation guides
- Code examples and best practices

---

## Testing

### Claude Ralph
```bash
# Test with sample PRD
./claude-ralph.sh 3  # Run 3 iterations
```

### ADK Agents
```bash
cd apps/<agent-name>
uv run adk web      # Web UI at localhost:8000
uv run adk run <pkg> # Terminal mode
uv run pytest       # Run tests
```

---

## Directory Structure

```
.
├── claude-ralph.sh              # Main autonomous loop
├── prompt.md                    # Claude instance instructions
├── prd.json.example            # PRD schema template
├── commands/
│   └── ralph.md                # /ralph slash command
├── skills/
│   ├── prd/SKILL.md            # PRD generator
│   ├── ralph/SKILL.md          # PRD to JSON converter
│   ├── adk-llm-agent/          # Core LlmAgent
│   ├── adk-sequential-agent/   # Sequential workflows
│   ├── adk-parallel-agent/     # Parallel execution
│   ├── adk-loop-agent/         # Iterative loops
│   ├── adk-multi-agent-orchestrator/  # Complex hierarchies
│   ├── adk-tools/              # Custom tools & MCP
│   ├── adk-sessions/           # State management
│   ├── adk-supabase-tools/     # Database integration
│   ├── adk-testing/            # Testing frameworks
│   ├── adk-deployment/         # Production deployment
│   └── adk-receipt-query-agent/ # Complete example
├── hooks/                       # Custom hooks (optional)
├── logs/                        # Session logs (runtime)
└── archive/                     # Previous runs (runtime)
```
