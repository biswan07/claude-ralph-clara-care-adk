# ClaraCare Warranty Agent

Multi-agent warranty claim system built on Google ADK that searches for manufacturer support contacts, assesses confidence, and routes claims to auto-submit or human review.

## Setup

1. Copy `.env.example` to `.env` and fill in your values
2. Install dependencies: `uv sync`
3. Run the agent: `uv run adk web`

## Architecture

- **Root Orchestrator**: Coordinates the entire workflow
- **Search Pipeline**: Parallel search of internal DB and web
- **Judge Agent**: Assesses confidence in found contacts
- **Writer Agent**: Composes warranty claim emails

## Development

```bash
# Run tests
uv run pytest

# Type check
uv run mypy clara_care

# Lint
uv run ruff check clara_care
```
